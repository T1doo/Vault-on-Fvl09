import copy
import hashlib
import json
import unittest

import numpy as np

from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT
from controlled_multi_future.f4_json_canonicalization_v9 import (
    CANONICALIZATION_VERSION as JSON_CANONICALIZATION_VERSION,
    json_safe_clone_v9,
)
from controlled_multi_future.f4_top_down_block_carry_v8 import (
    FROZEN_LAYOUT_SHA256,
    R7_MICRO_ACCEPTED_EVIDENCE,
    build_f4_top_down_block_carry_v8,
    validate_f4_top_down_block_carry_v8,
)
from controlled_multi_future.f4_top_down_clearance_v6 import (
    build_uniform_f4_top_down_clearance_contract_v6,
)
from controlled_multi_future.f4_uniform_block_carry_midpoint_v3 import (
    F4_ALLOWED_OBJECT_ORDERS,
    F4_SEGMENTED_BLOCK_SUFFIXES,
    build_uniform_carry_midpoint,
)
from controlled_multi_future.geometry import compose_pose


NEUTRAL = [
    0.24287901030859585,
    -0.018903042090389933,
    0.981401726222435,
    0.5243493205275805,
    -0.4743960933174202,
    0.47440145961494534,
    0.5243561688610553,
]


def build(order=("A", "B", "C")):
    return build_f4_top_down_block_carry_v8(
        object_poses=copy.deepcopy(LAYOUT["object_poses"]),
        slot_poses=copy.deepcopy(LAYOUT["slot_poses"]),
        neutral_pose=copy.deepcopy(NEUTRAL),
        object_order=order,
        arm="right",
        layout_version=LAYOUT["layout_version"],
    )


class F4TopDownBlockCarryV8Test(unittest.TestCase):
    def test_only_abc_acb_bac_and_exact_seven_segment_ids(self):
        for order in F4_ALLOWED_OBJECT_ORDERS:
            with self.subTest(order=order):
                receipt = build(order)
                self.assertTrue(receipt["pass"])
                self.assertEqual(receipt["object_order"], list(order))
                self.assertEqual(len(receipt["object_target_groups"]), 3)
                self.assertEqual(len(receipt["flattened_targets"]), 21)
                for group, role in zip(receipt["object_target_groups"], order):
                    self.assertEqual(group["role"], role)
                    self.assertEqual(
                        [item["segment_id"] for item in group["targets"]],
                        [f"{role}_{suffix}" for suffix in F4_SEGMENTED_BLOCK_SUFFIXES],
                    )
        for bad in (("A", "B"), ("A", "B", "C", "A"), ("C", "B", "A")):
            with self.assertRaisesRegex(ValueError, "only ABC, ACB, or BAC"):
                build(bad)

    def test_first_three_targets_reuse_r6_topdown_contract_for_all_roles(self):
        receipt = build()
        r6 = build_uniform_f4_top_down_clearance_contract_v6(
            object_poses=LAYOUT["object_poses"], arm="right"
        )
        source = {group["role"]: group for group in r6["groups"]}
        for group in receipt["object_target_groups"]:
            role = group["role"]
            expected = source[role]["targets"]
            actual = group["targets"]
            np.testing.assert_array_equal(actual[0]["pose"], expected[0]["pose"])
            np.testing.assert_array_equal(actual[1]["pose"], expected[1]["pose"])
            np.testing.assert_array_equal(actual[2]["pose"], expected[2]["pose"])
            self.assertEqual(group["lift_pose_source"], f"{role}_micro_lift")
            self.assertTrue(group["checks"]["exact_20mm_lift_actor_delta"])

    def test_frozen_grasp_mapping_reconstructs_same_object_slot_target(self):
        receipt = build()
        for group in receipt["object_target_groups"]:
            role = group["role"]
            release = np.asarray(group["targets"][5]["pose"], dtype=np.float64)
            eef_to_actor = np.asarray(
                group["frozen_eef_to_actor_pose"], dtype=np.float64
            )
            reconstructed = compose_pose(release, eef_to_actor)
            target = np.asarray(group["target_actor_pose"], dtype=np.float64)
            slot = np.asarray(LAYOUT["slot_poses"][role], dtype=np.float64)
            np.testing.assert_allclose(reconstructed[:3], target[:3], atol=1e-12)
            self.assertLess(
                quaternion_angular_error(reconstructed[3:], target[3:]), 1e-12
            )
            np.testing.assert_allclose(
                target[:3], slot[:3] + [0.0, 0.0, 0.022], atol=1e-12
            )
            np.testing.assert_allclose(
                target[3:], LAYOUT["object_poses"][role][3:], atol=1e-12
            )
            self.assertTrue(
                group["checks"]["target_actor_position_reconstructed"]
            )
            self.assertTrue(
                group["checks"]["target_actor_orientation_reconstructed"]
            )

    def test_existing_midpoint_and_same_neutral_are_reused_uniformly(self):
        receipt = build(("A", "C", "B"))
        for group in receipt["object_target_groups"]:
            targets = group["targets"]
            expected_mid, audit = build_uniform_carry_midpoint(
                targets[2]["pose"], targets[4]["pose"]
            )
            np.testing.assert_array_equal(targets[3]["pose"], expected_mid)
            np.testing.assert_array_equal(targets[6]["pose"], NEUTRAL)
            self.assertEqual(audit["midpoint_xy_fraction"], 0.5)
            self.assertEqual(group["midpoint_audit"]["z_policy"], "max(lift_z,preplace_z)")
            self.assertFalse(group["role_specific_condition"])

    def test_nominal_table_and_order_aware_noninterference_pass_all_programs(self):
        for order in F4_ALLOWED_OBJECT_ORDERS:
            receipt = build(order)
            audit = receipt["nominal_noninterference_audit"]
            self.assertTrue(audit["pass"])
            self.assertTrue(audit["nominal_only"])
            self.assertTrue(audit["runtime_whole_robot_collision_required"])
            self.assertTrue(audit["runtime_contact_noninterference_required"])
            self.assertAlmostEqual(
                audit["minimum_transport_bottom_clearance_m"], 0.02
            )
            self.assertAlmostEqual(
                audit["minimum_release_bottom_above_table_m"], 0.002
            )
            for role in order:
                role_audit = audit["per_role"][role]
                self.assertTrue(role_audit["pass"])
                self.assertEqual(
                    role_audit["segment_non_target_collisions"],
                    {"lift_to_carry_mid": [], "carry_mid_to_preplace": []},
                )

    def test_uniform_right_arm_contract_has_no_role_exception_or_layout_change(self):
        receipt = build(("B", "A", "C"))
        hashes = {
            group["r6_top_down_grasp_contract"]["grasp_contract_sha256"]
            for group in receipt["object_target_groups"]
        }
        self.assertEqual(len(hashes), 1)
        self.assertEqual(receipt["arm"], "right")
        self.assertFalse(receipt["role_specific_condition"])
        self.assertFalse(receipt["scene_layout_changed"])
        self.assertFalse(receipt["target_object_slot_mapping_changed"])
        self.assertFalse(receipt["executing_arm_changed"])
        self.assertFalse(receipt["common_prefix_changed"])
        self.assertFalse(receipt["neutral_pose_changed"])
        self.assertFalse(receipt["program_changed"])
        self.assertFalse(receipt["verifier_changed"])
        self.assertFalse(receipt["candidate_search"])
        self.assertFalse(receipt["fallback"])
        with self.assertRaisesRegex(ValueError, "right arm"):
            build_f4_top_down_block_carry_v8(
                object_poses=LAYOUT["object_poses"],
                slot_poses=LAYOUT["slot_poses"],
                neutral_pose=NEUTRAL,
                object_order=("A", "B", "C"),
                arm="left",
            )

    def test_r7_a_micro_accepted_evidence_and_frozen_layout_are_bound(self):
        receipt = build()
        evidence = receipt["source_evidence"]
        self.assertEqual(evidence, R7_MICRO_ACCEPTED_EVIDENCE)
        self.assertEqual(
            evidence["evidence_tree_sha256"],
            "5139caa8e5c63e75fc6b926c18c74acd9e2fa5846a870860e97b6ea6a6f4d1df",
        )
        self.assertEqual(
            evidence["gate_receipt_file_sha256"],
            "034a4de726e49e64a4818c77cd768cfc900eb68349a39e5dbab34865fbb1f5f3",
        )
        self.assertEqual(evidence["actor_rise_m"], 0.017215192317962646)
        self.assertEqual(evidence["selected_contact_fraction"], 1.0)
        self.assertEqual(evidence["selected_contact_break_count"], 0)
        self.assertEqual(evidence["minimum_selected_contact_count"], 2)
        self.assertEqual(receipt["frozen_layout_sha256"], FROZEN_LAYOUT_SHA256)
        self.assertEqual(FROZEN_LAYOUT_SHA256, hash_json(LAYOUT))
        self.assertIn("A top-down micro-lift only", receipt["evidence_scope_boundary"])

    def test_inputs_are_not_mutated_and_receipt_tamper_fails_closed(self):
        objects = copy.deepcopy(LAYOUT["object_poses"])
        slots = copy.deepcopy(LAYOUT["slot_poses"])
        neutral = copy.deepcopy(NEUTRAL)
        before = copy.deepcopy((objects, slots, neutral))
        receipt = build_f4_top_down_block_carry_v8(
            object_poses=objects,
            slot_poses=slots,
            neutral_pose=neutral,
            object_order=("A", "B", "C"),
        )
        self.assertEqual((objects, slots, neutral), before)
        json.dumps(receipt, ensure_ascii=False, allow_nan=False)
        self.assertEqual(validate_f4_top_down_block_carry_v8(receipt), receipt)

        tampered = copy.deepcopy(receipt)
        tampered["object_target_groups"][0]["targets"][3]["pose"][0] += 0.01
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f4_top_down_block_carry_v8(tampered)

        rehashed = copy.deepcopy(receipt)
        rehashed.pop("receipt_sha256")
        rehashed["source_evidence"]["evidence_file_count"] = 18
        payload = json.dumps(
            rehashed,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        rehashed["receipt_sha256"] = hashlib.sha256(payload).hexdigest()
        with self.assertRaisesRegex(ValueError, "evidence binding"):
            validate_f4_top_down_block_carry_v8(rehashed)

    def test_real_staged_callback_numpy_shapes_are_json_safe_and_identical(self):
        objects = {
            role: np.asarray(pose, dtype=np.float64)
            for role, pose in LAYOUT["object_poses"].items()
        }
        slots = {
            role: np.asarray(pose, dtype=np.float64)
            for role, pose in LAYOUT["slot_poses"].items()
        }
        neutral = np.asarray(NEUTRAL, dtype=np.float64)
        before_objects = {role: value.copy() for role, value in objects.items()}
        before_slots = {role: value.copy() for role, value in slots.items()}
        before_neutral = neutral.copy()

        numpy_receipt = build_f4_top_down_block_carry_v8(
            object_poses=objects,
            slot_poses=slots,
            neutral_pose=neutral,
            object_order=np.asarray(["A", "B", "C"]),
            arm="right",
            layout_version=LAYOUT["layout_version"],
        )
        list_receipt = build(("A", "B", "C"))

        self.assertEqual(numpy_receipt, list_receipt)
        self.assertEqual(
            numpy_receipt["json_canonicalization_version"],
            JSON_CANONICALIZATION_VERSION,
        )
        self.assertEqual(validate_f4_top_down_block_carry_v8(numpy_receipt), numpy_receipt)
        json.dumps(numpy_receipt, ensure_ascii=False, allow_nan=False)
        for role in objects:
            np.testing.assert_array_equal(objects[role], before_objects[role])
            np.testing.assert_array_equal(slots[role], before_slots[role])
        np.testing.assert_array_equal(neutral, before_neutral)

    def test_numpy_scalars_are_canonicalized_and_nonfinite_values_fail_closed(self):
        value = json_safe_clone_v9(
            {
                "float": np.float64(0.25),
                "integer": np.int64(3),
                "boolean": np.bool_(True),
                "array": np.asarray([[1.0, 2.0]], dtype=np.float32),
            }
        )
        self.assertEqual(
            value,
            {
                "array": [[1.0, 2.0]],
                "boolean": True,
                "float": 0.25,
                "integer": 3,
            },
        )
        with self.assertRaises(ValueError):
            json_safe_clone_v9({"bad": np.float64(np.nan)})


if __name__ == "__main__":
    unittest.main()
