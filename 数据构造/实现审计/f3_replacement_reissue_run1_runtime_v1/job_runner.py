#!/usr/bin/env python3
"""One approved reissue of the zero-scene-failed F3 replacement Gate."""

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
OVERLAY = (
    WORKSPACE
    / "Vault-on-Fvl09/数据构造/实现审计"
    / "f3_replacement_reissue_proposal_v1/job_runner_overlay.py"
)
OVERLAY_SHA256 = "586384db1676c3a4ec1cfa78f90f5de624059640da34e2c4707c6681dd9b9347"
FAILED_RUNNER = (
    WORKSPACE
    / "Vault-on-Fvl09/数据构造/实现审计"
    / "f3_replacement_run1_runtime_v1/job_runner.py"
)
FAILED_RUNNER_SHA256 = "36e447e8bc7b9909af4ac88dbf5930c83548d0f6c56db947e6797b7e1c3f4728"
FAILED_TERMINAL = (
    WORKSPACE
    / "Vault-on-Fvl09/数据构造/实现审计"
    / "F3_CENTRALIZED_REPLACEMENTS_RUN1_TERMINAL_V1.json"
)
FAILED_TERMINAL_SHA256 = "f9e7d24ae1ad40ce951b359a089cb0ee607ec9302c61db2ed37adae73ed20ef6"
EXPECTED_DECISION_SHA256 = "85023b5726611f6ed1b30365fae096c84e97c3973e1fab1bb2000d5251c540f4"
EXPECTED_SOURCE = "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
EXPECTED_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_STATUS = "APPROVED_F3_ZERO_SCENE_WIRING_REISSUE_RUN1_V1"
EXPECTED_JOB_ID = "f3-centralized-replacements-zero-scene-reissue-run1"
EXPECTED_PROPOSAL_SHA256 = "5203ca62afba5a594edabfd57ef0a0aa3e12106895ecf508478e4111f3451dd2"
EXPECTED_TUPLES = [
    ["bottle5", "right", "lower_body", "contact2", "rotation1", "r1505"],
    ["bottle4", "left", "upper_body", "contact0", "rotation6", "r2180"],
    ["bottle13", "right", "upper_body", "contact2", "rotation5", "r3677"],
]


def canonical_hash(value):
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


def load_overlay():
    if file_sha(OVERLAY) != OVERLAY_SHA256:
        raise RuntimeError("approved F3 wiring overlay changed")
    if file_sha(FAILED_RUNNER) != FAILED_RUNNER_SHA256:
        raise RuntimeError("sealed zero-scene-failed F3 runner changed")
    if file_sha(FAILED_TERMINAL) != FAILED_TERMINAL_SHA256:
        raise RuntimeError("sealed zero-scene F3 terminal changed")
    spec = importlib.util.spec_from_file_location(
        "cmf_f3_approved_reissue_overlay", OVERLAY
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load approved F3 wiring overlay")
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    overlay_preflight = overlay.preflight()
    if overlay_preflight.get("pass") is not True:
        raise RuntimeError("approved F3 wiring overlay preflight failed")
    patched, required, old_direct = overlay.load_corrected_runner()
    if old_direct is not False or not all(
        callable(getattr(patched.base, name, None)) for name in required
    ):
        raise RuntimeError("F3 patched helper resolution changed")
    return overlay, patched, overlay_preflight


def load_manifest(path: Path, job_id: str, *, phase: str):
    manifest_path = workspace_path(path, "manifest", must_file=True)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("F3 reissue manifest self-hash mismatch")
    if value.get("status") != EXPECTED_STATUS or value.get("approved") is not True:
        raise PermissionError("F3 reissue manifest is not approved")
    if (
        value.get("gpu_execution_authorized") is not True
        or value.get("planner_execution_authorized") is not True
        or value.get("physical_execution_authorized") is not True
    ):
        raise PermissionError("F3 reissue execution scope changed")
    if (
        value.get("implementation_source_sha256") != EXPECTED_SOURCE
        or python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_SOURCE
    ):
        raise ValueError("F3 controlled source differs from freeze")
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
        raise ValueError("F3 GPU scheduling contract changed")
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
            raise ValueError(f"forbidden F3 stage enabled: {key}")
    for path_key, sha_key in (
        ("runner_script_path", "runner_script_sha256"),
        ("guard_script_path", "guard_script_sha256"),
        ("external_review_decision_path", "external_review_decision_file_sha256"),
        ("wiring_overlay_path", "wiring_overlay_file_sha256"),
        ("failed_runner_path", "failed_runner_file_sha256"),
        ("failed_terminal_path", "failed_terminal_file_sha256"),
        ("retained_stage_a_path", "retained_stage_a_file_sha256"),
        ("retained_stage_b_path", "retained_stage_b_file_sha256"),
    ):
        bound = workspace_path(value[path_key], path_key, must_file=True)
        if file_sha(bound) != value[sha_key]:
            raise ValueError(f"F3 bound file hash changed: {path_key}")
    if (
        value["external_review_decision_file_sha256"] != EXPECTED_DECISION_SHA256
        or value["wiring_overlay_file_sha256"] != OVERLAY_SHA256
        or value["failed_runner_file_sha256"] != FAILED_RUNNER_SHA256
        or value["failed_terminal_file_sha256"] != FAILED_TERMINAL_SHA256
    ):
        raise ValueError("F3 reissue decision/lineage binding changed")
    assets = value.get("asset_hashes_by_family", {}).get("F3", {})
    if not assets:
        raise ValueError("F3 asset map missing")
    for relative, expected in assets.items():
        if file_sha(PROJECT / relative) != expected:
            raise ValueError(f"F3 asset changed: {relative}")
    jobs = value.get("jobs")
    if (
        not isinstance(jobs, list)
        or len(jobs) != 1
        or jobs[0].get("job_id") != job_id
        or job_id != EXPECTED_JOB_ID
    ):
        raise ValueError("F3 exact reissue job lookup failed")
    job = jobs[0]
    exact = {
        "family": "F3",
        "mode": "F3_CENTRALIZED_REPLACEMENT_GATE_ZERO_SCENE_REISSUE_V1",
        "planner_query_cap": 30,
        "planner_scene_cap": 6,
        "physical_candidate_cap": 4,
        "conditional_no_suffix_scene_cap": 3,
        "formal_trajectory_cap": 0,
        "reissue_count_cap": 1,
    }
    if any(job.get(key) != expected for key, expected in exact.items()):
        raise ValueError("F3 reviewed reissue job/caps changed")
    if (
        job.get("proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or job.get("replacement_tuples") != EXPECTED_TUPLES
        or job.get("retained_survivor_qualification_rerun") is not False
        or job.get("automatic_retry") is not False
        or job.get("fallback_allowed") is not False
        or job.get("second_reissue_allowed") is not False
    ):
        raise ValueError("F3 reissue tuple/retry contract changed")
    output = workspace_path(job["output_namespace"], "F3 output")
    guard_dir = workspace_path(value["guard_directory"], "F3 guard directory")
    cache_job = workspace_path(value["cache_directory"], "F3 cache directory") / job_id
    if output.exists():
        raise FileExistsError("F3 reissue output namespace must be new")
    if phase in {"guard", "preflight"} and (guard_dir.exists() or cache_job.exists()):
        raise FileExistsError("F3 reissue Guard/cache paths must be new")
    if phase == "runner" and (not guard_dir.is_dir() or not cache_job.is_dir()):
        raise ValueError("F3 reissue runner lacks Guard-created paths")
    return value, job


def prepare_contract(manifest, job):
    _overlay, patched, overlay_preflight = load_overlay()
    proposal, retained_a, retained_b = patched.prepare_contract(manifest, job)
    if (
        proposal["proposal_sha256"] != EXPECTED_PROPOSAL_SHA256
        or [item[-1] for item in job["replacement_tuples"]]
        != ["r1505", "r2180", "r3677"]
        or retained_a["spec"]["recipe"]["recipe_id"] != "f3-final-pose-v3-r0005"
    ):
        raise ValueError("F3 reissue proposal/retained survivor changed")
    return patched, proposal, retained_a, retained_b, overlay_preflight


def preflight(manifest_path, job_id):
    manifest, job = load_manifest(manifest_path, job_id, phase="preflight")
    _patched, proposal, retained_a, retained_b, overlay_preflight = prepare_contract(
        manifest, job
    )
    return {
        "schema_version": "cmf_f3_zero_scene_wiring_reissue_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "overlay_preflight": overlay_preflight,
        "replacement_recipe_sha256s": [
            item["recipe_sha256"] for item in proposal["replacement_candidates"]
        ],
        "retained_recipe_id": retained_a["spec"]["recipe"]["recipe_id"],
        "retained_stage_b_receipt_sha256": retained_b["terminal"]["receipt_sha256"],
        "retained_survivor_qualification_rerun": False,
        "reissue_count_cap": 1,
        "output_created": False,
        "scene_created": False,
        "gpu_context_created": False,
        "pass": True,
    }


def run_gate(manifest, job, output):
    patched, _proposal, _retained_a, _retained_b, overlay_preflight = (
        prepare_contract(manifest, job)
    )
    result = patched.run_gate(manifest, job, output)
    result["wiring_overlay_sha256"] = OVERLAY_SHA256
    result["wiring_overlay_preflight"] = overlay_preflight
    result["reissue_count"] = 1
    result["second_reissue_allowed"] = False
    return result


def write_new(path, value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    base_value = canonical_jsonable(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(base_value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
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
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--job-id", default=EXPECTED_JOB_ID)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--overlay-only", action="store_true")
    args = parser.parse_args(argv)
    if args.overlay_only:
        _overlay, _patched, overlay_preflight = load_overlay()
        print(json.dumps(overlay_preflight, sort_keys=True))
        return 0
    if args.manifest is None:
        raise ValueError("F3 manifest is required outside overlay-only mode")
    if args.preflight_only:
        print(json.dumps(preflight(args.manifest, args.job_id), sort_keys=True))
        return 0
    manifest, job = load_manifest(args.manifest, args.job_id, phase="runner")
    if (
        not os.environ.get("CUDA_VISIBLE_DEVICES")
        or os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX") is None
        or os.environ.get("LD_LIBRARY_PATH")
    ):
        raise PermissionError("F3 reissue runner lacks clean UUID-bound Guard environment")
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
            "schema_version": "cmf_f3_zero_scene_wiring_reissue_terminal_v1",
            "manifest_sha256": manifest["manifest_sha256"],
            "job_id": args.job_id,
            "result": result,
            "error": error,
            "pass": error is None and bool(result) and result.get("gate_pass") is True,
            "reissue_count": 1,
            "second_reissue_allowed": False,
            "formal_data": False,
            "stage1_authorized": False,
        }
    )
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
