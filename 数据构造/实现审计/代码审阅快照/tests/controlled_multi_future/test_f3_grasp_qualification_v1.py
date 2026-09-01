import copy
import unittest

from controlled_multi_future.f3_grasp_qualification_v1 import (
    MAXIMUM_CANDIDATE_COUNT,
    MAXIMUM_PHYSICAL_CANDIDATE_COUNT,
    REQUIRED_PHYSICAL_GATES,
    build_f3_grasp_qualification_v1,
    build_f3_grasp_candidate_spec_v1,
    build_f3_selected_grasp_contract_v1,
    preregistered_f3_grasp_candidates_v1,
    select_f3_physical_candidates_v1,
    select_stable_f3_grasp_v1,
    validate_f3_grasp_candidate_spec_v1,
    validate_f3_grasp_qualification_v1,
)
from controlled_multi_future.family_runners_v3_3 import F3ControllerV3_3


class F3GraspQualificationV1Tests(unittest.TestCase):
    def setUp(self):
        self.contract = build_f3_grasp_qualification_v1()
        self.candidates = preregistered_f3_grasp_candidates_v1()

    def test_exact_bounded_ranked_candidate_set(self):
        self.assertEqual(len(self.candidates), MAXIMUM_CANDIDATE_COUNT)
        self.assertEqual(
            [item["rank"] for item in self.candidates],
            list(range(1, MAXIMUM_CANDIDATE_COUNT + 1)),
        )
        self.assertEqual(validate_f3_grasp_qualification_v1(self.contract), self.contract)
        self.assertEqual(self.contract["program_ids"], ["F3-VVHH", "F3-VHVH", "F3-VHHV"])

    def test_no_close_sweep_and_scientific_semantics_frozen(self):
        self.assertEqual({item["close_normalized_target"] for item in self.candidates}, {0.5})
        self.assertTrue(all(item["program_independent"] for item in self.candidates))
        self.assertTrue(all(item["vh_axes_changed"] is False for item in self.candidates))
        self.assertTrue(all(item["programs_changed"] is False for item in self.candidates))

    def test_planner_screen_selects_first_four_by_rank_not_completion_order(self):
        receipts = [
            {
                "candidate_id": item["candidate_id"],
                "candidate_sha256": item["candidate_sha256"],
                "planner_success": item["rank"] in {2, 3, 5, 7, 8},
            }
            for item in reversed(self.candidates)
        ]
        terminal = select_f3_physical_candidates_v1(receipts)
        self.assertEqual(
            terminal["physical_candidate_ids"],
            [
                "f3-grasp-qv1-r02",
                "f3-grasp-qv1-r03",
                "f3-grasp-qv1-r05",
                "f3-grasp-qv1-r07",
            ],
        )
        self.assertLessEqual(
            len(terminal["physical_candidate_ids"]), MAXIMUM_PHYSICAL_CANDIDATE_COUNT
        )

    def test_lowest_rank_full_physical_pass_selected(self):
        planner = select_f3_physical_candidates_v1(
            [
                {
                    "candidate_id": item["candidate_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "planner_success": item["rank"] <= 4,
                }
                for item in self.candidates
            ]
        )
        receipts = []
        for candidate_id in reversed(planner["physical_candidate_ids"]):
            candidate = next(item for item in self.candidates if item["candidate_id"] == candidate_id)
            gates = {name: candidate["rank"] in {2, 4} for name in REQUIRED_PHYSICAL_GATES}
            receipts.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_sha256": candidate["candidate_sha256"],
                    "gates": gates,
                    "qualification_sequence_complete": True,
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        terminal = select_stable_f3_grasp_v1(planner, receipts)
        self.assertEqual(terminal["stable_candidate"]["rank"], 2)
        selected = build_f3_selected_grasp_contract_v1(terminal["stable_candidate"])
        self.assertTrue(selected["same_contract_all_programs"])

    def test_tamper_or_partial_coverage_fails_closed(self):
        changed = copy.deepcopy(self.contract)
        changed["maximum_physical_candidate_count"] = 5
        with self.assertRaises(ValueError):
            validate_f3_grasp_qualification_v1(changed)
        with self.assertRaises(ValueError):
            select_f3_physical_candidates_v1([])

    def test_controller_binds_selected_grasp_without_changing_vh_programs(self):
        controller = F3ControllerV3_3()
        selected = build_f3_selected_grasp_contract_v1(self.candidates[2])
        controller.f3_selected_stable_grasp_contract_v1 = selected
        prefix = controller.canonical_prefix_contract([])
        self.assertEqual(prefix["f3_selected_stable_grasp_contract_v1"], selected)
        self.assertEqual(prefix["shared_v_nominal_amplitude_m"], 0.055)
        self.assertEqual(prefix["close_normalized_target"], 0.5)
        self.assertNotIn("diagnostic_no_suffix", prefix)

    def test_candidate_specs_separate_prefix_qualification_from_full_root(self):
        candidate_id = self.candidates[0]["candidate_id"]
        physical = build_f3_grasp_candidate_spec_v1(candidate_id, purpose="physical")
        root = build_f3_grasp_candidate_spec_v1(candidate_id, purpose="full_root")
        self.assertEqual(validate_f3_grasp_candidate_spec_v1(physical), physical)
        self.assertEqual(validate_f3_grasp_candidate_spec_v1(root), root)
        self.assertTrue(physical["prefix_only"])
        self.assertFalse(physical["suffix_allowed"])
        self.assertFalse(root["prefix_only"])
        self.assertTrue(root["suffix_allowed"])


if __name__ == "__main__":
    unittest.main()
