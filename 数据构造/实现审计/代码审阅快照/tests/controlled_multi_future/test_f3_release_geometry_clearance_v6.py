import copy
import json
import unittest

import numpy as np

from controlled_multi_future.f3_release_geometry_clearance_v6 import (
    FROZEN_ASSEMBLY_CONSERVATIVE_MARGIN_M,
    FROZEN_FULL_ASSEMBLY_LINK_NAMES,
    FROZEN_GEOMETRIC_CLEARANCE_M,
    FROZEN_H_NOMINAL_AMPLITUDE_M,
    FROZEN_PROGRAMS,
    FROZEN_V_NOMINAL_AMPLITUDE_M,
    MODEL13_MODEL_DATA_SHA256,
    MODEL13_MODEL_DATA_CENTER,
    MODEL13_MODEL_DATA_EXTENTS,
    MODEL13_MODEL_DATA_SCALE,
    build_f3_release_geometry_clearance_v6,
    build_runtime_live_release_geometry_audit_v6,
    build_target_specific_full_assembly_projection_v6,
    canonical_json_sha256,
    model13_world_obb_z_bounds,
    validate_f3_release_geometry_clearance_v6,
    validate_runtime_live_release_geometry_audit_v6,
    validate_target_specific_full_assembly_projection_v6,
)


ORIGINAL_ACTOR_POSE = [
    -0.1849084049463272,
    -0.05993383005261421,
    0.7838152647018433,
    0.07213852554559708,
    0.0003441395238041878,
    0.9973942637443542,
    -0.0009695073240436614,
]
UNSHIFTED_RELEASE_EEF_POSE = [
    -0.21261061788325517,
    0.06276208597856583,
    0.9069758943310953,
    0.5514765593257213,
    -0.550108878739883,
    0.4399517137741321,
    0.446873937025888,
]


class F3ReleaseGeometryClearanceV6Test(unittest.TestCase):
    @staticmethod
    def assembly_links(*, fl6_z=0.82):
        return {
            "fl_link6": [0.0, 0.0, fl6_z, 1.0, 0.0, 0.0, 0.0],
            "fl_link7": [0.03, 0.0, 0.86, 1.0, 0.0, 0.0, 0.0],
            "fl_link8": [-0.03, 0.0, 0.87, 1.0, 0.0, 0.0, 0.0],
        }

    def test_model13_center_aware_shift_produces_true_10mm_gap(self):
        original_min, _ = model13_world_obb_z_bounds(ORIGINAL_ACTOR_POSE)
        self.assertAlmostEqual(original_min, 0.7449425506602794, places=14)
        self.assertAlmostEqual((original_min + 0.010) - 0.750, 0.0049425506602794, places=14)

        receipt = build_f3_release_geometry_clearance_v6(
            original_actor_pose=ORIGINAL_ACTOR_POSE,
            unshifted_release_eef_pose=UNSHIFTED_RELEASE_EEF_POSE,
            support_top_z_m=0.750,
            gripper_assembly_below_eef_m=0.120,
        )
        self.assertTrue(receipt["pass"])
        self.assertEqual(receipt["selected_shift_source"], "bottle_obb")
        self.assertAlmostEqual(
            receipt["bottle_required_world_z_shift_m"],
            0.0150574493397206,
            places=14,
        )
        self.assertAlmostEqual(
            receipt["selected_world_z_shift_m"],
            0.0150574493397206,
            places=14,
        )
        self.assertAlmostEqual(
            receipt["predicted_bottle_clearance_m"],
            FROZEN_GEOMETRIC_CLEARANCE_M,
            places=14,
        )
        self.assertEqual(receipt["model_data_sha256"], MODEL13_MODEL_DATA_SHA256)

    def test_assembly_requirement_can_only_raise_the_uniform_shift(self):
        bottle_dominant = build_f3_release_geometry_clearance_v6(
            original_actor_pose=ORIGINAL_ACTOR_POSE,
            unshifted_release_eef_pose=UNSHIFTED_RELEASE_EEF_POSE,
            support_top_z_m=0.750,
            gripper_assembly_below_eef_m=0.120,
        )
        assembly_dominant = build_f3_release_geometry_clearance_v6(
            original_actor_pose=ORIGINAL_ACTOR_POSE,
            unshifted_release_eef_pose=UNSHIFTED_RELEASE_EEF_POSE,
            support_top_z_m=0.750,
            gripper_assembly_below_eef_m=0.180,
        )
        self.assertEqual(
            assembly_dominant["selected_shift_source"],
            "gripper_assembly_envelope",
        )
        self.assertGreater(
            assembly_dominant["selected_world_z_shift_m"],
            bottle_dominant["selected_world_z_shift_m"],
        )
        self.assertAlmostEqual(
            assembly_dominant["predicted_assembly_clearance_m"],
            FROZEN_GEOMETRIC_CLEARANCE_M,
            places=14,
        )

    def test_only_common_world_z_changes_and_v_h_contract_is_frozen(self):
        receipt = build_f3_release_geometry_clearance_v6(
            original_actor_pose=ORIGINAL_ACTOR_POSE,
            unshifted_release_eef_pose=UNSHIFTED_RELEASE_EEF_POSE,
            support_top_z_m=0.750,
            gripper_assembly_below_eef_m=0.120,
        )
        actor = np.asarray(receipt["release_actor_pose"])
        eef = np.asarray(receipt["release_eef_pose"])
        original_actor = np.asarray(ORIGINAL_ACTOR_POSE)
        original_eef = np.asarray(UNSHIFTED_RELEASE_EEF_POSE)
        np.testing.assert_array_equal(
            actor[[0, 1, 3, 4, 5, 6]],
            original_actor[[0, 1, 3, 4, 5, 6]],
        )
        np.testing.assert_array_equal(
            eef[[0, 1, 3, 4, 5, 6]],
            original_eef[[0, 1, 3, 4, 5, 6]],
        )
        self.assertEqual(
            actor[2] - original_actor[2], eef[2] - original_eef[2]
        )
        invariants = receipt["scientific_invariants"]
        self.assertEqual(invariants["programs"], list(FROZEN_PROGRAMS))
        self.assertEqual(
            invariants["v_nominal_amplitude_m"],
            FROZEN_V_NOMINAL_AMPLITUDE_M,
        )
        self.assertEqual(
            invariants["h_nominal_amplitude_m"],
            FROZEN_H_NOMINAL_AMPLITUDE_M,
        )
        self.assertFalse(invariants["v_h_targets_changed"])
        self.assertFalse(invariants["event_order_changed"])

    def test_receipt_is_strict_json_self_hashed_and_tamper_evident(self):
        receipt = build_f3_release_geometry_clearance_v6(
            original_actor_pose=ORIGINAL_ACTOR_POSE,
            unshifted_release_eef_pose=UNSHIFTED_RELEASE_EEF_POSE,
            support_top_z_m=0.750,
            gripper_assembly_below_eef_m=0.120,
        )
        json.dumps(receipt, allow_nan=False)
        digest = receipt["receipt_sha256"]
        unsigned = dict(receipt)
        unsigned.pop("receipt_sha256")
        self.assertEqual(digest, canonical_json_sha256(unsigned))
        self.assertEqual(
            validate_f3_release_geometry_clearance_v6(receipt), receipt
        )
        tampered = copy.deepcopy(receipt)
        tampered["selected_world_z_shift_m"] += 0.001
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f3_release_geometry_clearance_v6(tampered)

    def test_nonfinite_zero_quaternion_and_negative_envelope_fail_closed(self):
        common = {
            "original_actor_pose": ORIGINAL_ACTOR_POSE,
            "unshifted_release_eef_pose": UNSHIFTED_RELEASE_EEF_POSE,
            "support_top_z_m": 0.750,
            "gripper_assembly_below_eef_m": 0.120,
        }
        for key, value in (
            ("support_top_z_m", np.nan),
            ("gripper_assembly_below_eef_m", -0.001),
        ):
            changed = dict(common)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                build_f3_release_geometry_clearance_v6(**changed)
        changed = dict(common)
        changed["original_actor_pose"] = [0, 0, 0, 0, 0, 0, 0]
        with self.assertRaisesRegex(ValueError, "quaternion"):
            build_f3_release_geometry_clearance_v6(**changed)

    def test_target_specific_projection_includes_fl6_and_is_quaternion_sensitive(self):
        current_eef = [0, 0, 1.0, 1, 0, 0, 0]
        identity = build_target_specific_full_assembly_projection_v6(
            current_eef_pose=current_eef,
            live_assembly_link_poses=self.assembly_links(),
            release_eef_pose=[0, 0, 1.1, 1, 0, 0, 0],
        )
        self.assertEqual(
            identity["assembly_link_names"],
            list(FROZEN_FULL_ASSEMBLY_LINK_NAMES),
        )
        self.assertEqual(identity["lowest_link_name"], "fl_link6")
        self.assertAlmostEqual(
            identity["predicted_assembly_lowest_z_m"],
            0.89,
        )

        angle = np.pi / 2.0
        rotated = build_target_specific_full_assembly_projection_v6(
            current_eef_pose=current_eef,
            live_assembly_link_poses=self.assembly_links(),
            release_eef_pose=[
                0,
                0,
                1.1,
                np.cos(angle / 2.0),
                0.0,
                np.sin(angle / 2.0),
                0.0,
            ],
        )
        self.assertNotEqual(
            rotated["predicted_assembly_lowest_z_m"],
            identity["predicted_assembly_lowest_z_m"],
        )
        self.assertEqual(
            validate_target_specific_full_assembly_projection_v6(rotated),
            rotated,
        )
        missing = self.assembly_links()
        missing.pop("fl_link6")
        with self.assertRaisesRegex(ValueError, "exactly fl_link6"):
            build_target_specific_full_assembly_projection_v6(
                current_eef_pose=current_eef,
                live_assembly_link_poses=missing,
                release_eef_pose=current_eef,
            )

    def test_runtime_audit_uses_live_links_support_and_model_config(self):
        planning = build_f3_release_geometry_clearance_v6(
            original_actor_pose=ORIGINAL_ACTOR_POSE,
            unshifted_release_eef_pose=UNSHIFTED_RELEASE_EEF_POSE,
            support_top_z_m=0.750,
            gripper_assembly_below_eef_m=0.120,
        )
        live_actor = planning["release_actor_pose"]
        live_eef = planning["release_eef_pose"]
        links = {
            "fl_link6": [0.0, 0.0, 0.80, 1.0, 0.0, 0.0, 0.0],
            "fl_link7": [0.03, 0.0, 0.81, 1.0, 0.0, 0.0, 0.0],
            "fl_link8": [-0.03, 0.0, 0.82, 1.0, 0.0, 0.0, 0.0],
        }
        audit = build_runtime_live_release_geometry_audit_v6(
            planning_clearance_receipt=planning,
            live_actor_pose=live_actor,
            live_release_eef_pose=live_eef,
            live_assembly_link_poses=links,
            live_support_top_z_m=0.750,
            live_model_center=MODEL13_MODEL_DATA_CENTER,
            live_model_extents=MODEL13_MODEL_DATA_EXTENTS,
            live_model_scale=MODEL13_MODEL_DATA_SCALE,
            conservative_margin_m=0.0,
        )
        self.assertTrue(audit["pass"])
        self.assertEqual(
            validate_runtime_live_release_geometry_audit_v6(audit), audit
        )

        wrong_scale = build_runtime_live_release_geometry_audit_v6(
            planning_clearance_receipt=planning,
            live_actor_pose=live_actor,
            live_release_eef_pose=live_eef,
            live_assembly_link_poses=links,
            live_support_top_z_m=0.750,
            live_model_center=MODEL13_MODEL_DATA_CENTER,
            live_model_extents=MODEL13_MODEL_DATA_EXTENTS,
            live_model_scale=[0.133, 0.132, 0.132],
            conservative_margin_m=0.0,
        )
        self.assertFalse(wrong_scale["pass"])
        self.assertFalse(
            wrong_scale["checks"]["live_model13_half_extents_match_frozen"]
        )

        wrong_support = build_runtime_live_release_geometry_audit_v6(
            planning_clearance_receipt=planning,
            live_actor_pose=live_actor,
            live_release_eef_pose=live_eef,
            live_assembly_link_poses=links,
            live_support_top_z_m=0.751,
            live_model_center=MODEL13_MODEL_DATA_CENTER,
            live_model_extents=MODEL13_MODEL_DATA_EXTENTS,
            live_model_scale=MODEL13_MODEL_DATA_SCALE,
            conservative_margin_m=0.0,
        )
        self.assertFalse(wrong_support["pass"])
        self.assertFalse(
            wrong_support["checks"]["live_support_top_matches_planning"]
        )

    def test_projection_and_runtime_receipts_are_tamper_evident(self):
        projection = build_target_specific_full_assembly_projection_v6(
            current_eef_pose=[0, 0, 1, 1, 0, 0, 0],
            live_assembly_link_poses=self.assembly_links(),
            release_eef_pose=[0, 0, 1.1, 1, 0, 0, 0],
            conservative_margin_m=FROZEN_ASSEMBLY_CONSERVATIVE_MARGIN_M,
        )
        changed = copy.deepcopy(projection)
        changed["predicted_assembly_lowest_z_m"] += 0.001
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_target_specific_full_assembly_projection_v6(changed)


if __name__ == "__main__":
    unittest.main()
