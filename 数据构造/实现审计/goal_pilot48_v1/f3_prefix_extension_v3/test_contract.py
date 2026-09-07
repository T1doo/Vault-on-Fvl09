import unittest,copy
from types import SimpleNamespace
import numpy as np
from .controller import lift_extension_goal,check_budget
from .boundaries import record,tail_with_markers
from .locked_tail import original_tail
from .prerequisite import verify_values
class Tests(unittest.TestCase):
    def test_exact_target_derivation(self):
        pose=np.array([.1,.2,.9,1.,0,0,0]);g=lift_extension_goal(pose,.015);self.assertAlmostEqual(g[2],.915);self.assertTrue(np.array_equal(g[[0,1,3,4,5,6]],pose[[0,1,3,4,5,6]]))
        self.assertAlmostEqual(lift_extension_goal(g,.04)[2],.955)
        with self.assertRaises(ValueError):lift_extension_goal(pose,.02)
    def test_V_is_seven_table_Z_goals_fixed_amplitude(self):
        from controlled_multi_future import family_runners_v3_3 as old
        pose=np.array([.1,.2,.9,1.,0,0,0]);targets=old._time_dilated_closed_loop_event_targets(pose,axis='V',amplitude_m=.055,segment_prefix='test')
        self.assertEqual(len(targets),7);self.assertTrue(np.allclose([t['pose'][2]-.9 for t in targets],[.0275,.055,0,-.0275,-.055,-.0275,0]));self.assertEqual(old.F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2,50)
        for t in targets:self.assertTrue(np.array_equal(t['pose'][:2],pose[:2]))
    def test_budget14_not15(self):
        count=3
        for n in [1,1,2,1,1,1,1,1,1,1]:check_budget(count,n);count+=n
        self.assertEqual(count,14)
        with self.assertRaises(ValueError):check_budget(count,1)
    def test_boundary_uses_earlier_trace_pose(self):
        row=lambda z,i:{'step_index':i,'timestamp':i*.004,'eef':[0,0,z,1,0,0,0],'actor_pose':[0,0,z-.1,1,0,0,0]}
        scene=SimpleNamespace(trace=[row(.9,0),row(1.2,1)],markers={});r=record(scene,'post_close',0)
        self.assertEqual(r['actual_eef'][2],.9);self.assertEqual(scene.markers['f3_extension_post_close'],0)
        with self.assertRaises(ValueError):record(scene,'post_close',1)
    def test_original_tail_has_exact_six_boundary_hooks(self):
        from controlled_multi_future import family_runners_v3_3 as old
        fn=tail_with_markers(original_tail,dict(old.__dict__));self.assertTrue(callable(fn))
    def test_prior_confirmation_must_pass_restoration_and_recipe(self):
        m={'manifest_sha256':'M','recipe_spec_path':'recipe','route_spec_path':'route'};n={'run_id':'new','recipe_spec_path':'recipe','route_spec_path':'route','expected_recipe_id':'R'}
        p={'pass':True,'accounting_complete':True,'job_id':'old','manifest_sha256':'M','receipt_sha256':'T','runtime_result':{'micro_pass':True,'proposal_id':'R','result':{'pass':True,'full_world_restoration_checks':{k:{'valid':True} for k in ('motion_gen','motion_gen_batch')}}}}
        g={'task_owned_cleanup_pass':True,'child_exit_code':0,'run_id':'old'};self.assertTrue(verify_values(p,g,m,n)['first_fresh_micro_pass'])
        bad=copy.deepcopy(p);bad['runtime_result']['result']['full_world_restoration_checks']={}
        with self.assertRaises(ValueError):verify_values(bad,g,m,n)
        with self.assertRaises(ValueError):verify_values(p,g,m,{**n,'run_id':'old'})
if __name__=='__main__':unittest.main()
