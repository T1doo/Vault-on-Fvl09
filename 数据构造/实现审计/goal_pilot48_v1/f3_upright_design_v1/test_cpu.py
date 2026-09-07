import copy,json,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from .scene import initial_gate,derive_targets,make_scene_class
from .qualification_entry import qualify_existing_scene
P=Path(__file__).parent
def spec():return json.loads((P/'design_spec.json').read_text(encoding='utf-8'))
def snapshot(s):return dict(seed=s['seed'],scene_instance_id='CPU_ONLY',canonical_settle_steps=60,asset_id=13,scale=[.132]*3,
    bottle_pose=s['bottle_actor_pose'],pad_pose=s['pad_actor_pose'],marker_pose=[0,-.05,.95,1,0,0,0],pad_physical_contact=True,contact_signal_complete=True,
    linear_velocity=[0,0,0],angular_velocity=[0,0,0],mass_properties=s['expected_mass_properties'])
calls=[]
def create_actor(scene,p,modelname,**kwargs):calls.append((p,modelname,kwargs));return SimpleNamespace(set_mass=lambda value:calls.append(('mass',value)))
class FakeScene:
    def load_actors(self):
        self.bottle=create_actor(self,'OLD_HORIZONTAL','001_bottle',convex=True,model_id=13);self.bottle.set_mass(.01)
class Tests(unittest.TestCase):
    def test_unique_B_freeze_and_limits(self):
        s=spec();self.assertEqual(s['selected_design'],'B_upper_straight_body');self.assertEqual(s['total_round_cap']['solver_problems'],23);self.assertFalse(s['execution_ready'])
    def test_nominal_target_roundtrip(self):
        s=spec();t=derive_targets(s,s['bottle_actor_pose'])
        self.assertTrue(np.allclose(t['grasp'],s['nominal_grasp_world_pose']));self.assertTrue(np.allclose(t['pregrasp'],s['nominal_pregrasp_world_pose']))
    def test_private_scene_override_preserves_mass_and_asset(self):
        calls.clear();s=spec();cls=make_scene_class(s,FakeScene,lambda p:list(p));cls().load_actors()
        self.assertEqual(calls[0][0],s['bottle_actor_pose']);self.assertEqual(calls[0][2]['model_id'],13);self.assertEqual(calls[-1],('mass',.01))
        self.assertIs(FakeScene.load_actors.__globals__['create_actor'],create_actor)
    def test_initial_gate_requires_true_standing_and_mass(self):
        s=spec();v=snapshot(s);self.assertTrue(initial_gate(v,s)['pass'])
        v['pad_physical_contact']=False;self.assertFalse(initial_gate(v,s)['pass'])
        v=snapshot(s);v['mass_properties']=copy.deepcopy(v['mass_properties']);v['mass_properties']['mass_kg']*=2;self.assertFalse(initial_gate(v,s)['pass'])
    def ports(self,s,fail=None):
        self.calls=[]
        def note(name,value):self.calls.append(name);return value
        micro={'pass':fail!='micro','solver_problems':3,'post_lift':{'pass':True},'native_full_arm_controls_pass':True,'full_world_restoration_checks':{k:{'valid':True} for k in ('motion_gen','motion_gen_batch')}}
        v=snapshot(s)
        if fail=='standing':v['pad_physical_contact']=False
        return SimpleNamespace(snapshot=lambda scene:v,capture_current_anchor_initialize_trace=lambda scene:note('init',None),
            single_full_constraint_IK=lambda scene,label,targets:note(label,{'pass':fail!=label,'solver_problems':1}),
            micro_three_plans=lambda *a:note('micro',micro),record_micro_pass=lambda *a:note('micro_receipt',None),
            original_prefix_extension_eleven_plans=lambda *a:note('prefix',{'pass':True,'solver_problems':11}))
    def test_first_qualification6_second17(self):
        s=spec();p=self.ports(s);r=qualify_existing_scene(None,s,p);self.assertTrue(r['qualified']);self.assertEqual(r['solver_problems'],6);self.assertNotIn('prefix',self.calls)
        p=self.ports(s);r=qualify_existing_scene(None,s,p,confirmation=True,prior_pass=r);self.assertEqual(r['solver_problems'],17);self.assertEqual(self.calls[-2:],['micro_receipt','prefix'])
    def test_standing_and_IK_failure_stop_before_micro(self):
        s=spec()
        for failure,count in [('standing',0),('current',1),('pregrasp',2),('grasp',3)]:
            p=self.ports(s,failure);r=qualify_existing_scene(None,s,p);self.assertFalse(r['qualified']);self.assertEqual(r['solver_problems'],count);self.assertNotIn('micro',self.calls)
    def test_failed_confirmation_never_reaches_sharedV(self):
        s=spec();p=self.ports(s,'micro');r=qualify_existing_scene(None,s,p,confirmation=True,prior_pass={'qualified':True,'spec_receipt':s['receipt_sha256']});self.assertFalse(r['qualified']);self.assertNotIn('prefix',self.calls)
        with self.assertRaises(ValueError):qualify_existing_scene(None,s,p,confirmation=True,prior_pass=None)
if __name__=='__main__':unittest.main()
