import copy,unittest
from .integrity import canonical_hash,verify_factory_inputs,verify_actual_binding
from .test_certificate import fixture,reseal
from .certificate import SinglePlanLease
from .factory import build_support_aware_motiongen
class Tests(unittest.TestCase):
    def data(self):
        c=fixture();world={'shapes':[{'name':'pad__0','value':1}]};cfg={'kinematics':{'value':1}};native=[{'name':'bottle','value':2}]
        c['world_sha256']=canonical_hash(world['shapes']);c['robot_config_sha256']=canonical_hash(cfg);c['native_geometry_sha256']=canonical_hash(native)
        return reseal(c),world,cfg,native
    def test_pure_factory_binding_pass(self):
        c,w,r,n=self.data();verify_factory_inputs(r,w,c)
    def test_factory_world_mismatch_rejected_before_CUDA(self):
        c,w,r,n=self.data();w['shapes'][0]['value']=99
        with self.assertRaisesRegex(ValueError,'world geometry changed'):
            build_support_aware_motiongen(r,w,c,tensor_args=None,lease=SinglePlanLease(c))
    def test_factory_config_mismatch_rejected_before_CUDA(self):
        c,w,r,n=self.data();r['kinematics']['value']=99
        with self.assertRaisesRegex(ValueError,'robot config changed'):
            build_support_aware_motiongen(r,w,c,tensor_args=None,lease=SinglePlanLease(c))
    def test_native_and_every_actual_pose_binding(self):
        c,w,r,n=self.data();args={'native_shapes':n,'joint_names':c['actual_joint_names'],'qpos':c['actual_qpos'],'actor_pose':c['actual_actor_pose'],'eef_pose':c['actual_eef_pose'],'world_shapes':w['shapes']}
        self.assertTrue(verify_actual_binding(c,**args))
        for key,new in [('native_shapes',[]),('joint_names',['other']),('qpos',[.001]),('actor_pose',[0,0,.79,1,0,0,0]),('eef_pose',[0,0,.94,1,0,0,0]),('world_shapes',[])]:
            changed={**args,key:new}
            with self.assertRaises(ValueError,msg=key):verify_actual_binding(c,**changed)
