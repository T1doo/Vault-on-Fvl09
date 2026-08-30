import json
import unittest
from types import SimpleNamespace

import numpy as np

from controlled_multi_future.f3_physical_contact_signal_v8 import (
    CONTACT_PAIR_SCHEMA_VERSION,
    classify_f3_preopen_support_contacts_v8,
)
from controlled_multi_future.probes.runtime_trace import (
    DenseTraceMixin,
    trace_rows_to_raw_streams,
)


class FakeShape:
    def __init__(self):
        self.pose = SimpleNamespace(
            p=np.asarray([0.0, 0.0, 0.0]),
            q=np.asarray([1.0, 0.0, 0.0, 0.0]),
        )

    def get_local_pose(self):
        return self.pose

    def get_collision_groups(self):
        return [1, 1, 0, 7]

    def get_contact_offset(self):
        return 0.02

    def get_rest_offset(self):
        return 0.0


class FakeBody:
    def __init__(self, name, shape):
        self.entity = SimpleNamespace(name=name)
        self.shape = shape

    def get_collision_shapes(self):
        return [self.shape]


class FakePoint:
    def __init__(self, separation=0.01, impulse=(0.0, 0.0, 0.0)):
        self.separation = separation
        self.impulse = np.asarray(impulse, dtype=np.float64)
        self.normal = np.asarray([0.0, 0.0, 1.0], dtype=np.float64)
        self.position = np.asarray([0.0, 0.0, 0.76], dtype=np.float64)


class MissingSeparationPoint:
    impulse = np.asarray([0.0, 0.0, 0.0], dtype=np.float64)
    normal = np.asarray([0.0, 0.0, 1.0], dtype=np.float64)
    position = np.asarray([0.0, 0.0, 0.76], dtype=np.float64)


class MissingImpulsePoint:
    separation = 0.01
    normal = np.asarray([0.0, 0.0, 1.0], dtype=np.float64)
    position = np.asarray([0.0, 0.0, 0.76], dtype=np.float64)


class FakeContact:
    def __init__(self, body_a, body_b, point, *, shapes_available=True):
        self.bodies = [body_a, body_b]
        self.points = [point]
        if shapes_available:
            self.shapes = [body_a.shape, body_b.shape]


class ContactProbe(DenseTraceMixin):
    def __init__(self, contacts):
        self.scene = SimpleNamespace(get_contacts=lambda: list(contacts))
        self.trace_contact_actor = SimpleNamespace(
            get_name=lambda: "f3_main_bottle"
        )

    def selected_gripper_links(self):
        return ["fl_link7", "fl_link8"]


def raw_row(index, pairs):
    return {
        "step_index": index,
        "initial_state": index == 0,
        "effective_setpoint": np.zeros(26),
        "requested_command": np.zeros(26),
        "planner_goal_eef_pose": np.full(14, np.nan),
        "planner_goal_available": np.asarray([False, False]),
        "planner_goal_active": np.asarray([False, False]),
        "planner_query_id": np.asarray([-1, -1]),
        "planner_goal_source": ("", ""),
        "component_mask": np.zeros(26, dtype=bool),
        "joint_qpos": np.zeros(14),
        "joint_qvel": np.zeros(14),
        "dual_eef": np.zeros(14),
        "eef": np.zeros(7),
        "gripper_command": np.zeros(2),
        "timestamp": index / 250.0,
        "actor_pose": np.zeros(7),
        "actor_linear_velocity": np.zeros(3),
        "actor_linear_velocity_measured": False,
        "actor_angular_velocity": np.zeros(3),
        "actor_angular_velocity_measured": False,
        "actor_component_linear_velocity": np.zeros(3),
        "actor_component_linear_velocity_measured": True,
        "actor_component_angular_velocity": np.zeros(3),
        "actor_component_angular_velocity_measured": True,
        "actor_component_velocity_provenance": {},
        "eef_linear_velocity": np.zeros(3),
        "eef_angular_velocity": np.zeros(3),
        "gripper_drive_target_readback": np.zeros(2),
        "left_gripper_joint_drive_target": np.zeros(2),
        "right_gripper_joint_drive_target": np.zeros(2),
        "left_gripper_joint_drive_velocity_target": np.zeros(2),
        "right_gripper_joint_drive_velocity_target": np.zeros(2),
        "realized_left_gripper_joint_qpos": np.zeros(2),
        "realized_right_gripper_joint_qpos": np.zeros(2),
        "selected_gripper_contact": False,
        "selected_gripper_contact_count": 0,
        "selected_gripper_contact_impulse": 0.0,
        "selected_contact_actor_name": "f3_main_bottle",
        "contact_pairs": pairs,
    }


class RuntimeTraceContactSignalV8Test(unittest.TestCase):
    @staticmethod
    def contact(point, *, shapes_available=True):
        shape_a = FakeShape()
        shape_b = FakeShape()
        body_a = FakeBody("f3_main_bottle", shape_a)
        body_b = FakeBody("f3_original_pad", shape_b)
        return FakeContact(
            body_a,
            body_b,
            point,
            shapes_available=shapes_available,
        )

    def test_trace_saves_signed_separation_and_deterministic_shape_identity(self):
        pairs, _, _ = ContactProbe(
            [self.contact(FakePoint(separation=0.012))]
        )._contacts()
        self.assertEqual(len(pairs), 1)
        pair = pairs[0]
        self.assertEqual(
            pair["contact_pair_schema_version"], CONTACT_PAIR_SCHEMA_VERSION
        )
        self.assertEqual(pair["point_separations"], [0.012])
        self.assertEqual(pair["point_separation_available"], [True])
        self.assertTrue(pair["impulse_available"])
        self.assertEqual(pair["point_impulse_available"], [True])
        self.assertTrue(pair["shape_identity_available"])
        self.assertEqual(len(pair["shape_identities"]), 2)
        self.assertEqual(
            pair["point_evidence"][0]["shape_identity_sha256"],
            [
                identity["identity_sha256"]
                for identity in pair["shape_identities"]
            ],
        )
        json.dumps(pair, allow_nan=False)

        classified = classify_f3_preopen_support_contacts_v8(
            [[pair]],
            bottle_actor_name="f3_main_bottle",
            gripper_assembly_link_names=("fl_link6", "fl_link7", "fl_link8"),
            support_actor_names=("table", "f3_original_pad"),
        )
        self.assertTrue(classified["pass"])

    def test_missing_separation_or_shapes_is_explicit_and_fails_closed(self):
        cases = (
            self.contact(MissingSeparationPoint()),
            self.contact(MissingImpulsePoint()),
            self.contact(FakePoint(), shapes_available=False),
        )
        for contact in cases:
            with self.subTest(shapes=hasattr(contact, "shapes")):
                pairs, _, _ = ContactProbe([contact])._contacts()
                pair = pairs[0]
                if hasattr(contact, "shapes"):
                    point = pair["point_evidence"][0]
                    if isinstance(contact.points[0], MissingSeparationPoint):
                        self.assertFalse(
                            point["signed_separation_available"]
                        )
                        self.assertIn(
                            "point_separation_api_error",
                            point["signed_separation_unavailable_reason"],
                        )
                    else:
                        self.assertFalse(point["impulse_available"])
                        self.assertFalse(pair["impulse_available"])
                else:
                    self.assertFalse(pair["shape_identity_available"])
                    self.assertIn(
                        "contact_shapes_api_error",
                        pair["shape_identities"][0]["unavailable_reason"],
                    )
                classified = classify_f3_preopen_support_contacts_v8(
                    [[pair]],
                    bottle_actor_name="f3_main_bottle",
                    gripper_assembly_link_names=(
                        "fl_link6",
                        "fl_link7",
                        "fl_link8",
                    ),
                    support_actor_names=("table", "f3_original_pad"),
                )
                self.assertFalse(classified["pass"])

    def test_contact_signal_survives_raw_audit_json_persistence(self):
        pairs, _, _ = ContactProbe(
            [self.contact(FakePoint(separation=0.015))]
        )._contacts()
        _, audit = trace_rows_to_raw_streams(
            [raw_row(0, pairs), raw_row(1, pairs)]
        )
        restored = json.loads(str(audit["contact_pairs_json"][0]))
        self.assertEqual(
            restored[0]["contact_pair_schema_version"],
            CONTACT_PAIR_SCHEMA_VERSION,
        )
        self.assertEqual(
            restored[0]["point_evidence"][0]["signed_separation_m"],
            0.015,
        )
        self.assertTrue(restored[0]["shape_identity_available"])


if __name__ == "__main__":
    unittest.main()
