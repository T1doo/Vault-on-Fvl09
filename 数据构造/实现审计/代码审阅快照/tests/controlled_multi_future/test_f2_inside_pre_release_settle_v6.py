import copy
import json
import unittest

from controlled_multi_future.f2_inside_pre_release_settle_v6 import (
    EVALUATED_STABILITY_FRAMES,
    STABLE_ANGULAR_SPEED_RPS,
    STABLE_LINEAR_SPEED_MPS,
    TOTAL_SETTLE_STEPS,
    WARMUP_STEPS,
    audit_f2_inside_pre_release_settle_window_v6,
    validate_f2_inside_pre_release_settle_receipt_v6,
)


CAN = "f2_main_can"
FINGERS = ["fl_link7", "fl_link8"]
ASSEMBLY = ["fl_link6", "fl_link7", "fl_link8"]


def row(*, linear=0.001, angular=0.001, contact=True, actor=CAN, extra=None):
    pairs = [
        {"body_a": CAN, "body_b": "fl_link7", "point_count": 1},
        {"body_a": CAN, "body_b": "fl_link8", "point_count": 1},
        {"body_a": CAN, "body_b": "fl_link6", "point_count": 1},
    ]
    if extra is not None:
        pairs.append(extra)
    return {
        "actor_linear_velocity": [linear, 0.0, 0.0],
        "actor_angular_velocity": [0.0, angular, 0.0],
        "selected_gripper_contact": contact,
        "selected_contact_actor_name": actor,
        "contact_pairs": pairs,
    }


def geometry(*, projection=True, clearance=0.0215, reported=True):
    return {
        "opening_projection_inside": projection,
        "rim_clearance_m": clearance,
        "rim_clearance_pass": reported,
        "can_geometry_center_pose": [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    }


def audit(rows, *, final_geometry=None):
    return audit_f2_inside_pre_release_settle_window_v6(
        rows,
        can_actor_name=CAN,
        selected_contact_signal_link_names=FINGERS,
        allowed_gripper_assembly_body_names=ASSEMBLY,
        final_geometry_gate=geometry()
        if final_geometry is None
        else final_geometry,
    )


class F2InsidePreReleaseSettleV6Test(unittest.TestCase):
    def test_warmup_spike_is_excluded_only_from_velocity_gate(self):
        rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
        rows[2] = row(angular=STABLE_ANGULAR_SPEED_RPS + 0.0065)
        receipt = audit(rows)
        self.assertTrue(receipt["pass"])
        self.assertEqual(receipt["warmup_steps"], 10)
        self.assertEqual(receipt["evaluated_stability_frames"], 50)
        self.assertEqual(receipt["total_settle_steps"], 60)
        self.assertGreater(
            receipt["warmup_metrics"]["maximum_angular_speed_rps"],
            STABLE_ANGULAR_SPEED_RPS,
        )
        self.assertLessEqual(
            receipt["evaluated_stability_metrics"][
                "maximum_angular_speed_rps"
            ],
            STABLE_ANGULAR_SPEED_RPS,
        )
        self.assertEqual(
            receipt["warmup_exclusion_scope"], "velocity stationarity only"
        )
        json.dumps(receipt, allow_nan=False)
        self.assertEqual(
            validate_f2_inside_pre_release_settle_receipt_v6(receipt),
            receipt,
        )

    def test_velocity_spike_in_final_fifty_fails(self):
        rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
        rows[WARMUP_STEPS] = row(
            angular=STABLE_ANGULAR_SPEED_RPS + 0.001
        )
        result = audit(rows)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["evaluated_angular_stationary"])

        rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
        rows[-1] = row(linear=STABLE_LINEAR_SPEED_MPS + 0.001)
        result = audit(rows)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["evaluated_linear_stationary"])

    def test_contact_and_identity_are_hard_over_all_sixty(self):
        for frame_index in (0, WARMUP_STEPS, TOTAL_SETTLE_STEPS - 1):
            with self.subTest(frame_index=frame_index, predicate="contact"):
                rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
                rows[frame_index] = row(contact=False)
                result = audit(rows)
                self.assertFalse(result["pass"])
                self.assertFalse(
                    result["checks"][
                        "selected_finger_contact_continuous_all_60"
                    ]
                )
            with self.subTest(frame_index=frame_index, predicate="identity"):
                rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
                rows[frame_index] = row(actor="other")
                result = audit(rows)
                self.assertFalse(result["pass"])
                self.assertFalse(
                    result["checks"]["selected_actor_identity_all_60"]
                )

    def test_unintended_contact_anywhere_fails_but_palm_is_allowed(self):
        rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
        self.assertTrue(audit(rows)["pass"])

        for frame_index in (2, 20, 59):
            with self.subTest(frame_index=frame_index):
                rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
                rows[frame_index] = row(
                    extra={
                        "body_a": CAN,
                        "body_b": "f2_plasticbox",
                        "point_count": 2,
                        "impulse_norm_sum": 0.1,
                    }
                )
                result = audit(rows)
                self.assertFalse(result["pass"])
                self.assertFalse(
                    result["checks"]["no_unintended_body_contact_all_60"]
                )
                self.assertEqual(
                    result["all_60_contact_identity_evidence"][
                        "unintended_contacts"
                    ][0]["window_phase"],
                    "warmup"
                    if frame_index < WARMUP_STEPS
                    else "evaluated_stability",
                )

    def test_final_geometry_remains_strict(self):
        rows = [row() for _ in range(TOTAL_SETTLE_STEPS)]
        for value, failed_check in (
            (geometry(projection=False), "final_opening_projection_inside"),
            (
                geometry(clearance=0.019, reported=True),
                "final_rim_clearance_at_least_20mm",
            ),
            (
                geometry(clearance=0.021, reported=False),
                "final_rim_clearance_reported_pass",
            ),
        ):
            with self.subTest(failed_check=failed_check):
                result = audit(rows, final_geometry=value)
                self.assertFalse(result["pass"])
                self.assertFalse(result["checks"][failed_check])

    def test_malformed_window_or_receipt_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "exactly 60 frames"):
            audit([row() for _ in range(TOTAL_SETTLE_STEPS - 1)])
        malformed = [row() for _ in range(TOTAL_SETTLE_STEPS)]
        malformed[-1]["actor_angular_velocity"] = [0.0, 0.0]
        with self.assertRaisesRegex(ValueError, "actor_angular_velocity"):
            audit(malformed)

        receipt = audit([row() for _ in range(TOTAL_SETTLE_STEPS)])
        tampered = copy.deepcopy(receipt)
        tampered["warmup_steps"] = 11
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f2_inside_pre_release_settle_receipt_v6(tampered)


if __name__ == "__main__":
    unittest.main()
