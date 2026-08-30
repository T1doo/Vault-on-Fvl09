"""Fail-closed GPU0–7 discovery and family-level scheduling for runtime-v3_4.

The pure parser/scheduler is unit-testable without touching CUDA.  Live
``nvidia-smi`` acquisition is explicit and does not launch a project job.
Every actual job still requires its own authorization, atomic Guard, UUID
binding, precheck, timeout and post-release receipt.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "cmf_runtime_v3_4_multi_gpu_scheduling_audit_v1"
ALLOWED_INDICES = tuple(range(8))
IDLE_MAX_MEMORY_MIB = 64
IDLE_MAX_UTILIZATION_PERCENT = 0
SCOPE_ORDER = (
    "F1_shared_regression_v3_4",
    "F2_inside_targeted_v10",
    "F3_grasp_three_context_v10",
    "F4_corridor_A_v10",
    "F2_full_root_v10",
    "F3_full_root_v10",
    "F4_BC_AB_v10",
    "F4_full_root_v10",
)


def _rows(text: str, expected_columns: int) -> list[list[str]]:
    parsed = []
    for row in csv.reader(io.StringIO(text.strip())):
        values = [item.strip() for item in row]
        if not values or values == [""]:
            continue
        if len(values) != expected_columns:
            raise ValueError("nvidia-smi CSV column count changed")
        parsed.append(values)
    return parsed


def parse_live_gpu_snapshot(
    gpu_csv: str, process_csv: str
) -> list[dict[str, Any]]:
    processes: dict[str, list[dict[str, Any]]] = {}
    for uuid, pid, used_memory in _rows(process_csv, 3):
        processes.setdefault(uuid, []).append(
            {
                "pid": int(pid),
                "used_memory_mib": None
                if used_memory in ("N/A", "[N/A]")
                else int(used_memory),
            }
        )
    values = []
    seen = set()
    for index, uuid, memory, utilization, pstate in _rows(gpu_csv, 5):
        physical_index = int(index)
        if physical_index not in ALLOWED_INDICES or physical_index in seen:
            raise ValueError("GPU snapshot index is outside unique GPU0–7")
        seen.add(physical_index)
        compute = processes.get(uuid, [])
        memory_mib = int(memory)
        utilization_percent = int(utilization)
        checks = {
            "allowed_index": physical_index in ALLOWED_INDICES,
            "near_baseline_memory": memory_mib <= IDLE_MAX_MEMORY_MIB,
            "zero_utilization": utilization_percent
            <= IDLE_MAX_UTILIZATION_PERCENT,
            "no_compute_process": not compute,
            "uuid_present": uuid.startswith("GPU-") and len(uuid) > 8,
            "pstate_recorded": bool(pstate),
        }
        values.append(
            {
                "physical_index": physical_index,
                "gpu_uuid": uuid,
                "memory_used_mib": memory_mib,
                "utilization_percent": utilization_percent,
                "pstate": pstate,
                "compute_processes": compute,
                "checks": checks,
                "independently_fresh_idle": all(checks.values()),
            }
        )
    if seen != set(ALLOWED_INDICES):
        raise ValueError("live snapshot must contain physical GPU0–7 exactly once")
    return sorted(values, key=lambda item: item["physical_index"])


def acquire_live_gpu_snapshot() -> dict[str, Any]:
    gpu_command = [
        "nvidia-smi",
        "--query-gpu=index,uuid,memory.used,utilization.gpu,pstate",
        "--format=csv,noheader,nounits",
    ]
    process_command = [
        "nvidia-smi",
        "--query-compute-apps=gpu_uuid,pid,used_memory",
        "--format=csv,noheader,nounits",
    ]
    gpu = subprocess.run(
        gpu_command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    process = subprocess.run(
        process_command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    parsed = parse_live_gpu_snapshot(gpu.stdout, process.stdout)
    return {
        "schema_version": "cmf_runtime_v3_4_live_gpu_snapshot_v1",
        "gpu_command": gpu_command,
        "process_command": process_command,
        "raw_gpu_csv": gpu.stdout,
        "raw_process_csv": process.stdout,
        "gpus": parsed,
    }


def schedule_ready_scopes(
    ready_scopes: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    scopes = [dict(item) for item in ready_scopes]
    ids = [str(item.get("scope")) for item in scopes]
    if len(ids) != len(set(ids)) or any(name not in SCOPE_ORDER for name in ids):
        raise ValueError("ready scopes must be unique known runtime-v3_4 scopes")
    scopes.sort(key=lambda item: SCOPE_ORDER.index(str(item["scope"])))
    gpus = list(snapshot.get("gpus", []))
    idle = [item for item in gpus if item.get("independently_fresh_idle") is True]
    idle.sort(key=lambda item: int(item["physical_index"]))
    assignments = []
    used_families = set()
    remaining = []
    for scope in scopes:
        family = str(scope.get("family"))
        if family in used_families or not idle:
            remaining.append(scope)
            continue
        gpu = idle.pop(0)
        assignments.append(
            {
                "scope": str(scope["scope"]),
                "family": family,
                "authorization_receipt_sha256": scope.get(
                    "authorization_receipt_sha256"
                ),
                "physical_gpu_index": int(gpu["physical_index"]),
                "gpu_uuid": str(gpu["gpu_uuid"]),
                "one_project_job_on_card": True,
                "root_sharded": False,
            }
        )
        used_families.add(family)
    checks = {
        "one_job_per_gpu": len(
            {item["physical_gpu_index"] for item in assignments}
        )
        == len(assignments),
        "one_ready_scope_per_family_per_wave": len(
            {item["family"] for item in assignments}
        )
        == len(assignments),
        "only_fresh_idle_gpu": all(
            next(
                gpu
                for gpu in gpus
                if int(gpu["physical_index"]) == item["physical_gpu_index"]
            )["independently_fresh_idle"]
            is True
            for item in assignments
        ),
        "no_root_sharding": all(item["root_sharded"] is False for item in assignments),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": "controlled_multi_future_runtime_v3_4",
        "scheduler_policy": "family_level_parallel_one_job_per_independently_idle_gpu",
        "maximum_concurrency": min(len(scopes), len([g for g in gpus if g.get("independently_fresh_idle") is True])),
        "snapshot": json.loads(json.dumps(snapshot, sort_keys=True)),
        "assignments": assignments,
        "deferred_ready_scopes": remaining,
        "checks": checks,
        "pass": all(checks.values()),
    }


__all__ = [
    "acquire_live_gpu_snapshot",
    "parse_live_gpu_snapshot",
    "schedule_ready_scopes",
]
