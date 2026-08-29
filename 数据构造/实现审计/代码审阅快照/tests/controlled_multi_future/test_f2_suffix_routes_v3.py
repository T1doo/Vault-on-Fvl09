import copy
import json
import unittest

import numpy as np

from controlled_multi_future.f2_suffix_routes_v3 import (
    BESIDE_CANDIDATES,
    BESIDE_EXHAUSTION_TERMINAL,
    BESIDE_PLANNER_SEED,
    BESIDE_SEGMENT_IDS,
    INSIDE_SAMPLE_STEPS,
    INSIDE_SEGMENT_IDS,
    audit_beside_candidate_receipts,
    audit_beside_route,
    audit_f2_held_transport_contacts,
    audit_inside_gravity_drop_route,
    beside_candidate_registry,
    build_beside_route,
    build_inside_gravity_drop_route,
    proposed_static_planner_envelope,
)
from controlled_multi_future.f2_mutually_exclusive_region_layout_v2 import LAYOUT
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.runtime_v3_contracts import F2_POSE_CANDIDATES
from controlled_multi_future.geometry import compose_pose, obb_inside_local_cavity
from controlled_multi_future.runtime_v3_2_contracts import (
    F2_INSIDE_LOCAL_QUATERNION_WXYZ,
    F2_PLASTICBOX_BASE2_CAVITY,
)


BOX_POSE = [-0.29, -0.20, 0.78, 0.5, 0.5, 0.5, 0.5]
STAND_POSE = [*LAYOUT["stand_xyz"], *LAYOUT["stand_q_wxyz"]]
CURRENT_ACTOR_POSE = [
    -0.2819347381591797,
    0.041474662721157074,
    0.8612411022186279,
    0.4992869794368744,
    0.5009192228317261,
    0.4996301531791687,
    0.5001623034477234,
]
CURRENT_EEF_POSE = [
    -0.2813752456398892,
    -0.1498255471076506,
    1.0527331238067062,
    0.6526103138032237,
    -0.270863903349079,
    0.653376905212569,
    0.27171886926565203,
]
REST_EEF_POSE = [
    -0.297923743724823,
    -0.31380218267440796,
    0.9419903755187988,
    0.7000005275036494,
    -1.61680875200991e-05,
    6.60717435563285e-06,
    0.7141423255833185,
]
CAN_HALF_EXTENTS = [
    0.06508397222247786 / 2.0,
    0.09657016642050303 / 2.0,
    0.06527871934324424 / 2.0,
]
CAN_LOCAL_GEOMETRY_CENTER = [
    -8.985256604840808e-05 * 0.05,
    0.9513497755527056 * 0.05,
    -0.0011933646434538318 * 0.05,
]


def candidate_receipt(candidate_id, *, fail_at=None):
    segments = []
    previous = "same-prefix-end"
    for index, segment_id in enumerate(BESIDE_SEGMENT_IDS):
        status = "Fail" if fail_at == index else "Success"
        end = previous if status == "Fail" else f"{candidate_id}-q{index}"
        segments.append(
            {
                "segment_id": segment_id,
                "planner_status": status,
                "start_qpos_sha256": previous,
                "end_qpos_sha256": end,
            }
        )
        previous = end
        if status == "Fail":
            break
    return {
        "candidate_id": candidate_id,
        "main_object": "071_can/base1",
        "arm": "left",
        "reference": "074_displaystand/base3",
        "planner_seed": BESIDE_PLANNER_SEED,
        "planner_start_state_sha256": "same-prefix-end",
        "rng_state_after_reset_sha256": "same-reset-state",
        "planner_instance_id": "same-planner-instance",
        "planner_reset_performed": True,
        "first_segment_start_matches_planner_input_prefix_end": True,
        "route_audit_pass": True,
        "upright_axis_audited": True,
        "terminal_qpos_within_joint_limits": True,
        "waypoint_envelope_pass": True,
        "actual_held_transport_contact_gate_required": True,
        "facility_distance_pass": True,
        "planner_query_count": len(segments),
        "segment_receipts": segments,
    }


class F2SuffixRoutesV3Test(unittest.TestCase):
    @staticmethod
    def held_row(*, contact=True, actor="can", extra_pair=None):
        pairs = [{"body_a": "can", "body_b": "left_finger"}]
        if extra_pair is not None:
            pairs.append(extra_pair)
        return {
            "selected_gripper_contact": contact,
            "selected_contact_actor_name": actor,
            "contact_pairs": pairs,
        }

    def test_actual_held_transport_contact_policy_is_fail_closed(self):
        clean_rows = [self.held_row() for _ in range(4)]
        clean = audit_f2_held_transport_contacts(
            clean_rows,
            relation="beside",
            can_actor_name="can",
            selected_gripper_body_names=["left_finger"],
            named_facility_body_names=["box", "scale", "stand"],
        )
        self.assertTrue(clean["pass"])
        json.dumps(clean, allow_nan=False)

        for body in ("table", "box", "arm_non_gripper"):
            with self.subTest(body=body):
                rows = list(clean_rows)
                rows[1] = self.held_row(
                    extra_pair={"body_a": "can", "body_b": body}
                )
                result = audit_f2_held_transport_contacts(
                    rows,
                    relation="beside",
                    can_actor_name="can",
                    selected_gripper_body_names=["left_finger"],
                    named_facility_body_names=["box", "scale", "stand"],
                )
                self.assertFalse(result["pass"])

        broken_contact = list(clean_rows)
        broken_contact[2] = self.held_row(contact=False)
        self.assertFalse(
            audit_f2_held_transport_contacts(
                broken_contact,
                relation="inside",
                can_actor_name="can",
                selected_gripper_body_names=["left_finger"],
                named_facility_body_names=["box", "scale", "stand"],
            )["pass"]
        )
        wrong_actor = list(clean_rows)
        wrong_actor[2] = self.held_row(actor="other")
        self.assertFalse(
            audit_f2_held_transport_contacts(
                wrong_actor,
                relation="inside",
                can_actor_name="can",
                selected_gripper_body_names=["left_finger"],
                named_facility_body_names=["box", "scale", "stand"],
            )["pass"]
        )

        on_rows = [self.held_row() for _ in range(4)]
        on_rows[1] = self.held_row(
            extra_pair={"body_a": "can", "body_b": "scale"}
        )
        early = audit_f2_held_transport_contacts(
            on_rows,
            relation="on",
            can_actor_name="can",
            selected_gripper_body_names=["left_finger"],
            named_facility_body_names=["box", "scale", "stand"],
            relation_support_body_names=["scale"],
            support_contact_start_relative_row=2,
        )
        self.assertFalse(early["pass"])
        on_rows[1] = self.held_row()
        on_rows[2] = self.held_row(
            extra_pair={"body_a": "can", "body_b": "scale"}
        )
        allowed = audit_f2_held_transport_contacts(
            on_rows,
            relation="on",
            can_actor_name="can",
            selected_gripper_body_names=["left_finger"],
            named_facility_body_names=["box", "scale", "stand"],
            relation_support_body_names=["scale"],
            support_contact_start_relative_row=2,
        )
        self.assertTrue(allowed["pass"])

    def test_inside_gravity_drop_route_is_rim_clear_and_strict(self):
        route = build_inside_gravity_drop_route(
            current_eef_pose=CURRENT_EEF_POSE,
            current_actor_pose=CURRENT_ACTOR_POSE,
            box_pose=BOX_POSE,
            can_half_extents_m=CAN_HALF_EXTENTS,
            can_local_geometry_center_m=CAN_LOCAL_GEOMETRY_CENTER,
            rest_eef_pose=REST_EEF_POSE,
        )
        self.assertTrue(route["audit"]["pass"])
        self.assertEqual(
            tuple(item["segment_id"] for item in route["targets"]),
            INSIDE_SEGMENT_IDS,
        )
        self.assertEqual(route["release_target_index"], 0)
        self.assertEqual(tuple(route["sample_steps"]), INSIDE_SAMPLE_STEPS)
        self.assertGreater(route["rim_clearance_m"], 0.025)
        self.assertTrue(route["gates"]["final_target_full_obb_inside"])
        self.assertFalse(route["gates"]["final_full_obb_verifier_relaxed"])
        old_actor_origin_at_cavity_center = compose_pose(
            BOX_POSE,
            [
                *F2_PLASTICBOX_BASE2_CAVITY["target_center_local_m"],
                *F2_INSIDE_LOCAL_QUATERNION_WXYZ,
            ],
        )
        old_geometry_center = compose_pose(
            old_actor_origin_at_cavity_center,
            [*CAN_LOCAL_GEOMETRY_CENTER, 1.0, 0.0, 0.0, 0.0],
        )
        old_fit = obb_inside_local_cavity(
            old_geometry_center,
            CAN_HALF_EXTENTS,
            BOX_POSE,
            F2_PLASTICBOX_BASE2_CAVITY["lower_m"],
            F2_PLASTICBOX_BASE2_CAVITY["upper_m"],
        )
        self.assertFalse(old_fit["pass_true_cavity_obb"])
        self.assertGreater(
            np.linalg.norm(
                np.asarray(route["target_actor_pose"][:3])
                - old_actor_origin_at_cavity_center[:3]
            ),
            0.04,
        )

        tampered = copy.deepcopy(route)
        tampered["gates"]["final_full_obb_verifier_relaxed"] = True
        self.assertFalse(audit_inside_gravity_drop_route(tampered)["pass"])

    def test_exact_six_candidate_registry_matches_preregistered_pairs(self):
        registry = beside_candidate_registry()
        self.assertEqual(len(registry), 6)
        self.assertEqual(
            [item["candidate_id"] for item in registry],
            [item["candidate_id"] for item in F2_POSE_CANDIDATES],
        )
        self.assertEqual(
            [item["stand_relative_xy_m"] for item in registry],
            [item["stand_relative_xy_m"] for item in F2_POSE_CANDIDATES],
        )
        self.assertEqual(
            [item["upright_yaw_id"] for item in registry],
            [item["upright_yaw_id"] for item in F2_POSE_CANDIDATES],
        )
        self.assertEqual(
            [item["preplace_height_rule"] for item in registry],
            [item["preplace_height_rule"] for item in F2_POSE_CANDIDATES],
        )
        self.assertEqual(
            [item["height_margin_m"] for item in registry],
            [0.08, 0.10, 0.10, 0.08, 0.08, 0.10],
        )

    def test_each_beside_candidate_builds_exact_reciprocal_route(self):
        expected_xy = (
            (0.20, 0.12),
            (0.20, 0.12),
            (0.12, 0.10),
            (0.12, 0.10),
            (0.08, 0.07),
            (0.08, 0.07),
        )
        for candidate, xy in zip(BESIDE_CANDIDATES, expected_xy):
            with self.subTest(candidate=candidate.candidate_id):
                route = build_beside_route(
                    candidate.candidate_id,
                    current_eef_pose=CURRENT_EEF_POSE,
                    current_actor_pose=CURRENT_ACTOR_POSE,
                    stand_pose=STAND_POSE,
                    rest_eef_pose=REST_EEF_POSE,
                )
                self.assertTrue(route["audit"]["pass"])
                self.assertEqual(
                    tuple(item["segment_id"] for item in route["targets"]),
                    BESIDE_SEGMENT_IDS,
                )
                self.assertTrue(
                    np.allclose(route["target_actor_pose"][:2], xy, atol=1e-12)
                )
                self.assertAlmostEqual(
                    route["target_actor_pose"][2], LAYOUT["can_xyz"][2]
                )
                self.assertEqual(route["targets"][2]["pose"], route["targets"][4]["pose"])
                self.assertEqual(route["targets"][1]["pose"], route["targets"][5]["pose"])
                json.dumps(route, allow_nan=False)
                self.assertEqual(len(hash_json(route)), 64)

                tampered = copy.deepcopy(route)
                tampered["target_actor_pose"][0] += 0.01
                self.assertFalse(
                    audit_beside_route(tampered, stand_pose=STAND_POSE)["pass"]
                )

    def test_first_full_chain_success_wins_and_later_query_is_rejected(self):
        first = candidate_receipt(BESIDE_CANDIDATES[0].candidate_id, fail_at=1)
        second = candidate_receipt(BESIDE_CANDIDATES[1].candidate_id)
        decision = audit_beside_candidate_receipts([first, second])
        json.dumps(decision, allow_nan=False)
        self.assertEqual(len(hash_json(decision)), 64)
        self.assertTrue(decision["pass"])
        self.assertEqual(decision["selected_candidate_id"], "p0_y1_h1")
        self.assertEqual(decision["planner_query_count"], 2 + 7)

        third = candidate_receipt(BESIDE_CANDIDATES[2].candidate_id, fail_at=0)
        with self.assertRaisesRegex(ValueError, "after first success"):
            audit_beside_candidate_receipts([first, second, third])

    def test_all_six_fail_terminal_without_layout_mutation(self):
        receipts = [
            candidate_receipt(item.candidate_id, fail_at=6)
            for item in BESIDE_CANDIDATES
        ]
        decision = audit_beside_candidate_receipts(receipts)
        self.assertFalse(decision["pass"])
        self.assertTrue(decision["exhausted"])
        self.assertEqual(
            decision["terminal_if_exhausted"], BESIDE_EXHAUSTION_TERMINAL
        )
        self.assertEqual(decision["planner_query_count"], 42)

        broken = copy.deepcopy(receipts)
        broken[1]["segment_receipts"][1]["start_qpos_sha256"] = "wrong"
        result = audit_beside_candidate_receipts(broken)
        self.assertFalse(result["evaluated"][1]["checks"]["chain_continuity"])

        broken_start = copy.deepcopy(receipts)
        broken_start[0]["first_segment_start_matches_planner_input_prefix_end"] = False
        result = audit_beside_candidate_receipts(broken_start)
        self.assertFalse(
            result["evaluated"][0]["checks"]["planner_input_prefix_start_link"]
        )

        broken_planner = copy.deepcopy(receipts)
        broken_planner[-1]["planner_instance_id"] = "other-planner"
        with self.assertRaisesRegex(ValueError, "frozen planner state"):
            audit_beside_candidate_receipts(broken_planner)

    def test_static_envelope_is_exactly_68_and_not_authorization(self):
        envelope = proposed_static_planner_envelope()
        self.assertEqual(
            envelope["components"],
            {"canonical_prefix": 19, "inside": 3, "on": 4, "beside": 42},
        )
        self.assertEqual(envelope["planner_query_count"], 68)
        self.assertTrue(envelope["within_existing_numeric_planner_limit"])
        self.assertIn("not revision authorization", envelope["authorization_note"])


if __name__ == "__main__":
    unittest.main()
