import copy
import unittest

from controlled_multi_future.f4_layout_candidate_search_v2 import (
    MAXIMUM_CANDIDATE_COUNT,
    build_f4_layout_candidate_search_v2,
    build_single_selected_layout_dispatch_v2,
    finalize_single_selected_layout_dispatch_v2,
    preregistered_f4_layout_candidates_v2,
    validate_f4_layout_candidate_search_v2,
)


class F4LayoutCandidateSearchV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.search = build_f4_layout_candidate_search_v2()

    def test_fixed_bounded_order_and_hash_are_reproducible(self):
        first = preregistered_f4_layout_candidates_v2()
        second = preregistered_f4_layout_candidates_v2()
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)
        self.assertLessEqual(len(first), MAXIMUM_CANDIDATE_COUNT)
        self.assertEqual(
            [item["candidate_index"] for item in first],
            list(range(1, len(first) + 1)),
        )
        self.assertEqual(
            self.search["fixed_candidate_order"],
            [item["candidate_id"] for item in first],
        )
        self.assertEqual(validate_f4_layout_candidate_search_v2(self.search), self.search)

    def test_cpu_pass_is_explicitly_not_selection_or_gpu_ready(self):
        self.assertIsNotNone(self.search["first_cpu_admissible_candidate_id"])
        self.assertFalse(self.search["selection_complete"])
        self.assertFalse(self.search["gpu_ready"])
        self.assertTrue(self.search["true_endpoint_ik_pending"])
        self.assertTrue(self.search["complete_three_program_planner_only_pending"])
        self.assertTrue(self.search["rendered_segmentation_visibility_pending"])
        self.assertTrue(self.search["cpu_pass_must_not_be_reported_as_layout_selected"])

    def test_allowed_diff_invariants_and_cpu_gates(self):
        passing = [item for item in self.search["cpu_audits"] if item["cpu_pass"]]
        self.assertTrue(passing)
        for audit in passing:
            self.assertTrue(audit["invariant_checks"]["allowed_layout_diff_only"])
            self.assertTrue(audit["invariant_checks"]["common_x_unchanged"])
            self.assertTrue(audit["invariant_checks"]["tray_unchanged"])
            self.assertTrue(audit["geometry"]["pass"])
            self.assertTrue(audit["camera_frustum"]["pass"])
            self.assertTrue(audit["camera_frustum"]["necessary_condition_only"])
            self.assertFalse(audit["camera_frustum"]["occlusion_checked"])
            self.assertTrue(audit["target_and_sequence"]["pass"])
            self.assertTrue(
                audit["target_and_sequence"]["checks"]
                ["only_preplace_quaternion_changed"]
            )

    def test_exact_seven_segments_and_no_temporary_waypoint(self):
        for candidate, audit in zip(self.search["candidates"], self.search["cpu_audits"]):
            self.assertEqual(candidate["added_waypoints"], [])
            self.assertFalse(candidate["temporary_waypoint_allowed"])
            ids = audit["target_and_sequence"]["target_segment_ids"]
            for role in ("A", "B", "C"):
                self.assertEqual(
                    ids[role],
                    [
                        f"{role}_pregrasp",
                        f"{role}_grasp",
                        f"{role}_lift",
                        f"{role}_carry_mid",
                        f"{role}_preplace",
                        f"{role}_release",
                        f"{role}_neutral",
                    ],
                )

    def test_contract_tamper_is_rejected(self):
        changed = copy.deepcopy(self.search)
        changed["gpu_ready"] = True
        with self.assertRaises(ValueError):
            validate_f4_layout_candidate_search_v2(changed)
        changed = copy.deepcopy(self.search)
        changed["fixed_candidate_order"].reverse()
        with self.assertRaises(ValueError):
            validate_f4_layout_candidate_search_v2(changed)

    def test_single_dispatch_and_failure_never_falls_back(self):
        dispatch = build_single_selected_layout_dispatch_v2(self.search)
        self.assertFalse(dispatch["gpu_ready"])
        self.assertEqual(dispatch["maximum_layout_dispatch_count"], 1)
        self.assertFalse(dispatch["automatic_fallback"])
        failed = finalize_single_selected_layout_dispatch_v2(
            dispatch,
            attempted_candidate_id=dispatch["dispatch_candidate_id"],
            complete_planner_only_pass=False,
            rendered_segmentation_visibility_pass=True,
        )
        self.assertFalse(failed["pass"])
        self.assertFalse(failed["later_candidate_attempt_allowed"])
        self.assertEqual(
            failed["next_state"], "higher_level_task_layout_redesign_required"
        )
        later = next(
            item
            for item in self.search["fixed_candidate_order"]
            if item != dispatch["dispatch_candidate_id"]
        )
        with self.assertRaises(ValueError):
            finalize_single_selected_layout_dispatch_v2(
                dispatch,
                attempted_candidate_id=later,
                complete_planner_only_pass=True,
                rendered_segmentation_visibility_pass=True,
            )


if __name__ == "__main__":
    unittest.main()
