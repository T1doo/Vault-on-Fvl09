"""Synthetic CPU stages; no simulator, qualification, or generated raw."""
import ast,copy,unittest
import numpy as np
from types import SimpleNamespace
from unittest.mock import patch
from .controller import execute
from .spec import make_targets,matrix,proposal
from . import gates

class Backend:
    def __init__(self,fail=None):self.solver_query_count=0;self.events=[];self.fail=fail
    def event(self,name):self.events.append(name);return {'pass':name!=self.fail}
    def install_carried(self,i):return self.event('carry'+str(i))
    def install_released(self):return self.event('released')
    def plan_one(self,i):self.solver_query_count+=1;return self.event('plan'+str(i))
    def screen_carried(self,i):return self.event('native'+str(i))
    def execute_one(self,i):return self.event('execute'+str(i))
    def held_gate(self):return self.event('held')
    def full_open(self):self.event('open')
    def wait_and_record(self,n):self.event('wait'+str(n))
    def final_gate(self):return self.event('final')

def spec(relation='on'):return {'relation':relation,'settle_frames':100,'rest_frames':75,'targets':[{} for _ in range(4)]}

class Tests(unittest.TestCase):
    def test_four_stages_original_windows_both_relations(self):
        for relation in ('on','beside'):
            b=Backend();r=execute(b,spec(relation));self.assertTrue(r['pass']);self.assertEqual(r['solver_problems'],4)
            self.assertEqual(b.events,['carry0','plan0','native0','execute0','carry1','plan1','native1','execute1','held','open','wait100','released','plan2','execute2','plan3','execute3','wait75','final'])
            self.assertFalse(r['whole_root_pass']);self.assertEqual(r['collection_attempts'],0)
    def test_every_required_failure_stops(self):
        for stage in ('carry0','plan0','native0','execute0','carry1','plan1','native1','execute1','held','released','plan2','execute2','plan3','execute3','final'):
            b=Backend(stage);r=execute(b,spec());self.assertFalse(r['pass']);self.assertEqual(b.events[-1],stage)
            if stage in ('held','native1'):self.assertNotIn('open',b.events)
    def test_no_inside_windows_or_extra_solver(self):
        s=spec();s['settle_frames']=250;self.assertFalse(execute(Backend(),s)['pass'])
        b=Backend();original=b.execute_one
        def illegal(i):b.solver_query_count+=1;return original(i)
        b.execute_one=illegal;self.assertFalse(execute(b,spec())['pass']);self.assertNotIn('open',b.events)
    def test_actual_grasp_not_old_eef_target(self):
        e=[0,0,1,1,0,0,0];can=[.1,0,.9,1,0,0,0];target=[.3,.2,.75,1,0,0,0];rest=[0,0,1.2,1,0,0,0]
        for height in (.1,proposal()['new_approach_height_m']):
            goals,grasp=make_targets(e,can,target,rest,height)
            np.testing.assert_allclose(matrix(goals[1]['pose'])@np.asarray(grasp),matrix(target),atol=1e-12)
            self.assertAlmostEqual(goals[0]['pose'][2]-goals[1]['pose'][2],height)
            self.assertEqual(len(goals),4)
        self.assertAlmostEqual(proposal()['new_approach_height_m'],.047946915502860445)
        changed=[.02,0,1,1,0,0,0]
        a,_=make_targets(e,can,target,rest,.1);b,_=make_targets(changed,can,target,rest,.1)
        self.assertNotEqual(a[1]['pose'],b[1]['pose'])
    def test_real_original_gate_AST_bindings(self):
        ns,held,final=gates.original_blocks()
        compile(ast.Module(body=held,type_ignores=[]),'<CPU actual held>','exec')
        compile(ast.Module(body=final,type_ignores=[]),'<CPU actual final>','exec')
        text=ast.unparse(ast.Module(body=final,type_ignores=[]))
        self.assertIn('on_bottom_height_error <= 0.02',text);self.assertIn('0.12 <= radial <= 0.23',text)
        self.assertIn('_stable_and_support',text);self.assertIn('PROVISIONAL_RUNTIME_THRESHOLDS',text)
        with self.assertRaises(ValueError):gates.final(None,{'relation':'inside'},None)
    def test_original_final_statements_execute_false_input_blocks(self):
        # Synthetic observations feed the REAL original final statements;
        # these fixtures are not verifier receipts for any actual dataset.
        ns,held,nodes=gates.original_blocks()
        can,box,scale,stand=object(),object(),SimpleNamespace(get_functional_point=lambda i:[0,0,.74]),object()
        scene=SimpleNamespace(can=can,box=box,scale=scale,stand=stand,trace=[{'eef_linear_velocity':[0,0,0],'eef_angular_velocity':[0,0,0]}])
        poses={id(can):np.array([0,0,.79,1,0,0,0]),id(box):np.array([2,2,0,1,0,0,0]),id(stand):np.array([1,0,.74,1,0,0,0])}
        ns.update(_pose=lambda a:poses[id(a)],_actor_geometry_center_pose=lambda a:poses[id(a)],
          _actor_half_extents=lambda a:np.array([.02,.02,.05]),verify_true_cavity_obb=lambda *a:{'pass_true_cavity_obb':False},
          _f2_active_cavity_contract=lambda s:{},_f2_active_scale_support_half_xy=lambda s:np.array([.1,.1]),
          _stable_and_support=lambda *a:([{'actor_angular_velocity':[0,0,0]}],[0.],[True]),
          _arm_eef_pose=lambda *a:np.array([0,0,1,1,0,0,0]),_arm_gripper_open=lambda *a:True)
        s={'relation':'on','targets':[{'pose':[0,0,1,1,0,0,0]}]*4}
        with patch.object(gates,'original_blocks',return_value=(ns,held,nodes)):
            self.assertTrue(gates.final(scene,s,{'pass':True})['pass'])
            self.assertFalse(gates.final(scene,s,{'pass':False})['pass'])
            poses[id(can)][0]=.2
            self.assertFalse(gates.final(scene,s,{'pass':True})['pass'])
    def test_real_prefix_bound_spec_uses_current_grasp(self):
        from .spec import build_contract,build_targets,validate
        from goal_pilot48_v1.f2_inward_runtime_v3.contract import P
        import json
        config=json.loads((P/'assets/objects/071_can/model_data0.json').read_text(encoding='utf-8'))
        can=SimpleNamespace(config=config,get_pose=lambda:SimpleNamespace(p=np.array([.0,-.1,.92]),q=np.array([1,0,0,0])))
        scene=SimpleNamespace(can=can,scale=SimpleNamespace(get_functional_point=lambda i:np.array([.2,-.1,.78])),
          _cmf_f2_asset_binding_v3=build_contract()['binding'],robot=SimpleNamespace(get_left_ee_pose=lambda:np.array([.1,-.1,1.,1,0,0,0]),left_original_pose=[0,0,1.1,1,0,0,0]))
        for relation in ('on','beside'):
            s=build_targets(scene,relation);self.assertTrue(validate(s));self.assertEqual(s['settle_frames'],100)
            np.testing.assert_allclose(matrix(s['targets'][1]['pose'])@np.asarray(s['actual_eef_to_can']),matrix(s['target_actor_pose']),atol=1e-12)
    def test_native_world_all_samples_table_only_no_scale_exception(self):
        import trimesh
        from .native import NativeWorld
        mesh=trimesh.creation.box(extents=[.1,.1,.1])
        shape={'name':'can__0','vertices':mesh.vertices.tolist(),'faces':mesh.faces.tolist(),
          'shape_local_pose':[0,0,0,1,0,0,0],'solver_pose':[0,0,0,1,0,0,0]}
        floor=copy.deepcopy(shape);floor['name']='table__0';floor['solver_pose']=[0,0,-.1,1,0,0,0]
        world=NativeWorld({'shapes':[floor]},[shape],[0,0,0,1,0,0,0])
        poses=[[0,0,.1,1,0,0,0],[0,0,.0,1,0,0,0]]
        self.assertTrue(world.screen(poses,table_support=True)['pass'])
        poses[-1][2]=-.01;self.assertFalse(world.screen(poses,table_support=True)['pass'])
        floor['name']='scale__0';world=NativeWorld({'shapes':[floor]},[shape],[0,0,0,1,0,0,0])
        self.assertFalse(world.screen(poses,table_support=True)['pass'])

if __name__=='__main__':unittest.main()
