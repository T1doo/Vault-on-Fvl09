#!/usr/bin/env python3
"""One externally approved F2 top-contact development-root runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import traceback


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
EXPECTED_SOURCE = "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
EXPECTED_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_STATUS = "APPROVED_F2_TOP_CONTACT_ONE_DEVELOPMENT_ROOT_V1"
EXPECTED_JOB_ID = "f2-top-contact-development-rpc-root-v1-run1"
EXPECTED_BUDGET = {
    "maximum_root_invocations": 1,
    "maximum_planner_queries": 75,
    "maximum_fresh_scenes": 8,
    "maximum_robot_action_scenes": 4,
    "maximum_branch_executions": 3,
    "maximum_raw_trajectories": 3,
    "maximum_debug_videos": 3,
    "maximum_accepted_development_roots": 1,
    "maximum_accepted_development_trajectories": 3,
    "maximum_formal_trajectories": 0,
}


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def python_tree_sha(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def workspace_path(value, label, *, must_file=False):
    path = Path(str(value)).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise ValueError(f"{label} is outside workspace")
    if must_file and not path.is_file():
        raise ValueError(f"{label} is missing")
    return path


def load_manifest(path: Path, job_id: str, *, phase: str):
    manifest_path = workspace_path(path, "manifest", must_file=True)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("F2 manifest self-hash mismatch")
    if value.get("status") != EXPECTED_STATUS or value.get("approved") is not True:
        raise PermissionError("F2 root manifest is not the exact approval")
    if value.get("gpu_execution_authorized") is not True or value.get("physical_execution_authorized") is not True:
        raise PermissionError("F2 root GPU/physical execution is not authorized")
    if value.get("implementation_source_sha256") != EXPECTED_SOURCE:
        raise ValueError("F2 controlled source binding changed")
    if python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_SOURCE:
        raise ValueError("active controlled source differs from F2 freeze")
    if value.get("robotwin_tracked_head") != EXPECTED_HEAD:
        raise ValueError("F2 RoboTwin head binding changed")
    head = subprocess.run(["git", "-C", str(PROJECT), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    tracked = subprocess.run(["git", "-C", str(PROJECT), "status", "--porcelain", "--untracked-files=no"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    if head != EXPECTED_HEAD or tracked:
        raise ValueError("official RoboTwin tracked source changed")
    if value.get("allowed_physical_gpu_indices") != list(range(8)) or value.get("one_job_per_gpu") is not True or value.get("root_sharding") is not False:
        raise ValueError("F2 GPU scheduling contract changed")
    for key in ("stage0_reopened", "stage1_authorized", "formal_360_authorized", "training_authorized", "h_reveal_authorized", "compression_authorized", "pi05_authorized", "formal_data"):
        if value.get(key) is not False:
            raise ValueError(f"forbidden F2 stage enabled: {key}")
    for path_key, sha_key in (
        ("runner_script_path", "runner_script_sha256"),
        ("guard_script_path", "guard_script_sha256"),
        ("external_review_decision_path", "external_review_decision_file_sha256"),
        ("source_selection_terminal_path", "source_selection_terminal_file_sha256"),
        ("source_physical_scene_path", "source_physical_scene_file_sha256"),
    ):
        bound = workspace_path(value[path_key], path_key, must_file=True)
        if file_sha(bound) != value[sha_key]:
            raise ValueError(f"F2 bound file hash changed: {path_key}")
    assets = value.get("asset_hashes_by_family", {}).get("F2", {})
    if not assets:
        raise ValueError("F2 asset map missing")
    for relative, expected in assets.items():
        if file_sha(PROJECT / relative) != expected:
            raise ValueError(f"F2 asset changed: {relative}")
    jobs = value.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1 or jobs[0].get("job_id") != job_id or job_id != EXPECTED_JOB_ID:
        raise ValueError("F2 exact job lookup failed")
    job = jobs[0]
    if job.get("family") != "F2" or job.get("mode") != "ONE_F2_TOP_CONTACT_DEVELOPMENT_R_PC_ROOT_V1":
        raise ValueError("F2 dispatch mode changed")
    for key, expected in EXPECTED_BUDGET.items():
        if job.get(key) != expected:
            raise ValueError(f"F2 budget changed: {key}")
    if job.get("automatic_retry") is not False or job.get("fallback_allowed") is not False or job.get("second_root_allowed") is not False:
        raise ValueError("F2 retry/fallback/second root enabled")
    output = workspace_path(job["output_namespace"], "F2 output")
    guard_dir = workspace_path(value["guard_directory"], "F2 guard directory")
    cache_job = workspace_path(value["cache_directory"], "F2 cache directory") / job_id
    if output.exists():
        raise FileExistsError("F2 output namespace must be new")
    if phase in {"guard", "preflight"} and guard_dir.exists():
        raise FileExistsError("F2 guard directory must be new before Guard")
    if phase in {"guard", "preflight"} and cache_job.exists():
        raise FileExistsError("F2 cache namespace must be new before Guard")
    if phase == "runner" and (not guard_dir.is_dir() or not cache_job.is_dir()):
        raise ValueError("F2 runner lacks Guard-created runtime paths")
    return value, job


def write_new(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def prepare_job(manifest, job):
    from controlled_multi_future.f2_top_contact_root_runtime_v1 import (
        F2TopContactRootControllerV1,
        build_f2_top_contact_planned_root_spec_v1,
        build_f2_top_contact_selected_binding_v1,
    )

    source = json.loads(Path(manifest["source_selection_terminal_path"]).read_text(encoding="utf-8"))
    physical = json.loads(Path(manifest["source_physical_scene_path"]).read_text(encoding="utf-8"))
    if source["stage_a_terminal"]["receipt_sha256"] != job["source_stage_a_terminal_receipt_sha256"]:
        raise ValueError("F2 source Stage-A terminal receipt changed")
    if physical.get("result", {}).get("physically_qualified") is not True or physical["receipt_sha256"] != job["source_physical_scene_receipt_sha256"]:
        raise ValueError("F2 source physical micro success changed")
    binding = build_f2_top_contact_selected_binding_v1(source["stage_a_spec"]["binding"])
    planned = build_f2_top_contact_planned_root_spec_v1(binding)
    F2TopContactRootControllerV1(binding, source["stage_a_spec"]["recipe"])
    return source, binding, planned


def preflight(manifest_path, job_id):
    manifest, job = load_manifest(manifest_path, job_id, phase="preflight")
    _source, binding, planned = prepare_job(manifest, job)
    return {
        "schema_version": "cmf_f2_top_contact_root_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "selected_binding_sha256": binding["binding_sha256"],
        "planned_root_slot_spec_sha256": planned["planned_root_slot_spec_sha256"],
        "output_created": False,
        "scene_created": False,
        "gpu_context_created": False,
        "pass": True,
    }


def run_job(manifest, job):
    from controlled_multi_future.f2_top_contact_root_runtime_v1 import (
        IMPLEMENTATION_VERSION,
        RoboTwinRealSapienF2TopContactRootV1Adapter,
    )
    from controlled_multi_future.root_orchestrator_v1_2 import (
        RealSapienStrictPrefixRootOrchestratorV1_2,
    )

    source, binding, planned = prepare_job(manifest, job)
    output = Path(job["output_namespace"])
    adapter = RoboTwinRealSapienF2TopContactRootV1Adapter(
        output_root=output / "scene_work",
        expected_implementation_source_sha256=manifest["implementation_source_sha256"],
        binding=binding,
        recipe=source["stage_a_spec"]["recipe"],
    )
    realization = {
        program_id: {"realization": "r_pc", "formal_data": False, "stage0_data": False, "stage1_authorized": False}
        for program_id in ("F2-inside", "F2-on", "F2-beside")
    }
    root = RealSapienStrictPrefixRootOrchestratorV1_2(
        adapter, implementation_version=IMPLEMENTATION_VERSION
    ).run_nonformal_root(
        output_dir=output / "root",
        planned_root_slot_spec=planned,
        realization_spec_by_program=realization,
        stage0_data=False,
        stage0_authorized=False,
        development_video_required=True,
    )
    counts = {
        "planner_queries": int(root.get("planner_query_count_total") or 0),
        "fresh_scenes": len(root.get("cleanup_records", [])),
        "branch_executions": int(root.get("branch_execution_attempt_count") or 0),
    }
    if counts["planner_queries"] > 75 or counts["fresh_scenes"] > 8 or counts["branch_executions"] > 3:
        raise RuntimeError(f"F2 root exceeded reviewed budget: {counts}")
    accepted = root.get("status") == "accepted"
    return {
        "family": "F2",
        "mode": job["mode"],
        "selected_binding_sha256": binding["binding_sha256"],
        "planned_root_slot_spec_sha256": planned["planned_root_slot_spec_sha256"],
        "root_receipt": root,
        "budget_counts": counts,
        "development_root_pass": accepted,
        "development_accepted_root_count": 1 if accepted else 0,
        "development_accepted_trajectory_count": 3 if accepted else 0,
        "accepted_trajectory_count": 0,
        "formal_data": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_only:
        print(json.dumps(preflight(args.manifest, args.job_id), sort_keys=True))
        return 0
    manifest, job = load_manifest(args.manifest, args.job_id, phase="runner")
    if not os.environ.get("CUDA_VISIBLE_DEVICES") or os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX") is None or os.environ.get("LD_LIBRARY_PATH"):
        raise PermissionError("F2 runner lacks clean UUID-bound Guard environment")
    output = Path(job["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "job_start.json", {"manifest_sha256": manifest["manifest_sha256"], "job_id": args.job_id})
    error = None
    result = None
    try:
        result = run_job(manifest, job)
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    terminal = {
        "schema_version": "cmf_f2_top_contact_root_job_terminal_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": args.job_id,
        "result": result,
        "error": error,
        "pass": error is None and bool(result) and result.get("development_root_pass") is True,
        "formal_data": False,
        "stage1_authorized": False,
    }
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
