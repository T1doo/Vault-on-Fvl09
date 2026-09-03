"""CPU-only contract for the F2--F4 production-path recovery."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_scene_binding_equivalence_v1 import (
    BOTTLE_ORIENTATION_ATOL_RAD,
    BOTTLE_POSITION_ATOL_M,
)
from .f4_collision_capability_audit_v1 import (
    build_f4_collision_capability_audit_v1,
)
from .runtime_source_lock_v1 import FAMILY_ASSET_FILES


IMPLEMENTATION_VERSION = "controlled_multi_future_production_recovery_v1"


def build_production_recovery_contract_v1() -> dict[str, Any]:
    f4 = build_f4_collision_capability_audit_v1()
    value = {
        "schema_version": "cmf_production_recovery_contract_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "objective": "repair production paths before further broad planner search",
        "stage0_reopened": False,
        "phase_a_budget": {
            "gpu": 0,
            "real_planner_queries": 0,
            "sapien_scenes": 0,
            "physical_executions": 0,
            "trajectories": 0,
        },
        "f2": {
            "production_runner": (
                "controlled_multi_future.f2_controlled_insertion_physical_v2."
                "run_f2_controlled_insertion_physical_v2"
            ),
            "legacy_dispatcher_disabled": True,
            "planner_dependency_required": True,
            "planner_query_limit_per_physical_attempt": 8,
            "development_asset_pairs": [
                {"can_model_id": 0, "box_model_id": 2},
                {"can_model_id": 5, "box_model_id": 8},
            ],
            "maximum_physical_attempts": 4,
        },
        "f3": {
            "scene_binding_gate": (
                "controlled_multi_future.f3_scene_binding_equivalence_v1."
                "audit_f3_scene_binding_equivalence_v1"
            ),
            "bottle_position_atol_m": BOTTLE_POSITION_ATOL_M,
            "bottle_orientation_atol_rad": BOTTLE_ORIENTATION_ATOL_RAD,
            "asset_model_ids": [15, 5, 4, 13],
            "maximum_physical_candidates": 4,
            "maximum_three_scene_no_suffix_diagnostics": 1,
            "planner_stage_b_proves_physical_grasp": False,
        },
        "f4": {
            "collision_capability_audit_receipt_sha256": f4["receipt_sha256"],
            "dynamic_or_attached_collision_available": False,
            "selected_route": f4["selected_recovery_route"],
            "maximum_development_roots": 1,
            "full_1696_query_panel_next": False,
        },
        "runtime_source_lock_assets": {
            family: list(FAMILY_ASSET_FILES[family]) for family in ("F2", "F3", "F4")
        },
        "next_authorized_scope_after_phase_a": "none_until_new_gpu_micro_qualification_approval",
        "stage1_authorized": False,
        "formal_360_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


def validate_unconsumed_wave_for_supersession_v1(
    meta: Mapping[str, Any], *, expected_wave_id: str
) -> dict[str, Any]:
    value = canonical_jsonable(meta)
    payload = dict(value)
    digest = payload.pop("ledger_sha256", None)
    if digest != canonical_hash_json(payload):
        raise ValueError("superseded wave ledger meta hash mismatch")
    checks = {
        "wave_id": value.get("wave_id") == expected_wave_id,
        "operational_execution_not_started": value.get(
            "operational_execution_started"
        )
        is False,
        "ledger_not_previously_closed": value.get("closed") is False,
        "physical_budget_zero": value.get("aggregate_budget", {}).get(
            "physical_execution_limit"
        )
        == 0,
        "trajectory_budget_zero": value.get("aggregate_budget", {}).get(
            "trajectory_limit"
        )
        == 0,
    }
    if not all(checks.values()):
        raise ValueError("wave is not eligible for zero-consumption supersession")
    return value


def build_unconsumed_wave_supersession_receipt_v1(
    meta: Mapping[str, Any],
    *,
    f2_source_lock: Mapping[str, Any],
    f3_source_lock: Mapping[str, Any],
    ledger_entry_counts: Mapping[str, int],
    superseding_plan_path: str,
) -> dict[str, Any]:
    wave = validate_unconsumed_wave_for_supersession_v1(
        meta,
        expected_wave_id="planner-wiring-smoke-v1-replacement-20260903-run2",
    )
    counts = {
        key: int(ledger_entry_counts.get(key, -1))
        for key in ("issued", "terminals", "skipped", "closures")
    }
    if any(value != 0 for value in counts.values()):
        raise ValueError("only a zero-entry wave may use this supersession receipt")
    f2_locked = set(
        canonical_jsonable(f2_source_lock)
        .get("snapshot", {})
        .get("asset_hashes", {})
    )
    f3_locked = set(
        canonical_jsonable(f3_source_lock)
        .get("snapshot", {})
        .get("asset_hashes", {})
    )
    f2_required = set(FAMILY_ASSET_FILES["F2"])
    f3_required = set(FAMILY_ASSET_FILES["F3"])
    missing = {
        "F2": sorted(f2_required - f2_locked),
        "F3": sorted(f3_required - f3_locked),
    }
    stale = {
        "F2": sorted(f2_locked - f2_required),
        "F3": sorted(f3_locked - f3_required),
    }
    if not missing["F2"] or not missing["F3"]:
        raise ValueError("supersession requires the observed F2 and F3 asset-lock gaps")
    value = {
        "schema_version": "cmf_unconsumed_wave_supersession_receipt_v1",
        "status": "SUPERSEDED_UNCONSUMED_BY_PRODUCTION_RECOVERY_V1",
        "superseded_wave_id": wave["wave_id"],
        "wave_approval_sha256": wave["wave_approval_sha256"],
        "ledger_sha256": wave["ledger_sha256"],
        "observed_ledger_entry_counts": counts,
        "operational_execution_started": False,
        "authorization_issued_count": 0,
        "guard_consumption_count": 0,
        "planner_query_count": 0,
        "scene_count": 0,
        "physical_execution_count": 0,
        "trajectory_count": 0,
        "supersession_reasons": [
            "planner-only smoke cannot qualify F2 insertion, F3 physical grasp, or F4 noninterference",
            "F2 source lock retained historical assets instead of the current/recovery asset pairs",
            "F3 source lock covered only bottle/base13 instead of the four-asset panel",
        ],
        "source_lock_missing_current_assets": missing,
        "source_lock_stale_assets": stale,
        "old_approval_ledger_and_source_locks_preserved": True,
        "old_wave_must_not_issue_new_slots": True,
        "superseding_plan_path": str(superseding_plan_path),
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_360_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "IMPLEMENTATION_VERSION",
    "build_production_recovery_contract_v1",
    "build_unconsumed_wave_supersession_receipt_v1",
    "validate_unconsumed_wave_for_supersession_v1",
]
