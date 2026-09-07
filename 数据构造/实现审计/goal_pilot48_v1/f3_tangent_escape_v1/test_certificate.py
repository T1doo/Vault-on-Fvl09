import copy,unittest
import numpy as np
from .certificate import SCHEMA,seal,validate,SinglePlanLease
def fixture():
    value={'schema_version':SCHEMA,'old_supported_hold_pass':False,'scene_id':'CPU_FIXTURE_SCENE','plan_id':'CPU_FIXTURE_PLAN',
        'job_namespace':'CPU_FIXTURE_ONLY','actual_joint_names':['fl_joint1'],'actual_qpos':[0.],
        'actual_actor_pose':[0,0,.78,1,0,0,0],'actual_eef_pose':[0,0,.93,1,0,0,0],
        'trace_window_sha256':'a'*64,'world_sha256':'b'*64,'robot_config_sha256':'c'*64,'native_geometry_sha256':'d'*64,
        'pad_actor_name':'pad','pad_shape_name':'pad__0','hold':{'frames':250,'support_actor_name':'pad','all_both_fingers':True,'all_selected_contact':True,'all_signal_complete':True,
        'forbidden_count':0,'support_contact_frames':16,'max_relative_translation_drift_m':.0001,'max_relative_orientation_drift_rad':.001},
        'table_contact_frames':0,'other_support_contact_frames':0,'native_gap_per_hold_frame_m':[.00002]*250,
        'hold_step_indices':list(range(250)),'hold_timestamps':(np.arange(250)*.004).tolist(),
        'overlap_pairs':[{'link':'attached_bottle','obstacle':'pad__0','clearance_m':-.0045}],
        'full_model_checks':{k:{'valid':False,'status':'MotionGenStatus.INVALID_START_STATE_WORLD_COLLISION'} for k in ('motion_gen','motion_gen_batch')},
        'target_delta_world_m':[0.,0.,.025],'target_orientation_unchanged':True}
    value['old_supported_witness']={'hold':copy.deepcopy(value['hold']),'pairs':copy.deepcopy(value['overlap_pairs']),'only_attached_bottle_support_pairs_overlap':True}
    return seal(value)
def reseal(c):c=dict(c);c.pop('certificate_sha256',None);return seal(c)
class Tests(unittest.TestCase):
    def test_new_valid_and_old_supported_mutually_exclusive(self):
        from support_pair_collision_v1.policy import verify_support_witness
        c=fixture();self.assertTrue(validate(c))
        old={'hold':c['hold'],'only_attached_bottle_support_pairs_overlap':True};self.assertFalse(verify_support_witness(old));self.assertFalse(validate(old))
    def test_raw_counts_not_rewritten(self):
        c=fixture();c['hold']['support_contact_frames']=250;self.assertFalse(validate(reseal(c)))
    def test_each_bad_boundary_rejected(self):
        for field,value in [('table_contact_frames',1),('other_support_contact_frames',1),('native_gap_per_hold_frame_m',[.00011]*250),('target_delta_world_m',[.01,0,.025]),('overlap_pairs',[{'link':'fl_link7','obstacle':'pad__0','clearance_m':-.001}]),('full_model_checks',{})]:
            c=fixture();c[field]=value;self.assertFalse(validate(reseal(c)),field)
        for field,value in [('all_both_fingers',False),('all_signal_complete',False),('forbidden_count',1),('support_contact_frames',0),('max_relative_translation_drift_m',.006),('max_relative_orientation_drift_rad',.06)]:
            c=fixture();c['hold'][field]=value;self.assertFalse(validate(reseal(c)),field)
    def test_hash_tampering_rejected(self):
        c=fixture();c['scene_id']='other';self.assertFalse(validate(c))
    def test_single_scene_single_plan_and_expiry(self):
        c=fixture();l=SinglePlanLease(c)
        with self.assertRaises(RuntimeError):l.begin_plan('other',c['plan_id'],c['world_sha256'])
        l.begin_plan(c['scene_id'],c['plan_id'],c['world_sha256'])
        with self.assertRaises(RuntimeError):l.begin_plan(c['scene_id'],c['plan_id'],c['world_sha256'])
        l.invalidate()
        with self.assertRaises(RuntimeError):l.check()
if __name__=='__main__':unittest.main()
