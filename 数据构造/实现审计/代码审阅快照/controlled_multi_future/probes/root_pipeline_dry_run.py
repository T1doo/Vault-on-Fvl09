"""CPU-only durable dry run of the root-level runtime-v3 orchestrator."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..families import F1ObjectSelection
from ..root_orchestrator import RealSapienPilotRootAdapterV1, RealSapienPilotRootOrchestratorV1
from ..runtime_v3_contracts import IMPLEMENTATION_VERSION
from .pipeline_dry_run import SyntheticAdapter


class SyntheticRootAdapter(SyntheticAdapter, RealSapienPilotRootAdapterV1):
    def last_scene_cleanup_audit(self):
        return self.cleanup_audit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adapter = SyntheticRootAdapter()
    programs = F1ObjectSelection().checked_provisional_programs()
    orchestrator = RealSapienPilotRootOrchestratorV1(adapter, IMPLEMENTATION_VERSION)
    receipt = orchestrator.run_nonformal_root(
        output_dir=args.output,
        planned_root_slot_spec={
            "slot_id": "synthetic_runtime_v3_root",
            "family": "F1",
            "seed": 20260828,
            "generator": "synthetic_root_pipeline_dry_run_v1",
            "origin": "nonformal_cpu_integration",
            "rank": 0,
            "stop_condition": "one_root",
        },
        realization_spec_by_program={
            program["program_id"]: {"realization": "r_pc", "synthetic": True}
            for program in programs
        },
    )
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
