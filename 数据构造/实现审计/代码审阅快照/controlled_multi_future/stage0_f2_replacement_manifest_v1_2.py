"""Replacement-only Stage-0 v1.2 manifest for the three invalid F2 slots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .f2_frozen_scene_layout_binding_v1 import (
    build_f2_frozen_scene_layout_binding_v1,
    validate_f2_frozen_scene_layout_binding_v1,
)
from .families import F2TargetRelation
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact


SCHEMA_VERSION = "cmf_stage0_f2_replacement_manifest_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1_2"
SCOPE = "Stage0_v1_2_F2_root_A_scene_layout_replacement"
SCENE_SEED = 20260829
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
AUDIT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09/数据构造/实现审计"
ORIGINAL_MANIFEST = AUDIT_ROOT / "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.json"
ORIGINAL_RESULT = AUDIT_ROOT / "STAGE0_SMOKE_RESULT_V1_1_20260830.json"
ORIGINAL_INTENDED_ANCHOR = (
    AUDIT_ROOT
    / "probe_outputs/nonformal_runtime_v3_4_1_f2_inside_targeted_v11_seed20260829_run1_gpu0"
    / "F2_inside_targeted/reference_anchor.json"
)
ORIGINAL_INTENDED_CURRENT = ORIGINAL_INTENDED_ANCHOR.with_name(
    "reference_current.json"
)
ORIGINAL_INVALID_F2_ROOT = (
    AUDIT_ROOT
    / "stage0_outputs/controlled_multi_future_stage0_smoke_v1_1"
    / "stage0_smoke_v1_1_F2_root_A_seed20260829_run1/stage0_family/root"
)
CANONICAL_OUTPUT = AUDIT_ROOT / "STAGE0_F2_REPLACEMENT_MANIFEST_V1_2.json"
DATASET_ROOT = (
    WORKSPACE_ROOT
    / "Robotwin2/datasets/controlled_multi_future_stage0_smoke_v1_2"
)
OUTPUT_NAMESPACE = (
    DATASET_ROOT / "stage0_smoke_v1_2_F2_root_A_scene_layout_replacement_run2"
)
REPLACEMENT_ATTEMPT_IDS = tuple(
    f"stage0-v1_2-F2-rootA-{index:02d}" for index in range(1, 4)
)
ORIGINAL_ATTEMPT_IDS = tuple(
    f"stage0-v1_1-F2-rootA-{index:02d}" for index in range(1, 4)
)
PROGRAM_IDS = tuple(
    item["program_id"] for item in F2TargetRelation().checked_provisional_programs()
)


def _copy(value: Any) -> Any:
    return json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )


def _file(path: Path) -> dict[str, Any]:
    if not Path(path).is_file():
        raise ValueError(f"required immutable evidence is missing: {path}")
    data = Path(path).read_bytes()
    return {
        "path": str(Path(path).resolve()),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def f2_replacement_budget_v1_2() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_stage0_f2_replacement_budget_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F2",
        "attempts": 3,
        "attempts_per_program": 1,
        "planner_query_limit": 64,
        "execution_limit": 3,
        "recovery_attempts": 0,
        "automatic_retry": False,
        "timeout_seconds": 7200,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = hash_json(value)
    return value


def planned_f2_replacement_root_spec_v1_2() -> dict[str, Any]:
    binding = build_f2_frozen_scene_layout_binding_v1()
    budget = f2_replacement_budget_v1_2()
    value = {
        "schema_version": "cmf_stage0_planned_root_slot_spec_v1_2",
        "slot_id": "stage0-v1_2-F2-pilot-root-A-scene-layout-replacement",
        "family": "F2",
        "scope": SCOPE,
        "seed": SCENE_SEED,
        "arm": "left",
        "generator": "controlled_multi_future_stage0_smoke_v1_2_adapter_v1_8",
        "origin": "stage0_v1_1_f2_infrastructure_slot_replacement",
        "program_ids": list(PROGRAM_IDS),
        "realizations": ["r_pc", "r_pc", "r_pc"],
        "stage0_attempt_ids": list(REPLACEMENT_ATTEMPT_IDS),
        "replacement_for_attempt_ids": list(ORIGINAL_ATTEMPT_IDS),
        "replacement_reason": "frozen_scene_layout_wiring_fix",
        "superseded_terminal_status": "FAILED_INFRASTRUCTURE_WITH_EVIDENCE",
        "scene_layout_version": binding["scene_layout_version"],
        "scene_layout": _copy(binding["scene_layout"]),
        "layout_payload_sha256": binding["layout_payload_sha256"],
        "f2_frozen_scene_layout_binding_v1": binding,
        "f2_frozen_scene_layout_binding_sha256": binding["binding_sha256"],
        "object_modelnames": _copy(binding["object_modelnames"]),
        "object_model_ids": _copy(binding["object_model_ids"]),
        "execution_arm": "left",
        "plasticbox_model_id": 2,
        "main_object": "071_can/base1",
        "budget_sha256": budget["budget_receipt_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "accepted_root_required": False,
        "success_and_failure_both_retained": True,
        "stage0_generated_trajectory_mp4_required": True,
        "stop_condition": "terminal family receipt or cleanup/source/GPU uncertainty",
    }
    value["planned_root_slot_spec_sha256"] = hash_json(value)
    return value


def build_stage0_f2_replacement_manifest_v1_2() -> dict[str, Any]:
    original_manifest = json.loads(ORIGINAL_MANIFEST.read_text(encoding="utf-8"))
    original_result = json.loads(ORIGINAL_RESULT.read_text(encoding="utf-8"))
    if original_result.get("authoritative") is not True:
        raise ValueError("original Stage 0 v1.1 result is not authoritative")
    original_attempts = {
        item.get("attempt_id"): item
        for item in original_result.get("attempt_receipts", [])
    }
    if set(ORIGINAL_ATTEMPT_IDS) - set(original_attempts):
        raise ValueError("original F2 attempt evidence is incomplete")
    if any(
        original_attempts[item].get("terminal_status")
        != "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
        for item in ORIGINAL_ATTEMPT_IDS
    ):
        raise ValueError("only infrastructure-failed F2 slots may be replaced")
    planned = planned_f2_replacement_root_spec_v1_2()
    programs = dict(zip(PROGRAM_IDS, zip(ORIGINAL_ATTEMPT_IDS, REPLACEMENT_ATTEMPT_IDS)))
    replacements = [
        {
            "family": "F2",
            "program_id": program,
            "realization": "r_pc",
            "active_attempt_id": replacement,
            "replacement_for_attempt_id": original,
            "superseded_terminal_status": original_attempts[original][
                "terminal_status"
            ],
            "replacement_reason": "frozen_scene_layout_wiring_fix",
            "formal_data": False,
            "stage0_data": True,
        }
        for program, (original, replacement) in programs.items()
    ]
    policy = current_gpu_policy_artifact()
    value = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "parent_vault_head": "8c0191056ea078f530bb098fade9610d41596136",
        "stage0_attempt_phase_v1_1_completed": True,
        "stage0_v1_1_completed": False,
        "replacement_scope": SCOPE,
        "replacement_root_spec": planned,
        "replacement_root_spec_sha256": planned[
            "planned_root_slot_spec_sha256"
        ],
        "replacement_attempts": replacements,
        "active_stage0_slot_count_after_replacement": 12,
        "historical_terminal_attempt_count_retained": 15,
        "original_f2_attempts_deleted": False,
        "original_f2_attempts_overwritten": False,
        "original_manifest": _file(ORIGINAL_MANIFEST),
        "original_result": _file(ORIGINAL_RESULT),
        "original_invalid_f2_reference_anchor": _file(
            ORIGINAL_INVALID_F2_ROOT / "reference_anchor.json"
        ),
        "original_invalid_f2_reference_current": _file(
            ORIGINAL_INVALID_F2_ROOT / "reference_current_hashes.json"
        ),
        "original_intended_layout_reference_anchor": _file(
            ORIGINAL_INTENDED_ANCHOR
        ),
        "original_intended_layout_reference_current": _file(
            ORIGINAL_INTENDED_CURRENT
        ),
        "original_attempt_current_comparability": (
            "not_comparable_due_to_missing_layout_binding_and_default_layout_drift"
        ),
        "intended_layout_lineage_source": (
            "runtime_v3_4_1 frozen F2 layout v2, same seed/object/arm"
        ),
        "gpu_policy_sha256": policy["policy_sha256"],
        "allowed_physical_gpu_indices": list(range(8)),
        "family_level_parallelism_authorized": True,
        "root_sharding": False,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "user_direction_source": (
            "https://chatgpt.com/s/t_6a95071af4c081919040e97237d3dca2"
        ),
        "stage0_video_contract": _copy(
            original_manifest["stage0_video_contract"]
        ),
    }
    value["manifest_sha256"] = hash_json(value)
    return value


def validate_stage0_f2_replacement_manifest_v1_2(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    result = _copy(value)
    digest = result.pop("manifest_sha256", None)
    expected = build_stage0_f2_replacement_manifest_v1_2()
    expected_digest = expected.pop("manifest_sha256")
    if result != expected or digest != expected_digest or hash_json(result) != digest:
        raise ValueError("Stage 0 F2 replacement manifest changed")
    validate_f2_frozen_scene_layout_binding_v1(
        result["replacement_root_spec"]["f2_frozen_scene_layout_binding_v1"]
    )
    return {**result, "manifest_sha256": digest}


__all__ = [
    "CANONICAL_OUTPUT",
    "DATASET_ROOT",
    "IMPLEMENTATION_VERSION",
    "ORIGINAL_ATTEMPT_IDS",
    "OUTPUT_NAMESPACE",
    "PROGRAM_IDS",
    "REPLACEMENT_ATTEMPT_IDS",
    "SCOPE",
    "build_stage0_f2_replacement_manifest_v1_2",
    "f2_replacement_budget_v1_2",
    "planned_f2_replacement_root_spec_v1_2",
    "validate_stage0_f2_replacement_manifest_v1_2",
]
