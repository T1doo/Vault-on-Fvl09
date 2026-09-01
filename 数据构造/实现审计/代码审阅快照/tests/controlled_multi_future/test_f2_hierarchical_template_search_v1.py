import copy
import unittest

from controlled_multi_future.f2_hierarchical_template_search_v1 import (
    MAXIMUM_INSIDE_CANDIDATES,
    MAXIMUM_REAL_INSIDE_EXECUTIONS,
    MAXIMUM_STAGE_B_LAYOUT_CANDIDATES,
    build_f2_hierarchical_template_search_v1,
    select_first_inside_success_v1,
    select_inside_physical_candidates_v1,
    validate_f2_hierarchical_template_search_v1,
)


class F2HierarchicalTemplateSearchV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_f2_hierarchical_template_search_v1()

    def test_matrix_is_collapsed_by_can_box_pair_before_ranking(self):
        self.assertEqual(self.contract["source_row_count"], 1650)
        self.assertEqual(self.contract["distinct_can_box_pair_count"], 66)
        self.assertEqual(self.contract["cpu_admissible_distinct_pair_count"], 44)
        self.assertTrue(
            all(
                item["scale_or_stand_used_for_stage_a_rank"] is False
                for item in self.contract["collapsed_pairs"]
            )
        )

    def test_twelve_candidates_cover_assets_and_both_arms(self):
        candidates = self.contract["inside_candidates"]
        self.assertEqual(len(candidates), MAXIMUM_INSIDE_CANDIDATES)
        self.assertEqual({item["arm"] for item in candidates}, {"left", "right"})
        self.assertGreaterEqual(len({item["main_object_model_id"] for item in candidates}), 2)
        self.assertGreaterEqual(len({item["plastic_box_model_id"] for item in candidates}), 2)
        keys = {
            (
                item["main_object_model_id"],
                item["plastic_box_model_id"],
                item["arm"],
            )
            for item in candidates
        }
        self.assertEqual(len(keys), MAXIMUM_INSIDE_CANDIDATES)
        self.assertTrue(all(item["electronic_scale_model_id"] is None for item in candidates))
        self.assertTrue(all(item["beside_reference_model_id"] is None for item in candidates))

    def test_hierarchy_and_authorization_boundaries_are_frozen(self):
        self.assertEqual(
            validate_f2_hierarchical_template_search_v1(self.contract), self.contract
        )
        self.assertEqual(
            self.contract["maximum_stage_b_layout_candidates"],
            MAXIMUM_STAGE_B_LAYOUT_CANDIDATES,
        )
        self.assertTrue(self.contract["stage_b_allowed_only_after_inside_success"])
        self.assertFalse(self.contract["formal_data"])
        self.assertFalse(self.contract["stage0_data"])
        self.assertFalse(self.contract["stage1_authorized"])

    def test_first_three_planner_passes_only_are_physically_eligible(self):
        receipts = [
            {
                "candidate_id": item["candidate_id"],
                "candidate_sha256": item["candidate_sha256"],
                "planner_success": item["rank"] in {2, 3, 5, 7, 9},
            }
            for item in reversed(self.contract["inside_candidates"])
        ]
        terminal = select_inside_physical_candidates_v1(self.contract, receipts)
        self.assertEqual(
            terminal["physical_candidate_ids"],
            [
                "f2-inside-hv1-r02",
                "f2-inside-hv1-r03",
                "f2-inside-hv1-r05",
            ],
        )
        self.assertEqual(
            terminal["maximum_real_inside_executions"], MAXIMUM_REAL_INSIDE_EXECUTIONS
        )

    def test_first_physical_inside_pass_freezes_and_opens_stage_b(self):
        planner = select_inside_physical_candidates_v1(
            self.contract,
            [
                {
                    "candidate_id": item["candidate_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "planner_success": item["rank"] <= 3,
                }
                for item in self.contract["inside_candidates"]
            ],
        )
        by_id = {item["candidate_id"]: item for item in self.contract["inside_candidates"]}
        physical = []
        for candidate_id in reversed(planner["physical_candidate_ids"]):
            item = by_id[candidate_id]
            physical.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_sha256": item["candidate_sha256"],
                    "strict_inside_verifier_pass": item["rank"] in {2, 3},
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        terminal = select_first_inside_success_v1(self.contract, planner, physical)
        self.assertEqual(terminal["frozen_inside_candidate"]["rank"], 2)
        self.assertTrue(terminal["stage_b_authorized_by_result"])

        changed = copy.deepcopy(self.contract)
        changed["maximum_real_inside_executions"] = 4
        with self.assertRaises(ValueError):
            validate_f2_hierarchical_template_search_v1(changed)


if __name__ == "__main__":
    unittest.main()
