"""CPU-only publications and one-shot bundle for post-Stage-0 F3."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from .current_hasher import hash_json
from .f3_contact_preserving_prefix_v11 import IMPLEMENTATION_VERSION
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .post_stage0_f3_scope_v1 import (
    AUTHORIZATION_ID,
    AUTHORIZATION_PATH,
    BUDGET_PUBLICATION,
    GUARD_PATH,
    IMPACT_REVIEW,
    OUTPUT_NAMESPACE,
    PARENT_AUTHORIZATION,
    REQUEST_PATH,
    SCENE_SEED,
    SCOPE,
    SCOPE_PUBLICATION,
    SOURCE_LOCK_PATH,
    post_stage0_f3_budget_v1,
    post_stage0_f3_parent_authorization_v1,
    post_stage0_f3_planned_spec_v1,
    post_stage0_f3_scope_publication_v1,
)
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.post_stage0_f3_authorization_v1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    authorization_receipt_sha256,
    validate_post_stage0_f3_authorization_v1,
)
from .probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from .runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
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
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def write_post_stage0_f3_cpu_publications_v1() -> dict[str, Any]:
    values = {
        BUDGET_PUBLICATION: post_stage0_f3_budget_v1(),
        SCOPE_PUBLICATION: post_stage0_f3_scope_publication_v1(),
        PARENT_AUTHORIZATION: post_stage0_f3_parent_authorization_v1(),
    }
    for path, value in values.items():
        _write_new_json(path, value)
    return {
        str(path): {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
        for path in values
    }


def build_post_stage0_f3_bundle_v1() -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    if head != origin:
        raise RuntimeError("Vault HEAD must equal origin/main before bundle freeze")
    if OUTPUT_NAMESPACE.exists() or GUARD_PATH.exists() or AUTHORIZATION_PATH.exists():
        raise RuntimeError("post-Stage-0 F3 run1 namespace already exists")
    ledger_path = (
        Path(CANONICAL_CONSUMPTION_LEDGER_DIRECTORY) / f"{AUTHORIZATION_ID}.json"
    )
    cache_path = Path(CANONICAL_JOB_CACHE_DIRECTORY) / AUTHORIZATION_ID
    if ledger_path.exists() or cache_path.exists():
        raise RuntimeError("post-Stage-0 F3 run1 was already consumed or cached")
    active_sha = _python_tree_sha256(ACTIVE_SOURCE)
    snapshot_sha = _python_tree_sha256(SNAPSHOT_SOURCE)
    if active_sha != snapshot_sha:
        raise RuntimeError("active and review snapshot Python trees differ")
    publications = {
        BUDGET_PUBLICATION: post_stage0_f3_budget_v1(),
        SCOPE_PUBLICATION: post_stage0_f3_scope_publication_v1(),
        PARENT_AUTHORIZATION: post_stage0_f3_parent_authorization_v1(),
    }
    for path, expected in publications.items():
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != expected:
            raise RuntimeError(f"CPU publication is missing or changed: {path}")
    impact = json.loads(IMPACT_REVIEW.read_text(encoding="utf-8"))
    if impact.get("review_payload_sha256") != (
        "07882b05fe0cbc1932aab24a9b7a4b669f79e53c10504faacd20078947d93325"
    ):
        raise RuntimeError("F3 impact review payload changed")
    source_lock = capture_runtime_source_lock(family="F3")
    if source_lock["snapshot"]["implementation_source_sha256"] != active_sha:
        raise RuntimeError("source-lock implementation hash mismatch")
    child_command = [
        str(PYTHON),
        "-m",
        "controlled_multi_future.probes.post_stage0_f3_scope_runner_v1",
        "--authorization-receipt",
        str(AUTHORIZATION_PATH.resolve()),
    ]
    policy = current_gpu_policy_artifact()
    budget = post_stage0_f3_budget_v1()
    planned = post_stage0_f3_planned_spec_v1()
    parent = post_stage0_f3_parent_authorization_v1()
    scope_publication = post_stage0_f3_scope_publication_v1()
    request = {
        "schema_version": "cmf_post_stage0_f3_scope_request_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "family": "F3",
        "scene_seed": SCENE_SEED,
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": planned["planned_scope_spec_sha256"],
        "scope_publication_sha256": scope_publication[
            "scope_publication_sha256"
        ],
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "impact_review_payload_sha256": impact["review_payload_sha256"],
        "implementation_source_sha256": active_sha,
        "reviewed_content_commit": head,
        "reviewed_content_commit_contains_current_changes": False,
        "uncommitted_source_bound_by_source_lock": True,
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
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
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
        "family": "F3",
        "scene_seed": SCENE_SEED,
        "max_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage0_reopened": False,
        "stage1_authorized": False,
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": planned["planned_scope_spec_sha256"],
        "scope_publication_path": str(SCOPE_PUBLICATION.resolve()),
        "scope_publication_file_sha256": _sha256_file(SCOPE_PUBLICATION),
        "scope_publication_sha256": scope_publication[
            "scope_publication_sha256"
        ],
        "budget_publication_path": str(BUDGET_PUBLICATION.resolve()),
        "budget_publication_file_sha256": _sha256_file(BUDGET_PUBLICATION),
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": budget["execution_limit"],
        "physics_step_limit": budget["physics_step_limit"],
        "timeout_seconds": budget["timeout_seconds"],
        "impact_review_path": str(IMPACT_REVIEW.resolve()),
        "impact_review_file_sha256": _sha256_file(IMPACT_REVIEW),
        "impact_review_payload_sha256": impact["review_payload_sha256"],
        "source_lock_receipt_path": str(SOURCE_LOCK_PATH.resolve()),
        "source_lock_receipt_sha256": source_lock[
            "source_lock_receipt_sha256"
        ],
        "implementation_source_sha256": active_sha,
        "reviewed_content_commit": head,
        "reviewed_content_commit_contains_current_changes": False,
        "uncommitted_source_bound_by_source_lock": True,
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
    validate_post_stage0_f3_authorization_v1(
        authorization,
        requested_scope=SCOPE,
        now=issued + timedelta(seconds=1),
        expected_family="F3",
        expected_seed=SCENE_SEED,
        expected_output_namespace=str(OUTPUT_NAMESPACE.resolve()),
        expected_reviewed_content_commit=head,
    )
    return {
        "schema_version": "cmf_post_stage0_f3_bundle_receipt_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "reviewed_content_commit": head,
        "reviewed_content_commit_contains_current_changes": False,
        "uncommitted_source_bound_by_source_lock": True,
        "implementation_source_sha256": active_sha,
        "scope_publication_sha256": scope_publication[
            "scope_publication_sha256"
        ],
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
    "build_post_stage0_f3_bundle_v1",
    "write_post_stage0_f3_cpu_publications_v1",
]
