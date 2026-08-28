import contextlib
import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.current_hasher import build_current_hashes
from controlled_multi_future.families import F1ObjectSelection
from controlled_multi_future.raw_writer import pack_effective_setpoint
from controlled_multi_future.root_orchestrator import RealSapienPilotRootAdapterV1, RealSapienPilotRootOrchestratorV1


class RootScene:
    def __init__(self, generation, phase, program):
        self.generation = generation
        self.phase = phase
        self.program = program
        self.mutated = False


class SyntheticRootAdapter(RealSapienPilotRootAdapterV1):
    def __init__(self, *, failed_feasibility=None, failed_verifier=None):
        self.generation = 0
        self.closed = 0
        self.events = []
        self.last_cleanup = {}
        self.failed_feasibility = failed_feasibility
        self.failed_verifier = failed_verifier

    @contextlib.contextmanager
    def scene(self, planned_root_slot_spec, *, phase, program=None):
        self.generation += 1
        scene = RootScene(self.generation, phase, program)
        self.events.append(("scene_open", phase, program and program["program_id"], self.generation))
        try:
            yield scene
        finally:
            self.closed += 1
            self.last_cleanup = {
                "scene_created": True,
                "scene_cleanup_succeeded": True,
                "orphan_process_count": 0,
                "generation": self.generation,
            }
            self.events.append(("scene_close", phase, program and program["program_id"], self.generation))

    def capture_current(self, scene):
        self.events.append(("capture_current", scene.phase, scene.program and scene.program["program_id"], scene.generation))
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            object_role_layout={"red": [0, 0, 0], "green": [1, 0, 0], "blue": [2, 0, 0]},
            camera_config_version="synthetic_head_left_right_v1",
            scene_seed=9,
            generator_version="synthetic_root_v1",
        )

    def capture_anchor(self, scene):
        self.events.append(("capture_anchor", scene.phase, scene.program and scene.program["program_id"], scene.generation))
        return capture_anchor(
            robot_qpos=np.zeros(14),
            robot_qvel=np.zeros(14),
            actor_poses={"red": [0, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1],
            metadata={"seed": 9},
        )

    def build_programs(self, pristine_scene):
        self.events.append(("build_programs", pristine_scene.phase, None, pristine_scene.generation))
        return F1ObjectSelection().checked_provisional_programs()

    def task_trees(self, programs):
        ids = [item["program_id"] for item in programs]
        return {"observable": {"root": {"compatible": ids}}, "oracle": {"root": {"compatible": ids}}}

    def canonical_prefix(self, programs):
        return {"prefix_id": "shared", "program_ids": [item["program_id"] for item in programs]}

    def audit_feasibility(self, disposable_scene, program):
        self.events.append(("audit_feasibility", disposable_scene.phase, program["program_id"], disposable_scene.generation))
        disposable_scene.mutated = True
        return program["program_id"] != self.failed_feasibility

    @staticmethod
    def _raw(program_id):
        n = 2
        action = pack_effective_setpoint(np.zeros(6), np.zeros(6), 1, np.zeros(6), np.zeros(6), 1)
        streams = {
            "controller_effective_setpoint": np.repeat(action[None], n, axis=0),
            "requested_command": np.repeat(action.copy()[None], n, axis=0),
            "planner_goal_eef_pose": np.full((n, 14), np.nan),
            "gripper_command": np.ones((n, 2)),
            "action_interval_start_timestamps": np.asarray([0.0, 0.004]),
            "action_interval_end_timestamps": np.asarray([0.004, 0.008]),
            "state_timestamps": np.asarray([0.0, 0.004, 0.008]),
            "component_masks": np.ones((n, 26), dtype=bool),
            "realized_qpos": np.zeros((n + 1, 14)),
            "realized_qvel": np.zeros((n + 1, 14)),
            "realized_eef": np.zeros((n + 1, 14)),
            "field_metadata": {
                "controller_effective_setpoint": {"status": "measured", "source": "synthetic drive targets"},
                "requested_command": {"status": "commanded", "source": "synthetic request"},
                "planner_goal_eef_pose": {"status": "unavailable", "source": "synthetic no planner"},
                "realized_qpos": {"status": "measured", "source": "synthetic qpos"},
                "realized_qvel": {"status": "measured", "source": "synthetic qvel"},
                "realized_eef": {"status": "measured", "source": "synthetic eef"},
                "gripper_command": {"status": "commanded", "source": "synthetic command"},
                "action_interval_start_timestamps": {"status": "derived", "source": "state starts"},
                "action_interval_end_timestamps": {"status": "derived", "source": "state ends"},
                "state_timestamps": {"status": "derived", "source": "250 Hz states"},
                "component_masks": {"status": "derived", "source": "synthetic mask"},
            },
        }
        audit = {
            "object_pose": np.zeros((n + 1, 7)),
            "contact_count": np.zeros(n + 1, dtype=np.int64),
            "gripper_drive_target_readback": np.ones((n + 1, 2)),
            "realized_left_gripper_joint_qpos": np.zeros((n + 1, 2)),
            "realized_right_gripper_joint_qpos": np.zeros((n + 1, 2)),
            "planner_goal_available": np.zeros((n, 2), dtype=bool),
            "planner_query_id": np.full((n, 2), -1, dtype=np.int64),
            "planner_goal_active": np.zeros((n, 2), dtype=bool),
            "planner_goal_source": np.full((n, 2), "", dtype="U64"),
            "planner_goal_start_step": np.full((n, 2), -1, dtype=np.int64),
            "planner_goal_end_step": np.full((n, 2), -1, dtype=np.int64),
            "field_metadata": {
                "object_pose": {"status": "measured", "source": "synthetic object"},
                "contact_count": {"status": "measured", "source": "synthetic contact"},
                "gripper_drive_target_readback": {"status": "measured", "source": "synthetic drive target"},
                "realized_left_gripper_joint_qpos": {"status": "measured", "source": "synthetic left qpos"},
                "realized_right_gripper_joint_qpos": {"status": "measured", "source": "synthetic right qpos"},
                "planner_goal_available": {"status": "derived", "source": "synthetic no active planner goal"},
                "planner_query_id": {"status": "derived", "source": "synthetic no active planner query"},
                "planner_goal_active": {"status": "derived", "source": "synthetic no active planner control"},
                "planner_goal_source": {"status": "derived", "source": "synthetic no planner source"},
                "planner_goal_start_step": {"status": "derived", "source": "synthetic no planner interval"},
                "planner_goal_end_step": {"status": "derived", "source": "synthetic no planner interval"},
            },
        }
        return {
            "streams": streams,
            "audit_streams": audit,
            "provenance": {
                "synthetic": True,
                "program_id": program_id,
                "simulator_timing": {
                    "simulator_timestep_seconds": 0.004,
                    "control_steps_per_action": 1,
                    "effective_action_interval_seconds": 0.004,
                    "scene_timestep_source": "synthetic deterministic 250 Hz contract",
                },
                "planner_queries": [],
                "trace_source_sha256": hashlib.sha256(f"legacy-root:{program_id}".encode()).hexdigest(),
            },
        }

    def rollout(self, fresh_scene, program, realization_spec):
        self.events.append(("rollout", fresh_scene.phase, program["program_id"], fresh_scene.generation))
        return self._raw(program["program_id"])

    def verify(self, fresh_scene, program, rollout_result):
        return {"pass": program["program_id"] != self.failed_verifier}

    def last_scene_cleanup_audit(self):
        return self.last_cleanup


class RootOrchestratorTest(unittest.TestCase):
    @staticmethod
    def run_root(adapter):
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = RealSapienPilotRootOrchestratorV1(adapter, "controlled_multi_future_runtime_v3")
            program_ids = [item["program_id"] for item in F1ObjectSelection().checked_provisional_programs()]
            receipt = orchestrator.run_nonformal_root(
                output_dir=Path(directory) / "root",
                planned_root_slot_spec={"slot_id": "root", "family": "F1", "seed": 9},
                realization_spec_by_program={program_id: {"realization": "r_pc"} for program_id in program_ids},
            )
            return receipt, list(adapter.events)

    def test_prepare_freezes_once_and_runs_three_fresh_branches(self):
        receipt, events = self.run_root(SyntheticRootAdapter())
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(receipt["freeze_call_count"], 1)
        self.assertEqual(len(receipt["feasibility_receipts"]), 3)
        self.assertEqual(len(receipt["branch_receipts"]), 3)
        self.assertTrue(receipt["root_finalization"]["accepted"])
        self.assertEqual(receipt["reference_capture_order"][:2], ["capture_pristine_current", "capture_pristine_anchor"])
        phases = [event[1] for event in events if event[0] == "scene_open"]
        self.assertEqual(phases, ["pristine"] + ["feasibility"] * 3 + ["rollout"] * 3)

    def test_branch_failure_is_retained_and_other_branches_still_run(self):
        failed = F1ObjectSelection().checked_provisional_programs()[1]["program_id"]
        receipt, events = self.run_root(SyntheticRootAdapter(failed_verifier=failed))
        self.assertEqual(receipt["status"], "failed_verifier")
        self.assertEqual(len(receipt["branch_receipts"]), 3)
        self.assertEqual([item["status"] for item in receipt["branch_receipts"]], ["accepted", "failed_verifier", "accepted"])
        self.assertEqual(sum(event[0] == "rollout" for event in events), 3)

    def test_feasibility_failure_prevents_freeze_and_rollout(self):
        failed = F1ObjectSelection().checked_provisional_programs()[1]["program_id"]
        receipt, events = self.run_root(SyntheticRootAdapter(failed_feasibility=failed))
        self.assertEqual(receipt["status"], "failed_planner")
        self.assertEqual(receipt["freeze_call_count"], 0)
        self.assertFalse(any(event[0] == "rollout" for event in events))


if __name__ == "__main__":
    unittest.main()
