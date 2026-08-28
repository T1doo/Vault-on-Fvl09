import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.a0_orchestrator_v1_1 import (
    A0CurrentAnchorOrchestratorV1_1,
    A0_PHASES,
)
from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.current_hasher import build_current_hashes
from controlled_multi_future.root_orchestrator_v1_1 import SceneHandleV1_1


class A0SyntheticScene:
    def __init__(self, phase):
        self.phase = phase


class A0SyntheticContext:
    def __init__(self, adapter, phase):
        adapter.scene_counter += 1
        self.adapter = adapter
        self.phase = phase
        self.scene_instance_id = f"a0-synthetic-{adapter.scene_counter}"
        self.handle = SceneHandleV1_1(
            scene_instance_id=self.scene_instance_id,
            scene=A0SyntheticScene(phase),
        )
        self.cleanup_receipt = None

    def __enter__(self):
        self.adapter.opened_phases.append(self.phase)
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        certain = self.phase != self.adapter.cleanup_uncertain_phase
        self.cleanup_receipt = {
            "scene_instance_id": self.scene_instance_id,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": certain,
            "cleanup_safety_pass": certain,
            "orphan_process_count": 0 if certain else None,
            "cleanup_error": None if certain else "synthetic cleanup uncertainty",
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        return False


class A0SyntheticAdapter:
    def __init__(
        self,
        *,
        current_mismatch_phase=None,
        anchor_mismatch_phase=None,
        cleanup_uncertain_phase=None,
        activity_violation_phase=None,
    ):
        self.current_mismatch_phase = current_mismatch_phase
        self.anchor_mismatch_phase = anchor_mismatch_phase
        self.cleanup_uncertain_phase = cleanup_uncertain_phase
        self.activity_violation_phase = activity_violation_phase
        self.scene_counter = 0
        self.opened_phases = []

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        if program is not None:
            raise AssertionError("A0 must not pass a program")
        return A0SyntheticContext(self, phase)

    def capture_current(self, scene):
        mismatch = scene.phase == self.current_mismatch_phase
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={
                "left": np.zeros((1, 1, 3), dtype=np.uint8),
                "right": np.zeros((1, 1, 3), dtype=np.uint8),
            },
            robot_state=np.asarray([1.0 if mismatch else 0.0]),
            gripper_actual_state=np.zeros(2),
            object_role_layout={"object": [0.0, 0.0, 0.0]},
            camera_config_version="a0-synthetic-camera-v1",
            scene_seed=20260829,
            generator_version="a0-synthetic-v1",
        )

    def capture_anchor(self, scene):
        mismatch = scene.phase == self.anchor_mismatch_phase
        return capture_anchor(
            robot_qpos=np.asarray([0.01 if mismatch else 0.0]),
            robot_qvel=np.zeros(1),
            actor_poses={"object": [0, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1],
            metadata={"seed": 20260829},
        )

    def capture_a0_activity_audit(self, scene):
        violation = scene.phase == self.activity_violation_phase
        count = 1 if violation else 0
        return {
            "schema_version": "cmf_a0_activity_audit_v1",
            "planner_query_count": count,
            "planner_query_record_count": count,
            "action_execution_count": 0,
            "trace_row_count": 0,
            "canonical_settle_steps": 60,
            "canonical_settle_is_control_action": False,
        }


class A0CurrentAnchorOrchestratorV1_1Test(unittest.TestCase):
    def run_a0(self, adapter):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "a0"
        receipt = A0CurrentAnchorOrchestratorV1_1(adapter).run(
            output_dir=output,
            planned_root_slot_spec={"slot_id": "a0-test", "family": "F1", "seed": 20260829},
            receipt_metadata={"test_only": True},
        )
        return receipt, output

    def test_four_fresh_scenes_pass_with_zero_planner_and_zero_action(self):
        adapter = A0SyntheticAdapter()
        receipt, output = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "passed_nonformal_A0")
        self.assertEqual(adapter.opened_phases, list(A0_PHASES))
        self.assertEqual(len({item["scene_instance_id"] for item in receipt["scenes"]}), 4)
        self.assertEqual(receipt["planner_query_count"], 0)
        self.assertEqual(receipt["action_execution_count"], 0)
        self.assertTrue(receipt["all_four_scenes_created"])
        self.assertTrue(receipt["scene_cleanup_succeeded"])
        self.assertTrue((output / "reference_current.json").is_file())
        self.assertTrue((output / "reference_anchor.json").is_file())
        self.assertTrue((output / "receipt.json").is_file())

    def test_current_mismatch_is_terminal_after_scene_cleanup(self):
        adapter = A0SyntheticAdapter(current_mismatch_phase="A0_fresh_2")
        receipt, _ = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_current_hash")
        self.assertEqual(adapter.opened_phases, list(A0_PHASES[:3]))
        self.assertEqual(len(receipt["cleanup_records"]), 3)

    def test_anchor_mismatch_is_terminal(self):
        adapter = A0SyntheticAdapter(anchor_mismatch_phase="A0_fresh_1")
        receipt, _ = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_anchor_equivalence")
        self.assertEqual(adapter.opened_phases, list(A0_PHASES[:2]))

    def test_cleanup_uncertainty_stops_later_scenes(self):
        adapter = A0SyntheticAdapter(cleanup_uncertain_phase="A0_fresh_1")
        receipt, _ = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_cleanup_uncertain")
        self.assertEqual(adapter.opened_phases, list(A0_PHASES[:2]))
        self.assertFalse(receipt["scene_cleanup_succeeded"])

    def test_any_planner_activity_violates_zero_action_gate(self):
        adapter = A0SyntheticAdapter(activity_violation_phase="A0_fresh_1")
        receipt, _ = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_zero_action_contract")
        self.assertEqual(adapter.opened_phases, list(A0_PHASES[:2]))
        self.assertEqual(receipt["planner_query_count"], 1)


if __name__ == "__main__":
    unittest.main()
