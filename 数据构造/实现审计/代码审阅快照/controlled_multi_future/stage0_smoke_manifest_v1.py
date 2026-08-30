"""Deterministic manifest for exactly 12 Stage 0 r_pc smoke attempts."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .current_hasher import hash_json
from .families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from .stage0_smoke_budget_v1 import budget_receipt_sha256, scope_budget


SCHEMA_VERSION = "cmf_stage0_smoke_manifest_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1"
SCENE_SEED = 20260829
FAMILY_CLASSES = {
    "F1": F1ObjectSelection,
    "F2": F2TargetRelation,
    "F3": F3MotionOrder,
    "F4": F4SubtaskOrder,
}


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
    f4_infrastructure_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    infra = json.loads(
        json.dumps(f4_infrastructure_receipt, sort_keys=True, allow_nan=False)
    )
    if infra.get("hash_infrastructure_pass") is not True:
        raise ValueError("F4 hash infrastructure fix must pass before Stage 0")
    selected = infra.get("selected_corridor_candidate_v11")
    blocker = None
    if not isinstance(selected, Mapping):
        blocker = {
            "failure_type": "f4_no_planner_solvable_corridor",
            "message": "F4 hash infrastructure passed but no physical corridor was selected",
            "f4_infrastructure_receipt_sha256": infra.get("receipt_sha256"),
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
        "f4_infrastructure_receipt_sha256": infra.get("receipt_sha256"),
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
]
