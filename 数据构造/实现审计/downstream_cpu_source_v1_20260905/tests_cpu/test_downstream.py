import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from cmf_downstream_cpu.io import canonical,seal,write_new,load
from cmf_downstream_cpu.publication import TwoPhasePublisher
from cmf_downstream_cpu.matrices import finalize_matrix,LEVELS,EVIDENCE,check_split_atomicity
from cmf_downstream_cpu.realizations import build_spec,retime_control_for_new_execution,execute_realization,preflight
from cmf_downstream_cpu.schemas import build_stage1,build_stage2_pending
from controlled_multi_future.anchor import capture_anchor

class PublisherTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp');self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def branches(self,shared=2):
        anchor=capture_anchor(robot_qpos=np.zeros(14),robot_qvel=np.zeros(14),actor_poses={'red':[0,0,0,1,0,0,0]},gripper_state=[1,1],metadata={'synthetic':True})
        rows=[]
        for color,letter in zip(('red','green','blue'),('1','2','3')):
            prefix={'executed_prefix_action_sha256':'a'*64,'executed_prefix_step_count':10,'executed_prefix_start_state_sha256':'b'*64,
               'executed_prefix_end_state_sha256':'c'*64,'executed_prefix_start_anchor':anchor,'executed_prefix_end_anchor':anchor,
               'canonical_prefix_end_step':10,'first_post_prefix_divergence_step':10,'neutral_confirmation_step_count':0,
               'neutral_confirmation_minimum_required_steps':0,'post_prefix_action_step_sha256':['f'*64]*shared+[letter*64]}
            rows.append({'program_id':'F1-'+color,'status':'accepted','reference_current_sha256':'c'*64,'branch_current':{'aggregate_sha256':'c'*64},
               'anchor_equivalence':{'equivalent':True},'candidate_universe_sha256':'d'*64,'prefix_sha256':'e'*64,'executed_prefix':prefix,
               'verifier':{'pass':True},'synthetic_fixture':True})
        return rows
    def publish(self,rows,publisher=None):return (publisher or TwoPhasePublisher(self.path)).publish('cpu-root',rows,reference_current_sha256='c'*64,cleanup_pass=True)
    def test_immediate_divergence(self):self.assertEqual(self.publish(self.branches(0))['computed_divergence'],10)
    def test_late_divergence_real_publisher_finalizer(self):
        rows=self.branches(2);r=self.publish(rows);self.assertEqual(r['computed_divergence'],12)
        self.assertTrue(all(x['executed_prefix']['first_post_prefix_divergence_step']==10 for x in rows))
        root=load(TwoPhasePublisher(self.path).location('cpu-root')/'root.json');self.assertTrue(all(x['executed_prefix']['canonical_prefix_end_step']==10 and x['executed_prefix']['first_post_prefix_divergence_step']==12 for x in root['branches']))
    def test_incomplete_branch_set_never_registered(self):
        with self.assertRaises(ValueError):self.publish(self.branches()[:2])
        self.assertFalse(TwoPhasePublisher(self.path).index('cpu-root').exists())
    def test_interruption_before_index(self):
        count=[0]
        def interrupt(path,value):
            if 'finalized' in str(path):
                count[0]+=1
                if count[0]==2:raise OSError('synthetic interruption')
            write_new(path,value)
        with self.assertRaises(OSError):self.publish(self.branches(),TwoPhasePublisher(self.path,writer=interrupt))
        self.assertFalse(TwoPhasePublisher(self.path).index('cpu-root').exists())
    def test_duplicate_registration_is_idempotent(self):
        rows=self.branches();self.assertTrue(self.publish(rows)['new_registration']);self.assertFalse(self.publish(rows)['new_registration'])
        self.assertEqual(len(list((self.path/'acceptance_index').glob('*.json'))),1)
    def test_disk_final_branch_mismatch(self):
        self.publish(self.branches());p=next(TwoPhasePublisher(self.path).location('cpu-root').glob('finalized/*.json'))
        d=json.loads(p.read_text());d['payload']['executed_prefix']['first_post_prefix_divergence_step']=11;p.write_text(json.dumps(d))
        with self.assertRaises(ValueError):TwoPhasePublisher(self.path).audit('cpu-root')

class MatrixTests(unittest.TestCase):
    programs={'F1-red':'a'*64,'F1-green':'b'*64,'F1-blue':'c'*64}
    def rows(self,level):
        return [{'root_id':'r','program_id':p,'program_semantic_sha256':h,'realization':v,'raw_id':p+v,'rollout_id':p+v,
          'origin_kind':'real_rollout','derived_from_raw_id':None,'current_sha256':'cur','candidate_universe_sha256':'universe',
          'orphan_process_count':0,'evidence_scope':'synthetic_fixture',**{k:True for k in EVIDENCE}} for p,h in self.programs.items() for v in LEVELS[level]]
    def audit(self,rows,level='pilot_A'):return finalize_matrix('r',self.programs,rows,level=level,family='F1')
    def test_separate_counts_3_6_6_9(self):
        for level,n in zip(LEVELS,(3,6,6,9)):
            r=self.audit(self.rows(level),level);self.assertTrue(r['matrix_complete']);self.assertEqual(r['expected_trajectory_count'],n);self.assertFalse(r['accepted'])
    def test_duplicate_raw_id(self):
        r=self.rows('pilot_A');r[1]['raw_id']=r[0]['raw_id'];self.assertFalse(self.audit(r)['matrix_complete'])
    def test_resampled_view_not_realization(self):
        r=self.rows('pilot_A');r[1]['origin_kind']='resampled_view';self.assertFalse(self.audit(r)['matrix_complete'])
    def test_pilot_A_motion_variant_rejected(self):
        r=self.rows('pilot_A');r[1]['realization']='r_inv_motion';self.assertFalse(self.audit(r)['matrix_complete'])
    def test_pilot_B_missing_rpc(self):self.assertFalse(self.audit(self.rows('pilot_B')[1:],'pilot_B')['matrix_complete'])
    def test_wrong_program(self):
        r=self.rows('pilot_A');r[0]['program_semantic_sha256']='wrong';self.assertFalse(self.audit(r)['matrix_complete'])
    def test_mixed_root(self):
        r=self.rows('pilot_A');r[1]['root_id']='other';self.assertFalse(self.audit(r)['matrix_complete'])
    def test_superroot_split_leak(self):
        with self.assertRaises(ValueError):check_split_atomicity([{'root_id':'a','super_root_id':'s','split':'train'},{'root_id':'b','super_root_id':'s','split':'test'}])

class RealizationTests(unittest.TestCase):
    def fixtures(self):
        p={'program_id':'F4-ABC','order':['A','B','C']};root={'root_id':'r','family':'F4','programs':{p['program_id']:canonical(p)},'candidate_universe_sha256':'u','current_sha256':'c','anchor_sha256':'a'}
        ops=[{'kind':'move','operation_id':'carry','arm':'left','target_pose':[0.,0.,1.,1.,0.,0.,0.],'noncritical_transport':True},
             {'kind':'move','operation_id':'place','arm':'left','target_pose':[.1,0.,.8,1.,0.,0.,0.],'boundary_critical':True}]
        return root,p,ops
    def test_path_only_noncritical_changes(self):
        root,p,ops=self.fixtures();s=build_spec(root,p,ops,'r_inv_path');self.assertEqual(s['operations'][1],ops[1]);self.assertAlmostEqual(s['operations'][0]['target_pose'][2],1.015);self.assertEqual(s['budget']['planner_queries'],2)
    def test_same_rule_across_program_order(self):
        root,p,ops=self.fixtures();a=build_spec(root,p,ops,'r_inv_motion');q={'program_id':'F4-ACB','order':['A','C','B']};root['programs'][q['program_id']]=canonical(q);b=build_spec(root,q,ops,'r_inv_motion');self.assertEqual(a['variation_rule_sha256'],b['variation_rule_sha256']);self.assertEqual(q['order'],['A','C','B'])
    def test_new_execution_speed_controls_not_raw(self):
        c={'position':np.array([[0.],[1.],[2.]],np.float32),'velocity':np.ones((3,1),np.float32)};out=retime_control_for_new_execution(c,1.1)
        self.assertGreater(len(out['position']),len(c['position']));np.testing.assert_array_equal(out['position'][[0,-1]],c['position'][[0,-1]]);self.assertEqual(out['position'].dtype,np.float32)
    def test_unbound_adapter_fails_cpu_preflight(self):
        root,p,ops=self.fixtures();s=build_spec(root,p,ops,'r_inv_path')
        with self.assertRaises(ValueError):preflight(s,object())
    def test_gpu_authorization_not_inferred(self):
        root,p,ops=self.fixtures();s=build_spec(root,p,ops,'r_inv_motion')
        class Adapter:
            def __getattr__(self,n):return lambda *a,**k:None
        with self.assertRaises(PermissionError):execute_realization(s,Adapter(),seal({'authorized':False}))

class SchemaTests(unittest.TestCase):
    def test_48_cells_no_auto_promotion(self):
        m=build_stage1({});self.assertEqual(len(m['cells']),48);self.assertEqual(m['accepted_authorized_count'],0);self.assertTrue(all(c['stage_authorized'] is False for c in m['cells']))
    def test_pending_40_16_and_quotas(self):
        from collections import Counter
        m=build_stage2_pending();self.assertEqual(len(m['primary_slots']),40);self.assertEqual(len(m['ordered_reserves']),16)
        for f in ('F1','F2','F3','F4'):
            rows=[r for r in m['primary_slots'] if r['family']==f];self.assertEqual(Counter(r['split'] for r in rows),{'train':5,'validation':2,'test':3});self.assertEqual(Counter(r['difficulty'] for r in rows),{'clear':2,'medium':6,'crowded':2})
        self.assertTrue(all(r['current_sha256'] is None and r['candidate_universe_sha256'] is None for r in m['primary_slots']+m['ordered_reserves']))
if __name__=='__main__':unittest.main()
