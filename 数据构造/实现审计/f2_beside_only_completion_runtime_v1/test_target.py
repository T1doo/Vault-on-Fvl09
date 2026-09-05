import unittest
from contextlib import contextmanager
from types import SimpleNamespace
import numpy as np
from semantic_target import corrected_contract,old,compose_pose,pose_matrix,sha
from scene_attempt import record_attempt

class TargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c,cls.a=corrected_contract()
    def test_old_xy_overwrite_rejected(self):
        self.assertGreater(self.a["old_xy_overwrite_position_error_m"],1e-6)
    def test_geometry_center_lands_on_candidate2_xy(self):
        np.testing.assert_allclose(self.a["composed_geometry_center_pose"][:2],[.08,.07],rtol=0,atol=1e-12)
    def test_actor_origin_contains_rotated_local_center_compensation(self):
        np.testing.assert_allclose(np.asarray(self.a["corrected_actor_pose"][:2]),np.asarray(self.a["candidate_geometry_xy"])-np.asarray(self.a["rotated_local_center"][:2]),rtol=0,atol=1e-12)
    def test_candidate0_template_translated_to_candidate2_matches(self):
        self.assertTrue(self.a["translated_candidate0_matches"])
    def test_orientation_unchanged(self):
        self.assertEqual(self.a["corrected_actor_pose"][3:],[.5,.5,.5,.5])
    def test_support_plane_unchanged(self):
        self.assertAlmostEqual(self.a["support_plane_z_m"],.74,12)
    def test_beside_six_segment_order_unchanged(self):
        self.assertEqual([t["segment_id"] for t in self.a["six_targets"]],list(old.BESIDE_SEGMENTS))
    def test_inside_receipt_unchanged(self):
        from pathlib import Path
        p=Path("/nfs_share/lijunhui/Robotwin2/datasets/controlled_multi_future_f2_controlled_insertion_route_gate_v1/f2-controlled-insertion-route-gate-short-tmpdir-recovery-run3/inside_planner_receipt.json")
        before=sha(p); corrected_contract();self.assertEqual(before,sha(p))
    def test_target_failure_still_writes_scene_cleanup(self):
        context=SimpleNamespace(cleanup_receipt=None);scene=SimpleNamespace(planner_query_count=0)
        @contextmanager
        def opened():
            try:yield scene,context
            finally:context.cleanup_receipt={"scene_instance_id":"cpu","cleanup_safety_pass":True}
        def derive(s):raise ValueError("synthetic target mismatch")
        def plan(*a):raise AssertionError("planner must not be called")
        written=[];r=record_attempt(opened,derive,plan,written.append)
        self.assertEqual(len(written),1);self.assertTrue(r["cleanup"]["cleanup_safety_pass"])
        self.assertEqual(r["planner_delta"],0);self.assertIsNotNone(r["error"])
if __name__=="__main__":unittest.main()
