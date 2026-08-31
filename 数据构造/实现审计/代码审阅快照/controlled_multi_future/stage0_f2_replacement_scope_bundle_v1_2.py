"""CPU-only publication and one-shot bundle builder for F2 replacement v1.2."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from .current_hasher import hash_json
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from .stage0_f2_replacement_manifest_v1_2 import (
    CANONICAL_OUTPUT,
    IMPLEMENTATION_VERSION,
    OUTPUT_NAMESPACE,
    SCOPE,
    build_stage0_f2_replacement_manifest_v1_2,
    f2_replacement_budget_v1_2,
)
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from .probes.stage0_f2_replacement_authorization_v1_2 import (
    AUTHORIZATION_ID,
    AUTHORIZATION_PATH,
    AUTHORIZATION_SCHEMA_VERSION,
    BUDGET_PUBLICATION,
    GUARD_PATH,
    PARENT_AUTHORIZATION,
    REQUEST_PATH,
    SOURCE_LOCK_PATH,
    authorization_receipt_sha256,
)


WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
ROBOTWIN_ROOT = WORKSPACE_ROOT / "Robotwin2/project/RoboTwin"
ACTIVE_SOURCE = ROBOTWIN_ROOT / "controlled_multi_future"
SNAPSHOT_SOURCE = (
    WORKSPACE_ROOT
    / "Vault-on-Fvl09/数据构造/实现审计/代码审阅快照/controlled_multi_future"
)
VAULT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09"
PYTHON = WORKSPACE_ROOT / "Robotwin2/env/bin/python"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _python_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(VAULT_ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _write_new_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    fd = path.open("xb")
    with fd:
        fd.write(data)
        fd.flush()


def build_parent_user_authorization_v1_2() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_stage0_f2_replacement_parent_user_authorization_v1_2",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "authorized_scope": SCOPE,
        "replacement_only": True,
        "attempts": 3,
        "attempts_per_program": 1,
        "same_seed": 20260829,
        "same_programs": ["F2-inside", "F2-on", "F2-beside"],
        "replacement_reason": "frozen_scene_layout_wiring_fix",
        "old_attempts_retained": True,
        "old_attempts_overwritten": False,
        "allowed_physical_gpu_indices": list(range(8)),
        "family_level_parallelism_authorized": True,
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal": None,
        "compression_authorized": False,
        "pi05_authorized": False,
        "user_direction_source": (
            "https://chatgpt.com/s/t_6a95071af4c081919040e97237d3dca2"
        ),
    }
    value["parent_user_authorization_sha256"] = hash_json(value)
    return value


def write_cpu_publications_v1_2() -> dict[str, Any]:
    values = {
        CANONICAL_OUTPUT: build_stage0_f2_replacement_manifest_v1_2(),
        BUDGET_PUBLICATION: f2_replacement_budget_v1_2(),
        PARENT_AUTHORIZATION: build_parent_user_authorization_v1_2(),
    }
    for path, value in values.items():
        _write_new_json(path, value)
    return {
        str(path): {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
        for path in values
    }


def build_f2_replacement_bundle_v1_2() -> dict[str, Any]:
    if _git("status", "--porcelain"):
        raise RuntimeError("Vault worktree must be clean before one-shot bundle")
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    if head != origin:
        raise RuntimeError("Vault HEAD must equal origin/main")
    active_sha = _python_tree_sha256(ACTIVE_SOURCE)
    if _python_tree_sha256(SNAPSHOT_SOURCE) != active_sha:
        raise RuntimeError("active and review snapshot source differ")
    manifest = build_stage0_f2_replacement_manifest_v1_2()
    published_manifest = json.loads(CANONICAL_OUTPUT.read_text(encoding="utf-8"))
    if published_manifest != manifest:
        raise RuntimeError("published replacement manifest changed")
    budget = f2_replacement_budget_v1_2()
    if json.loads(BUDGET_PUBLICATION.read_text(encoding="utf-8")) != budget:
        raise RuntimeError("published replacement budget changed")
    parent = build_parent_user_authorization_v1_2()
    if json.loads(PARENT_AUTHORIZATION.read_text(encoding="utf-8")) != parent:
        raise RuntimeError("published parent authorization changed")
    source_lock = capture_runtime_source_lock(family="F2")
    if source_lock["snapshot"]["implementation_source_sha256"] != active_sha:
        raise RuntimeError("source-lock implementation hash mismatch")
    child_command = [
        str(PYTHON),
        "-m",
        "controlled_multi_future.probes.stage0_f2_replacement_scope_runner_v1_2",
        "--authorization-receipt",
        str(AUTHORIZATION_PATH.resolve()),
    ]
    policy = current_gpu_policy_artifact()
    request = {
        "schema_version": "cmf_stage0_f2_replacement_scope_request_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F2",
        "scene_seed": 20260829,
        "planned_root_slot_spec": manifest["replacement_root_spec"],
        "planned_root_slot_spec_sha256": manifest[
            "replacement_root_spec_sha256"
        ],
        "replacement_manifest_sha256": manifest["manifest_sha256"],
        "scope_budget": budget,
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "implementation_source_sha256": active_sha,
        "reviewed_content_commit": head,
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "authorized_command": child_command,
        "authorized_command_sha256": command_sha256(child_command),
        "output_namespace": str(OUTPUT_NAMESPACE.resolve()),
        "guard_receipt_path": str(GUARD_PATH.resolve()),
        "allowed_physical_gpu_indices": list(range(8)),
        "gpu_policy_sha256": policy["policy_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
    }
    request["scope_request_sha256"] = hash_json(request)
    write_runtime_source_lock(SOURCE_LOCK_PATH, source_lock)
    _write_new_json(REQUEST_PATH, request)
    issued = datetime.now(timezone.utc)
    authorization = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "approved": True,
        "approved_scopes": [SCOPE],
        "authorization_id": AUTHORIZATION_ID,
        "authorized_run_id": AUTHORIZATION_ID + "-run",
        "issued_at": issued.isoformat(),
        "expires_at": (issued + timedelta(seconds=3600)).isoformat(),
        "family": "F2",
        "scene_seed": 20260829,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "planned_root_slot_spec": manifest["replacement_root_spec"],
        "planned_root_slot_spec_sha256": manifest[
            "replacement_root_spec_sha256"
        ],
        "replacement_manifest_path": str(CANONICAL_OUTPUT.resolve()),
        "replacement_manifest_file_sha256": _sha256_file(CANONICAL_OUTPUT),
        "replacement_manifest_sha256": manifest["manifest_sha256"],
        "budget_publication_path": str(BUDGET_PUBLICATION.resolve()),
        "budget_publication_file_sha256": _sha256_file(BUDGET_PUBLICATION),
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": budget["execution_limit"],
        "physics_step_limit": -1,
        "timeout_seconds": budget["timeout_seconds"],
        "source_lock_receipt_path": str(SOURCE_LOCK_PATH.resolve()),
        "source_lock_receipt_sha256": source_lock[
            "source_lock_receipt_sha256"
        ],
        "implementation_source_sha256": active_sha,
        "reviewed_content_commit": head,
        "parent_user_authorization_path": str(PARENT_AUTHORIZATION.resolve()),
        "parent_user_authorization_file_sha256": _sha256_file(
            PARENT_AUTHORIZATION
        ),
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "approval_request_path": str(REQUEST_PATH.resolve()),
        "approval_request_file_sha256": _sha256_file(REQUEST_PATH),
        "approval_request_sha256": request["scope_request_sha256"],
        "authorized_command": child_command,
        "authorized_command_sha256": command_sha256(child_command),
        "output_namespace": str(OUTPUT_NAMESPACE.resolve()),
        "guard_receipt_path": str(GUARD_PATH.resolve()),
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        **{
            key: policy[key]
            for key in (
                "gpu_policy_version",
                "allowed_physical_gpu_indices",
                "dynamic_fresh_idle_selection",
                "parallel_different_cards_authorized",
                "one_project_job_per_gpu",
                "one_root_one_gpu",
                "root_sharding_authorized",
                "share_busy_gpu_authorized",
                "atomic_guard_recheck_before_launch",
                "automatic_gpu0_fallback",
            )
        },
    }
    authorization["receipt_sha256"] = authorization_receipt_sha256(
        authorization
    )
    _write_new_json(AUTHORIZATION_PATH, authorization)
    return {
        "schema_version": "cmf_stage0_f2_replacement_bundle_receipt_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "reviewed_content_commit": head,
        "implementation_source_sha256": active_sha,
        "replacement_manifest_sha256": manifest["manifest_sha256"],
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "parent_user_authorization_sha256": parent[
            "parent_user_authorization_sha256"
        ],
        "source_lock_receipt_sha256": source_lock[
            "source_lock_receipt_sha256"
        ],
        "scope_request_sha256": request["scope_request_sha256"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorization_path": str(AUTHORIZATION_PATH.resolve()),
        "guard_path": str(GUARD_PATH.resolve()),
        "output_namespace": str(OUTPUT_NAMESPACE.resolve()),
        "child_command": child_command,
        "timeout_seconds": budget["timeout_seconds"],
        "physical_gpu_indices": list(range(8)),
    }


__all__ = [
    "build_f2_replacement_bundle_v1_2",
    "build_parent_user_authorization_v1_2",
    "write_cpu_publications_v1_2",
]
