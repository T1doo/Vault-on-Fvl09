#!/usr/bin/env python3
"""Fail-closed Runtime V2.1 contract for one future F4 development root.

This module intentionally reuses only the immutable V2 source/history verifier.
It adds authority lineage, executable identity, exact child-environment binding,
and trustworthy post-child outcome validation.  It does not authorize a run.
"""

from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Mapping


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
VAULT = WORKSPACE / "Vault-on-Fvl09"
AUDIT = VAULT / "数据构造/实现审计"

V2_RUNTIME = AUDIT / "f4_development_root_runtime_v2"
V2_CONTRACT_PATH = V2_RUNTIME / "manifest_contract.py"
V2_CONTRACT_SHA256 = "64484a94d436e5c521975b8906c427965235865c278f16e7a935a63376f58bb9"

EXTERNAL_DECISION_PATH = AUDIT / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_20260904.md"
EXTERNAL_DECISION_FILE_SHA256 = "790fc6e3e48694d212bb1c1a8833d270f2dc0dbe4748a605f319003787fd0dcd"
EXTERNAL_DECISION_RECEIPT_PATH = AUDIT / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_RECEIPT_20260904.json"
EXTERNAL_DECISION_RECEIPT_FILE_SHA256 = "bcd64b8e013893707565b63a312ce396b1acdad3d502f0c9fdaf37fbd951401a"
EXTERNAL_DECISION_RECEIPT_SHA256 = "c8ff692590d7cdb63995c9ce6932d851c1ef918fb5a8e8003881d2035eca7c35"

SOURCE_PROPOSAL_PATH = AUDIT / "PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_MANIFEST_V1.json"
SOURCE_PROPOSAL_FILE_SHA256 = "227cb378f662885a3151182756fdccdd21b2c966e75846641d32cb5a6e9afe94"
SOURCE_PROPOSAL_MANIFEST_SHA256 = "8afaf49a83aaaedc9473cd20866ad06e2b18e1f8adfcd1e6747baa401ce0a4f5"

SOURCE_CPU_REVIEW_PATH = AUDIT / "F4_DEVELOPMENT_ROOT_RUNTIME_V2_CPU_REVIEW.json"
SOURCE_CPU_REVIEW_FILE_SHA256 = "0a249108d6a3871c5d5f72831857d78d34a1ae6979715dc8ef34783ea16292f9"
SOURCE_CPU_REVIEW_RECEIPT_SHA256 = "27685393a762a0ab12ad332dc717dd4b80b0fd16e328484374d712ca803e180a"

SOURCE_LIFECYCLE_RECEIPT_PATH = AUDIT / "F4_DEVELOPMENT_ROOT_RUNTIME_V2_LIFECYCLE_PREFLIGHT.json"
SOURCE_LIFECYCLE_RECEIPT_FILE_SHA256 = "33f2bc3f9036fe602d48fcc8acf3927018cec7c41923aae9ae1cbd95be058b01"
SOURCE_LIFECYCLE_RECEIPT_SHA256 = "3df1f4c21fec4c1b7f304c8a0f08351179f0eaf1dad2039e699be02547d3a3ba"

EXPECTED_PROGRAMS = ["F4-ABC", "F4-ACB", "F4-BAC"]
EXPECTED_CANDIDATE_ID = "f4-slot-corridor-hv2-r01"
EXPECTED_CANDIDATE_SHA256 = "981d7a2ecf791b3d5545aa0ca136105e5f8e41ba4523333370de87ed5dffb2df"
EXPECTED_DRY_CANDIDATE_FREEZE_SHA256 = "812a90425662352ccb4f0402549aea9a879ddf17a8d189e0464a772d021bfed6"
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
EXPECTED_CACHE_ENV = {
    "CONDA_PKGS_DIRS": "conda_pkgs",
    "CUDA_CACHE_PATH": "cuda",
    "HOME": "home",
    "MPLCONFIGDIR": "matplotlib",
    "NUMBA_CACHE_DIR": "numba",
    "TMPDIR": "tmp",
    "TORCH_EXTENSIONS_DIR": "torch_extensions",
    "TORCH_HOME": "torch",
    "XDG_CACHE_HOME": "xdg",
}
EXPECTED_CACHE_SUBDIRS = tuple(EXPECTED_CACHE_ENV.values())
EXPECTED_CUDA_HOME = WORKSPACE / "Robotwin2/tools/cuda-12.1"
EXPECTED_PYTHONPATH = PROJECT

PREPUBLICATION = "PREPUBLICATION"
GUARD_ENTRY = "GUARD_ENTRY"
RUNNER_ENTRY = "RUNNER_ENTRY"
POST_CHILD = "POST_CHILD"
PHASES = {PREPUBLICATION, GUARD_ENTRY, RUNNER_ENTRY, POST_CHILD}


class F4ManifestContractError(RuntimeError):
    """Raised when any authority, identity, lifecycle, or outcome check fails."""


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


def _load_v2_contract():
    if file_sha(V2_CONTRACT_PATH) != V2_CONTRACT_SHA256:
        raise F4ManifestContractError("sealed Runtime V2 contract changed")
    spec = importlib.util.spec_from_file_location(
        "cmf_f4_runtime_v2_sealed_contract", V2_CONTRACT_PATH
    )
    if spec is None or spec.loader is None:
        raise F4ManifestContractError("cannot load sealed Runtime V2 contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V2 = _load_v2_contract()


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


def _self_hashed_json(path: Path, key: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except BaseException as exc:
        raise F4ManifestContractError(f"{label} is not valid JSON") from exc
    if not isinstance(value, Mapping):
        raise F4ManifestContractError(f"{label} must be a mapping")
    payload = dict(value)
    digest = payload.pop(key, None)
    if digest != canonical_hash(payload):
        raise F4ManifestContractError(f"{label} self-hash mismatch")
    return dict(value)


def _exact_path_and_sha(
    value: Mapping[str, Any],
    *,
    path_key: str,
    sha_key: str,
    expected_path: Path,
    expected_sha: str,
    label: str,
) -> Path:
    path = _workspace_path(_required(value, path_key, "manifest"), label, file=True)
    if path != expected_path.resolve():
        raise F4ManifestContractError(f"{label} path changed")
    claimed = str(_required(value, sha_key, "manifest"))
    if claimed != expected_sha or file_sha(path) != expected_sha:
        raise F4ManifestContractError(f"{label} SHA-256 mismatch")
    return path


def read_manifest(path: Path) -> tuple[Path, dict[str, Any]]:
    resolved = _workspace_path(path, "manifest", file=True)
    value = _self_hashed_json(resolved, "manifest_sha256", "manifest")
    return resolved, value


def validate_job_budget(job: Mapping[str, Any]) -> dict[str, Any]:
    for key, expected in EXPECTED_BUDGET.items():
        if _required(job, key, "job") != expected:
            raise F4ManifestContractError(f"F4 V2.1 budget changed: {key}")
    derivation = _required(job, "planner_budget_derivation", "job")
    expected_derivation = {
        "canonical_prefix": 10,
        "suffix_target_construction_per_program": 12,
        "suffix_control_chain_per_program": 30,
        "program_count": 3,
        "total": 136,
    }
    if derivation != expected_derivation:
        raise F4ManifestContractError("F4 10 + 3*(12+30) derivation changed")
    return {"budget": dict(EXPECTED_BUDGET), "derivation": dict(derivation), "pass": True}


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
        "APPROVED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2"
        if require_execution_authorized
        else "PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2"
    )
    if _required(value, "status", "manifest") != expected_status:
        raise F4ManifestContractError("F4 V2.1 manifest status differs from authority")
    for key in ("approved", "gpu_execution_authorized", "planner_execution_authorized", "scene_execution_authorized", "physical_execution_authorized", "root_execution_authorized"):
        if _required(value, key, "manifest") is not bool(require_execution_authorized):
            raise F4ManifestContractError(f"manifest {key} authority mismatch")
    if _required(value, "cpu_infrastructure_repair_authorized", "manifest") is not True:
        raise F4ManifestContractError("F4 CPU final hardening is not authorized")
    if _required(value, "scientific_status", "manifest") != "PHYSICALLY_QUALIFIED":
        raise F4ManifestContractError("F4 scientific status changed")
    if _required(value, "root_status", "manifest") != ("ONE_DEVELOPMENT_ROOT_AUTHORIZED" if require_execution_authorized else "CPU_HARDENING_COMPLETE_AWAITING_EXTERNAL_APPROVAL"):
        raise F4ManifestContractError("F4 V2.1 root status changed")
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
    for legacy in (
        "third_reopening_authorized",
        "third_reopen_authorized",
        "reopen_ordinal_after_run14",
    ):
        if legacy in value:
            raise F4ManifestContractError(f"legacy reopen field forbidden: {legacy}")
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
    if _required(job, "mode", "job") != "ONE_F4_DEVELOPMENT_R_PC_ROOT_V2_1":
        raise F4ManifestContractError("F4 V2.1 dispatch mode changed")
    if _required(job, "candidate_id", "job") != EXPECTED_CANDIDATE_ID:
        raise F4ManifestContractError("F4 candidate changed")
    if _required(job, "candidate_sha256", "job") != EXPECTED_CANDIDATE_SHA256:
        raise F4ManifestContractError("F4 candidate SHA changed")
    if _required(job, "dry_candidate_frozen_spec_sha256", "job") != EXPECTED_DRY_CANDIDATE_FREEZE_SHA256:
        raise F4ManifestContractError("F4 dry candidate freeze changed")
    if _required(job, "program_order", "job") != EXPECTED_PROGRAMS:
        raise F4ManifestContractError("F4 program order changed")
    if _required(job, "fixed_arm_schedule", "job") != {
        "canonical_prefix": "right",
        "program_suffix": "left",
    }:
        raise F4ManifestContractError("F4 fixed arm schedule changed")
    for key in (
        "automatic_retry",
        "fallback_allowed",
        "candidate_search_allowed",
        "seed_retry_allowed",
        "second_root_allowed",
    ):
        if _required(job, key, "job") is not False:
            raise F4ManifestContractError(f"forbidden F4 behavior enabled: {key}")
    validate_job_budget(job)
    return dict(job)


def _validate_lineage(value: Mapping[str, Any], *, execution_authorized: bool, fixture: bool) -> dict[str, Any]:
    decision = _exact_path_and_sha(
        value,
        path_key="external_review_decision_path",
        sha_key="external_review_decision_file_sha256",
        expected_path=EXTERNAL_DECISION_PATH,
        expected_sha=EXTERNAL_DECISION_FILE_SHA256,
        label="Runtime V2.1 external review decision",
    )
    decision_receipt = _exact_path_and_sha(
        value,
        path_key="external_review_decision_receipt_path",
        sha_key="external_review_decision_receipt_file_sha256",
        expected_path=EXTERNAL_DECISION_RECEIPT_PATH,
        expected_sha=EXTERNAL_DECISION_RECEIPT_FILE_SHA256,
        label="Runtime V2.1 external review decision receipt",
    )
    decision_value = _self_hashed_json(decision_receipt, "receipt_sha256", "external review decision receipt")
    if (
        _required(value, "external_review_decision_receipt_sha256", "manifest")
        != EXTERNAL_DECISION_RECEIPT_SHA256
        or decision_value.get("receipt_sha256") != EXTERNAL_DECISION_RECEIPT_SHA256
        or decision_value.get("authoritative_message", {}).get("file_sha256")
        != EXTERNAL_DECISION_FILE_SHA256
        or decision_value.get("decision_summary", {}).get("F4")
        != "REVISE_TO_NEW_CPU_ONLY_RUNTIME_V2_1_THEN_NEW_EXTERNAL_REVIEW"
    ):
        raise F4ManifestContractError("Runtime V2.1 external decision receipt changed")

    proposal = _exact_path_and_sha(
        value,
        path_key="source_proposal_manifest_path",
        sha_key="source_proposal_manifest_file_sha256",
        expected_path=SOURCE_PROPOSAL_PATH,
        expected_sha=SOURCE_PROPOSAL_FILE_SHA256,
        label="Runtime V2 source proposal",
    )
    proposal_value = _self_hashed_json(proposal, "manifest_sha256", "Runtime V2 source proposal")
    if (
        _required(value, "source_proposal_manifest_sha256", "manifest")
        != SOURCE_PROPOSAL_MANIFEST_SHA256
        or proposal_value.get("manifest_sha256") != SOURCE_PROPOSAL_MANIFEST_SHA256
        or proposal_value.get("approved") is not False
    ):
        raise F4ManifestContractError("Runtime V2 source proposal binding changed")

    cpu_review = _exact_path_and_sha(
        value,
        path_key="source_cpu_review_path",
        sha_key="source_cpu_review_file_sha256",
        expected_path=SOURCE_CPU_REVIEW_PATH,
        expected_sha=SOURCE_CPU_REVIEW_FILE_SHA256,
        label="Runtime V2 CPU review",
    )
    cpu_review_value = _self_hashed_json(cpu_review, "receipt_sha256", "Runtime V2 CPU review")
    if (
        _required(value, "source_cpu_review_receipt_sha256", "manifest")
        != SOURCE_CPU_REVIEW_RECEIPT_SHA256
        or cpu_review_value.get("receipt_sha256") != SOURCE_CPU_REVIEW_RECEIPT_SHA256
        or cpu_review_value.get("cpu_review_status") != "PASS_READY_FOR_EXTERNAL_REVIEW"
    ):
        raise F4ManifestContractError("Runtime V2 CPU review binding changed")

    lifecycle = _exact_path_and_sha(
        value,
        path_key="source_lifecycle_receipt_path",
        sha_key="source_lifecycle_receipt_file_sha256",
        expected_path=SOURCE_LIFECYCLE_RECEIPT_PATH,
        expected_sha=SOURCE_LIFECYCLE_RECEIPT_FILE_SHA256,
        label="Runtime V2 lifecycle receipt",
    )
    lifecycle_value = _self_hashed_json(lifecycle, "receipt_sha256", "Runtime V2 lifecycle receipt")
    if (
        _required(value, "source_lifecycle_receipt_sha256", "manifest")
        != SOURCE_LIFECYCLE_RECEIPT_SHA256
        or lifecycle_value.get("receipt_sha256") != SOURCE_LIFECYCLE_RECEIPT_SHA256
        or lifecycle_value.get("pass") is not True
    ):
        raise F4ManifestContractError("Runtime V2 lifecycle receipt binding changed")

    hardening_test_bound = False
    if not fixture:
        hardening_test_path = _workspace_path(
            _required(value, "v2_1_hardening_test_receipt_path", "manifest"),
            "Runtime V2.1 hardening test receipt",
            file=True,
        )
        if file_sha(hardening_test_path) != _required(
            value, "v2_1_hardening_test_receipt_file_sha256", "manifest"
        ):
            raise F4ManifestContractError("Runtime V2.1 hardening test file SHA mismatch")
        hardening_test = _self_hashed_json(
            hardening_test_path,
            "receipt_sha256",
            "Runtime V2.1 hardening test receipt",
        )
        if (
            hardening_test.get("receipt_sha256")
            != _required(value, "v2_1_hardening_test_receipt_sha256", "manifest")
            or hardening_test.get("pass") is not True
            or hardening_test.get("runtime_files")
            != {
                "manifest_contract.py": value["manifest_contract_sha256"],
                "guarded_launcher.py": value["guard_script_sha256"],
                "job_runner.py": value["runner_script_sha256"],
                "lifecycle_preflight.py": value["lifecycle_preflight_sha256"],
            }
        ):
            raise F4ManifestContractError("Runtime V2.1 hardening test binding changed")
        hardening_test_bound = True

    approval_bound = False
    if execution_authorized and not fixture:
        approval_path = _workspace_path(
            _required(value, "root_execution_approval_decision_path", "manifest"),
            "F4 root execution approval decision",
            file=True,
        )
        if file_sha(approval_path) != _required(
            value, "root_execution_approval_decision_file_sha256", "manifest"
        ):
            raise F4ManifestContractError("F4 root execution approval decision SHA mismatch")
        approval_receipt_path = _workspace_path(
            _required(value, "root_execution_approval_receipt_path", "manifest"),
            "F4 root execution approval receipt",
            file=True,
        )
        if file_sha(approval_receipt_path) != _required(
            value, "root_execution_approval_receipt_file_sha256", "manifest"
        ):
            raise F4ManifestContractError("F4 root execution approval receipt file SHA mismatch")
        approval_receipt = _self_hashed_json(
            approval_receipt_path, "receipt_sha256", "F4 root execution approval receipt"
        )
        if (
            approval_receipt.get("receipt_sha256")
            != _required(value, "root_execution_approval_receipt_sha256", "manifest")
            or approval_receipt.get("authoritative_message", {}).get("file_sha256")
            != file_sha(approval_path)
            or not exact_root_decision(approval_receipt)
        ):
            raise F4ManifestContractError("F4 root execution approval is not exact")
        approval_bound = True
    elif not execution_authorized:
        forbidden = [key for key in value if key.startswith("root_execution_approval_")]
        if forbidden:
            raise F4ManifestContractError("proposal must not claim a root execution approval")

    return {
        "external_decision_path": str(decision),
        "external_decision_receipt": decision_value["receipt_sha256"],
        "source_proposal_path": str(proposal),
        "source_proposal_manifest": proposal_value["manifest_sha256"],
        "source_cpu_review_path": str(cpu_review),
        "source_cpu_review_receipt": cpu_review_value["receipt_sha256"],
        "source_lifecycle_path": str(lifecycle),
        "source_lifecycle_receipt": lifecycle_value["receipt_sha256"],
        "v2_1_hardening_test_bound": hardening_test_bound,
        "root_execution_approval_bound": approval_bound,
        "pass": True,
    }


def validate_executable_identity(
    value: Mapping[str, Any], *, role: str, executable_path: Path
) -> dict[str, Any]:
    keys = {
        "contract": ("manifest_contract_path", "manifest_contract_sha256"),
        "guard": ("guard_script_path", "guard_script_sha256"),
        "runner": ("runner_script_path", "runner_script_sha256"),
        "lifecycle": ("lifecycle_preflight_path", "lifecycle_preflight_sha256"),
    }
    if role not in keys:
        raise F4ManifestContractError(f"unknown executable identity role: {role}")
    path_key, sha_key = keys[role]
    bound = _workspace_path(_required(value, path_key, "manifest"), role, file=True)
    actual = Path(executable_path).resolve()
    if actual != bound:
        raise F4ManifestContractError(f"{role} __file__ path differs from manifest")
    if file_sha(actual) != _required(value, sha_key, "manifest"):
        raise F4ManifestContractError(f"{role} __file__ SHA differs from manifest")
    return {"role": role, "path": str(actual), "sha256": file_sha(actual), "pass": True}


def validate_bound_sources(
    value: Mapping[str, Any],
    job: Mapping[str, Any],
    *,
    execution_authorized: bool,
    fixture: bool,
) -> dict[str, Any]:
    # V2 remains the immutable source/history/asset/planner-terminal verifier.
    try:
        sources = V2.validate_bound_sources(value, job)
    except BaseException as exc:
        raise F4ManifestContractError(f"sealed Runtime V2 source validation failed: {exc}") from exc
    contract_identity = validate_executable_identity(
        value, role="contract", executable_path=Path(__file__)
    )
    lineage = _validate_lineage(
        value, execution_authorized=execution_authorized, fixture=fixture
    )
    return {**sources, "contract_identity": contract_identity, "authority_lineage": lineage}


def _runtime_paths(value: Mapping[str, Any], job: Mapping[str, Any]) -> dict[str, Path]:
    output = _workspace_path(_required(job, "output_namespace", "job"), "output")
    guard_dir = _workspace_path(_required(value, "guard_directory", "manifest"), "guard directory")
    cache_job = _workspace_path(_required(value, "cache_directory", "manifest"), "cache directory") / str(job["job_id"])
    return {
        "output": output,
        "guard_directory": guard_dir,
        "cache_job": cache_job,
        "start_receipt": guard_dir / f"{job['job_id']}.start.json",
        "guard_terminal": guard_dir / f"{job['job_id']}.terminal.json",
        "stdout_log": guard_dir / f"{job['job_id']}.stdout.log",
        "stderr_log": guard_dir / f"{job['job_id']}.stderr.log",
    }



def exact_root_decision(receipt):
    expected = {
        "schema_version": "cmf_external_execution_decision_v1",
        "decision": "F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2",
        "authorized": True,
        "candidate": "f4-slot-corridor-hv2-r01",
        "programs": ["F4-ABC", "F4-ACB", "F4-BAC"],
        "maximum_root_invocations": 1,
        "maximum_accepted_development_roots": 1,
        "maximum_accepted_development_trajectories": 3,
        "maximum_formal_trajectories": 0,
    }
    return all(type(receipt.get(k)) is type(v) and receipt.get(k) == v for k, v in expected.items())


def require_held_lease(path):
    with Path(path).open("r+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            raise F4ManifestContractError("Guard lease is not exclusively held")


def _validate_runner_entry(
    value: Mapping[str, Any],
    job: Mapping[str, Any],
    paths: Mapping[str, Path],
    environment: Mapping[str, str],
) -> dict[str, Any]:
    if paths["output"].exists():
        raise F4ManifestContractError("RUNNER_ENTRY requires absent output")
    for key, label in (
        ("guard_directory", "guard directory"),
        ("start_receipt", "Guard start receipt"),
        ("stdout_log", "stdout log"),
        ("stderr_log", "stderr log"),
        ("cache_job", "cache job"),
    ):
        if not paths[key].exists():
            raise F4ManifestContractError(f"RUNNER_ENTRY missing {label}")
    missing_cache = [
        relative
        for relative in EXPECTED_CACHE_SUBDIRS
        if not (paths["cache_job"] / relative).is_dir()
    ]
    if missing_cache:
        raise F4ManifestContractError(f"RUNNER_ENTRY missing cache subdirs: {missing_cache}")
    start = _self_hashed_json(paths["start_receipt"], "receipt_sha256", "Guard start receipt")
    if (
        start.get("schema_version") != "cmf_f4_development_root_v2_1_guard_start_v1"
        or start.get("family") != "F4"
        or start.get("run_id") != value["run_id"]
        or start.get("job_id") != job["job_id"]
        or start.get("manifest_sha256") != value["manifest_sha256"]
    ):
        raise F4ManifestContractError("RUNNER_ENTRY start schema/family/run/job/manifest mismatch")
    try:
        physical_index = int(start["physical_gpu_index"])
    except (KeyError, TypeError, ValueError) as exc:
        raise F4ManifestContractError("RUNNER_ENTRY start GPU index invalid") from exc
    if physical_index not in value["allowed_physical_gpu_indices"]:
        raise F4ManifestContractError("RUNNER_ENTRY start GPU index outside authority")
    uuid = start.get("gpu_uuid")
    if not isinstance(uuid, str) or not uuid.startswith("GPU-") or "," in uuid:
        raise F4ManifestContractError("RUNNER_ENTRY start GPU UUID invalid")
    lease = _workspace_path(start.get("lease_path"), "RUNNER_ENTRY lease", file=True)
    require_held_lease(lease)
    env = dict(environment)
    if "LD_LIBRARY_PATH" in env:
        raise F4ManifestContractError("RUNNER_ENTRY requires LD_LIBRARY_PATH absent")
    if env.get("CUDA_VISIBLE_DEVICES") != uuid or "," in env.get("CUDA_VISIBLE_DEVICES", ""):
        raise F4ManifestContractError("RUNNER_ENTRY CUDA_VISIBLE_DEVICES is not one bound UUID")
    if env.get("CMF_GPU_GUARD_PHYSICAL_INDEX") != str(physical_index):
        raise F4ManifestContractError("RUNNER_ENTRY GPU index environment mismatch")
    if Path(env.get("CMF_GPU_LEASE_PATH", "")).resolve() != lease:
        raise F4ManifestContractError("RUNNER_ENTRY lease environment mismatch")
    if Path(env.get("CMF_F4_GUARD_START_RECEIPT", "")).resolve() != paths["start_receipt"].resolve():
        raise F4ManifestContractError("RUNNER_ENTRY start receipt environment mismatch")
    if Path(env.get("CUDA_HOME", "")).resolve() != EXPECTED_CUDA_HOME.resolve():
        raise F4ManifestContractError("RUNNER_ENTRY CUDA_HOME mismatch")
    if Path(env.get("PYTHONPATH", "")).resolve() != EXPECTED_PYTHONPATH.resolve():
        raise F4ManifestContractError("RUNNER_ENTRY PYTHONPATH mismatch")
    if env.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise F4ManifestContractError("RUNNER_ENTRY PYTHONDONTWRITEBYTECODE mismatch")
    cache_bindings = {}
    for name, relative in EXPECTED_CACHE_ENV.items():
        expected = (paths["cache_job"] / relative).resolve()
        actual = Path(env.get(name, "")).resolve()
        if actual != expected or not expected.is_dir():
            raise F4ManifestContractError(f"RUNNER_ENTRY cache environment mismatch: {name}")
        cache_bindings[name] = str(expected)
    return {
        "start_receipt_sha256": start["receipt_sha256"],
        "family": "F4",
        "physical_gpu_index": physical_index,
        "gpu_uuid": uuid,
        "lease_path": str(lease),
        "cache_environment": cache_bindings,
        "cuda_home": str(EXPECTED_CUDA_HOME),
        "pythonpath": str(EXPECTED_PYTHONPATH),
        "pass": True,
    }


def _self_hash_mapping(value: Mapping[str, Any], key: str, label: str) -> None:
    payload = dict(value)
    digest = payload.pop(key, None)
    if digest != canonical_hash(payload):
        raise F4ManifestContractError(f"{label} self-hash mismatch")


def validate_post_child_records(
    value: Mapping[str, Any],
    job: Mapping[str, Any],
    guard_terminal: Mapping[str, Any],
    job_terminal: Mapping[str, Any],
) -> dict[str, Any]:
    _self_hash_mapping(guard_terminal, "receipt_sha256", "Guard terminal")
    _self_hash_mapping(job_terminal, "receipt_sha256", "job terminal")
    for record, label, schema in (
        (guard_terminal, "Guard terminal", "cmf_f4_development_root_v2_1_guard_terminal_v1"),
        (job_terminal, "job terminal", "cmf_f4_development_root_v2_1_job_terminal_v1"),
    ):
        if (
            record.get("schema_version") != schema
            or record.get("family") != "F4"
            or record.get("run_id") != value["run_id"]
            or record.get("job_id") != job["job_id"]
            or record.get("manifest_sha256") != value["manifest_sha256"]
        ):
            raise F4ManifestContractError(f"POST_CHILD {label} binding mismatch")
    finalizer = job_terminal.get("root_finalizer")
    if not isinstance(finalizer, Mapping):
        raise F4ManifestContractError("POST_CHILD job terminal lacks root finalizer")
    _self_hash_mapping(finalizer, "receipt_sha256", "root finalizer")
    finalizer_checks = finalizer.get("checks")
    if not isinstance(finalizer_checks, Mapping) or not finalizer_checks:
        raise F4ManifestContractError("POST_CHILD root finalizer checks are missing")
    exit_zero = guard_terminal.get("child_exit_code") == 0
    job_pass = job_terminal.get("pass") is True
    finalizer_accepted = finalizer.get("accepted") is True
    checks_all_true = all(item is True for item in finalizer_checks.values())
    if finalizer_accepted != checks_all_true:
        raise F4ManifestContractError("POST_CHILD finalizer accepted/checks mismatch")
    if finalizer_accepted != (finalizer.get("failure") is None):
        raise F4ManifestContractError("POST_CHILD finalizer accepted/failure mismatch")
    if not (exit_zero == job_pass == finalizer_accepted):
        raise F4ManifestContractError("POST_CHILD exit/pass/finalizer equivalence failed")
    counts = finalizer.get("counts") if isinstance(finalizer.get("counts"), Mapping) else {}
    expected_roots = 1 if finalizer_accepted else 0
    expected_trajectories = 3 if finalizer_accepted else 0
    if (
        counts.get("accepted_development_roots") != expected_roots
        or counts.get("accepted_development_trajectories") != expected_trajectories
        or counts.get("formal_trajectories") != 0
        or job_terminal.get("accepted_development_root_count") != expected_roots
        or job_terminal.get("accepted_development_trajectory_count") != expected_trajectories
    ):
        raise F4ManifestContractError("POST_CHILD accepted 1/3 counts mismatch")
    result = job_terminal.get("result")
    if finalizer_accepted and (
        not isinstance(result, Mapping)
        or result.get("development_root_pass") is not True
        or result.get("development_accepted_root_count") != 1
        or result.get("development_accepted_trajectory_count") != 3
        or job_terminal.get("error") is not None
    ):
        raise F4ManifestContractError("POST_CHILD accepted result/error mismatch")
    if (
        guard_terminal.get("physical_gpu_index")
        != job_terminal.get("physical_gpu_index")
        or guard_terminal.get("gpu_uuid") != job_terminal.get("gpu_uuid")
    ):
        raise F4ManifestContractError("POST_CHILD Guard/job GPU identity mismatch")
    cleanup_pass = (
        guard_terminal.get("cache_removed") is True
        and guard_terminal.get("lease_released") is True
        and guard_terminal.get("gpu_returned_to_idle_baseline") is True
        and guard_terminal.get("task_owned_cleanup_pass") is True
        and guard_terminal.get("cleanup_errors") == []
    )
    if not cleanup_pass:
        raise F4ManifestContractError("POST_CHILD Guard cleanup/baseline failed")
    expected_status = "completed" if finalizer_accepted else "failed_or_blocked_with_cleanup_evidence"
    if guard_terminal.get("status") != expected_status:
        raise F4ManifestContractError("POST_CHILD Guard status disagrees with child outcome")
    if guard_terminal.get("output_exists") is not True:
        raise F4ManifestContractError("POST_CHILD Guard did not observe output")
    return {
        "child_exit_zero": exit_zero,
        "job_terminal_pass": job_pass,
        "root_finalizer_accepted": finalizer_accepted,
        "accepted_development_roots": expected_roots,
        "accepted_development_trajectories": expected_trajectories,
        "guard_cleanup_pass": cleanup_pass,
        "gpu_returned_to_idle_baseline": True,
        "job_succeeded": finalizer_accepted,
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
    paths = _runtime_paths(value, job)
    outcome = None
    if phase in {PREPUBLICATION, GUARD_ENTRY}:
        present = {
            key: paths[key].exists()
            for key in ("output", "guard_directory", "cache_job")
        }
        if any(present.values()):
            raise F4ManifestContractError(f"{phase} requires absent runtime paths: {present}")
    elif phase == RUNNER_ENTRY:
        outcome = _validate_runner_entry(
            value, job, paths, dict(os.environ if environment is None else environment)
        )
    else:
        for key, label in (
            ("guard_terminal", "Guard terminal"),
            ("stdout_log", "stdout log"),
            ("stderr_log", "stderr log"),
        ):
            if not paths[key].is_file():
                raise F4ManifestContractError(f"POST_CHILD missing {label}")
        if not paths["output"].is_dir():
            raise F4ManifestContractError("POST_CHILD requires runner output directory")
        job_terminal_path = paths["output"] / "job_terminal.json"
        if not job_terminal_path.is_file():
            raise F4ManifestContractError("POST_CHILD requires job terminal")
        guard_terminal = json.loads(paths["guard_terminal"].read_text(encoding="utf-8"))
        job_terminal = json.loads(job_terminal_path.read_text(encoding="utf-8"))
        outcome = validate_post_child_records(value, job, guard_terminal, job_terminal)
    result = {key: str(path) for key, path in paths.items()}
    result.update({"phase": phase, "pass": True})
    if outcome is not None:
        result["phase_validation"] = outcome
    return result


def load_and_validate_manifest_job(
    manifest_path: Path,
    job_id: str,
    *,
    phase: str,
    require_execution_authorized: bool,
    allow_lifecycle_fixture: bool = False,
    environment: Mapping[str, str] | None = None,
    executable_role: str | None = None,
    executable_path: Path | None = None,
) -> dict[str, Any]:
    path, value = read_manifest(manifest_path)
    job = validate_manifest_semantics(
        value,
        require_execution_authorized=require_execution_authorized,
        allow_lifecycle_fixture=allow_lifecycle_fixture,
    )
    if _required(job, "job_id", "job") != job_id:
        raise F4ManifestContractError("requested F4 job differs from manifest")
    fixture = value.get("cpu_lifecycle_fixture") is True
    sources = validate_bound_sources(
        value,
        job,
        execution_authorized=require_execution_authorized,
        fixture=fixture,
    )
    identity = None
    if executable_role is not None or executable_path is not None:
        if executable_role is None or executable_path is None:
            raise F4ManifestContractError("incomplete executable identity request")
        identity = validate_executable_identity(
            value, role=executable_role, executable_path=executable_path
        )
    paths = validate_runtime_paths(value, job, phase=phase, environment=environment)
    return {
        "manifest": value,
        "job": job,
        "manifest_path": str(path),
        "manifest_sha256": value["manifest_sha256"],
        "sources": sources,
        "executable_identity": identity,
        "paths": paths,
        "phase": phase,
        "execution_authorized": require_execution_authorized,
        "cpu_lifecycle_fixture": fixture,
    }


__all__ = [
    "EXPECTED_BUDGET",
    "EXPECTED_CACHE_ENV",
    "EXPECTED_CACHE_SUBDIRS",
    "F4ManifestContractError",
    "GUARD_ENTRY",
    "POST_CHILD",
    "PREPUBLICATION",
    "RUNNER_ENTRY",
    "canonical_hash",
    "file_sha",
    "load_and_validate_manifest_job",
    "read_manifest",
    "validate_bound_sources",
    "validate_executable_identity",
    "validate_job_budget",
    "validate_manifest_semantics",
    "validate_post_child_records",
    "validate_runtime_paths",
]
