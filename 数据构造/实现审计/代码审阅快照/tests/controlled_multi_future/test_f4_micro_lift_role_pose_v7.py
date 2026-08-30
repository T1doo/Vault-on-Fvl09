import copy
import json
import unittest

import numpy as np

from controlled_multi_future.f4_boundary_micro_lift_v5 import (
    ACTUAL_GRIPPER_OPEN_MIN_QPOS_M,
    A_MICRO_LIFT_DISTANCE_M,
    A_PREGRASP_DISTANCE_M,
    GRASP_BOUNDARY_ORIENTATION_ATOL_RAD,
    GRASP_BOUNDARY_POSITION_ATOL_M,
    MICRO_LIFT_MAX_CONTACT_BREAK_COUNT,
    MICRO_LIFT_MIN_BILATERAL_CONTACT_COUNT,
    MICRO_LIFT_MIN_ACTOR_RISE_M,
    MICRO_LIFT_MIN_CONTACT_FRACTION,
    MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
    NONZERO_CONTACT_IMPULSE_EPS,
    build_micro_lift_noninterference_receipt_v5,
)
from controlled_multi_future.f4_micro_lift_role_pose_v7 import (
    build_a_role_pose_micro_lift_gate_receipt_v7,
    build_a_role_pose_micro_lift_rows_v7,
    validate_a_role_pose_micro_lift_gate_receipt_v7,
)


Q = [1.0, 0.0, 0.0, 0.0]
A_NAME = "f4_object_a"
COMMON_X_POSE = [0.20347312092781067, -0.11390811204910278, 0.788322925567627, *Q]
A_START_Z = 0.7620106935501099
A_END_Z = 0.7793172597885132
FRAME_COUNT = 87
SOURCE_START = 3667


def _targets():
    pregrasp = [0.16, -0.001, 0.9869525509109666, *Q]
    grasp = [0.16, 0.008, 0.8974017753160367, *Q]
    lift = [0.16, 0.008, 0.9174017753160367, *Q]
    return [
        {"segment_id": "A_pregrasp", "pose": pregrasp},
        {"segment_id": "A_grasp", "pose": grasp},
        {"segment_id": "A_micro_lift", "pose": lift},
    ]


def _trace_rows(*, positive_tail=False, wrong_actor=False, break_contact=False):
    rows = []
    for index in range(FRAME_COUNT):
        fraction = index / (FRAME_COUNT - 1)
        a_z = A_START_Z + fraction * (A_END_Z - A_START_Z)
        impulse = 0.005 if index < 7 else 0.0
        if positive_tail and index == FRAME_COUNT - 1:
            impulse = 1e-5
        selected = not (break_contact and index == FRAME_COUNT // 2)
        rows.append(
            {
                "actor_pose": list(COMMON_X_POSE),
                "role_actor_poses": {
                    "A": [0.159158, 0.019964, a_z, *Q],
                    "B": [0.28, 0.02, 0.762, *Q],
                    "C": [0.40, 0.02, 0.762, *Q],
                    "common_x": list(COMMON_X_POSE),
                },
                "selected_gripper_contact": selected,
                "selected_gripper_contact_count": 2 if selected else 0,
                "selected_contact_actor_name": (
                    "f4_common_x" if wrong_actor and index == 0 else A_NAME
                ),
                "contact_pairs": [
                    {
                        "body_a": A_NAME,
                        "body_b": "table",
                        "impulse_norm_sum": impulse,
                    },
                    {
                        "body_a": "fr_link7",
                        "body_b": A_NAME,
                        "impulse_norm_sum": 0.12,
                    },
                    {
                        "body_a": "fr_link8",
                        "body_b": A_NAME,
                        "impulse_norm_sum": 0.12,
                    },
                ],
            }
        )
    return rows


def _noninterference(*, moved=False):
    baseline = {
        "common_x": COMMON_X_POSE,
        "B": [0.28, 0.02, 0.762, *Q],
        "C": [0.40, 0.02, 0.762, *Q],
    }
    stages = []
    for stage_id in (
        "after_A_pregrasp",
        "after_A_grasp",
        "after_A_micro_lift",
    ):
        poses = copy.deepcopy(baseline)
        if moved and stage_id == "after_A_micro_lift":
            poses["common_x"][0] += 0.011
        stages.append(
            {
                "stage_id": stage_id,
                "poses": poses,
                "stability_and_support": {
                    "common_x": True,
                    "B": True,
                    "C": True,
                },
                "common_x_tray_predicate": True,
            }
        )
    return build_micro_lift_noninterference_receipt_v5(
        baseline_poses=baseline, stage_states=stages
    )


def _build(*, rows=None, noninterference=None):
    targets = _targets()
    return build_a_role_pose_micro_lift_gate_receipt_v7(
        targets=targets,
        realized_pregrasp_pose=targets[0]["pose"],
        realized_grasp_pose=targets[1]["pose"],
        pregrasp_linear_velocity=[0.0, 0.0, 0.0],
        pregrasp_angular_velocity=[0.0, 0.0, 0.0],
        grasp_linear_velocity=[0.0, 0.0, 0.0],
        grasp_angular_velocity=[0.0, 0.0, 0.0],
        preclose_right_gripper_joint_qpos=[0.045, 0.045],
        trace_rows=_trace_rows() if rows is None else rows,
        source_trace_indices=list(range(SOURCE_START, SOURCE_START + FRAME_COUNT)),
        expected_actor_name=A_NAME,
        allowed_nonzero_contact_pairs=[
            [A_NAME, "fr_link7"],
            [A_NAME, "fr_link8"],
            [A_NAME, "table"],
        ],
        noninterference_receipt=(
            _noninterference() if noninterference is None else noninterference
        ),
    )


class F4MicroLiftRolePoseV7Test(unittest.TestCase):
    def test_common_x_stays_fixed_but_role_a_rises_and_zero_impulse_tail_passes(self):
        receipt = _build()
        self.assertTrue(receipt["pass"])
        adapter = receipt["role_pose_adapter"]
        self.assertEqual(
            adapter["actor_pose_source"],
            'trace_rows[*].role_actor_poses["A"]',
        )
        self.assertAlmostEqual(
            adapter["summary"]["actor_rise_m"],
            0.01730656623840332,
        )
        self.assertGreaterEqual(
            adapter["summary"]["actor_rise_m"], MICRO_LIFT_MIN_ACTOR_RISE_M
        )
        self.assertEqual(
            adapter["summary"]["actor_table_pair_presence_count"], FRAME_COUNT
        )
        self.assertEqual(
            adapter["summary"]["actor_table_nonzero_impulse_contact_count"], 7
        )
        self.assertEqual(
            adapter["summary"]["tail_pair_presence"],
            [True] * MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
        )
        self.assertEqual(
            adapter["summary"]["tail_nonzero_impulse_contact"],
            [False] * MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
        )
        self.assertEqual(
            adapter["summary"]["tail_impulse_norm_sum"],
            [0.0] * MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
        )
        gate = receipt["micro_lift_gate"]
        self.assertTrue(gate["checks"]["actor_rise"])
        self.assertTrue(gate["checks"]["table_contact_cleared_in_tail"])
        self.assertEqual(gate["micro_lift_metrics"]["actor_start_z_m"], A_START_Z)
        self.assertEqual(gate["micro_lift_metrics"]["actor_end_z_m"], A_END_Z)
        self.assertNotEqual(
            adapter["frame_audit"][0]["role_actor_pose"],
            adapter["frame_audit"][0]["trace_actor_pose_audit_only"],
        )

    def test_positive_table_impulse_in_tail_fails_without_threshold_change(self):
        receipt = _build(rows=_trace_rows(positive_tail=True))
        self.assertFalse(receipt["pass"])
        self.assertFalse(
            receipt["micro_lift_gate"]["checks"][
                "table_contact_cleared_in_tail"
            ]
        )
        adapter = receipt["role_pose_adapter"]
        self.assertTrue(
            adapter["summary"]["tail_nonzero_impulse_contact"][-1]
        )
        self.assertGreater(
            adapter["summary"]["tail_impulse_norm_sum"][-1],
            NONZERO_CONTACT_IMPULSE_EPS,
        )
        self.assertEqual(
            receipt["micro_lift_gate"]["thresholds"][
                "nonzero_contact_impulse_eps"
            ],
            NONZERO_CONTACT_IMPULSE_EPS,
        )

    def test_actor_identity_and_contact_continuity_remain_hard_gates(self):
        wrong_actor = _build(rows=_trace_rows(wrong_actor=True))
        self.assertFalse(wrong_actor["pass"])
        self.assertFalse(
            wrong_actor["micro_lift_gate"]["checks"][
                "selected_actor_identity"
            ]
        )
        broken = _build(rows=_trace_rows(break_contact=True))
        self.assertFalse(broken["pass"])
        self.assertFalse(
            broken["micro_lift_gate"]["checks"][
                "selected_contact_break_count"
            ]
        )
        self.assertFalse(
            broken["micro_lift_gate"]["checks"]["bilateral_contact"]
        )

    def test_noninterference_remains_an_independent_hard_gate(self):
        receipt = _build(noninterference=_noninterference(moved=True))
        self.assertFalse(receipt["pass"])
        self.assertTrue(receipt["micro_lift_gate"]["pass"])
        self.assertFalse(receipt["noninterference_gate"]["pass"])
        self.assertFalse(receipt["checks"]["noninterference_gate_pass"])

    def test_role_a_is_required_and_primary_actor_pose_is_never_a_fallback(self):
        rows = _trace_rows()
        for row in rows:
            row["role_actor_poses"].pop("A")
        with self.assertRaisesRegex(ValueError, "role_actor_poses"):
            build_a_role_pose_micro_lift_rows_v7(
                trace_rows=rows,
                source_trace_indices=list(
                    range(SOURCE_START, SOURCE_START + FRAME_COUNT)
                ),
                expected_actor_name=A_NAME,
            )

    def test_thresholds_and_revision6_terminal_boundary_are_immutable(self):
        receipt = _build()
        self.assertTrue(receipt["micro_lift_gate_v5_thresholds_unchanged"])
        self.assertFalse(receipt["numeric_threshold_changed"])
        self.assertFalse(receipt["revision6_retroactive_acceptance_allowed"])
        self.assertTrue(receipt["fresh_source_distinct_execution_required"])
        self.assertEqual(
            receipt["micro_lift_gate"]["thresholds"][
                "actual_gripper_open_min_qpos_m"
            ],
            ACTUAL_GRIPPER_OPEN_MIN_QPOS_M,
        )
        self.assertEqual(
            receipt["micro_lift_gate"]["thresholds"],
            {
                "pregrasp_distance_m": A_PREGRASP_DISTANCE_M,
                "micro_lift_distance_m": A_MICRO_LIFT_DISTANCE_M,
                "minimum_actor_rise_m": MICRO_LIFT_MIN_ACTOR_RISE_M,
                "minimum_contact_fraction": MICRO_LIFT_MIN_CONTACT_FRACTION,
                "minimum_bilateral_contact_count": (
                    MICRO_LIFT_MIN_BILATERAL_CONTACT_COUNT
                ),
                "maximum_contact_break_count": (
                    MICRO_LIFT_MAX_CONTACT_BREAK_COUNT
                ),
                "table_free_tail_frames": MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
                "position_boundary_atol_m": GRASP_BOUNDARY_POSITION_ATOL_M,
                "orientation_boundary_atol_rad": (
                    GRASP_BOUNDARY_ORIENTATION_ATOL_RAD
                ),
                "actual_gripper_open_min_qpos_m": (
                    ACTUAL_GRIPPER_OPEN_MIN_QPOS_M
                ),
                "nonzero_contact_impulse_eps": NONZERO_CONTACT_IMPULSE_EPS,
            },
        )
        self.assertEqual(
            receipt,
            validate_a_role_pose_micro_lift_gate_receipt_v7(receipt),
        )
        json.dumps(receipt, allow_nan=False)

    def test_receipt_is_tamper_evident(self):
        receipt = _build()
        tampered = copy.deepcopy(receipt)
        tampered["role_pose_adapter"]["summary"]["actor_rise_m"] = 0.0
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_a_role_pose_micro_lift_gate_receipt_v7(tampered)


if __name__ == "__main__":
    unittest.main()
