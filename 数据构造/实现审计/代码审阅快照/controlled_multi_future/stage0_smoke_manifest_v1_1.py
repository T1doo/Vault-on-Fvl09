"""Canonical 4x3 Stage-0 v1.1 manifest after the F4 v13 Gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .f4_frozen_canonical_neutral_binding_v13 import (
    canonical_neutral_pose_sha256_v13,
    validate_f4_frozen_canonical_neutral_binding_v13,
)
from .f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from .stage0_smoke_budget_v1_1 import (
    budget_artifact,
    budget_receipt_sha256,
    scope_budget,
)


SCHEMA_VERSION = "cmf_stage0_smoke_attempt_manifest_v1_1"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1_1"
SCENE_SEED = 20260829
CANONICAL_INFRA_NAMESPACE = (
    "prestage0_f4_candidate_hash_infra_v13_stage0_v1_1_seed20260829_run1"
)
CANONICAL_INFRA_RECEIPT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs"
) / CANONICAL_INFRA_NAMESPACE / "receipt.json"
CANONICAL_OUTPUT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.json"
)
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def _self_hash(value: Mapping[str, Any], field: str) -> bool:
    payload = dict(value)
    digest = payload.pop(field, None)
    return isinstance(digest, str) and hash_json(payload) == digest


def _attempt_ids(family: str) -> list[str]:
    return [f"stage0-v1_1-{family}-rootA-{index + 1:02d}" for index in range(3)]


def planned_stage0_root_spec_v1_1(
    family: str,
    *,
    selected_f4_candidate_v13: Mapping[str, Any] | None = None,
    f4_canonical_neutral_binding_v13: Mapping[str, Any] | None = None,
    f4_shared_preflight_blocker: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if family not in FAMILY_CLASSES:
        raise ValueError("unsupported Stage 0 v1.1 family")
    if family != "F4" and any(
        item is not None
        for item in (
            selected_f4_candidate_v13,
            f4_canonical_neutral_binding_v13,
            f4_shared_preflight_blocker,
        )
    ):
        raise ValueError("F4-only v13 fields leaked to another family")
    binding = None
    selected = None
    blocker = None
    if family == "F4":
        binding = validate_f4_frozen_canonical_neutral_binding_v13(
            f4_canonical_neutral_binding_v13
        )
        if (selected_f4_candidate_v13 is None) == (f4_shared_preflight_blocker is None):
            raise ValueError("F4 v1.1 requires exactly one selected candidate or blocker")
        selected = None if selected_f4_candidate_v13 is None else _copy(selected_f4_candidate_v13)
        blocker = None if f4_shared_preflight_blocker is None else _copy(f4_shared_preflight_blocker)
        if selected is not None:
            contract = selected.get("candidate_contract_segments")
            applied = selected.get("applied_planner_targets")
            if (
                not isinstance(contract, list)
                or not contract
                or contract[-1].get("segment_id") != "A_neutral"
                or not isinstance(applied, list)
                or not applied
                or applied[-1].get("segment_id") != "A_neutral"
                or contract[-1].get("pose") != applied[-1].get("pose")
            ):
                raise ValueError("selected F4 candidate terminal neutral structure changed")
            if canonical_neutral_pose_sha256_v13(
                contract[-1]["pose"]
            ) != binding[
                "canonical_terminal_neutral_pose_sha256"
            ]:
                raise ValueError("selected F4 candidate neutral target hash changed")
    scope = f"Stage0_v1_1_{family}_root_A"
    programs = FAMILY_CLASSES[family]().checked_provisional_programs()
    result: dict[str, Any] = {
        "schema_version": "cmf_stage0_planned_root_slot_spec_v1_1",
        "slot_id": f"stage0-v1_1-{family}-pilot-root-A",
        "family": family,
        "scope": scope,
        "seed": SCENE_SEED,
        "arm": "right" if family == "F4" else "left",
        "generator": "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7",
        "origin": "authorized_stage0_smoke_v1_1",
        "program_ids": [item["program_id"] for item in programs],
        "realizations": ["r_pc", "r_pc", "r_pc"],
        "stage0_attempt_ids": _attempt_ids(family),
        "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "success_and_failure_both_retained": True,
        "accepted_root_required": False,
        "stage0_generated_trajectory_mp4_required": True,
        "stage0_video_contract": _copy(
            budget_artifact()["stage0_video_contract"]
        ),
        "stop_condition": "terminal family receipt or cleanup/source/GPU uncertainty",
    }
    if family == "F4":
        result.update(
            {
                "scene_layout": _copy(F4_LAYOUT),
                "scene_layout_sha256": hash_json(F4_LAYOUT),
                "f4_canonical_neutral_binding_v13": binding,
                "f4_canonical_neutral_binding_sha256_v13": binding["binding_sha256"],
                "canonical_terminal_neutral_pose_sha256_v13": binding[
                    "canonical_terminal_neutral_pose_sha256"
                ],
                "selected_f4_corridor_candidate_v13": selected,
                # Compatibility alias contains the same truthful candidate payload;
                # the binding stays separate and never rewrites base-v11 provenance.
                "selected_f4_corridor_candidate_v11": selected,
                "f4_shared_preflight_blocker": blocker,
            }
        )
    result["planned_root_slot_spec_sha256"] = hash_json(result)
    return result


def build_stage0_smoke_manifest_v1_1(
    f4_infrastructure_receipt_path: Path = CANONICAL_INFRA_RECEIPT,
    *,
    require_canonical_path: bool = True,
) -> dict[str, Any]:
    path = Path(f4_infrastructure_receipt_path).resolve()
    if require_canonical_path and path != CANONICAL_INFRA_RECEIPT.resolve():
        raise ValueError("F4 v13 infrastructure receipt path is not canonical")
    if not path.is_file():
        raise ValueError("F4 v13 infrastructure receipt is missing")
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    infra = json.loads(path.read_text(encoding="utf-8"))
    if not _self_hash(infra, "guard_sealed_receipt_sha256"):
        raise ValueError("F4 v13 outer receipt Guard seal is invalid")
    guard_path = Path(str(infra.get("guard_receipt", ""))).resolve()
    guard = json.loads(guard_path.read_text(encoding="utf-8")) if guard_path.is_file() else {}
    guard_payload = dict(guard)
    guard_digest = guard_payload.pop("guard_receipt_sha256", None)
    consumption_path = Path(str(guard.get("consumption_receipt", ""))).resolve()
    consumption = (
        json.loads(consumption_path.read_text(encoding="utf-8"))
        if consumption_path.is_file()
        else {}
    )
    consumption_payload = dict(consumption)
    consumption_digest = consumption_payload.pop("consumption_receipt_sha256", None)
    audit = infra.get("hash_infrastructure_audit_v13")
    binding = infra.get("canonical_neutral_binding_v13")
    selected = infra.get("selected_corridor_candidate_v13")
    checks = {
        "schema": infra.get("schema_version") == "cmf_stage0_smoke_guarded_scope_receipt_v1_1",
        "implementation": infra.get("implementation_version") == IMPLEMENTATION_VERSION,
        "scope": infra.get("scope") == "F4_candidate_hash_infra_v13",
        "family": infra.get("family") == "F4",
        "terminal": infra.get("status") == "completed_f4_hash_infrastructure_v13",
        "pipeline": infra.get("pipeline_integrity_pass") is True,
        "hash_pass": infra.get("hash_infrastructure_pass") is True,
        "audit_pass": isinstance(audit, Mapping) and audit.get("pass") is True,
        "audit_candidate_query_check": isinstance(audit, Mapping)
        and audit.get("checks", {}).get(
            "at_least_one_candidate_reached_real_planner"
        )
        is True,
        "candidate_query_positive": int(
            infra.get("candidate_corridor_planner_query_count", 0)
        )
        > 0,
        "execution_zero": int(infra.get("budget_counts", {}).get("execution_attempt_count", -1)) == 0,
        "recovery_zero": int(infra.get("budget_counts", {}).get("recovery_attempt_count", -1)) == 0,
        "cleanup": infra.get("scene_cleanup_succeeded") is True
        and int(infra.get("orphan_process_count", -1)) == 0,
        "source_bound": isinstance(
            infra.get("authorization", {}).get("implementation_source_sha256"), str
        ),
        "guard_exists": guard_path.is_file(),
        "guard_self_hash": isinstance(guard_digest, str)
        and hash_json(guard_payload) == guard_digest,
        "guard_completed": guard.get("status") == "completed",
        "guard_source_lock": guard.get("post_source_lock_pass") is True,
        "guard_no_timeout_or_orphan": guard.get("timed_out") is False
        and int(guard.get("orphan_process_count", -1)) == 0,
        "guard_post_release": guard.get("postcheck_release", {}).get("verified")
        is True
        and infra.get("gpu_postcheck_release", {}).get("verified") is True,
        "guard_child_hash": guard.get("child_receipt_file", {}).get("sha256")
        == file_sha,
        "guard_binding": guard.get("binding")
        == infra.get("guard_binding")
        == infra.get("gpu_guard_binding"),
        "consumption_exists": consumption_path.is_file(),
        "consumption_self_hash": isinstance(consumption_digest, str)
        and hash_json(consumption_payload) == consumption_digest,
        "consumption_binding": consumption_digest
        == infra.get("authorization_consumption_receipt_sha256")
        and consumption.get("authorization_receipt_sha256")
        == infra.get("authorization", {}).get("receipt_sha256"),
        "authorization_guard_binding": infra.get("authorization", {}).get(
            "receipt_sha256"
        )
        == guard.get("binding", {}).get("authorization_receipt_sha256"),
        "not_data": infra.get("stage0_data") is False and infra.get("formal_data") is False,
    }
    if not all(checks.values()):
        raise ValueError(f"F4 v13 infrastructure receipt failed: {checks}")
    validated_binding = validate_f4_frozen_canonical_neutral_binding_v13(binding)
    blocker = None
    if not isinstance(selected, Mapping):
        selected = None
        blocker = {
            "failure_type": "f4_no_planner_solvable_corridor_v13",
            "message": "v13 infrastructure passed but no physical corridor was selected",
            "f4_infrastructure_guard_seal_sha256": infra["guard_sealed_receipt_sha256"],
            "f4_canonical_neutral_binding_sha256_v13": validated_binding["binding_sha256"],
        }
    roots = {
        family: planned_stage0_root_spec_v1_1(
            family,
            selected_f4_candidate_v13=selected if family == "F4" else None,
            f4_canonical_neutral_binding_v13=validated_binding if family == "F4" else None,
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
            "mp4_required_if_trajectory_generated": True,
        }
        for family, spec in roots.items()
        for attempt_id, program_id in zip(spec["stage0_attempt_ids"], spec["program_ids"])
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage": 0,
        "canonical_publication_filename": CANONICAL_OUTPUT.name,
        "planned_family_root_count": 4,
        "planned_attempt_count": 12,
        "attempts_per_family": 3,
        "realization": "r_pc",
        "root_specs": roots,
        "attempts": attempts,
        "f4_infrastructure_receipt_path": str(path),
        "f4_infrastructure_receipt_file_sha256": file_sha,
        "f4_infrastructure_guard_seal_sha256": infra["guard_sealed_receipt_sha256"],
        "f4_infrastructure_guard_receipt_sha256": guard_digest,
        "f4_infrastructure_consumption_receipt_sha256": consumption_digest,
        "f4_infrastructure_source_sha256": infra["authorization"][
            "implementation_source_sha256"
        ],
        "f4_infrastructure_validation_checks": checks,
        "f4_canonical_neutral_binding_v13": validated_binding,
        "f4_canonical_neutral_binding_sha256_v13": validated_binding["binding_sha256"],
        "f4_candidate_corridor_planner_query_count": int(
            infra["candidate_corridor_planner_query_count"]
        ),
        "budget_receipt_sha256": budget_receipt_sha256(),
        "success_required_for_stage_completion": False,
        "allowed_family_outcomes": ["PASS", "FAILED_WITH_EVIDENCE"],
        "success_and_failure_both_retained": True,
        "stage0_generated_trajectory_mp4_required": True,
        "stage0_video_contract": _copy(
            budget_artifact()["stage0_video_contract"]
        ),
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    structure = validate_stage0_smoke_manifest_structure(result, require_self_hash=False)
    if not structure["pass"]:
        raise ValueError(f"Stage 0 v1.1 manifest construction failed: {structure['checks']}")
    result["manifest_sha256"] = hash_json(result)
    return result


def validate_stage0_smoke_manifest_structure(
    stage0_manifest: Mapping[str, Any], *, require_self_hash: bool = True
) -> dict[str, Any]:
    manifest = _copy(stage0_manifest)
    digest = manifest.pop("manifest_sha256", None)
    roots = manifest.get("root_specs", {})
    attempts = manifest.get("attempts", [])
    binding = manifest.get("f4_canonical_neutral_binding_v13")
    try:
        validated_binding = validate_f4_frozen_canonical_neutral_binding_v13(binding)
        binding_valid = True
    except (TypeError, ValueError):
        validated_binding = {}
        binding_valid = False
    root_identity_checks = {
        family: bool(
            isinstance(root, Mapping)
            and root.get("family") == family
            and root.get("scope") == f"Stage0_v1_1_{family}_root_A"
            and root.get("generator")
            == "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7"
            and isinstance(root.get("program_ids"), list)
            and len(root["program_ids"]) == 3
            and len(set(root["program_ids"])) == 3
            and root.get("realizations") == ["r_pc", "r_pc", "r_pc"]
            and isinstance(root.get("stage0_attempt_ids"), list)
            and len(root["stage0_attempt_ids"]) == 3
        )
        for family, root in roots.items()
    }
    expected_attempts = [
        {
            "attempt_id": attempt_id,
            "family": family,
            "root_slot_id": root["slot_id"],
            "program_id": program_id,
            "realization": "r_pc",
            "formal_data": False,
            "stage0_data": True,
            "mp4_required_if_trajectory_generated": True,
        }
        for family, root in roots.items()
        for attempt_id, program_id in zip(
            root.get("stage0_attempt_ids", []), root.get("program_ids", [])
        )
    ] if set(roots) == set(FAMILY_CLASSES) else []
    checks = {
        "manifest_self_hash": (not require_self_hash)
        or isinstance(digest, str)
        and hash_json(manifest) == digest,
        "implementation": manifest.get("implementation_version") == IMPLEMENTATION_VERSION,
        "stage0_not_formal": manifest.get("stage0_data") is True
        and manifest.get("stage0_authorized") is True
        and manifest.get("formal_data") is False,
        "exact_four_roots": set(roots) == set(FAMILY_CLASSES),
        "root_self_hashes": len(roots) == 4
        and all(_self_hash(root, "planned_root_slot_spec_sha256") for root in roots.values()),
        "root_identities": len(root_identity_checks) == 4
        and all(root_identity_checks.values()),
        "exact_twelve_attempts": len(attempts) == 12
        and len({item.get("attempt_id") for item in attempts}) == 12,
        "three_per_family": all(
            sum(item.get("family") == family for item in attempts) == 3
            for family in FAMILY_CLASSES
        ),
        "all_r_pc": all(item.get("realization") == "r_pc" for item in attempts),
        "attempts_match_root_exact_zipped_triples": attempts == expected_attempts,
        "attempt_data_roles": all(
            item.get("formal_data") is False
            and item.get("stage0_data") is True
            and item.get("mp4_required_if_trajectory_generated") is True
            for item in attempts
        ),
        "video_contract": manifest.get(
            "stage0_generated_trajectory_mp4_required"
        )
        is True
        and manifest.get("stage0_video_contract")
        == budget_artifact()["stage0_video_contract"]
        and all(
            root.get("stage0_generated_trajectory_mp4_required") is True
            and root.get("stage0_video_contract")
            == budget_artifact()["stage0_video_contract"]
            for root in roots.values()
        ),
        "binding_valid": binding_valid,
        "f4_root_binding_exact": binding_valid
        and roots.get("F4", {}).get("f4_canonical_neutral_binding_sha256_v13")
        == validated_binding.get("binding_sha256"),
        "no_stage1": manifest.get("stage1_authorized") is False
        and manifest.get("formal_collection_authorized") is False
        and manifest.get("training_authorized") is False,
    }
    return {
        "checks": checks,
        "root_identity_checks": root_identity_checks,
        "pass": all(checks.values()),
    }


__all__ = [
    "CANONICAL_INFRA_NAMESPACE",
    "CANONICAL_INFRA_RECEIPT",
    "CANONICAL_OUTPUT",
    "IMPLEMENTATION_VERSION",
    "SCENE_SEED",
    "build_stage0_smoke_manifest_v1_1",
    "planned_stage0_root_spec_v1_1",
    "validate_stage0_smoke_manifest_structure",
]
