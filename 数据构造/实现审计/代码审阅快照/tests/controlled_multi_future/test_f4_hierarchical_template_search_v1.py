import copy
import unittest

from controlled_multi_future.f4_hierarchical_template_search_v1 import (
    MAXIMUM_SLOT_CORRIDOR_CANDIDATES,
    MAXIMUM_SOURCE_GRASP_CANDIDATES,
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
    select_f4_stage_a_source_v1,
    select_f4_stage_b_layout_v1,
    validate_f4_hierarchical_template_search_v1,
)


class F4HierarchicalTemplateSearchV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_f4_hierarchical_template_search_v1()

    def test_stage_a_has_eight_real_source_grasp_candidates_and_no_slots(self):
        candidates = self.contract["stage_a_candidates"]
        self.assertEqual(len(candidates), MAXIMUM_SOURCE_GRASP_CANDIDATES)
        self.assertEqual({item["arm"] for item in candidates}, {"left", "right"})
        self.assertEqual(
            len({tuple(item["A_pregrasp_xyz_m"]) for item in candidates}),
            MAXIMUM_SOURCE_GRASP_CANDIDATES,
        )
        self.assertTrue(all(item["A_pregrasp_differs_from_old_f4"] for item in candidates))
        self.assertTrue(all(item["slot_fields_present"] is False for item in candidates))
        self.assertTrue(
            all(item["minimum_pairwise_block_surface_clearance_m"] > 0 for item in candidates)
        )

    def test_f1_reference_and_scientific_semantics_are_frozen(self):
        reference = self.contract["f1_reference"]
        self.assertEqual(reference["accepted_root_count"], 5)
        self.assertEqual(reference["accepted_trajectory_count"], 15)
        self.assertEqual(reference["same_block_half_extents_m"], [0.022, 0.022, 0.022])
        self.assertEqual(
            self.contract["program_ids"], ["F4-ABC", "F4-ACB", "F4-BAC"]
        )
        self.assertTrue(self.contract["common_x_completed_first"])
        self.assertTrue(self.contract["equal_final_world_state_required"])
        self.assertFalse(self.contract["formal_data"])
        self.assertFalse(self.contract["stage1_authorized"])
        self.assertEqual(validate_f4_hierarchical_template_search_v1(self.contract), self.contract)

    def test_lowest_rank_full_stage_a_pass_is_selected(self):
        gates = self.contract["stage_a_required_gates"]
        receipts = []
        for candidate in reversed(self.contract["stage_a_candidates"]):
            passed = candidate["rank"] in {3, 6}
            receipts.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_sha256": candidate["candidate_sha256"],
                    "checks": {name: passed for name in gates},
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        terminal = select_f4_stage_a_source_v1(self.contract, receipts)
        self.assertEqual(terminal["selected_source_grasp"]["rank"], 3)
        self.assertTrue(terminal["stage_b_authorized_by_result"])

    def test_stage_b_is_impossible_before_stage_a_pass_and_bounded_after_pass(self):
        with self.assertRaises(ValueError):
            build_f4_stage_b_candidates_v1(
                self.contract,
                {"selected_source_grasp": None, "stage_b_authorized_by_result": False},
            )
        gates = self.contract["stage_a_required_gates"]
        receipts = []
        for candidate in self.contract["stage_a_candidates"]:
            passed = candidate["rank"] == 1
            receipts.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_sha256": candidate["candidate_sha256"],
                    "checks": {name: passed for name in gates},
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        terminal = select_f4_stage_a_source_v1(self.contract, receipts)
        stage_b = build_f4_stage_b_candidates_v1(self.contract, terminal)
        self.assertEqual(len(stage_b["candidates"]), MAXIMUM_SLOT_CORRIDOR_CANDIDATES)
        self.assertTrue(
            all(
                item["source_grasp_candidate_sha256"]
                == terminal["selected_source_grasp"]["candidate_sha256"]
                for item in stage_b["candidates"]
            )
        )
        stage_b_receipts = []
        for candidate in reversed(stage_b["candidates"]):
            passed = candidate["rank"] in {2, 5}
            stage_b_receipts.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_sha256": candidate["candidate_sha256"],
                    "checks": {
                        name: passed
                        for name in self.contract["stage_b_required_gates"]
                    },
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        selected = select_f4_stage_b_layout_v1(
            self.contract, terminal, stage_b_receipts
        )
        self.assertEqual(selected["selected_slot_corridor"]["rank"], 2)
        self.assertTrue(selected["single_role_physical_authorized_by_result"])

    def test_contract_tamper_fails_closed(self):
        changed = copy.deepcopy(self.contract)
        changed["maximum_stage_a_candidates"] = 9
        with self.assertRaises(ValueError):
            validate_f4_hierarchical_template_search_v1(changed)


if __name__ == "__main__":
    unittest.main()
