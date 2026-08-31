"""One-family Stage 0 smoke runner with exactly three terminal attempts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .root_orchestrator_v1_1 import _write_json
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from .raw_writer import verify_raw_artifact_integrity


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


def _attempt_status(
    branch: Mapping[str, Any] | None,
    root_status: str,
    *,
    raw_integrity_pass: bool,
) -> str:
    if branch is not None:
        status = str(branch.get("status", "failed_execution"))
        return (
            "PASS"
            if status == "accepted"
            and root_status == "accepted"
            and raw_integrity_pass
            and branch.get("verifier", {}).get("pass") is True
            else "FAILED_WITH_EVIDENCE"
        )
    return "FAILED_WITH_EVIDENCE"


def _validate_planned_spec(
    planned: Mapping[str, Any], family: str, program_ids: list[str]
) -> dict[str, Any]:
    stored = planned.get("planned_root_slot_spec_sha256")
    payload = dict(planned)
    payload.pop("planned_root_slot_spec_sha256", None)
    payload.pop("stage0_manifest_sha256", None)
    payload.pop("stage0_manifest_attempt_count", None)
    expected_attempt_ids = [
        f"stage0-{family}-rootA-{index + 1:02d}" for index in range(3)
    ]
    checks = {
        "family_exact": planned.get("family") == family,
        "program_ids_exact": planned.get("program_ids") == program_ids,
        "attempt_ids_exact": planned.get("stage0_attempt_ids")
        == expected_attempt_ids,
        "realizations_exact_r_pc": planned.get("realizations")
        == ["r_pc", "r_pc", "r_pc"],
        "stage0_flags": planned.get("stage0_data") is True
        and planned.get("stage0_authorized") is True
        and planned.get("formal_data") is False,
        "root_spec_self_hash": isinstance(stored, str)
        and hash_json(payload) == stored,
    }
    return {"checks": checks, "pass": all(checks.values())}


def _raw_integrity(
    branch_dir: Path,
    branch: Mapping[str, Any] | None,
    *,
    family: str,
    program_id: str,
    attempt_id: str,
    root_slot_id: str,
    stage0_manifest_sha256: str,
    expected_implementation_version: str | None = None,
) -> dict:
    if branch is None or not isinstance(branch.get("raw_manifest"), Mapping):
        return {"pass": False, "reason": "raw_manifest_missing"}
    raw_dir = branch_dir / "raw"
    try:
        integrity = verify_raw_artifact_integrity(raw_dir)
    except BaseException as exc:
        return {
            "pass": False,
            "reason": "raw_integrity_exception",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    manifest = integrity.get("manifest", {})
    provenance = manifest.get("provenance", {})
    realization = provenance.get("realization_spec", {})
    branch_manifest = branch.get("raw_manifest", {})
    flags = {
        "stage0_data": manifest.get("stage0_data") is True,
        "stage0_authorized": manifest.get("stage0_authorized") is True,
        "formal_data_false": manifest.get("formal_data") is False,
        "family_exact": provenance.get("family") == family,
        "program_exact": provenance.get("program_id") == program_id,
        "implementation_exact": expected_implementation_version is None
        or provenance.get("implementation_version")
        == expected_implementation_version,
        "realization_exact_r_pc": realization.get("realization") == "r_pc",
        "attempt_root_manifest_bound": realization.get("stage0_attempt_id")
        == attempt_id
        and realization.get("stage0_root_slot_id") == root_slot_id
        and realization.get("stage0_manifest_sha256")
        == stage0_manifest_sha256,
        "provenance_stage0": provenance.get("stage0_data") is True
        and provenance.get("stage0_authorized") is True
        and provenance.get("formal_data") is False,
        "branch_manifest_matches_disk": branch_manifest.get(
            "raw_streams_npz_sha256"
        )
        == manifest.get("raw_streams_npz_sha256")
        and branch_manifest.get("manifest_payload_sha256")
        == manifest.get("manifest_payload_sha256"),
    }
    return {
        "pass": integrity.get("pass") is True and all(flags.values()),
        "integrity_checks": integrity.get("checks"),
        "data_role_checks": flags,
        "raw_streams_npz_sha256": manifest.get("raw_streams_npz_sha256"),
        "manifest_payload_sha256": manifest.get("manifest_payload_sha256"),
    }


def _audit_root_terminal_evidence(root: Mapping[str, Any]) -> dict[str, Any]:
    status = str(root.get("status"))
    branches = list(root.get("branch_receipts", []))
    task_receipts = list(root.get("task_physical_feasibility_receipts", []))
    suffix_receipts = list(root.get("suffix_planner_receipts", []))
    checks = {"recognized_terminal_status": False}
    if status == "accepted":
        checks = {
            "recognized_terminal_status": True,
            "root_finalizer_accepted": root.get("root_finalization", {}).get(
                "accepted"
            )
            is True,
            "three_clean_accepted_branches": len(branches) == 3
            and all(
                item.get("status") == "accepted"
                and not item.get("error_type")
                for item in branches
            ),
        }
    elif status == "failed_verifier":
        checks = {
            "recognized_terminal_status": True,
            "three_branches_present": len(branches) == 3,
            "no_branch_implementation_exception": len(branches) == 3
            and all(
                item.get("status") in ("accepted", "failed_verifier")
                and not item.get("error_type")
                and not item.get("traceback")
                for item in branches
            ),
            "at_least_one_explicit_verifier_failure": any(
                item.get("status") == "failed_verifier"
                and item.get("verifier", {}).get("pass") is False
                for item in branches
            ),
            "root_finalizer_rejected": root.get("root_finalization", {}).get(
                "accepted"
            )
            is False,
        }
    elif status == "failed_task_physical_feasibility":
        checks = {
            "recognized_terminal_status": True,
            "three_task_receipts": len(task_receipts) == 3,
            "structured_task_failure": len(task_receipts) == 3
            and any(item.get("status") == "failed" for item in task_receipts)
            and all(isinstance(item.get("evidence"), Mapping) for item in task_receipts)
            and all(
                item.get("task_infrastructure_failure") is not True
                and item.get("failure_stage") is None
                for item in task_receipts
            ),
        }
    elif status in ("failed_planner", "failed_family_suffix_gate"):
        checks = {
            "recognized_terminal_status": True,
            "three_suffix_receipts": len(suffix_receipts) == 3,
            "no_suffix_implementation_error": len(suffix_receipts) == 3
            and all(
                item.get("failure_stage") != "suffix_implementation_error"
                and item.get("status") != "failed_implementation_error"
                for item in suffix_receipts
            ),
            "all_suffix_receipts_structured": len(suffix_receipts) == 3
            and all(
                isinstance(item.get("evidence"), Mapping)
                and bool(item["evidence"])
                and isinstance(item.get("actual_prefix_end_qpos_sha256"), str)
                and (
                    item.get("planner_solvable") is True
                    or isinstance(item.get("failure_type"), str)
                    and bool(item["failure_type"])
                )
                for item in suffix_receipts
            ),
            "explicit_planner_or_family_gate_failure": any(
                item.get("planner_solvable") is False for item in suffix_receipts
            )
            or root.get("family_suffix_gate", {}).get("pass") is False,
            "family_gate_evidence_complete_if_used": status != "failed_family_suffix_gate"
            or (
                root.get("family_suffix_gate", {}).get("evidence_complete")
                is True
                and root.get("family_suffix_gate", {}).get(
                    "scientific_gate_pass"
                )
                is False
            ),
        }
    elif status == "failed_prefix_replay_gate":
        prefix_failures = [
            item.get("prefix_replay_failure")
            or item.get("evidence", {}).get("prefix_replay_failure")
            for item in suffix_receipts
            if isinstance(
                item.get("prefix_replay_failure")
                or item.get("evidence", {}).get("prefix_replay_failure"),
                Mapping,
            )
        ]
        checks = {
            "recognized_terminal_status": True,
            "prefix_failure_receipt_present": bool(prefix_failures),
            "exact_prefix_replay_remained_equivalent": bool(prefix_failures)
            and all(
                item.get("prefix_end_equivalent") is True
                for item in prefix_failures
            ),
            "explicit_physical_prefix_gate_failure": any(
                isinstance(
                    item.get("replayed_prefix_physical_acceptance"), Mapping
                )
                and item["replayed_prefix_physical_acceptance"].get("pass")
                is False
                for item in prefix_failures
            ),
            "no_suffix_implementation_error": all(
                item.get("failure_stage") != "suffix_implementation_error"
                for item in suffix_receipts
            ),
        }
    elif status == "failed_execution" and root.get("error_type") == (
        "F3PreVBoundaryGateFailure"
    ):
        prefix_failure = root.get("canonical_prefix_failure_receipt")
        checks = {
            "recognized_terminal_status": True,
            "f3_structured_prefix_failure": isinstance(prefix_failure, Mapping)
            and prefix_failure.get("error_type") == "F3PreVBoundaryGateFailure"
            and isinstance(prefix_failure.get("structured_gate_evidence"), Mapping),
            "no_branch_execution": not branches,
        }
    elif status == "failed_shared_preflight_with_evidence":
        checks = {
            "recognized_terminal_status": True,
            "shared_preflight_blocker_present": isinstance(
                root.get("shared_preflight_blocker"), Mapping
            ),
            "no_branch_execution": not branches,
        }
    return {
        "status": status,
        "checks": checks,
        "pass": all(checks.values()),
    }


class Stage0SmokeFamilyRunnerV1:
    def __init__(self, adapter, *, implementation_version=IMPLEMENTATION_VERSION):
        if adapter.family not in FAMILY_CLASSES:
            raise ValueError("Stage 0 family runner received unsupported family")
        if not isinstance(implementation_version, str) or not implementation_version:
            raise ValueError("Stage 0 family runner implementation version is invalid")
        self.adapter = adapter
        self.implementation_version = implementation_version

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
        program_ids = [item["program_id"] for item in programs]
        planned_spec_audit = _validate_planned_spec(
            planned_root_slot_spec, family, program_ids
        )
        if planned_spec_audit["pass"] is not True:
            raise ValueError(
                f"Stage 0 planned root spec failed: {planned_spec_audit['checks']}"
            )
        realization = {
            item["program_id"]: {
                "realization": "r_pc",
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
                "stage0_smoke": True,
                "stage0_attempt_id": planned_root_slot_spec[
                    "stage0_attempt_ids"
                ][index],
                "stage0_root_slot_id": planned_root_slot_spec["slot_id"],
                "stage0_manifest_sha256": planned_root_slot_spec.get(
                    "stage0_manifest_sha256"
                ),
            }
            for index, item in enumerate(programs)
        }
        root_dir = output_dir / "root"
        if shared_preflight_blocker is None:
            root = RealSapienStrictPrefixRootOrchestratorV1_2(
                self.adapter,
                implementation_version=self.implementation_version,
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
                "implementation_version": self.implementation_version,
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
        branch_raw_contract_checks = []
        for index, program in enumerate(programs):
            program_id = program["program_id"]
            branch = branches.get(program_id)
            branch_path = root_dir / "branches" / program_id / "receipt.json"
            raw_integrity = _raw_integrity(
                branch_path.parent,
                branch,
                family=family,
                program_id=program_id,
                attempt_id=f"stage0-{family}-rootA-{index + 1:02d}",
                root_slot_id=str(planned_root_slot_spec["slot_id"]),
                stage0_manifest_sha256=str(
                    planned_root_slot_spec.get("stage0_manifest_sha256")
                ),
            )
            branch_reference = _file_reference(branch_path, output_dir)
            status = _attempt_status(
                branch,
                str(root.get("status")),
                raw_integrity_pass=raw_integrity["pass"],
            )
            if status == "PASS" and branch_reference is None:
                status = "FAILED_WITH_EVIDENCE"
            raw_required = branch is not None and branch.get("status") in (
                "accepted",
                "failed_verifier",
            )
            raw_contract_pass = (not raw_required) or (
                raw_integrity["pass"] and branch_reference is not None
            )
            branch_raw_contract_checks.append(
                {
                    "program_id": program_id,
                    "raw_required": raw_required,
                    "pass": raw_contract_pass,
                }
            )
            attempt = {
                "schema_version": "cmf_stage0_smoke_attempt_receipt_v1",
                "attempt_id": f"stage0-{family}-rootA-{index + 1:02d}",
                "family": family,
                "root_slot_id": str(planned_root_slot_spec["slot_id"]),
                "program_id": program_id,
                "realization": "r_pc",
                "planned_attempt": True,
                "controller_execution_started": branch is not None
                and "suffix_execution_planner_query_delta" in branch,
                "trajectory_generated": raw_integrity["pass"],
                "raw_required_by_branch_status": raw_required,
                "raw_integrity": raw_integrity,
                "verifier_pass": branch is not None
                and branch.get("verifier", {}).get("pass") is True,
                "branch_status": None if branch is None else branch.get("status"),
                "root_status": root.get("status"),
                "terminal_status": status,
                "failure_type": (
                    None
                    if status == "PASS"
                    else (None if branch is None else branch.get("error_type"))
                    or root.get("error_type")
                    or root.get("status")
                ),
                "failure_message": (
                    None
                    if status == "PASS"
                    else (None if branch is None else branch.get("error"))
                    or root.get("error")
                    or "shared root Gate stopped before branch execution"
                ),
                "branch_receipt": branch_reference,
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
        root_status = str(root.get("status"))
        root_terminal_audit = _audit_root_terminal_evidence(root)
        root_terminal_evidence_complete = root_terminal_audit["pass"]
        root_acceptance_consistent = (
            root_status != "accepted"
            or root.get("root_finalization", {}).get("accepted") is True
        )
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": self.implementation_version,
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
            "planned_spec_audit": planned_spec_audit,
            "root_terminal_evidence_complete": root_terminal_evidence_complete,
            "root_terminal_evidence_audit": root_terminal_audit,
            "root_acceptance_consistent": root_acceptance_consistent,
            "branch_raw_contract_checks": branch_raw_contract_checks,
            "all_required_branch_raw_complete": all(
                item["pass"] for item in branch_raw_contract_checks
            ),
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
            "pipeline_integrity_pass": len(attempts) == 3
            and cleanup_pass
            and planned_spec_audit["pass"]
            and root_terminal_evidence_complete
            and root_acceptance_consistent
            and all(item["pass"] for item in branch_raw_contract_checks),
            "formal_data": False,
            "stage0_data": True,
            "stage0_authorized": True,
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "stage0_family_receipt.json", receipt)
        return receipt


__all__ = ["Stage0SmokeFamilyRunnerV1"]
