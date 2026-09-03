#!/usr/bin/env python3
"""Shared pre-GPU manifest/job validation for the final F4 reopen exception."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
EXPECTED_STATUS = "APPROVED_FINAL_F4_GUARD_SCHEMA_REPAIR_REOPEN2"
EXPECTED_CONTROLLED_SOURCE_SHA256 = (
    "3dcef886f108efb88e81540e9f36e7fd00646165b794d0d4203fa806b7fbd3fd"
)
EXPECTED_ROBOTWIN_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_DECISION_FILE_SHA256 = (
    "ee818c10005d5bef0e60c46dd0d9fb4811333d1e34c65c3e350ac35bdf553d73"
)
EXPECTED_RUN13_TERMINAL_FILE_SHA256 = (
    "3890ef5b5b09b40d6ea8a169571353006ae1f9fcc8040e5887e2293ab21d1f1a"
)
EXPECTED_RUN13_TERMINAL_RECEIPT_SHA256 = (
    "1a91f72fc164870a450f112785de179f949ea3a0a8e45a3210940d3a6310bf7d"
)
EXPECTED_F4_SOURCE_SHA256 = (
    "f9f12de9f23e784fa1fa600aaa3b9e2ac27e4226d3fea8b84c466230a4f67ea8"
)
EXPECTED_PROGRAMS = ["F4-ABC", "F4-ACB", "F4-BAC"]
EXPECTED_CANDIDATE_SHA256 = (
    "981d7a2ecf791b3d5545aa0ca136105e5f8e41ba4523333370de87ed5dffb2df"
)
EXPECTED_DRY_CANDIDATE_FREEZE_SHA256 = (
    "812a90425662352ccb4f0402549aea9a879ddf17a8d189e0464a772d021bfed6"
)
EXPECTED_BUDGET = {
    "maximum_root_invocations": 1,
    "maximum_canonical_prefix_generations": 1,
    "maximum_exact_prefix_replays": 3,
    "maximum_suffix_preflights": 3,
    "maximum_branch_executions": 3,
    "maximum_planner_queries": 136,
    "maximum_fresh_scenes": 8,
    "maximum_robot_action_scenes": 4,
    "maximum_debug_videos": 3,
    "maximum_raw_trajectories": 3,
    "maximum_accepted_development_roots": 1,
    "maximum_accepted_development_trajectories": 3,
    "maximum_formal_trajectories": 0,
}


class ManifestContractError(RuntimeError):
    pass


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def python_tree_sha(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _required(value: Mapping[str, Any], key: str, label: str):
    if key not in value:
        raise ManifestContractError(f"{label} missing required field: {key}")
    return value[key]


def _workspace_path(value: Any, label: str, *, file: bool | None = None) -> Path:
    path = Path(str(value)).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise ManifestContractError(f"{label} is outside workspace")
    if file is True and not path.is_file():
        raise ManifestContractError(f"{label} file is missing")
    if file is False and path.exists():
        raise ManifestContractError(f"{label} must be a new path")
    return path


def _bound_file(
    value: Mapping[str, Any], path_key: str, sha_key: str, label: str
) -> Path:
    path = _workspace_path(_required(value, path_key, "manifest"), label, file=True)
    expected = str(_required(value, sha_key, "manifest"))
    if file_sha(path) != expected:
        raise ManifestContractError(f"{label} SHA-256 mismatch")
    return path


def load_and_validate_manifest_job(
    manifest_path: Path,
    job_id: str,
) -> dict[str, Any]:
    """The only pre-GPU validator used by Guard and runner preflight/runtime."""

    path = _workspace_path(manifest_path, "manifest", file=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ManifestContractError("manifest must be a mapping")
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ManifestContractError("manifest self-hash mismatch")
    if _required(value, "status", "manifest") != EXPECTED_STATUS:
        raise ManifestContractError("manifest status is not the reviewed F4 approval")
    for key in ("approved", "gpu_execution_authorized", "physical_execution_authorized"):
        if _required(value, key, "manifest") is not True:
            raise ManifestContractError(f"manifest {key} must be true")
    run_id = _required(value, "run_id", "manifest")
    if not isinstance(run_id, str) or not run_id:
        raise ManifestContractError("manifest run_id is invalid")
    guard_directory = _workspace_path(
        _required(value, "guard_directory", "manifest"),
        "guard_directory",
        file=False,
    )
    cache_directory = _workspace_path(
        _required(value, "cache_directory", "manifest"),
        "cache_directory",
    )
    contract_path = _bound_file(
        value, "manifest_contract_path", "manifest_contract_sha256", "manifest contract"
    )
    guard_path = _bound_file(
        value, "guard_script_path", "guard_script_sha256", "guard script"
    )
    runner_path = _bound_file(
        value, "runner_script_path", "runner_script_sha256", "runner script"
    )
    decision_path = _bound_file(
        value,
        "external_review_decision_path",
        "external_review_decision_file_sha256",
        "external review decision",
    )
    if file_sha(decision_path) != EXPECTED_DECISION_FILE_SHA256:
        raise ManifestContractError("external review decision differs from reviewed file")
    run13_path = _bound_file(
        value,
        "run13_terminal_path",
        "run13_terminal_file_sha256",
        "Run13 terminal",
    )
    if file_sha(run13_path) != EXPECTED_RUN13_TERMINAL_FILE_SHA256:
        raise ManifestContractError("Run13 terminal differs from zero-consumption evidence")
    run13 = json.loads(run13_path.read_text(encoding="utf-8"))
    if run13.get("receipt_sha256") != EXPECTED_RUN13_TERMINAL_RECEIPT_SHA256:
        raise ManifestContractError("Run13 terminal receipt binding changed")
    if _required(value, "implementation_source_sha256", "manifest") != EXPECTED_CONTROLLED_SOURCE_SHA256:
        raise ManifestContractError("controlled source binding differs from review")
    if python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_CONTROLLED_SOURCE_SHA256:
        raise ManifestContractError("active controlled source differs from freeze")
    if _required(value, "f4_source_sha256", "manifest") != EXPECTED_F4_SOURCE_SHA256:
        raise ManifestContractError("F4 operational source hash changed")
    if file_sha(PROJECT / "controlled_multi_future/f4_full_program_physical_v1.py") != EXPECTED_F4_SOURCE_SHA256:
        raise ManifestContractError("active F4 operational source changed")
    if _required(value, "robotwin_tracked_head", "manifest") != EXPECTED_ROBOTWIN_HEAD:
        raise ManifestContractError("RoboTwin tracked head binding changed")
    head = subprocess.run(
        ["git", "-C", str(PROJECT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "-C", str(PROJECT), "status", "--porcelain", "--untracked-files=no"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    ).stdout.strip()
    if head != EXPECTED_ROBOTWIN_HEAD or tracked:
        raise ManifestContractError("official RoboTwin tracked worktree changed")
    if _required(value, "allowed_physical_gpu_indices", "manifest") != list(range(8)):
        raise ManifestContractError("allowed physical GPU scope changed")
    if _required(value, "one_job_per_gpu", "manifest") is not True:
        raise ManifestContractError("one-job-per-GPU contract missing")
    if _required(value, "root_sharding", "manifest") is not False:
        raise ManifestContractError("root sharding must remain false")
    for key in (
        "stage0_reopened",
        "stage1_authorized",
        "formal_360_authorized",
        "training_authorized",
        "h_reveal_authorized",
        "compression_authorized",
        "pi05_authorized",
        "formal_data",
    ):
        if _required(value, key, "manifest") is not False:
            raise ManifestContractError(f"forbidden manifest field enabled: {key}")
    assets_by_family = _required(value, "asset_hashes_by_family", "manifest")
    if set(assets_by_family) != {"F4"} or not assets_by_family["F4"]:
        raise ManifestContractError("F4 asset hash map is missing")
    for relative, expected in assets_by_family["F4"].items():
        asset = (PROJECT / relative).resolve()
        if not asset.is_file() or file_sha(asset) != expected:
            raise ManifestContractError(f"F4 asset hash mismatch: {relative}")
    jobs = _required(value, "jobs", "manifest")
    if not isinstance(jobs, list) or len(jobs) != 1:
        raise ManifestContractError("F4 approval requires exactly one job")
    job = jobs[0]
    if _required(job, "job_id", "job") != job_id:
        raise ManifestContractError("requested job ID differs from approved job")
    if _required(job, "family", "job") != "F4":
        raise ManifestContractError("approved job family is not F4")
    if _required(job, "mode", "job") != "ONE_F4_DEVELOPMENT_R_PC_ROOT_V1":
        raise ManifestContractError("approved F4 dispatch mode changed")
    if _required(job, "program_order", "job") != EXPECTED_PROGRAMS:
        raise ManifestContractError("F4 program order changed")
    if _required(job, "fixed_arm_schedule", "job") != {
        "canonical_prefix": "right",
        "program_suffix": "left",
    }:
        raise ManifestContractError("F4 fixed arm schedule changed")
    if _required(job, "candidate_id", "job") != "f4-slot-corridor-hv2-r01":
        raise ManifestContractError("F4 candidate changed")
    if _required(job, "candidate_sha256", "job") != EXPECTED_CANDIDATE_SHA256:
        raise ManifestContractError("F4 candidate SHA changed")
    if (
        _required(job, "dry_candidate_frozen_spec_sha256", "job")
        != EXPECTED_DRY_CANDIDATE_FREEZE_SHA256
    ):
        raise ManifestContractError("F4 dry candidate-freeze receipt changed")
    for key, expected in EXPECTED_BUDGET.items():
        if _required(job, key, "job") != expected:
            raise ManifestContractError(f"F4 reviewed budget changed: {key}")
    for key in ("automatic_retry", "fallback_allowed", "second_replacement_allowed"):
        if _required(job, key, "job") is not False:
            raise ManifestContractError(f"forbidden F4 behavior enabled: {key}")
    if _required(value, "reopen_ordinal_after_run13", "manifest") != 1:
        raise ManifestContractError("F4 final repair exception ordinal changed")
    if _required(value, "third_reopening_authorized", "manifest") is not False:
        raise ManifestContractError("third F4 reopening must remain forbidden")
    output = _workspace_path(
        _required(job, "output_namespace", "job"), "output namespace", file=False
    )
    cache_job = cache_directory / job_id
    if cache_job.exists():
        raise ManifestContractError("job cache namespace must be new")
    for required_path, expected_path in (
        (contract_path, Path(__file__).resolve()),
        (guard_path, Path(value["guard_script_path"]).resolve()),
        (runner_path, Path(value["runner_script_path"]).resolve()),
    ):
        if required_path != expected_path:
            raise ManifestContractError("runtime path resolution changed")
    return {
        "manifest": dict(value),
        "job": dict(job),
        "manifest_path": str(path),
        "manifest_sha256": digest,
        "run_id": run_id,
        "guard_directory": str(guard_directory),
        "cache_directory": str(cache_directory),
        "output_namespace": str(output),
        "contract_path": str(contract_path),
        "guard_path": str(guard_path),
        "runner_path": str(runner_path),
        "validation_stage": "complete_pre_gpu_no_side_effects",
    }


__all__ = [
    "ManifestContractError",
    "canonical_hash",
    "file_sha",
    "load_and_validate_manifest_job",
    "python_tree_sha",
]
