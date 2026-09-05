#!/usr/bin/env python3
"""Machine-reproducible CPU hardening suite for F4 Runtime V2.1.

The suite builds an execution-authorized *synthetic* lifecycle fixture, uses the
real manifest loader and runner-entry subprocess, and stops before a real GPU
lease, nvidia-smi, CUDA, scene, planner, or production output.  It then creates
isolated synthetic artifacts under a temporary workspace directory to exercise
the disk finalizer and POST_CHILD verifier, including corruption cases.
"""

from __future__ import annotations

import argparse
import fcntl
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping

import numpy as np


RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from manifest_contract import (  # noqa: E402
    EXPECTED_CACHE_ENV,
    EXPECTED_PROGRAMS,
    GUARD_ENTRY,
    POST_CHILD,
    PREPUBLICATION,
    RUNNER_ENTRY,
    canonical_hash,
    file_sha,
    load_and_validate_manifest_job,
    validate_runtime_paths,
)
import job_runner  # noqa: E402


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
AUDIT = WORKSPACE / "Vault-on-Fvl09/数据构造/实现审计"
ENV_PYTHON = WORKSPACE / "Robotwin2/env/bin/python"
SOURCE_PROPOSAL = AUDIT / "PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_MANIFEST_V1.json"
DECISION = AUDIT / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_20260904.md"
DECISION_RECEIPT = AUDIT / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_RECEIPT_20260904.json"
CPU_REVIEW = AUDIT / "F4_DEVELOPMENT_ROOT_RUNTIME_V2_CPU_REVIEW.json"
SOURCE_LIFECYCLE = AUDIT / "F4_DEVELOPMENT_ROOT_RUNTIME_V2_LIFECYCLE_PREFLIGHT.json"


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def overwrite(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def hashed(value: Mapping[str, Any], key: str = "receipt_sha256") -> dict[str, Any]:
    result = deepcopy(dict(value))
    result.pop(key, None)
    result[key] = canonical_hash(result)
    return result


def record_rejection(label: str, callback: Callable[[], Any], observed: list[dict[str, Any]]) -> None:
    try:
        callback()
    except BaseException as exc:
        observed.append(
            {
                "label": label,
                "rejected": True,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        return
    raise AssertionError(f"negative case unexpectedly passed: {label}")


def build_execution_authorized_fixture(temp_root: Path) -> tuple[Path, dict[str, Any]]:
    manifest = json.loads(SOURCE_PROPOSAL.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "cmf_f4_infrastructure_corrected_root_manifest_v2",
            "status": "APPROVED_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2",
            "approved": True,
            "gpu_execution_authorized": True,
            "physical_execution_authorized": True,
            "planner_execution_authorized": True,
            "scene_execution_authorized": True,
            "root_execution_authorized": True,
            "cpu_lifecycle_fixture": True,
            "root_status": "ONE_DEVELOPMENT_ROOT_AUTHORIZED",
            "run_id": "f4-v2-1-execution-authorized-cpu-lifecycle-fixture",
            "guard_directory": str(temp_root / "guards"),
            "cache_directory": str(temp_root / "cache"),
            "manifest_contract_path": str(RUNTIME / "manifest_contract.py"),
            "manifest_contract_sha256": file_sha(RUNTIME / "manifest_contract.py"),
            "guard_script_path": str(RUNTIME / "guarded_launcher.py"),
            "guard_script_sha256": file_sha(RUNTIME / "guarded_launcher.py"),
            "runner_script_path": str(RUNTIME / "job_runner.py"),
            "runner_script_sha256": file_sha(RUNTIME / "job_runner.py"),
            "lifecycle_preflight_path": str(Path(__file__).resolve()),
            "lifecycle_preflight_sha256": file_sha(Path(__file__).resolve()),
            "external_review_decision_path": str(DECISION),
            "external_review_decision_file_sha256": file_sha(DECISION),
            "external_review_decision_receipt_path": str(DECISION_RECEIPT),
            "external_review_decision_receipt_file_sha256": file_sha(DECISION_RECEIPT),
            "external_review_decision_receipt_sha256": "c8ff692590d7cdb63995c9ce6932d851c1ef918fb5a8e8003881d2035eca7c35",
            "source_proposal_manifest_path": str(SOURCE_PROPOSAL),
            "source_proposal_manifest_file_sha256": file_sha(SOURCE_PROPOSAL),
            "source_proposal_manifest_sha256": "8afaf49a83aaaedc9473cd20866ad06e2b18e1f8adfcd1e6747baa401ce0a4f5",
            "source_cpu_review_path": str(CPU_REVIEW),
            "source_cpu_review_file_sha256": file_sha(CPU_REVIEW),
            "source_cpu_review_receipt_sha256": "27685393a762a0ab12ad332dc717dd4b80b0fd16e328484374d712ca803e180a",
            "source_lifecycle_receipt_path": str(SOURCE_LIFECYCLE),
            "source_lifecycle_receipt_file_sha256": file_sha(SOURCE_LIFECYCLE),
            "source_lifecycle_receipt_sha256": "3df1f4c21fec4c1b7f304c8a0f08351179f0eaf1dad2039e699be02547d3a3ba",
        }
    )
    manifest["jobs"][0].update(
        {
            "mode": "ONE_F4_DEVELOPMENT_R_PC_ROOT_V2_1",
            "output_namespace": str(temp_root / "synthetic_output"),
        }
    )
    manifest = hashed(manifest, "manifest_sha256")
    path = temp_root / "execution_authorized_fixture.json"
    write_new(path, manifest)
    return path, manifest


def establish_runner_entry_state(
    temp_root: Path, manifest: Mapping[str, Any], job: Mapping[str, Any]
) -> tuple[dict[str, str], dict[str, Path]]:
    guard_dir = Path(manifest["guard_directory"])
    cache_job = Path(manifest["cache_directory"]) / job["job_id"]
    output = Path(job["output_namespace"])
    guard_dir.mkdir(parents=True, exist_ok=False)
    cache_job.mkdir(parents=True, exist_ok=False)
    for relative in EXPECTED_CACHE_ENV.values():
        (cache_job / relative).mkdir(exist_ok=False)
    start_path = guard_dir / f"{job['job_id']}.start.json"
    stdout = guard_dir / f"{job['job_id']}.stdout.log"
    stderr = guard_dir / f"{job['job_id']}.stderr.log"
    synthetic_lease_marker = temp_root / "synthetic_lease_marker_not_flocked.lock"
    synthetic_lease_marker.touch(exist_ok=False)
    held_lease = synthetic_lease_marker.open("r+")
    fcntl.flock(held_lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    start = hashed(
        {
            "schema_version": "cmf_f4_development_root_v2_1_guard_start_v1",
            "run_id": manifest["run_id"],
            "job_id": job["job_id"],
            "family": "F4",
            "manifest_sha256": manifest["manifest_sha256"],
            "physical_gpu_index": 0,
            "gpu_uuid": "GPU-CPU-LIFECYCLE-NO-DEVICE",
            "guard_pid": os.getpid(),
            "lease_path": str(synthetic_lease_marker),
            "pre_snapshot": {"synthetic_cpu_fixture": True},
        }
    )
    write_new(start_path, start)
    stdout.touch(exist_ok=False)
    stderr.touch(exist_ok=False)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GIT_CONFIG_GLOBAL": str(WORKSPACE / ".config/git/config"),
        "CUDA_VISIBLE_DEVICES": "GPU-CPU-LIFECYCLE-NO-DEVICE",
        "CUDA_HOME": str(WORKSPACE / "Robotwin2/tools/cuda-12.1"),
        "PYTHONPATH": str(PROJECT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "CMF_GPU_GUARD_PHYSICAL_INDEX": "0",
        "CMF_GPU_LEASE_PATH": str(synthetic_lease_marker),
        "CMF_F4_GUARD_START_RECEIPT": str(start_path),
        "CMF_F4_CPU_LIFECYCLE_PREFLIGHT": "1",
    }
    for name, relative in EXPECTED_CACHE_ENV.items():
        env[name] = str(cache_job / relative)
    return env, {
        "guard_dir": guard_dir,
        "cache_job": cache_job,
        "output": output,
        "start": start_path,
        "stdout": stdout,
        "stderr": stderr,
        "lease": synthetic_lease_marker,
        "held_lease": held_lease,
        "guard_terminal": guard_dir / f"{job['job_id']}.terminal.json",
    }


def build_raw_artifact(raw_dir: Path) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=False)
    raw_path = raw_dir / "raw_streams.npz"
    with raw_path.open("wb") as handle:
        np.savez(handle, marker=np.asarray([1, 2, 3], dtype=np.int64))
    payload = {
        "schema_version": "cmf_synthetic_raw_manifest_for_v2_1_cpu_test",
        "development_data": True,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "raw_streams_npz_sha256": file_sha(raw_path),
    }
    manifest = {**payload, "manifest_payload_sha256": canonical_hash(payload)}
    manifest_path = raw_dir / "manifest.json"
    write_new(manifest_path, manifest)
    sidecar = {
        "manifest_file_sha256": file_sha(manifest_path),
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
    }
    sidecar_path = raw_dir / "manifest.sha256.json"
    write_new(sidecar_path, sidecar)
    return {
        **manifest,
        "manifest_file_sha256": file_sha(manifest_path),
        "manifest_integrity_sidecar": "manifest.sha256.json",
        "manifest_integrity_sidecar_sha256": file_sha(sidecar_path),
    }


def build_video_artifact(video_dir: Path) -> dict[str, Any]:
    video_dir.mkdir(parents=True, exist_ok=False)
    path = video_dir / "trajectory.mp4"
    path.write_bytes(b"synthetic-cpu-only-mp4-integrity-fixture")
    receipt = {
        "schema_version": "cmf_development_trajectory_mp4_v1",
        "formal_data": False,
        "stage0_data": False,
        "development_data": True,
        "camera_name": "head_camera",
        "video_fps": 25,
        "control_frequency_hz": 250,
        "sample_stride_steps": 10,
        "frame_count": 2,
        "frame_shape": [2, 2, 3],
        "sampled_step_indices": [0, 1],
        "includes_initial_frame": True,
        "includes_final_frame": True,
        "terminal_status_at_close": "accepted",
        "path": str(path),
        "bytes": path.stat().st_size,
        "file_sha256": file_sha(path),
    }
    receipt["receipt_sha256"] = canonical_hash(receipt)
    return receipt


def branch_receipt(program_id: str, raw_manifest: Mapping[str, Any], video: Mapping[str, Any]) -> dict[str, Any]:
    role_checks = [
        {
            "role": role,
            "checks": {
                "selected_contact_continuity": True,
                "selected_contact_actor_identity": True,
                "prior_slots_preserved": True,
                "uncompleted_roles_preserved": True,
            },
        }
        for role in ("A", "B", "C")
    ]
    return {
        "program_id": program_id,
        "status": "accepted",
        "suffix_execution_planner_query_delta": 0,
        "raw_manifest": dict(raw_manifest),
        "development_video_receipt": dict(video),
        "development_video_integrity": {"pass": True},
        "verifier": {
            "pass": True,
            "family_semantic_verifier": {
                "role_receipts": role_checks,
                "checks": {
                    "all_final_slots": True,
                    "common_x_preserved": True,
                    "selected_gripper_open": True,
                    "selected_arm_neutral_position": True,
                    "selected_arm_neutral_orientation": True,
                },
            },
        },
    }


def suffix_receipt(program_id: str) -> dict[str, Any]:
    return {
        "program_id": program_id,
        "status": "passed",
        "planner_solvable": True,
        "planner_query_count": 42,
        "execution_spec": {
            "targets": [{"segment_id": f"segment-{index}"} for index in range(30)],
            "segment_receipts": [{"planner_status": "Success"} for _ in range(30)],
            "planner_query_receipts": [{"status": "Success"} for _ in range(42)],
        },
    }


def cleanup_records() -> list[dict[str, Any]]:
    phases = ["pristine"]
    phases += [f"task_physical_feasibility:{program}" for program in EXPECTED_PROGRAMS]
    phases += ["canonical_prefix_reference"]
    phases += [f"suffix_preflight:{program}" for program in EXPECTED_PROGRAMS]
    phases += [f"strict_prefix_branch:{program}" for program in EXPECTED_PROGRAMS]
    return [
        {
            "scene_instance_id": f"synthetic-f4-v2-1-scene-{index:02d}",
            "phase": phase,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": True,
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }
        for index, phase in enumerate(phases)
    ]


def build_success_root(output: Path) -> dict[str, Any]:
    root_dir = output / "development_root"
    branches = []
    for program_id in EXPECTED_PROGRAMS:
        branch_dir = root_dir / "branches" / program_id
        raw = build_raw_artifact(branch_dir / "raw")
        video = build_video_artifact(branch_dir / "video")
        branch = branch_receipt(program_id, raw, video)
        write_new(branch_dir / "receipt.json", branch)
        branches.append(branch)
    root = {
        "status": "accepted",
        "branch_receipts": branches,
        "cleanup_records": cleanup_records(),
        "suffix_planner_receipts": [suffix_receipt(program) for program in EXPECTED_PROGRAMS],
        "root_finalization": {
            "accepted": True,
            "checks": {
                "branch_current_matches_reference": True,
                "branch_anchor_equivalent": True,
                "one_executed_prefix_action_hash": True,
                "prefix_start_anchor_equivalent": True,
                "prefix_end_state_equivalent": True,
                "final_state_equivalence": True,
            },
        },
        "task_physical_feasibility_receipts": [
            {"program_id": program, "status": "passed"} for program in EXPECTED_PROGRAMS
        ],
        "freeze_call_count": 1,
        "canonical_prefix_generation_count": 1,
        "canonical_prefix_reference_execution_count": 1,
        "suffix_prefix_replay_count": 3,
        "branch_prefix_replay_count": 3,
        "branch_execution_attempt_count": 3,
        "canonical_prefix_planner_query_count": 10,
        "suffix_planner_query_count_total": 126,
        "planner_query_count_total": 136,
    }
    write_new(root_dir / "root_receipt.json", root)
    return {
        "family": "F4",
        "development_root_pass": True,
        "development_accepted_root_count": 1,
        "development_accepted_trajectory_count": 3,
        "root_receipt": root,
    }


def rewrite_root(output: Path, result: Mapping[str, Any]) -> None:
    overwrite(output / "development_root/root_receipt.json", result["root_receipt"])


def rewrite_branch(output: Path, result: Mapping[str, Any], program_index: int = 0) -> None:
    branch = result["root_receipt"]["branch_receipts"][program_index]
    overwrite(
        output / "development_root/branches" / branch["program_id"] / "receipt.json",
        branch,
    )


def run_finalizer_case(
    temp_root: Path,
    job: Mapping[str, Any],
    label: str,
    mutate: Callable[[Path, dict[str, Any]], None] | None,
    expected_accept: bool,
) -> dict[str, Any]:
    output = temp_root / f"finalizer_{label}"
    result = build_success_root(output)
    if mutate is not None:
        mutate(output, result)
    finalizer = job_runner.finalize_f4_root_result(result, job, output=output)
    observed = finalizer.get("accepted") is True
    if observed is not expected_accept:
        raise AssertionError(f"finalizer case {label} accepted={observed}, expected={expected_accept}")
    return {
        "label": label,
        "expected_accept": expected_accept,
        "observed_accept": observed,
        "failure": finalizer.get("failure"),
        "receipt_sha256": finalizer.get("receipt_sha256"),
        "pass": True,
    }


def paired_branch_mutation(output: Path, result: dict[str, Any], callback: Callable[[dict[str, Any]], None]) -> None:
    callback(result["root_receipt"]["branch_receipts"][0])
    rewrite_branch(output, result, 0)
    rewrite_root(output, result)


def paired_root_mutation(output: Path, result: dict[str, Any], callback: Callable[[dict[str, Any]], None]) -> None:
    callback(result["root_receipt"])
    rewrite_root(output, result)


def finalizer_matrix(temp_root: Path, job: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases = [run_finalizer_case(temp_root, job, "accepted_three_of_three", None, True)]
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "failed_verifier_without_exception",
            lambda output, result: paired_branch_mutation(
                output,
                result,
                lambda branch: branch["verifier"].update({"pass": False}),
            ),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "missing_raw_npz",
            lambda output, result: (
                output
                / "development_root/branches/F4-ABC/raw/raw_streams.npz"
            ).unlink(),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "tampered_raw_npz",
            lambda output, result: (
                output
                / "development_root/branches/F4-ABC/raw/raw_streams.npz"
            ).write_bytes(b"tampered"),
            False,
        )
    )

    def coordinated_raw_replacement(output: Path, result: dict[str, Any]) -> None:
        """Replace all three raw files consistently but leave the branch receipt frozen."""

        raw_dir = output / "development_root/branches/F4-ABC/raw"
        raw_path = raw_dir / "raw_streams.npz"
        with raw_path.open("wb") as handle:
            np.savez(handle, marker=np.asarray([91, 92, 93], dtype=np.int64))
        manifest_path = raw_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["raw_streams_npz_sha256"] = file_sha(raw_path)
        payload = dict(manifest)
        payload.pop("manifest_payload_sha256", None)
        payload.pop("manifest_sha256", None)
        manifest["manifest_payload_sha256"] = canonical_hash(payload)
        if "manifest_sha256" in manifest:
            manifest["manifest_sha256"] = manifest["manifest_payload_sha256"]
        overwrite(manifest_path, manifest)
        sidecar_path = raw_dir / "manifest.sha256.json"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        sidecar["manifest_file_sha256"] = file_sha(manifest_path)
        sidecar["manifest_payload_sha256"] = manifest["manifest_payload_sha256"]
        sidecar["raw_streams_npz_sha256"] = file_sha(raw_path)
        overwrite(sidecar_path, sidecar)

    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "coordinated_raw_npz_manifest_sidecar_replacement",
            coordinated_raw_replacement,
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "missing_mp4",
            lambda output, result: (
                output
                / "development_root/branches/F4-ABC/video/trajectory.mp4"
            ).unlink(),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "tampered_mp4",
            lambda output, result: (
                output
                / "development_root/branches/F4-ABC/video/trajectory.mp4"
            ).write_bytes(b"tampered"),
            False,
        )
    )

    def disk_only_branch_tamper(output: Path, result: dict[str, Any]) -> None:
        path = output / "development_root/branches/F4-ABC/receipt.json"
        branch = json.loads(path.read_text(encoding="utf-8"))
        branch["status"] = "tampered"
        overwrite(path, branch)

    cases.append(
        run_finalizer_case(temp_root, job, "tampered_branch_receipt", disk_only_branch_tamper, False)
    )

    def disk_only_root_tamper(output: Path, result: dict[str, Any]) -> None:
        path = output / "development_root/root_receipt.json"
        root = json.loads(path.read_text(encoding="utf-8"))
        root["status"] = "tampered"
        overwrite(path, root)

    cases.append(
        run_finalizer_case(temp_root, job, "tampered_root_receipt", disk_only_root_tamper, False)
    )

    def append_null_branch(root: dict[str, Any]) -> None:
        root["branch_receipts"].append(None)

    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "extra_null_branch_receipt",
            lambda output, result: paired_root_mutation(
                output, result, append_null_branch
            ),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "reversed_branch_program_order",
            lambda output, result: paired_root_mutation(
                output,
                result,
                lambda root: root["branch_receipts"].reverse(),
            ),
            False,
        )
    )

    def duplicate_task_feasibility_programs(root: dict[str, Any]) -> None:
        for row in root["task_physical_feasibility_receipts"]:
            row["program_id"] = "F4-ABC"

    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "duplicate_task_feasibility_program_ids",
            lambda output, result: paired_root_mutation(
                output, result, duplicate_task_feasibility_programs
            ),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "suffix_query_not_42",
            lambda output, result: paired_root_mutation(
                output,
                result,
                lambda root: root["suffix_planner_receipts"][0].update(
                    {"planner_query_count": 41}
                ),
            ),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "planner_total_not_136",
            lambda output, result: paired_root_mutation(
                output, result, lambda root: root.update({"planner_query_count_total": 135})
            ),
            False,
        )
    )

    def duplicate_scene(root: dict[str, Any]) -> None:
        root["cleanup_records"][1]["scene_instance_id"] = root["cleanup_records"][0][
            "scene_instance_id"
        ]

    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "duplicate_scene_id",
            lambda output, result: paired_root_mutation(output, result, duplicate_scene),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "wrong_phase_multiset",
            lambda output, result: paired_root_mutation(
                output,
                result,
                lambda root: root["cleanup_records"][1].update(
                    {"phase": "suffix_preflight:F4-ABC"}
                ),
            ),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "branch_execution_planner_delta_nonzero",
            lambda output, result: paired_branch_mutation(
                output,
                result,
                lambda branch: branch.update({"suffix_execution_planner_query_delta": 1}),
            ),
            False,
        )
    )
    cases.append(
        run_finalizer_case(
            temp_root,
            job,
            "final_state_equivalence_false",
            lambda output, result: paired_root_mutation(
                output,
                result,
                lambda root: root["root_finalization"]["checks"].update(
                    {"final_state_equivalence": False}
                ),
            ),
            False,
        )
    )
    return cases


def numpy_serialization_test(temp_root: Path) -> dict[str, Any]:
    path = temp_root / "numpy_serialization.json"
    value = {
        "bool": np.bool_(True),
        "int": np.int64(7),
        "float": np.float32(1.25),
        "array": np.asarray([[1, 2], [3, 4]], dtype=np.int16),
    }
    job_runner.write_new(path, value)
    decoded = json.loads(path.read_text(encoding="utf-8"))
    expected = {"bool": True, "int": 7, "float": 1.25, "array": [[1, 2], [3, 4]]}
    return {"path": str(path), "decoded": decoded, "pass": decoded == expected}


def rewrite_hashed(path: Path, value: Mapping[str, Any], key: str = "receipt_sha256") -> None:
    overwrite(path, hashed(value, key))


def post_child_matrix(
    manifest: Mapping[str, Any],
    job: Mapping[str, Any],
    paths: Mapping[str, Path],
    success_finalizer: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    job_terminal_path = Path(job["output_namespace"]) / "job_terminal.json"
    guard_terminal_path = paths["guard_terminal"]
    job_terminal = hashed(
        {
            "schema_version": "cmf_f4_development_root_v2_1_job_terminal_v1",
            "run_id": manifest["run_id"],
            "job_id": job["job_id"],
            "family": "F4",
            "manifest_sha256": manifest["manifest_sha256"],
            "physical_gpu_index": 0,
            "gpu_uuid": "GPU-CPU-LIFECYCLE-NO-DEVICE",
            "result": {
                "development_root_pass": True,
                "development_accepted_root_count": 1,
                "development_accepted_trajectory_count": 3,
            },
            "root_finalizer": dict(success_finalizer),
            "error": None,
            "accepted_development_root_count": 1,
            "accepted_development_trajectory_count": 3,
            "pass": True,
            "formal_data": False,
            "stage1_authorized": False,
        }
    )
    guard_terminal = hashed(
        {
            "schema_version": "cmf_f4_development_root_v2_1_guard_terminal_v1",
            "run_id": manifest["run_id"],
            "job_id": job["job_id"],
            "family": "F4",
            "manifest_sha256": manifest["manifest_sha256"],
            "physical_gpu_index": 0,
            "gpu_uuid": "GPU-CPU-LIFECYCLE-NO-DEVICE",
            "child_exit_code": 0,
            "cache_removed": True,
            "lease_released": True,
            "execution_errors": [],
            "cleanup_errors": [],
            "gpu_returned_to_idle_baseline": True,
            "task_owned_cleanup_pass": True,
            "output_exists": True,
            "status": "completed",
        }
    )
    write_new(job_terminal_path, job_terminal)
    write_new(guard_terminal_path, guard_terminal)
    success = validate_runtime_paths(manifest, job, phase=POST_CHILD)
    if success.get("phase_validation", {}).get("job_succeeded") is not True:
        raise AssertionError("POST_CHILD success case did not prove job success")
    negatives = []

    def run_mutation(label: str, *, mutate_job=None, mutate_guard=None, rehash_job=True, rehash_guard=True):
        changed_job = deepcopy(job_terminal)
        changed_guard = deepcopy(guard_terminal)
        if mutate_job:
            mutate_job(changed_job)
        if mutate_guard:
            mutate_guard(changed_guard)
        overwrite(job_terminal_path, hashed(changed_job) if rehash_job else changed_job)
        overwrite(guard_terminal_path, hashed(changed_guard) if rehash_guard else changed_guard)
        try:
            record_rejection(
                label,
                lambda: validate_runtime_paths(manifest, job, phase=POST_CHILD),
                negatives,
            )
        finally:
            overwrite(job_terminal_path, job_terminal)
            overwrite(guard_terminal_path, guard_terminal)

    run_mutation(
        "job_terminal_self_hash_tamper",
        mutate_job=lambda value: value.update({"job_id": "tampered"}),
        rehash_job=False,
    )
    run_mutation(
        "job_terminal_binding_wrong",
        mutate_job=lambda value: value.update({"run_id": "wrong"}),
    )
    run_mutation(
        "child_exit_zero_but_job_pass_false",
        mutate_job=lambda value: value.update({"pass": False}),
    )

    def reject_finalizer(value: dict[str, Any]) -> None:
        finalizer = deepcopy(value["root_finalizer"])
        finalizer["accepted"] = False
        finalizer["counts"]["accepted_development_roots"] = 0
        finalizer["counts"]["accepted_development_trajectories"] = 0
        value["root_finalizer"] = hashed(finalizer)

    run_mutation("root_finalizer_disagrees_with_pass", mutate_job=reject_finalizer)

    def tamper_finalizer_self_hash(value: dict[str, Any]) -> None:
        value["root_finalizer"]["counts"]["planner_queries"] = 999

    run_mutation(
        "root_finalizer_self_hash_tamper",
        mutate_job=tamper_finalizer_self_hash,
    )
    run_mutation(
        "accepted_counts_wrong",
        mutate_job=lambda value: value.update({"accepted_development_trajectory_count": 2}),
    )
    run_mutation(
        "accepted_result_counts_wrong",
        mutate_job=lambda value: value["result"].update(
            {"development_accepted_root_count": 0}
        ),
    )
    run_mutation(
        "guard_job_gpu_identity_mismatch",
        mutate_guard=lambda value: value.update({"gpu_uuid": "GPU-WRONG"}),
    )
    run_mutation(
        "guard_cleanup_false",
        mutate_guard=lambda value: value.update({"task_owned_cleanup_pass": False}),
    )
    run_mutation(
        "gpu_baseline_false",
        mutate_guard=lambda value: value.update({"gpu_returned_to_idle_baseline": False}),
    )

    failed_finalizer = deepcopy(success_finalizer)
    failed_finalizer["accepted"] = False
    failed_finalizer["checks"]["root_status_accepted"] = False
    failed_finalizer["failure"] = "root_status_accepted"
    failed_finalizer["counts"]["accepted_development_roots"] = 0
    failed_finalizer["counts"]["accepted_development_trajectories"] = 0
    failed_finalizer = hashed(failed_finalizer)
    failed_job = deepcopy(job_terminal)
    failed_job.update(
        {
            "pass": False,
            "root_finalizer": failed_finalizer,
            "accepted_development_root_count": 0,
            "accepted_development_trajectory_count": 0,
        }
    )
    failed_job = hashed(failed_job)
    failed_guard = deepcopy(guard_terminal)
    failed_guard.update(
        {
            "child_exit_code": 1,
            "status": "failed_or_blocked_with_cleanup_evidence",
        }
    )
    failed_guard = hashed(failed_guard)
    overwrite(job_terminal_path, failed_job)
    overwrite(guard_terminal_path, failed_guard)
    consistent_failure = validate_runtime_paths(manifest, job, phase=POST_CHILD)
    if consistent_failure.get("phase_validation", {}).get("job_succeeded") is not False:
        raise AssertionError("POST_CHILD consistent failure was misclassified as success")
    overwrite(job_terminal_path, job_terminal)
    overwrite(guard_terminal_path, guard_terminal)
    return success, negatives + [
        {
            "label": "consistent_failed_job_integrity_valid_but_not_success",
            "rejected": False,
            "job_succeeded": False,
            "pass": True,
        }
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.receipt_out.exists():
        raise FileExistsError("CPU hardening receipt output must be new")
    temp_root = Path(
        tempfile.mkdtemp(prefix="f4_runtime_v2_2_cpu_", dir=str(WORKSPACE / "Robotwin2/tmp"))
    )
    environment_negatives = []
    lineage_negatives = []
    identity_negatives = []
    finalizer_cases = []
    post_success = None
    post_cases = []
    runner_receipt = None
    fixture_manifest_sha = None
    temporary_paths_cleaned = False
    paths = {}
    try:
        fixture_path, manifest = build_execution_authorized_fixture(temp_root)
        job = manifest["jobs"][0]
        fixture_manifest_sha = manifest["manifest_sha256"]
        prepublication = load_and_validate_manifest_job(
            fixture_path,
            job["job_id"],
            phase=PREPUBLICATION,
            require_execution_authorized=True,
            allow_lifecycle_fixture=True,
            executable_role="lifecycle",
            executable_path=Path(__file__),
        )
        guard_entry = load_and_validate_manifest_job(
            fixture_path,
            job["job_id"],
            phase=GUARD_ENTRY,
            require_execution_authorized=True,
            allow_lifecycle_fixture=True,
            executable_role="lifecycle",
            executable_path=Path(__file__),
        )
        env, paths = establish_runner_entry_state(temp_root, manifest, job)
        runner_entry = load_and_validate_manifest_job(
            fixture_path,
            job["job_id"],
            phase=RUNNER_ENTRY,
            require_execution_authorized=True,
            allow_lifecycle_fixture=True,
            environment=env,
            executable_role="runner",
            executable_path=RUNTIME / "job_runner.py",
        )
        command = [
            str(ENV_PYTHON),
            str(RUNTIME / "job_runner.py"),
            "--manifest",
            str(fixture_path),
            "--job-id",
            job["job_id"],
            "--preflight-runner-entry",
            "--allow-lifecycle-fixture",
        ]
        completed = subprocess.run(
            command,
            cwd=str(PROJECT),
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if completed.returncode != 0 or len(lines) != 1:
            raise RuntimeError("V2.1 runner-entry subprocess failed: " + completed.stderr[-2000:])
        runner_receipt = json.loads(lines[0])
        if (
            runner_receipt.get("pass") is not True
            or runner_receipt.get("authorization_consumed") is not False
            or runner_receipt.get("real_gpu_lease_acquired") is not False
            or runner_receipt.get("nvidia_smi_called") is not False
            or runner_receipt.get("scene_created") is not False
            or runner_receipt.get("output_created") is not False
            or paths["output"].exists()
        ):
            raise RuntimeError("execution-authorized lifecycle fixture crossed CPU boundary")

        valid_start = json.loads(paths["start"].read_text(encoding="utf-8"))

        def validate_env(changed_env):
            return load_and_validate_manifest_job(
                fixture_path,
                job["job_id"],
                phase=RUNNER_ENTRY,
                require_execution_authorized=True,
                allow_lifecycle_fixture=True,
                environment=changed_env,
                executable_role="runner",
                executable_path=RUNTIME / "job_runner.py",
            )

        env_mutations = {
            "cuda_visible_devices_multi_uuid": lambda item: item.update(
                {"CUDA_VISIBLE_DEVICES": "GPU-A,GPU-B"}
            ),
            "gpu_index_mismatch": lambda item: item.update(
                {"CMF_GPU_GUARD_PHYSICAL_INDEX": "1"}
            ),
            "lease_path_mismatch": lambda item: item.update(
                {"CMF_GPU_LEASE_PATH": str(temp_root / "other.lock")}
            ),
            "start_receipt_path_mismatch": lambda item: item.update(
                {"CMF_F4_GUARD_START_RECEIPT": str(temp_root / "other.json")}
            ),
            "cuda_home_mismatch": lambda item: item.update({"CUDA_HOME": str(temp_root)}),
            "pythonpath_mismatch": lambda item: item.update({"PYTHONPATH": str(temp_root)}),
            "pythondontwritebytecode_mismatch": lambda item: item.update(
                {"PYTHONDONTWRITEBYTECODE": "0"}
            ),
            "ld_library_path_present": lambda item: item.update(
                {"LD_LIBRARY_PATH": "/forbidden"}
            ),
        }
        for name in EXPECTED_CACHE_ENV:
            env_mutations[f"cache_environment_{name}_mismatch"] = (
                lambda item, field=name: item.update({field: str(temp_root)})
            )
        for label, mutate in env_mutations.items():
            changed = dict(env)
            mutate(changed)
            record_rejection(label, lambda changed=changed: validate_env(changed), environment_negatives)

        def bad_start(label: str, field: str, replacement: Any):
            changed = deepcopy(valid_start)
            changed[field] = replacement
            overwrite(paths["start"], hashed(changed))
            try:
                record_rejection(label, lambda: validate_env(env), environment_negatives)
            finally:
                overwrite(paths["start"], valid_start)

        bad_start("start_family_wrong", "family", "F3")
        bad_start("start_gpu_index_wrong", "physical_gpu_index", 1)
        bad_start("start_gpu_uuid_wrong", "gpu_uuid", "GPU-WRONG")
        missing_lease = paths["lease"]
        hidden_lease = missing_lease.with_suffix(".hidden")
        missing_lease.rename(hidden_lease)
        try:
            record_rejection("lease_marker_missing", lambda: validate_env(env), environment_negatives)
        finally:
            hidden_lease.rename(missing_lease)

        record_rejection(
            "runner_executable_identity_wrong",
            lambda: load_and_validate_manifest_job(
                fixture_path,
                job["job_id"],
                phase=RUNNER_ENTRY,
                require_execution_authorized=True,
                allow_lifecycle_fixture=True,
                environment=env,
                executable_role="runner",
                executable_path=RUNTIME / "guarded_launcher.py",
            ),
            identity_negatives,
        )
        record_rejection(
            "guard_executable_identity_wrong",
            lambda: load_and_validate_manifest_job(
                fixture_path,
                job["job_id"],
                phase=RUNNER_ENTRY,
                require_execution_authorized=True,
                allow_lifecycle_fixture=True,
                environment=env,
                executable_role="guard",
                executable_path=RUNTIME / "job_runner.py",
            ),
            identity_negatives,
        )

        wrong_contract = deepcopy(manifest)
        wrong_contract["manifest_contract_path"] = str(RUNTIME / "guarded_launcher.py")
        wrong_contract["manifest_contract_sha256"] = file_sha(
            RUNTIME / "guarded_launcher.py"
        )
        wrong_contract = hashed(wrong_contract, "manifest_sha256")
        wrong_contract_path = temp_root / "identity_negative_contract.json"
        write_new(wrong_contract_path, wrong_contract)
        record_rejection(
            "contract_executable_identity_wrong",
            lambda: load_and_validate_manifest_job(
                wrong_contract_path,
                job["job_id"],
                phase=RUNNER_ENTRY,
                require_execution_authorized=True,
                allow_lifecycle_fixture=True,
                environment=env,
            ),
            identity_negatives,
        )

        def lineage_changed(label: str, changer: Callable[[dict[str, Any]], None]):
            changed = deepcopy(manifest)
            changer(changed)
            changed = hashed(changed, "manifest_sha256")
            changed_path = temp_root / f"lineage_negative_{len(lineage_negatives):02d}.json"
            write_new(changed_path, changed)
            record_rejection(
                label,
                lambda: load_and_validate_manifest_job(
                    changed_path,
                    job["job_id"],
                    phase=RUNNER_ENTRY,
                    require_execution_authorized=True,
                    allow_lifecycle_fixture=True,
                    environment=env,
                ),
                lineage_negatives,
            )

        lineage_changed(
            "external_decision_file_sha_wrong",
            lambda value: value.update({"external_review_decision_file_sha256": "0" * 64}),
        )
        lineage_changed(
            "external_decision_receipt_wrong",
            lambda value: value.update({"external_review_decision_receipt_sha256": "0" * 64}),
        )
        lineage_changed(
            "source_proposal_manifest_wrong",
            lambda value: value.update({"source_proposal_manifest_sha256": "0" * 64}),
        )
        lineage_changed(
            "source_cpu_review_receipt_wrong",
            lambda value: value.update({"source_cpu_review_receipt_sha256": "0" * 64}),
        )
        lineage_changed(
            "source_lifecycle_receipt_wrong",
            lambda value: value.update({"source_lifecycle_receipt_sha256": "0" * 64}),
        )

        finalizer_cases = finalizer_matrix(temp_root, job)
        numpy_case = numpy_serialization_test(temp_root)
        if numpy_case["pass"] is not True:
            raise RuntimeError("nested NumPy canonical serialization failed")

        success_output = temp_root / "post_child_output"
        success_result = build_success_root(success_output)
        success_finalizer = job_runner.finalize_f4_root_result(
            success_result, job, output=success_output
        )
        if success_finalizer.get("accepted") is not True:
            raise RuntimeError("POST_CHILD source finalizer fixture failed")
        # Repoint only the in-memory fixture for direct POST_CHILD testing.
        post_manifest = deepcopy(manifest)
        post_manifest["jobs"][0]["output_namespace"] = str(success_output)
        post_manifest = hashed(post_manifest, "manifest_sha256")
        post_job = post_manifest["jobs"][0]
        # Terminal paths depend only on unchanged guard/job IDs. Cache is removed.
        shutil.rmtree(paths["cache_job"])
        post_success, post_cases = post_child_matrix(
            post_manifest, post_job, paths, success_finalizer
        )

        phases = Counter(
            item.get("phase") for item in success_result["root_receipt"]["cleanup_records"]
        )
        execution_fixture_summary = {
            "prepublication_phase": prepublication["phase"],
            "guard_entry_phase": guard_entry["phase"],
            "runner_entry_phase": runner_entry["phase"],
            "require_execution_authorized": True,
            "approved_fixture": manifest["approved"] is True,
            "real_guard_main_called": False,
            "real_gpu_lease_acquired": False,
            "synthetic_lease_marker_only": False,
            "parent_exclusive_flock_held": True,
            "nvidia_smi_called": False,
            "cuda_context_created": False,
            "scene_created": False,
            "planner_called": False,
            "production_output_created": False,
            "authorization_consumed": False,
            "runner_entry_subprocess_returncode": completed.returncode,
            "runner_entry_receipt_sha256": runner_receipt["receipt_sha256"],
            "synthetic_phase_rows": len(phases),
            "pass": True,
        }
    finally:
        if paths.get("held_lease") is not None:
            paths["held_lease"].close()
        shutil.rmtree(temp_root)
        temporary_paths_cleaned = not temp_root.exists()

    receipt = {
        "schema_version": "cmf_f4_development_root_runtime_v2_1_finalizer_post_child_test_v1",
        "runtime_files": {
            "manifest_contract.py": file_sha(RUNTIME / "manifest_contract.py"),
            "guarded_launcher.py": file_sha(RUNTIME / "guarded_launcher.py"),
            "job_runner.py": file_sha(RUNTIME / "job_runner.py"),
            "lifecycle_preflight.py": file_sha(Path(__file__).resolve()),
        },
        "source_lineage": {
            "external_decision_file_sha256": file_sha(DECISION),
            "external_decision_receipt_sha256": "c8ff692590d7cdb63995c9ce6932d851c1ef918fb5a8e8003881d2035eca7c35",
            "source_proposal_manifest_sha256": "8afaf49a83aaaedc9473cd20866ad06e2b18e1f8adfcd1e6747baa401ce0a4f5",
            "source_cpu_review_receipt_sha256": "27685393a762a0ab12ad332dc717dd4b80b0fd16e328484374d712ca803e180a",
            "source_lifecycle_receipt_sha256": "3df1f4c21fec4c1b7f304c8a0f08351179f0eaf1dad2039e699be02547d3a3ba",
        },
        "execution_authorized_lifecycle_fixture_manifest_sha256": fixture_manifest_sha,
        "execution_authorized_lifecycle_fixture": execution_fixture_summary,
        "runner_environment_negative_tests": environment_negatives,
        "runner_environment_negative_test_count": len(environment_negatives),
        "lineage_negative_tests": lineage_negatives,
        "lineage_negative_test_count": len(lineage_negatives),
        "executable_identity_negative_tests": identity_negatives,
        "finalizer_tests": finalizer_cases,
        "finalizer_test_count": len(finalizer_cases),
        "post_child_success": post_success,
        "post_child_tests": post_cases,
        "post_child_test_count": len(post_cases),
        "numpy_serialization": numpy_case,
        "temporary_paths_cleaned": temporary_paths_cleaned,
        "real_gpu_lease_acquired": False,
        "nvidia_smi_called": False,
        "gpu_context_created": False,
        "scene_created": False,
        "planner_called": False,
        "production_output_created": False,
        "authorization_consumed": False,
        "pass": bool(
            temporary_paths_cleaned
            and runner_receipt
            and runner_receipt.get("pass") is True
            and all(item.get("rejected") is True for item in environment_negatives)
            and all(item.get("rejected") is True for item in lineage_negatives)
            and all(item.get("rejected") is True for item in identity_negatives)
            and len(finalizer_cases) == 18
            and all(item.get("pass") is True for item in finalizer_cases)
            and post_success
            and post_success.get("phase_validation", {}).get("job_succeeded") is True
            and len(post_cases) == 11
            and all(item.get("pass", item.get("rejected") is True) for item in post_cases)
            and numpy_case.get("pass") is True
        ),
    }
    receipt["receipt_sha256"] = canonical_hash(receipt)
    write_new(args.receipt_out, receipt)
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
