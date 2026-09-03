#!/usr/bin/env python3
"""Approved F3 centralized-replacement qualification and physical Gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import traceback
from unittest.mock import patch


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
BASE_HELPER = WORKSPACE / "Robotwin2/post_recovery_gate_v1/job_runner.py"
BASE_HELPER_SHA256 = "2d6dd7fc8e50539eb10163888cacadd6fab95664417a07839be15fcece2b5af6"
EXPECTED_SOURCE = "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
EXPECTED_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_STATUS = "APPROVED_F3_CENTRALIZED_REPLACEMENTS_RUN1_V1"
EXPECTED_JOB_ID = "f3-centralized-replacements-run1"


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


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


def load_base():
    if file_sha(BASE_HELPER) != BASE_HELPER_SHA256:
        raise RuntimeError("sealed F3 helper runner changed")
    spec = importlib.util.spec_from_file_location("cmf_f3_replacement_base", BASE_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load F3 helper runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base()


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
        raise ValueError("F3 manifest self-hash mismatch")
    if value.get("status") != EXPECTED_STATUS or value.get("approved") is not True:
        raise PermissionError("F3 replacement manifest is not approved")
    if value.get("gpu_execution_authorized") is not True or value.get("physical_execution_authorized") is not True:
        raise PermissionError("F3 GPU/physical execution is not authorized")
    if value.get("implementation_source_sha256") != EXPECTED_SOURCE or python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_SOURCE:
        raise ValueError("F3 controlled source differs from freeze")
    head = subprocess.run(["git", "-C", str(PROJECT), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    tracked = subprocess.run(["git", "-C", str(PROJECT), "status", "--porcelain", "--untracked-files=no"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    if value.get("robotwin_tracked_head") != EXPECTED_HEAD or head != EXPECTED_HEAD or tracked:
        raise ValueError("official RoboTwin tracked source changed")
    if value.get("allowed_physical_gpu_indices") != list(range(8)) or value.get("one_job_per_gpu") is not True or value.get("root_sharding") is not False:
        raise ValueError("F3 GPU scheduling contract changed")
    for key in ("stage0_reopened", "stage1_authorized", "formal_360_authorized", "training_authorized", "h_reveal_authorized", "compression_authorized", "pi05_authorized", "formal_data"):
        if value.get(key) is not False:
            raise ValueError(f"forbidden F3 stage enabled: {key}")
    for path_key, sha_key in (
        ("runner_script_path", "runner_script_sha256"),
        ("guard_script_path", "guard_script_sha256"),
        ("external_review_decision_path", "external_review_decision_file_sha256"),
        ("retained_stage_a_path", "retained_stage_a_file_sha256"),
        ("retained_stage_b_path", "retained_stage_b_file_sha256"),
    ):
        bound = workspace_path(value[path_key], path_key, must_file=True)
        if file_sha(bound) != value[sha_key]:
            raise ValueError(f"F3 bound file hash changed: {path_key}")
    assets = value.get("asset_hashes_by_family", {}).get("F3", {})
    if not assets:
        raise ValueError("F3 asset map missing")
    for relative, expected in assets.items():
        if file_sha(PROJECT / relative) != expected:
            raise ValueError(f"F3 asset changed: {relative}")
    jobs = value.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1 or jobs[0].get("job_id") != job_id or job_id != EXPECTED_JOB_ID:
        raise ValueError("F3 exact job lookup failed")
    job = jobs[0]
    if job.get("family") != "F3" or job.get("mode") != "F3_CENTRALIZED_REPLACEMENT_GATE_V1":
        raise ValueError("F3 dispatch mode changed")
    exact = {
        "planner_query_cap": 30,
        "planner_scene_cap": 6,
        "physical_candidate_cap": 4,
        "conditional_no_suffix_scene_cap": 3,
    }
    for key, expected in exact.items():
        if job.get(key) != expected:
            raise ValueError(f"F3 reviewed cap changed: {key}")
    if job.get("retained_survivor_qualification_rerun") is not False or job.get("automatic_retry") is not False or job.get("fallback_allowed") is not False:
        raise ValueError("F3 retained rerun/retry/fallback enabled")
    output = workspace_path(job["output_namespace"], "F3 output")
    guard_dir = workspace_path(value["guard_directory"], "F3 guard directory")
    cache_job = workspace_path(value["cache_directory"], "F3 cache directory") / job_id
    if output.exists():
        raise FileExistsError("F3 output namespace must be new")
    if phase in {"guard", "preflight"} and (guard_dir.exists() or cache_job.exists()):
        raise FileExistsError("F3 Guard/cache paths must be new")
    if phase == "runner" and (not guard_dir.is_dir() or not cache_job.is_dir()):
        raise ValueError("F3 runner lacks Guard-created paths")
    return value, job


def prepare_contract(manifest, job):
    from controlled_multi_future.f3_post_rotation1_replacement_proposal_v1 import (
        build_f3_post_rotation1_replacement_proposal_v1,
        validate_f3_post_rotation1_replacement_proposal_v1,
    )

    proposal = build_f3_post_rotation1_replacement_proposal_v1()
    if proposal["proposal_sha256"] != job["proposal_sha256"] or not validate_f3_post_rotation1_replacement_proposal_v1(proposal)["pass"]:
        raise ValueError("F3 approved replacement proposal changed")
    retained_a = json.loads(Path(manifest["retained_stage_a_path"]).read_text(encoding="utf-8"))
    retained_b = json.loads(Path(manifest["retained_stage_b_path"]).read_text(encoding="utf-8"))
    if retained_a.get("terminal", {}).get("stage_a_pass") is not True or retained_b.get("terminal", {}).get("stage_b_pass") is not True:
        raise ValueError("F3 retained r0005 survivor terminal changed")
    if retained_a["spec"]["recipe"]["recipe_sha256"] != proposal["retained_prior_survivor"]["recipe_sha256"]:
        raise ValueError("F3 retained survivor recipe changed")
    return proposal, retained_a, retained_b


def preflight(manifest_path, job_id):
    manifest, job = load_manifest(manifest_path, job_id, phase="preflight")
    proposal, retained_a, retained_b = prepare_contract(manifest, job)
    return {
        "schema_version": "cmf_f3_centralized_replacement_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "replacement_recipe_sha256s": [item["recipe_sha256"] for item in proposal["replacement_candidates"]],
        "retained_recipe_sha256": retained_a["spec"]["recipe"]["recipe_sha256"],
        "retained_stage_b_receipt_sha256": retained_b["terminal"]["receipt_sha256"],
        "output_created": False,
        "scene_created": False,
        "gpu_context_created": False,
        "pass": True,
    }


def run_gate(manifest, job, output):
    from controlled_multi_future.f3_asset_grasp_qualification_v2 import build_f3_asset_grasp_qualification_v2
    from controlled_multi_future.f3_final_pose_search_v3 import build_f3_final_pose_recipe_universe_v3
    from controlled_multi_future.f3_lift_anchored_event_center_v1 import audit_f3_lift_anchored_stage_b_targets_v1, build_f3_lift_anchored_stage_b_targets_v1
    from controlled_multi_future.f3_planner_integration_v3_1 import build_f3_stage_a_planner_spec_v3_1, build_f3_stage_b_planner_spec_v3_1, run_f3_stage_a_planner_v3_1, run_f3_stage_b_planner_v3_1
    from controlled_multi_future.f3_shared_v_physical_v1 import build_f3_shared_v_physical_spec_v1, run_f3_shared_v_physical_v1
    from controlled_multi_future.high_level_runtime_specs_v1 import build_f3_runtime_spec_v1
    from controlled_multi_future.planner_qualification_manifests_v2_3 import _f3_scene_binding

    proposal, retained_a, retained_b = prepare_contract(manifest, job)
    universe = build_f3_final_pose_recipe_universe_v3()["recipes"]
    tuples = build_f3_asset_grasp_qualification_v2()["grasp_tuples"]
    planner_rows = []
    new_survivors = []
    planner_queries = 0
    for index, frozen in enumerate(proposal["replacement_candidates"], start=1):
        recipe = next(item for item in universe if item["recipe_sha256"] == frozen["recipe_sha256"])
        entry = {"recipe": recipe, "scene_binding": _f3_scene_binding(recipe)}
        tuple_value = next(item for item in tuples if item["asset"] == recipe["asset"] and item["arm"] == recipe["arm"])
        candidate_dir = output / f"candidate_{index:02d}_{recipe['recipe_id']}"
        candidate_dir.mkdir(parents=True, exist_ok=False)
        legacy_a = build_f3_runtime_spec_v1(tuple_value["tuple_id"], purpose="f3_level1_planner")
        spec_a = build_f3_stage_a_planner_spec_v3_1(recipe, entry["scene_binding"], slot_id=f"{job['job_id']}-a-{index}", panel_sha256=proposal["proposal_sha256"], planner_reset_nonce=2026090700 + 10 * index)
        adapter_a = base.adapter_for("F3", legacy_a, candidate_dir / "scene_a", manifest["implementation_source_sha256"])
        error_a = None
        with base.opened_scene(adapter_a, legacy_a, phase="F3_CENTRALIZED_REPLACEMENT_STAGE_A", program=None, family="F3") as (scene, context_a):
            try:
                binding_a = base.prepare_f3_scene(scene, adapter_a, recipe, entry["scene_binding"])
                terminal_a = run_f3_stage_a_planner_v3_1(scene, spec_a)
            except BaseException as exc:
                binding_a = getattr(exc, "evidence", None)
                terminal_a = None
                error_a = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        base.write_new(candidate_dir / "stage_a.json", {"spec": spec_a, "binding": binding_a, "terminal": terminal_a, "error": error_a, "cleanup": context_a.cleanup_receipt})
        a_queries = len(((terminal_a or {}).get("planner_result") or {}).get("segment_receipts", []))
        planner_queries += a_queries
        if not isinstance(terminal_a, dict) or terminal_a.get("stage_a_pass") is not True:
            planner_rows.append({"candidate": frozen, "stage_a_pass": False, "stage_b_pass": False, "stage_a_queries": a_queries, "failure": "F3_STAGE_A_FAILED"})
            continue
        spec_b = build_f3_stage_b_planner_spec_v3_1(terminal_a, spec_a, slot_id=f"{job['job_id']}-b-{index}", selection_policy_sha256=proposal["proposal_sha256"], planner_reset_nonce=2026090701 + 10 * index)
        legacy_b = build_f3_runtime_spec_v1(tuple_value["tuple_id"], purpose="f3_level1_planner")
        adapter_b = base.adapter_for("F3", legacy_b, candidate_dir / "scene_b", manifest["implementation_source_sha256"])
        error_b = None
        target_audit = None
        with base.opened_scene(adapter_b, legacy_b, phase="F3_CENTRALIZED_REPLACEMENT_STAGE_B", program=None, family="F3") as (scene, context_b):
            try:
                binding_b = base.prepare_f3_scene(scene, adapter_b, recipe, entry["scene_binding"])
                raw_targets = build_f3_lift_anchored_stage_b_targets_v1(spec_b["stage_a_lift_pose"])
                target_audit = audit_f3_lift_anchored_stage_b_targets_v1(spec_b["stage_a_lift_pose"], raw_targets)
                names = ("central_1", "V_plus", "V_minus", "central_2", "H_plus", "H_minus", "central_3")
                targets = [{"segment_id": f"f3_v3_stage_b_{name}", "pose": item["pose"]} for name, item in zip(names, raw_targets)]
                with patch("controlled_multi_future.f3_planner_integration_v3_1.build_f3_stage_b_targets_v3_1", return_value=targets):
                    terminal_b = run_f3_stage_b_planner_v3_1(scene, spec_b)
            except BaseException as exc:
                binding_b = getattr(exc, "evidence", None)
                terminal_b = None
                error_b = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        base.write_new(candidate_dir / "stage_b.json", {"spec": spec_b, "binding": binding_b, "target_audit": target_audit, "terminal": terminal_b, "error": error_b, "cleanup": context_b.cleanup_receipt})
        b_queries = len(((terminal_b or {}).get("planner_result") or {}).get("segment_receipts", []))
        planner_queries += b_queries
        passed_b = isinstance(terminal_b, dict) and terminal_b.get("stage_b_pass") is True
        planner_rows.append({"candidate": frozen, "stage_a_pass": True, "stage_b_pass": passed_b, "stage_a_queries": a_queries, "stage_b_queries": b_queries, "failure": None if passed_b else "F3_STAGE_B_FAILED"})
        if passed_b:
            new_survivors.append({"frozen": frozen, "recipe": recipe, "entry": entry, "spec_a": spec_a, "terminal_a": terminal_a, "spec_b": spec_b, "terminal_b": terminal_b, "dir": candidate_dir})
    if planner_queries > 30:
        raise RuntimeError("F3 replacement qualification exceeded 30 queries")
    physical_rows = []
    if new_survivors:
        retained_recipe = retained_a["spec"]["recipe"]
        cumulative = [{"frozen": proposal["retained_prior_survivor"], "recipe": retained_recipe, "entry": {"scene_binding": retained_a["spec"]["scene_binding"]}, "spec_a": retained_a["spec"], "terminal_a": retained_a["terminal"], "spec_b": retained_b["spec"], "terminal_b": retained_b["terminal"], "dir": output / "retained_r0005"}] + new_survivors
        for index, survivor in enumerate(cumulative[:4], start=1):
            survivor["dir"].mkdir(parents=True, exist_ok=True)
            raw_targets = build_f3_lift_anchored_stage_b_targets_v1(survivor["spec_b"]["stage_a_lift_pose"])
            names = ("central_1", "V_plus", "V_minus", "central_2", "H_plus", "H_minus", "central_3")
            targets = [{"segment_id": f"f3_v3_stage_b_{name}", "pose": item["pose"]} for name, item in zip(names, raw_targets)]
            with patch("controlled_multi_future.f3_shared_v_physical_v1.build_f3_stage_b_targets_v3_1", return_value=targets):
                physical_spec = build_f3_shared_v_physical_spec_v1(survivor["spec_a"], survivor["terminal_a"], survivor["spec_b"], survivor["terminal_b"], slot_id=f"{job['job_id']}-physical-{index}", planner_reset_nonce=2026090800 + index)
            base.write_new(survivor["dir"] / "physical_spec.json", physical_spec)
            adapter = base.adapter_for("F3", physical_spec["legacy_scene_spec"], survivor["dir"] / "physical_scene", manifest["implementation_source_sha256"])
            def execute(scene, s=survivor, spec=physical_spec, adapter=adapter):
                base.prepare_f3_scene(scene, adapter, s["recipe"], s["entry"]["scene_binding"])
                return run_f3_shared_v_physical_v1(scene, spec)
            receipt = base.record_physical_scene(family="F3", adapter=adapter, legacy_scene_spec=physical_spec["legacy_scene_spec"], output=survivor["dir"] / "physical", trace_actor_name="bottle", arm=physical_spec["arm"], execute=execute, phase="F3_CENTRALIZED_REPLACEMENT_PHYSICAL")
            terminal = receipt.get("result") or {}
            passed = terminal.get("shared_v_physically_qualified") is True
            physical_rows.append({"candidate": survivor["frozen"], "physical_pass": passed, "physical_planner_queries": terminal.get("planner_query_count", 0), "failure": None if passed else ((receipt.get("error") or {}).get("message") or "F3_PHYSICAL_FAILED"), "scene_receipt_sha256": receipt["receipt_sha256"]})
    successes = [item for item in physical_rows if item["physical_pass"]]
    return {
        "family": "F3",
        "proposal_sha256": proposal["proposal_sha256"],
        "retained_survivor_qualification_rerun": False,
        "planner_rows": planner_rows,
        "replacement_planner_queries": planner_queries,
        "new_survivor_count": len(new_survivors),
        "cumulative_survivor_count": 1 + len(new_survivors),
        "physical_rows": physical_rows,
        "physical_execution_count": len(physical_rows),
        "physical_success_count": len(successes),
        "gate_pass": len(successes) >= 2,
        "conditional_no_suffix_triggered": len(successes) >= 2,
        "conditional_no_suffix_executed": False,
        "accepted_trajectory_count": 0,
        "formal_data": False,
    }


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


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
        raise PermissionError("F3 runner lacks clean UUID-bound Guard environment")
    output = Path(job["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "job_start.json", {"manifest_sha256": manifest["manifest_sha256"], "job_id": args.job_id})
    error = None
    result = None
    try:
        result = run_gate(manifest, job, output)
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    terminal = canonical_jsonable({"schema_version": "cmf_f3_centralized_replacement_job_terminal_v1", "manifest_sha256": manifest["manifest_sha256"], "job_id": args.job_id, "result": result, "error": error, "pass": error is None and bool(result) and result.get("gate_pass") is True, "formal_data": False, "stage1_authorized": False})
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
