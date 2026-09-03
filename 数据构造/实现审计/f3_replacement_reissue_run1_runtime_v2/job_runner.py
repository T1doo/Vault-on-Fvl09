#!/usr/bin/env python3
"""Budget-complete V2 wrapper for the one unconsumed F3 reissue."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import traceback


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
VAULT = WORKSPACE / "Vault-on-Fvl09"
V1_RUNNER = (
    VAULT
    / "数据构造/实现审计/f3_replacement_reissue_run1_runtime_v1/job_runner.py"
)
V1_RUNNER_SHA256 = "321452f51b99b00543cd144122c2acaf851c226017b582a3c032aece0ef25a78"
PLAN = VAULT / "数据构造/实现审计/CMF_F2_F3_F4_NEXT_EXECUTION_PLAN_V1_20260904.md"
PLAN_SHA256 = "f219a4e57f617b322a9526f939bf9498716f4e428ba220bbd80e64e21e7cfe12"
EXPECTED_SOURCE = "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
EXPECTED_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_STATUS = "APPROVED_F3_ZERO_SCENE_WIRING_REISSUE_RUN1_V2"
EXPECTED_JOB_ID = "f3-centralized-replacements-zero-scene-reissue-run1-v2"
EXPECTED_PROPOSAL_SHA256 = "5203ca62afba5a594edabfd57ef0a0aa3e12106895ecf508478e4111f3451dd2"
EXPECTED_TUPLES = [
    ["bottle5", "right", "lower_body", "contact2", "rotation1", "r1505"],
    ["bottle4", "left", "upper_body", "contact0", "rotation6", "r2180"],
    ["bottle13", "right", "upper_body", "contact2", "rotation5", "r3677"],
]
EXPECTED_CAPS = {
    "replacement_qualification_planner_query_cap": 30,
    "physical_planner_query_cap_per_candidate": 7,
    "physical_candidate_cap": 4,
    "aggregate_planner_query_cap": 58,
    "planner_scene_cap": 6,
    "physical_scene_cap": 4,
    "aggregate_scene_cap": 10,
    "conditional_no_suffix_scene_cap_in_this_job": 0,
    "reserved_next_no_suffix_scene_cap": 3,
    "formal_trajectory_cap": 0,
}


def canonical_hash(value) -> str:
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


def workspace_path(value, label, *, must_file=False):
    path = Path(str(value)).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise ValueError(f"{label} is outside workspace")
    if must_file and not path.is_file():
        raise ValueError(f"{label} is missing")
    return path


def load_v1():
    if file_sha(V1_RUNNER) != V1_RUNNER_SHA256:
        raise RuntimeError("immutable F3 reissue V1 runner changed")
    if file_sha(PLAN) != PLAN_SHA256:
        raise RuntimeError("two-part F3 budget-clarification plan changed")
    spec = importlib.util.spec_from_file_location("cmf_f3_reissue_v1_for_v2", V1_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load immutable F3 reissue V1 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1 = load_v1()


def load_manifest(path: Path, job_id: str, *, phase: str):
    manifest_path = workspace_path(path, "manifest", must_file=True)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("F3 V2 manifest self-hash mismatch")
    if value.get("status") != EXPECTED_STATUS or value.get("approved") is not True:
        raise PermissionError("F3 V2 manifest is not approved")
    if (
        value.get("gpu_execution_authorized") is not True
        or value.get("planner_execution_authorized") is not True
        or value.get("physical_execution_authorized") is not True
    ):
        raise PermissionError("F3 V2 execution scope changed")
    if (
        value.get("implementation_source_sha256") != EXPECTED_SOURCE
        or python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_SOURCE
    ):
        raise ValueError("F3 V2 controlled source differs from freeze")
    head = subprocess.run(
        ["git", "-C", str(PROJECT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "-C", str(PROJECT), "status", "--porcelain", "--untracked-files=no"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    if value.get("robotwin_tracked_head") != EXPECTED_HEAD or head != EXPECTED_HEAD or tracked:
        raise ValueError("official RoboTwin tracked source changed")
    if (
        value.get("allowed_physical_gpu_indices") != list(range(8))
        or value.get("one_job_per_gpu") is not True
        or value.get("root_sharding") is not False
    ):
        raise ValueError("F3 V2 GPU scheduling contract changed")
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
        if value.get(key) is not False:
            raise ValueError(f"forbidden F3 V2 stage enabled: {key}")
    for path_key, sha_key in (
        ("runner_script_path", "runner_script_sha256"),
        ("guard_script_path", "guard_script_sha256"),
        ("execution_plan_path", "execution_plan_file_sha256"),
        ("v1_manifest_path", "v1_manifest_file_sha256"),
        ("v1_runner_path", "v1_runner_file_sha256"),
        ("v1_supersession_receipt_path", "v1_supersession_receipt_file_sha256"),
        ("wiring_overlay_path", "wiring_overlay_file_sha256"),
        ("failed_runner_path", "failed_runner_file_sha256"),
        ("failed_terminal_path", "failed_terminal_file_sha256"),
        ("retained_stage_a_path", "retained_stage_a_file_sha256"),
        ("retained_stage_b_path", "retained_stage_b_file_sha256"),
    ):
        bound = workspace_path(value[path_key], path_key, must_file=True)
        if file_sha(bound) != value[sha_key]:
            raise ValueError(f"F3 V2 bound file hash changed: {path_key}")
    if (
        value["execution_plan_file_sha256"] != PLAN_SHA256
        or value["v1_runner_file_sha256"] != V1_RUNNER_SHA256
        or value.get("reissue_ordinal") != 1
        or value.get("v1_consumed") is not False
        or value.get("second_reissue") is not False
    ):
        raise ValueError("F3 V2 supersession/reissue lineage changed")
    assets = value.get("asset_hashes_by_family", {}).get("F3", {})
    if not assets:
        raise ValueError("F3 V2 asset map missing")
    for relative, expected in assets.items():
        if file_sha(PROJECT / relative) != expected:
            raise ValueError(f"F3 V2 asset changed: {relative}")
    jobs = value.get("jobs")
    if (
        not isinstance(jobs, list)
        or len(jobs) != 1
        or jobs[0].get("job_id") != job_id
        or job_id != EXPECTED_JOB_ID
    ):
        raise ValueError("F3 V2 exact job lookup failed")
    job = jobs[0]
    if (
        job.get("family") != "F3"
        or job.get("mode") != "F3_CENTRALIZED_REPLACEMENT_GATE_ZERO_SCENE_REISSUE_V2"
        or job.get("proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or job.get("replacement_tuples") != EXPECTED_TUPLES
        or any(job.get(key) != expected for key, expected in EXPECTED_CAPS.items())
        or job.get("conditional_no_suffix_executed_in_this_job") is not False
        or job.get("retained_survivor_qualification_rerun") is not False
        or job.get("automatic_retry") is not False
        or job.get("fallback_allowed") is not False
        or job.get("second_reissue_allowed") is not False
    ):
        raise ValueError("F3 V2 exact tuple/budget/stop contract changed")
    output = workspace_path(job["output_namespace"], "F3 V2 output")
    guard_dir = workspace_path(value["guard_directory"], "F3 V2 guard directory")
    cache_job = workspace_path(value["cache_directory"], "F3 V2 cache directory") / job_id
    if output.exists():
        raise FileExistsError("F3 V2 output namespace must be new")
    if phase in {"guard", "preflight"} and (guard_dir.exists() or cache_job.exists()):
        raise FileExistsError("F3 V2 Guard/cache paths must be new")
    if phase == "runner" and (not guard_dir.is_dir() or not cache_job.is_dir()):
        raise ValueError("F3 V2 runner lacks Guard-created paths")
    return value, job


def prepare_contract(manifest, job):
    patched, proposal, retained_a, retained_b, overlay_preflight = v1.prepare_contract(
        manifest, job
    )
    return patched, proposal, retained_a, retained_b, overlay_preflight


def _account(result, job):
    planner_rows = result.get("planner_rows") or []
    physical_rows = result.get("physical_rows") or []
    qualification = int(result.get("replacement_planner_queries", -1))
    physical_queries = [int(row.get("physical_planner_queries", -1)) for row in physical_rows]
    physical_total = sum(physical_queries)
    aggregate = qualification + physical_total
    planner_scenes = len(planner_rows) + sum(
        row.get("stage_a_pass") is True for row in planner_rows
    )
    physical_scenes = len(physical_rows)
    aggregate_scenes = planner_scenes + physical_scenes
    checks = {
        "qualification_at_most_30": qualification
        <= job["replacement_qualification_planner_query_cap"],
        "each_physical_at_most_7": all(
            0 <= value <= job["physical_planner_query_cap_per_candidate"]
            for value in physical_queries
        ),
        "physical_candidates_at_most_4": physical_scenes
        <= job["physical_candidate_cap"],
        "aggregate_planner_at_most_58": aggregate
        <= job["aggregate_planner_query_cap"],
        "planner_scenes_at_most_6": planner_scenes <= job["planner_scene_cap"],
        "physical_scenes_at_most_4": physical_scenes <= job["physical_scene_cap"],
        "aggregate_scenes_at_most_10": aggregate_scenes
        <= job["aggregate_scene_cap"],
        "no_suffix_scenes_zero": result.get("conditional_no_suffix_executed")
        is False
        and job["conditional_no_suffix_scene_cap_in_this_job"] == 0,
    }
    return {
        "schema_version": "cmf_f3_reissue_v2_runtime_accounting_v1",
        "replacement_qualification_planner_queries": qualification,
        "physical_planner_queries_by_candidate": physical_queries,
        "physical_planner_queries": physical_total,
        "aggregate_planner_queries": aggregate,
        "planner_scenes": planner_scenes,
        "physical_scenes": physical_scenes,
        "aggregate_scenes": aggregate_scenes,
        "conditional_no_suffix_scenes": 0,
        "reserved_next_no_suffix_scene_cap": job[
            "reserved_next_no_suffix_scene_cap"
        ],
        "checks": checks,
        "pass": all(checks.values()),
    }


def preflight(manifest_path, job_id):
    manifest, job = load_manifest(manifest_path, job_id, phase="preflight")
    _patched, proposal, retained_a, retained_b, overlay_preflight = prepare_contract(
        manifest, job
    )
    return {
        "schema_version": "cmf_f3_zero_scene_wiring_reissue_v2_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "overlay_preflight": overlay_preflight,
        "replacement_recipe_sha256s": [
            item["recipe_sha256"] for item in proposal["replacement_candidates"]
        ],
        "retained_recipe_id": retained_a["spec"]["recipe"]["recipe_id"],
        "retained_stage_b_receipt_sha256": retained_b["terminal"]["receipt_sha256"],
        "budget_contract": {key: job[key] for key in EXPECTED_CAPS},
        "conditional_no_suffix_executed_in_this_job": False,
        "reissue_ordinal": 1,
        "v1_consumed": False,
        "output_created": False,
        "scene_created": False,
        "gpu_context_created": False,
        "pass": True,
    }


def run_gate(manifest, job, output):
    result = v1.run_gate(manifest, job, output)
    accounting = _account(result, job)
    if accounting["pass"] is not True:
        raise RuntimeError(f"F3 V2 runtime accounting failed: {accounting['checks']}")
    result.update(
        {
            "runtime_version": "f3_replacement_reissue_run1_runtime_v2",
            "runtime_accounting": accounting,
            "conditional_no_suffix_executed": False,
            "conditional_no_suffix_scene_count": 0,
            "reserved_next_no_suffix_scene_cap": 3,
            "reissue_ordinal": 1,
            "second_reissue_allowed": False,
        }
    )
    return result


def write_new(path, value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    serializable = canonical_jsonable(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(serializable, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv=None):
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_only:
        print(json.dumps(preflight(args.manifest, args.job_id), sort_keys=True))
        return 0
    manifest, job = load_manifest(args.manifest, args.job_id, phase="runner")
    if (
        not os.environ.get("CUDA_VISIBLE_DEVICES")
        or os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX") is None
        or os.environ.get("LD_LIBRARY_PATH")
    ):
        raise PermissionError("F3 V2 runner lacks clean UUID-bound Guard environment")
    output = Path(job["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    write_new(
        output / "job_start.json",
        {"manifest_sha256": manifest["manifest_sha256"], "job_id": args.job_id},
    )
    error = None
    result = None
    try:
        result = run_gate(manifest, job, output)
    except BaseException as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    terminal = canonical_jsonable(
        {
            "schema_version": "cmf_f3_zero_scene_wiring_reissue_v2_terminal_v1",
            "manifest_sha256": manifest["manifest_sha256"],
            "job_id": args.job_id,
            "result": result,
            "error": error,
            "pass": error is None
            and bool(result)
            and result.get("gate_pass") is True
            and result.get("runtime_accounting", {}).get("pass") is True,
            "reissue_ordinal": 1,
            "second_reissue_allowed": False,
            "conditional_no_suffix_executed_in_this_job": False,
            "formal_data": False,
            "stage1_authorized": False,
        }
    )
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
