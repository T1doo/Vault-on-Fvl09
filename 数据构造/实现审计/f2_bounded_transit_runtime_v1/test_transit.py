import ast,copy,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from transit import build_transit_spec,plan_test,run_ordered

class TransitTests(unittest.TestCase):
    def test_exact_routes_and_endpoints(self):
        s=build_transit_spec();self.assertEqual([r['symbols'] for r in s['routes']],[['U','D','U','N'],['H_low','U','D','U','H_low','N'],['H_current_orientation','U','D','U','H_current_orientation','N']])
        from semantic_target import corrected_contract
        _,a=corrected_contract();self.assertEqual(s['poses']['D'],a['six_targets'][2]['pose']);self.assertEqual(s['poses']['U'],a['six_targets'][1]['pose']);self.assertEqual(s['final_actor_pose'],a['corrected_actor_pose'])
    def test_hub_transform_only_permitted_fields(self):
        p=build_transit_spec()['poses'];self.assertEqual(p['H_low'][:2],p['H'][:2]);self.assertEqual(p['H_low'][3:],p['H'][3:]);self.assertEqual(p['H_low'][2],p['U'][2]);self.assertEqual(p['H_current_orientation'][:3],p['H'][:3]);self.assertEqual(p['H_current_orientation'][3:],p['C'][3:])
    def test_total_bound(self):
        s=build_transit_spec();self.assertEqual(sum(x['query_cap'] for x in s['diagnostics']+s['routes']),19)
    def fake(self,start=3,fail_at=None):
        scene=SimpleNamespace(planner_query_count=start);calls=[]
        def restore(s):calls.append('restore');return {'start':'sealed'}
        def reset(s,name):calls.append('reset');return {}
        def plan(s,targets,query_limit,arm):
            calls.append(query_limit);n=len(targets) if fail_at is None else fail_at;s.planner_query_count+=n
            return {'pass':fail_at is None,'controls':[],'segment_receipts':[{}]*n,'planner_query_count':s.planner_query_count}
        def dispatch(s,t):return plan_test(s,t,restore=restore,reset=reset,plan=plan,save_controls=lambda *x:{})
        return scene,calls,dispatch
    def test_cumulative_limit_and_delta_not_sum_of_totals(self):
        scene,calls,dispatch=self.fake();spec=build_transit_spec();r1=dispatch(scene,spec['routes'][0]);r2=dispatch(scene,spec['routes'][1])
        self.assertEqual((r1['before'],r1['after'],r1['delta'],r1['absolute_limit']),(3,7,4,7));self.assertEqual((r2['before'],r2['after'],r2['delta'],r2['absolute_limit']),(7,13,6,13));self.assertEqual(calls,['restore','reset',7,'restore','reset',13])
    def test_first_route_pass_stops(self):
        scene,calls,dispatch=self.fake(0);r=run_ordered(scene,build_transit_spec()['routes'],diagnostic=False,dispatch=dispatch);self.assertEqual(len(r),1)
    def test_D0_failure_stops(self):
        scene,calls,dispatch=self.fake(0,1);r=run_ordered(scene,build_transit_spec()['diagnostics'],diagnostic=True,dispatch=dispatch);self.assertEqual(len(r),1);self.assertFalse(r[0]['pass'])
    def test_failed_routes_consume_only_live_deltas(self):
        scene,calls,dispatch=self.fake(0,1);r=run_ordered(scene,build_transit_spec()['routes'],diagnostic=False,dispatch=dispatch);self.assertEqual(sum(x['delta'] for x in r),3)
    def test_missing_counter_rejected(self):
        scene=SimpleNamespace(planner_query_count=0)
        def bad(s,*a,**kw):del s.planner_query_count;return {'pass':False,'controls':[],'segment_receipts':[],'planner_query_count':0}
        r=plan_test(scene,build_transit_spec()['routes'][0],restore=lambda s:{},reset=lambda *x:{},plan=bad,save_controls=lambda *x:{})
        self.assertIsNone(r['delta']);self.assertFalse(r['accounting_complete'])
    def test_real_plan_chain_chains_qpos(self):
        import controlled_multi_future.family_runners_v3_1 as f
        scene=SimpleNamespace(planner_query_count=2,planner_queries=[],robot=SimpleNamespace(left_entity=SimpleNamespace(get_qpos=lambda:np.array([0.,0.],dtype=np.float32))))
        starts=[]
        def arm(s,pose,*,last_qpos,source,arm):
            self.assertLess(s.planner_query_count,s.planner_query_limit);starts.append(np.asarray(last_qpos).tolist());s.planner_query_count+=1;s.planner_queries.append({'query_id':s.planner_query_count});return {'status':'Success','position':np.array([np.asarray(last_qpos)+1],dtype=np.float32),'velocity':np.zeros((1,2),dtype=np.float32)}
        with patch.object(f,'_plan_arm',side_effect=arm):
            r=f._plan_chain(scene,build_transit_spec()['routes'][0]['targets'],query_limit=6,arm='left')
        self.assertTrue(r['pass']);self.assertEqual(starts,[[0.,0.],[1.,1.],[2.,2.],[3.,3.]]);self.assertEqual(r['planner_query_count'],6)
    def test_no_physical_control_entry(self):
        s=(Path(__file__).parent/'job_runner.py').read_text();tree=ast.parse(s)
        forbidden={'move','move_to_pose','close_gripper','open_gripper','_execute_control','_execute_planned_segment','_must_action','step'}
        calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        self.assertFalse(calls&forbidden)
if __name__=='__main__':unittest.main()
