"""CPU-only synthetic integration probe for the nonformal pilot pipeline."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from ..anchor import capture_anchor
from ..current_hasher import build_current_hashes
from ..families import F1ObjectSelection
from ..pilot_pipeline import PilotAttemptPipeline, PilotPipelineAdapter
from ..raw_writer import pack_effective_setpoint
from ..runtime_v2_contracts import IMPLEMENTATION_VERSION


class SyntheticScene:
    def __init__(self, generation):
        self.generation = generation


class SyntheticAdapter(PilotPipelineAdapter):
    def __init__(self):
        self.generation = 0
        self.closed = 0

    @contextmanager
    def scene(self, planned_root_slot_spec, *, phase, program=None):
        self.generation += 1
        scene = SyntheticScene(self.generation)
        try:
            yield scene
        finally:
            self.closed += 1

    def build_programs(self, scene):
        return F1ObjectSelection().checked_provisional_programs()

    def audit_feasibility(self, scene, program):
        return True

    def capture_current(self, scene):
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            robot_state=np.zeros(14, dtype=np.float64),
            object_role_layout={"red_block": [-0.2, 0.02, 0.762], "green_block": [-0.11, 0.02, 0.762], "blue_block": [-0.02, 0.02, 0.762]},
            scene_seed=20260827,
            generator_version="synthetic_pipeline_dry_run_v2",
        )

    def capture_anchor(self, scene):
        return capture_anchor(
            robot_qpos=np.zeros(14), robot_qvel=np.zeros(14),
            actor_poses={"red_block": [-0.2, 0.02, 0.762, 1, 0, 0, 0]},
            gripper_state=[1, 1], metadata={"scene_seed": 20260827, "generator_version": "synthetic_pipeline_dry_run_v2"},
        )

    def task_trees(self, programs):
        ids = [program["program_id"] for program in programs]
        return {"observable": {"root": {"compatible": ids}}, "oracle": {"root": {"compatible": ids}}}

    def canonical_prefix(self, programs):
        return {"prefix_type": "synthetic_zero_step", "steps": [], "program_ids": [item["program_id"] for item in programs]}

    def rollout(self, scene, program, realization_spec):
        n = 4
        action = pack_effective_setpoint(np.zeros(6), np.zeros(6), 1, np.zeros(6), np.zeros(6), 1)
        streams = {
            "controller_effective_setpoint": np.repeat(action[None, :], n, axis=0),
            "requested_command": np.repeat(action.copy()[None, :], n, axis=0),
            "planner_target": np.full((n, 14), np.nan),
            "gripper_command": np.ones((n, 2)),
            "timestamps": np.arange(n) / 250.0,
            "component_masks": np.ones((n, 26), dtype=bool),
            "realized_qpos": np.zeros((n + 1, 14)),
            "realized_qvel": np.zeros((n + 1, 14)),
            "realized_eef": np.zeros((n + 1, 14)),
            "field_metadata": {
                "controller_effective_setpoint": {"status": "commanded", "source": "synthetic dry-run effective setpoint generator"},
                "requested_command": {"status": "commanded", "source": "synthetic dry-run requested command generator"},
                "planner_target": {"status": "unavailable", "source": "synthetic dry-run has no planner"},
                "realized_qpos": {"status": "measured", "source": "synthetic deterministic adapter state"},
                "realized_qvel": {"status": "measured", "source": "synthetic deterministic adapter state"},
                "realized_eef": {"status": "measured", "source": "synthetic deterministic adapter state"},
                "gripper_command": {"status": "commanded", "source": "synthetic deterministic adapter command"},
                "timestamps": {"status": "derived", "source": "synthetic 250 Hz step index"},
                "component_masks": {"status": "derived", "source": "synthetic component availability"},
            },
        }
        audit_streams = {
            "object_pose": np.zeros((n + 1, 7)),
            "contact_count": np.zeros(n + 1, dtype=np.int64),
            "field_metadata": {
                "object_pose": {"status": "measured", "source": "synthetic deterministic adapter object state"},
                "contact_count": {"status": "measured", "source": "synthetic deterministic adapter contact state"},
            },
        }
        return {"streams": streams, "audit_streams": audit_streams, "provenance": {"synthetic": True, "program_id": program["program_id"]}}

    def verify(self, scene, program, rollout_result):
        return {"pass": True, "synthetic_only": True}

    def cleanup_audit(self):
        return {"scene_created": self.generation > 0, "scene_cleanup_attempted": self.generation > 0, "scene_cleanup_succeeded": self.closed == self.generation, "cleanup_error": None, "orphan_process_count": 0, "gpu_postcheck": "not_applicable_cpu_dry_run"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adapter = SyntheticAdapter()
    pipeline = PilotAttemptPipeline(adapter, IMPLEMENTATION_VERSION)
    receipt = pipeline.run_nonformal_attempt(
        output_dir=args.output,
        planned_root_slot_spec={"slot_id": "synthetic_f1_runtime_v2", "family": "F1", "seed": 20260828, "generator": "synthetic_pipeline_dry_run_v2", "origin": "nonformal_integration", "rank": 0, "stop_condition": "one_attempt"},
        program_id="F1-red_block",
        realization_spec={"realization": "r_pc", "synthetic": True},
    )
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
