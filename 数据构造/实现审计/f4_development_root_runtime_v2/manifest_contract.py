#!/usr/bin/env python3
"""Phase-aware F4 development-root manifest and lifecycle contract."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
VAULT = WORKSPACE / "Vault-on-Fvl09"
PLAN = VAULT / "数据构造/实现审计/CMF_F2_F3_F4_NEXT_EXECUTION_PLAN_V1_20260904.md"
PLAN_SHA256 = "f219a4e57f617b322a9526f939bf9498716f4e428ba220bbd80e64e21e7cfe12"
EXPECTED_CONTROLLED_SOURCE_SHA256 = (
    "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
)
EXPECTED_ROBOTWIN_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_F4_SOURCE_SHA256 = (
    "f9f12de9f23e784fa1fa600aaa3b9e2ac27e4226d3fea8b84c466230a4f67ea8"
)
EXPECTED_PROGRAMS = ["F4-ABC", "F4-ACB", "F4-BAC"]
EXPECTED_CANDIDATE_ID = "f4-slot-corridor-hv2-r01"
EXPECTED_CANDIDATE_SHA256 = (
    "981d7a2ecf791b3d5545aa0ca136105e5f8e41ba4523333370de87ed5dffb2df"
)
EXPECTED_DRY_CANDIDATE_FREEZE_SHA256 = (
    "812a90425662352ccb4f0402549aea9a879ddf17a8d189e0464a772d021bfed6"
)
EXPECTED_HISTORICAL_STATUSES = {
    "Run10": "F4_DEVELOPMENT_ROOT_INCOMPLETE_LEGACY_TASK_FEASIBILITY_MISMATCH",
    "Run11": "F4_DEVELOPMENT_ROOT_INCOMPLETE_SUFFIX_QUERY_ACCOUNTING_INTEGRATION_ERROR",
    "Run12": "F4_DEVELOPMENT_ROOT_FINAL_INCOMPLETE_NO_FURTHER_REPLACEMENT",
    "Run13": "FAILED_GUARD_MANIFEST_SCHEMA_WITH_EVIDENCE",
    "Run14": "F4_FINAL_REOPEN_CLOSED_RUNNER_VALIDATION_FAILURE",
}
EXPECTED_BUDGET = {
    "maximum_root_invocations": 1,
    "maximum_canonical_prefix_generations": 1,
    "maximum_suffix_prefix_replays": 3,
    "maximum_branch_prefix_replays": 3,
    "maximum_total_prefix_replays": 6,
    "maximum_suffix_preflights": 3,
    "maximum_branch_executions": 3,
    "maximum_planner_queries": 136,
    "maximum_fresh_scenes": 11,
    "maximum_robot_action_scenes": 7,
    "maximum_raw_trajectories": 3,
    "maximum_debug_videos": 3,
    "maximum_accepted_development_roots": 1,
    "maximum_accepted_development_trajectories": 3,
    "maximum_formal_trajectories": 0,
}
EXPECTED_CACHE_SUBDIRS = (
    "conda_pkgs",
    "cuda",
    "home",
    "matplotlib",
    "numba",
    "tmp",
    "torch_extensions",
    "torch",
    "xdg",
)

PREPUBLICATION = "PREPUBLICATION"
GUARD_ENTRY = "GUARD_ENTRY"
RUNNER_ENTRY = "RUNNER_ENTRY"
POST_CHILD = "POST_CHILD"
PHASES = {PREPUBLICATION, GUARD_ENTRY, RUNNER_ENTRY, POST_CHILD}


class F4ManifestContractError(RuntimeError):
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
        raise F4ManifestContractError(f"{label} missing required field: {key}")
    return value[key]


def _workspace_path(value: Any, label: str, *, file: bool | None = None) -> Path:
    path = Path(str(value)).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise F4ManifestContractError(f"{label} is outside workspace")
    if file is True and not path.is_file():
        raise F4ManifestContractError(f"{label} file is missing")
    if file is False and path.exists():
        raise F4ManifestContractError(f"{label} must be absent")
    return path


def _bound_file(
    value: Mapping[str, Any], path_key: str, sha_key: str, label: str
) -> Path:
    path = _workspace_path(_required(value, path_key, "manifest"), label, file=True)
    expected = str(_required(value, sha_key, "manifest"))
    if file_sha(path) != expected:
        raise F4ManifestContractError(f"{label} SHA-256 mismatch")
    return path


def _self_hashed_file(path: Path, key: str, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop(key, None)
    if digest != canonical_hash(payload):
        raise F4ManifestContractError(f"{label} self-hash mismatch")
    return value


def read_manifest(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = _workspace_path(path, "manifest", file=True)
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise F4ManifestContractError("manifest must be a mapping")
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise F4ManifestContractError("manifest self-hash mismatch")
    return resolved, dict(value)


def validate_manifest_semantics(
    value: Mapping[str, Any],
    *,
    require_execution_authorized: bool,
    allow_lifecycle_fixture: bool = False,
) -> dict[str, Any]:
    fixture = value.get("cpu_lifecycle_fixture") is True
    if fixture and not allow_lifecycle_fixture:
        raise F4ManifestContractError("CPU lifecycle fixture is not allowed here")
    expected_status = (
        "APPROVED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V1"
        if require_execution_authorized
        else "PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V1"
    )
    if _required(value, "status", "manifest") != expected_status:
        raise F4ManifestContractError("F4 manifest status differs from phase authority")
    for key in ("approved", "gpu_execution_authorized", "physical_execution_authorized"):
        expected = bool(require_execution_authorized)
        if _required(value, key, "manifest") is not expected:
            raise F4ManifestContractError(f"manifest {key} must be {expected}")
    if _required(value, "cpu_infrastructure_repair_authorized", "manifest") is not True:
        raise F4ManifestContractError("F4 CPU infrastructure repair is not authorized")
    if _required(value, "scientific_status", "manifest") != "PHYSICALLY_QUALIFIED":
        raise F4ManifestContractError("F4 physical qualification status changed")
    if _required(value, "root_status", "manifest") != "INFRASTRUCTURE_BLOCKED_BEFORE_BRANCH":
        raise F4ManifestContractError("F4 root infrastructure status changed")
    for key in (
        "stage0_reopened",
        "stage1_authorized",
        "formal_360_authorized",
        "training_authorized",
        "h_reveal_authorized",
        "compression_authorized",
        "pi05_authorized",
        "formal_data",
        "third_candidate_search_authorized",
        "automatic_continuation",
    ):
        if _required(value, key, "manifest") is not False:
            raise F4ManifestContractError(f"forbidden manifest field enabled: {key}")
    for unknown in (
        "third_reopening_authorized",
        "third_reopen_authorized",
        "reopen_ordinal_after_run14",
    ):
        if unknown in value:
            raise F4ManifestContractError(f"unknown/legacy F4 reopen field forbidden: {unknown}")
    if _required(value, "allowed_physical_gpu_indices", "manifest") != list(range(8)):
        raise F4ManifestContractError("allowed physical GPU scope changed")
    if _required(value, "one_job_per_gpu", "manifest") is not True:
        raise F4ManifestContractError("one-job-per-GPU contract missing")
    if _required(value, "root_sharding", "manifest") is not False:
        raise F4ManifestContractError("root sharding must remain false")
    jobs = _required(value, "jobs", "manifest")
    if not isinstance(jobs, list) or len(jobs) != 1:
        raise F4ManifestContractError("F4 manifest requires exactly one job")
    job = jobs[0]
    if _required(job, "family", "job") != "F4":
        raise F4ManifestContractError("F4 job family changed")
    if _required(job, "mode", "job") != "ONE_F4_DEVELOPMENT_R_PC_ROOT_V2":
        raise F4ManifestContractError("F4 V2 dispatch mode changed")
    if _required(job, "candidate_id", "job") != EXPECTED_CANDIDATE_ID:
        raise F4ManifestContractError("F4 candidate changed")
    if _required(job, "candidate_sha256", "job") != EXPECTED_CANDIDATE_SHA256:
        raise F4ManifestContractError("F4 candidate SHA changed")
    if (
        _required(job, "dry_candidate_frozen_spec_sha256", "job")
        != EXPECTED_DRY_CANDIDATE_FREEZE_SHA256
    ):
        raise F4ManifestContractError("F4 dry candidate freeze changed")
    if _required(job, "program_order", "job") != EXPECTED_PROGRAMS:
        raise F4ManifestContractError("F4 program order changed")
    if _required(job, "fixed_arm_schedule", "job") != {
        "canonical_prefix": "right",
        "program_suffix": "left",
    }:
        raise F4ManifestContractError("F4 fixed arm schedule changed")
    for key in ("automatic_retry", "fallback_allowed", "candidate_search_allowed", "seed_retry_allowed", "second_root_allowed"):
        if _required(job, key, "job") is not False:
            raise F4ManifestContractError(f"forbidden F4 behavior enabled: {key}")
    validate_job_budget(job)
    return dict(job)


def validate_job_budget(job: Mapping[str, Any]) -> dict[str, Any]:
    for key, expected in EXPECTED_BUDGET.items():
        if _required(job, key, "job") != expected:
            raise F4ManifestContractError(f"F4 V2 budget changed: {key}")
    derivation = _required(job, "planner_budget_derivation", "job")
    if derivation != {
        "canonical_prefix": 10,
        "suffix_target_construction_per_program": 12,
        "suffix_control_chain_per_program": 30,
        "program_count": 3,
        "total": 136,
    }:
        raise F4ManifestContractError("F4 10 + 3*(12+30) derivation changed")
    return {"budget": dict(EXPECTED_BUDGET), "derivation": dict(derivation), "pass": True}


def validate_bound_sources(value: Mapping[str, Any], job: Mapping[str, Any]) -> dict[str, Any]:
    contract = _bound_file(
        value, "manifest_contract_path", "manifest_contract_sha256", "manifest contract"
    )
    guard = _bound_file(value, "guard_script_path", "guard_script_sha256", "Guard")
    runner = _bound_file(value, "runner_script_path", "runner_script_sha256", "runner")
    lifecycle = _bound_file(
        value, "lifecycle_preflight_path", "lifecycle_preflight_sha256", "lifecycle preflight"
    )
    plan = _bound_file(value, "execution_plan_path", "execution_plan_file_sha256", "execution plan")
    if file_sha(plan) != PLAN_SHA256:
        raise F4ManifestContractError("two-part execution plan changed")
    if _required(value, "implementation_source_sha256", "manifest") != EXPECTED_CONTROLLED_SOURCE_SHA256:
        raise F4ManifestContractError("controlled source binding changed")
    if python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_CONTROLLED_SOURCE_SHA256:
        raise F4ManifestContractError("active controlled source differs from freeze")
    source = PROJECT / "controlled_multi_future/f4_full_program_physical_v1.py"
    if (
        _required(value, "f4_source_sha256", "manifest") != EXPECTED_F4_SOURCE_SHA256
        or file_sha(source) != EXPECTED_F4_SOURCE_SHA256
    ):
        raise F4ManifestContractError("F4 operational source changed")
    if _required(value, "robotwin_tracked_head", "manifest") != EXPECTED_ROBOTWIN_HEAD:
        raise F4ManifestContractError("RoboTwin tracked HEAD binding changed")
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
        raise F4ManifestContractError("official RoboTwin tracked worktree changed")
    assets = _required(value, "asset_hashes_by_family", "manifest")
    if set(assets) != {"F4"} or not assets["F4"]:
        raise F4ManifestContractError("F4 asset map is missing")
    for relative, expected in assets["F4"].items():
        asset = PROJECT / relative
        if not asset.is_file() or file_sha(asset) != expected:
            raise F4ManifestContractError(f"F4 asset hash mismatch: {relative}")
    template = _workspace_path(
        _required(job, "template_gate_terminal_path", "job"),
        "Run9 template terminal",
        file=True,
    )
    if file_sha(template) != _required(job, "template_gate_terminal_file_sha256", "job"):
        raise F4ManifestContractError("Run9 template terminal file changed")
    template_value = _self_hashed_file(template, "receipt_sha256", "Run9 template terminal")
    if (
        template_value.get("receipt_sha256")
        != _required(job, "template_gate_receipt_sha256", "job")
        or template_value.get("status") != "F4_FULL_PROGRAM_TEMPLATE_QUALIFICATION_PASS"
        or template_value.get("terminal_matrix", {}).get("full_program_pass") is not True
    ):
        raise F4ManifestContractError("Run9 full-program qualification changed")
    isolation = _workspace_path(
        _required(job, "isolation_gate_terminal_path", "job"),
        "Run2 isolation terminal",
        file=True,
    )
    if file_sha(isolation) != _required(job, "isolation_gate_terminal_file_sha256", "job"):
        raise F4ManifestContractError("Run2 isolation terminal file changed")
    isolation_value = _self_hashed_file(isolation, "receipt_sha256", "Run2 isolation terminal")
    if (
        isolation_value.get("receipt_sha256")
        != _required(job, "isolation_gate_receipt_sha256", "job")
        or isolation_value.get("F4", {}).get("all_five_isolation_stages_pass") is not True
    ):
        raise F4ManifestContractError("Run2 F4 isolation 5/5 evidence changed")
    history = _required(value, "historical_terminal_files", "manifest")
    if set(history) != set(EXPECTED_HISTORICAL_STATUSES):
        raise F4ManifestContractError("Run10-Run14 historical terminal set changed")
    historical_receipts = {}
    for run, expected_status in EXPECTED_HISTORICAL_STATUSES.items():
        record = history[run]
        path = _workspace_path(record.get("path"), f"{run} terminal", file=True)
        if file_sha(path) != record.get("file_sha256"):
            raise F4ManifestContractError(f"{run} terminal file changed")
        terminal_value = _self_hashed_file(path, "receipt_sha256", f"{run} terminal")
        if (
            terminal_value.get("receipt_sha256") != record.get("receipt_sha256")
            or terminal_value.get("status") != expected_status
        ):
            raise F4ManifestContractError(f"{run} terminal status/receipt changed")
        historical_receipts[run] = terminal_value["receipt_sha256"]
    terminals = _required(job, "source_planner_terminals", "job")
    if set(terminals) != set(EXPECTED_PROGRAMS):
        raise F4ManifestContractError("F4 planner terminal program set changed")
    terminal_receipts = {}
    for program_id in EXPECTED_PROGRAMS:
        record = terminals[program_id]
        path = _workspace_path(record.get("path"), f"{program_id} planner terminal", file=True)
        if file_sha(path) != record.get("file_sha256"):
            raise F4ManifestContractError(f"{program_id} planner terminal file changed")
        envelope = json.loads(path.read_text(encoding="utf-8"))
        terminal = envelope.get("terminal")
        if not isinstance(terminal, Mapping):
            raise F4ManifestContractError(f"{program_id} planner terminal missing")
        payload = dict(terminal)
        digest = payload.pop("receipt_sha256", None)
        if digest != canonical_hash(payload):
            raise F4ManifestContractError(f"{program_id} planner terminal self-hash mismatch")
        if terminal.get("planner_query_accounting") != {
            "budget_exhaustion_is_infrastructure_error": True,
            "chain_queries": 30,
            "target_construction_queries": 12,
            "total_queries": 42,
            "total_query_limit": 42,
        }:
            raise F4ManifestContractError(
                f"{program_id} 12+30=42 planner accounting changed"
            )
        terminal_receipts[program_id] = digest
    return {
        "contract_path": str(contract),
        "guard_path": str(guard),
        "runner_path": str(runner),
        "lifecycle_path": str(lifecycle),
        "plan_path": str(plan),
        "planner_terminal_receipts": terminal_receipts,
        "historical_terminal_receipts": historical_receipts,
        "isolation_gate_receipt": isolation_value["receipt_sha256"],
        "pass": True,
    }


def validate_runtime_paths(
    value: Mapping[str, Any],
    job: Mapping[str, Any],
    *,
    phase: str,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if phase not in PHASES:
        raise F4ManifestContractError(f"unknown F4 runtime phase: {phase}")
    output = _workspace_path(_required(job, "output_namespace", "job"), "output")
    guard_dir = _workspace_path(_required(value, "guard_directory", "manifest"), "guard directory")
    cache_job = _workspace_path(_required(value, "cache_directory", "manifest"), "cache directory") / str(job["job_id"])
    start = guard_dir / f"{job['job_id']}.start.json"
    terminal = guard_dir / f"{job['job_id']}.terminal.json"
    stdout = guard_dir / f"{job['job_id']}.stdout.log"
    stderr = guard_dir / f"{job['job_id']}.stderr.log"
    if phase in {PREPUBLICATION, GUARD_ENTRY}:
        present = {
            "output": output.exists(),
            "guard_directory": guard_dir.exists(),
            "cache_job": cache_job.exists(),
        }
        if any(present.values()):
            raise F4ManifestContractError(f"{phase} requires absent runtime paths: {present}")
    elif phase == RUNNER_ENTRY:
        if output.exists():
            raise F4ManifestContractError("RUNNER_ENTRY requires absent output")
        for path, label in (
            (guard_dir, "guard directory"),
            (start, "Guard start receipt"),
            (stdout, "stdout log"),
            (stderr, "stderr log"),
            (cache_job, "cache job"),
        ):
            if not path.exists():
                raise F4ManifestContractError(f"RUNNER_ENTRY missing {label}")
        missing_cache = [name for name in EXPECTED_CACHE_SUBDIRS if not (cache_job / name).is_dir()]
        if missing_cache:
            raise F4ManifestContractError(f"RUNNER_ENTRY missing cache subdirs: {missing_cache}")
        start_value = _self_hashed_file(start, "receipt_sha256", "Guard start receipt")
        if (
            start_value.get("manifest_sha256") != value["manifest_sha256"]
            or start_value.get("job_id") != job["job_id"]
            or start_value.get("run_id") != value["run_id"]
        ):
            raise F4ManifestContractError("RUNNER_ENTRY Guard start receipt binding changed")
        env = dict(os.environ if environment is None else environment)
        if (
            not env.get("CUDA_VISIBLE_DEVICES")
            or env.get("CMF_GPU_GUARD_PHYSICAL_INDEX") is None
            or not env.get("CMF_GPU_LEASE_PATH")
            or Path(env.get("CMF_F4_GUARD_START_RECEIPT", "")).resolve() != start.resolve()
        ):
            raise F4ManifestContractError("RUNNER_ENTRY lease/UUID/start environment missing")
    else:
        if not terminal.is_file():
            raise F4ManifestContractError("POST_CHILD requires Guard terminal")
        guard_terminal = _self_hashed_file(terminal, "receipt_sha256", "Guard terminal")
        if (
            guard_terminal.get("manifest_sha256") != value["manifest_sha256"]
            or guard_terminal.get("job_id") != job["job_id"]
        ):
            raise F4ManifestContractError("POST_CHILD Guard terminal binding changed")
        if output.exists() and not (output / "job_terminal.json").is_file():
            raise F4ManifestContractError("POST_CHILD output started without job terminal")
        if not output.exists() and guard_terminal.get("child_exit_code") in (None, 0):
            raise F4ManifestContractError("POST_CHILD absent output lacks terminal child error")
    return {
        "phase": phase,
        "output": str(output),
        "guard_directory": str(guard_dir),
        "cache_job": str(cache_job),
        "start_receipt": str(start),
        "guard_terminal": str(terminal),
        "stdout_log": str(stdout),
        "stderr_log": str(stderr),
        "pass": True,
    }


def load_and_validate_manifest_job(
    manifest_path: Path,
    job_id: str,
    *,
    phase: str,
    require_execution_authorized: bool,
    allow_lifecycle_fixture: bool = False,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    path, value = read_manifest(manifest_path)
    job = validate_manifest_semantics(
        value,
        require_execution_authorized=require_execution_authorized,
        allow_lifecycle_fixture=allow_lifecycle_fixture,
    )
    if _required(job, "job_id", "job") != job_id:
        raise F4ManifestContractError("requested F4 job differs from manifest")
    sources = validate_bound_sources(value, job)
    paths = validate_runtime_paths(
        value, job, phase=phase, environment=environment
    )
    return {
        "manifest": value,
        "job": job,
        "manifest_path": str(path),
        "manifest_sha256": value["manifest_sha256"],
        "sources": sources,
        "paths": paths,
        "phase": phase,
        "execution_authorized": require_execution_authorized,
        "cpu_lifecycle_fixture": value.get("cpu_lifecycle_fixture") is True,
    }


__all__ = [
    "EXPECTED_BUDGET",
    "EXPECTED_CACHE_SUBDIRS",
    "F4ManifestContractError",
    "GUARD_ENTRY",
    "POST_CHILD",
    "PREPUBLICATION",
    "RUNNER_ENTRY",
    "canonical_hash",
    "file_sha",
    "load_and_validate_manifest_job",
    "python_tree_sha",
    "read_manifest",
    "validate_bound_sources",
    "validate_job_budget",
    "validate_manifest_semantics",
    "validate_runtime_paths",
]
