"""Fresh physical GPU snapshot, UUID guard, and CPU-only wave assignment."""

from __future__ import annotations

import csv
import io
import os
import subprocess
from typing import Any, Mapping, Sequence


ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
MAX_MEMORY_MIB = 128
MAX_UTILIZATION_PERCENT = 1


class GPUUnavailable(RuntimeError):
    """The host did not expose a usable fresh GPU snapshot."""


class GPUGuardError(ValueError):
    """A launch would violate physical ownership or freshness rules."""


def _rows(raw: str, width: int) -> list[list[str]]:
    result = []
    for row in csv.reader(io.StringIO(raw.strip())):
        values = [item.strip() for item in row]
        if values and values != [""]:
            if len(values) != width:
                raise GPUGuardError(f"expected {width} nvidia-smi columns")
            result.append(values)
    return result


def parse_snapshot(gpu_csv: str, process_csv: str) -> list[dict[str, Any]]:
    processes: dict[str, list[dict[str, Any]]] = {}
    for uuid, pid, used in _rows(process_csv, 3):
        processes.setdefault(uuid, []).append({"pid": int(pid), "used_memory_mib": used})
    cards = []
    seen_indices: set[int] = set()
    seen_uuids: set[str] = set()
    for index, uuid, memory, utilization, pstate in _rows(gpu_csv, 5):
        physical_index = int(index)
        if physical_index not in ALLOWED_PHYSICAL_GPU_INDICES or physical_index in seen_indices:
            raise GPUGuardError("GPU snapshot must contain unique physical indices 0--7")
        if not uuid.startswith("GPU-") or uuid in seen_uuids:
            raise GPUGuardError("GPU UUID is missing or duplicated")
        compute = processes.get(uuid, [])
        memory_mib = int(memory)
        util = int(utilization)
        checks = {
            "allowed_physical_index": True,
            "near_baseline_memory": 0 <= memory_mib <= MAX_MEMORY_MIB,
            "near_baseline_utilization": 0 <= util <= MAX_UTILIZATION_PERCENT,
            "pstate_recorded": bool(pstate),
            "no_compute_process": not compute,
        }
        cards.append({
            "physical_index": physical_index,
            "gpu_uuid": uuid,
            "memory_used_mib": memory_mib,
            "utilization_percent": util,
            "pstate": pstate,
            "compute_processes": compute,
            "checks": checks,
            "independently_fresh_idle": all(checks.values()),
        })
        seen_indices.add(physical_index)
        seen_uuids.add(uuid)
    if seen_indices != set(ALLOWED_PHYSICAL_GPU_INDICES):
        raise GPUGuardError("fresh snapshot must include physical GPU0--7 exactly once")
    return sorted(cards, key=lambda item: item["physical_index"])


def live_snapshot() -> dict[str, Any]:
    gpu_cmd = ["nvidia-smi", "--query-gpu=index,uuid,memory.used,utilization.gpu,pstate", "--format=csv,noheader,nounits"]
    proc_cmd = ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,used_memory", "--format=csv,noheader,nounits"]
    try:
        gpu = subprocess.run(gpu_cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc = subprocess.run(proc_cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise GPUUnavailable(f"nvidia-smi snapshot unavailable: {detail.strip()}") from exc
    return {
        "schema_version": "cmf_f2_f3_live_gpu_snapshot_v1",
        "gpu_command": gpu_cmd,
        "process_command": proc_cmd,
        "raw_gpu_csv": gpu.stdout,
        "raw_process_csv": proc.stdout,
        "gpus": parse_snapshot(gpu.stdout, proc.stdout),
    }


def guard_card(snapshot: Mapping[str, Any], physical_index: int, expected_uuid: str | None = None) -> dict[str, Any]:
    cards = {int(item["physical_index"]): item for item in snapshot.get("gpus", [])}
    if physical_index not in cards:
        raise GPUGuardError("selected physical GPU is absent from fresh snapshot")
    card = cards[physical_index]
    if expected_uuid is not None and card.get("gpu_uuid") != expected_uuid:
        raise GPUGuardError("GPU UUID changed between scheduling and launch")
    if not card.get("independently_fresh_idle"):
        raise GPUGuardError("selected GPU is not independently fresh and idle")
    return dict(card)


def assign_ready_jobs(ready_jobs: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    idle = [item for item in snapshot.get("gpus", []) if item.get("independently_fresh_idle")]
    idle.sort(key=lambda item: int(item["physical_index"]))
    assignments = []
    seen_roots: set[str] = set()
    seen_cards: set[int] = set()
    deferred = []
    for job in ready_jobs:
        root = str(job.get("root_id", ""))
        if not root or root in seen_roots or not idle:
            deferred.append(dict(job))
            continue
        card = idle.pop(0)
        index = int(card["physical_index"])
        if index in seen_cards:
            raise GPUGuardError("same GPU assigned twice in one wave")
        assignments.append({
            "job_id": str(job["job_id"]),
            "root_id": root,
            "physical_gpu_index": index,
            "gpu_uuid": card["gpu_uuid"],
            "allowed_physical_gpu_indices": list(ALLOWED_PHYSICAL_GPU_INDICES),
            "one_root_one_gpu": True,
        })
        seen_roots.add(root)
        seen_cards.add(index)
    return {"assignments": assignments, "deferred": deferred, "pass": True}


def child_environment(gpu_uuid: str) -> dict[str, str]:
    if not gpu_uuid.startswith("GPU-"):
        raise GPUGuardError("child must bind a concrete GPU UUID")
    environment = dict(os.environ)
    environment.pop("LD_LIBRARY_PATH", None)
    environment["CUDA_VISIBLE_DEVICES"] = gpu_uuid
    environment["CUDA_HOME"] = "/nfs_share/lijunhui/Robotwin2/tools/cuda-12.1"
    environment["CMF_BOUND_GPU_UUID"] = gpu_uuid
    return environment
