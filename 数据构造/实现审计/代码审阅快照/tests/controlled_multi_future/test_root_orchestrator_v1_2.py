import contextlib
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
from controlled_multi_future.current_hasher import build_current_hashes, hash_array
from controlled_multi_future.families import F1ObjectSelection
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter as RawSyntheticAdapter
from controlled_multi_future.root_orchestrator_v1_1 import SceneHandleV1_1
from controlled_multi_future.root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
)


def prefix_arrays():
    actions = np.zeros((2, 26), dtype=np.float64)
    actions[0, 0] = 0.1
    actions[1, 0] = 0.2
    return {
        "effective_setpoint_actions": actions,
        "requested_commands": actions.copy(),
        "component_masks": np.ones((2, 26), dtype=bool),
        "action_interval_start_timestamps": np.asarray([0.0, 0.004]),
        "action_interval_end_timestamps": np.asarray([0.004, 0.008]),
        "left_gripper_joint_drive_targets": np.zeros((2, 1), dtype=np.float64),
        "right_gripper_joint_drive_targets": np.zeros((2, 1), dtype=np.float64),
        "left_gripper_joint_drive_velocity_targets": np.zeros((2, 1), dtype=np.float64),
        "right_gripper_joint_drive_velocity_targets": np.zeros((2, 1), dtype=np.float64),
    }


def anchor(value):
    return capture_anchor(
        robot_qpos=np.full(14, value),
        robot_qvel=np.zeros(14),
        actor_poses={"red": [value, 0, 0, 1, 0, 0, 0]},
        gripper_state=[1, 1],
        metadata={"seed": 17},
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


class Scene:
    def __init__(self, phase, corrupt=False):
        self.phase = phase
        self.corrupt = corrupt
        self.robot = Robot()
        self.trace = []
        self.markers = {}
        self.planner_query_count = 0
        self.action_count = 0

    def reset_trace(self):
        self.trace = [{"effective_setpoint": np.zeros(26)}]
        self.markers = {}
        self.action_count = 0
        self.planner_query_count = 0

    def mark(self, name):
        self.markers[name] = max(0, len(self.trace) - 1)

    def replay_effective_setpoint_step(
        self,
        action,
        *,
        requested_command,
        component_mask,
        left_gripper_joint_drive_target,
        right_gripper_joint_drive_target,
        left_gripper_joint_drive_velocity_target,
        right_gripper_joint_drive_velocity_target,
    ):
        value = np.asarray(action, dtype=np.float64).copy()
        if self.corrupt and self.action_count == 0:
            value[0] += 1.0
        self.trace.append(
            {
                "effective_setpoint": value,
                "requested_command": np.asarray(requested_command).copy(),
                "component_mask": np.asarray(component_mask).copy(),
                "left_gripper_joint_drive_target": np.asarray(left_gripper_joint_drive_target, dtype=np.float64).copy(),
                "right_gripper_joint_drive_target": np.asarray(right_gripper_joint_drive_target, dtype=np.float64).copy(),
                "left_gripper_joint_drive_velocity_target": np.asarray(left_gripper_joint_drive_velocity_target, dtype=np.float64).copy(),
                "right_gripper_joint_drive_velocity_target": np.asarray(right_gripper_joint_drive_velocity_target, dtype=np.float64).copy(),
            }
        )
        self.action_count += 1
        self.robot.left_entity.qpos[:] = self.action_count
        self.robot.right_entity.qpos[:] = self.action_count

    def save_trace(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            effective=np.asarray(
                [item["effective_setpoint"] for item in self.trace],
                dtype=np.float64,
            ),
        )
        return {"path": str(path), "sample_count": len(self.trace)}


class SceneContext:
    counter = 0

    def __init__(self, adapter, phase, program):
        type(self).counter += 1
        self.adapter = adapter
        self.phase = phase
        program_id = None if program is None else program["program_id"]
        corrupt = phase.startswith("strict_prefix_branch:") and program_id == adapter.corrupt_program
        self.scene = Scene(phase, corrupt=corrupt)
        self.handle = SceneHandleV1_1(
            scene_instance_id=f"strict-prefix-scene-{type(self).counter}",
            scene=self.scene,
        )
        self.cleanup_receipt = None

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        self.cleanup_receipt = {
            "scene_instance_id": self.handle.scene_instance_id,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": True,
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
            "cleanup_error": None,
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        return False


class StrictPrefixSyntheticAdapter:
    def __init__(
        self,
        corrupt_program=None,
        suffix_fail_program=None,
        verifier_error_program=None,
    ):
        self.corrupt_program = corrupt_program
        self.suffix_fail_program = suffix_fail_program
        self.verifier_error_program = verifier_error_program
        self.prefix_generation_count = 0
        self.suffix_execution_count = 0
        self.raw = RawSyntheticAdapter()
        self.arrays = prefix_arrays()

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        return SceneContext(self, phase, program)

    def capture_current(self, scene):
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={
                "left": np.zeros((1, 1, 3), dtype=np.uint8),
                "right": np.zeros((1, 1, 3), dtype=np.uint8),
            },
            robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            object_role_layout={"red": [0, 0, 0]},
            camera_config_version="camera-v1",
            scene_seed=17,
            generator_version="strict-prefix-test-v1",
        )

    def capture_anchor(self, scene):
        count = scene.action_count
        return anchor(0 if count == 0 else 1 if count == 2 else 2)

    def build_programs(self, scene):
        return F1ObjectSelection().checked_provisional_programs()

    def task_trees(self, programs):
        ids = [item["program_id"] for item in programs]
        return {
            "observable": {"root": {"compatible": ids}},
            "oracle": {"root": {"compatible": ids}},
        }

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f1-cluster-neutral",
            "arm": "left",
            "ops": ["cluster-neutral"],
        }

    def audit_task_physical_feasibility(self, scene, program):
        return {
            "task_feasible": True,
            "physical_feasible": True,
            "planner_solvable": None,
            "failure_type": None,
            "evidence": {"synthetic": True},
        }

    def plan_and_execute_canonical_prefix(self, scene, prefix_contract):
        self.prefix_generation_count += 1
        scene.planner_query_count = 1
        return {
            "arrays": self.arrays,
            "semantic_prefix_end_anchor": anchor(1),
            "acceptance_prefix_end_anchor": anchor(2),
            "planner_query_receipts": [{"query_id": 1, "status": "Success"}],
            "planner_source_hash": "b" * 64,
            "planner_seed": 11,
            "settling_step_count": 1,
            "settling_policy": {
                "mode": "hold_last_effective_setpoint",
                "semantic": False,
                "component_mask_policy": "all_false_no_new_control_command",
                "transition_operator": "replay_effective_setpoint_step_v1_1",
            },
            "prefix_physical_acceptance": {
                "pass": True,
                "checks": {"synthetic": True},
            },
        }

    def initialize_prefix_replay_trace(self, scene):
        scene.reset_trace()

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        if program["program_id"] == self.suffix_fail_program:
            scene.planner_query_count = 3
            return {
                "planner_solvable": False,
                "planner_query_count": 3,
                "failure_type": "synthetic_suffix_failure",
                "evidence": {"synthetic": True},
                "actual_prefix_end_qpos_sha256": replay[
                    "actual_prefix_end_qpos_sha256"
                ],
            }
        scene.planner_query_count = 1
        position = np.zeros((2, 6), dtype=np.float32)
        velocity = np.zeros((2, 6), dtype=np.float32)
        qpos = np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64)
        planner_qpos = np.asarray(qpos, dtype=np.float32)
        start_hash = hash_array(qpos)
        planner_hash = hash_array(planner_qpos)
        return {
            "planner_solvable": True,
            "planner_query_count": 1,
            "failure_type": None,
            "evidence": {"synthetic": True},
            "actual_prefix_end_qpos_sha256": replay[
                "actual_prefix_end_qpos_sha256"
            ],
            "execution_spec": {
                "program_id": program["program_id"],
                "actual_prefix_end_qpos_sha256": start_hash,
                "planner_input_prefix_end_qpos_sha256": planner_hash,
                "terminal_qpos": qpos.tolist(),
                "terminal_qpos_sha256": start_hash,
                "terminal_joint_limit_margin_rad": [1.0] * len(qpos),
                "minimum_terminal_joint_limit_margin_rad": 1.0,
                "terminal_qpos_within_joint_limits": True,
                "targets": [
                    {
                        "segment_id": f"{program['program_id']}-suffix",
                        "pose": [0, 0, 0.9, 1, 0, 0, 0],
                    }
                ],
                "segment_receipts": [
                    {
                        "segment_id": f"{program['program_id']}-suffix",
                        "start_qpos_sha256": planner_hash,
                        "end_qpos_sha256": planner_hash,
                        "start_qpos": planner_qpos.tolist(),
                        "end_qpos": planner_qpos.tolist(),
                        "planner_status": "Success",
                        "executed": False,
                        "goal_eef_pose": [0, 0, 0.9, 1, 0, 0, 0],
                    }
                ],
            },
            "_execution_controls": [
                {
                    "status": "Success",
                    "position": position,
                    "velocity": velocity,
                    "_cmf_planner_query": {
                        "query_id": 1,
                        "arm": "left",
                        "source": f"{program['program_id']}-suffix",
                        "goal_eef_pose": [0, 0, 0.9, 1, 0, 0, 0],
                        "status": "Success",
                        "start_step": None,
                        "end_step": None,
                    },
                }
            ],
            "_actual_prefix_end_qpos": np.asarray(
                scene.robot.left_entity.get_qpos(), dtype=np.float64
            ),
        }

    def validate_family_suffix_gate(self, receipts):
        return {
            "schema_version": "synthetic-family-suffix-gate-v1",
            "pass": len(receipts) == 3
            and all(item.get("planner_solvable") is True for item in receipts),
        }

    def validate_replayed_prefix_physical(self, scene, replay):
        return {"pass": replay["prefix_end_equivalent"], "synthetic": True}

    def execute_frozen_suffix_spec(
        self, scene, program, execution_spec, replay, realization
    ):
        self.suffix_execution_count += 1
        result = self.raw.rollout(None, program, realization)
        prefix = self.arrays["effective_setpoint_actions"]
        actions = result["streams"]["controller_effective_setpoint"]
        actions[:2] = prefix
        actions[2] = prefix[-1]
        role = {"F1-red": 1.0, "F1-green": 2.0, "F1-blue": 3.0}[
            program["program_id"]
        ]
        actions[3, 0] = role
        result["streams"]["requested_command"] = actions.copy()
        result["streams"]["component_masks"][:] = True
        scene.trace.append({"effective_setpoint": actions[3].copy()})
        result["semantic_verifier"] = {"pass": True}
        result["final_state_equivalence_payload"] = None
        return result

    def verify(self, scene, program, result):
        if program["program_id"] == self.verifier_error_program:
            raise RuntimeError("synthetic verifier failure")
        return {"pass": result["semantic_verifier"]["pass"]}


class RootOrchestratorV1_2Test(unittest.TestCase):
    def run_root(self, adapter):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "root"
        programs = F1ObjectSelection().checked_provisional_programs()
        receipt = RealSapienStrictPrefixRootOrchestratorV1_2(
            adapter
        ).run_nonformal_root(
            output_dir=output,
            planned_root_slot_spec={
                "slot_id": "root-17",
                "family": "F1",
                "seed": 17,
                "origin": "test",
            },
            realization_spec_by_program={
                item["program_id"]: {
                    "realization": "r_pc",
                    "formal_data": False,
                    "stage0_data": False,
                }
                for item in programs
            },
        )
        return receipt, output

    def test_prefix_generated_once_and_replayed_exactly_three_times(self):
        adapter = StrictPrefixSyntheticAdapter()
        receipt, output = self.run_root(adapter)
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(adapter.prefix_generation_count, 1)
        self.assertEqual(receipt["freeze_call_count"], 1)
        self.assertEqual(receipt["canonical_prefix_generation_count"], 1)
        self.assertEqual(
            receipt["candidate_prefix_link"]["canonical_prefix_artifact_sha256"],
            receipt["canonical_prefix_artifact_sha256"],
        )
        self.assertTrue(
            (output / "candidate_prefix_link_receipt.json").is_file()
        )
        self.assertEqual(len(receipt["branch_receipts"]), 3)
        hashes = {
            item["executed_prefix"]["executed_prefix_action_sha256"]
            for item in receipt["branch_receipts"]
        }
        steps = {
            item["executed_prefix"]["executed_prefix_step_count"]
            for item in receipt["branch_receipts"]
        }
        starts = {
            item["suffix_planner"]["actual_prefix_end_qpos_sha256"]
            for item in receipt["branch_receipts"]
        }
        self.assertEqual(len(hashes), 1)
        self.assertEqual(steps, {2})
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            receipt["root_finalization"]["computed_first_post_prefix_divergence_step"],
            3,
        )
        self.assertTrue(
            all(
                receipt["root_finalization"][
                    "runtime_v3_3_independent_checks"
                ].values()
            )
        )
        artifact, arrays = load_canonical_prefix_artifact(
            output / "canonical_prefix_artifact"
        )
        self.assertEqual(artifact["prefix_step_count"], 2)
        np.testing.assert_array_equal(
            arrays["effective_setpoint_actions"], prefix_arrays()["effective_setpoint_actions"]
        )
        events = [
            json.loads(line)
            for line in (output / "root_events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        event_names = [item["event"] for item in events]
        planner_indices = [
            index
            for index, name in enumerate(event_names)
            if name == "suffix_planner_receipt"
        ]
        branch_indices = [
            index
            for index, name in enumerate(event_names)
            if name == "branch_terminal_receipt"
        ]
        self.assertEqual(len(planner_indices), 3)
        self.assertEqual(len(branch_indices), 3)
        self.assertLess(max(planner_indices), min(branch_indices))
        self.assertEqual(
            len(list((output / "suffix_artifacts").glob("*/frozen_suffix_artifact.json"))),
            3,
        )

    def test_corrupt_replay_keeps_root_incomplete(self):
        receipt, _ = self.run_root(StrictPrefixSyntheticAdapter(corrupt_program="F1-blue"))
        self.assertNotEqual(receipt["status"], "accepted")
        self.assertFalse(receipt.get("root_finalization", {}).get("accepted", False))
        blue = next(
            item for item in receipt["branch_receipts"] if item["program_id"] == "F1-blue"
        )
        self.assertEqual(blue["status"], "failed_execution")
        self.assertIn("effective action bytes differ", blue["error"])

    def test_suffix_planner_failure_runs_all_preflights_and_zero_execution(self):
        adapter = StrictPrefixSyntheticAdapter(suffix_fail_program="F1-green")
        receipt, _ = self.run_root(adapter)
        self.assertEqual(receipt["status"], "failed_planner")
        self.assertEqual(len(receipt["suffix_planner_receipts"]), 3)
        self.assertEqual(receipt["branch_execution_attempt_count"], 0)
        self.assertEqual(adapter.suffix_execution_count, 0)
        self.assertEqual(receipt["budget_counts"]["planner_query_count"], 6)

    def test_verifier_exception_preserves_raw_manifest_and_root_incomplete(self):
        adapter = StrictPrefixSyntheticAdapter(
            verifier_error_program="F1-green"
        )
        receipt, _ = self.run_root(adapter)
        self.assertNotEqual(receipt["status"], "accepted")
        green = next(
            item
            for item in receipt["branch_receipts"]
            if item["program_id"] == "F1-green"
        )
        self.assertEqual(green["partial_output_status"], "raw_saved_verifier_pending")
        self.assertIn("raw_manifest", green)
        self.assertEqual(receipt["branch_execution_attempt_count"], 3)


if __name__ == "__main__":
    unittest.main()
