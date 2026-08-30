import copy
import unittest

from controlled_multi_future.f2_release_gates_v10 import (
    FINAL_SETTLE_FRAMES,
    audit_f2_final_inside_success_gate_v10,
    audit_f2_release_safety_gate_v10,
)
from controlled_multi_future.f3_grasp_robustness_v10 import (
    PROGRAMS,
    audit_f3_grasp_robustness_diagnostic_v10,
    audit_f3_three_context_gate_v10,
    build_f3_common_grasp_contract_v10,
    validate_f3_common_grasp_contract_v10,
)
from controlled_multi_future.f3_physical_contact_signal_v8 import (
    CONTACT_PAIR_SCHEMA_VERSION,
    canonical_json_sha256,
)
from controlled_multi_future.f4_carry_corridor_v10 import (
    audit_f4_corridor_planner_results_v10,
    build_f4_fixed_order_corridors_v10,
    validate_f4_fixed_order_corridors_v10,
)


def shape_identity(name, index):
    value = {
        "available": True,
        "body_name": name,
        "body_collision_shape_index": index,
    }
    value["identity_sha256"] = canonical_json_sha256(value)
    return value


def physical_pair(first, second):
    identities = [shape_identity(first, 0), shape_identity(second, 0)]
    hashes = [item["identity_sha256"] for item in identities]
    return {
        "contact_pair_schema_version": CONTACT_PAIR_SCHEMA_VERSION,
        "body_a": first,
        "body_b": second,
        "point_count": 1,
        "impulse_norm_sum": 0.1,
        "impulse_available": True,
        "shape_identity_available": True,
        "shape_identities": identities,
        "point_evidence": [
            {
                "point_index": 0,
                "impulse_norm": 0.1,
                "impulse_available": True,
                "signed_separation_m": -0.001,
                "signed_separation_available": True,
                "shape_identity_available": True,
                "shape_identity_sha256": hashes,
            }
        ],
    }


def f2_rows(count, *, speed=0.0):
    return [
        {
            "actor_linear_velocity": [speed, 0.0, 0.0],
            "actor_angular_velocity": [0.0, 0.0, speed],
            "contact_pairs": [physical_pair("f2_main_can", "f2_plasticbox")],
            "contact_signal_complete": True,
        }
        for _ in range(count)
    ]


def f2_geometry(count):
    return [
        {
            "opening_center_inside": True,
            "opening_projection_overlaps": True,
            "opening_center_signed_margin_m": 0.02,
            "opening_projection_overlap_signed_m": 0.03,
            "geometry_evidence_complete": True,
        }
        for _ in range(count)
    ]


class F2ReleaseGatesV10Test(unittest.TestCase):
    def test_safety_gate_does_not_require_final_inside_or_final_stability(self):
        result = audit_f2_release_safety_gate_v10(
            f2_rows(50, speed=0.01),
            f2_geometry(50),
            can_actor_name="f2_main_can",
            selected_finger_link_names=("fl_link7", "fl_link8"),
            box_actor_name="f2_plasticbox",
        )
        self.assertTrue(result["pass"])
        self.assertTrue(result["full_open_allowed"])
        self.assertFalse(result["true_cavity_obb_evaluated"])
        self.assertFalse(result["final_angular_stability_evaluated"])

    def test_safety_gate_blocks_escape_contact_and_dangerous_motion(self):
        geometry = f2_geometry(50)
        geometry[-1]["opening_center_inside"] = False
        result = audit_f2_release_safety_gate_v10(
            f2_rows(50, speed=0.06),
            geometry,
            can_actor_name="f2_main_can",
            selected_finger_link_names=("fl_link7", "fl_link8"),
            box_actor_name="f2_plasticbox",
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["dynamics_non_dangerous"])
        self.assertFalse(result["checks"]["opening_center_inside_confirm_window"])

    def test_final_gate_requires_exact_250_and_unchanged_semantics(self):
        result = audit_f2_final_inside_success_gate_v10(
            f2_rows(FINAL_SETTLE_FRAMES),
            true_cavity_obb_pass=True,
            relation_predicates={"inside": True, "on": False, "beside": False},
            gripper_full_open=True,
            arm_rest_pass=True,
            can_actor_name="f2_main_can",
            box_actor_name="f2_plasticbox",
        )
        self.assertTrue(result["pass"])
        self.assertFalse(result["thresholds"]["verifier_thresholds_changed"])
        with self.assertRaisesRegex(ValueError, "exactly 250"):
            audit_f2_final_inside_success_gate_v10(
                f2_rows(FINAL_SETTLE_FRAMES - 1),
                true_cavity_obb_pass=True,
                relation_predicates={"inside": True, "on": False, "beside": False},
                gripper_full_open=True,
                arm_rest_pass=True,
                can_actor_name="f2_main_can",
                box_actor_name="f2_plasticbox",
            )


class F3GraspRobustnessV10Test(unittest.TestCase):
    def test_contract_is_one_midbody_grasp_without_fallback(self):
        contract = build_f3_common_grasp_contract_v10()
        self.assertEqual(validate_f3_common_grasp_contract_v10(contract), contract)
        self.assertEqual(contract["contact_point_id"], 0)
        self.assertEqual(contract["rotation_candidate_index"], 0)
        self.assertEqual(contract["post_close_settle_frames"], 250)
        self.assertTrue(contract["invariants"]["program_specific_grasp_forbidden"])
        tampered = copy.deepcopy(contract)
        tampered["contact_point_id"] = 3
        with self.assertRaises(ValueError):
            validate_f3_common_grasp_contract_v10(tampered)

    def diagnostic(self, program, *, drift=0.0):
        contract = build_f3_common_grasp_contract_v10()
        base = [0.1, 0.0, -0.1, 1.0, 0.0, 0.0, 0.0]
        moved = [0.1 + drift, 0.0, -0.1, 1.0, 0.0, 0.0, 0.0]
        return audit_f3_grasp_robustness_diagnostic_v10(
            program=program,
            grasp_contract=contract,
            canonical_prefix_action_sha256="a" * 64,
            expected_canonical_prefix_action_sha256="a" * 64,
            boundary_T_eef_actor={
                "post_close": base,
                "post_shared_V": moved,
                "post_first_suffix_event": moved,
            },
            selected_contact_fraction=1.0,
            selected_contact_break_count=0,
            shared_v_motion_pass=True,
            first_suffix_event_motion_pass=True,
            eef_tracking_pass=True,
            stopped_before_release=True,
        )

    def test_three_context_gate_is_3_of_3_and_preopen(self):
        receipts = [self.diagnostic(program) for program in PROGRAMS]
        result = audit_f3_three_context_gate_v10(receipts)
        self.assertTrue(result["pass"])
        self.assertTrue(result["full_root_allowed"])
        receipts[1] = self.diagnostic(PROGRAMS[1], drift=0.006)
        failed = audit_f3_three_context_gate_v10(receipts)
        self.assertFalse(failed["pass"])
        self.assertFalse(failed["full_root_allowed"])


def base_f4_targets():
    q = [1.0, 0.0, 0.0, 0.0]
    return [
        {"segment_id": "A_pregrasp", "pose": [0.16, 0.00, 0.98, *q]},
        {"segment_id": "A_grasp", "pose": [0.16, 0.01, 0.90, *q]},
        {"segment_id": "A_lift", "pose": [0.16, 0.01, 0.92, *q]},
        {"segment_id": "A_carry_mid", "pose": [0.155, 0.08, 1.00, *q]},
        {"segment_id": "A_preplace", "pose": [0.15, 0.15, 1.00, *q]},
        {"segment_id": "A_release", "pose": [0.15, 0.15, 0.90, *q]},
        {"segment_id": "A_neutral", "pose": [0.20, -0.12, 1.01, *q]},
    ]


def corridor_receipt(candidate_id, *, passed):
    return {
        "candidate_id": candidate_id,
        "fresh_scene": True,
        "cleanup_pass": True,
        "execution_attempt_count": 0,
        "segment_receipts": [
            {
                "endpoint_ik_pass": passed,
                "collision_pass": passed,
                "joint_margin_pass": passed,
                "chain_continuity_pass": passed,
            }
        ],
    }


class F4CarryCorridorV10Test(unittest.TestCase):
    def test_contract_has_exact_fixed_order_and_unchanged_release(self):
        contract = build_f4_fixed_order_corridors_v10(base_f4_targets())
        self.assertEqual(validate_f4_fixed_order_corridors_v10(contract), contract)
        self.assertEqual(
            [item["priority"] for item in contract["candidates"]], [1, 2, 3, 4]
        )
        self.assertFalse(contract["invariants"]["layout_changed"])
        self.assertFalse(contract["invariants"]["arm_changed"])

    def test_first_fixed_order_planner_pass_is_selected_without_execution(self):
        contract = build_f4_fixed_order_corridors_v10(base_f4_targets())
        ids = [item["candidate_id"] for item in contract["candidates"]]
        receipts = [
            corridor_receipt(ids[0], passed=False),
            corridor_receipt(ids[1], passed=True),
        ]
        result = audit_f4_corridor_planner_results_v10(contract, receipts)
        self.assertTrue(result["pass"])
        self.assertEqual(result["selected_candidate_id"], ids[1])
        self.assertTrue(result["A_execution_allowed"])
        self.assertFalse(result["layout_impact_review_required"])

    def test_four_planner_failures_stop_at_layout_review(self):
        contract = build_f4_fixed_order_corridors_v10(base_f4_targets())
        receipts = [
            corridor_receipt(item["candidate_id"], passed=False)
            for item in contract["candidates"]
        ]
        result = audit_f4_corridor_planner_results_v10(contract, receipts)
        self.assertFalse(result["pass"])
        self.assertFalse(result["A_execution_allowed"])
        self.assertTrue(result["layout_impact_review_required"])


if __name__ == "__main__":
    unittest.main()
