import inspect
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    load_canonical_prefix_artifact,
    prefix_action_sha256,
    validate_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from controlled_multi_future.canonical_prefix_replay_v1 import replay_canonical_prefix
from controlled_multi_future.probes.runtime_trace import DenseTraceMixin


def anchor(value):
    return capture_anchor(
        robot_qpos=np.full(14, value, dtype=np.float64),
        robot_qvel=np.zeros(14),
        actor_poses={"object": [value, 0, 0, 1, 0, 0, 0]},
        gripper_state=[1, 1],
        metadata={"seed": 7},
    )


def arrays():
    actions = np.zeros((2, 26), dtype=np.float64)
    actions[0] = np.arange(26, dtype=np.float64) / 100.0
    actions[1] = np.arange(26, dtype=np.float64) / 100.0 + 0.25
    return {
        "effective_setpoint_actions": actions,
        "requested_commands": actions.copy(),
        "component_masks": np.ones((2, 26), dtype=bool),
        "action_interval_start_timestamps": np.asarray([0.0, 0.004]),
        "action_interval_end_timestamps": np.asarray([0.004, 0.008]),
    }


def artifact(prefix_contract=None):
    return build_canonical_prefix_artifact(
        root_slot_id="root-1",
        family="F1",
        reference_current_sha256="a" * 64,
        reference_anchor=anchor(0),
        prefix_contract=prefix_contract
        or {"prefix_id": "f1-common", "arm": "left", "ops": ["cluster-neutral"]},
        planner_seed=11,
        planner_query_receipts=[{"query_id": 1, "status": "Success"}],
        planner_source_hash="b" * 64,
        arrays=arrays(),
        semantic_prefix_end_anchor=anchor(1),
        acceptance_prefix_end_anchor=anchor(2),
        settling_step_count=1,
        settling_policy={"mode": "hold_last_effective_setpoint", "semantic": False},
        prefix_physical_acceptance={"pass": True, "checks": {"synthetic": True}},
        reference_trace_source={"sha256": "c" * 64, "path": "synthetic.npz"},
    )


class Entity:
    def __init__(self):
        self.qpos = np.zeros(7)

    def get_qpos(self):
        return self.qpos.copy()


class Robot:
    def __init__(self):
        self.left_entity = Entity()
        self.right_entity = Entity()


class ReplayScene:
    def __init__(self, expected_arrays):
        self.robot = Robot()
        self.trace = [{"effective_setpoint": np.zeros(26)}]
        self.markers = {}
        self.planner_query_count = 0
        self.expected_arrays = expected_arrays

    def mark(self, name):
        self.markers[name] = len(self.trace) - 1

    def replay_effective_setpoint_step(self, action, *, requested_command, component_mask):
        self.trace.append(
            {
                "effective_setpoint": np.asarray(action, dtype=np.float64).copy(),
                "requested_command": np.asarray(requested_command, dtype=np.float64).copy(),
                "component_mask": np.asarray(component_mask, dtype=bool).copy(),
            }
        )
        value = float(len(self.trace) - 1)
        self.robot.left_entity.qpos[:] = value
        self.robot.right_entity.qpos[:] = value


class CanonicalPrefixV3_3Test(unittest.TestCase):
    def test_artifact_round_trip_and_settling_excluded(self):
        manifest, values = artifact()
        self.assertEqual(manifest["prefix_step_count"], 2)
        self.assertEqual(manifest["semantic_prefix_step_count"], 2)
        self.assertEqual(manifest["settling_step_count_excluded_from_semantic_prefix"], 1)
        self.assertFalse(manifest["settling_is_part_of_semantic_prefix"])
        self.assertEqual(
            manifest["prefix_action_sha256"],
            prefix_action_sha256(values["effective_setpoint_actions"]),
        )
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "artifact"
        written = write_canonical_prefix_artifact(output, manifest, values)
        loaded, loaded_arrays = load_canonical_prefix_artifact(output)
        self.assertEqual(loaded["artifact_sha256"], manifest["artifact_sha256"])
        self.assertEqual(loaded["prefix_arrays_npz_sha256"], written["prefix_arrays_npz_sha256"])
        np.testing.assert_array_equal(
            loaded_arrays["effective_setpoint_actions"],
            values["effective_setpoint_actions"],
        )

    def test_artifact_rejects_target_leakage_and_tamper(self):
        with self.assertRaisesRegex(ValueError, "forbidden key"):
            artifact({"prefix_id": "bad", "target_role": "blue"})
        manifest, values = artifact()
        changed = dict(values)
        changed["effective_setpoint_actions"] = values["effective_setpoint_actions"].copy()
        changed["effective_setpoint_actions"][0, 0] += 1.0
        with self.assertRaisesRegex(ValueError, "action hash|array hash"):
            validate_canonical_prefix_artifact(manifest, changed)

    def test_three_fresh_replays_use_identical_bytes_without_planner(self):
        manifest, values = artifact()
        evidence = []
        for _ in range(3):
            scene = ReplayScene(values)

            def capture_current(_scene):
                return {"aggregate_sha256": "a" * 64}

            def capture_anchor_for_scene(active):
                action_count = len(active.trace) - 1
                return anchor(0 if action_count == 0 else 1 if action_count == 2 else 2)

            item = replay_canonical_prefix(
                scene,
                manifest=manifest,
                arrays=values,
                reference_current={"aggregate_sha256": "a" * 64},
                capture_current=capture_current,
                capture_anchor=capture_anchor_for_scene,
            )
            self.assertTrue(item["prefix_end_equivalent"])
            self.assertEqual(item["planner_query_delta"], 0)
            self.assertEqual(item["executed_prefix_step_count"], 2)
            self.assertEqual(len(scene.trace), 4)
            evidence.append(item)
        self.assertEqual(len({item["executed_prefix_action_sha256"] for item in evidence}), 1)
        self.assertEqual(len({item["executed_prefix_step_count"] for item in evidence}), 1)

    def test_dense_trace_replay_is_direct_and_planner_free(self):
        source = inspect.getsource(DenseTraceMixin.replay_effective_setpoint_step)
        self.assertIn('set_arm_joints(effective[0:6]', source)
        self.assertIn('set_arm_joints(effective[6:12]', source)
        self.assertIn('set_gripper(float(effective[24])', source)
        self.assertNotIn("plan_path", source)
        self.assertNotIn("move_to_pose", source)


if __name__ == "__main__":
    unittest.main()
