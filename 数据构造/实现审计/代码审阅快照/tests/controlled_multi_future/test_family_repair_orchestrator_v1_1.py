import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.current_hasher import build_current_hashes, hash_json
from controlled_multi_future.family_repair_orchestrator_v1_1 import FamilyRepairOrchestratorV1_1
from controlled_multi_future.families import F4SubtaskOrder
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter as RawSyntheticAdapter
from controlled_multi_future.root_orchestrator_v1_1 import SceneHandleV1_1


class RepairScene:
    def __init__(self, phase):
        self.phase = phase


class RepairContext:
    def __init__(self, adapter, phase):
        adapter.counter += 1
        self.adapter = adapter
        self.phase = phase
        self.handle = SceneHandleV1_1(scene_instance_id=f"repair-scene-{adapter.counter}", scene=RepairScene(phase))
        self.cleanup_receipt = None

    def __enter__(self):
        self.adapter.events.append(("open", self.phase, self.handle.scene_instance_id))
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        uncertain = self.phase == self.adapter.cleanup_uncertain_phase
        self.cleanup_receipt = {
            "scene_instance_id": self.handle.scene_instance_id,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": not uncertain,
            "cleanup_safety_pass": not uncertain,
            "orphan_process_count": 0 if not uncertain else None,
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        self.adapter.events.append(("close", self.phase, self.handle.scene_instance_id))
        return False


class SyntheticF4RepairAdapter:
    family = "F4"

    def __init__(self, cleanup_uncertain_phase=None):
        self.cleanup_uncertain_phase = cleanup_uncertain_phase
        self.counter = 0
        self.events = []
        self.raw = RawSyntheticAdapter()

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        return RepairContext(self, phase)

    def capture_current(self, scene):
        return build_current_hashes(
            head_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            robot_state=np.zeros(2),
            gripper_actual_state=np.zeros(2),
            object_role_layout={"common_x": [0, 0, 0]},
            camera_config_version="repair-test",
            scene_seed=1,
            generator_version="repair-test",
        )

    def capture_anchor(self, scene):
        return capture_anchor(
            robot_qpos=[0, 0], robot_qvel=[0, 0],
            actor_poses={"common_x": [0, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1], metadata={"seed": 1},
        )

    def planner_audit_variants(self, program):
        return [{"variant_id": "route1_minimum_height_segmented"}, {"variant_id": "route2_carry_neutral_fallback"}]

    def audit_task_physical_feasibility(self, scene, program):
        return {"task_feasible": True, "physical_feasible": True, "planner_solvable": None, "failure_type": None, "evidence": {"synthetic": True}}

    def audit_planner_solvability(self, scene, program, variant):
        passed = variant["variant_id"] == "route2_carry_neutral_fallback"
        return {
            "planner_solvable": passed,
            "failure_type": None if passed else "failed_planner",
            "evidence": {"synthetic": True},
            "planner_query_count": 1,
            "execution_spec": {"variant_id": variant["variant_id"]} if passed else None,
        }

    def rollout(self, scene, program, realization_spec):
        raw = self.raw.rollout(None, program, realization_spec)
        anchor = self.capture_anchor(scene)
        raw["executed_prefix"] = {
            "executed_prefix_action_sha256": "a" * 64,
            "executed_prefix_step_count": 1,
            "executed_prefix_start_state_sha256": "b" * 64,
            "executed_prefix_end_state_sha256": hash_json(anchor),
            "executed_prefix_start_anchor": anchor,
            "executed_prefix_end_anchor": anchor,
            "canonical_prefix_end_step": 1,
            "first_post_prefix_divergence_step": 1,
            "neutral_confirmation_step_count": 1,
            "neutral_confirmation_minimum_required_steps": 1,
        }
        raw["semantic_verifier"] = {"pass": False, "common_x_repair_probe_pass": True, "full_f4_program_complete": False}
        return raw

    def verify(self, scene, program, rollout):
        return {"pass": False, "common_x_repair_probe_pass": True}


class FamilyRepairOrchestratorV1_1Test(unittest.TestCase):
    def run_repair(self, adapter):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        program = F4SubtaskOrder().checked_provisional_programs()[0]
        receipt = FamilyRepairOrchestratorV1_1(adapter).run(
            output_dir=Path(directory.name) / "repair",
            planned_root_slot_spec={"slot_id": "repair", "family": "F4", "seed": 1},
            program=program,
        )
        return receipt

    def test_route2_uses_fresh_scene_after_terminal_route1_failure(self):
        adapter = SyntheticF4RepairAdapter()
        receipt = self.run_repair(adapter)
        self.assertEqual(receipt["status"], "passed_nonformal_repair_probe_full_program_incomplete")
        planner = [item for item in adapter.events if item[0] == "open" and item[1].startswith("repair_planner")]
        self.assertEqual([item[1] for item in planner], ["repair_planner:route1_minimum_height_segmented", "repair_planner:route2_carry_neutral_fallback"])
        self.assertNotEqual(planner[0][2], planner[1][2])

    def test_route1_cleanup_uncertain_forbids_route2(self):
        phase = "repair_planner:route1_minimum_height_segmented"
        adapter = SyntheticF4RepairAdapter(cleanup_uncertain_phase=phase)
        receipt = self.run_repair(adapter)
        self.assertEqual(receipt["status"], "failed_cleanup_uncertain")
        self.assertFalse(any(item[0] == "open" and item[1] == "repair_planner:route2_carry_neutral_fallback" for item in adapter.events))


if __name__ == "__main__":
    unittest.main()
