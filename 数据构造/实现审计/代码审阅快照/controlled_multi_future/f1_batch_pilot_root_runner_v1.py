"""One-root runner/finalizer for the nonformal F1 batch pilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json as hash_json
from .development_video_capture_v1 import (
    validate_development_trajectory_mp4_receipt_v1,
)
from .f1_batch_generation_pilot_v1 import (
    IMPLEMENTATION_VERSION,
    PROGRAM_IDS,
)
from .raw_writer import verify_raw_artifact_integrity
from .root_orchestrator_v1_1 import _write_json
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2


SCHEMA_VERSION = "cmf_f1_batch_pilot_root_receipt_v1"


def _validate_root_spec(value: Mapping[str, Any]) -> dict[str, Any]:
    spec = dict(value)
    claimed = spec.pop("planned_root_slot_spec_sha256", None)
    layout = value.get("scene_layout", {})
    checks = {
        "family": value.get("family") == "F1",
        "implementation": value.get("implementation_version")
        == IMPLEMENTATION_VERSION,
        "self_hash": isinstance(claimed, str) and hash_json(spec) == claimed,
        "programs": value.get("program_ids") == list(PROGRAM_IDS),
        "display": set(value.get("candidate_display_order", []))
        == set(PROGRAM_IDS),
        "layout": isinstance(layout, Mapping)
        and value.get("scene_layout_sha256") == layout.get("layout_sha256"),
        "single_attempt": value.get("automatic_retry") is False
        and value.get("recovery_attempts") == 0
        and value.get("maximum_root_invocations") == 1,
        "development_only": value.get("formal_data") is False
        and value.get("stage0_data") is False
        and value.get("stage1_authorized") is False
        and value.get("accepted_root_increment") == 0,
    }
    return {"checks": checks, "pass": all(checks.values())}


class F1BatchPilotRootRunnerV1:
    def __init__(self, adapter):
        if getattr(adapter, "family", None) != "F1":
            raise ValueError("F1 batch root runner requires F1 adapter")
        self.adapter = adapter

    def run(
        self, *, output_dir: Path, planned_root_slot_spec: Mapping[str, Any]
    ) -> dict[str, Any]:
        audit = _validate_root_spec(planned_root_slot_spec)
        if not audit["pass"]:
            raise ValueError(f"F1 batch root spec failed: {audit['checks']}")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        realization = {
            program_id: {
                "realization": "r_pc",
                "development_data": True,
                "f1_batch_pilot": True,
                "formal_data": False,
                "stage0_data": False,
                "stage0_authorized": False,
                "stage1_authorized": False,
                "accepted_root_increment": 0,
                "implementation_version": IMPLEMENTATION_VERSION,
                "root_slot_id": planned_root_slot_spec["slot_id"],
            }
            for program_id in PROGRAM_IDS
        }
        root_dir = output_dir / "root"
        root = RealSapienStrictPrefixRootOrchestratorV1_2(
            self.adapter, implementation_version=IMPLEMENTATION_VERSION
        ).run_nonformal_root(
            output_dir=root_dir,
            planned_root_slot_spec=planned_root_slot_spec,
            realization_spec_by_program=realization,
            stage0_data=False,
            stage0_authorized=False,
            development_video_required=True,
        )
        branches = {
            item.get("program_id"): item for item in root.get("branch_receipts", [])
        }
        reference_current = json.loads(
            (root_dir / "reference_current_hashes.json").read_text(encoding="utf-8")
        )
        branch_audits = []
        for program_id in PROGRAM_IDS:
            branch = branches.get(program_id, {})
            branch_dir = root_dir / "branches" / program_id
            raw = verify_raw_artifact_integrity(branch_dir / "raw")
            video = branch.get("development_video_receipt")
            try:
                video_audit = validate_development_trajectory_mp4_receipt_v1(
                    video,
                    expected_path=branch_dir / "video" / "trajectory.mp4",
                )
            except BaseException as exc:
                video_audit = {
                    "pass": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            checks = {
                "branch_accepted": branch.get("status") == "accepted",
                "verifier": branch.get("verifier", {}).get("pass") is True,
                "raw": raw.get("pass") is True,
                "raw_development_labels": raw.get("manifest", {}).get(
                    "formal_data"
                )
                is False
                and raw.get("manifest", {}).get("stage0_data") is False
                and raw.get("manifest", {}).get("stage0_authorized") is False,
                "video": video_audit.get("pass") is True,
                "video_development_labels": isinstance(video, Mapping)
                and video.get("development_data") is True
                and video.get("stage0_data") is False,
            }
            branch_audits.append(
                {
                    "program_id": program_id,
                    "checks": checks,
                    "pass": all(checks.values()),
                    "raw_integrity": raw,
                    "video_integrity": video_audit,
                }
            )
        cleanup = list(root.get("cleanup_records", []))
        cleanup_pass = bool(cleanup) and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count", -1)) == 0
            for item in cleanup
        )
        checks = {
            "root_accepted": root.get("status") == "accepted",
            "three_branches": set(branches) == set(PROGRAM_IDS),
            "one_prefix": root.get("canonical_prefix_generation_count") == 1,
            "three_replays": root.get("branch_prefix_replay_count") == 3,
            "same_current_and_anchor": all(
                item.get("branch_current", {}).get("aggregate_sha256")
                == reference_current.get("aggregate_sha256")
                and item.get("anchor_equivalence", {}).get("equivalent") is True
                for item in branches.values()
            ),
            "branch_artifacts": len(branch_audits) == 3
            and all(item["pass"] for item in branch_audits),
            "cleanup": cleanup_pass,
        }
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": IMPLEMENTATION_VERSION,
            "root_slot_id": planned_root_slot_spec["slot_id"],
            "root_status": root.get("status"),
            "accepted_development_root": all(checks.values()),
            "trajectory_count": sum(
                item["checks"]["branch_accepted"] for item in branch_audits
            ),
            "branch_audits": branch_audits,
            "checks": checks,
            "pass": all(checks.values()),
            "budget_counts": dict(root.get("budget_counts", {})),
            "elapsed_seconds": root.get("elapsed_seconds"),
            "cleanup_records": cleanup,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
            "accepted_root_increment": 0,
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "f1_batch_pilot_root_receipt.json", receipt)
        return receipt


__all__ = ["F1BatchPilotRootRunnerV1"]
