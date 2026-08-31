"""Current GPU0--7 policy and dynamic multi-GPU wave scheduling.

This module is additive.  It does not rewrite historical one-shot GPU
authorizations or their immutable evidence.  New Controlled Multi-Future GPU
work must bind this policy (or a later explicitly approved version).

The scheduler is deliberately pure CPU code.  A scheduling decision is not a
reservation: every assigned job must still pass the atomic GPU Guard's fresh
UUID/idle check immediately before authorization consumption and launch.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


POLICY_VERSION = "cmf_gpu_parallel_policy_v2"
SCHEDULE_SCHEMA_VERSION = "cmf_gpu_dynamic_wave_schedule_v2"
ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
MAX_SCHEDULER_SNAPSHOT_AGE_SECONDS = 15.0
IDLE_MAX_MEMORY_MIB = 100
IDLE_MAX_UTILIZATION_PERCENT = 1
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class GpuPolicyError(ValueError):
    """Raised when a request could weaken or bypass the current GPU policy."""


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise GpuPolicyError("GPU snapshot captured_at must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise GpuPolicyError("GPU snapshot captured_at is invalid") from exc
    if parsed.tzinfo is None:
        raise GpuPolicyError("GPU snapshot captured_at must include timezone")
    return parsed.astimezone(timezone.utc)


def _normalize_gpu_snapshot(
    snapshots: Sequence[Mapping[str, Any]], *, now: datetime
) -> list[dict[str, Any]]:
    if len(snapshots) != len(ALLOWED_PHYSICAL_GPU_INDICES):
        raise GpuPolicyError("live snapshot must contain physical GPU0--7 exactly once")
    normalized: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    seen_uuids: set[str] = set()
    for raw in snapshots:
        index = int(raw.get("physical_index", -1))
        uuid = raw.get("uuid", raw.get("gpu_uuid"))
        if index not in ALLOWED_PHYSICAL_GPU_INDICES or index in seen_indices:
            raise GpuPolicyError("GPU index is outside unique physical GPU0--7")
        if not isinstance(uuid, str) or not uuid.startswith("GPU-") or uuid in seen_uuids:
            raise GpuPolicyError("GPU UUID is missing or duplicated")
        captured = _parse_time(raw.get("captured_at"))
        age = (now - captured).total_seconds()
        if age < 0:
            raise GpuPolicyError("GPU snapshot timestamp is in the future")
        processes = raw.get("compute_processes")
        if not isinstance(processes, list):
            raise GpuPolicyError("GPU compute_processes must be a list")
        memory = int(raw.get("memory_used_mib", -1))
        utilization = int(raw.get("utilization_percent", -1))
        pstate = str(raw.get("pstate", ""))
        checks = {
            "allowed_index": index in ALLOWED_PHYSICAL_GPU_INDICES,
            "snapshot_fresh": age <= MAX_SCHEDULER_SNAPSHOT_AGE_SECONDS,
            "near_baseline_memory": 0 <= memory <= IDLE_MAX_MEMORY_MIB,
            "near_zero_utilization": (
                0 <= utilization <= IDLE_MAX_UTILIZATION_PERCENT
            ),
            "idle_pstate": pstate == "P8",
            "no_compute_process": len(processes) == 0,
        }
        normalized.append(
            {
                "physical_index": index,
                "gpu_uuid": uuid,
                "memory_used_mib": memory,
                "utilization_percent": utilization,
                "pstate": pstate,
                "compute_processes": json.loads(
                    json.dumps(processes, sort_keys=True, allow_nan=False)
                ),
                "captured_at": captured.isoformat(),
                "snapshot_age_seconds": age,
                "checks": checks,
                "independently_fresh_idle": all(checks.values()),
            }
        )
        seen_indices.add(index)
        seen_uuids.add(uuid)
    if seen_indices != set(ALLOWED_PHYSICAL_GPU_INDICES):
        raise GpuPolicyError("live snapshot omitted a physical GPU index")
    return sorted(normalized, key=lambda item: item["physical_index"])


def validate_current_gpu_authorization(value: Mapping[str, Any]) -> dict[str, Any]:
    """Reject new authorizations that silently reinstate GPU0-only behavior."""

    required = {
        "gpu_policy_version": POLICY_VERSION,
        "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
        "dynamic_fresh_idle_selection": True,
        "parallel_different_cards_authorized": True,
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "share_busy_gpu_authorized": False,
        "atomic_guard_recheck_before_launch": True,
        "automatic_gpu0_fallback": False,
    }
    mismatches = {
        key: {"expected": expected, "actual": value.get(key)}
        for key, expected in required.items()
        if value.get(key) != expected
    }
    if mismatches:
        raise GpuPolicyError(f"current GPU authorization policy mismatch: {mismatches}")
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def current_gpu_policy_artifact() -> dict[str, Any]:
    value = {
        "schema_version": POLICY_VERSION,
        "gpu_policy_version": POLICY_VERSION,
        "host": "fvl05",
        "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
        "dynamic_fresh_idle_selection": True,
        "parallel_different_cards_authorized": True,
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "share_busy_gpu_authorized": False,
        "atomic_guard_recheck_before_launch": True,
        "automatic_gpu0_fallback": False,
        "scheduler_snapshot_is_reservation": False,
        "schedule_partial_wave_when_fewer_cards_idle": True,
        "historical_gpu0_only_authorizations_remain_immutable": True,
        "new_gpu0_only_authorization_allowed": False,
    }
    validate_current_gpu_authorization(value)
    value["policy_sha256"] = _canonical_sha256(value)
    return value


def _normalize_jobs(jobs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_jobs: set[str] = set()
    seen_roots: set[str] = set()
    seen_namespaces: set[str] = set()
    for order, raw in enumerate(jobs):
        job_id = raw.get("job_id")
        root_id = raw.get("root_id")
        family = raw.get("family")
        namespace = raw.get("output_namespace")
        auth_sha = raw.get("authorization_receipt_sha256")
        if not all(isinstance(item, str) and item for item in (
            job_id,
            root_id,
            family,
            namespace,
        )):
            raise GpuPolicyError("job/root/family/output identifiers must be non-empty")
        if job_id in seen_jobs or root_id in seen_roots or namespace in seen_namespaces:
            raise GpuPolicyError("jobs, roots and output namespaces must be unique per wave")
        if not isinstance(auth_sha, str) or HEX64.fullmatch(auth_sha) is None:
            raise GpuPolicyError("job authorization receipt SHA-256 is invalid")
        if raw.get("allowed_physical_gpu_indices") != list(
            ALLOWED_PHYSICAL_GPU_INDICES
        ):
            raise GpuPolicyError("new jobs must authorize dynamic physical GPU0--7")
        if raw.get("root_sharded") is not False:
            raise GpuPolicyError("one root must remain one unsharded GPU job")
        rank = int(raw.get("queue_rank", order))
        normalized.append(
            {
                "job_id": job_id,
                "root_id": root_id,
                "family": family,
                "output_namespace": namespace,
                "authorization_receipt_sha256": auth_sha,
                "allowed_physical_gpu_indices": list(
                    ALLOWED_PHYSICAL_GPU_INDICES
                ),
                "root_sharded": False,
                "queue_rank": rank,
            }
        )
        seen_jobs.add(job_id)
        seen_roots.add(root_id)
        seen_namespaces.add(namespace)
    return sorted(normalized, key=lambda item: (item["queue_rank"], item["job_id"]))


def schedule_dynamic_gpu_wave(
    jobs: Sequence[Mapping[str, Any]],
    snapshots: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
    max_concurrency: int = 8,
) -> dict[str, Any]:
    """Assign as many queued roots as currently idle cards permit.

    Unlike the historical Stage 0 v1/v1.1 scheduler, this does not require four
    GPUs to become idle simultaneously.  One idle GPU yields one assignment;
    several idle GPUs yield a parallel wave.  Busy GPU0 never blocks use of an
    idle GPU1--7 and is never used as an implicit fallback.
    """

    if not 1 <= int(max_concurrency) <= len(ALLOWED_PHYSICAL_GPU_INDICES):
        raise GpuPolicyError("max_concurrency must be between 1 and 8")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    normalized_gpus = _normalize_gpu_snapshot(snapshots, now=current)
    normalized_jobs = _normalize_jobs(jobs)
    idle = [
        item for item in normalized_gpus if item["independently_fresh_idle"]
    ][: int(max_concurrency)]
    scheduled_count = min(len(normalized_jobs), len(idle))
    assignments = []
    snapshot_sha = _canonical_sha256(normalized_gpus)
    policy = current_gpu_policy_artifact()
    for job, gpu in zip(normalized_jobs[:scheduled_count], idle[:scheduled_count]):
        assignments.append(
            {
                **job,
                "physical_gpu_index": gpu["physical_index"],
                "expected_gpu_uuid": gpu["gpu_uuid"],
                "scheduler_snapshot_sha256": snapshot_sha,
                "gpu_policy_sha256": policy["policy_sha256"],
                "atomic_guard_recheck_required": True,
                "authorization_consumed_by_scheduler": False,
                "scheduler_decision_is_reservation": False,
            }
        )
    deferred = normalized_jobs[scheduled_count:]
    selected_indices = [item["physical_gpu_index"] for item in assignments]
    checks = {
        "only_allowed_indices": all(
            item in ALLOWED_PHYSICAL_GPU_INDICES for item in selected_indices
        ),
        "one_job_per_gpu": len(selected_indices) == len(set(selected_indices)),
        "one_root_per_assignment": len(
            {item["root_id"] for item in assignments}
        )
        == len(assignments),
        "all_selected_fresh_idle": all(
            next(
                gpu
                for gpu in normalized_gpus
                if gpu["physical_index"] == assignment["physical_gpu_index"]
            )["independently_fresh_idle"]
            for assignment in assignments
        ),
        "no_busy_gpu0_fallback": not (
            next(gpu for gpu in normalized_gpus if gpu["physical_index"] == 0)[
                "independently_fresh_idle"
            ]
            is False
            and 0 in selected_indices
        ),
        "partial_wave_supported": scheduled_count == min(
            len(normalized_jobs), len(idle)
        ),
        "authorization_not_consumed": all(
            item["authorization_consumed_by_scheduler"] is False
            for item in assignments
        ),
    }
    if not all(checks.values()):
        raise GpuPolicyError(f"dynamic GPU schedule failed invariants: {checks}")
    return {
        "schema_version": SCHEDULE_SCHEMA_VERSION,
        "gpu_policy": policy,
        "scheduler_snapshot_sha256": snapshot_sha,
        "snapshot": normalized_gpus,
        "queue_size": len(normalized_jobs),
        "fresh_idle_gpu_indices": [
            item["physical_index"] for item in normalized_gpus
            if item["independently_fresh_idle"]
        ],
        "assignments": assignments,
        "assigned_count": len(assignments),
        "deferred_jobs": deferred,
        "deferred_count": len(deferred),
        "maximum_parallelism_this_wave": len(assignments),
        "status": (
            "waiting_no_fresh_idle_gpu"
            if not assignments and normalized_jobs
            else "scheduled_all"
            if not deferred
            else "scheduled_partial_wave"
        ),
        "checks": checks,
        "pass": True,
    }


__all__ = [
    "ALLOWED_PHYSICAL_GPU_INDICES",
    "GpuPolicyError",
    "POLICY_VERSION",
    "current_gpu_policy_artifact",
    "schedule_dynamic_gpu_wave",
    "validate_current_gpu_authorization",
]
