import copy,unittest,types
from unittest.mock import patch
import numpy as np
from . import spec,controller,runtime
from .native import screen_actor_path
from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import reference_certificate
from goal_pilot48_v1.f2_inside_native_floor_v1.geometry_verifier import GeometryVerifier

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=reference_certificate();cls.v=GeometryVerifier(cls.c);cls.lineage=spec.prefix_lineage()
        with np.load(spec.REFERENCE/'prefix_trace.npz',allow_pickle=False) as z:
            cls.eef=np.asarray(z['eef_pose'])[-1];cls.can=np.asarray(z['role_object_pose__main_can'])[-1];cls.box=np.asarray(z['role_object_pose__box'])[-1];cls.neutral=np.asarray(z['eef_pose'])[0]
        cls.s=spec.build_targets(actual_eef_pose=cls.eef,actual_can_pose=cls.can,actual_box_pose=cls.box,neutral_eef_pose=cls.neutral,certificate=cls.c,lineage=cls.lineage)
    def test_real_prefix_fresh_grasp_and_unique_support(self):
        self.assertEqual(self.s['target_geometry']['floor_geometry_candidate_indices'],[9]);self.assertTrue(self.s['target_geometry']['pass'])
        E=spec.matrix(self.s['targets'][2]['pose']);C=E@np.asarray(self.s['actual_eef_to_can'])
        self.assertTrue(np.allclose(C,spec.matrix(self.s['target_actor_pose']),atol=1e-12))
        self.assertEqual(self.s['caps']['solver_problems'],5);self.assertFalse(self.s['old_inside_success_inherited'])
    def test_old_target_or_budget_or_source_rejected(self):
        for key,value in [('support_frames',49),('settle_frames',249),('allowed_support_shape_names',['box__9','box__4'])]:
            s=copy.deepcopy(self.s);s[key]=value;s['receipt_sha256']=spec.digest({k:v for k,v in s.items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):spec.validate_spec(s)
        with self.assertRaises(ValueError):spec.build_targets(actual_eef_pose=self.eef,actual_can_pose=self.can,actual_box_pose=self.box,neutral_eef_pose=self.neutral,certificate=self.c,lineage={})
    def test_native_support_descent_and_penetration(self):
        end=np.asarray(self.s['target_actor_pose']);up=end.copy();up[2]+=.03
        p=np.asarray([up,end]);r=screen_actor_path(p,self.box,self.v,actual_start_can_pose=up,require_support=True);self.assertTrue(r['pass'])
        bad=end.copy();bad[2]-=.002
        self.assertFalse(screen_actor_path([up,bad],self.box,self.v,actual_start_can_pose=up,require_support=True)['pass'])
        with self.assertRaises(ValueError):screen_actor_path([up,end],self.box,self.v,actual_start_can_pose=end)
        with self.assertRaises(ValueError):screen_actor_path([1],self.box,self.v,actual_start_can_pose=end)
    def test_bounded_sequence_failure_propagation(self):
        class Fake:
            solver_query_count=0
            def __init__(self,fail=None):self.events=[];self.fail=fail
            def receipt(self,name):self.events.append(name);return {'pass':name!=self.fail}
            def install_carried_fullworld(self):return self.receipt('full')
            def install_floor_only(self):return self.receipt('floor')
            def plan_one(self,i):self.solver_query_count+=1;return self.receipt('plan'+str(i))
            def screen_carried(self,i):return self.receipt('screen'+str(i))
            def execute_one(self,i):return self.receipt('execute'+str(i))
            def wait_and_record(self,n):self.events.append('wait'+str(n))
            def support_gate(self):return self.receipt('support')
            def release_safety_gate(self):return self.receipt('safety')
            def open_gripper(self,x):self.events.append('open'+str(x))
            def begin_settle(self):self.events.append('begin_settle')
            def install_released_fullworld(self):return self.receipt('released')
            def final_gate(self):return self.receipt('final')
        b=Fake();r=controller.execute(b,self.s);self.assertTrue(r['pass']);self.assertEqual(r['solver_problems'],5)
        self.assertLess(b.events.index('support'),b.events.index('open0.2'));self.assertLess(b.events.index('wait250'),b.events.index('released'));self.assertLess(b.events.index('released'),b.events.index('plan3'))
        for fail in ('full','floor','plan0','screen2','execute2','support','safety','released','plan4','final'):
            b=Fake(fail);r=controller.execute(b,self.s);self.assertFalse(r['pass']);self.assertLessEqual(r['solver_problems'],5)
            if fail in ('full','floor','plan0','screen2','execute2','support'):self.assertFalse(any(str(e).startswith('open') for e in b.events))
            if fail=='safety':self.assertNotIn('open1.0',b.events)
    def test_actual_entry_rejects_wrong_current_before_model(self):
        scene=types.SimpleNamespace(planner_query_count=0)
        with patch.object(runtime,'LiveBackend',side_effect=AssertionError('must not initialize')):
            r=runtime.run(scene,{},output='CPU-no-output',current_sha256='wrong',initial_anchor_sha256=self.lineage['initial_anchor_sha256'])
        self.assertFalse(r['pass']);self.assertIn('same current/anchor',r['error']['message']);self.assertEqual(r['solver_problems'],0)
    def test_real_contact_completeness_adapter_not_fabricated(self):
        from .gates import physical_rows
        rows=[{'contact_pairs':[]},{'contact_pairs':[{}]},{}]
        result=physical_rows(rows)
        self.assertEqual([r['contact_signal_complete'] for r in result],[True,False,False])
        self.assertTrue(all('contact_signal_complete' not in r for r in rows))
    def test_anchor_equivalence_lineage_not_byte_identity(self):
        f=runtime.validate_initial_anchor_lineage
        self.assertTrue(f('ref','ref',None))
        receipt={'equivalent':True,'failures':[],'reference_sha256':'ref','candidate_sha256':'actual'}
        self.assertTrue(f('actual','ref',receipt))
        for key,value in [('equivalent',False),('reference_sha256','wrong'),('candidate_sha256','wrong'),('failures',['bad'])]:
            with self.assertRaises(ValueError):f('actual','ref',{**receipt,key:value})
        with self.assertRaises(ValueError):f('actual','ref',None)
    def test_actual_entry_preserves_earliest_library_initialization_failure(self):
        import controlled_multi_future.family_runners_v3_3 as original
        import goal_pilot48_v1.f2_inside_native_floor_v1.certificate as cert
        scene=types.SimpleNamespace(planner_query_count=0,can=object(),box=object(),robot=types.SimpleNamespace(left_original_pose=self.neutral))
        with patch.object(original.F2ControllerV3_3,'validate_replayed_prefix_physical',return_value={'pass':True}),patch.object(original,'_arm_eef_pose',return_value=self.eef),patch.object(original,'_pose',side_effect=lambda actor:self.can if actor is scene.can else self.box),patch.object(cert,'build_live_certificate',return_value=self.c),patch.object(runtime,'LiveBackend',side_effect=ImportError('CPU-only model init failure')):
            r=runtime.run(scene,{},output='CPU-no-output',current_sha256=self.lineage['reference_current']['aggregate_sha256'],initial_anchor_sha256=self.lineage['initial_anchor_sha256'])
        self.assertFalse(r['pass']);self.assertEqual(r['error']['type'],'ImportError');self.assertIn('model init',r['error']['message']);self.assertEqual(r['solver_problems'],0);self.assertTrue(r['cleanup_owned_by_caller'])
    def test_post_retreat_geometry_cannot_borrow_settle_success(self):
        from . import gates
        import controlled_multi_future.high_level_physical_runner_v1 as high
        import controlled_multi_future.family_runners_v3_3 as original
        import goal_pilot48_v1.f2_inside_native_floor_v1.contact as contact
        row={'eef_linear_velocity':np.zeros(3),'eef_angular_velocity':np.zeros(3),'actor_angular_velocity':np.zeros(3),'contact_pairs':[]}
        b=runtime.LiveBackend.__new__(runtime.LiveBackend);b.scene=types.SimpleNamespace(trace=[row],can=object(),box=object())
        b.settle_rows=[];b.spec=self.s;b.binding={'binding_sha256':self.c['binding_sha256']}
        b.verifier=types.SimpleNamespace(evaluate=lambda *args,**kwargs:{'pass':False})
        with patch.object(high,'_f2_relation_predicates',return_value={'on':False,'beside':False}),patch.object(high,'_arm_eef_pose',return_value=self.s['targets'][4]['pose']),patch.object(high,'_arm_gripper_open',return_value=True),patch.object(original,'_pose',return_value=self.can),patch.object(gates,'final_inside_gate',return_value={'pass':True}),patch.object(contact,'verify_floor_contact_window',return_value={'pass':True}),patch.object(original,'_stable_and_support',return_value=([row]*50,[0.]*50,[True]*50)):
            r=b.final_gate()
            b.verifier.evaluate=lambda *args,**kwargs:{'pass':True}
            row['eef_linear_velocity']=np.ones(3)
            moving=b.final_gate()
        self.assertFalse(r['pass']);self.assertTrue(r['original_250_settle_and_rest_gate']['pass']);self.assertFalse(r['actual_after_retreat_rest_geometry']['pass'])
        self.assertFalse(moving['pass']);self.assertFalse(moving['original_family_final_checks']['eef_linear_stationary'])
    def test_original_transport_keeps_box_contact_and_intermediate_break(self):
        from .transport import audit_transport
        row={'contact_pairs':[],'selected_gripper_contact':True,'selected_contact_actor_name':'can'}
        kw=dict(descent_start_relative_row=1,verifier=None,can_actor_name='can',selected_gripper_body_names=['finger'],allowed_gripper_assembly_body_names=['finger'],named_facility_body_names=['box'])
        self.assertTrue(audit_transport([row,row],**kw)['pass'])
        pair={'body_a':'can','body_b':'box','point_count':1,'impulse_norm_sum':.01}
        self.assertFalse(audit_transport([row,{**row,'contact_pairs':[pair]}],**kw)['pass'])
        self.assertFalse(audit_transport([row,{**row,'selected_gripper_contact':False},row],**kw)['pass'])

if __name__=='__main__':unittest.main()
