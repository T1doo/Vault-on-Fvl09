import copy
import json
import unittest

import numpy as np

from controlled_multi_future.f4_boundary_micro_lift_v5 import (
    ACTUAL_GRIPPER_OPEN_MIN_QPOS_M,
    A_DIAGNOSTIC_SEGMENT_IDS,
    A_MICRO_LIFT_DISTANCE_M,
    BOUNDARY_FRAME_COUNT,
    COMMON_PREFIX_LEGACY_IDS,
    COMMON_PREFIX_REPAIRED_IDS,
    MICRO_LIFT_FRAME_COUNT,
    MICRO_LIFT_MIN_ACTOR_RISE_M,
    MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
    build_a_micro_lift_gate_receipt_v5,
    build_a_top_down_micro_lift_targets_v5,
    build_actual_open_contact_boundary_receipt_v5,
    build_micro_lift_noninterference_receipt_v5,
    build_repaired_common_prefix_targets_v5,
    validate_a_micro_lift_gate_receipt_v5,
    validate_actual_open_contact_boundary_receipt_v5,
    validate_repaired_common_prefix_targets_v5,
)
from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT
from controlled_multi_future.geometry import quaternion_multiply


Q = np.asarray(
    [
        0.5243570072481656,
        -0.47439082845243685,
        0.4743935067167858,
        0.5243604405510669,
    ],
    dtype=np.float64,
)


def _legacy_common_targets():
    poses = {
        "common_pregrasp": [0.28, 0.079, 0.971, *Q],
        "common_grasp": [0.28, 0.088, 0.881, *Q],
        "common_lift": [0.28, 0.088, 0.981, *Q],
        "common_safe_vertical": [0.28, 0.088, 0.981, *Q],
        "common_center_high": [0.243, -0.019, 0.981, *Q],
        "common_above_tray": [0.206, -0.126, 0.981, *Q],
        "common_preplace": [0.206, -0.126, 1.009, *Q],
        "common_release": [0.206, -0.126, 0.909, *Q],
        "common_neutral": [0.15, -0.02, 0.95, *Q],
    }
    return [
        {"segment_id": segment_id, "pose": poses[segment_id]}
        for segment_id in COMMON_PREFIX_LEGACY_IDS
    ]


def _allowed_support_pairs():
    return (
        ("f4_common_x", "f4_common_tray"),
        ("f4_object_a", "table"),
        ("f4_object_b", "table"),
        ("f4_object_c", "table"),
    )


def _boundary_rows(target_pose):
    return [
        {
            "step_index": 5000 + index,
            "timestamp": (5000 + index) / 250.0,
            "realized_right_gripper_joint_qpos": [0.044, 0.043],
            "right_gripper_command": 1.0,
            "right_gripper_drive_target_readback": 1.0,
            "eef_pose": list(target_pose),
            "eef_linear_velocity": [0.0, 0.0, 0.0],
            "eef_angular_velocity": [0.0, 0.0, 0.0],
            "contact_pairs": [
                {
                    "body_a": "f4_common_x",
                    "body_b": "f4_common_tray",
                    "impulse_norm_sum": 0.001,
                },
                {
                    "body_a": "f4_object_a",
                    "body_b": "table",
                    "impulse_norm_sum": 0.001,
                },
            ],
        }
        for index in range(BOUNDARY_FRAME_COUNT)
    ]


def _micro_rows(actor_pose, *, passing=True):
    start = np.asarray(actor_pose, dtype=np.float64)
    rows = []
    for index in range(MICRO_LIFT_FRAME_COUNT):
        fraction = index / (MICRO_LIFT_FRAME_COUNT - 1)
        pose = start.copy()
        pose[2] += (0.020 if passing else 0.0025) * fraction
        selected = passing or index < 8
        table_contact = False if passing and index >= 10 else True
        contacts = [
            {
                "body_a": "fr_link7",
                "body_b": "f4_object_a",
                "impulse_norm_sum": 0.1 if selected else 0.0,
            },
            {
                "body_a": "fr_link8",
                "body_b": "f4_object_a",
                "impulse_norm_sum": 0.1 if selected else 0.0,
            },
        ]
        if table_contact:
            contacts.append(
                {
                    "body_a": "f4_object_a",
                    "body_b": "table",
                    "impulse_norm_sum": 0.01,
                }
            )
        if not passing and index == 0:
            contacts.append(
                {
                    "body_a": "fr_link8",
                    "body_b": "f4_common_x",
                    "impulse_norm_sum": 0.1,
                }
            )
        rows.append(
            {
                "actor_pose": pose,
                "selected_gripper_contact": selected,
                "selected_gripper_contact_count": 2 if selected else 0,
                "selected_contact_actor_name": "f4_object_a",
                "actor_table_contact": table_contact,
                "contact_pairs": contacts,
            }
        )
    return rows


def _micro_allowed_pairs():
    return (
        ("fr_link7", "f4_object_a"),
        ("fr_link8", "f4_object_a"),
        ("f4_object_a", "table"),
    )


class F4BoundaryMicroLiftV5Test(unittest.TestCase):
    def test_micro_noninterference_rejects_any_target_displacement_or_tray_loss(self):
        baseline = {
            "common_x": [0.20, -0.11, 0.788, 1, 0, 0, 0],
            "B": LAYOUT["object_poses"]["B"],
            "C": LAYOUT["object_poses"]["C"],
        }
        passing_stage = {
            "stage_id": "after_A_micro_lift",
            "poses": copy.deepcopy(baseline),
            "stability_and_support": {
                "common_x": True,
                "B": True,
                "C": True,
            },
            "common_x_tray_predicate": True,
        }
        self.assertTrue(
            build_micro_lift_noninterference_receipt_v5(
                baseline_poses=baseline,
                stage_states=[passing_stage],
            )["pass"]
        )
        for role in ("common_x", "B", "C"):
            changed = copy.deepcopy(passing_stage)
            changed["poses"][role][0] += 0.011
            self.assertFalse(
                build_micro_lift_noninterference_receipt_v5(
                    baseline_poses=baseline,
                    stage_states=[changed],
                )["pass"]
            )
        lost_tray = copy.deepcopy(passing_stage)
        lost_tray["common_x_tray_predicate"] = False
        self.assertFalse(
            build_micro_lift_noninterference_receipt_v5(
                baseline_poses=baseline,
                stage_states=[lost_tray],
            )["pass"]
        )

    def test_common_prefix_repair_is_vertical_then_reuses_high_center(self):
        original = _legacy_common_targets()
        for item in original:
            item["pose"] = np.asarray(item["pose"], dtype=np.float64)
        before = copy.deepcopy(original)
        repaired, audit = build_repaired_common_prefix_targets_v5(original)
        for left, right in zip(original, before):
            self.assertEqual(left["segment_id"], right["segment_id"])
            np.testing.assert_array_equal(left["pose"], right["pose"])
        self.assertEqual(
            [item["segment_id"] for item in repaired],
            list(COMMON_PREFIX_REPAIRED_IDS),
        )
        np.testing.assert_array_equal(repaired[8]["pose"], repaired[6]["pose"])
        np.testing.assert_array_equal(repaired[9]["pose"], repaired[4]["pose"])
        self.assertAlmostEqual(audit["withdraw_height_m"], 0.10)
        self.assertFalse(audit["common_actor_release_target_changed"])
        self.assertFalse(audit["common_tray_changed"])
        self.assertFalse(audit["program_changed"])
        self.assertTrue(audit["canonical_prefix_target_structure_changed"])
        self.assertTrue(audit["canonical_prefix_must_refreeze"])
        self.assertTrue(audit["pass"])
        self.assertTrue(validate_repaired_common_prefix_targets_v5(repaired)["pass"])

    def test_common_prefix_repair_rejects_nonvertical_withdraw_source(self):
        targets = _legacy_common_targets()
        targets[6]["pose"][0] += 0.001
        with self.assertRaisesRegex(ValueError, "vertical withdraw"):
            build_repaired_common_prefix_targets_v5(targets)
        with self.assertRaisesRegex(ValueError, "nine targets"):
            build_repaired_common_prefix_targets_v5(targets[:-1])

    def test_actual_open_contact_boundary_uses_both_real_fingers(self):
        neutral = _legacy_common_targets()[4]["pose"]
        receipt = build_actual_open_contact_boundary_receipt_v5(
            phase="common_prefix_end",
            rows=_boundary_rows(neutral),
            target_neutral_pose=neutral,
            allowed_nonzero_contact_pairs=_allowed_support_pairs(),
        )
        self.assertTrue(receipt["pass"])
        self.assertTrue(receipt["checks"]["actual_both_fingers_open"])
        self.assertEqual(
            receipt["minimum_actual_right_gripper_joint_qpos_m"],
            [0.044, 0.043],
        )
        self.assertEqual(receipt["forbidden_nonzero_contacts"], [])
        self.assertEqual(
            receipt,
            validate_actual_open_contact_boundary_receipt_v5(receipt),
        )
        json.dumps(receipt, allow_nan=False)

    def test_boundary_catches_r4_command_open_false_positive_and_tray_collision(self):
        neutral = _legacy_common_targets()[4]["pose"]
        rows = _boundary_rows(neutral)
        for row in rows:
            row["realized_right_gripper_joint_qpos"] = [0.006, 0.044]
        rows[0]["contact_pairs"].append(
            {
                "body_a": "fr_link7",
                "body_b": "f4_common_tray",
                "impulse_norm_sum": 0.5,
            }
        )
        receipt = build_actual_open_contact_boundary_receipt_v5(
            phase="common_prefix_end",
            rows=rows,
            target_neutral_pose=neutral,
            allowed_nonzero_contact_pairs=_allowed_support_pairs(),
        )
        self.assertFalse(receipt["pass"])
        self.assertFalse(receipt["checks"]["actual_both_fingers_open"])
        self.assertTrue(receipt["checks"]["command_open"])
        self.assertTrue(receipt["checks"]["drive_target_readback_open"])
        self.assertFalse(receipt["checks"]["no_forbidden_nonzero_contact"])
        self.assertEqual(receipt["first_forbidden_contact_frame"], 0)
        self.assertLess(
            receipt["minimum_actual_right_gripper_joint_qpos_m"][0],
            ACTUAL_GRIPPER_OPEN_MIN_QPOS_M,
        )

    def test_top_down_a_targets_use_existing_contract_and_exact_20mm_lift(self):
        targets, audit = build_a_top_down_micro_lift_targets_v5(
            actor_pose=LAYOUT["object_poses"]["A"]
        )
        self.assertEqual(
            [item["segment_id"] for item in targets],
            list(A_DIAGNOSTIC_SEGMENT_IDS),
        )
        grasp = np.asarray(targets[1]["pose"])
        lift = np.asarray(targets[2]["pose"])
        np.testing.assert_allclose(
            lift[:3] - grasp[:3],
            [0.0, 0.0, A_MICRO_LIFT_DISTANCE_M],
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_array_equal(lift[3:], grasp[3:])
        self.assertTrue(audit["uses_existing_project_top_down_grasp_v1"])
        self.assertTrue(audit["diagnostic_only"])
        self.assertFalse(audit["place_target_defined"])
        self.assertTrue(audit["pass"])

    def test_passing_micro_lift_gate_requires_realized_boundary_and_table_clear(self):
        targets, _ = build_a_top_down_micro_lift_targets_v5(
            actor_pose=LAYOUT["object_poses"]["A"]
        )
        receipt = build_a_micro_lift_gate_receipt_v5(
            targets=targets,
            realized_pregrasp_pose=targets[0]["pose"],
            realized_grasp_pose=targets[1]["pose"],
            pregrasp_linear_velocity=[0.0, 0.0, 0.0],
            pregrasp_angular_velocity=[0.0, 0.0, 0.0],
            grasp_linear_velocity=[0.0, 0.0, 0.0],
            grasp_angular_velocity=[0.0, 0.0, 0.0],
            preclose_right_gripper_joint_qpos=[0.044, 0.044],
            micro_lift_rows=_micro_rows(LAYOUT["object_poses"]["A"]),
            expected_actor_name="f4_object_a",
            allowed_nonzero_contact_pairs=_micro_allowed_pairs(),
        )
        self.assertTrue(receipt["pass"])
        self.assertGreaterEqual(
            receipt["micro_lift_metrics"]["actor_rise_m"],
            MICRO_LIFT_MIN_ACTOR_RISE_M,
        )
        self.assertEqual(
            receipt["micro_lift_metrics"]["table_contact_tail"],
            [False] * MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
        )
        self.assertEqual(
            receipt,
            validate_a_micro_lift_gate_receipt_v5(receipt),
        )
        json.dumps(receipt, allow_nan=False)

    def test_r4_like_missed_grasp_fails_before_full_block(self):
        targets, _ = build_a_top_down_micro_lift_targets_v5(
            actor_pose=LAYOUT["object_poses"]["A"]
        )
        pregrasp = np.asarray(targets[0]["pose"], dtype=np.float64).copy()
        grasp = np.asarray(targets[1]["pose"], dtype=np.float64).copy()
        pregrasp[0] += 0.00935
        grasp[1] += 0.08493
        half = 0.29208 / 2.0
        grasp[3:] = quaternion_multiply(
            [np.cos(half), np.sin(half), 0.0, 0.0], grasp[3:]
        )
        receipt = build_a_micro_lift_gate_receipt_v5(
            targets=targets,
            realized_pregrasp_pose=pregrasp,
            realized_grasp_pose=grasp,
            pregrasp_linear_velocity=[0.0, 0.0, 0.0],
            pregrasp_angular_velocity=[0.0, 0.0, 0.0],
            grasp_linear_velocity=[0.0, 0.0, 0.0],
            grasp_angular_velocity=[0.0, 0.0, 0.0],
            preclose_right_gripper_joint_qpos=[0.006, 0.044],
            micro_lift_rows=_micro_rows(
                LAYOUT["object_poses"]["A"], passing=False
            ),
            expected_actor_name="f4_object_a",
            allowed_nonzero_contact_pairs=_micro_allowed_pairs(),
        )
        self.assertFalse(receipt["pass"])
        for check in (
            "pregrasp_position_boundary",
            "grasp_position_boundary",
            "grasp_orientation_boundary",
            "actual_both_fingers_open_before_close",
            "selected_contact_fraction",
            "selected_contact_break_count",
            "bilateral_contact",
            "actor_rise",
            "table_contact_cleared_in_tail",
            "no_forbidden_nonzero_contact",
        ):
            self.assertFalse(receipt["checks"][check], check)
        self.assertEqual(receipt["first_forbidden_contact_frame"], 0)
        self.assertLess(receipt["micro_lift_metrics"]["actor_rise_m"], 0.003)

    def test_invalid_lengths_nonfinite_and_tampering_fail_closed(self):
        neutral = _legacy_common_targets()[4]["pose"]
        with self.assertRaisesRegex(ValueError, "exactly 50"):
            build_actual_open_contact_boundary_receipt_v5(
                phase="common_prefix_end",
                rows=_boundary_rows(neutral)[:-1],
                target_neutral_pose=neutral,
                allowed_nonzero_contact_pairs=_allowed_support_pairs(),
            )
        rows = _boundary_rows(neutral)
        rows[0]["eef_linear_velocity"] = [np.nan, 0.0, 0.0]
        with self.assertRaisesRegex(ValueError, "finite"):
            build_actual_open_contact_boundary_receipt_v5(
                phase="common_prefix_end",
                rows=rows,
                target_neutral_pose=neutral,
                allowed_nonzero_contact_pairs=_allowed_support_pairs(),
            )
        targets, _ = build_a_top_down_micro_lift_targets_v5(
            actor_pose=LAYOUT["object_poses"]["A"]
        )
        with self.assertRaisesRegex(ValueError, "exactly 20 mm"):
            build_a_top_down_micro_lift_targets_v5(
                actor_pose=LAYOUT["object_poses"]["A"],
                micro_lift_distance_m=0.019,
            )
        with self.assertRaisesRegex(ValueError, "at least 50"):
            build_a_micro_lift_gate_receipt_v5(
                targets=targets,
                realized_pregrasp_pose=targets[0]["pose"],
                realized_grasp_pose=targets[1]["pose"],
                pregrasp_linear_velocity=[0.0, 0.0, 0.0],
                pregrasp_angular_velocity=[0.0, 0.0, 0.0],
                grasp_linear_velocity=[0.0, 0.0, 0.0],
                grasp_angular_velocity=[0.0, 0.0, 0.0],
                preclose_right_gripper_joint_qpos=[0.044, 0.044],
                micro_lift_rows=_micro_rows(
                    LAYOUT["object_poses"]["A"]
                )[:-1],
                expected_actor_name="f4_object_a",
                allowed_nonzero_contact_pairs=_micro_allowed_pairs(),
            )
        receipt = build_a_micro_lift_gate_receipt_v5(
            targets=targets,
            realized_pregrasp_pose=targets[0]["pose"],
            realized_grasp_pose=targets[1]["pose"],
            pregrasp_linear_velocity=[0.0, 0.0, 0.0],
            pregrasp_angular_velocity=[0.0, 0.0, 0.0],
            grasp_linear_velocity=[0.0, 0.0, 0.0],
            grasp_angular_velocity=[0.0, 0.0, 0.0],
            preclose_right_gripper_joint_qpos=[0.044, 0.044],
            micro_lift_rows=_micro_rows(LAYOUT["object_poses"]["A"]),
            expected_actor_name="f4_object_a",
            allowed_nonzero_contact_pairs=_micro_allowed_pairs(),
        )
        receipt["checks"]["actor_rise"] = False
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_a_micro_lift_gate_receipt_v5(receipt)


if __name__ == "__main__":
    unittest.main()
