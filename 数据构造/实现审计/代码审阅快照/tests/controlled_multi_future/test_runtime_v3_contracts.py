import unittest

from controlled_multi_future.runtime_v3_contracts import (
    DESIGN_VERSION,
    F1_COMMON_PREFIX,
    F1_TARGET_ORDER,
    F2_POSE_CANDIDATES,
    F3_RELEASE_SAMPLE_POINTS,
    F3_INITIAL_ANCHOR_REQUIREMENTS,
    F3_VERIFIER_INVARIANTS,
    F4_ROUTE_ORDER,
    GPU_PROBE_AUTHORIZED,
    IMPLEMENTATION_VERSION,
    RAW_LAYOUT_VERSION,
    RUNTIME_V3_BUDGET_PROPOSAL,
    STAGE0_AUTHORIZED,
    adjudicate_f4_routes,
    classify_f3_release_dynamics,
    f1_branch_spec,
    f4_route_specs,
    minimum_f4_safe_actor_center_height,
    select_first_f2_verified_candidate,
    validate_f1_three_branch_coverage,
)


def f2_result(candidate, *, verified=False):
    return {
        **candidate,
        "main_object": "071_can/base1",
        "arm": "left",
        "reference": "074_displaystand/base3",
        "planner_seed": 20260828,
        "planner_start_state_sha256": "same-start",
        "upright_axis_audited": verified,
        "release_planner_status": "Success" if verified else "Fail",
        "preplace_planner_status": "Success" if verified else "Fail",
        "joint_limit_margin_pass": verified,
        "carried_swept_geometry_pass": verified,
        "facility_distance_pass": verified,
    }


def f3_samples(*, before_position=0.0, later_position=0.0):
    values = {}
    for index, name in enumerate(F3_RELEASE_SAMPLE_POINTS):
        values[name] = {
            "bottle_position_error_m": before_position if index == 0 else later_position,
            "bottle_orientation_error": 0.0,
            "eef_tracking_error_m": 0.0,
            "bottle_linear_speed_mps": max(0.0, 0.02 - index * 0.002),
            "bottle_angular_speed_rps": 0.0,
            "bottle_footprint_inside_pad": True,
            "bottle_pad_contact_count": 1,
            "bottle_pad_contact_normal": [0, 0, 1],
            "bottle_pad_contact_impulse": 0.1,
            "selected_gripper_contact": index == 0,
            "actual_gripper_joint_qpos": [0.0, 0.0],
        }
    return values


class RuntimeV3ContractsTest(unittest.TestCase):
    def test_runtime_v3_keeps_science_and_execution_closed(self):
        self.assertEqual(DESIGN_VERSION, "controlled_multi_future_f1_f4_v1_2")
        self.assertEqual(IMPLEMENTATION_VERSION, "controlled_multi_future_runtime_v3")
        self.assertEqual(RAW_LAYOUT_VERSION, "controller_effective_setpoint_v1_layout_v2_1")
        self.assertFalse(GPU_PROBE_AUTHORIZED)
        self.assertFalse(STAGE0_AUTHORIZED)

    def test_f1_all_roles_are_parameterized_with_shared_prefix(self):
        specs = [f1_branch_spec(role) for role in F1_TARGET_ORDER]
        self.assertEqual([item["target_role"] for item in specs], ["red", "green", "blue"])
        self.assertEqual([item["non_target_roles"] for item in specs], [["green", "blue"], ["red", "blue"], ["red", "green"]])
        self.assertTrue(all(item["canonical_prefix_id"] == F1_COMMON_PREFIX["prefix_id"] for item in specs))
        self.assertFalse(F1_COMMON_PREFIX["target_role_visible"])

    def test_f1_coverage_requires_three_of_three_same_root_hashes(self):
        receipts = [
            {"target_role": role, "scene_spec_sha256": "scene", "reference_current_sha256": "current", "canonical_prefix_sha256": "prefix", "semantic_probe_pass": True}
            for role in F1_TARGET_ORDER
        ]
        self.assertTrue(validate_f1_three_branch_coverage(receipts)["pass"])
        receipts[1]["semantic_probe_pass"] = False
        self.assertFalse(validate_f1_three_branch_coverage(receipts)["pass"])
        receipts[1]["scene_spec_sha256"] = "different"
        with self.assertRaises(ValueError):
            validate_f1_three_branch_coverage(receipts)

    def test_f2_six_candidates_are_fixed_and_first_success_wins(self):
        self.assertEqual(len(F2_POSE_CANDIDATES), 6)
        results = [f2_result(item, verified=index in (2, 4)) for index, item in enumerate(F2_POSE_CANDIDATES)]
        decision = select_first_f2_verified_candidate(results)
        self.assertEqual(decision["selected"]["candidate_id"], F2_POSE_CANDIDATES[2]["candidate_id"])
        results[0]["arm"] = "right"
        with self.assertRaises(ValueError):
            select_first_f2_verified_candidate(results)

    def test_f2_candidates_require_fair_planner_seed_and_start_state(self):
        results = [f2_result(item, verified=False) for item in F2_POSE_CANDIDATES]
        results[-1]["planner_seed"] = 7
        with self.assertRaises(ValueError):
            select_first_f2_verified_candidate(results)
        results[-1]["planner_seed"] = 20260828
        results[-1]["planner_start_state_sha256"] = "different"
        with self.assertRaises(ValueError):
            select_first_f2_verified_candidate(results)

    def test_f2_exhaustion_enters_layout_review(self):
        results = [f2_result(item, verified=False) for item in F2_POSE_CANDIDATES]
        decision = select_first_f2_verified_candidate(results)
        self.assertFalse(decision["pass"])
        self.assertEqual(decision["terminal_if_exhausted"], "f2_stand_layout_impact_review_v5")

    def test_f3_diagnosis_separates_pre_release_and_post_release(self):
        pre = classify_f3_release_dynamics(
            f3_samples(before_position=0.04, later_position=0.04),
            pre_release_position_tolerance_m=0.03,
            pre_release_orientation_tolerance=0.02,
        )
        self.assertEqual(pre["classification"], "pre_release_offset")
        self.assertTrue(pre["actor_to_eef_correction_allowed"])
        post = classify_f3_release_dynamics(
            f3_samples(before_position=0.0, later_position=0.04),
            pre_release_position_tolerance_m=0.03,
            pre_release_orientation_tolerance=0.02,
        )
        self.assertEqual(post["classification"], "post_release_dynamics")
        self.assertFalse(post["actor_to_eef_correction_allowed"])
        self.assertTrue(F3_INITIAL_ANCHOR_REQUIREMENTS["stable_window_required_before_anchor"])
        self.assertEqual(F3_VERIFIER_INVARIANTS["position_threshold"], "inherit_runtime_v2_without_relaxation")

    def test_f4_safe_height_and_route_order_are_fixed(self):
        height = minimum_f4_safe_actor_center_height([0.80, 0.82, 0.79], 0.022, 0.03)
        self.assertAlmostEqual(height, 0.872)
        routes = f4_route_specs(height)
        self.assertEqual([item["route_id"] for item in routes], list(F4_ROUTE_ORDER))
        self.assertTrue(all(item["changes_tray_pose"] is False for item in routes))
        decision = adjudicate_f4_routes([
            {"route_id": routes[0]["route_id"], "semantic_probe_pass": False, "terminal_status": "failed_planner", "changes_tray_pose": False, "all_segment_endpoint_preflight_pass": False},
            {"route_id": routes[1]["route_id"], "semantic_probe_pass": False, "terminal_status": "failed_planner", "changes_tray_pose": False, "all_segment_endpoint_preflight_pass": False},
        ])
        self.assertEqual(decision["terminal_if_exhausted"], "f4_tray_layout_impact_review_v4")

    def test_runtime_v3_budget_is_proposal_only(self):
        self.assertEqual(RUNTIME_V3_BUDGET_PROPOSAL["status"], "proposed_for_user_review")
        self.assertFalse(RUNTIME_V3_BUDGET_PROPOSAL["approved"])
        self.assertFalse(RUNTIME_V3_BUDGET_PROPOSAL["frozen"])
        self.assertEqual(RUNTIME_V3_BUDGET_PROPOSAL["F1"]["execution_limit"], 3)
        self.assertEqual(RUNTIME_V3_BUDGET_PROPOSAL["F2"]["pose_candidate_limit"], 6)
        self.assertEqual(RUNTIME_V3_BUDGET_PROPOSAL["F4"]["route_limit"], 2)


if __name__ == "__main__":
    unittest.main()
