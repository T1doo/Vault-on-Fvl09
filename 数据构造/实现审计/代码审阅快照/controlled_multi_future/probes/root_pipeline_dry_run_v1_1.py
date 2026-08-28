"""CPU-only durable dry run for root orchestrator v1_1 and raw v2_1_1."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from ..anchor import capture_anchor
from ..current_hasher import build_current_hashes, hash_json
from ..families import F1ObjectSelection
from ..root_orchestrator_v1_1 import RealSapienPilotRootAdapterV1_1, RealSapienPilotRootOrchestratorV1_1, SceneHandleV1_1
from .pipeline_dry_run import SyntheticAdapter as RawSyntheticAdapter


class DryScene:
    def __init__(self, phase, program):
        self.phase = phase
        self.program = program


class DryContext:
    def __init__(self, adapter, phase, program):
        adapter.generation += 1
        self.adapter = adapter
        self.scene_instance_id = f"runtime-v3_1-cpu-scene-{adapter.generation}"
        self.handle = SceneHandleV1_1(scene_instance_id=self.scene_instance_id, scene=DryScene(phase, program))
        self.cleanup_receipt = None

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        self.cleanup_receipt = {
            "scene_instance_id": self.scene_instance_id,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": True,
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
            "cleanup_error": None,
            "gpu_postcheck": "not_applicable_cpu_dry_run",
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        return False


class DurableSyntheticAdapterV1_1(RealSapienPilotRootAdapterV1_1):
    def __init__(self):
        self.generation = 0
        self.raw = RawSyntheticAdapter()

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        return DryContext(self, phase, program)

    def capture_current(self, scene):
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            object_role_layout={"red": [0, 0, 0], "green": [1, 0, 0], "blue": [2, 0, 0]},
            camera_config_version="synthetic-v3_1",
            scene_seed=20260829,
            generator_version="synthetic-root-v1_1",
        )

    def capture_anchor(self, scene):
        return capture_anchor(
            robot_qpos=np.zeros(14),
            robot_qvel=np.zeros(14),
            actor_poses={"red": [0, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1],
            metadata={"seed": 20260829},
        )

    def build_programs(self, pristine_scene):
        return F1ObjectSelection().checked_provisional_programs()

    def task_trees(self, programs):
        ids = [item["program_id"] for item in programs]
        return {"observable": {"root": {"compatible": ids}}, "oracle": {"root": {"compatible": ids}}}

    def canonical_prefix(self, programs):
        return {"prefix_id": "synthetic-actual-prefix-v1_1", "program_ids": [item["program_id"] for item in programs]}

    def audit_task_physical_feasibility(self, disposable_scene, program):
        return {"task_feasible": True, "physical_feasible": True, "planner_solvable": None, "failure_type": None, "evidence": {"synthetic": True}}

    def audit_planner_solvability(self, disposable_scene, frozen_program, planner_variant):
        return {
            "planner_solvable": True,
            "failure_type": None,
            "evidence": {"synthetic": True},
            "planner_query_count": 0,
            "execution_spec": {"variant_id": planner_variant["variant_id"], "synthetic": True},
        }

    def rollout(self, fresh_scene, frozen_program, realization_spec):
        result = self.raw.rollout(None, frozen_program, realization_spec)
        anchor = self.capture_anchor(fresh_scene)
        result["executed_prefix"] = {
            "target_role": frozen_program["target_role"],
            "target_role_visible_during_prefix": False,
            "executed_prefix_action_sha256": "a" * 64,
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
        return result

    def verify(self, fresh_scene, frozen_program, rollout_result):
        return {"pass": True, "synthetic_only": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    programs = F1ObjectSelection().checked_provisional_programs()
    receipt = RealSapienPilotRootOrchestratorV1_1(DurableSyntheticAdapterV1_1()).run_nonformal_root(
        output_dir=args.output,
        planned_root_slot_spec={
            "slot_id": "synthetic_runtime_v3_1_root",
            "family": "F1",
            "seed": 20260829,
            "generator": "synthetic_root_pipeline_dry_run_v1_1",
            "origin": "nonformal_cpu_integration",
            "rank": 0,
            "stop_condition": "one_root",
        },
        realization_spec_by_program={program["program_id"]: {"realization": "r_pc", "synthetic": True} for program in programs},
    )
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
