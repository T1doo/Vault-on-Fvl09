import contextlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.current_hasher import build_current_hashes, hash_json
from controlled_multi_future.families import F1ObjectSelection
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter as RawSyntheticAdapter
from controlled_multi_future.root_orchestrator_v1_1 import (
    RealSapienPilotRootAdapterV1_1,
    RealSapienPilotRootOrchestratorV1_1,
    SceneHandleV1_1,
)


class SyntheticSceneV1_1:
    def __init__(self, *, phase, program, planned_spec, scene_instance_id):
        self.phase = phase
        self.program = program
        self.planned_spec = planned_spec
        self.scene_instance_id = scene_instance_id


class SyntheticSceneContextV1_1:
    def __init__(self, adapter, planned_spec, phase, program):
        adapter.scene_counter += 1
        self.adapter = adapter
        self.phase = phase
        self.scene_instance_id = f"synthetic-scene-{adapter.scene_counter}"
        self.handle = SceneHandleV1_1(
            scene_instance_id=self.scene_instance_id,
            scene=SyntheticSceneV1_1(
                phase=phase,
                program=program,
                planned_spec=planned_spec,
                scene_instance_id=self.scene_instance_id,
            ),
        )
        self.cleanup_receipt = None

    def __enter__(self):
        self.adapter.events.append(("scene_open", self.phase, self.scene_instance_id))
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        uncertain = self.phase == self.adapter.cleanup_uncertain_phase
        self.cleanup_receipt = {
            "scene_instance_id": self.scene_instance_id,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": not uncertain,
            "cleanup_safety_pass": not uncertain,
            "orphan_process_count": 0 if not uncertain else None,
            "cleanup_error": "synthetic uncertainty" if uncertain else None,
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        self.adapter.events.append(("scene_close", self.phase, self.scene_instance_id))
        if self.phase == self.adapter.exit_exception_phase:
            self.cleanup_receipt["cleanup_safety_pass"] = False
            self.cleanup_receipt["scene_cleanup_succeeded"] = False
            self.handle.cleanup_receipt = dict(self.cleanup_receipt)
            raise RuntimeError("synthetic context-manager cleanup exception")
        return False


class SyntheticRootAdapterV1_1(RealSapienPilotRootAdapterV1_1):
    def __init__(
        self,
        *,
        task_failure=None,
        planner_failure=None,
        verifier_exception=None,
        cleanup_uncertain_phase=None,
        exit_exception_phase=None,
        mutate_program=None,
        mutate_planned_phase=None,
        current_mismatch_program=None,
        prefix_mismatch_program=None,
    ):
        self.task_failure = task_failure
        self.planner_failure = planner_failure
        self.verifier_exception = verifier_exception
        self.cleanup_uncertain_phase = cleanup_uncertain_phase
        self.exit_exception_phase = exit_exception_phase
        self.mutate_program = mutate_program
        self.mutate_planned_phase = mutate_planned_phase
        self.current_mismatch_program = current_mismatch_program
        self.prefix_mismatch_program = prefix_mismatch_program
        self.scene_counter = 0
        self.events = []
        self.raw_adapter = RawSyntheticAdapter()

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        return SyntheticSceneContextV1_1(self, planned_root_slot_spec, phase, program)

    def capture_current(self, scene):
        mismatch = scene.phase.startswith("rollout:") and scene.program["program_id"] == self.current_mismatch_program
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            robot_state=np.asarray([1.0 if mismatch else 0.0]),
            gripper_actual_state=np.zeros(2),
            object_role_layout={"red": [0, 0, 0], "green": [1, 0, 0], "blue": [2, 0, 0]},
            camera_config_version="synthetic-camera-v1",
            scene_seed=9,
            generator_version="synthetic-root-v1_1",
        )

    def capture_anchor(self, scene):
        return capture_anchor(
            robot_qpos=np.zeros(14),
            robot_qvel=np.zeros(14),
            actor_poses={"red": [0, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1],
            metadata={"seed": 9},
        )

    def build_programs(self, pristine_scene):
        return F1ObjectSelection().checked_provisional_programs()

    def task_trees(self, programs):
        ids = [item["program_id"] for item in programs]
        return {"observable": {"root": {"compatible": ids}}, "oracle": {"root": {"compatible": ids}}}

    def canonical_prefix(self, programs):
        return {"prefix_id": "synthetic-shared-prefix-v1_1", "program_ids": [item["program_id"] for item in programs]}

    def _maybe_mutate(self, scene, program):
        if scene.phase == self.mutate_planned_phase:
            scene.planned_spec["seed"] = 123456
        if program["program_id"] == self.mutate_program:
            program["injected_mutation"] = True

    def audit_task_physical_feasibility(self, scene, program):
        self._maybe_mutate(scene, program)
        passed = program["program_id"] != self.task_failure
        return {
            "task_feasible": passed,
            "physical_feasible": passed,
            "planner_solvable": None,
            "failure_type": None if passed else "synthetic_task_physical_failure",
            "evidence": {"synthetic": True},
        }

    def audit_planner_solvability(self, scene, frozen_program, planner_variant):
        self._maybe_mutate(scene, frozen_program)
        passed = frozen_program["program_id"] != self.planner_failure
        return {
            "planner_solvable": passed,
            "failure_type": None if passed else "synthetic_planner_failure",
            "evidence": {"synthetic": True},
            "planner_query_count": 1,
            "execution_spec": {"variant_id": planner_variant["variant_id"]} if passed else None,
        }

    def _prefix(self, program_id):
        anchor = self.capture_anchor(None)
        action_hash = "f" * 64 if program_id == self.prefix_mismatch_program else "a" * 64
        return {
            "target_role": program_id.removeprefix("F1-"),
            "target_role_visible_during_prefix": False,
            "executed_prefix_action_sha256": action_hash,
            "executed_prefix_step_count": 2,
            "executed_prefix_start_state_sha256": "b" * 64,
            "executed_prefix_end_state_sha256": hash_json(anchor),
            "executed_prefix_start_anchor": anchor,
            "executed_prefix_end_anchor": anchor,
            "canonical_prefix_end_step": 2,
            "first_post_prefix_divergence_step": 2,
            "neutral_confirmation_step_count": 1,
            "neutral_confirmation_minimum_required_steps": 1,
        }

    def rollout(self, fresh_scene, frozen_program, realization_spec):
        self._maybe_mutate(fresh_scene, frozen_program)
        raw = self.raw_adapter.rollout(None, frozen_program, realization_spec)
        raw["executed_prefix"] = self._prefix(frozen_program["program_id"])
        return raw

    def verify(self, fresh_scene, frozen_program, rollout_result):
        if frozen_program["program_id"] == self.verifier_exception:
            raise RuntimeError("synthetic verifier exception")
        return {"pass": True, "synthetic_only": True}


class RootOrchestratorV1_1Test(unittest.TestCase):
    def run_root(self, adapter):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "root"
        programs = F1ObjectSelection().checked_provisional_programs()
        receipt = RealSapienPilotRootOrchestratorV1_1(adapter).run_nonformal_root(
            output_dir=output,
            planned_root_slot_spec={"slot_id": "root-v1_1", "family": "F1", "seed": 9},
            realization_spec_by_program={item["program_id"]: {"realization": "r_pc"} for item in programs},
        )
        return receipt, output

    def test_success_separates_feasibility_freeze_planner_and_rollout(self):
        adapter = SyntheticRootAdapterV1_1()
        receipt, output = self.run_root(adapter)
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(receipt["freeze_call_count"], 1)
        self.assertEqual(len(receipt["task_physical_feasibility_receipts"]), 3)
        self.assertEqual(len(receipt["planner_solvability_receipts"]), 3)
        self.assertEqual(len(receipt["branch_receipts"]), 3)
        self.assertTrue(receipt["root_finalization"]["accepted"])
        for name in ("provisional_programs.json", "provisional_task_tree.json", "provisional_prefix_spec.json"):
            self.assertTrue((output / name).is_file())

    def test_task_physical_and_planner_failures_are_distinct(self):
        program = F1ObjectSelection().checked_provisional_programs()[1]["program_id"]
        task_receipt, _ = self.run_root(SyntheticRootAdapterV1_1(task_failure=program))
        self.assertEqual(task_receipt["status"], "failed_task_physical_feasibility")
        self.assertEqual(task_receipt["freeze_call_count"], 0)
        planner_receipt, _ = self.run_root(SyntheticRootAdapterV1_1(planner_failure=program))
        self.assertEqual(planner_receipt["status"], "failed_planner")
        self.assertEqual(planner_receipt["freeze_call_count"], 1)

    def test_cleanup_uncertain_stops_entire_root(self):
        program = F1ObjectSelection().checked_provisional_programs()[0]["program_id"]
        phase = f"task_physical_feasibility:{program}"
        adapter = SyntheticRootAdapterV1_1(cleanup_uncertain_phase=phase)
        receipt, _ = self.run_root(adapter)
        self.assertEqual(receipt["status"], "failed_cleanup_uncertain")
        self.assertEqual(len(receipt["task_physical_feasibility_receipts"]), 0)
        self.assertFalse(any(event[1].startswith("planner_solvability") for event in adapter.events))

    def test_context_manager_cleanup_exception_is_terminal(self):
        adapter = SyntheticRootAdapterV1_1(exit_exception_phase="pristine")
        receipt, _ = self.run_root(adapter)
        self.assertEqual(receipt["status"], "failed_cleanup_uncertain")

    def test_program_and_planned_spec_mutation_fail_closed(self):
        program = F1ObjectSelection().checked_provisional_programs()[0]["program_id"]
        receipt, _ = self.run_root(SyntheticRootAdapterV1_1(mutate_program=program))
        self.assertEqual(receipt["status"], "failed_candidate_mutation")
        phase = f"task_physical_feasibility:{program}"
        receipt, _ = self.run_root(SyntheticRootAdapterV1_1(mutate_planned_phase=phase))
        self.assertEqual(receipt["status"], "failed_candidate_mutation")

    def test_verifier_exception_retains_raw_manifest(self):
        program = F1ObjectSelection().checked_provisional_programs()[1]["program_id"]
        receipt, output = self.run_root(SyntheticRootAdapterV1_1(verifier_exception=program))
        branch = next(item for item in receipt["branch_receipts"] if item["program_id"] == program)
        self.assertEqual(branch["status"], "failed_verifier")
        self.assertIn("raw_manifest", branch)
        self.assertEqual(branch["partial_output_status"], "raw_saved_verifier_pending")
        self.assertTrue((output / "branches" / program / "raw" / "raw_streams.npz").is_file())

    def test_branch_current_and_executed_prefix_mismatch_fail_finalizer(self):
        program = F1ObjectSelection().checked_provisional_programs()[1]["program_id"]
        receipt, _ = self.run_root(SyntheticRootAdapterV1_1(current_mismatch_program=program))
        self.assertNotEqual(receipt["status"], "accepted")
        receipt, _ = self.run_root(SyntheticRootAdapterV1_1(prefix_mismatch_program=program))
        self.assertEqual(receipt["status"], "failed_verifier")
        self.assertFalse(receipt["root_finalization"]["checks"]["one_executed_prefix_action_hash"])


if __name__ == "__main__":
    unittest.main()
