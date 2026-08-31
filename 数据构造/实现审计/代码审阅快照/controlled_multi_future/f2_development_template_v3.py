"""Nonformal one-root execution template for a selected F2 V3 binding.

This is a contract layer, not a GPU launch.  The shared Guard dispatcher must
be wired separately.  Until a hash-bound authorization and selected binding
are supplied, the runner fails closed before constructing any scene.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from .f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    validate_frozen_asset_layout_binding_v3,
)


SCOPE = "F2_official_asset_first_all_gates_one_development_root_v3"
NAMESPACE = "post_stage0_f2_asset_redesign_v3_one_root_run1"
SCHEMA_VERSION = "cmf_f2_one_development_root_template_v3"
AUTHORIZATION_SCHEMA_VERSION = "cmf_f2_one_development_root_authorization_v3"
GPU_POLICY_VERSION = "cmf_gpu_parallel_policy_v2"


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def _hash_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def f2_development_budget_v3() -> dict[str, Any]:
    return {
        "schema_version": "cmf_f2_development_budget_v3",
        "scope": SCOPE,
        "maximum_dynamic_candidate_count": 12,
        "maximum_development_root_count": 1,
        "program_ids": list(PROGRAM_IDS),
        "attempts_per_program": 1,
        "maximum_branch_execution_attempts": 3,
        "maximum_planner_queries_total": 768,
        "maximum_recovery_attempts": 0,
        "maximum_wall_time_seconds": 14400,
        "automatic_retry": False,
        "fallback_beyond_candidate_12": False,
        "temporary_waypoint_allowed": False,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }


def build_f2_development_scope_v3(binding: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_frozen_asset_layout_binding_v3(binding)
    budget = f2_development_budget_v3()
    value = {
        "schema_version": "cmf_f2_development_scope_v3",
        "scope": SCOPE,
        "output_namespace": NAMESPACE,
        "selected_binding_sha256": checked["binding_sha256"],
        "selected_candidate_key": checked["selected_candidate_key"],
        "selected_execution_arm": checked["selected_execution_arm"],
        "program_ids": list(PROGRAM_IDS),
        "branch_order": list(PROGRAM_IDS),
        "same_main_object_all_branches": True,
        "same_execution_arm_all_branches": True,
        "fresh_scene_per_branch": True,
        "same_current_anchor_prefix_lineage_required": True,
        "inside_on_beside_semantics_unchanged": True,
        "release_chain_or_verifier_relaxation_allowed": False,
        "budget": budget,
        "budget_sha256": _hash_json(budget),
        "guard_dispatch_integrated": False,
        "guard_dispatch_owner": "root_agent_shared_dispatch_merge",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["scope_sha256"] = _hash_json(value)
    return value


def validate_f2_development_authorization_v3(
    value: Mapping[str, Any], *, binding: Mapping[str, Any]
) -> dict[str, Any]:
    checked_binding = validate_frozen_asset_layout_binding_v3(binding)
    expected_budget = f2_development_budget_v3()
    result = _copy(value)
    digest = result.pop("authorization_sha256", None)
    if not isinstance(digest, str) or _hash_json(result) != digest:
        raise ValueError("F2 development authorization hash mismatch")
    checks = {
        "schema": result.get("schema_version") == AUTHORIZATION_SCHEMA_VERSION,
        "scope": result.get("scope") == SCOPE,
        "namespace": result.get("output_namespace") == NAMESPACE,
        "binding": result.get("selected_binding_sha256") == checked_binding["binding_sha256"],
        "single_use": result.get("single_use") is True,
        "no_retry": result.get("automatic_retry") is False,
        "no_recovery": result.get("maximum_recovery_attempts") == 0,
        "one_root": result.get("maximum_development_root_count") == 1,
        "three_executions": result.get("maximum_branch_execution_attempts") == 3,
        "exact_budget": result.get("budget") == expected_budget
        and result.get("budget_sha256") == _hash_json(expected_budget),
        "gpu_policy": result.get("gpu_policy_version") == GPU_POLICY_VERSION
        and result.get("allowed_physical_gpu_indices") == list(range(8))
        and result.get("one_project_job_per_gpu") is True
        and result.get("one_root_one_gpu") is True
        and result.get("root_sharding_authorized") is False,
        "source_lock": isinstance(result.get("source_lock_sha256"), str)
        and len(result["source_lock_sha256"]) == 64,
        "approved": result.get("approved") is True,
        "not_stage0_formal_stage1": result.get("formal_data") is False
        and result.get("stage0_data") is False
        and result.get("stage1_authorized") is False,
    }
    if not all(checks.values()):
        raise ValueError(f"F2 development authorization failed: {checks}")
    return {**result, "authorization_sha256": digest}


class F2AssetBoundDevelopmentControllerV3:
    """Identity/order guard around future runtime callbacks."""

    def __init__(self, binding: Mapping[str, Any]):
        self.binding = validate_frozen_asset_layout_binding_v3(binding)

    @property
    def main_object_id(self) -> int:
        return int(self.binding["selected_candidate_key"]["main_object_model_id"])

    @property
    def arm(self) -> str:
        return str(self.binding["selected_execution_arm"])

    def validate_branch_result(self, result: Mapping[str, Any], *, program_id: str) -> dict[str, Any]:
        value = _copy(result)
        checks = {
            "program": value.get("program_id") == program_id,
            "main_object": value.get("main_object_modelname") == "071_can"
            and value.get("main_object_model_id") == self.main_object_id,
            "arm": value.get("execution_arm") == self.arm,
            "binding": value.get("selected_binding_sha256") == self.binding["binding_sha256"],
            "accepted": value.get("status") == "accepted",
            "verifier": value.get("verifier_pass") is True,
            "release_unchanged": value.get("release_chain_unchanged") is True,
            "verifier_unchanged": value.get("verifier_unchanged") is True,
            "nonformal": value.get("formal_data") is False
            and value.get("stage0_data") is False
            and value.get("stage1_authorized") is False,
            "single_execution": value.get("execution_attempt_count") == 1,
            "no_recovery": value.get("recovery_attempt_count") == 0,
            "fresh_scene": value.get("fresh_scene") is True,
        }
        if not all(checks.values()):
            raise ValueError(f"F2 development branch violated frozen identity: {checks}")
        for name in ("current_sha256", "anchor_sha256", "canonical_prefix_sha256"):
            if not isinstance(value.get(name), str) or len(value[name]) != 64:
                raise ValueError(f"F2 development branch lacks {name}")
        return value


class F2AssetBoundDevelopmentAdapterV3:
    """Binding-preserving scene-factory adapter for the future SAPIEN child."""

    def __init__(
        self,
        *,
        binding: Mapping[str, Any],
        scene_factory: Callable[[str, Mapping[str, Any]], Any],
    ):
        self.binding = validate_frozen_asset_layout_binding_v3(binding)
        self.scene_factory = scene_factory

    def scene(self, program_id: str):
        if program_id not in PROGRAM_IDS:
            raise ValueError("F2 development adapter received an unknown program")
        scene = self.scene_factory(program_id, self.binding)
        identity = getattr(scene, "f2_asset_binding_identity", None)
        expected = {
            "binding_sha256": self.binding["binding_sha256"],
            "main_object_model_id": self.binding["selected_candidate_key"][
                "main_object_model_id"
            ],
            "execution_arm": self.binding["selected_execution_arm"],
        }
        if not isinstance(identity, Mapping) or dict(identity) != expected:
            raise ValueError("F2 development scene does not expose the frozen asset identity")
        return scene


class F2OneDevelopmentRootRunnerV3:
    """Exactly-once callback runner; actual scene construction remains external."""

    def __init__(
        self,
        *,
        binding: Mapping[str, Any],
        authorization: Mapping[str, Any],
        guard_context: Mapping[str, Any],
    ):
        self.controller = F2AssetBoundDevelopmentControllerV3(binding)
        self.authorization = validate_f2_development_authorization_v3(
            authorization, binding=self.controller.binding
        )
        guard = _copy(guard_context)
        checks = {
            "schema": guard.get("schema_version") == "cmf_f2_guard_launch_context_v3",
            "scope": guard.get("scope") == SCOPE,
            "authorization": guard.get("authorization_sha256")
            == self.authorization["authorization_sha256"],
            "binding": guard.get("selected_binding_sha256")
            == self.controller.binding["binding_sha256"],
            "fresh_recheck": guard.get("atomic_fresh_idle_recheck_pass") is True,
            "uuid_bound": isinstance(guard.get("physical_gpu_uuid"), str)
            and guard["physical_gpu_uuid"].startswith("GPU-"),
            "physical_index": guard.get("physical_gpu_index") in range(8),
            "lease": guard.get("per_gpu_lease_acquired") is True,
            "source_lock": guard.get("source_lock_sha256")
            == self.authorization["source_lock_sha256"],
        }
        if not all(checks.values()):
            raise ValueError(f"F2 development Guard launch context failed: {checks}")
        self.guard_context = guard
        self._consumed = False

    def run(self, execute_branch: Callable[[str, Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
        if self._consumed:
            raise RuntimeError("F2 development authorization is single-use")
        self._consumed = True
        branches = []
        for program_id in PROGRAM_IDS:
            raw = execute_branch(program_id, self.controller.binding)
            branches.append(self.controller.validate_branch_result(raw, program_id=program_id))
        planner_queries = sum(int(branch.get("planner_query_count", -1)) for branch in branches)
        if planner_queries < 0 or planner_queries > int(
            self.authorization["budget"]["maximum_planner_queries_total"]
        ):
            raise ValueError("F2 development root exceeded planner-query budget")
        lineage = {
            name: {branch[name] for branch in branches}
            for name in ("current_sha256", "anchor_sha256", "canonical_prefix_sha256")
        }
        if any(len(values) != 1 for values in lineage.values()):
            raise ValueError("F2 development branches do not share current/anchor/prefix lineage")
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "scope": SCOPE,
            "selected_binding_sha256": self.controller.binding["binding_sha256"],
            "program_ids": list(PROGRAM_IDS),
            "branch_count": len(branches),
            "all_branches_accepted": True,
            "planner_query_count_total": planner_queries,
            "execution_attempt_count_total": sum(
                int(branch["execution_attempt_count"]) for branch in branches
            ),
            "recovery_attempt_count_total": 0,
            "same_main_object_all_branches": True,
            "same_execution_arm_all_branches": True,
            "lineage_sha256s": {name: next(iter(values)) for name, values in lineage.items()},
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        receipt["receipt_sha256"] = _hash_json(receipt)
        return receipt


def guard_dispatch_descriptor_v3() -> dict[str, Any]:
    """Descriptor for the root agent's conflict-free shared Guard merge."""

    return {
        "scope": SCOPE,
        "authorization_schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "runner_module": "controlled_multi_future.f2_development_template_v3",
        "allowed_physical_gpu_indices": list(range(8)),
        "single_use": True,
        "automatic_retry": False,
        "shared_guard_dispatch_integrated": False,
        "must_preserve_f3_v2_1_dispatch": True,
    }


__all__ = [
    "F2AssetBoundDevelopmentControllerV3",
    "F2AssetBoundDevelopmentAdapterV3",
    "F2OneDevelopmentRootRunnerV3",
    "SCOPE",
    "build_f2_development_scope_v3",
    "f2_development_budget_v3",
    "guard_dispatch_descriptor_v3",
    "validate_f2_development_authorization_v3",
]
