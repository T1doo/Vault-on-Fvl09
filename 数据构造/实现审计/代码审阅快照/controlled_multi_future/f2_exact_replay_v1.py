"""Exact replay wrapper for the frozen F2 rank50--61 development search."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_dynamic_search_contract_v3 import validate_cpu_static_screening_v3
from .f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    validate_static_compatibility_matrix_v3,
)


SCHEMA_VERSION = "cmf_f2_exact_replay_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f2_exact_replay_v1"
SCOPE = "F2_EXACT_REPLAY_RANK50_61_V1"
NAMESPACE = "development_pipeline_consolidation_v1_f2_exact_replay_run1"
FROZEN_MATRIX_SHA256 = "2789dbaa70e139ebb270cabf8f7e634b4c5bc23555aa3fe9349425bebcfa3645"
FROZEN_SCREENING_SHA256 = "3b7b7239ef93e20351bb8a5667fee6cee68d8ad485c17fbbef5da7c4d5e1d14e"
FROZEN_RANKS = tuple(range(50, 62))
FROZEN_CANDIDATE_KEY_SHA256 = (
    "b4267b0acac0541309753e8d9e0318c5c311b19570dce2e5184a32a5419cb1bc",
    "6256da755ee92c4c719eb4cbbaa33646498256ca87864374ac3e833ce97c97f3",
    "f5b3074fde6124ed260fbb27c083c9c55f0f10e32635fcb417111a8622cab792",
    "a2205f25c1813e36e9684ab7287a500c191197ff12fb4c41d626cf5caf3774f9",
    "e0f0f9862e6a841ee48f6a72a4941ec59a15bd8cf93024ca9d8e0f6b59e7aa0a",
    "a686b286a0aeb78f435d0440beed16528aa068b566966762be3399c45aa11001",
    "cb6683db2dd99923751372f668bac98c24284166d9b0b23fbc4c5032746bf24e",
    "2ed0b358d60833945f1b53a40dcd30cee8630f68a75d0c97b67ea14de8028d63",
    "ff68885751f202b6d8853e7b1d41d890318d9fb66b45d00f9785c5bc4997fb9c",
    "34c5000abbf2ea215db1d9a663b44baab52765fc4da54304ac8a6ba4c987e5ac",
    "40067cf93dcf68f9d1cc2343a403d739989224b1971f14b6b429b21657c706f3",
    "e2b3f0d4849f5f80c6f9c74afb700331fe28490521ae22b3ab9541f889d159e6",
)


def build_f2_exact_replay_v1(
    matrix: Mapping[str, Any], screening: Mapping[str, Any]
) -> dict[str, Any]:
    frozen_matrix = validate_static_compatibility_matrix_v3(matrix)
    frozen_screening = validate_cpu_static_screening_v3(screening)
    candidates = frozen_screening["dynamic_scope"]["candidates"]
    ranks = tuple(int(item["rank"]) for item in candidates)
    hashes = tuple(str(item["candidate_key_sha256"]) for item in candidates)
    checks = {
        "matrix_hash": frozen_matrix["matrix_sha256"] == FROZEN_MATRIX_SHA256,
        "screening_hash": frozen_screening["screening_sha256"]
        == FROZEN_SCREENING_SHA256,
        "matrix_link": frozen_screening["matrix_sha256"] == FROZEN_MATRIX_SHA256,
        "exact_ranks": ranks == FROZEN_RANKS,
        "exact_candidate_hashes": hashes == FROZEN_CANDIDATE_KEY_SHA256,
        "exact_candidate_count": len(candidates) == 12,
    }
    if not all(checks.values()):
        raise ValueError(f"F2 exact replay source differs from frozen V3: {checks}")
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "namespace": NAMESPACE,
        "family": "F2",
        "matrix_sha256": FROZEN_MATRIX_SHA256,
        "screening_sha256": FROZEN_SCREENING_SHA256,
        "candidate_ranks": list(FROZEN_RANKS),
        "candidate_key_sha256": list(FROZEN_CANDIDATE_KEY_SHA256),
        "program_ids": list(PROGRAM_IDS),
        "selection_rule": "first rank satisfying all frozen gates",
        "maximum_dynamic_candidates": 12,
        "maximum_development_roots": 1,
        "inside_on_beside_verifier_changed": False,
        "asset_changed": False,
        "layout_changed": False,
        "planner_changed": False,
        "threshold_changed": False,
        "release_changed": False,
        "candidate_rank_changed": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "source_checks": checks,
    }
    value["exact_replay_contract_sha256"] = canonical_hash_json(value)
    return value


def f2_exact_replay_budget_v1() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_exact_replay_budget_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "maximum_dynamic_candidates": 12,
        "maximum_passive_on_scenes": 12,
        "maximum_planner_only_roots": 12,
        "maximum_development_execution_roots": 1,
        "maximum_prefix_reference_executions": 13,
        "maximum_suffix_execution_attempts": 3,
        "maximum_planner_queries_total": 768,
        "maximum_recovery_attempts": 0,
        "maximum_wall_time_seconds": 21600,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "automatic_retry": False,
        "fallback_beyond_rank61": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = canonical_hash_json(value)
    return value


def build_f2_exact_replay_spec_v1(
    matrix: Mapping[str, Any], screening: Mapping[str, Any]
) -> dict[str, Any]:
    contract = build_f2_exact_replay_v1(matrix, screening)
    value = {
        "schema_version": "cmf_f2_exact_replay_planned_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "slot_id": "f2-exact-replay-rank50-61-v1",
        "family": "F2",
        "arm": "left",
        "seed": 20260829,
        "generator": "controlled_multi_future_f2_exact_replay_v1_adapter",
        "origin": "development_pipeline_consolidation_and_template_convergence_v1",
        "f2_exact_replay_v1": contract,
        "f2_exact_replay_contract_sha256": contract[
            "exact_replay_contract_sha256"
        ],
        "canonical_program_ids": list(PROGRAM_IDS),
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_scope_spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_exact_replay_spec_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    payload = dict(normalized)
    digest = payload.pop("planned_scope_spec_sha256", None)
    if digest != canonical_hash_json(payload):
        raise ValueError("F2 exact replay planned spec hash mismatch")
    contract = payload.get("f2_exact_replay_v1")
    if not isinstance(contract, Mapping):
        raise ValueError("F2 exact replay planned spec lacks contract")
    fixed = {
        "schema_version": "cmf_f2_exact_replay_planned_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "slot_id": "f2-exact-replay-rank50-61-v1",
        "family": "F2",
        "arm": "left",
        "seed": 20260829,
        "generator": "controlled_multi_future_f2_exact_replay_v1_adapter",
        "origin": "development_pipeline_consolidation_and_template_convergence_v1",
        "f2_exact_replay_contract_sha256": contract.get(
            "exact_replay_contract_sha256"
        ),
        "canonical_program_ids": list(PROGRAM_IDS),
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    if any(payload.get(key) != expected for key, expected in fixed.items()):
        raise ValueError("F2 exact replay planned spec fixed fields changed")
    if (
        contract.get("matrix_sha256") != FROZEN_MATRIX_SHA256
        or contract.get("screening_sha256") != FROZEN_SCREENING_SHA256
        or contract.get("candidate_ranks") != list(FROZEN_RANKS)
        or contract.get("candidate_key_sha256")
        != list(FROZEN_CANDIDATE_KEY_SHA256)
        or contract.get("exact_replay_contract_sha256")
        != canonical_hash_json(
            {
                key: item
                for key, item in contract.items()
                if key != "exact_replay_contract_sha256"
            }
        )
    ):
        raise ValueError("F2 exact replay embedded contract changed")
    return normalized


def finalize_f2_exact_replay_v1(result: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(result)
    dynamic = list(normalized.get("dynamic_candidate_receipts", []))
    selected = normalized.get("selected_binding")
    root = normalized.get("development_root")
    ranks = [int(item.get("rank", -1)) for item in dynamic]
    rank_prefix = list(FROZEN_RANKS[: len(ranks)])
    if ranks != rank_prefix or len(dynamic) > 12:
        raise ValueError("F2 exact replay dynamic receipts violate rank order")
    pass_root = (
        selected is not None
        and isinstance(root, Mapping)
        and root.get("status") == "accepted"
        and int(root.get("branch_execution_attempt_count", -1)) == 3
    )
    exhausted = selected is None and len(dynamic) == 12
    if not (pass_root or exhausted):
        raise ValueError("F2 exact replay result is not terminal")
    status = "PASS_TEMPLATE" if pass_root else "ALL_12_DYNAMIC_CANDIDATES_EXHAUSTED"
    value = {
        "schema_version": "cmf_f2_exact_replay_terminal_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": status,
        "dynamic_candidate_receipts": dynamic,
        "selected_binding": selected,
        "development_root": root,
        "planner_query_count_total": int(
            normalized.get("planner_query_count_total", 0)
        ),
        "prefix_reference_execution_count": int(
            normalized.get("prefix_reference_execution_count", 0)
        ),
        "branch_execution_attempt_count": int(
            normalized.get("branch_execution_attempt_count", 0)
        ),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "FROZEN_CANDIDATE_KEY_SHA256",
    "FROZEN_MATRIX_SHA256",
    "FROZEN_RANKS",
    "FROZEN_SCREENING_SHA256",
    "IMPLEMENTATION_VERSION",
    "NAMESPACE",
    "SCOPE",
    "build_f2_exact_replay_v1",
    "build_f2_exact_replay_spec_v1",
    "f2_exact_replay_budget_v1",
    "finalize_f2_exact_replay_v1",
    "validate_f2_exact_replay_spec_v1",
]
