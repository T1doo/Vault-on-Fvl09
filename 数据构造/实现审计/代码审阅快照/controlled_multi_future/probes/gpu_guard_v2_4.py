"""Atomic single-card guard through controlled Stage 0 smoke v1."""

from __future__ import annotations

import argparse
import atexit
import ctypes
import functools
import hashlib
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time
from typing import Any, Mapping, Sequence

from ..canonical_artifact import canonical_hash_json, canonical_write_json
from ..runtime_source_lock_v1 import SourceLockError, load_runtime_source_lock
from .gpu_guard import (
    build_child_environment,
    classify_terminal_status,
    is_idle,
    pids_in_process_group,
    snapshot,
    verify_post_release,
)
from .gpu_guard_v2_1 import command_sha256, update_child_receipt_v2_1
from .runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationError,
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
    consume_authorization_once,
    load_authorization_v3_3,
    validate_consumption_receipt,
)
from .runtime_v3_4_authorization_v1 import (
    consume_authorization_once as consume_authorization_once_v3_4,
    load_authorization_v3_4,
    validate_consumption_receipt as validate_consumption_receipt_v3_4,
)
from .runtime_v3_4_1_authorization_v1 import (
    consume_authorization_once as consume_authorization_once_v3_4_1,
    load_authorization_v3_4_1,
    validate_consumption_receipt as validate_consumption_receipt_v3_4_1,
)
from .stage0_smoke_authorization_v1 import (
    consume_authorization_once as consume_stage0_smoke_authorization_once,
    load_stage0_smoke_authorization,
    validate_consumption_receipt as validate_stage0_smoke_consumption_receipt,
)
from .stage0_smoke_authorization_v1_1 import (
    consume_authorization_once_v1_1 as consume_stage0_smoke_authorization_once_v1_1,
    load_stage0_smoke_authorization_v1_1,
    validate_consumption_receipt_v1_1 as validate_stage0_smoke_consumption_receipt_v1_1,
)
from .stage0_f2_replacement_authorization_v1_2 import (
    consume_stage0_f2_replacement_authorization_once_v1_2,
    load_stage0_f2_replacement_authorization_v1_2,
    validate_stage0_f2_replacement_consumption_v1_2,
)
from .post_stage0_f3_authorization_v1 import (
    consume_post_stage0_f3_authorization_once_v1,
    load_post_stage0_f3_authorization_v1,
    validate_post_stage0_f3_consumption_v1,
)
from .post_stage0_f4_authorization_v1 import (
    consume_post_stage0_f4_authorization_once_v1,
    load_post_stage0_f4_authorization_v1,
    validate_post_stage0_f4_consumption_v1,
)
from .closure_f3_authorization_v2 import (
    consume as consume_closure_f3_v2,
    load as load_closure_f3_v2,
    validate_consumption as validate_closure_f3_consumption_v2,
)
from .closure_f3_authorization_v2_1 import (
    consume as consume_closure_f3_v2_1,
    load as load_closure_f3_v2_1,
    validate_consumption as validate_closure_f3_consumption_v2_1,
)
from .closure_f4_authorization_v2 import (
    consume as consume_closure_f4_v2,
    load as load_closure_f4_v2,
    validate_consumption as validate_closure_f4_consumption_v2,
)
from .f1_batch_pilot_authorization_v1 import (
    consume as consume_f1_batch_pilot_v1,
    load as load_f1_batch_pilot_v1,
    validate_consumption as validate_f1_batch_pilot_consumption_v1,
)
from .f2_dynamic_development_authorization_v3 import (
    consume as consume_f2_dynamic_development_v3,
    load as load_f2_dynamic_development_v3,
    validate_consumption as validate_f2_dynamic_development_consumption_v3,
)
from .f4_selected_layout_authorization_v2 import (
    consume as consume_f4_selected_layout_v2,
    load as load_f4_selected_layout_v2,
    validate_consumption as validate_f4_selected_layout_consumption_v2,
)
from .development_consolidation_authorization_v1 import (
    IMPLEMENTATION_VERSION as DEVELOPMENT_CONSOLIDATION_IMPLEMENTATION_VERSION,
    consume as consume_development_consolidation_v1,
    load as load_development_consolidation_v1,
    validate_consumption as validate_development_consolidation_consumption_v1,
)
from .high_level_authorization_v1 import (
    IMPLEMENTATION_VERSION as HIGH_LEVEL_IMPLEMENTATION_VERSION,
    consume as consume_high_level_v1,
    load as load_high_level_v1,
    validate_consumption as validate_high_level_consumption_v1,
)
from .planner_qualification_authorization_v2_3 import (
    IMPLEMENTATION_VERSION as PLANNER_QUALIFICATION_V2_3_IMPLEMENTATION_VERSION,
    consume as consume_planner_qualification_v2_3,
    load as load_planner_qualification_v2_3,
    validate_consumption as validate_planner_qualification_consumption_v2_3,
)
from .planner_qualification_authorization_v2_3_1 import (
    IMPLEMENTATION_VERSION as PLANNER_QUALIFICATION_V2_3_1_IMPLEMENTATION_VERSION,
    consume as consume_planner_qualification_v2_3_1,
    load as load_planner_qualification_v2_3_1,
    validate_consumption as validate_planner_qualification_consumption_v2_3_1,
)
from .planner_qualification_authorization_v2_3_1a import (
    IMPLEMENTATION_VERSION as PLANNER_QUALIFICATION_V2_3_1A_IMPLEMENTATION_VERSION,
    consume as consume_planner_qualification_v2_3_1a,
    load as load_planner_qualification_v2_3_1a,
    validate_consumption as validate_planner_qualification_consumption_v2_3_1a,
)


GUARD_SCHEMA_VERSION = "cmf_gpu_guard_v2_4_1"
GPU_LEASE_SCHEMA_VERSION = "cmf_physical_gpu_lease_v1"
PRECHECK_MAX_AGE_SECONDS = 60.0
ALLOWED_PHYSICAL_GPU_INDICES = tuple(range(8))
JOB_CACHE_ENVIRONMENT_SUBDIRECTORIES = {
    "CONDA_PKGS_DIRS": "conda_pkgs",
    "CUDA_CACHE_PATH": "cuda",
    "HF_HOME": "huggingface",
    "HUGGINGFACE_HUB_CACHE": "huggingface_hub",
    "HOME": "home",
    "MPLCONFIGDIR": "matplotlib",
    "NUMBA_CACHE_DIR": "numba",
    "PIP_CACHE_DIR": "pip",
    "TMPDIR": "tmp",
    "TORCH_EXTENSIONS_DIR": "torch_extensions",
    "TORCH_HOME": "torch",
    "TRITON_CACHE_DIR": "triton",
    "XDG_CACHE_HOME": "xdg",
}


def planner_wiring_smoke_guard_purpose_v1(
    authorization: Mapping[str, Any],
) -> str | None:
    if (
        authorization.get("implementation_version")
        == PLANNER_QUALIFICATION_V2_3_1A_IMPLEMENTATION_VERSION
    ):
        return "planner_wiring_smoke_v1"
    return None


def _write_guard_receipt(path: Path, value: dict[str, Any]) -> None:
    value.pop("guard_receipt_sha256", None)
    value["guard_receipt_sha256"] = canonical_hash_json(value)
    canonical_write_json(path, value, mode=0o600)


def _authorization_implementation(path: Path) -> str:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("authorization receipt is unreadable") from exc
    return str(value.get("implementation_version"))


def _load_runtime_authorization(path: Path, *, requested_scope: str, **kwargs):
    implementation = _authorization_implementation(path)
    if implementation == PLANNER_QUALIFICATION_V2_3_1A_IMPLEMENTATION_VERSION:
        return load_planner_qualification_v2_3_1a(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == PLANNER_QUALIFICATION_V2_3_1_IMPLEMENTATION_VERSION:
        return load_planner_qualification_v2_3_1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == PLANNER_QUALIFICATION_V2_3_IMPLEMENTATION_VERSION:
        return load_planner_qualification_v2_3(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == HIGH_LEVEL_IMPLEMENTATION_VERSION:
        return load_high_level_v1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == DEVELOPMENT_CONSOLIDATION_IMPLEMENTATION_VERSION:
        return load_development_consolidation_v1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_f1_batch_pilot_v1":
        return load_f1_batch_pilot_v1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_f2_asset_redesign_dynamic_v3":
        return load_f2_dynamic_development_v3(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_post_stage0_f4_selected_layout_v2":
        return load_f4_selected_layout_v2(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_post_stage0_closure_f4_v2":
        return load_closure_f4_v2(path, requested_scope=requested_scope, **kwargs)
    if implementation == "controlled_multi_future_post_stage0_closure_f3_v2":
        return load_closure_f3_v2(path, requested_scope=requested_scope, **kwargs)
    if implementation == "controlled_multi_future_post_stage0_closure_f3_v2_1":
        return load_closure_f3_v2_1(path, requested_scope=requested_scope, **kwargs)
    if implementation == "controlled_multi_future_post_stage0_f4_v1":
        return load_post_stage0_f4_authorization_v1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_post_stage0_f3_v1":
        return load_post_stage0_f3_authorization_v1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_stage0_smoke_v1_2":
        return load_stage0_f2_replacement_authorization_v1_2(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_stage0_smoke_v1_1":
        return load_stage0_smoke_authorization_v1_1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_stage0_smoke_v1":
        return load_stage0_smoke_authorization(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_runtime_v3_4_1":
        return load_authorization_v3_4_1(
            path, requested_scope=requested_scope, **kwargs
        )
    if implementation == "controlled_multi_future_runtime_v3_4":
        return load_authorization_v3_4(
            path, requested_scope=requested_scope, **kwargs
        )
    return load_authorization_v3_3(
        path, requested_scope=requested_scope, **kwargs
    )


def _consume_runtime_authorization(authorization, *, ledger_directory):
    if authorization.get("implementation_version") == PLANNER_QUALIFICATION_V2_3_1A_IMPLEMENTATION_VERSION:
        return consume_planner_qualification_v2_3_1a(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == PLANNER_QUALIFICATION_V2_3_1_IMPLEMENTATION_VERSION:
        return consume_planner_qualification_v2_3_1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == PLANNER_QUALIFICATION_V2_3_IMPLEMENTATION_VERSION:
        return consume_planner_qualification_v2_3(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == HIGH_LEVEL_IMPLEMENTATION_VERSION:
        return consume_high_level_v1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == DEVELOPMENT_CONSOLIDATION_IMPLEMENTATION_VERSION:
        return consume_development_consolidation_v1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_f1_batch_pilot_v1":
        return consume_f1_batch_pilot_v1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_f2_asset_redesign_dynamic_v3":
        return consume_f2_dynamic_development_v3(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_f4_selected_layout_v2":
        return consume_f4_selected_layout_v2(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_closure_f4_v2":
        return consume_closure_f4_v2(authorization, ledger_directory=ledger_directory)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_closure_f3_v2":
        return consume_closure_f3_v2(authorization, ledger_directory=ledger_directory)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_closure_f3_v2_1":
        return consume_closure_f3_v2_1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_f4_v1":
        return consume_post_stage0_f4_authorization_once_v1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_f3_v1":
        return consume_post_stage0_f3_authorization_once_v1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_stage0_smoke_v1_2":
        return consume_stage0_f2_replacement_authorization_once_v1_2(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_stage0_smoke_v1_1":
        return consume_stage0_smoke_authorization_once_v1_1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_stage0_smoke_v1":
        return consume_stage0_smoke_authorization_once(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_runtime_v3_4_1":
        return consume_authorization_once_v3_4_1(
            authorization, ledger_directory=ledger_directory
        )
    if authorization.get("implementation_version") == "controlled_multi_future_runtime_v3_4":
        return consume_authorization_once_v3_4(
            authorization, ledger_directory=ledger_directory
        )
    return consume_authorization_once(
        authorization, ledger_directory=ledger_directory
    )


def _validate_runtime_consumption(consumption, authorization):
    if authorization.get("implementation_version") == PLANNER_QUALIFICATION_V2_3_1A_IMPLEMENTATION_VERSION:
        return validate_planner_qualification_consumption_v2_3_1a(
            consumption, authorization
        )
    if authorization.get("implementation_version") == PLANNER_QUALIFICATION_V2_3_1_IMPLEMENTATION_VERSION:
        return validate_planner_qualification_consumption_v2_3_1(
            consumption, authorization
        )
    if authorization.get("implementation_version") == PLANNER_QUALIFICATION_V2_3_IMPLEMENTATION_VERSION:
        return validate_planner_qualification_consumption_v2_3(
            consumption, authorization
        )
    if authorization.get("implementation_version") == HIGH_LEVEL_IMPLEMENTATION_VERSION:
        return validate_high_level_consumption_v1(consumption, authorization)
    if authorization.get("implementation_version") == DEVELOPMENT_CONSOLIDATION_IMPLEMENTATION_VERSION:
        return validate_development_consolidation_consumption_v1(
            consumption, authorization
        )
    if authorization.get("implementation_version") == "controlled_multi_future_f1_batch_pilot_v1":
        return validate_f1_batch_pilot_consumption_v1(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_f2_asset_redesign_dynamic_v3":
        return validate_f2_dynamic_development_consumption_v3(
            consumption, authorization
        )
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_f4_selected_layout_v2":
        return validate_f4_selected_layout_consumption_v2(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_closure_f4_v2":
        return validate_closure_f4_consumption_v2(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_closure_f3_v2":
        return validate_closure_f3_consumption_v2(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_closure_f3_v2_1":
        return validate_closure_f3_consumption_v2_1(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_f4_v1":
        return validate_post_stage0_f4_consumption_v1(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_post_stage0_f3_v1":
        return validate_post_stage0_f3_consumption_v1(
            consumption, authorization
        )
    if authorization.get("implementation_version") == "controlled_multi_future_stage0_smoke_v1_2":
        return validate_stage0_f2_replacement_consumption_v1_2(
            consumption, authorization
        )
    if authorization.get("implementation_version") == "controlled_multi_future_stage0_smoke_v1_1":
        return validate_stage0_smoke_consumption_receipt_v1_1(
            consumption, authorization
        )
    if authorization.get("implementation_version") == "controlled_multi_future_stage0_smoke_v1":
        return validate_stage0_smoke_consumption_receipt(
            consumption, authorization
        )
    if authorization.get("implementation_version") == "controlled_multi_future_runtime_v3_4_1":
        return validate_consumption_receipt_v3_4_1(consumption, authorization)
    if authorization.get("implementation_version") == "controlled_multi_future_runtime_v3_4":
        return validate_consumption_receipt_v3_4(consumption, authorization)
    return validate_consumption_receipt(consumption, authorization)


class GuardAuthorizationMismatch(PermissionError):
    failure_status = "failed_guard_authorization_mismatch"


class GuardBudgetMismatch(PermissionError):
    failure_status = "failed_guard_budget_mismatch"


class GuardLaunchPrecheckNotIdle(PermissionError):
    failure_status = "blocked_launch_precheck_not_idle"


class GuardGpuLeaseUnavailable(PermissionError):
    failure_status = "blocked_physical_gpu_lease_unavailable"


class GuardSignalInterrupt(RuntimeError):
    failure_status = "aborted_with_reason"

    def __init__(self, signum: int):
        super().__init__(f"Guard interrupted by signal {signum}")
        self.signum = int(signum)


def build_task_owned_cleanup_audit_v1(
    *,
    child_exited: bool,
    orphan_pids: Sequence[int],
    owned_process_cleanup_errors: Sequence[Mapping[str, Any]],
    job_cache_cleanup: Mapping[str, Any],
    lease_release: Mapping[str, Any],
    post_error: Mapping[str, Any] | None,
    post_release: Mapping[str, Any],
) -> dict[str, Any]:
    external = list(post_release.get("new_compute_processes", []))
    external_detected = bool(external)
    task_owned_pass = bool(
        child_exited
        and not orphan_pids
        and not owned_process_cleanup_errors
        and job_cache_cleanup.get("succeeded") is True
        and lease_release.get("released") is True
    )
    idle_baseline = post_release.get("verified") is True
    uncertain = bool(
        not task_owned_pass
        or post_error is not None
        or (not idle_baseline and not external_detected)
    )
    return {
        "task_owned_cleanup_pass": task_owned_pass,
        "task_owned_orphan_count": len(orphan_pids),
        "gpu_returned_to_idle_baseline": idle_baseline,
        "external_process_detected_after_release": external_detected,
        "external_processes_after_release": external,
        "external_process_not_modified": True,
        "cleanup_uncertain": uncertain,
    }


def _require_workspace_path(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or not str(path).startswith("/nfs_share/lijunhui/"):
        raise GuardAuthorizationMismatch(f"{label} must be an absolute workspace path")
    return path


def _file_evidence(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"path": str(path.resolve()), "exists": False, "bytes": 0, "sha256": None}
    data = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def acquire_physical_gpu_lease(
    physical_index: int, *, lease_directory: Path | None = None
) -> dict:
    if physical_index not in ALLOWED_PHYSICAL_GPU_INDICES:
        raise GuardGpuLeaseUnavailable("physical GPU index is outside lease policy")
    directory = _require_workspace_path(
        Path(lease_directory or CANONICAL_GPU_LEASE_DIRECTORY),
        "GPU lease directory",
    )
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"physical_gpu_{physical_index}.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(fd, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise GuardGpuLeaseUnavailable(
            f"physical GPU{physical_index} already has an active CMF lease"
        ) from exc
    return {
        "schema_version": GPU_LEASE_SCHEMA_VERSION,
        "lease_path": str(path.resolve()),
        "physical_gpu_index": int(physical_index),
        "owner_guard_pid": int(os.getpid()),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "acquired": True,
        "_fd": fd,
    }


def release_physical_gpu_lease(lease: Mapping[str, Any]) -> dict:
    fd = lease.get("_fd") if isinstance(lease, Mapping) else None
    result = {
        "schema_version": GPU_LEASE_SCHEMA_VERSION,
        "lease_path": lease.get("lease_path") if isinstance(lease, Mapping) else None,
        "physical_gpu_index": (
            lease.get("physical_gpu_index") if isinstance(lease, Mapping) else None
        ),
        "released_at": datetime.now(timezone.utc).isoformat(),
        "released": False,
        "error": None,
    }
    try:
        if not isinstance(fd, int):
            raise RuntimeError("GPU lease file descriptor is missing")
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        result["released"] = True
    except BaseException as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return result


def prepare_isolated_job_cache(authorization: Mapping[str, Any]) -> tuple[Path, dict]:
    root = _require_workspace_path(
        Path(authorization["job_cache_root_directory"]), "job cache root"
    )
    if str(root) != CANONICAL_JOB_CACHE_DIRECTORY:
        raise GuardAuthorizationMismatch("job cache root is not canonical")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / authorization["authorization_id"]
    if path.exists():
        raise GuardAuthorizationMismatch("job cache path must be new and immutable per authorization")
    path.mkdir(mode=0o700)
    subdirectories = {}
    for name in sorted(set(JOB_CACHE_ENVIRONMENT_SUBDIRECTORIES.values())):
        child = path / name
        child.mkdir(mode=0o700)
        subdirectories[name] = str(child.resolve())
    return path, {
        "root": str(path.resolve()),
        "subdirectories": subdirectories,
        "isolated": True,
    }


def cleanup_isolated_job_cache(path: Path | None) -> dict:
    result = {
        "path": str(path.resolve()) if isinstance(path, Path) else None,
        "attempted": isinstance(path, Path),
        "succeeded": False,
        "error": None,
    }
    if not isinstance(path, Path):
        return result
    try:
        shutil.rmtree(path)
        result["succeeded"] = not path.exists()
    except BaseException as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return result


def build_isolated_child_environment(
    base_environment: Mapping[str, str],
    expected_uuid: str,
    job_cache_receipt: Mapping[str, Any],
) -> dict:
    environment = build_child_environment(base_environment, expected_uuid)
    subdirectories = job_cache_receipt.get("subdirectories")
    if not isinstance(subdirectories, Mapping):
        raise GuardAuthorizationMismatch("job cache receipt lacks subdirectories")
    for environment_key, receipt_key in JOB_CACHE_ENVIRONMENT_SUBDIRECTORIES.items():
        value = subdirectories.get(receipt_key)
        if not isinstance(value, str) or not value.startswith(
            str(job_cache_receipt.get("root")) + "/"
        ):
            raise GuardAuthorizationMismatch(
                f"job cache receipt is invalid for {environment_key}"
            )
        environment[environment_key] = value
    return environment


def claim_guard_receipt(path: Path, payload: Mapping[str, Any]) -> None:
    path = _require_workspace_path(Path(path), "guard receipt")
    canonical_write_json(path, payload, exclusive=True, mode=0o600)


def _set_parent_death_signal(
    expected_parent_pid: int, inherited_signal_mask
) -> None:
    """Linux child-side last resort when the Guard dies without cleanup."""

    signal.pthread_sigmask(signal.SIG_SETMASK, inherited_signal_mask)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, int(signal.SIGKILL), 0, 0, 0) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    if os.getppid() != int(expected_parent_pid):
        os.kill(os.getpid(), signal.SIGKILL)


def build_guard_binding(
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    physical_index: int,
    expected_uuid: str,
    timeout_seconds: int,
    output_namespace: str,
    command: Sequence[str],
    guard_pid: int,
) -> dict:
    if timeout_seconds != authorization["timeout_seconds"]:
        raise GuardBudgetMismatch("guard timeout differs from authorization budget")
    if output_namespace != authorization["output_namespace"]:
        raise GuardAuthorizationMismatch("guard output namespace differs from authorization")
    if physical_index not in authorization["allowed_physical_gpu_indices"]:
        raise GuardAuthorizationMismatch("guard physical GPU index is outside authorization")
    if not isinstance(expected_uuid, str) or not expected_uuid.startswith("GPU-"):
        raise GuardAuthorizationMismatch("guard requires an explicit GPU UUID")
    _validate_runtime_consumption(consumption, authorization)
    actual_command_sha256 = command_sha256(command)
    if actual_command_sha256 != authorization["authorized_command_sha256"]:
        raise GuardAuthorizationMismatch("guard child command differs from authorization")
    job_cache_directory = (
        Path(authorization["job_cache_root_directory"])
        / authorization["authorization_id"]
    ).resolve()
    job_cache_environment = {
        key: str((job_cache_directory / subdirectory).resolve())
        for key, subdirectory in JOB_CACHE_ENVIRONMENT_SUBDIRECTORIES.items()
    }
    return {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "wave_id": authorization.get("wave_id"),
        "slot": authorization.get("slot"),
        "planner_reset_nonce": authorization.get("planner_reset_nonce"),
        "guard_purpose": authorization.get("guard_purpose"),
        "approved_scope": authorization["approved_scopes"][0],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "planned_root_slot_spec_sha256": authorization["planned_root_slot_spec_sha256"],
        "parent_user_authorization_sha256": authorization["parent_user_authorization_sha256"],
        "approval_request_sha256": authorization["approval_request_sha256"],
        "source_lock_receipt_sha256": authorization["source_lock_receipt_sha256"],
        "implementation_source_sha256": authorization["implementation_source_sha256"],
        "budget_receipt_sha256": authorization["budget_receipt_sha256"],
        "planner_query_limit": authorization["planner_query_limit"],
        "controlled_action_limit": authorization["controlled_action_limit"],
        "physics_step_limit": authorization["physics_step_limit"],
        "timeout_seconds": timeout_seconds,
        "output_namespace": output_namespace,
        "guard_receipt_path": authorization["guard_receipt_path"],
        "consumption_ledger_directory": authorization[
            "consumption_ledger_directory"
        ],
        "gpu_lease_directory": authorization["gpu_lease_directory"],
        "job_cache_root_directory": authorization["job_cache_root_directory"],
        "job_cache_directory": str(job_cache_directory),
        "job_cache_environment": job_cache_environment,
        "family_revision_index": authorization.get("family_revision_index"),
        "physical_gpu_index": physical_index,
        "expected_gpu_uuid": expected_uuid,
        "command_sha256": actual_command_sha256,
        "consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_pid": int(guard_pid),
    }


def validate_guard_binding(
    guard: Mapping[str, Any],
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    physical_index: int,
    expected_uuid: str,
    child_parent_pid: int,
    now: datetime | None = None,
) -> dict:
    if guard.get("schema_version") != GUARD_SCHEMA_VERSION:
        raise GuardAuthorizationMismatch("guard schema mismatch")
    if guard.get("status") not in ("precheck_passed", "running"):
        raise GuardAuthorizationMismatch("guard has no launchable precheck status")
    binding = guard.get("binding")
    if not isinstance(binding, Mapping):
        raise GuardAuthorizationMismatch("guard binding is missing")
    expected_job_cache_directory = (
        Path(authorization["job_cache_root_directory"])
        / authorization["authorization_id"]
    ).resolve()
    expected = {
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorized_run_id": authorization["authorized_run_id"],
        "wave_id": authorization.get("wave_id"),
        "slot": authorization.get("slot"),
        "planner_reset_nonce": authorization.get("planner_reset_nonce"),
        "guard_purpose": authorization.get("guard_purpose"),
        "approved_scope": authorization["approved_scopes"][0],
        "family": authorization["family"],
        "scene_seed": authorization["scene_seed"],
        "planned_root_slot_spec_sha256": authorization["planned_root_slot_spec_sha256"],
        "parent_user_authorization_sha256": authorization["parent_user_authorization_sha256"],
        "approval_request_sha256": authorization["approval_request_sha256"],
        "source_lock_receipt_sha256": authorization["source_lock_receipt_sha256"],
        "implementation_source_sha256": authorization["implementation_source_sha256"],
        "budget_receipt_sha256": authorization["budget_receipt_sha256"],
        "planner_query_limit": authorization["planner_query_limit"],
        "controlled_action_limit": authorization["controlled_action_limit"],
        "physics_step_limit": authorization["physics_step_limit"],
        "timeout_seconds": authorization["timeout_seconds"],
        "output_namespace": authorization["output_namespace"],
        "guard_receipt_path": authorization["guard_receipt_path"],
        "consumption_ledger_directory": authorization[
            "consumption_ledger_directory"
        ],
        "gpu_lease_directory": authorization["gpu_lease_directory"],
        "job_cache_root_directory": authorization["job_cache_root_directory"],
        "job_cache_directory": str(expected_job_cache_directory),
        "job_cache_environment": {
            key: str((expected_job_cache_directory / subdirectory).resolve())
            for key, subdirectory in JOB_CACHE_ENVIRONMENT_SUBDIRECTORIES.items()
        },
        "family_revision_index": authorization.get("family_revision_index"),
        "physical_gpu_index": physical_index,
        "expected_gpu_uuid": expected_uuid,
        "consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
        "guard_pid": child_parent_pid,
        "command_sha256": authorization["authorized_command_sha256"],
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            error = GuardBudgetMismatch if key.endswith("limit") or key == "timeout_seconds" else GuardAuthorizationMismatch
            raise error(f"guard binding mismatch: {key}")
    precheck = guard.get("precheck")
    if not isinstance(precheck, Mapping):
        raise GuardAuthorizationMismatch("guard precheck is missing")
    try:
        captured = datetime.fromisoformat(precheck["captured_at"])
        if captured.tzinfo is None:
            raise ValueError
        age = ((now or datetime.now(timezone.utc)).astimezone(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds()
    except (KeyError, TypeError, ValueError) as exc:
        raise GuardAuthorizationMismatch("guard precheck timestamp is invalid") from exc
    if not 0.0 <= age <= PRECHECK_MAX_AGE_SECONDS:
        raise GuardAuthorizationMismatch("guard precheck is stale")
    if (
        precheck.get("uuid") != expected_uuid
        or precheck.get("physical_index") != physical_index
        or int(precheck.get("memory_used_mib", 10**9)) > 100
        or int(precheck.get("utilization_percent", 100)) > 1
        or precheck.get("pstate") != "P8"
        or precheck.get("compute_processes")
    ):
        raise GuardAuthorizationMismatch("guard precheck does not prove a matching fresh-idle GPU")
    _validate_runtime_consumption(consumption, authorization)
    return {"binding": dict(binding), "precheck": dict(precheck), "precheck_age_seconds": age}


def require_atomic_gpu_guard_v2_4(
    authorization: Mapping[str, Any],
    consumption: Mapping[str, Any],
    *,
    expected_uuid: str,
    physical_index: int,
) -> dict:
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    auth_path = os.environ.get("CMF_RUNTIME_AUTHORIZATION_RECEIPT")
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    index_value = os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX")
    lease_path = os.environ.get("CMF_GPU_LEASE_PATH")
    job_cache_path = os.environ.get("CMF_JOB_CACHE_DIRECTORY")
    if not guard_path or not auth_path or not consumption_path or index_value != str(physical_index):
        raise GuardAuthorizationMismatch("child was not launched by bound GPU guard v2_4")
    try:
        environment_authorization = json.loads(Path(auth_path).read_text(encoding="utf-8"))
        guard = json.loads(Path(guard_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardAuthorizationMismatch("bound guard/authorization file is unreadable") from exc
    if environment_authorization.get("receipt_sha256") != authorization.get("receipt_sha256"):
        raise GuardAuthorizationMismatch("bound authorization file differs from validated authorization")
    if str(Path(guard_path).resolve()) != str(
        Path(authorization["guard_receipt_path"]).resolve()
    ):
        raise GuardAuthorizationMismatch("bound guard path differs from authorization")
    if Path(consumption_path).resolve() != Path(consumption.get("path", consumption_path)).resolve():
        raise GuardAuthorizationMismatch("consumption environment path is inconsistent")
    expected_lease = (
        Path(authorization["gpu_lease_directory"])
        / f"physical_gpu_{physical_index}.lock"
    ).resolve()
    if not lease_path or Path(lease_path).resolve() != expected_lease:
        raise GuardAuthorizationMismatch("child GPU lease path is inconsistent")
    expected_cache = (
        Path(authorization["job_cache_root_directory"])
        / authorization["authorization_id"]
    ).resolve()
    if not job_cache_path or Path(job_cache_path).resolve() != expected_cache:
        raise GuardAuthorizationMismatch("child job cache path is inconsistent")
    lease_fd = os.open(expected_lease, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            fcntl.flock(lease_fd, fcntl.LOCK_UN)
            raise GuardAuthorizationMismatch(
                "parent Guard no longer holds the physical GPU lease"
            )
    finally:
        os.close(lease_fd)
    result = validate_guard_binding(
        guard,
        authorization,
        consumption,
        physical_index=physical_index,
        expected_uuid=expected_uuid,
        child_parent_pid=os.getppid(),
    )
    expected_cache_environment = result["binding"].get("job_cache_environment")
    if not isinstance(expected_cache_environment, Mapping):
        raise GuardAuthorizationMismatch("guard binding lacks job cache environment")
    for key, expected_value in expected_cache_environment.items():
        if os.environ.get(key) != expected_value:
            raise GuardAuthorizationMismatch(
                f"child mutable cache environment differs from guard binding: {key}"
            )
    return {"path": guard_path, **result}


def _peek_scope(path: Path) -> str:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        scopes = value.get("approved_scopes")
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationBindingError("cannot read authorization before guard launch") from exc
    if not isinstance(scopes, list) or len(scopes) != 1:
        raise AuthorizationBindingError("authorization must contain one approved scope")
    return scopes[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    parser.add_argument("--consumption-ledger-dir", type=Path, required=True)
    parser.add_argument("--physical-index", type=int, choices=ALLOWED_PHYSICAL_GPU_INDICES, required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--guard-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a child command is required after --")
    for path, label in (
        (args.authorization_receipt, "authorization receipt"),
        (args.consumption_ledger_dir, "consumption ledger"),
        (args.guard_receipt, "guard receipt"),
        (args.output_dir, "output namespace"),
    ):
        _require_workspace_path(path, label)
    if args.output_dir.exists():
        raise FileExistsError("output namespace must be new and immutable")
    started = time.time()
    raw_authorization = json.loads(
        args.authorization_receipt.read_text(encoding="utf-8")
    )
    stage0_mode = raw_authorization.get("implementation_version") in (
        "controlled_multi_future_stage0_smoke_v1",
        "controlled_multi_future_stage0_smoke_v1_1",
        "controlled_multi_future_stage0_smoke_v1_2",
    )
    post_stage0_f3_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_post_stage0_f3_v1"
    post_stage0_f4_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_post_stage0_f4_v1"
    closure_f3_v2_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_post_stage0_closure_f3_v2"
    closure_f3_v2_1_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_post_stage0_closure_f3_v2_1"
    closure_f4_v2_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_post_stage0_closure_f4_v2"
    f1_batch_pilot_v1_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_f1_batch_pilot_v1"
    f2_dynamic_development_v3_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_f2_asset_redesign_dynamic_v3"
    f4_selected_layout_v2_mode = raw_authorization.get(
        "implementation_version"
    ) == "controlled_multi_future_post_stage0_f4_selected_layout_v2"
    development_consolidation_v1_mode = raw_authorization.get(
        "implementation_version"
    ) == DEVELOPMENT_CONSOLIDATION_IMPLEMENTATION_VERSION
    high_level_v1_mode = raw_authorization.get(
        "implementation_version"
    ) == HIGH_LEVEL_IMPLEMENTATION_VERSION
    planner_wiring_smoke_v1_mode = raw_authorization.get(
        "implementation_version"
    ) == PLANNER_QUALIFICATION_V2_3_1A_IMPLEMENTATION_VERSION
    planner_wiring_purpose = planner_wiring_smoke_guard_purpose_v1(
        raw_authorization
    )
    guard = {
        "schema_version": GUARD_SCHEMA_VERSION,
        "purpose": (
            planner_wiring_purpose
            if planner_wiring_purpose is not None
            else "controlled_stage0_smoke"
            if stage0_mode and raw_authorization.get("stage0_data") is True
            else "pre_stage0_infrastructure_validation"
            if stage0_mode
            else "post_stage0_nonformal_f3_diagnostic"
            if post_stage0_f3_mode
            else "post_stage0_nonformal_f4_planner_only"
            if post_stage0_f4_mode
            else "post_stage0_closure_f3_v2"
            if closure_f3_v2_mode
            else "post_stage0_closure_f3_v2_1"
            if closure_f3_v2_1_mode
            else "post_stage0_closure_f4_v2"
            if closure_f4_v2_mode
            else "post_stage0_f1_batch_pilot_v1"
            if f1_batch_pilot_v1_mode
            else "post_stage0_f2_asset_redesign_dynamic_v3"
            if f2_dynamic_development_v3_mode
            else "post_stage0_f4_selected_layout_v2"
            if f4_selected_layout_v2_mode
            else "development_pipeline_consolidation_v1"
            if development_consolidation_v1_mode
            else "high_level_template_redesign_v1"
            if high_level_v1_mode
            else "pre_stage0_nonformal_validation"
        ),
        "formal_data": False,
        "stage0_data": stage0_mode
        and raw_authorization.get("stage0_data") is True,
        "stage0_authorized": stage0_mode,
        "status": "starting",
    }
    claim_guard_receipt(args.guard_receipt, guard)
    try:
        if str(args.consumption_ledger_dir) != CANONICAL_CONSUMPTION_LEDGER_DIRECTORY:
            raise GuardAuthorizationMismatch("guard consumption ledger is not canonical")
        scope = _peek_scope(args.authorization_receipt)
        authorization = _load_runtime_authorization(
            args.authorization_receipt,
            requested_scope=scope,
            expected_output_namespace=str(args.output_dir),
        )
        if args.timeout_seconds != authorization["timeout_seconds"]:
            raise GuardBudgetMismatch("guard timeout does not match authorization")
        if args.physical_index not in authorization["allowed_physical_gpu_indices"]:
            raise GuardAuthorizationMismatch("physical index is not authorized")
        if str(args.consumption_ledger_dir) != authorization["consumption_ledger_directory"]:
            raise GuardAuthorizationMismatch("guard consumption ledger differs from authorization")
        if str(args.guard_receipt.resolve()) != str(
            Path(authorization["guard_receipt_path"]).resolve()
        ):
            raise GuardAuthorizationMismatch("guard receipt path differs from authorization")
        if command_sha256(command) != authorization["authorized_command_sha256"]:
            raise GuardAuthorizationMismatch("child command differs from authorization")
        stdout_path = args.guard_receipt.with_suffix(".stdout.log")
        stderr_path = args.guard_receipt.with_suffix(".stderr.log")
        if stdout_path.exists() or stderr_path.exists():
            raise GuardAuthorizationMismatch(
                "guard stdout/stderr paths must be new and immutable"
            )
    except (AuthorizationError, GuardAuthorizationMismatch, GuardBudgetMismatch, SourceLockError) as exc:
        guard.update(
            {
                "status": getattr(exc, "failure_status", "failed_runtime_source_lock"),
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_seconds": time.time() - started,
            }
        )
        _write_guard_receipt(args.guard_receipt, guard)
        return 96
    except BaseException as exc:
        guard.update(
            {
                "status": "failed_guard_internal_prevalidation",
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_seconds": time.time() - started,
            }
        )
        _write_guard_receipt(args.guard_receipt, guard)
        return 99

    try:
        lease = acquire_physical_gpu_lease(
            args.physical_index,
            lease_directory=Path(authorization["gpu_lease_directory"]),
        )
    except GuardGpuLeaseUnavailable as exc:
        guard.update(
            {
                "status": exc.failure_status,
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "elapsed_seconds": time.time() - started,
            }
        )
        _write_guard_receipt(args.guard_receipt, guard)
        return 43
    guard["gpu_lease"] = {key: value for key, value in lease.items() if key != "_fd"}
    job_cache_path = None
    try:
        job_cache_path, job_cache_receipt = prepare_isolated_job_cache(
            authorization
        )
        guard["job_cache"] = job_cache_receipt
    except BaseException as exc:
        lease_release = release_physical_gpu_lease(lease)
        guard.update(
            {
                "status": (
                    "failed_guard_internal_prelaunch"
                    if lease_release["released"]
                    else "failed_cleanup_uncertain"
                ),
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "gpu_lease_release": lease_release,
                "elapsed_seconds": time.time() - started,
            }
        )
        _write_guard_receipt(args.guard_receipt, guard)
        return 98 if lease_release["released"] else 94

    def finish_before_child(status: str, return_code: int, **extra) -> int:
        cache_cleanup = cleanup_isolated_job_cache(job_cache_path)
        lease_release = release_physical_gpu_lease(lease)
        cleanup_pass = bool(
            cache_cleanup.get("succeeded") and lease_release.get("released")
        )
        guard.update(extra)
        guard.update(
            {
                "status": status if cleanup_pass else "failed_cleanup_uncertain",
                "job_cache_cleanup": cache_cleanup,
                "gpu_lease_release": lease_release,
                "elapsed_seconds": time.time() - started,
            }
        )
        _write_guard_receipt(args.guard_receipt, guard)
        return return_code if cleanup_pass else 94

    try:
        pre = snapshot(args.physical_index, args.expected_uuid)
    except BaseException as exc:
        return finish_before_child(
            "failed_gpu_precheck",
            95,
            error={"type": type(exc).__name__, "message": str(exc)},
        )
    guard["admission_precheck"] = pre
    if not is_idle(pre):
        return finish_before_child("blocked_precheck_not_idle", 42)

    try:
        # Revalidate immediately before the irreversible one-shot consumption.
        source_lock = load_runtime_source_lock(
            Path(authorization["source_lock_receipt_path"]),
            expected_family=authorization["family"],
        )
        if source_lock["source_lock_receipt_sha256"] != authorization["source_lock_receipt_sha256"]:
            raise SourceLockError("source lock hash changed before authorization consumption")
        launch_pre = snapshot(args.physical_index, args.expected_uuid)
        guard["launch_precheck"] = launch_pre
        guard["precheck"] = launch_pre
        if not is_idle(launch_pre):
            raise GuardLaunchPrecheckNotIdle(
                "GPU stopped being fresh-idle before authorization consumption"
            )
        authorization = _load_runtime_authorization(
            args.authorization_receipt,
            requested_scope=authorization["approved_scopes"][0],
            expected_family=authorization["family"],
            expected_seed=authorization["scene_seed"],
            expected_output_namespace=str(args.output_dir),
            expected_reviewed_content_commit=authorization[
                "reviewed_content_commit"
            ],
        )
        consumption = _consume_runtime_authorization(
            authorization, ledger_directory=args.consumption_ledger_dir
        )
        binding = build_guard_binding(
            authorization,
            consumption,
            physical_index=args.physical_index,
            expected_uuid=args.expected_uuid,
            timeout_seconds=args.timeout_seconds,
            output_namespace=str(args.output_dir),
            command=command,
            guard_pid=os.getpid(),
        )
    except (
        AuthorizationError,
        GuardAuthorizationMismatch,
        GuardBudgetMismatch,
        GuardLaunchPrecheckNotIdle,
        SourceLockError,
    ) as exc:
        return finish_before_child(
            getattr(exc, "failure_status", "failed_runtime_source_lock"),
            97,
            error={"type": type(exc).__name__, "message": str(exc)},
        )
    except BaseException as exc:
        return finish_before_child(
            "failed_guard_internal_prelaunch",
            98,
            error={"type": type(exc).__name__, "message": str(exc)},
        )
    guard.update({"binding": binding, "consumption_receipt": consumption["path"], "status": "precheck_passed"})
    _write_guard_receipt(args.guard_receipt, guard)

    environment = build_isolated_child_environment(
        os.environ, args.expected_uuid, guard["job_cache"]
    )
    environment.update(
        {
            "CMF_GPU_GUARD_RECEIPT": str(args.guard_receipt.resolve()),
            "CMF_GPU_GUARD_PHYSICAL_INDEX": str(args.physical_index),
            "CMF_RUNTIME_AUTHORIZATION_RECEIPT": str(args.authorization_receipt.resolve()),
            "CMF_AUTHORIZATION_CONSUMPTION_RECEIPT": str(Path(consumption["path"]).resolve()),
            "CMF_GPU_LEASE_PATH": guard["gpu_lease"]["lease_path"],
            "CMF_JOB_CACHE_DIRECTORY": guard["job_cache"]["root"],
        }
    )
    child = None
    child_exit = None
    timed_out = False
    interrupted_signal = None
    terminal_cleanup_started = False
    orphan_pids: list[int] = []
    launch_error = None
    owned_process_cleanup_errors = []
    original_signal_handlers = {}
    atexit_registered = False

    def kill_owned_child_group(sig=signal.SIGKILL):
        if child is None:
            return
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            return
        except BaseException as exc:
            owned_process_cleanup_errors.append(
                {"type": type(exc).__name__, "message": str(exc)}
            )

    def handle_guard_signal(signum, _frame):
        nonlocal interrupted_signal
        interrupted_signal = int(signum)
        if terminal_cleanup_started:
            return
        if child is not None and child.poll() is None:
            kill_owned_child_group(signal.SIGTERM)
        raise GuardSignalInterrupt(signum)

    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            for signum in (signal.SIGINT, signal.SIGTERM):
                original_signal_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, handle_guard_signal)
            atexit.register(kill_owned_child_group)
            atexit_registered = True
            blocked_signals = {signal.SIGINT, signal.SIGTERM}
            inherited_signal_mask = signal.pthread_sigmask(
                signal.SIG_BLOCK, blocked_signals
            )
            try:
                child = subprocess.Popen(
                    command,
                    env=environment,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                    preexec_fn=functools.partial(
                        _set_parent_death_signal,
                        os.getpid(),
                        inherited_signal_mask,
                    ),
                )
                guard.update(
                    {
                        "status": "running",
                        "child_pid": int(child.pid),
                        "child_process_group_id": int(child.pid),
                        "selected_physical_gpu_index": int(args.physical_index),
                        "selected_gpu_uuid": args.expected_uuid,
                        "child_started_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                _write_guard_receipt(args.guard_receipt, guard)
            finally:
                signal.pthread_sigmask(
                    signal.SIG_SETMASK, inherited_signal_mask
                )
            try:
                child_exit = child.wait(timeout=args.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child_exit = child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child_exit = child.wait(timeout=15)
    except BaseException as exc:
        launch_error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        terminal_cleanup_started = True
        if child is not None:
            try:
                orphan_pids = pids_in_process_group(child.pid)
                if orphan_pids:
                    kill_owned_child_group(signal.SIGKILL)
                    time.sleep(1)
                    orphan_pids = pids_in_process_group(child.pid)
            except BaseException as exc:
                owned_process_cleanup_errors.append(
                    {"type": type(exc).__name__, "message": str(exc)}
                )
                orphan_pids = list(orphan_pids)

    time.sleep(1)
    post_error = None
    try:
        post = snapshot(args.physical_index, args.expected_uuid)
        post_release = verify_post_release(launch_pre, post)
    except BaseException as exc:
        post_error = {"type": type(exc).__name__, "message": str(exc)}
        post = {"status": "postcheck_failed", "error": post_error}
        post_release = {"verified": False, "checks": {}, "reason": "postcheck_snapshot_failed"}
    post_source_lock_error = None
    post_source_lock_pass = False
    try:
        post_source_lock = load_runtime_source_lock(
            Path(authorization["source_lock_receipt_path"]),
            expected_family=authorization["family"],
        )
        post_source_lock_pass = bool(
            post_source_lock["source_lock_receipt_sha256"]
            == authorization["source_lock_receipt_sha256"]
        )
        if not post_source_lock_pass:
            raise SourceLockError("post-run source lock hash mismatch")
    except BaseException as exc:
        post_source_lock_error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    job_cache_cleanup = cleanup_isolated_job_cache(job_cache_path)
    lease_release = release_physical_gpu_lease(lease)
    additional_cleanup_audit = {
        "job_cache_cleanup": job_cache_cleanup,
        "gpu_lease_release": lease_release,
        "pass": bool(
            job_cache_cleanup.get("succeeded") is True
            and lease_release.get("released") is True
        ),
    }
    receipt_updated = False
    receipt_update_error = None
    child_status_before_guard = None
    child_receipt_path = args.output_dir / "receipt.json"
    if child_receipt_path.is_file():
        try:
            child_status_before_guard = json.loads(
                child_receipt_path.read_text(encoding="utf-8")
            ).get("status")
        except BaseException:
            child_status_before_guard = None
    task_cleanup = build_task_owned_cleanup_audit_v1(
        child_exited=child is not None and child.poll() is not None,
        orphan_pids=orphan_pids,
        owned_process_cleanup_errors=owned_process_cleanup_errors,
        job_cache_cleanup=job_cache_cleanup,
        lease_release=lease_release,
        post_error=post_error,
        post_release=post_release,
    )
    external_processes_after_release = task_cleanup[
        "external_processes_after_release"
    ]
    external_process_detected_after_release = task_cleanup[
        "external_process_detected_after_release"
    ]
    task_owned_cleanup_pass = task_cleanup["task_owned_cleanup_pass"]
    gpu_returned_to_idle_baseline = task_cleanup[
        "gpu_returned_to_idle_baseline"
    ]
    try:
        receipt_updated = update_child_receipt_v2_1(
            args.output_dir,
            args.guard_receipt,
            binding,
            post,
            orphan_pids,
            post_release,
            post_error,
            additional_cleanup_audit=additional_cleanup_audit,
        )
    except BaseException as exc:
        receipt_update_error = {"type": type(exc).__name__, "message": str(exc)}
    cleanup_uncertain = task_cleanup["cleanup_uncertain"]
    if receipt_updated:
        child_receipt = json.loads((args.output_dir / "receipt.json").read_text(encoding="utf-8"))
        child_receipt["task_owned_cleanup_pass"] = task_owned_cleanup_pass
        child_receipt["task_owned_orphan_count"] = len(orphan_pids)
        child_receipt["gpu_returned_to_idle_baseline"] = (
            gpu_returned_to_idle_baseline
        )
        child_receipt["external_process_detected_after_release"] = (
            external_process_detected_after_release
        )
        child_receipt["external_processes_after_release"] = (
            external_processes_after_release
        )
        child_receipt["external_process_not_modified"] = True
        if (
            external_process_detected_after_release
            and task_owned_cleanup_pass
            and child_receipt.get("status") == "failed_cleanup_uncertain"
            and isinstance(child_status_before_guard, str)
        ):
            child_receipt["status"] = child_status_before_guard
        if interrupted_signal is not None:
            child_receipt["abort_signal"] = int(interrupted_signal)
            if cleanup_uncertain or child_receipt.get("status") == "failed_cleanup_uncertain":
                child_receipt["status"] = "failed_cleanup_uncertain"
            else:
                child_receipt["status"] = "aborted_with_reason"
            canonical_write_json(args.output_dir / "receipt.json", child_receipt)
        if post_source_lock_pass is not True:
            child_receipt["post_source_lock_error"] = post_source_lock_error
            if (
                cleanup_uncertain is not True
                and child_receipt.get("status") != "failed_cleanup_uncertain"
            ):
                child_receipt["status"] = "failed_runtime_source_lock"
            canonical_write_json(args.output_dir / "receipt.json", child_receipt)
        cleanup_uncertain = cleanup_uncertain or child_receipt.get("status") == "failed_cleanup_uncertain"
        sealed = dict(child_receipt)
        sealed.pop("guard_sealed_receipt_sha256", None)
        child_receipt["guard_sealed_receipt_sha256"] = canonical_hash_json(sealed)
        canonical_write_json(args.output_dir / "receipt.json", child_receipt)
    if cleanup_uncertain:
        terminal_status, return_code = classify_terminal_status(
            child_started=child is not None,
            receipt_updated=receipt_updated,
            receipt_update_error=receipt_update_error,
            cleanup_uncertain=True,
            timed_out=timed_out,
            child_exit=child_exit,
        )
    elif post_source_lock_pass is not True:
        terminal_status, return_code = "failed_runtime_source_lock", 97
    elif interrupted_signal is not None:
        terminal_status = "aborted_with_reason"
        return_code = 128 + int(interrupted_signal)
    elif launch_error is not None and child is None:
        terminal_status, return_code = "failed_child_launch", 93
    else:
        terminal_status, return_code = classify_terminal_status(
            child_started=child is not None,
            receipt_updated=receipt_updated,
            receipt_update_error=receipt_update_error,
            cleanup_uncertain=cleanup_uncertain,
            timed_out=timed_out,
            child_exit=child_exit,
        )
    guard.update(
        {
            "status": terminal_status,
            "child_exit_code": child_exit,
            "child_launch_error": launch_error,
            "timed_out": timed_out,
            "interrupted_signal": interrupted_signal,
            "postcheck": post,
            "postcheck_error": post_error,
            "postcheck_release": post_release,
            "post_source_lock_pass": post_source_lock_pass,
            "post_source_lock_error": post_source_lock_error,
            "job_cache_cleanup": job_cache_cleanup,
            "gpu_lease_release": lease_release,
            "task_owned_orphan_pids": orphan_pids,
            "owned_process_cleanup_errors": owned_process_cleanup_errors,
            "orphan_process_count": len(orphan_pids),
            "task_owned_cleanup_pass": task_owned_cleanup_pass,
            "task_owned_orphan_count": len(orphan_pids),
            "gpu_returned_to_idle_baseline": gpu_returned_to_idle_baseline,
            "external_process_detected_after_release": external_process_detected_after_release,
            "external_processes_after_release": external_processes_after_release,
            "external_process_not_modified": True,
            "child_receipt_updated": receipt_updated,
            "child_receipt_update_error": receipt_update_error,
            "elapsed_seconds": time.time() - started,
        }
    )
    guard["stdout_log"] = _file_evidence(stdout_path)
    guard["stderr_log"] = _file_evidence(stderr_path)
    guard["child_receipt_file"] = _file_evidence(args.output_dir / "receipt.json")
    guard["guard_receipt_sha256"] = canonical_hash_json(guard)
    _write_guard_receipt(args.guard_receipt, guard)
    for signum, handler in original_signal_handlers.items():
        signal.signal(signum, handler)
    if atexit_registered:
        atexit.unregister(kill_owned_child_group)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
