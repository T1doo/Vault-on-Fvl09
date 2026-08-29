import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.current_hasher import build_current_hashes, hash_array
from controlled_multi_future.f4_staged_block_gate_v1 import (
    F4StagedBlockExecutionGateV1,
    GATE_SEQUENCE,
)
from controlled_multi_future.families import F4SubtaskOrder
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter as RawSyntheticAdapter
from controlled_multi_future.root_orchestrator_v1_1 import SceneHandleV1_1

from test_root_orchestrator_v1_2 import Scene, anchor, prefix_arrays


class SceneContext:
    counter = 0

    def __init__(self, phase):
        type(self).counter += 1
        self.scene = Scene(phase)
        self.handle = SceneHandleV1_1(
            scene_instance_id=f"f4-staged-synthetic-{type(self).counter}",
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


class Controller:
    def plan_diagnostic_blocks_from_actual_prefix_end_state(
        self, scene, roles, replay
    ):
        roles = list(roles)
        scene.planner_query_count = len(roles)
        scene.planner_queries = [
            {
                "query_id": index + 1,
                "status": "Success",
                "source": role,
            }
            for index, role in enumerate(roles)
        ]
        actual = np.asarray(scene.robot.right_entity.get_qpos(), dtype=np.float64)
        planner = actual.astype(np.float32)
        targets = []
        receipts = []
        controls = []
        for index, role in enumerate(roles):
            segment_id = f"{role}-synthetic"
            targets.append(
                {
                    "segment_id": segment_id,
                    "pose": [0, 0, 0.9 + index * 0.01, 1, 0, 0, 0],
                }
            )
            receipts.append(
                {
                    "segment_id": segment_id,
                    "start_qpos_sha256": hash_array(planner),
                    "end_qpos_sha256": hash_array(planner),
                    "start_qpos": planner.tolist(),
                    "end_qpos": planner.tolist(),
                    "planner_status": "Success",
                    "executed": False,
                    "goal_eef_pose": targets[-1]["pose"],
                }
            )
            controls.append(
                {
                    "status": "Success",
                    "position": np.repeat(planner[None, :], 2, axis=0),
                    "velocity": np.zeros((2, len(planner)), dtype=np.float32),
                    "_cmf_planner_query": {
                        "query_id": index + 1,
                        "arm": "right",
                        "source": role,
                        "goal_eef_pose": targets[-1]["pose"],
                        "status": "Success",
                        "start_step": None,
                        "end_step": None,
                    },
                }
            )
        program_id = "F4-DIAG-" + "".join(roles)
        return {
            "planner_solvable": True,
            "planner_query_count": len(roles),
            "failure_type": None,
            "evidence": {"synthetic": True},
            "actual_prefix_end_qpos_sha256": hash_array(actual),
            "execution_spec": {
                "schema_version": "synthetic-f4-staged-v1",
                "program_id": program_id,
                "arm": "right",
                "actual_prefix_end_qpos_sha256": hash_array(actual),
                "targets": targets,
                "segment_receipts": receipts,
                "object_order": roles,
                "object_target_groups": [
                    {"role": role, "target_start_index": index}
                    for index, role in enumerate(roles)
                ],
                "terminal_qpos": actual.tolist(),
                "terminal_qpos_sha256": hash_array(actual),
                "terminal_joint_limit_margin_rad": [1.0] * len(actual),
                "minimum_terminal_joint_limit_margin_rad": 1.0,
                "terminal_qpos_within_joint_limits": True,
            },
            "_execution_controls": controls,
            "_actual_prefix_end_qpos": actual,
        }


class Adapter:
    family = "F4"

    def __init__(self):
        self.arrays = prefix_arrays()
        self.raw = RawSyntheticAdapter()
        self.controller_v3_3 = Controller()

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        return SceneContext(phase)

    def capture_current(self, scene):
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={
                "left": np.zeros((1, 1, 3), dtype=np.uint8),
                "right": np.zeros((1, 1, 3), dtype=np.uint8),
            },
            robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            object_role_layout={"common_x": [0, 0, 0]},
            camera_config_version="synthetic-camera-v1",
            scene_seed=17,
            generator_version="synthetic-f4-staged-v1",
        )

    def capture_anchor(self, scene):
        count = scene.action_count
        return anchor(0 if count == 0 else 1 if count == 2 else 2)

    def build_programs(self, scene):
        return F4SubtaskOrder().checked_provisional_programs()

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f4-synthetic-common",
            "arm": "right",
            "ops": ["common-X", "neutral"],
        }

    def plan_and_execute_canonical_prefix(self, scene, prefix_contract):
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
            "prefix_physical_acceptance": {"pass": True},
        }

    def initialize_prefix_replay_trace(self, scene):
        scene.reset_trace()

    def validate_replayed_prefix_physical(self, scene, replay):
        return {"pass": replay["prefix_end_equivalent"]}

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization
    ):
        result = self.raw.rollout(None, program, realization)
        result["semantic_verifier"] = {"pass": True, "synthetic": True}
        scene.trace.append(
            {
                "effective_setpoint": np.zeros(26),
                "requested_command": np.zeros(26),
                "component_mask": np.ones(26, dtype=bool),
            }
        )
        return result

    def verify(self, scene, program, result):
        return {"pass": result["semantic_verifier"]["pass"]}


class VerifierFailureAdapter(Adapter):
    def verify(self, scene, program, result):
        raise RuntimeError("synthetic verifier exception")


class F4StagedBlockGateV1Test(unittest.TestCase):
    def test_all_four_gates_run_fresh_and_preserve_raw(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "f4-gate"
        receipt = F4StagedBlockExecutionGateV1(Adapter()).run(
            output_dir=output,
            planned_root_slot_spec={
                "slot_id": "f4-root",
                "family": "F4",
                "seed": 17,
            },
        )
        self.assertEqual(receipt["status"], "passed_f4_staged_block_gate")
        self.assertEqual(receipt["gate_sequence"], [list(item) for item in GATE_SEQUENCE])
        self.assertEqual(len(receipt["gate_receipts"]), 4)
        self.assertEqual(receipt["execution_attempt_count"], 4)
        self.assertEqual(receipt["prefix_replay_count"], 8)
        self.assertEqual(receipt["planner_query_count"], 6)
        self.assertEqual(len(receipt["cleanup_records"]), 10)
        for gate_id in ("A", "B", "C", "AB"):
            self.assertTrue((output / f"gate_{gate_id}/raw/manifest.json").is_file())

    def test_verifier_exception_keeps_raw_manifest_trace_and_stops_next_gate(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "f4-gate-failure"
        receipt = F4StagedBlockExecutionGateV1(VerifierFailureAdapter()).run(
            output_dir=output,
            planned_root_slot_spec={
                "slot_id": "f4-root",
                "family": "F4",
                "seed": 17,
            },
        )
        self.assertEqual(receipt["status"], "failed_f4_staged_block_gate")
        gate = json.loads(
            (output / "gate_A/receipt.json").read_text(encoding="utf-8")
        )
        self.assertEqual(gate["status"], "failed_verifier_exception")
        self.assertIn("raw_manifest", gate)
        self.assertIn("trace_source", gate)
        self.assertFalse((output / "gate_B").exists())


if __name__ == "__main__":
    unittest.main()
