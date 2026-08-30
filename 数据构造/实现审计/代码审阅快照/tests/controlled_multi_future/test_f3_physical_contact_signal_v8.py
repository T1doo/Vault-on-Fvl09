import copy
import inspect
import json
import unittest

from controlled_multi_future.f3_physical_contact_signal_v8 import (
    CONTACT_PAIR_SCHEMA_VERSION,
    NONZERO_CONTACT_IMPULSE_EPS,
    canonical_json_sha256,
    classify_contact_pair_physical_hit_v8,
    classify_f3_preopen_support_contacts_v8,
    validate_contact_pair_physical_hit_v8,
    validate_f3_physical_contact_signal_v8,
)
from controlled_multi_future.f3_return_release_v5 import (
    PRE_OPEN_STABLE_FRAMES,
    build_pre_open_gate_v5,
)
from controlled_multi_future.family_runners_v3_3 import F3ControllerV3_3


def shape_identity(body_name, index):
    value = {
        "available": True,
        "body_name": body_name,
        "body_collision_shape_index": index,
        "shape_type": "FakeShape",
        "local_pose": [0, 0, 0, 1, 0, 0, 0],
        "collision_groups": [1, 1, 0, index],
        "contact_offset_m": 0.02,
        "rest_offset_m": 0.0,
        "identity_source": "test",
    }
    value["identity_sha256"] = canonical_json_sha256(value)
    return value


def contact_pair(
    body_a,
    body_b,
    *,
    separation=0.01,
    impulse=0.0,
    separation_available=True,
    shape_available=True,
    schema=True,
    impulse_available=True,
):
    identities = [
        shape_identity(body_a, 0),
        shape_identity(body_b, 0),
    ]
    shape_hashes = [item["identity_sha256"] for item in identities]
    return {
        "contact_pair_schema_version": CONTACT_PAIR_SCHEMA_VERSION
        if schema
        else None,
        "body_a": body_a,
        "body_b": body_b,
        "point_count": 1,
        "impulse_norm_sum": impulse,
        "impulse_available": impulse_available,
        "shape_identity_available": shape_available,
        "shape_identities": identities if shape_available else [],
        "point_evidence": [
            {
                "point_index": 0,
                "impulse_norm": impulse if impulse_available else None,
                "impulse_available": impulse_available,
                "signed_separation_m": separation
                if separation_available
                else None,
                "signed_separation_available": separation_available,
                "shape_identity_available": shape_available,
                "shape_identity_sha256": shape_hashes
                if shape_available
                else [],
            }
        ],
    }


def classify(frames):
    return classify_f3_preopen_support_contacts_v8(
        frames,
        bottle_actor_name="f3_main_bottle",
        gripper_assembly_link_names=("fl_link6", "fl_link7", "fl_link8"),
        support_actor_names=("table", "f3_original_pad"),
    )


class F3PhysicalContactSignalV8Test(unittest.TestCase):
    def test_runner_uses_physical_helper_for_disengagement_and_recontact(self):
        source = inspect.getsource(
            F3ControllerV3_3.execute_frozen_suffix_spec
        )
        self.assertIn("classify_contact_pair_physical_hit_v8", source)
        self.assertIn("def assembly_contact", source)
        self.assertIn("def selected_finger_contact", source)
        self.assertIn(
            "no_selected_finger_recontact_through_250", source
        )
        self.assertIn(
            "no_selected_finger_physical_recontact_through_after_release_250",
            source,
        )
        self.assertIn(
            "no_selected_pair_presence_through_250_audit", source
        )
        self.assertIn(
            "selected_pair_presence_false_at_physical_release_audit_only",
            source,
        )

    def test_r7_like_positive_separation_zero_impulse_is_audit_only(self):
        result = classify(
            [
                [
                    contact_pair(
                        "f3_main_bottle",
                        "f3_original_pad",
                        separation=0.0102,
                        impulse=0.0,
                    ),
                    contact_pair(
                        "fl_link7",
                        "f3_original_pad",
                        separation=0.0116,
                        impulse=0.0,
                    ),
                ]
            ]
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["relevant_pair_count"], 2)
        self.assertEqual(
            len(result["pair_presence_audit"]["bottle_support"]), 1
        )
        self.assertEqual(
            len(result["pair_presence_audit"]["assembly_support"]), 1
        )
        self.assertEqual(
            result["physical_support_hits"],
            {"bottle_support": [], "assembly_support": []},
        )
        self.assertTrue(result["pair_presence_is_audit_only"])

    def test_zero_and_negative_separation_are_physical_contact(self):
        for separation in (0.0, -1e-6):
            with self.subTest(separation=separation):
                result = classify(
                    [
                        [
                            contact_pair(
                                "f3_main_bottle",
                                "f3_original_pad",
                                separation=separation,
                                impulse=0.0,
                            )
                        ]
                    ]
                )
                self.assertFalse(result["pass"])
                self.assertFalse(
                    result["checks"][
                        "bottle_has_no_physical_support_contact"
                    ]
                )
                hit = result["physical_support_hits"]["bottle_support"][0]
                self.assertIn(
                    "nonpositive_signed_separation",
                    hit["physical_contact_reasons"],
                )

    def test_nonzero_impulse_is_physical_contact_at_positive_separation(self):
        boundary = classify(
            [
                [
                    contact_pair(
                        "fl_link7",
                        "f3_original_pad",
                        separation=0.01,
                        impulse=NONZERO_CONTACT_IMPULSE_EPS,
                    )
                ]
            ]
        )
        self.assertTrue(boundary["pass"])
        result = classify(
            [
                [
                    contact_pair(
                        "fl_link7",
                        "f3_original_pad",
                        separation=0.01,
                        impulse=NONZERO_CONTACT_IMPULSE_EPS * 2,
                    )
                ]
            ]
        )
        self.assertFalse(result["pass"])
        hit = result["physical_support_hits"]["assembly_support"][0]
        self.assertIn(
            "impulse_above_epsilon", hit["physical_contact_reasons"]
        )

    def test_missing_impulse_separation_shape_or_schema_fails_closed(self):
        cases = (
            contact_pair(
                "f3_main_bottle",
                "f3_original_pad",
                impulse_available=False,
            ),
            contact_pair(
                "f3_main_bottle",
                "f3_original_pad",
                separation_available=False,
            ),
            contact_pair(
                "f3_main_bottle",
                "f3_original_pad",
                shape_available=False,
            ),
            contact_pair(
                "f3_main_bottle",
                "f3_original_pad",
                schema=False,
            ),
        )
        expected_failed_check = (
            "all_relevant_pair_impulses_available",
            "all_relevant_points_have_signed_separation",
            "all_relevant_points_have_shape_identity",
            "all_relevant_pairs_use_v2_contact_schema",
        )
        for pair, check in zip(cases, expected_failed_check):
            with self.subTest(check=check):
                result = classify([[pair]])
                self.assertFalse(result["pass"])
                self.assertFalse(result["checks"][check])
                self.assertTrue(
                    result["physical_support_hits"]["bottle_support"][0][
                        "physical_contact"
                    ]
                )
                self.assertIn(
                    "signal_unavailable_fail_closed",
                    result["physical_support_hits"]["bottle_support"][0][
                        "physical_contact_reasons"
                    ],
                )

    def test_single_pair_helper_supports_disengagement_and_fails_closed(self):
        released = contact_pair(
            "f3_main_bottle",
            "fl_link7",
            separation=0.002,
            impulse=0.0,
        )
        result = classify_contact_pair_physical_hit_v8(released)
        self.assertTrue(result["evidence_complete"])
        self.assertFalse(result["observed_physical_contact"])
        self.assertFalse(result["physical_hit_for_gate"])
        self.assertEqual(
            validate_contact_pair_physical_hit_v8(result), result
        )

        touching = contact_pair(
            "f3_main_bottle",
            "fl_link7",
            separation=0.002,
            impulse=NONZERO_CONTACT_IMPULSE_EPS * 2,
        )
        self.assertTrue(
            classify_contact_pair_physical_hit_v8(touching)[
                "physical_hit_for_gate"
            ]
        )

        unavailable = contact_pair(
            "f3_main_bottle",
            "fl_link7",
            separation_available=False,
        )
        missing = classify_contact_pair_physical_hit_v8(unavailable)
        self.assertFalse(missing["evidence_complete"])
        self.assertFalse(missing["observed_physical_contact"])
        self.assertTrue(missing["physical_hit_for_gate"])
        self.assertIn(
            "signal_unavailable_fail_closed",
            missing["physical_contact_reasons"],
        )

    def test_receipt_is_json_safe_self_hashed_and_tamper_evident(self):
        result = classify([])
        json.dumps(result, allow_nan=False)
        digest = result["receipt_sha256"]
        unsigned = dict(result)
        unsigned.pop("receipt_sha256")
        self.assertEqual(digest, canonical_json_sha256(unsigned))
        self.assertEqual(
            validate_f3_physical_contact_signal_v8(result), result
        )
        tampered = copy.deepcopy(result)
        tampered["frame_count"] += 1
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f3_physical_contact_signal_v8(tampered)

    @staticmethod
    def preopen_rows(pair):
        return [
            {
                "actor_pose": [0, 0, 1.01, 1, 0, 0, 0],
                "eef": [0, 0, 1.1, 1, 0, 0, 0],
                "eef_linear_velocity": [0, 0, 0],
                "eef_angular_velocity": [0, 0, 0],
                "actor_linear_velocity": [0, 0, 0],
                "actor_angular_velocity": [0, 0, 0],
                "selected_gripper_contact": True,
                "selected_contact_actor_name": "f3_main_bottle",
                "realized_left_gripper_joint_qpos": [0.032, 0.031],
                "gripper_command": [0, 1],
                "gripper_drive_target_readback": [0, 1],
                "contact_pairs": [] if pair is None else [pair],
            }
            for _ in range(PRE_OPEN_STABLE_FRAMES)
        ]

    @staticmethod
    def preopen_gate(rows):
        return build_pre_open_gate_v5(
            rows,
            bottle_actor_name="f3_main_bottle",
            support_actor_names=("table", "f3_original_pad"),
            target_actor_pose=[0, 0, 1.01, 1, 0, 0, 0],
            release_eef_pose=[0, 0, 1.1, 1, 0, 0, 0],
            initial_eef_actor_transform=[0, 0, -0.09, 1, 0, 0, 0],
            final_eef_actor_transform=[0, 0, -0.09, 1, 0, 0, 0],
            expected_closed_gripper_qpos=[0.032, 0.031],
            gripper_assembly_link_names=("fl_link6", "fl_link7", "fl_link8"),
        )

    def test_preopen_gate_uses_physical_signal_and_requires_geometry_separately(self):
        near_pair = contact_pair(
            "f3_main_bottle",
            "f3_original_pad",
            separation=0.01,
            impulse=0.0,
        )
        gate = self.preopen_gate(self.preopen_rows(near_pair))
        self.assertTrue(gate["pass"])
        self.assertTrue(gate["checks"]["physical_contact_signal_complete"])
        self.assertTrue(gate["checks"]["contact_free_of_pad_and_table"])
        self.assertEqual(len(gate["support_hits"]), PRE_OPEN_STABLE_FRAMES)
        self.assertEqual(
            gate["support_hits_semantics"], "pair_presence_audit_only"
        )
        self.assertTrue(gate["r6_runtime_geometry_gate_required_separately"])

        penetrating = contact_pair(
            "f3_main_bottle",
            "f3_original_pad",
            separation=-1e-6,
            impulse=0.0,
        )
        failed = self.preopen_gate(self.preopen_rows(penetrating))
        self.assertFalse(failed["pass"])
        self.assertFalse(
            failed["checks"]["contact_free_of_pad_and_table"]
        )


if __name__ == "__main__":
    unittest.main()
