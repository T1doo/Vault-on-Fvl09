import unittest

from controlled_multi_future.generation_repair_v2 import (
    GenerationRepairExecutionDisabled,
    assert_high_level_gpu_issuance_disabled_v2,
    build_generation_repair_contract_v2,
    validate_generation_repair_contract_v2,
)


class GenerationRepairV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_generation_repair_contract_v2()

    def test_all_execution_and_later_stage_authorizations_are_false(self):
        for key in (
            "old_terminal_scope_rerun_authorized",
            "planner_execution_authorized",
            "gpu_execution_authorized",
            "physical_execution_authorized",
            "stage1_authorized",
            "formal_360_authorized",
            "training_authorized",
            "h_reveal_authorized",
            "compression_authorized",
            "pi05_authorized",
        ):
            self.assertFalse(self.contract[key], key)
        self.assertEqual(
            validate_generation_repair_contract_v2(self.contract), self.contract
        )

    def test_old_terminal_claims_are_corrected_without_rerun(self):
        self.assertEqual(
            self.contract["legacy_terminals"]["F4"]["corrected_status"],
            "INVALID_BY_CONSTRUCTION_TARGET_OVERLAPS_UNMOVED_OBJECT",
        )
        self.assertIn(
            "SEARCH_DESIGN_INCOMPLETE",
            self.contract["legacy_terminals"]["F3"]["corrected_status"],
        )
        self.assertEqual(
            self.contract["new_cpu_contracts"]["F3"]["recipe_count"], 3840
        )
        f2 = self.contract["new_cpu_contracts"]["F2"]
        self.assertTrue(f2["two_phase_controlled_insertion_executor_implemented"])
        self.assertTrue(f2["post_close_actual_transform_replan_required"])
        self.assertTrue(f2["support_before_release_required"])
        self.assertFalse(f2["primary_10cm_gravity_drop"])

    def test_high_level_gpu_bundle_issuance_is_fail_closed(self):
        with self.assertRaises(GenerationRepairExecutionDisabled):
            assert_high_level_gpu_issuance_disabled_v2()


if __name__ == "__main__":
    unittest.main()
