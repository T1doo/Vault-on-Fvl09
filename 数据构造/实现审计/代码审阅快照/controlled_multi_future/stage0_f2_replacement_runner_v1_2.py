"""Exactly-once F2 Stage-0 replacement runner with frozen-layout lineage."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .current_hasher import hash_json
from .families import F2TargetRelation
from .geometry import quaternion_orientation_error
from .root_orchestrator_v1_1 import _write_json
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from .stage0_f2_replacement_manifest_v1_2 import (
    IMPLEMENTATION_VERSION,
    ORIGINAL_ATTEMPT_IDS,
    ORIGINAL_INTENDED_ANCHOR,
    ORIGINAL_INTENDED_CURRENT,
    PROGRAM_IDS,
    REPLACEMENT_ATTEMPT_IDS,
    SCOPE,
    validate_stage0_f2_replacement_manifest_v1_2,
)
from .stage0_smoke_family_runner_v1 import (
    _audit_root_terminal_evidence,
    _file_reference,
    _raw_integrity,
)
from .stage0_smoke_family_runner_v1_1 import (
    _stage0_video_integrity,
    classify_stage0_attempt_outcome_v1_1,
)


SCHEMA_VERSION = "cmf_stage0_f2_replacement_family_runner_v1_2"


def _self_hash(value: Mapping[str, Any], field: str) -> bool:
    payload = dict(value)
    digest = payload.pop(field, None)
    return isinstance(digest, str) and hash_json(payload) == digest


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pose_audit(actual, expected) -> dict[str, Any]:
    actual_value = np.asarray(actual, dtype=np.float64).reshape(7)
    expected_value = np.asarray(expected, dtype=np.float64).reshape(7)
    position_error = float(np.linalg.norm(actual_value[:3] - expected_value[:3]))
    orientation_error = float(
        quaternion_orientation_error(actual_value[3:], expected_value[3:])
    )
    return {
        "position_error_m": position_error,
        "orientation_error_rad": orientation_error,
        "pass": position_error <= 2e-5 and orientation_error <= 2e-4,
    }


def audit_f2_replacement_current_anchor_lineage_v1_2(
    replacement_root_dir: Path,
) -> dict[str, Any]:
    root = Path(replacement_root_dir)
    replacement_anchor_path = root / "reference_anchor.json"
    replacement_current_path = root / "reference_current_hashes.json"
    replacement_anchor = _load_json(replacement_anchor_path)
    replacement_current = _load_json(replacement_current_path)
    intended_anchor = _load_json(ORIGINAL_INTENDED_ANCHOR)
    intended_current = _load_json(ORIGINAL_INTENDED_CURRENT)
    invalid_anchor_path = (
        Path("/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计")
        / "stage0_outputs/controlled_multi_future_stage0_smoke_v1_1"
        / "stage0_smoke_v1_1_F2_root_A_seed20260829_run1"
        / "stage0_family/root/reference_anchor.json"
    )
    invalid_current_path = invalid_anchor_path.with_name(
        "reference_current_hashes.json"
    )
    invalid_anchor = _load_json(invalid_anchor_path)
    invalid_current = _load_json(invalid_current_path)
    facilities = {}
    for role in ("box", "scale", "stand"):
        facilities[role] = _pose_audit(
            replacement_anchor["facility_poses"][role],
            intended_anchor["facility_poses"][role],
        )
    actor = _pose_audit(
        replacement_anchor["actor_states"]["main_can"]["pose"],
        intended_anchor["actor_states"]["main_can"]["pose"],
    )
    model_visible_keys = (
        "camera_configuration_sha256",
        "gripper_actual_state_sha256",
        "head_rgb_sha256",
        "robot_state_sha256",
        "visible_object_roles_sha256",
        "wrist_rgb_sha256",
    )
    replacement_components = replacement_current["model_visible_components"]
    intended_components = intended_current["model_visible_components"]
    component_checks = {
        key: replacement_components.get(key) == intended_components.get(key)
        for key in model_visible_keys
    }
    checks = {
        "replacement_files_exist": replacement_anchor_path.is_file()
        and replacement_current_path.is_file(),
        "intended_reference_files_exist": ORIGINAL_INTENDED_ANCHOR.is_file()
        and ORIGINAL_INTENDED_CURRENT.is_file(),
        "facility_pose_equivalence": all(
            item["pass"] for item in facilities.values()
        ),
        "main_can_pose_equivalence": actor["pass"],
        "main_can_velocity_equivalence": np.allclose(
            replacement_anchor["actor_states"]["main_can"]["linear_velocity"],
            intended_anchor["actor_states"]["main_can"]["linear_velocity"],
            rtol=0.0,
            atol=1e-8,
        )
        and np.allclose(
            replacement_anchor["actor_states"]["main_can"]["angular_velocity"],
            intended_anchor["actor_states"]["main_can"]["angular_velocity"],
            rtol=0.0,
            atol=1e-8,
        ),
        "model_visible_current_components_exact": all(component_checks.values()),
        "invalid_default_layout_is_not_replacement": replacement_anchor.get(
            "anchor_sha256"
        )
        != invalid_anchor.get("anchor_sha256")
        and replacement_current.get("model_visible_aggregate_sha256")
        != invalid_current.get("model_visible_aggregate_sha256"),
        "original_invalid_current_not_claimed_equivalent": True,
    }
    result = {
        "schema_version": "cmf_f2_replacement_current_anchor_lineage_audit_v1_2",
        "replacement_anchor_path": str(replacement_anchor_path.resolve()),
        "replacement_current_path": str(replacement_current_path.resolve()),
        "intended_anchor_path": str(ORIGINAL_INTENDED_ANCHOR.resolve()),
        "intended_current_path": str(ORIGINAL_INTENDED_CURRENT.resolve()),
        "original_invalid_anchor_path": str(invalid_anchor_path.resolve()),
        "original_invalid_current_path": str(invalid_current_path.resolve()),
        "original_attempt_current_comparability": (
            "not_comparable_due_to_missing_layout_binding_and_default_layout_drift"
        ),
        "facility_pose_audits": facilities,
        "main_can_pose_audit": actor,
        "model_visible_component_checks": component_checks,
        "checks": checks,
        "pass": all(checks.values()),
    }
    result["receipt_sha256"] = hash_json(result)
    return result


def _planned_spec_audit(
    planned: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    stored = planned.get("planned_root_slot_spec_sha256")
    payload = dict(planned)
    payload.pop("planned_root_slot_spec_sha256", None)
    payload.pop("stage0_replacement_manifest_sha256", None)
    checks = {
        "family_scope": planned.get("family") == "F2"
        and planned.get("scope") == SCOPE,
        "generator": planned.get("generator")
        == "controlled_multi_future_stage0_smoke_v1_2_adapter_v1_8",
        "programs": planned.get("program_ids") == list(PROGRAM_IDS),
        "attempt_ids": planned.get("stage0_attempt_ids")
        == list(REPLACEMENT_ATTEMPT_IDS),
        "replacement_ids": planned.get("replacement_for_attempt_ids")
        == list(ORIGINAL_ATTEMPT_IDS),
        "replacement_reason": planned.get("replacement_reason")
        == "frozen_scene_layout_wiring_fix",
        "realizations": planned.get("realizations") == ["r_pc"] * 3,
        "self_hash": isinstance(stored, str) and hash_json(payload) == stored,
        "manifest_spec": stored == manifest.get("replacement_root_spec_sha256"),
        "stage0_not_formal": planned.get("stage0_data") is True
        and planned.get("formal_data") is False
        and planned.get("stage1_authorized") is False,
    }
    return {"checks": checks, "pass": all(checks.values())}


class Stage0F2ReplacementRunnerV1_2:
    def __init__(self, adapter):
        if adapter.family != "F2":
            raise ValueError("Stage 0 v1.2 replacement runner is F2-only")
        self.adapter = adapter

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        replacement_manifest: Mapping[str, Any],
    ) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        manifest = validate_stage0_f2_replacement_manifest_v1_2(
            replacement_manifest
        )
        planned_audit = _planned_spec_audit(planned_root_slot_spec, manifest)
        if not planned_audit["pass"]:
            raise ValueError(
                f"F2 replacement planned spec failed: {planned_audit['checks']}"
            )
        manifest_sha = manifest["manifest_sha256"]
        planned = dict(planned_root_slot_spec)
        planned["stage0_replacement_manifest_sha256"] = manifest_sha
        programs = F2TargetRelation().checked_provisional_programs()
        realization = {
            program_id: {
                "realization": "r_pc",
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
                "stage0_f2_replacement": True,
                "implementation_version": IMPLEMENTATION_VERSION,
                "stage0_attempt_id": REPLACEMENT_ATTEMPT_IDS[index],
                "replacement_for_attempt_id": ORIGINAL_ATTEMPT_IDS[index],
                "replacement_reason": "frozen_scene_layout_wiring_fix",
                "stage0_root_slot_id": planned["slot_id"],
                "stage0_manifest_sha256": manifest_sha,
            }
            for index, program_id in enumerate(PROGRAM_IDS)
        }
        root_dir = output_dir / "root"
        root = RealSapienStrictPrefixRootOrchestratorV1_2(
            self.adapter, implementation_version=IMPLEMENTATION_VERSION
        ).run_nonformal_root(
            output_dir=root_dir,
            planned_root_slot_spec=planned,
            realization_spec_by_program=realization,
            stage0_data=True,
            stage0_authorized=True,
        )
        lineage = audit_f2_replacement_current_anchor_lineage_v1_2(root_dir)
        _write_json(output_dir / "f2_current_anchor_lineage_audit.json", lineage)
        branches = {
            str(item.get("program_id")): item
            for item in root.get("branch_receipts", [])
        }
        attempts = []
        raw_checks = []
        video_checks = []
        for index, program_id in enumerate(PROGRAM_IDS):
            branch = branches.get(program_id)
            branch_path = root_dir / "branches" / program_id / "receipt.json"
            raw = _raw_integrity(
                branch_path.parent,
                branch,
                family="F2",
                program_id=program_id,
                attempt_id=REPLACEMENT_ATTEMPT_IDS[index],
                root_slot_id=planned["slot_id"],
                stage0_manifest_sha256=manifest_sha,
                expected_implementation_version=IMPLEMENTATION_VERSION,
            )
            branch_ref = _file_reference(branch_path, output_dir)
            video = _stage0_video_integrity(
                branch_path.parent, branch, trajectory_generated=raw["pass"]
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
            raw_checks.append(
                {
                    "program_id": program_id,
                    "raw_required": raw_required,
                    "pass": (not raw_required)
                    or (raw["pass"] and branch_ref is not None),
                }
            )
            video_checks.append(
                {
                    "program_id": program_id,
                    "video_required": raw["pass"],
                    "pass": video["pass"],
                }
            )
            attempt = {
                "schema_version": "cmf_stage0_f2_replacement_attempt_receipt_v1_2",
                "implementation_version": IMPLEMENTATION_VERSION,
                "attempt_id": REPLACEMENT_ATTEMPT_IDS[index],
                "replacement_for_attempt_id": ORIGINAL_ATTEMPT_IDS[index],
                "superseded_terminal_status": "FAILED_INFRASTRUCTURE_WITH_EVIDENCE",
                "replacement_reason": "frozen_scene_layout_wiring_fix",
                "family": "F2",
                "root_slot_id": planned["slot_id"],
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
                "layout_payload_sha256": planned["layout_payload_sha256"],
                "stage0_replacement_manifest_sha256": manifest_sha,
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
                "stage1_authorized": False,
            }
            attempt["receipt_sha256"] = hash_json(attempt)
            attempts.append(attempt)
            attempt_dir = output_dir / "attempt_receipts"
            attempt_dir.mkdir(parents=True, exist_ok=True)
            _write_json(attempt_dir / f"{attempt['attempt_id']}.json", attempt)
        cleanup_records = list(root.get("cleanup_records", []))
        cleanup_pass = bool(cleanup_records) and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in cleanup_records
        )
        root_audit = _audit_root_terminal_evidence(root)
        success_count = sum(
            item["terminal_status"] == "PASSED" for item in attempts
        )
        active_no_infrastructure = all(
            item["terminal_status"] != "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
            for item in attempts
        )
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": IMPLEMENTATION_VERSION,
            "family": "F2",
            "scope": SCOPE,
            "root_slot_id": planned["slot_id"],
            "replacement_manifest_sha256": manifest_sha,
            "stage0_attempt_count": 3,
            "successful_attempt_count": success_count,
            "failed_attempt_count": 3 - success_count,
            "generated_trajectory_count": sum(
                item["trajectory_generated"] for item in attempts
            ),
            "generated_video_count": sum(
                item["video_required"]
                and item["video_integrity"].get("pass") is True
                for item in attempts
            ),
            "attempt_receipts": attempts,
            "root_status": root.get("status"),
            "root_terminal_evidence_audit": root_audit,
            "planned_spec_audit": planned_audit,
            "current_anchor_lineage_audit": lineage,
            "branch_raw_contract_checks": raw_checks,
            "branch_video_contract_checks": video_checks,
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
            "outcome": "PASS"
            if success_count == 3
            else "FAILED_WITH_EVIDENCE",
            "active_slot_terminal_evidence_valid": active_no_infrastructure,
            "pipeline_integrity_pass": len(attempts) == 3
            and planned_audit["pass"]
            and lineage["pass"]
            and cleanup_pass
            and root_audit["pass"]
            and all(item["pass"] for item in raw_checks)
            and all(item["pass"] for item in video_checks)
            and active_no_infrastructure,
            "all_required_videos_complete": all(
                item["pass"] for item in video_checks
            ),
            "formal_data": False,
            "stage0_data": True,
            "stage0_authorized": True,
            "stage1_authorized": False,
            "formal_collection_authorized": False,
            "training_authorized": False,
        }
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "stage0_f2_replacement_family_receipt.json", receipt)
        return receipt


__all__ = [
    "Stage0F2ReplacementRunnerV1_2",
    "audit_f2_replacement_current_anchor_lineage_v1_2",
]
