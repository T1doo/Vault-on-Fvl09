import copy
import unittest

from controlled_multi_future.f4_template_qualification_v1 import (
    PROGRAM_IDS,
    REQUIRED_ROLE_SEGMENT_SUFFIXES,
    ROLES,
    build_f4_template_candidate_spec_v1,
    build_f4_template_qualification_v1,
    select_f4_template_v1,
    summarize_f4_template_candidate_result_v1,
    validate_f4_template_candidate_spec_v1,
    validate_f4_template_qualification_v1,
)


def passing_planner_result():
    programs = []
    for program_id in PROGRAM_IDS:
        segments = []
        for role in ROLES:
            for suffix in REQUIRED_ROLE_SEGMENT_SUFFIXES:
                segments.append(
                    {
                        "segment_id": f"{role}_{suffix}",
                        "planner_status": "Success",
                        "joint_limit_evidence_complete": True,
                        "terminal_qpos_within_joint_limits": True,
                    }
                )
        programs.append(
            {
                "program_id": program_id,
                "segment_chain_audit": {"pass": True},
                "planner_receipt": {
                    "evidence": {
                        "segment_receipts": segments,
                        "block_carry_route_audit": {"pass": True},
                    }
                },
            }
        )
    return {
        "rendered_visibility_receipts": [{"pass": True} for _ in range(4)],
        "canonical_prefix_reference_execution_count": 1,
        "program_receipts": programs,
        "suffix_execution_attempt_count": 0,
        "release_execution_count": 0,
        "cleanup_records": [
            {"cleanup_safety_pass": True, "orphan_process_count": 0}
            for _ in range(4)
        ],
    }


class F4TemplateQualificationV1Tests(unittest.TestCase):
    def setUp(self):
        self.qualification = build_f4_template_qualification_v1()

    def test_all_candidates_frozen_before_gpu_and_no_semantic_escape_hatches(self):
        self.assertEqual(
            validate_f4_template_qualification_v1(self.qualification),
            self.qualification,
        )
        self.assertGreater(self.qualification["candidate_count"], 0)
        self.assertLessEqual(self.qualification["candidate_count"], 12)
        for key in (
            "temporary_waypoint_allowed",
            "online_slot_move_allowed",
            "program_specific_orientation_allowed",
            "different_layout_per_program_allowed",
            "verifier_threshold_change_allowed",
        ):
            self.assertFalse(self.qualification[key])

    def test_candidate_spec_exactly_binds_one_frozen_layout(self):
        candidate_id = self.qualification["fixed_candidate_order"][1]
        spec = build_f4_template_candidate_spec_v1(candidate_id)
        self.assertEqual(validate_f4_template_candidate_spec_v1(spec), spec)
        changed = copy.deepcopy(spec)
        changed["scene_layout"]["slot_poses"]["A"][0] += 0.001
        with self.assertRaises(ValueError):
            validate_f4_template_candidate_spec_v1(changed)

    def test_candidate_summary_requires_full_visibility_ik_chains_and_cleanup(self):
        spec = build_f4_template_candidate_spec_v1(
            self.qualification["fixed_candidate_order"][0]
        )
        terminal = summarize_f4_template_candidate_result_v1(
            candidate_spec=spec, planner_result=passing_planner_result()
        )
        self.assertTrue(terminal["pass"])
        self.assertTrue(terminal["checks"]["all_role_endpoint_sets"])
        failed = passing_planner_result()
        failed["program_receipts"][1]["planner_receipt"]["evidence"][
            "segment_receipts"
        ][4]["planner_status"] = "IK_FAIL"
        terminal = summarize_f4_template_candidate_result_v1(
            candidate_spec=spec, planner_result=failed
        )
        self.assertFalse(terminal["pass"])

    def test_lowest_rank_pass_selected_independent_of_completion_order(self):
        receipts = []
        for candidate in reversed(self.qualification["candidates"]):
            receipts.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "candidate_sha256": candidate["candidate_sha256"],
                    "pass": candidate["candidate_index"] in {2, 5},
                }
            )
        terminal = select_f4_template_v1(receipts)
        self.assertEqual(terminal["selected_template"]["candidate_index"], 2)

    def test_all_candidates_required_for_terminal_selection(self):
        with self.assertRaises(ValueError):
            select_f4_template_v1([])


if __name__ == "__main__":
    unittest.main()
