"""Deterministic manifest for exactly 12 Stage 0 r_pc smoke attempts."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from .stage0_smoke_budget_v1 import budget_receipt_sha256, scope_budget


SCHEMA_VERSION = "cmf_stage0_smoke_manifest_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1"
SCENE_SEED = 20260829
CANONICAL_INFRA_RECEIPT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "probe_outputs/prestage0_f4_candidate_hash_infra_v12_seed20260829_run1/receipt.json"
)
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


def validate_stage0_smoke_manifest_structure(
    stage0_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = json.loads(
        json.dumps(stage0_manifest, sort_keys=True, allow_nan=False)
    )
    payload = dict(manifest)
    digest = payload.pop("manifest_sha256", None)
    roots = manifest.get("root_specs", {})
    attempts = manifest.get("attempts", [])
    root_checks = {}
    for family, root in roots.items():
        root_payload = dict(root)
        root_digest = root_payload.pop("planned_root_slot_spec_sha256", None)
        root_checks[family] = isinstance(root_digest, str) and hash_json(
            root_payload
        ) == root_digest
    checks = {
        "manifest_self_hash": isinstance(digest, str)
        and hash_json(payload) == digest,
        "implementation_version": manifest.get("implementation_version")
        == IMPLEMENTATION_VERSION,
        "stage0_flags": manifest.get("stage0_authorized") is True
        and manifest.get("stage0_data") is True
        and manifest.get("formal_data") is False,
        "exact_four_roots": set(roots) == set(FAMILY_CLASSES),
        "all_root_specs_self_hashed": len(root_checks) == 4
        and all(root_checks.values()),
        "exact_twelve_unique_attempts": len(attempts) == 12
        and len({item.get("attempt_id") for item in attempts}) == 12,
        "three_attempts_per_family": all(
            sum(item.get("family") == family for item in attempts) == 3
            for family in FAMILY_CLASSES
        ),
        "attempts_match_root_programs": all(
            {
                item.get("program_id")
                for item in attempts
                if item.get("family") == family
            }
            == set(roots.get(family, {}).get("program_ids", []))
            for family in FAMILY_CLASSES
        ),
    }
    return {"checks": checks, "root_checks": root_checks, "pass": all(checks.values())}


def planned_stage0_root_spec(
    family: str,
    *,
    selected_f4_candidate: Mapping[str, Any] | None = None,
    f4_shared_preflight_blocker: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if family not in FAMILY_CLASSES:
        raise ValueError("unsupported Stage 0 family")
    if family != "F4" and (
        selected_f4_candidate is not None
        or f4_shared_preflight_blocker is not None
    ):
        raise ValueError("F4-only Stage 0 metadata leaked to another family")
    if family == "F4" and selected_f4_candidate is None and f4_shared_preflight_blocker is None:
        raise ValueError("F4 Stage 0 spec needs a selected corridor or blocker")
    scope = f"Stage0_{family}_root_A"
    programs = FAMILY_CLASSES[family]().checked_provisional_programs()
    result = {
        "schema_version": "cmf_stage0_planned_root_slot_spec_v1",
        "slot_id": f"stage0-{family}-pilot-root-A",
        "family": family,
        "scope": scope,
        "seed": SCENE_SEED,
        "arm": "right" if family == "F4" else "left",
        "generator": "controlled_multi_future_stage0_smoke_v1_adapter_v1_6",
        "origin": "authorized_stage0_smoke",
        "program_ids": [item["program_id"] for item in programs],
        "realizations": ["r_pc", "r_pc", "r_pc"],
        "stage0_attempt_ids": [
            f"stage0-{family}-rootA-{index + 1:02d}"
            for index in range(3)
        ],
        "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "success_and_failure_both_retained": True,
        "accepted_root_required": False,
        "stop_condition": "terminal family receipt or cleanup/source/GPU uncertainty",
    }
    if family == "F4":
        result["scene_layout"] = json.loads(
            json.dumps(F4_LAYOUT, sort_keys=True, allow_nan=False)
        )
        result["scene_layout_sha256"] = hash_json(result["scene_layout"])
        result["selected_f4_corridor_candidate_v11"] = (
            None
            if selected_f4_candidate is None
            else json.loads(
                json.dumps(selected_f4_candidate, sort_keys=True, allow_nan=False)
            )
        )
        result["f4_shared_preflight_blocker"] = (
            None
            if f4_shared_preflight_blocker is None
            else json.loads(
                json.dumps(
                    f4_shared_preflight_blocker,
                    sort_keys=True,
                    allow_nan=False,
                )
            )
        )
    result["planned_root_slot_spec_sha256"] = hash_json(result)
    return result


def build_stage0_smoke_manifest(
    f4_infrastructure_receipt_path: Path,
    *,
    require_canonical_path: bool = True,
) -> dict[str, Any]:
    receipt_path = Path(f4_infrastructure_receipt_path).resolve()
    if require_canonical_path and receipt_path != CANONICAL_INFRA_RECEIPT:
        raise ValueError("F4 infrastructure receipt path is not canonical")
    if not receipt_path.is_file():
        raise ValueError("F4 infrastructure receipt file is missing")
    receipt_file_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    infra = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload = dict(infra)
    receipt_sha = payload.pop("guard_sealed_receipt_sha256", None)
    guard_path = Path(str(infra.get("guard_receipt", ""))).resolve()
    guard = (
        json.loads(guard_path.read_text(encoding="utf-8"))
        if guard_path.is_file()
        else {}
    )
    guard_payload = dict(guard)
    guard_digest = guard_payload.pop("guard_receipt_sha256", None)
    consumption_path = Path(str(guard.get("consumption_receipt", ""))).resolve()
    consumption = (
        json.loads(consumption_path.read_text(encoding="utf-8"))
        if consumption_path.is_file()
        else {}
    )
    consumption_payload = dict(consumption)
    consumption_digest = consumption_payload.pop(
        "consumption_receipt_sha256", None
    )
    required_infra_checks = {
        "schema_version": infra.get("schema_version")
        == "cmf_stage0_smoke_guarded_scope_receipt_v1",
        "guard_sealed_receipt_self_hash": isinstance(receipt_sha, str)
        and hash_json(payload) == receipt_sha,
        "implementation_version": infra.get("implementation_version")
        == IMPLEMENTATION_VERSION,
        "scope": infra.get("scope") == "F4_candidate_hash_infra_v12",
        "family": infra.get("family") == "F4",
        "hash_infrastructure_pass": infra.get("hash_infrastructure_pass")
        is True,
        "pipeline_integrity_pass": infra.get("pipeline_integrity_pass") is True,
        "terminal_status": infra.get("status")
        == "completed_f4_hash_infrastructure",
        "hash_audit_pass": infra.get("hash_infrastructure_audit_v12", {}).get(
            "pass"
        )
        is True,
        "real_corridor_planner_query_reached": int(
            infra.get("budget_counts", {}).get("planner_query_count", 0)
        )
        > 0,
        "cleanup_pass": infra.get("scene_cleanup_succeeded") is True
        and int(infra.get("orphan_process_count", -1)) == 0,
        "source_bound": isinstance(
            infra.get("authorization", {}).get(
                "implementation_source_sha256"
            ),
            str,
        ),
        "not_stage0_data": infra.get("stage0_data") is False
        and infra.get("formal_data") is False,
        "guard_receipt_exists": guard_path.is_file(),
        "guard_receipt_self_hash": isinstance(guard_digest, str)
        and hash_json(guard_payload) == guard_digest,
        "guard_completed": guard.get("status") == "completed",
        "guard_source_lock_pass": guard.get("post_source_lock_pass") is True,
        "guard_no_timeout_or_orphan": guard.get("timed_out") is False
        and int(guard.get("orphan_process_count", -1)) == 0,
        "guard_child_file_hash_matches": guard.get("child_receipt_file", {}).get(
            "sha256"
        )
        == receipt_file_sha256,
        "guard_binding_matches_child": guard.get("binding")
        == infra.get("gpu_guard_binding")
        == infra.get("guard_binding"),
        "consumption_receipt_exists": consumption_path.is_file(),
        "consumption_receipt_self_hash": isinstance(consumption_digest, str)
        and hash_json(consumption_payload) == consumption_digest,
        "consumption_binding_matches": consumption_digest
        == infra.get("authorization_consumption_receipt_sha256"),
        "consumption_authorization_matches": consumption.get(
            "authorization_receipt_sha256"
        )
        == infra.get("authorization", {}).get("receipt_sha256"),
        "authorization_hash_matches_guard": infra.get("authorization", {}).get(
            "receipt_sha256"
        )
        == guard.get("binding", {}).get("authorization_receipt_sha256"),
        "post_release_verified": infra.get("gpu_postcheck_release", {}).get(
            "verified"
        )
        is True,
    }
    if not all(required_infra_checks.values()):
        raise ValueError(
            f"F4 infrastructure receipt is invalid: {required_infra_checks}"
        )
    if infra.get("hash_infrastructure_pass") is not True:
        raise ValueError("F4 hash infrastructure fix must pass before Stage 0")
    selected = infra.get("selected_corridor_candidate_v11")
    blocker = None
    if not isinstance(selected, Mapping):
        blocker = {
            "failure_type": "f4_no_planner_solvable_corridor",
            "message": "F4 hash infrastructure passed but no physical corridor was selected",
            "f4_infrastructure_receipt_sha256": receipt_sha,
        }
        selected = None
    roots = {
        family: planned_stage0_root_spec(
            family,
            selected_f4_candidate=selected if family == "F4" else None,
            f4_shared_preflight_blocker=blocker if family == "F4" else None,
        )
        for family in ("F1", "F2", "F3", "F4")
    }
    attempts = [
        {
            "attempt_id": attempt_id,
            "family": family,
            "root_slot_id": spec["slot_id"],
            "program_id": program_id,
            "realization": "r_pc",
            "formal_data": False,
            "stage0_data": True,
        }
        for family, spec in roots.items()
        for attempt_id, program_id in zip(
            spec["stage0_attempt_ids"], spec["program_ids"]
        )
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage": 0,
        "purpose": "smoke engineering feasibility and evidence collection",
        "headline_scientific_claim_allowed": False,
        "planned_family_root_count": 4,
        "planned_attempt_count": 12,
        "attempts_per_family": 3,
        "realization": "r_pc",
        "root_specs": roots,
        "attempts": attempts,
        "f4_infrastructure_receipt_sha256": receipt_sha,
        "f4_infrastructure_receipt_file_sha256": receipt_file_sha256,
        "f4_infrastructure_guard_receipt_sha256": guard_digest,
        "f4_infrastructure_receipt_path": str(receipt_path),
        "f4_infrastructure_source_sha256": infra["authorization"][
            "implementation_source_sha256"
        ],
        "f4_infrastructure_validation_checks": required_infra_checks,
        "budget_receipt_sha256": budget_receipt_sha256(),
        "success_required_for_stage_completion": False,
        "allowed_family_outcomes": ["PASS", "FAILED_WITH_EVIDENCE"],
        "success_and_failure_both_retained": True,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    if len(attempts) != 12 or any(
        sum(item["family"] == family for item in attempts) != 3
        for family in roots
    ):
        raise ValueError("Stage 0 manifest must contain exactly 4x3 attempts")
    result["manifest_sha256"] = hash_json(result)
    return result


__all__ = [
    "SCENE_SEED",
    "build_stage0_smoke_manifest",
    "planned_stage0_root_spec",
    "validate_stage0_smoke_manifest_structure",
]
