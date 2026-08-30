import copy
import unittest

import numpy as np

from controlled_multi_future.f3_return_release_v5 import (
    DISENGAGEMENT_CONFIRM_FRAMES,
    PRE_OPEN_STABLE_FRAMES,
    RELEASE_CLEARANCE_WORLD_Z_M,
    RETURN_SEGMENT_IDS,
    build_pre_open_gate_v5,
    contact_free_release_actor_pose,
    first_confirmed_disengagement_index,
    transform_f3_return_controls_v5,
)


def control(query_id, steps=5):
    position = np.arange(steps * 6, dtype=np.float32).reshape(steps, 6) / 100.0
    velocity = np.ones((steps, 6), dtype=np.float32)
    return {
        "status": "Success",
        "position": position,
        "velocity": velocity,
        "_cmf_planner_query": {
            "query_id": query_id,
            "arm": "left",
            "dtype_contract": {
                "control": {
                    "position": {"shape": list(position.shape), "dtype": "float32"},
                    "velocity": {"shape": list(velocity.shape), "dtype": "float32"},
                }
            },
        },
    }


class F3ReturnReleaseV5Test(unittest.TestCase):
    def test_clearance_changes_only_world_z(self):
        original = np.asarray([1, 2, 3, 1, 0, 0, 0], dtype=np.float64)
        result = contact_free_release_actor_pose(original)
        np.testing.assert_array_equal(result[[0, 1, 3, 4, 5, 6]], original[[0, 1, 3, 4, 5, 6]])
        self.assertEqual(result[2], original[2] + RELEASE_CLEARANCE_WORLD_Z_M)

    def test_only_two_return_controls_are_dilated(self):
        targets = [
            {"segment_id": "suffix_event"},
            {"segment_id": RETURN_SEGMENT_IDS[0]},
            {"segment_id": RETURN_SEGMENT_IDS[1]},
            {"segment_id": "f3_return_retreat"},
        ]
        controls = [control(index + 1) for index in range(len(targets))]
        before = copy.deepcopy(controls)
        output, receipts = transform_f3_return_controls_v5(controls, targets)
        self.assertEqual([item["segment_id"] for item in receipts], list(RETURN_SEGMENT_IDS))
        self.assertEqual(output[0]["position"].shape, before[0]["position"].shape)
        self.assertEqual(output[3]["position"].shape, before[3]["position"].shape)
        for index in (1, 2):
            self.assertEqual(output[index]["position"].shape[0], 2 * before[index]["position"].shape[0] - 1)
            np.testing.assert_array_equal(output[index]["position"][0], before[index]["position"][0])
            np.testing.assert_array_equal(output[index]["position"][-1], before[index]["position"][-1])
            self.assertTrue(np.allclose(output[index]["velocity"].max(), 0.5))
            audit = output[index]["_cmf_planner_query"]["execution_control_transform"]
            self.assertNotEqual(audit["planner_control"]["position_shape"], audit["executed_control"]["position_shape"])
            self.assertTrue(output[index]["_cmf_planner_query"]["planner_control_shape_is_not_executed_control_shape"])

    @staticmethod
    def rows(
        *,
        support=False,
        selected_support=False,
        palm_support=False,
        contact=True,
        identity="f3_main_bottle",
        qpos=(0.032, 0.031),
    ):
        result = []
        for _ in range(PRE_OPEN_STABLE_FRAMES):
            result.append(
                {
                    "actor_pose": [0, 0, 1.01, 1, 0, 0, 0],
                    "eef": [0, 0, 1.1, 1, 0, 0, 0],
                    "eef_linear_velocity": [0, 0, 0],
                    "eef_angular_velocity": [0, 0, 0],
                    "actor_linear_velocity": [0, 0, 0],
                    "actor_angular_velocity": [0, 0, 0],
                    "selected_gripper_contact": contact,
                    "selected_contact_actor_name": identity,
                    "realized_left_gripper_joint_qpos": list(qpos),
                    "gripper_command": [0, 1],
                    "gripper_drive_target_readback": [0, 1],
                    "contact_pairs": (
                        [{"body_a": "f3_main_bottle", "body_b": "table"}]
                        if support
                        else [{"body_a": "fl_link7", "body_b": "table"}]
                        if selected_support
                        else [{"body_a": "fl_link6", "body_b": "table"}]
                        if palm_support
                        else []
                    ),
                }
            )
        return result

    def gate(self, rows):
        return build_pre_open_gate_v5(
            rows,
            bottle_actor_name="f3_main_bottle",
            support_actor_names=("table", "f3_original_pad"),
            target_actor_pose=[0, 0, 1.01, 1, 0, 0, 0],
            release_eef_pose=[0, 0, 1.1, 1, 0, 0, 0],
            initial_eef_actor_transform=[0, 0, -0.09, 1, 0, 0, 0],
            final_eef_actor_transform=[0, 0, -0.09, 1, 0, 0, 0],
            expected_closed_gripper_qpos=[0.032, 0.031],
            gripper_assembly_link_names=[
                "fl_link6",
                "fl_link7",
                "fl_link8",
            ],
        )

    def test_pre_open_gate_passes_and_fails_closed(self):
        self.assertTrue(self.gate(self.rows())["pass"])
        self.assertFalse(self.gate(self.rows(support=True))["pass"])
        self.assertFalse(
            self.gate(self.rows(selected_support=True))["pass"]
        )
        self.assertFalse(self.gate(self.rows(palm_support=True))["pass"])
        self.assertFalse(self.gate(self.rows(contact=False))["pass"])
        self.assertFalse(self.gate(self.rows(identity="other"))["pass"])
        self.assertTrue(self.gate(self.rows(qpos=(0.032, 0.031)))["pass"])

    def test_physical_disengagement_requires_consecutive_false(self):
        flags = [True] * 4 + [False] * (DISENGAGEMENT_CONFIRM_FRAMES - 1) + [True] + [False] * DISENGAGEMENT_CONFIRM_FRAMES
        open_qpos = [[0.044, 0.044] for _ in flags]
        self.assertEqual(
            first_confirmed_disengagement_index(flags, open_qpos),
            4 + DISENGAGEMENT_CONFIRM_FRAMES,
        )
        closed_qpos = [[0.03, 0.03] for _ in flags]
        self.assertIsNone(
            first_confirmed_disengagement_index(flags, closed_qpos)
        )
        self.assertIsNone(
            first_confirmed_disengagement_index(
                [True, False, True], [[0.044, 0.044]] * 3
            )
        )


if __name__ == "__main__":
    unittest.main()
