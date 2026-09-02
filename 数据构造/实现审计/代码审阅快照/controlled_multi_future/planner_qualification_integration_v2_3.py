"""CPU/source seal, job order contracts, and proposals for V2.3."""

from __future__ import annotations

import inspect
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_planner_integration_v2 import run_f2_final_grasp_stage_a_planner_v2
from .f3_planner_integration_v3_1 import (
    run_f3_stage_a_planner_v3_1,
    run_f3_stage_b_planner_v3_1,
)
from .f4_program_planner_integration_v2 import run_f4_program_planner_v2
from .planner_qualification_manifests_v2_3 import (
    build_f2_planner_panel_manifest_v1,
    build_f3_stage_a_panel_manifest_v1,
    build_f3_stage_b_selection_policy_v1,
    build_f4_program_panel_manifest_v1,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_planner_qualification_integration_v2_3"
RUNNER_SYMBOLS = {
    "F2_STAGE_A": (
        "controlled_multi_future.f2_planner_integration_v2."
        "run_f2_final_grasp_stage_a_planner_v2"
    ),
    "F3_STAGE_A": (
        "controlled_multi_future.f3_planner_integration_v3_1."
        "run_f3_stage_a_planner_v3_1"
    ),
    "F3_STAGE_B": (
        "controlled_multi_future.f3_planner_integration_v3_1."
        "run_f3_stage_b_planner_v3_1"
    ),
    "F4_PROGRAM": (
        "controlled_multi_future.f4_program_planner_integration_v2."
        "run_f4_program_planner_v2"
    ),
}
RUNNER_FUNCTIONS = {
    "F2_STAGE_A": run_f2_final_grasp_stage_a_planner_v2,
    "F3_STAGE_A": run_f3_stage_a_planner_v3_1,
    "F3_STAGE_B": run_f3_stage_b_planner_v3_1,
    "F4_PROGRAM": run_f4_program_planner_v2,
}


def build_manifest_bundle_v2_3() -> dict[str, Any]:
    f2 = build_f2_planner_panel_manifest_v1()
    f3a = build_f3_stage_a_panel_manifest_v1()
    f3b = build_f3_stage_b_selection_policy_v1(f3a)
    f4 = build_f4_program_panel_manifest_v1()
    value = {
        "schema_version": "cmf_planner_qualification_manifest_bundle_v2_3",
        "f2_panel_sha256": f2["panel_sha256"],
        "f3_stage_a_panel_sha256": f3a["panel_sha256"],
        "f3_stage_b_policy_sha256": f3b["policy_sha256"],
        "f4_panel_sha256": f4["panel_sha256"],
        "manifests": {"F2": f2, "F3_STAGE_A": f3a, "F3_STAGE_B": f3b, "F4": f4},
    }
    value["bundle_sha256"] = canonical_hash_json(value)
    return value


def build_planner_qualification_integration_v2_3_contract(
    *,
    vault_head: str,
    active_source_tree_sha256: str,
    robotwin_tracked_head: str,
) -> dict[str, Any]:
    bundle = build_manifest_bundle_v2_3()
    signatures = {
        key: list(inspect.signature(function).parameters)
        for key, function in RUNNER_FUNCTIONS.items()
    }
    if any("callback" in name or name.endswith("_fn") for names in signatures.values() for name in names):
        raise AssertionError("V2.3 production runner exposes callable injection")
    value = {
        "schema_version": "cmf_planner_qualification_integration_v2_3_contract",
        "implementation_version": IMPLEMENTATION_VERSION,
        "vault_head": str(vault_head),
        "active_source_tree_sha256": str(active_source_tree_sha256),
        "robotwin_tracked_head": str(robotwin_tracked_head),
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "manifest_sha256s": {
            "F2": bundle["f2_panel_sha256"],
            "F3_STAGE_A": bundle["f3_stage_a_panel_sha256"],
            "F3_STAGE_B": bundle["f3_stage_b_policy_sha256"],
            "F4": bundle["f4_panel_sha256"],
        },
        "runner_symbols": RUNNER_SYMBOLS,
        "runner_signatures": signatures,
        "production_arbitrary_callable_injection_allowed": False,
        "planner_rng_reset_receipt_required": True,
        "unique_authorization_scene_output_per_job": True,
        "o_excl_output_required": True,
        "source_change_invalidates_remaining_authorizations": True,
        "infrastructure_error_stops_entire_wave": True,
        "real_planner_fail_is_terminal_candidate_evidence": True,
        "guard_contract": {
            "allowed_physical_gpu_indices": list(range(8)),
            "fresh_idle_precheck": True,
            "physical_index_uuid_pci_lease_equal": True,
            "one_job_per_gpu": True,
            "root_or_scene_job_sharding_allowed": False,
            "pre_post_cleanup_required": True,
            "planner_query_scene_wall_time_hard_counted": True,
        },
        "authorization": {
            "planner_execution": False,
            "gpu_execution": False,
            "physical_execution": False,
            "stage1": False,
            "formal_360": False,
            "training": False,
            "h_reveal": False,
            "compression": False,
            "pi_0_5": False,
        },
        "physical_execution_count": 0,
        "new_trajectory_count": 0,
        "stage0_reopened": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


def build_planner_wiring_smoke_v1_proposal() -> dict[str, Any]:
    bundle = build_manifest_bundle_v2_3()
    f2_entries = bundle["manifests"]["F2"]["ordered_recipes"]
    f2_left = next(item for item in f2_entries if item["arm"] == "left")
    f2_right = next(item for item in f2_entries if item["arm"] == "right")
    f3_entries = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
    f3_first = f3_entries[0]
    f3_second = next(
        item
        for item in f3_entries
        if item["stratum"]["asset_model_id"] != f3_first["stratum"]["asset_model_id"]
        and item["stratum"]["arm"] != f3_first["stratum"]["arm"]
    )
    f4_jobs = [
        item
        for item in bundle["manifests"]["F4"]["ordered_jobs"]
        if item["candidate_rank"] == 1
    ]
    value = {
        "schema_version": "cmf_planner_wiring_smoke_v1_proposal",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "F2": {
            "recipe_sha256s": [f2_left["recipe_sha256"], f2_right["recipe_sha256"]],
            "different_arms": True,
            "scene_limit": 2,
            "planner_query_limit": 6,
        },
        "F3": {
            "stage_a_recipe_sha256s": [f3_first["recipe_sha256"], f3_second["recipe_sha256"]],
            "different_asset_and_arm": True,
            "stage_a_query_limit": 6,
            "conditional_stage_b_query_limit": 14,
            "scene_limit": 4,
            "planner_query_limit": 20,
        },
        "F4": {
            "candidate_id": f4_jobs[0]["candidate_id"],
            "conditional_program_order": [item["program_id"] for item in f4_jobs],
            "scene_limit": 3,
            "planner_query_limit": 90,
        },
        "aggregate": {
            "planner_query_limit": 116,
            "scene_limit": 9,
            "physical_execution_limit": 0,
            "trajectory_limit": 0,
            "single_fresh_idle_gpu": True,
            "serial_only": True,
            "automatic_full_panel_continuation": False,
        },
        "required_terminal_artifacts": [
            "PLANNER_WIRING_SMOKE_V1_TERMINAL",
            "PLANNER_WIRING_SMOKE_V1_REVIEW",
        ],
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


def build_full_planner_panel_v1_proposal() -> dict[str, Any]:
    bundle = build_manifest_bundle_v2_3()
    value = {
        "schema_version": "cmf_full_planner_panel_v1_proposal",
        "status": "PROPOSAL_ONLY_NOT_AUTHORIZED",
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "F2": {"recipes": 64, "queries_per_recipe": 3, "maximum_queries": 192},
        "F3": {
            "stage_a_recipes": 128,
            "stage_a_queries": 384,
            "maximum_stage_b_strata_survivors": 16,
            "queries_per_stage_b_survivor": 7,
            "stage_b_queries": 112,
            "maximum_queries": 496,
        },
        "F4": {
            "candidate_count": 8,
            "queries_per_candidate": 90,
            "maximum_queries": 720,
            "stop_after_lowest_rank_complete_three_program_pass": True,
        },
        "maximum_aggregate_queries": 1408,
        "separate_family_authorizations_required": True,
        "maximum_parallel_family_gpus_after_smoke": 3,
        "same_family_serial_order_required": True,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["proposal_sha256"] = canonical_hash_json(value)
    return value


def select_f3_stage_b_survivors_v1(
    panel: Mapping[str, Any],
    policy: Mapping[str, Any],
    stage_a_terminals: Sequence[Mapping[str, Any]],
) -> list[str]:
    source = canonical_jsonable(panel)
    entries = {item["recipe_sha256"]: item for item in source["ordered_recipes"]}
    passing = {
        item.get("recipe_sha256")
        for item in stage_a_terminals
        if item.get("stage_a_pass") is True
    }
    selected = []
    for stratum in policy["ordered_strata"]:
        matches = [
            item
            for item in source["ordered_recipes"]
            if item["recipe_sha256"] in passing and item["stratum"] == stratum
        ]
        if matches:
            selected.append(matches[0]["recipe_sha256"])
    if len(selected) > 16 or any(item not in entries for item in selected):
        raise AssertionError("F3 Stage-B survivor policy changed")
    return selected


def validate_f4_next_job_v1(
    panel: Mapping[str, Any],
    requested_job: Mapping[str, Any],
    prior_terminals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    source = canonical_jsonable(panel)
    jobs = source["ordered_jobs"]
    matches = [item for item in jobs if item["job_sha256"] == requested_job.get("job_sha256")]
    if len(matches) != 1:
        raise ValueError("F4 requested job is outside the frozen panel")
    requested = matches[0]
    completed = {
        (item.get("candidate_id"), item.get("program_id")): item
        for item in prior_terminals
    }
    for rank in range(1, requested["candidate_rank"]):
        candidate_id = next(
            item["candidate_id"] for item in jobs if item["candidate_rank"] == rank
        )
        values = [completed.get((candidate_id, program_id)) for program_id in ("F4-ABC", "F4-ACB", "F4-BAC")]
        if any(item is None for item in values):
            raise ValueError("F4 higher rank cannot issue before lower rank terminates")
        if all(item.get("robot_kinematic_table_world_planner_pass") is True for item in values):
            raise ValueError("F4 higher rank cannot issue after lower rank full pass")
    same_rank_order = ("F4-ABC", "F4-ACB", "F4-BAC")
    index = same_rank_order.index(requested["program_id"])
    for prior_program in same_rank_order[:index]:
        prior = completed.get((requested["candidate_id"], prior_program))
        if prior is None or prior.get("robot_kinematic_table_world_planner_pass") is not True:
            raise ValueError("F4 conditional program order is not satisfied")
    return requested


__all__ = [
    "IMPLEMENTATION_VERSION", "RUNNER_SYMBOLS",
    "build_full_planner_panel_v1_proposal",
    "build_manifest_bundle_v2_3",
    "build_planner_qualification_integration_v2_3_contract",
    "build_planner_wiring_smoke_v1_proposal",
    "select_f3_stage_b_survivors_v1",
    "validate_f4_next_job_v1",
]
