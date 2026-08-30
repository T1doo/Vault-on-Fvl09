"""One-family Stage 0 smoke runner with exactly three terminal attempts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .root_orchestrator_v1_1 import _write_json
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2


SCHEMA_VERSION = "cmf_stage0_smoke_family_runner_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1"
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


def _file_reference(path: Path, base: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return {
        "relative_path": path.relative_to(base).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _attempt_status(branch: Mapping[str, Any] | None, root_status: str) -> str:
    if branch is not None:
        status = str(branch.get("status", "failed_execution"))
        return "PASS" if status == "accepted" else "FAILED_WITH_EVIDENCE"
    return "FAILED_WITH_EVIDENCE"


class Stage0SmokeFamilyRunnerV1:
    def __init__(self, adapter):
        if adapter.family not in FAMILY_CLASSES:
            raise ValueError("Stage 0 family runner received unsupported family")
        self.adapter = adapter

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        shared_preflight_blocker: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        family = self.adapter.family
        programs = FAMILY_CLASSES[family]().checked_provisional_programs()
        realization = {
            item["program_id"]: {
                "realization": "r_pc",
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
                "stage0_smoke": True,
            }
            for item in programs
        }
        root_dir = output_dir / "root"
        if shared_preflight_blocker is None:
            root = RealSapienStrictPrefixRootOrchestratorV1_2(
                self.adapter,
                implementation_version=IMPLEMENTATION_VERSION,
            ).run_nonformal_root(
                output_dir=root_dir,
                planned_root_slot_spec=planned_root_slot_spec,
                realization_spec_by_program=realization,
                stage0_data=True,
                stage0_authorized=True,
            )
        else:
            root = {
                "schema_version": "cmf_stage0_shared_preflight_blocked_root_v1",
                "implementation_version": IMPLEMENTATION_VERSION,
                "design_version": "controlled_multi_future_f1_f4_v1_2",
                "family": family,
                "status": "failed_shared_preflight_with_evidence",
                "shared_preflight_blocker": dict(shared_preflight_blocker),
                "branch_receipts": [],
                "cleanup_records": [],
                "budget_counts": {
                    "planner_query_count": 0,
                    "execution_attempt_count": 0,
                    "recovery_attempt_count": 0,
                },
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
            }
            root["receipt_sha256"] = hash_json(root)
            root_dir.mkdir(parents=True, exist_ok=False)
            _write_json(root_dir / "root_receipt.json", root)
        branches = {
            str(item.get("program_id")): item
            for item in root.get("branch_receipts", [])
        }
        attempts = []
        for index, program in enumerate(programs):
            program_id = program["program_id"]
            branch = branches.get(program_id)
            branch_path = root_dir / "branches" / program_id / "receipt.json"
            status = _attempt_status(branch, str(root.get("status")))
            attempt = {
                "schema_version": "cmf_stage0_smoke_attempt_receipt_v1",
                "attempt_id": f"stage0-{family}-rootA-{index + 1:02d}",
                "family": family,
                "root_slot_id": str(planned_root_slot_spec["slot_id"]),
                "program_id": program_id,
                "realization": "r_pc",
                "planned_attempt": True,
                "controller_execution_started": branch is not None,
                "trajectory_generated": branch is not None
                and isinstance(branch.get("raw_manifest"), Mapping),
                "verifier_pass": branch is not None
                and branch.get("verifier", {}).get("pass") is True,
                "branch_status": None if branch is None else branch.get("status"),
                "root_status": root.get("status"),
                "terminal_status": status,
                "failure_type": (
                    None
                    if status == "PASS"
                    else branch.get("error_type")
                    if branch is not None
                    else root.get("error_type")
                    or root.get("status")
                ),
                "failure_message": (
                    None
                    if status == "PASS"
                    else branch.get("error")
                    if branch is not None
                    else root.get("error")
                    or "shared root Gate stopped before branch execution"
                ),
                "branch_receipt": _file_reference(branch_path, output_dir),
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
            }
            attempt["receipt_sha256"] = hash_json(attempt)
            attempts.append(attempt)
        for attempt in attempts:
            attempt_dir = output_dir / "attempt_receipts"
            attempt_dir.mkdir(parents=True, exist_ok=True)
            _write_json(
                attempt_dir / f"{attempt['attempt_id']}.json", attempt
            )
        success_count = sum(item["terminal_status"] == "PASS" for item in attempts)
        failed_count = len(attempts) - success_count
        cleanup_records = list(root.get("cleanup_records", []))
        cleanup_pass = all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in cleanup_records
        ) if cleanup_records else shared_preflight_blocker is not None
        outcome = "PASS" if success_count == 3 else "FAILED_WITH_EVIDENCE"
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": IMPLEMENTATION_VERSION,
            "family": family,
            "root_slot_id": str(planned_root_slot_spec["slot_id"]),
            "stage0_attempt_count": 3,
            "successful_attempt_count": success_count,
            "failed_attempt_count": failed_count,
            "generated_trajectory_count": sum(
                item["trajectory_generated"] for item in attempts
            ),
            "attempt_receipts": attempts,
            "root_status": root.get("status"),
            "root_receipt": _file_reference(
                root_dir / "root_receipt.json", output_dir
            ),
            "budget_counts": dict(root.get("budget_counts", {})),
            "cleanup_pass": cleanup_pass,
            "cleanup_records": cleanup_records,
            "orphan_process_count": sum(
                int(item.get("orphan_process_count") or 0)
                for item in cleanup_records
            ),
            "outcome": outcome,
            "pipeline_integrity_pass": len(attempts) == 3 and cleanup_pass,
            "formal_data": False,
            "stage0_data": True,
            "stage0_authorized": True,
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "stage0_family_receipt.json", receipt)
        return receipt


__all__ = ["Stage0SmokeFamilyRunnerV1"]
