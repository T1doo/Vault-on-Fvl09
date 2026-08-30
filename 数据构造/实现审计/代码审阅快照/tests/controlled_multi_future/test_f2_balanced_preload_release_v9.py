import copy
import unittest

import numpy as np

from controlled_multi_future.f2_balanced_preload_release_v9 import (
    DISENGAGEMENT_CONFIRM_FRAMES,
    R8_FAILURE_EVIDENCE,
    STABLE_WINDOW_FRAMES,
    audit_f2_balanced_preload_release_gate_v9,
    build_f2_balanced_preload_release_spec_v9,
    canonical_json_sha256,
    validate_f2_balanced_preload_release_spec_v9,
)
from controlled_multi_future.f3_physical_contact_signal_v8 import (
    CONTACT_PAIR_SCHEMA_VERSION,
)


def shape_identity(body_name, index):
    value = {
        "available": True,
        "body_name": body_name,
        "body_collision_shape_index": index,
    }
    value["identity_sha256"] = canonical_json_sha256(value)
    return value


def pair(body_a, body_b, *, physical):
    identities = [shape_identity(body_a, 0), shape_identity(body_b, 0)]
    hashes = [item["identity_sha256"] for item in identities]
    separation = -0.001 if physical else 0.01
    impulse = 0.1 if physical else 0.0
    return {
        "contact_pair_schema_version": CONTACT_PAIR_SCHEMA_VERSION,
        "body_a": body_a,
        "body_b": body_b,
        "point_count": 1,
        "impulse_norm_sum": impulse,
        "impulse_available": True,
        "shape_identity_available": True,
        "shape_identities": identities,
        "point_evidence": [
            {
                "point_index": 0,
                "impulse_norm": impulse,
                "impulse_available": True,
                "signed_separation_m": separation,
                "signed_separation_available": True,
                "shape_identity_available": True,
                "shape_identity_sha256": hashes,
            }
        ],
    }


def rows(*, finger_physical=False, box_physical=True, speed=0.0):
    values = []
    for _ in range(STABLE_WINDOW_FRAMES):
        values.append(
            {
                "actor_linear_velocity": [speed, 0.0, 0.0],
                "actor_angular_velocity": [0.0, 0.0, speed],
                "realized_left_gripper_joint_qpos": [0.024, 0.024],
                "realized_left_gripper_joint_qf": [0.0, 0.0],
                "left_gripper_joint_drive_target_error": [0.0, 0.0],
                "estimated_left_gripper_joint_drive_effort": [0.0, 0.0],
                "contact_pairs": [
                    pair("f2_main_can", "fl_link7", physical=finger_physical),
                    pair("f2_main_can", "f2_plasticbox", physical=box_physical),
                ],
            }
        )
    return values


class F2BalancedPreloadReleaseV9Test(unittest.TestCase):
    def spec(self):
        return build_f2_balanced_preload_release_spec_v9(
            actual_finger_qpos=[0.023580040782690048, 0.021501483395695686],
            current_drive_target=[-0.01, -0.01],
            applied_finger_qf=[1.0, -1.0],
            estimated_drive_effort=[-12.0, -10.0],
            drive_stiffness=[1000.0, 1000.0],
            drive_damping=[100.0, 100.0],
            drive_force_limit=[50.0, 50.0],
            drive_mode=["force", "force"],
        )

    def test_balanced_target_is_single_formula_and_frozen_evidence_bound(self):
        receipt = self.spec()
        expected = np.mean([0.023580040782690048, 0.021501483395695686])
        self.assertEqual(receipt["balanced_drive_target_m"], expected)
        self.assertEqual(
            receipt["partial_open_normalized_target"],
            (expected + 0.01) / 0.055,
        )
        self.assertEqual(
            receipt["expected_balanced_joint_targets_m"],
            [expected, expected],
        )
        self.assertEqual(receipt["source_evidence"], R8_FAILURE_EVIDENCE)
        self.assertFalse(receipt["candidate_search"])
        self.assertFalse(receipt["fallback"])
        self.assertFalse(receipt["desired_actor_target_changed"])
        self.assertEqual(
            validate_f2_balanced_preload_release_spec_v9(receipt), receipt
        )

    def test_tamper_and_nonfinite_inputs_fail_closed(self):
        tampered = copy.deepcopy(self.spec())
        tampered["partial_open_normalized_target"] += 0.01
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f2_balanced_preload_release_spec_v9(tampered)
        with self.assertRaisesRegex(ValueError, "finite"):
            build_f2_balanced_preload_release_spec_v9(
                actual_finger_qpos=[np.nan, 0.02],
                current_drive_target=[0.0, 0.0],
                applied_finger_qf=[0.0, 0.0],
                estimated_drive_effort=[0.0, 0.0],
                drive_stiffness=[1.0, 1.0],
                drive_damping=[1.0, 1.0],
                drive_force_limit=[1.0, 1.0],
                drive_mode=["force", "force"],
            )
        with self.assertRaisesRegex(ValueError, "force mode"):
            build_f2_balanced_preload_release_spec_v9(
                actual_finger_qpos=[0.02, 0.02],
                current_drive_target=[0.0, 0.0],
                applied_finger_qf=[0.0, 0.0],
                estimated_drive_effort=[0.0, 0.0],
                drive_stiffness=[1.0, 1.0],
                drive_damping=[1.0, 1.0],
                drive_force_limit=[1.0, 1.0],
                drive_mode=["acceleration", "acceleration"],
            )

    def test_full_open_requires_inside_stable_support_and_disengagement(self):
        receipt = audit_f2_balanced_preload_release_gate_v9(
            rows(),
            can_actor_name="f2_main_can",
            selected_finger_link_names=("fl_link7", "fl_link8"),
            box_actor_name="f2_plasticbox",
            true_cavity_obb_pass=True,
        )
        self.assertTrue(receipt["pass"])
        self.assertTrue(receipt["full_open_allowed"])
        self.assertEqual(
            len(receipt["finger_contact_confirm_window"]),
            DISENGAGEMENT_CONFIRM_FRAMES,
        )

        cases = (
            (rows(finger_physical=True), True),
            (rows(box_physical=False), True),
            (rows(speed=0.1), True),
            (rows(), False),
        )
        for value, inside in cases:
            with self.subTest(inside=inside):
                failed = audit_f2_balanced_preload_release_gate_v9(
                    value,
                    can_actor_name="f2_main_can",
                    selected_finger_link_names=("fl_link7", "fl_link8"),
                    box_actor_name="f2_plasticbox",
                    true_cavity_obb_pass=inside,
                )
                self.assertFalse(failed["pass"])
                self.assertFalse(failed["full_open_allowed"])

    def test_missing_contact_signal_fails_closed(self):
        value = rows()
        value[-1]["contact_pairs"][1]["point_evidence"][0][
            "signed_separation_available"
        ] = False
        receipt = audit_f2_balanced_preload_release_gate_v9(
            value,
            can_actor_name="f2_main_can",
            selected_finger_link_names=("fl_link7", "fl_link8"),
            box_actor_name="f2_plasticbox",
            true_cavity_obb_pass=True,
        )
        self.assertFalse(receipt["pass"])


if __name__ == "__main__":
    unittest.main()
