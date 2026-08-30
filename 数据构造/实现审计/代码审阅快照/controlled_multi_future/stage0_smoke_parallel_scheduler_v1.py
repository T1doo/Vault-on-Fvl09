"""Pure-CPU assignment of four Stage 0 family jobs to fresh-idle GPUs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .probes.gpu_guard import is_idle
from .stage0_smoke_budget_v1 import STAGE0_SCOPES


def _idle(snapshot: Mapping[str, Any]) -> bool:
    try:
        captured = datetime.fromisoformat(str(snapshot["captured_at"]))
        if captured.tzinfo is None:
            return False
        age = (
            datetime.now(timezone.utc) - captured.astimezone(timezone.utc)
        ).total_seconds()
        return (
            int(snapshot.get("physical_index", -1)) in range(8)
            and isinstance(snapshot.get("uuid"), str)
            and bool(snapshot["uuid"])
            and 0 <= age <= 60
            and is_idle(snapshot)
        )
    except (KeyError, TypeError, ValueError):
        return False


def assign_stage0_scopes_to_idle_gpus(
    bundle_set: Mapping[str, Any],
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    bundles = bundle_set.get("bundles")
    if not isinstance(bundles, Mapping) or set(bundles) != set(STAGE0_SCOPES):
        raise ValueError("Stage 0 scheduler requires the exact four-bundle set")
    idle = sorted(
        (dict(item) for item in snapshots if _idle(item)),
        key=lambda item: int(item["physical_index"]),
    )
    if len({int(item["physical_index"]) for item in idle}) != len(idle):
        raise ValueError("GPU snapshot contains duplicate physical indices")
    if len({item["uuid"] for item in idle}) != len(idle):
        raise ValueError("GPU snapshot contains duplicate UUIDs")
    if len(idle) < 4:
        return {
            "schema_version": "cmf_stage0_smoke_parallel_schedule_v1",
            "assignments": [],
            "assigned_scope_count": 0,
            "pending_scopes": list(STAGE0_SCOPES),
            "one_project_job_per_gpu": True,
            "one_family_root_per_gpu": True,
            "all_selected_gpus_fresh_idle": False,
            "required_simultaneous_idle_gpu_count": 4,
            "pass": False,
        }
    assignments = []
    for scope, gpu in zip(STAGE0_SCOPES, idle):
        bundle = bundles[scope]
        if int(gpu["physical_index"]) not in bundle.get(
            "physical_gpu_indices", []
        ):
            raise ValueError("selected GPU is outside bundle authorization")
        assignments.append(
            {
                "scope": scope,
                "family": bundle["family"],
                "physical_gpu_index": int(gpu["physical_index"]),
                "gpu_uuid": gpu["uuid"],
                "authorization_path": bundle["authorization_path"],
                "guard_path": bundle["guard_path"],
                "output_namespace": bundle["output_namespace"],
                "timeout_seconds": int(bundle["timeout_seconds"]),
                "child_command": list(bundle["child_command"]),
            }
        )
    assigned_scopes = {item["scope"] for item in assignments}
    result = {
        "schema_version": "cmf_stage0_smoke_parallel_schedule_v1",
        "assignments": assignments,
        "assigned_scope_count": len(assignments),
        "pending_scopes": [
            scope for scope in STAGE0_SCOPES if scope not in assigned_scopes
        ],
        "one_project_job_per_gpu": len(
            {item["physical_gpu_index"] for item in assignments}
        )
        == len(assignments),
        "one_family_root_per_gpu": len(
            {item["family"] for item in assignments}
        )
        == len(assignments),
        "all_selected_gpus_fresh_idle": len(assignments)
        <= len(idle),
    }
    result["pass"] = (
        result["assigned_scope_count"] == 4
        and not result["pending_scopes"]
        and result["one_project_job_per_gpu"]
        and result["one_family_root_per_gpu"]
        and result["all_selected_gpus_fresh_idle"]
    )
    return result


__all__ = ["assign_stage0_scopes_to_idle_gpus"]
