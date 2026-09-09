"""Independent V2.1 execution contract validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


TASK_ID = "f2_f3_redesign_20260907"
EXECUTION_VERSION = "redesign_f2_f3_v1"
ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
BUDGET_CAPS = {
    "solver_problems": 2980,
    "fresh_scenes": 136,
    "action_scenes": 118,
    "collection_attempts": 71,
    "gpu_lease_seconds": 61200,
}
ROOTS = ("F2-A", "F2-B", "F3-A", "F3-B")
COUNTERS = tuple(BUDGET_CAPS)


class ContractError(ValueError):
    """Raised for an invalid or accidentally inherited execution contract."""


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{name} must be a non-negative integer")
    return value


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    if contract.get("task_id") != TASK_ID:
        raise ContractError("wrong independent task id")
    if contract.get("execution_version") != EXECUTION_VERSION:
        raise ContractError("wrong execution version")
    if contract.get("status") != "ACTIVE":
        raise ContractError("contract is not active")
    if list(contract.get("allowed_physical_gpu_indices", [])) != list(
        ALLOWED_PHYSICAL_GPU_INDICES
    ):
        raise ContractError("contract must authorize physical GPU0--7")
    caps = contract.get("budget_caps")
    if not isinstance(caps, Mapping) or {
        key: _integer(caps.get(key), f"budget_caps.{key}") for key in COUNTERS
    } != BUDGET_CAPS:
        raise ContractError("budget caps do not match the V2.1 common cap")
    policy = contract.get("gpu_policy", {})
    required_policy = {
        "one_root_one_gpu": True,
        "one_project_job_per_gpu": True,
        "root_sharding": False,
        "busy_gpu_sharing": False,
        "dynamic_fresh_idle_selection": True,
        "automatic_gpu0_fallback": False,
        "fresh_guard_before_launch": True,
        "fresh_post_snapshot": True,
        "owned_cleanup_and_device_idle_separate": True,
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise ContractError(f"GPU policy mismatch at {key}")
    scope = contract.get("scientific_scope", {})
    if scope.get("families") != ["F2", "F3"]:
        raise ContractError("scientific scope must be F2/F3 only")
    if scope.get("pilot_roots") != list(ROOTS):
        raise ContractError("pilot roots are not the four V2.1 roots")
    if scope.get("new_input_count") != 24 or scope.get("combined_index_count") != 48:
        raise ContractError("pilot/index counts are not V2.1 counts")
    legacy = contract.get("legacy_isolation", {})
    for key in ("inherit_old_budget", "inherit_old_state", "inherit_old_revision_count", "mutate_old_state", "reaccept_old_data"):
        if legacy.get(key) is not False:
            raise ContractError(f"legacy isolation failed at {key}")
    return dict(contract)


def load_contract(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        value = json.load(stream)
    return validate_contract(value)


def validate_counters(value: Mapping[str, Any], *, label: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for key in COUNTERS:
        result[key] = _integer(value.get(key), f"{label}.{key}")
    return result


def validate_state(state: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    validate_contract(contract)
    if state.get("task_id") != TASK_ID or state.get("execution_version") != EXECUTION_VERSION:
        raise ContractError("state belongs to another task")
    budget = state.get("budget", {})
    caps = validate_counters(budget.get("caps", {}), label="state.budget.caps")
    if caps != BUDGET_CAPS:
        raise ContractError("state caps differ from contract")
    reserved = validate_counters(budget.get("reserved", {}), label="state.budget.reserved")
    consumed = validate_counters(budget.get("consumed", {}), label="state.budget.consumed")
    for key in COUNTERS:
        if consumed[key] > caps[key] or reserved[key] > caps[key]:
            raise ContractError(f"state exceeds cap for {key}")
    jobs = state.get("jobs")
    if not isinstance(jobs, dict):
        raise ContractError("state.jobs must be a job-id mapping")
    return dict(state)
