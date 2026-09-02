import unittest

from controlled_multi_future.generation_repair_v2_2 import (
    build_generation_repair_v2_2_contract,
)


class GenerationRepairV22Tests(unittest.TestCase):
    def test_all_v2_2_repairs_are_machine_bound(self):
        contract = build_generation_repair_v2_2_contract()
        self.assertEqual(contract["f2"]["planner_query_minimum"], 8)
        self.assertTrue(
            contract["f2"]["forbidden_external_geometry_parameters_absent"]
        )
        self.assertFalse(contract["f3"]["stage_a_alone_candidate_ready"])
        self.assertTrue(contract["f3"]["both_stages_required"])
        self.assertEqual(
            set(contract["f4"]["program_orders"]),
            {"F4-ABC", "F4-ACB", "F4-BAC"},
        )
        self.assertTrue(contract["f4"]["abc_only_candidate_qualification_forbidden"])

    def test_execution_and_later_scopes_remain_closed(self):
        contract = build_generation_repair_v2_2_contract()
        self.assertTrue(
            all(value is False for value in contract["authorization"].values())
        )
        self.assertFalse(contract["dispatch"]["legacy_high_level_dispatch_activated"])
        self.assertFalse(contract["dispatch"]["v2_2_planner_issuer_implemented"])
        self.assertFalse(contract["stage0_reopened_or_rerun"])
        self.assertEqual(contract["new_trajectory_count"], 0)


if __name__ == "__main__":
    unittest.main()
