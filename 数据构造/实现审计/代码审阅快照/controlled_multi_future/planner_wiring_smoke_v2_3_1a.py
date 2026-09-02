"""V2.3.1a proposals and approval schema bound to the corrected bundle."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .planner_qualification_integration_v2_3_1a import (
    build_manifest_bundle_v2_3_1a,
)


def _smoke_jobs_v2():
    bundle = build_manifest_bundle_v2_3_1a()
    f2 = bundle["manifests"]["F2"]["ordered_recipes"]
    f2_left = next(item for item in f2 if item["arm"] == "left")
    f2_right = next(item for item in f2 if item["arm"] == "right")
    f3 = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
    f3_first = f3[0]
    f3_second = next(
        item
        for item in f3
        if item["stratum"]["asset_model_id"]
        != f3_first["stratum"]["asset_model_id"]
        and item["stratum"]["arm"] != f3_first["stratum"]["arm"]
    )
    f4 = [
        item
        for item in bundle["manifests"]["F4"]["ordered_jobs"]
        if item["candidate_rank"] == 1
    ]
    f4_query_limit = bundle["manifests"]["F4"][
        "total_query_limit_per_job"
    ]
    jobs = [
        {"slot": "S1", "job_kind": "F2_STAGE_A", "entry_sha256": f2_left["entry_sha256"], "max_queries": 3, "condition": "always"},
        {"slot": "S2", "job_kind": "F3_STAGE_A", "entry_sha256": f3_first["entry_sha256"], "max_queries": 3, "condition": "S1 infrastructure-clean"},
        {"slot": "S3", "job_kind": "F4_PROGRAM", "entry_sha256": f4[0]["job_sha256"], "max_queries": f4_query_limit, "condition": "S1-S2 infrastructure-clean"},
        {"slot": "S4", "job_kind": "F2_STAGE_A", "entry_sha256": f2_right["entry_sha256"], "max_queries": 3, "condition": "S1-S3 infrastructure-clean"},
        {"slot": "S5", "job_kind": "F3_STAGE_A", "entry_sha256": f3_second["entry_sha256"], "max_queries": 3, "condition": "S1-S4 infrastructure-clean"},
        {"slot": "S6A", "job_kind": "F3_STAGE_B", "entry_sha256": f3_first["entry_sha256"], "max_queries": 7, "condition": "S2 planner pass"},
        {"slot": "S6B", "job_kind": "F3_STAGE_B", "entry_sha256": f3_second["entry_sha256"], "max_queries": 7, "condition": "S5 planner pass"},
        {"slot": "S7A", "job_kind": "F4_PROGRAM", "entry_sha256": f4[1]["job_sha256"], "max_queries": f4_query_limit, "condition": "S3 planner pass"},
        {"slot": "S7B", "job_kind": "F4_PROGRAM", "entry_sha256": f4[2]["job_sha256"], "max_queries": f4_query_limit, "condition": "S7A planner pass"},
    ]
    return bundle, jobs


def build_updated_planner_wiring_smoke_v1_proposal_v2() -> dict[str, Any]:
    bundle, jobs = _smoke_jobs_v2()
    f4_manifest = bundle["manifests"]["F4"]
    f4_program_limit = f4_manifest["total_query_limit_per_job"]
    f4_smoke_limit = 3 * f4_program_limit
    value = {
        "schema_version": "cmf_planner_wiring_smoke_v1_proposal_v2",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "f4_manifest_sha256": bundle["f4_panel_sha256"],
        "ordered_job_slots": jobs,
        "F2": {"scene_limit": 2, "planner_query_limit": 6},
        "F3": {"scene_limit": 4, "planner_query_limit": 20},
        "F4": {
            "scene_limit": 3,
            "target_construction_queries_per_program": f4_manifest[
                "target_construction_query_limit_per_job"
            ],
            "chain_queries_per_program": f4_manifest[
                "chain_query_limit_per_job"
            ],
            "total_queries_per_program": f4_program_limit,
            "planner_query_limit": f4_smoke_limit,
        },
        "aggregate": {
            "scene_limit": 9,
            "planner_query_limit": 6 + 20 + f4_smoke_limit,
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


def build_updated_full_planner_panel_v1_proposal_v2() -> dict[str, Any]:
    bundle = build_manifest_bundle_v2_3_1a()
    f4 = bundle["manifests"]["F4"]
    value = {
        "schema_version": "cmf_full_planner_panel_v1_proposal_v2",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "F2": {"maximum_queries": 192},
        "F3": {"maximum_queries": 496},
        "F4": {
            "manifest_sha256": f4["panel_sha256"],
            "candidate_count": f4["candidate_count"],
            "programs_per_candidate": f4["programs_per_candidate"],
            "target_construction_queries_per_program": f4[
                "target_construction_query_limit_per_job"
            ],
            "chain_queries_per_program": f4["chain_query_limit_per_job"],
            "total_queries_per_program": f4["total_query_limit_per_job"],
            "maximum_queries": f4["maximum_panel_queries"],
            "stop_after_lowest_rank_complete_pass": True,
        },
        "maximum_aggregate_queries": 192 + 496 + f4["maximum_panel_queries"],
        "separate_family_authorizations_required": True,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


def build_wave_approval_schema_v2(*, activation_contract_sha256: str):
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    value = {
        "schema_version": "cmf_planner_wiring_smoke_v1_wave_approval_schema_v2",
        "approval_artifact_schema": "cmf_planner_wiring_smoke_v1_wave_approval_v2",
        "activation_contract_sha256": str(activation_contract_sha256),
        "proposal_sha256": proposal["proposal_sha256"],
        "manifest_bundle_sha256": proposal["manifest_bundle_sha256"],
        "required_fields": [
            "wave_id", "approved", "approved_scope",
            "activation_contract_sha256", "proposal_sha256",
            "manifest_bundle_sha256", "ordered_job_slots",
            "aggregate_budget", "conditional_issuance_rules", "vault_head",
            "implementation_source_sha256", "robotwin_tracked_head",
        ],
        "single_wave_approval_multiple_single_use_job_authorizations": True,
        "job_level_reapproval_required": False,
        "approval_granted_by_schema": False,
    }
    value["schema_sha256"] = canonical_hash_json(value)
    return value


def validate_wave_approval_v2(
    approval: Mapping[str, Any], *, activation_contract: Mapping[str, Any]
) -> dict[str, Any]:
    value = canonical_jsonable(approval)
    payload = dict(value)
    digest = payload.pop("wave_approval_sha256", None)
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    contract = canonical_jsonable(activation_contract)
    if (
        value.get("schema_version")
        != "cmf_planner_wiring_smoke_v1_wave_approval_v2"
        or digest != canonical_hash_json(payload)
        or not isinstance(value.get("wave_id"), str)
        or not value["wave_id"]
        or value.get("approved") is not True
        or value.get("approved_scope") != "PLANNER_WIRING_SMOKE_V1"
        or value.get("activation_contract_sha256")
        != contract.get("contract_sha256")
        or value.get("proposal_sha256") != proposal["proposal_sha256"]
        or value.get("manifest_bundle_sha256")
        != proposal["manifest_bundle_sha256"]
        or value.get("ordered_job_slots") != proposal["ordered_job_slots"]
        or value.get("aggregate_budget") != proposal["aggregate"]
        or value.get("conditional_issuance_rules")
        != proposal["conditional_issuance_rules"]
        or value.get("vault_head") != contract.get("vault_head")
        or value.get("implementation_source_sha256")
        != contract.get("implementation_source_sha256")
        or value.get("robotwin_tracked_head")
        != contract.get("robotwin_tracked_head")
    ):
        raise PermissionError("V2.3.1a wave approval binding mismatch")
    return value


__all__ = [
    "build_updated_full_planner_panel_v1_proposal_v2",
    "build_updated_planner_wiring_smoke_v1_proposal_v2",
    "build_wave_approval_schema_v2",
    "validate_wave_approval_v2",
]
