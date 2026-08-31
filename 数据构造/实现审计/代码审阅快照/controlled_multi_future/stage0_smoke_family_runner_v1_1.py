"""One-family Stage-0 v1.1 runner; exactly three planned r_pc attempts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .f4_frozen_canonical_neutral_binding_v13 import (
    canonical_neutral_pose_sha256_v13,
    validate_f4_frozen_canonical_neutral_binding_v13,
)
from .root_orchestrator_v1_1 import _write_json
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from .stage0_smoke_family_runner_v1 import (
    _audit_root_terminal_evidence,
    _file_reference,
    _raw_integrity,
)
from .stage0_smoke_budget_v1_1 import budget_artifact
from .stage0_video_capture_v1 import (
    validate_stage0_trajectory_mp4_receipt_v1,
)


SCHEMA_VERSION = "cmf_stage0_smoke_family_runner_v1_1"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1_1"
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}
TERMINAL_OUTCOMES = (
    "PASSED",
    "FAILED_PLANNER_WITH_EVIDENCE",
    "FAILED_EXECUTION_WITH_EVIDENCE",
    "FAILED_VERIFIER_WITH_EVIDENCE",
    "FAILED_INFRASTRUCTURE_WITH_EVIDENCE",
)
INFRASTRUCTURE_ROOT_STATUSES = {
    "failed_cleanup_uncertain",
    "failed_current_hash",
    "failed_anchor_equivalence",
    "failed_implementation_error",
    "failed_candidate_mutation",
}
PLANNER_ROOT_STATUSES = {
    "failed_planner",
    "failed_family_suffix_gate",
    "failed_shared_preflight_with_evidence",
}
PHYSICAL_EXECUTION_ROOT_STATUSES = {
    "failed_task_physical_feasibility",
    "failed_prefix_replay_gate",
}


def classify_stage0_attempt_outcome_v1_1(
    branch: Mapping[str, Any] | None,
    root: Mapping[str, Any],
    *,
    raw_integrity_pass: bool,
    branch_receipt_present: bool,
    video_integrity_pass: bool = True,
) -> str:
    root_status = str(root.get("status"))
    if root_status in INFRASTRUCTURE_ROOT_STATUSES:
        return "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
    if branch is not None:
        branch_status = str(branch.get("status", "failed_execution"))
        if branch_status == "accepted":
            if (
                raw_integrity_pass
                and branch_receipt_present
                and video_integrity_pass
                and branch.get("verifier", {}).get("pass") is True
            ):
                return "PASSED"
            return "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
        if branch_status == "failed_verifier":
            return (
                "FAILED_VERIFIER_WITH_EVIDENCE"
                if raw_integrity_pass
                and branch_receipt_present
                and video_integrity_pass
                else "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
            )
        if branch_status == "failed_execution":
            return "FAILED_EXECUTION_WITH_EVIDENCE"
        if branch_status == "failed_cleanup_uncertain":
            return "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
    if root_status in PHYSICAL_EXECUTION_ROOT_STATUSES or (
        root_status == "failed_execution"
        and root.get("error_type") == "F3PreVBoundaryGateFailure"
    ):
        return "FAILED_EXECUTION_WITH_EVIDENCE"
    if root_status in PLANNER_ROOT_STATUSES:
        return "FAILED_PLANNER_WITH_EVIDENCE"
    return "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"


def _stage0_video_integrity(
    branch_dir: Path,
    branch: Mapping[str, Any] | None,
    *,
    trajectory_generated: bool,
) -> dict[str, Any]:
    if not trajectory_generated:
        return {
            "required": False,
            "applicable": False,
            "status": "video_not_applicable_no_trajectory",
            "pass": True,
        }
    if not isinstance(branch, Mapping):
        return {
            "required": True,
            "applicable": True,
            "status": "missing_branch_receipt",
            "pass": False,
        }
    expected = branch_dir / "video" / "trajectory.mp4"
    try:
        audit = validate_stage0_trajectory_mp4_receipt_v1(
            branch.get("stage0_video_receipt"),
            expected_path=expected,
        )
    except BaseException as exc:
        return {
            "required": True,
            "applicable": True,
            "status": "failed_required_video",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "pass": False,
        }
    reference = branch.get("stage0_video_file")
    reference_pass = bool(
        isinstance(reference, Mapping)
        and reference.get("relative_path") == "video/trajectory.mp4"
        and reference.get("bytes") == audit["receipt"].get("bytes")
        and reference.get("sha256") == audit["receipt"].get("file_sha256")
    )
    return {
        "required": True,
        "applicable": True,
        "status": "generated" if reference_pass else "failed_video_reference",
        "video_receipt_sha256": audit["receipt"].get("receipt_sha256"),
        "file_sha256": audit["receipt"].get("file_sha256"),
        "relative_path": "video/trajectory.mp4",
        "frame_count": audit["receipt"].get("frame_count"),
        "video_fps": audit["receipt"].get("video_fps"),
        "pass": reference_pass,
    }


def _planned_spec_audit(planned: Mapping[str, Any], family: str, program_ids: list[str]) -> dict:
    stored = planned.get("planned_root_slot_spec_sha256")
    payload = dict(planned)
    payload.pop("planned_root_slot_spec_sha256", None)
    payload.pop("stage0_manifest_sha256", None)
    payload.pop("stage0_manifest_attempt_count", None)
    expected_ids = [f"stage0-v1_1-{family}-rootA-{index + 1:02d}" for index in range(3)]
    checks = {
        "family": planned.get("family") == family,
        "scope": planned.get("scope") == f"Stage0_v1_1_{family}_root_A",
        "generator": planned.get("generator")
        == "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7",
        "program_ids": planned.get("program_ids") == program_ids,
        "attempt_ids": planned.get("stage0_attempt_ids") == expected_ids,
        "realizations": planned.get("realizations") == ["r_pc", "r_pc", "r_pc"],
        "stage0_not_formal": planned.get("stage0_data") is True
        and planned.get("stage0_authorized") is True
        and planned.get("formal_data") is False,
        "self_hash": isinstance(stored, str) and hash_json(payload) == stored,
        "video_contract": planned.get(
            "stage0_generated_trajectory_mp4_required"
        )
        is True
        and planned.get("stage0_video_contract")
        == budget_artifact()["stage0_video_contract"],
    }
    binding = None
    if family == "F4":
        try:
            binding = validate_f4_frozen_canonical_neutral_binding_v13(
                planned.get("f4_canonical_neutral_binding_v13")
            )
            checks["v13_binding"] = planned.get(
                "f4_canonical_neutral_binding_sha256_v13"
            ) == binding["binding_sha256"]
            selected13 = planned.get("selected_f4_corridor_candidate_v13")
            selected11 = planned.get("selected_f4_corridor_candidate_v11")
            checks["selected_alias_exact"] = selected13 == selected11
            if selected13 is not None:
                contract = selected13.get("candidate_contract_segments")
                applied = selected13.get("applied_planner_targets")
                checks["selected_neutral_exact"] = bool(
                    isinstance(contract, list)
                    and contract
                    and contract[-1].get("segment_id") == "A_neutral"
                    and isinstance(applied, list)
                    and applied
                    and applied[-1].get("segment_id") == "A_neutral"
                    and contract[-1].get("pose") == applied[-1].get("pose")
                    and canonical_neutral_pose_sha256_v13(contract[-1]["pose"])
                    == binding["canonical_terminal_neutral_pose_sha256"]
                )
        except (TypeError, ValueError):
            checks["v13_binding"] = False
    return {"checks": checks, "pass": all(checks.values()), "binding": binding}


class Stage0SmokeFamilyRunnerV1_1:
    def __init__(self, adapter):
        if adapter.family not in FAMILY_CLASSES:
            raise ValueError("Stage 0 v1.1 runner received unsupported family")
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
        program_ids = [item["program_id"] for item in programs]
        planned_audit = _planned_spec_audit(planned_root_slot_spec, family, program_ids)
        if not planned_audit["pass"]:
            raise ValueError(f"Stage 0 v1.1 planned spec failed: {planned_audit['checks']}")
        manifest_sha = planned_root_slot_spec.get("stage0_manifest_sha256")
        if not isinstance(manifest_sha, str) or len(manifest_sha) != 64:
            raise ValueError("Stage 0 v1.1 planned spec lacks manifest binding")
        root_slot_id = str(planned_root_slot_spec["slot_id"])
        planned_attempt_ids = list(planned_root_slot_spec["stage0_attempt_ids"])
        realization = {
            program_id: {
                "realization": "r_pc",
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
                "stage0_smoke": True,
                "implementation_version": IMPLEMENTATION_VERSION,
                "stage0_attempt_id": planned_attempt_ids[index],
                "stage0_root_slot_id": root_slot_id,
                "stage0_manifest_sha256": manifest_sha,
            }
            for index, program_id in enumerate(program_ids)
        }
        root_dir = output_dir / "root"
        if shared_preflight_blocker is None:
            root = RealSapienStrictPrefixRootOrchestratorV1_2(
                self.adapter, implementation_version=IMPLEMENTATION_VERSION
            ).run_nonformal_root(
                output_dir=root_dir,
                planned_root_slot_spec=planned_root_slot_spec,
                realization_spec_by_program=realization,
                stage0_data=True,
                stage0_authorized=True,
            )
        else:
            root = {
                "schema_version": "cmf_stage0_v1_1_shared_preflight_blocked_root",
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
        branches = {str(item.get("program_id")): item for item in root.get("branch_receipts", [])}
        attempts = []
        raw_contract_checks = []
        video_contract_checks = []
        for index, program_id in enumerate(program_ids):
            branch = branches.get(program_id)
            branch_path = root_dir / "branches" / program_id / "receipt.json"
            raw = _raw_integrity(
                branch_path.parent,
                branch,
                family=family,
                program_id=program_id,
                attempt_id=planned_attempt_ids[index],
                root_slot_id=root_slot_id,
                stage0_manifest_sha256=manifest_sha,
                expected_implementation_version=IMPLEMENTATION_VERSION,
            )
            branch_ref = _file_reference(branch_path, output_dir)
            video = _stage0_video_integrity(
                branch_path.parent,
                branch,
                trajectory_generated=raw["pass"],
            )
            status = classify_stage0_attempt_outcome_v1_1(
                branch,
                root,
                raw_integrity_pass=raw["pass"],
                branch_receipt_present=branch_ref is not None,
                video_integrity_pass=video["pass"],
            )
            raw_required = branch is not None and branch.get("status") in (
                "accepted",
                "failed_verifier",
            )
            raw_contract_checks.append(
                {
                    "program_id": program_id,
                    "raw_required": raw_required,
                    "pass": (not raw_required) or (raw["pass"] and branch_ref is not None),
                }
            )
            video_contract_checks.append(
                {
                    "program_id": program_id,
                    "video_required": raw["pass"],
                    "pass": video["pass"],
                }
            )
            attempt = {
                "schema_version": "cmf_stage0_smoke_attempt_receipt_v1_1",
                "implementation_version": IMPLEMENTATION_VERSION,
                "attempt_id": planned_attempt_ids[index],
                "family": family,
                "root_slot_id": root_slot_id,
                "program_id": program_id,
                "realization": "r_pc",
                "planned_attempt": True,
                "trajectory_generated": raw["pass"],
                "raw_required_by_branch_status": raw_required,
                "raw_integrity": raw,
                "video_required": raw["pass"],
                "mp4_required_if_trajectory_generated": True,
                "video_integrity": video,
                "video_status": video["status"],
                "verifier_pass": branch is not None
                and branch.get("verifier", {}).get("pass") is True,
                "branch_status": None if branch is None else branch.get("status"),
                "root_status": root.get("status"),
                "terminal_status": status,
                "failure_type": None
                if status == "PASSED"
                else (None if branch is None else branch.get("error_type"))
                or root.get("error_type")
                or root.get("status"),
                "failure_message": None
                if status == "PASSED"
                else (None if branch is None else branch.get("error"))
                or root.get("error")
                or "shared root Gate stopped before branch execution",
                "branch_receipt": branch_ref,
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
                "stage1_authorized": False,
            }
            if family == "F4":
                binding = planned_audit["binding"]
                attempt["f4_canonical_neutral_binding_sha256_v13"] = binding[
                    "binding_sha256"
                ]
                attempt["canonical_terminal_neutral_pose_sha256_v13"] = binding[
                    "canonical_terminal_neutral_pose_sha256"
                ]
            attempt["receipt_sha256"] = hash_json(attempt)
            attempts.append(attempt)
            attempt_dir = output_dir / "attempt_receipts"
            attempt_dir.mkdir(parents=True, exist_ok=True)
            _write_json(attempt_dir / f"{attempt['attempt_id']}.json", attempt)
        cleanup_records = list(root.get("cleanup_records", []))
        cleanup_pass = (
            all(
                item.get("cleanup_safety_pass") is True
                and int(item.get("orphan_process_count") or 0) == 0
                for item in cleanup_records
            )
            if cleanup_records
            else shared_preflight_blocker is not None
        )
        root_audit = _audit_root_terminal_evidence(root)
        root_status = str(root.get("status"))
        root_acceptance_consistent = (
            root_status != "accepted"
            or root.get("root_finalization", {}).get("accepted") is True
        )
        success_count = sum(item["terminal_status"] == "PASSED" for item in attempts)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": IMPLEMENTATION_VERSION,
            "family": family,
            "root_slot_id": root_slot_id,
            "stage0_attempt_count": 3,
            "successful_attempt_count": success_count,
            "failed_attempt_count": 3 - success_count,
            "generated_trajectory_count": sum(item["trajectory_generated"] for item in attempts),
            "generated_video_count": sum(
                item["video_integrity"].get("pass") is True
                and item["video_required"] is True
                for item in attempts
            ),
            "attempt_receipts": attempts,
            "root_status": root.get("status"),
            "root_terminal_evidence_audit": root_audit,
            "root_acceptance_consistent": root_acceptance_consistent,
            "planned_spec_audit": {k: v for k, v in planned_audit.items() if k != "binding"},
            "branch_raw_contract_checks": raw_contract_checks,
            "branch_video_contract_checks": video_contract_checks,
            "root_receipt": _file_reference(root_dir / "root_receipt.json", output_dir),
            "budget_counts": dict(root.get("budget_counts", {})),
            "cleanup_pass": cleanup_pass,
            "cleanup_records": cleanup_records,
            "orphan_process_count": sum(
                int(item.get("orphan_process_count") or 0) for item in cleanup_records
            ),
            "outcome": "PASS" if success_count == 3 else "FAILED_WITH_EVIDENCE",
            "pipeline_integrity_pass": len(attempts) == 3
            and planned_audit["pass"]
            and cleanup_pass
            and root_audit["pass"]
            and root_acceptance_consistent
            and all(item["pass"] for item in raw_contract_checks)
            and all(item["pass"] for item in video_contract_checks),
            "all_required_videos_complete": all(
                item["pass"] for item in video_contract_checks
            ),
            "formal_data": False,
            "stage0_data": True,
            "stage0_authorized": True,
            "stage1_authorized": False,
            "formal_collection_authorized": False,
            "training_authorized": False,
        }
        if family == "F4":
            receipt["f4_canonical_neutral_binding_v13"] = planned_audit["binding"]
            receipt["f4_canonical_neutral_binding_sha256_v13"] = planned_audit[
                "binding"
            ]["binding_sha256"]
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "stage0_family_receipt.json", receipt)
        return receipt


__all__ = [
    "TERMINAL_OUTCOMES",
    "Stage0SmokeFamilyRunnerV1_1",
    "classify_stage0_attempt_outcome_v1_1",
]
