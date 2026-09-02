"""Updated V2.3.1 smoke proposal and wave-level approval contract."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .planner_qualification_integration_v2_3 import build_manifest_bundle_v2_3


F4_TARGET_CONSTRUCTION_QUERIES = 12
F4_CHAIN_QUERIES = 30
F4_TOTAL_QUERIES_PER_PROGRAM = 42


def _smoke_jobs():
    bundle = build_manifest_bundle_v2_3()
    f2 = bundle["manifests"]["F2"]["ordered_recipes"]
    f2_left = next(item for item in f2 if item["arm"] == "left")
    f2_right = next(item for item in f2 if item["arm"] == "right")
    f3 = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
    f3_first = f3[0]
    f3_second = next(
        item for item in f3
        if item["stratum"]["asset_model_id"] != f3_first["stratum"]["asset_model_id"]
        and item["stratum"]["arm"] != f3_first["stratum"]["arm"]
    )
    f4 = [
        item for item in bundle["manifests"]["F4"]["ordered_jobs"]
        if item["candidate_rank"] == 1
    ]
    jobs = [
        {"slot": "S1", "job_kind": "F2_STAGE_A", "entry_sha256": f2_left["entry_sha256"], "max_queries": 3, "condition": "always"},
        {"slot": "S2", "job_kind": "F3_STAGE_A", "entry_sha256": f3_first["entry_sha256"], "max_queries": 3, "condition": "S1 infrastructure-clean"},
        {"slot": "S3", "job_kind": "F4_PROGRAM", "entry_sha256": f4[0]["job_sha256"], "max_queries": 42, "condition": "S1-S2 infrastructure-clean"},
        {"slot": "S4", "job_kind": "F2_STAGE_A", "entry_sha256": f2_right["entry_sha256"], "max_queries": 3, "condition": "S1-S3 infrastructure-clean"},
        {"slot": "S5", "job_kind": "F3_STAGE_A", "entry_sha256": f3_second["entry_sha256"], "max_queries": 3, "condition": "S1-S4 infrastructure-clean"},
        {"slot": "S6A", "job_kind": "F3_STAGE_B", "entry_sha256": f3_first["entry_sha256"], "max_queries": 7, "condition": "S2 planner pass"},
        {"slot": "S6B", "job_kind": "F3_STAGE_B", "entry_sha256": f3_second["entry_sha256"], "max_queries": 7, "condition": "S5 planner pass"},
        {"slot": "S7A", "job_kind": "F4_PROGRAM", "entry_sha256": f4[1]["job_sha256"], "max_queries": 42, "condition": "S3 planner pass"},
        {"slot": "S7B", "job_kind": "F4_PROGRAM", "entry_sha256": f4[2]["job_sha256"], "max_queries": 42, "condition": "S7A planner pass"},
    ]
    return bundle, jobs


def build_updated_planner_wiring_smoke_v1_proposal() -> dict[str, Any]:
    bundle, jobs = _smoke_jobs()
    value = {
        "schema_version": "cmf_planner_wiring_smoke_v1_proposal_v2_3_1",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "ordered_job_slots": jobs,
        "F2": {"scene_limit": 2, "planner_query_limit": 6},
        "F3": {"scene_limit": 4, "planner_query_limit": 20},
        "F4": {
            "scene_limit": 3,
            "target_construction_queries_per_program": 12,
            "chain_queries_per_program": 30,
            "total_queries_per_program": 42,
            "planner_query_limit": 126,
        },
        "aggregate": {
            "scene_limit": 9,
            "planner_query_limit": 152,
            "wall_time_seconds": 16200,
            "physical_execution_limit": 0,
            "trajectory_limit": 0,
            "single_fresh_idle_gpu": True,
            "serial_only": True,
        },
        "infrastructure_error_stops_wave": True,
        "planner_candidate_fail_is_valid_terminal_evidence": True,
        "conditional_issuance_rules": {
            "S1_to_S5": "serial; any INFRASTRUCTURE_ERROR stops later issuance",
            "S6A": "only if S2 planner_pass",
            "S6B": "only if S5 planner_pass",
            "S7A": "only if S3 planner_pass",
            "S7B": "only if S7A planner_pass",
        },
        "automatic_full_panel_continuation": False,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


def build_updated_full_planner_panel_v1_proposal() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_full_planner_panel_v1_proposal_v2_3_1",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "F2": {"maximum_queries": 192},
        "F3": {"maximum_queries": 496},
        "F4": {
            "target_construction_queries_per_program": 12,
            "chain_queries_per_program": 30,
            "total_queries_per_program": 42,
            "maximum_queries": 1008,
            "stop_after_lowest_rank_complete_pass": True,
        },
        "maximum_aggregate_queries": 1696,
        "separate_family_authorizations_required": True,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


def build_planner_wiring_smoke_v1_wave_approval_schema(
    *, activation_contract_sha256: str
) -> dict[str, Any]:
    proposal = build_updated_planner_wiring_smoke_v1_proposal()
    value = {
        "schema_version": "cmf_planner_wiring_smoke_v1_wave_approval_schema",
        "approval_artifact_schema": "cmf_planner_wiring_smoke_v1_wave_approval",
        "activation_contract_sha256": str(activation_contract_sha256),
        "proposal_sha256": proposal["proposal_sha256"],
        "manifest_bundle_sha256": proposal["manifest_bundle_sha256"],
        "required_fields": [
            "approved", "approved_scope", "activation_contract_sha256",
            "proposal_sha256", "manifest_bundle_sha256", "ordered_job_slots",
            "aggregate_budget", "conditional_issuance_rules", "vault_head",
            "implementation_source_sha256", "robotwin_tracked_head",
        ],
        "single_wave_approval_multiple_single_use_job_authorizations": True,
        "job_level_reapproval_required": False,
        "approval_granted_by_schema": False,
    }
    value["schema_sha256"] = canonical_hash_json(value)
    return value


def validate_wave_approval_v1(
    approval: Mapping[str, Any],
    *,
    activation_contract: Mapping[str, Any],
) -> dict[str, Any]:
    value = canonical_jsonable(approval)
    payload = dict(value)
    digest = payload.pop("wave_approval_sha256", None)
    proposal = build_updated_planner_wiring_smoke_v1_proposal()
    contract = canonical_jsonable(activation_contract)
    if (
        value.get("schema_version") != "cmf_planner_wiring_smoke_v1_wave_approval"
        or digest != canonical_hash_json(payload)
        or value.get("approved") is not True
        or value.get("approved_scope") != "PLANNER_WIRING_SMOKE_V1"
        or value.get("activation_contract_sha256") != contract.get("contract_sha256")
        or value.get("proposal_sha256") != proposal["proposal_sha256"]
        or value.get("manifest_bundle_sha256") != proposal["manifest_bundle_sha256"]
        or value.get("ordered_job_slots") != proposal["ordered_job_slots"]
        or value.get("aggregate_budget") != proposal["aggregate"]
        or value.get("conditional_issuance_rules")
        != proposal["conditional_issuance_rules"]
        or value.get("vault_head") != contract.get("vault_head")
        or value.get("implementation_source_sha256")
        != contract.get("implementation_source_sha256")
        or value.get("robotwin_tracked_head") != contract.get("robotwin_tracked_head")
    ):
        raise PermissionError("smoke wave approval does not bind V2.3.1 exactly")
    return value


__all__ = [
    "build_planner_wiring_smoke_v1_wave_approval_schema",
    "build_updated_full_planner_panel_v1_proposal",
    "build_updated_planner_wiring_smoke_v1_proposal",
    "validate_wave_approval_v1",
]
