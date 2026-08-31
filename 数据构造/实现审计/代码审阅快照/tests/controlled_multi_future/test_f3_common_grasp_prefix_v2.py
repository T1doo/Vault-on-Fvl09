import unittest
from controlled_multi_future.f3_common_grasp_prefix_v2 import build_f3_common_grasp_prefix_v2,validate_f3_common_grasp_prefix_v2
from controlled_multi_future.family_runners_v3_3 import F3ControllerV3_3
class TestF3CommonGraspPrefixV2(unittest.TestCase):
    def test_contract(self):
        value=build_f3_common_grasp_prefix_v2(); self.assertEqual(validate_f3_common_grasp_prefix_v2(value),value); self.assertEqual(value["close_normalized_target"],0.5); self.assertEqual(value["trace_evidence"]["contact_window_contact_fraction"],1.0); self.assertFalse(value["invariants"]["online_success_selection_forbidden"] is False)
    def test_controller_binding(self):
        c=F3ControllerV3_3(); c.f3_common_grasp_prefix_v2=build_f3_common_grasp_prefix_v2(); p=c.canonical_prefix_contract([]); self.assertEqual(p["close_normalized_target"],0.5); self.assertIn("f3_common_grasp_prefix_v2",p)
    def test_mutual_exclusion(self):
        from controlled_multi_future.f3_contact_preserving_prefix_v11 import build_f3_contact_preserving_prefix_contract_v11
        c=F3ControllerV3_3(); c.f3_common_grasp_prefix_v2=build_f3_common_grasp_prefix_v2(); c.f3_shared_prefix_repair_v11=build_f3_contact_preserving_prefix_contract_v11()
        with self.assertRaises(ValueError): c.canonical_prefix_contract([])
if __name__=="__main__": unittest.main()
