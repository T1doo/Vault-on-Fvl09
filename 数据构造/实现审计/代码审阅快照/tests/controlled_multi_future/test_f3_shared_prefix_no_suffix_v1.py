import unittest

from controlled_multi_future.f3_contact_preserving_prefix_v11 import (
    CLOSE_NORMALIZED_TARGET,
    PROGRAM_IDS,
    build_f3_contact_preserving_prefix_contract_v11,
    validate_f3_contact_preserving_prefix_contract_v11,
)
from controlled_multi_future.f3_shared_prefix_no_suffix_diagnostic_v1 import (
    finalize_f3_shared_prefix_no_suffix_diagnostic_v1,
)
from controlled_multi_future.family_runners_v3_3 import F3ControllerV3_3


class F3SharedPrefixNoSuffixV1Tests(unittest.TestCase):
    def test_contract_is_exact_and_program_independent(self):
        value = build_f3_contact_preserving_prefix_contract_v11()
        self.assertEqual(
            validate_f3_contact_preserving_prefix_contract_v11(value), value
        )
        self.assertEqual(value["program_ids"], list(PROGRAM_IDS))
        self.assertEqual(value["close_normalized_target"], 0.35)
        self.assertTrue(value["invariants"]["same_repair_all_programs"])

    def test_controller_default_remains_stage0_close_zero(self):
        controller = F3ControllerV3_3()
        contract = controller.canonical_prefix_contract([])
        self.assertNotIn("shared_prefix_repair_v11", contract)
        self.assertNotIn("close_normalized_target", contract)
        self.assertEqual(contract["ops"][2], "close")

    def test_controller_repair_contract_is_additive(self):
        controller = F3ControllerV3_3()
        repair = build_f3_contact_preserving_prefix_contract_v11()
        controller.f3_shared_prefix_repair_v11 = repair
        contract = controller.canonical_prefix_contract([])
        self.assertEqual(contract["shared_prefix_repair_v11"], repair)
        self.assertEqual(contract["close_normalized_target"], CLOSE_NORMALIZED_TARGET)
        self.assertTrue(contract["diagnostic_no_suffix"])

    def test_finalizer_requires_exact_three_and_zero_suffix(self):
        contexts = []
        cleanups = []
        for index, program_id in enumerate(PROGRAM_IDS):
            contexts.append(
                {
                    "program_id": program_id,
                    "execution_mode": "reference_generation"
                    if index == 0
                    else "exact_replay",
                    "pass": True,
                    "scene_instance_id": f"scene-{index}",
                    "executed_prefix_action_sha256": "a" * 64,
                    "suffix_planner_query_count": 0,
                    "suffix_executed": False,
                    "release_executed": False,
                    "diagnostic_nonroot": True,
                }
            )
            cleanups.append(
                {
                    "scene_instance_id": f"scene-{index}",
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        result = finalize_f3_shared_prefix_no_suffix_diagnostic_v1(
            contexts, cleanup_records=cleanups
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["accepted_root_increment"], 0)
        contexts[1]["suffix_planner_query_count"] = 1
        self.assertFalse(
            finalize_f3_shared_prefix_no_suffix_diagnostic_v1(
                contexts, cleanup_records=cleanups
            )["pass"]
        )


if __name__ == "__main__":
    unittest.main()
