import copy
import unittest

import numpy as np

from controlled_multi_future.f3_physical_contact_signal_v8 import (
    CONTACT_PAIR_SCHEMA_VERSION,
)
from controlled_multi_future.f3_symmetric_staged_release_v9 import (
    DISENGAGEMENT_CONFIRM_FRAMES,
    DISENGAGEMENT_DELTA_NORMALIZED,
    R8_FAILURE_EVIDENCE,
    STABLE_WINDOW_FRAMES,
    audit_f3_symmetric_staged_release_gate_v9,
    build_f3_symmetric_staged_release_spec_v9,
    canonical_json_sha256,
    validate_f3_symmetric_staged_release_spec_v9,
)


def identity(body_name, index):
    value = {
        "available": True,
        "body_name": body_name,
        "body_collision_shape_index": index,
    }
    value["identity_sha256"] = canonical_json_sha256(value)
    return value


def pair(body_a, body_b, *, physical):
    identities = [identity(body_a, 0), identity(body_b, 0)]
    hashes = [value["identity_sha256"] for value in identities]
    impulse = 0.1 if physical else 0.0
    separation = -0.001 if physical else 0.01
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


def rows(*, assembly_physical=False, pad_physical=True, speed=0.0):
    return [
        {
            "actor_linear_velocity": [speed, 0.0, 0.0],
            "actor_angular_velocity": [0.0, speed, 0.0],
            "realized_left_gripper_joint_qpos": [0.041, 0.041],
            "realized_left_gripper_joint_qf": [0.0, 0.0],
            "left_gripper_joint_drive_target_error": [0.0, 0.0],
            "estimated_left_gripper_joint_drive_effort": [0.0, 0.0],
            "contact_pairs": [
                pair("f3_main_bottle", "fl_link7", physical=assembly_physical),
                pair("f3_main_bottle", "f3_original_pad", physical=pad_physical),
            ],
        }
        for _ in range(STABLE_WINDOW_FRAMES)
    ]


class F3SymmetricStagedReleaseV9Test(unittest.TestCase):
    def spec(self):
        return build_f3_symmetric_staged_release_spec_v9(
            actual_finger_qpos=[0.03316526487469673, 0.03046014904975891],
            current_drive_target=[-0.01, -0.01],
            applied_finger_qf=[1.0, -1.0],
            estimated_drive_effort=[-12.0, -10.0],
            drive_stiffness=[1000.0, 1000.0],
            drive_damping=[100.0, 100.0],
            drive_force_limit=[50.0, 50.0],
            drive_mode=["force", "force"],
        )

    def test_single_evidence_derived_staged_formula_and_frozen_invariants(self):
        receipt = self.spec()
        balanced_m = np.mean([0.03316526487469673, 0.03046014904975891])
        balanced = (balanced_m + 0.01) / 0.055
        self.assertEqual(receipt["balanced_normalized_target"], balanced)
        self.assertEqual(
            receipt["disengagement_normalized_target"],
            balanced + DISENGAGEMENT_DELTA_NORMALIZED,
        )
        self.assertEqual(receipt["source_evidence"], R8_FAILURE_EVIDENCE)
        self.assertFalse(receipt["candidate_search"])
        self.assertFalse(receipt["pad_changed"])
        self.assertFalse(receipt["physics_changed"])
        self.assertFalse(receipt["VH_axis_or_program_changed"])
        self.assertEqual(
            validate_f3_symmetric_staged_release_spec_v9(receipt), receipt
        )

    def test_tamper_and_nonfinite_input_fail_closed(self):
        receipt = copy.deepcopy(self.spec())
        receipt["disengagement_normalized_target"] += 0.01
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f3_symmetric_staged_release_spec_v9(receipt)
        with self.assertRaisesRegex(ValueError, "finite"):
            build_f3_symmetric_staged_release_spec_v9(
                actual_finger_qpos=[np.nan, 0.03],
                current_drive_target=[0.0, 0.0],
                applied_finger_qf=[0.0, 0.0],
                estimated_drive_effort=[0.0, 0.0],
                drive_stiffness=[1.0, 1.0],
                drive_damping=[1.0, 1.0],
                drive_force_limit=[1.0, 1.0],
                drive_mode=["force", "force"],
            )
        with self.assertRaisesRegex(ValueError, "force mode"):
            build_f3_symmetric_staged_release_spec_v9(
                actual_finger_qpos=[0.03, 0.03],
                current_drive_target=[0.0, 0.0],
                applied_finger_qf=[0.0, 0.0],
                estimated_drive_effort=[0.0, 0.0],
                drive_stiffness=[1.0, 1.0],
                drive_damping=[1.0, 1.0],
                drive_force_limit=[1.0, 1.0],
                drive_mode=["acceleration", "acceleration"],
            )

    def test_full_open_requires_frozen_return_support_stability_and_disengagement(self):
        receipt = audit_f3_symmetric_staged_release_gate_v9(
            rows(),
            bottle_actor_name="f3_main_bottle",
            gripper_assembly_link_names=("fl_link6", "fl_link7", "fl_link8"),
            pad_actor_name="f3_original_pad",
            bottle_position_error_m=0.003,
            bottle_orientation_error_rad=0.01,
            footprint_inside_pad=True,
        )
        self.assertTrue(receipt["pass"])
        self.assertEqual(
            len(receipt["assembly_contact_confirm_window"]),
            DISENGAGEMENT_CONFIRM_FRAMES,
        )
        cases = (
            dict(value=rows(assembly_physical=True)),
            dict(value=rows(pad_physical=False)),
            dict(value=rows(speed=0.1)),
            dict(value=rows(), orientation=0.1),
            dict(value=rows(), footprint=False),
        )
        for case in cases:
            failed = audit_f3_symmetric_staged_release_gate_v9(
                case["value"],
                bottle_actor_name="f3_main_bottle",
                gripper_assembly_link_names=("fl_link6", "fl_link7", "fl_link8"),
                pad_actor_name="f3_original_pad",
                bottle_position_error_m=0.003,
                bottle_orientation_error_rad=case.get("orientation", 0.01),
                footprint_inside_pad=case.get("footprint", True),
            )
            self.assertFalse(failed["pass"])
            self.assertFalse(failed["full_open_allowed"])


if __name__ == "__main__":
    unittest.main()
