import copy,types,unittest
from unittest.mock import patch
from goal_pilot48_v1.f2_inside_native_floor_v1.test_cpu import Tests as NativeFixtures
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.spec import digest
from . import runtime
from .transport import audit_transport,validate_projection,row_commitment
from .approval import verify_approval,APPROVAL_SHA

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NativeFixtures.setUpClass();cls.fixture=NativeFixtures();cls.v=cls.fixture.verifier
    def row(self,**kwargs):
        row=self.fixture.row(**kwargs);row.update(selected_gripper_contact=True,selected_contact_actor_name=self.v.c['can_actor_name'])
        grasp=copy.deepcopy(row['contact_pairs'][0]);grasp['body_b']='finger';row['contact_pairs'].append(grasp)
        return row
    def kwargs(self,end=1):return dict(descent_start_relative_row=0,supported_stage_end_relative_row=end,held_window_start_trace_row=100,verifier=self.v,
      can_actor_name=self.v.c['can_actor_name'],selected_gripper_body_names=['finger'],allowed_gripper_assembly_body_names=['finger'],named_facility_body_names=[self.v.c['box_actor_name']])
    def rows(self):
        r=self.row();start=copy.deepcopy(r);start['contact_pairs']=start['contact_pairs'][1:];return [start,r]
    def test_approved_native_projection_keeps_old_failure_and_raw(self):
        rows=self.rows();before=row_commitment(rows);r=audit_transport(rows,**self.kwargs())
        self.assertTrue(r['pass']);self.assertFalse(r['original_unmodified_audit']['pass']);self.assertEqual(before,row_commitment(rows));self.assertEqual(len(r['projected_pair_receipts']),1)
        self.assertEqual(r['approval']['approval_sha256'],APPROVAL_SHA);self.assertTrue(validate_projection(r,rows,**self.kwargs()))
        self.assertEqual(r['projected_pair_receipts'][0]['absolute_trace_row'],101)
    def test_boundary_before_start_last_hold_and_after_end(self):
        self.assertFalse(audit_transport([self.row(),self.row()],**self.kwargs())['pass'])
        rows=self.rows()+[self.row() for _ in range(50)]
        r=audit_transport(rows,**self.kwargs(end=51));self.assertTrue(r['pass']);self.assertEqual(r['projected_pair_receipts'][-1]['relative_row'],51)
        self.assertFalse(audit_transport(rows,**self.kwargs(end=50))['pass'])
    def test_other_floor_wall_wrong_unknown_shape_rejected(self):
        for index in (0,4,14):
            rows=self.rows();rows[-1]=self.row(box_index=index);self.assertFalse(audit_transport(rows,**self.kwargs())['pass'])
        rows=self.rows();rows[-1]['contact_pairs'][0]['shape_identities'][1]['body_collision_shape_index']=8
        self.assertFalse(audit_transport(rows,**self.kwargs())['pass'])
        rows=self.rows();rows[-1]['contact_pairs'][0]['shape_identities']=[];self.assertFalse(audit_transport(rows,**self.kwargs())['pass'])
    def test_grasp_loss_missing_physical_grasp_or_contact_evidence_rejected(self):
        for mutate in (lambda r:r.update(selected_gripper_contact=False),lambda r:r.update(selected_contact_actor_name='wrong'),
          lambda r:r['contact_pairs'].pop(),lambda r:r['contact_pairs'][0].update(point_evidence=[])):
            rows=self.rows();mutate(rows[-1]);self.assertFalse(audit_transport(rows,**self.kwargs())['pass'])
    def test_native_penetration_and_wrong_frame_rejected(self):
        rows=self.rows();rows[-1]['role_actor_poses']['main_can'][2]-=.002;self.assertFalse(audit_transport(rows,**self.kwargs())['pass'])
        rows=self.rows();rows[-1]['actor_pose_frame']='box_local';self.assertFalse(audit_transport(rows,**self.kwargs())['pass'])
    def test_tampered_projection_even_rehashed_rejected(self):
        rows=self.rows();r=audit_transport(rows,**self.kwargs());r['projected_pair_receipts'][0]['relative_row']=0
        with self.assertRaises(ValueError):validate_projection(r,rows,**self.kwargs())
        r['receipt_sha256']=digest({k:v for k,v in r.items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):validate_projection(r,rows,**self.kwargs())
    def test_after_first_slow_open_and_old_globals_unchanged(self):
        b=runtime.LiveBackend.__new__(runtime.LiveBackend);b.slow_open_started=True
        with self.assertRaises(ValueError):b.transport_gate()
        old=runtime.old;before=old._run.__globals__['LiveBackend'];fn=runtime.private(old._run,LiveBackend=runtime.LiveBackend)
        self.assertIs(old._run.__globals__['LiveBackend'],before);self.assertIsNot(fn.__globals__,old._run.__globals__)
        with patch('goal_pilot48_v1.f2_controlled_inside_runtime_v3.approval.sha',return_value='bad'):
            with self.assertRaises(ValueError):verify_approval()
    def test_actual_v3_run_dispatches_new_backend_without_mutating_v2(self):
        from goal_pilot48_v1.f2_controlled_inside_runtime_v2.test_cpu import Tests as OldFixture
        import controlled_multi_future.family_runners_v3_3 as original
        import goal_pilot48_v1.f2_inside_native_floor_v1.certificate as certificate
        OldFixture.setUpClass();f=OldFixture;old_class=runtime.old.LiveBackend
        scene=types.SimpleNamespace(planner_query_count=0,can=object(),box=object(),robot=types.SimpleNamespace(left_original_pose=f.neutral))
        with patch.object(original.F2ControllerV3_3,'validate_replayed_prefix_physical',return_value={'pass':True}),patch.object(original,'_arm_eef_pose',return_value=f.eef),patch.object(original,'_pose',side_effect=lambda actor:f.can if actor is scene.can else f.box),patch.object(certificate,'build_live_certificate',return_value=f.c),patch.object(runtime,'LiveBackend',side_effect=ImportError('CPU_V3_BACKEND_DISPATCH')):
            r=runtime.run(scene,{},output='CPU-no-output',current_sha256=f.lineage['reference_current']['aggregate_sha256'],initial_anchor_sha256=f.lineage['initial_anchor_sha256'])
        self.assertFalse(r['pass']);self.assertEqual(r['error']['message'],'CPU_V3_BACKEND_DISPATCH');self.assertIs(runtime.old.LiveBackend,old_class)
        self.assertEqual(r['implementation_version'],'f2_controlled_inside_runtime_v3')
