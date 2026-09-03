#!/usr/bin/env python3
"""Direct F4 root runner with strict finalization and CPU entry preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback


RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from manifest_contract import (  # noqa: E402
    RUNNER_ENTRY,
    canonical_hash,
    file_sha,
    load_and_validate_manifest_job,
)


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
BASE_RUNNER = WORKSPACE / "Robotwin2/production_micro_gate_v1/job_runner.py"
BASE_RUNNER_SHA256 = "376ddfbe07b1c9ae3e6e3b2d1975344a8605c6e81e49f27e92241c88a851a1d4"


def _load_base_runner():
    if file_sha(BASE_RUNNER) != BASE_RUNNER_SHA256:
        raise RuntimeError("sealed base F4 function source changed")
    spec = importlib.util.spec_from_file_location("cmf_f4_v2_bound_base_runner", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed base F4 function source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dispatch = getattr(module, "run_f4_development_r_pc_root", None)
    if not callable(dispatch):
        raise RuntimeError("sealed base lacks run_f4_development_r_pc_root")
    return module


def _build_bound_specs(job):
    from controlled_multi_future.f4_full_program_physical_v1 import (
        PROGRAM_IDS,
        build_f4_full_program_physical_spec_v1,
    )
    from controlled_multi_future.planner_qualification_manifests_v2_3 import (
        build_f4_program_panel_manifest_v1_1,
    )

    panel = build_f4_program_panel_manifest_v1_1()
    source = panel["source_candidate"]
    candidate = panel["candidates"][0]
    if (
        candidate["candidate_id"] != job["candidate_id"]
        or candidate["candidate_sha256"] != job["candidate_sha256"]
        or list(PROGRAM_IDS) != job["program_order"]
    ):
        raise RuntimeError("F4 candidate/program dispatch binding changed")
    specs = {}
    terminal_receipts = {}
    planner_accounting = {}
    for program_id in PROGRAM_IDS:
        record = job["source_planner_terminals"][program_id]
        path = Path(record["path"])
        if file_sha(path) != record["file_sha256"]:
            raise RuntimeError(f"F4 {program_id} planner source changed")
        envelope = json.loads(path.read_text(encoding="utf-8"))
        prior_spec = envelope.get("spec")
        terminal = envelope.get("terminal")
        if not isinstance(prior_spec, dict) or not isinstance(terminal, dict):
            raise RuntimeError(f"F4 {program_id} planner source incomplete")
        payload = dict(terminal)
        digest = payload.pop("receipt_sha256", None)
        if digest != canonical_hash(payload):
            raise RuntimeError(f"F4 {program_id} planner terminal self-hash changed")
        accounting = terminal.get("planner_query_accounting")
        if accounting != {
            "budget_exhaustion_is_infrastructure_error": True,
            "chain_queries": 30,
            "target_construction_queries": 12,
            "total_queries": 42,
            "total_query_limit": 42,
        }:
            raise RuntimeError(f"F4 {program_id} planner accounting is not 12+30=42")
        specs[program_id] = build_f4_full_program_physical_spec_v1(
            source,
            candidate,
            terminal,
            program_id=program_id,
            slot_id=prior_spec["slot_id"],
            planner_reset_nonce=prior_spec["planner_reset_nonce"],
            isolation_gate_receipt_sha256=job["isolation_gate_receipt_sha256"],
        )
        terminal_receipts[program_id] = digest
        planner_accounting[program_id] = dict(accounting)
    scene_hashes = {value["legacy_scene_spec_sha256"] for value in specs.values()}
    if scene_hashes != {job["planned_scene_spec_sha256"]}:
        raise RuntimeError("F4 full-program specs do not share the frozen scene")
    return {
        "program_order": list(PROGRAM_IDS),
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "planned_scene_spec_sha256": next(iter(scene_hashes)),
        "full_program_spec_sha256s": {
            key: value["spec_sha256"] for key, value in specs.items()
        },
        "planner_terminal_receipt_sha256s": terminal_receipts,
        "source_planner_query_accounting": planner_accounting,
        "aggregate_suffix_query_count": sum(
            item["total_queries"] for item in planner_accounting.values()
        ),
    }


def select_f4_dispatch_runner_entry(
    manifest_path: Path,
    job_id: str,
    *,
    allow_lifecycle_fixture: bool,
) -> dict:
    environment = dict(os.environ)
    lifecycle = environment.get("CMF_F4_CPU_LIFECYCLE_PREFLIGHT") == "1"
    if allow_lifecycle_fixture is not lifecycle:
        raise RuntimeError("F4 lifecycle fixture flag/environment mismatch")
    validated = load_and_validate_manifest_job(
        manifest_path,
        job_id,
        phase=RUNNER_ENTRY,
        require_execution_authorized=False if lifecycle else True,
        allow_lifecycle_fixture=allow_lifecycle_fixture,
        environment=environment,
    )
    base = _load_base_runner()
    dispatch = getattr(base, "run_f4_development_r_pc_root")
    bound = _build_bound_specs(validated["job"])
    output = Path(validated["job"]["output_namespace"])
    if output.exists():
        raise RuntimeError("F4 runner-entry preflight created output")
    result = {
        "schema_version": "cmf_f4_development_root_v2_runner_entry_preflight_v1",
        "manifest_sha256": validated["manifest_sha256"],
        "job_id": job_id,
        "phase": RUNNER_ENTRY,
        "dispatch_function": "run_f4_development_r_pc_root",
        "dispatch_callable": callable(dispatch),
        **bound,
        "scene_created": False,
        "gpu_context_created": False,
        "output_created": False,
        "nvidia_smi_called": False,
        "planner_called": False,
        "authorization_consumed": False,
        "pass": True,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def _action_scene_count(cleanup_records) -> int:
    return sum(
        str(item.get("phase", "")) == "canonical_prefix_reference"
        or str(item.get("phase", "")).startswith("suffix_preflight:")
        or str(item.get("phase", "")).startswith("strict_prefix_branch:")
        for item in cleanup_records
    )


def finalize_f4_root_result(result, job, *, output: Path) -> dict:
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    value = canonical_jsonable(result)
    root = value.get("root_receipt") if isinstance(value, dict) else None
    if not isinstance(root, dict):
        return {
            "schema_version": "cmf_f4_development_root_v2_finalizer_v1",
            "accepted": False,
            "checks": {"root_receipt_structured": False},
            "failure": "missing_structured_root_receipt",
        }
    branches = root.get("branch_receipts") or []
    cleanup = root.get("cleanup_records") or []
    suffix = root.get("suffix_planner_receipts") or []
    root_finalization = root.get("root_finalization") or {}
    branch_programs = [item.get("program_id") for item in branches]
    raw_count = sum(isinstance(item.get("raw_manifest"), dict) for item in branches)
    video_count = sum(
        item.get("development_video_integrity", {}).get("pass") is True
        for item in branches
    )
    verifier_count = sum(
        item.get("verifier", {}).get("pass") is True for item in branches
    )
    raw_integrity = len(branches) == 3 and all(
        isinstance(item.get("raw_manifest"), dict)
        and isinstance(item["raw_manifest"].get("raw_streams_npz_sha256"), str)
        and isinstance(item["raw_manifest"].get("manifest_file_sha256"), str)
        and isinstance(
            item["raw_manifest"].get("manifest_integrity_sidecar_sha256"), str
        )
        for item in branches
    )
    semantic = [
        item.get("verifier", {}).get("family_semantic_verifier", {})
        for item in branches
    ]
    role_checks = [
        role.get("checks", {})
        for branch in semantic
        for role in branch.get("role_receipts", [])
    ]
    branch_final_checks = [branch.get("checks", {}) for branch in semantic]
    frozen_execution_zero = all(
        item.get("suffix_execution_planner_query_delta") == 0 for item in branches
    ) if len(branches) == 3 else False
    cleanup_pass = len(cleanup) == job["maximum_fresh_scenes"] and all(
        item.get("cleanup_safety_pass") is True
        and item.get("orphan_process_count") == 0
        for item in cleanup
    )
    action_scenes = _action_scene_count(cleanup)
    total_prefix_replays = int(root.get("suffix_prefix_replay_count", -1)) + int(
        root.get("branch_prefix_replay_count", -1)
    )
    checks = {
        "root_receipt_structured": True,
        "root_status_accepted": root.get("status") == "accepted",
        "result_development_root_pass": value.get("development_root_pass") is True,
        "task_feasibility_three_of_three": len(root.get("task_physical_feasibility_receipts") or []) == 3
        and all(
            item.get("status") == "passed"
            for item in root.get("task_physical_feasibility_receipts") or []
        ),
        "one_candidate_freeze": root.get("freeze_call_count") == 1,
        "one_canonical_prefix": root.get("canonical_prefix_generation_count") == 1
        and root.get("canonical_prefix_reference_execution_count") == 1,
        "three_suffix_preflights": len(suffix) == 3,
        "suffix_prefix_replays_three": root.get("suffix_prefix_replay_count") == 3,
        "branch_prefix_replays_three": root.get("branch_prefix_replay_count") == 3,
        "total_prefix_replays_six": total_prefix_replays == 6,
        "three_branch_executions": root.get("branch_execution_attempt_count") == 3,
        "three_branches_accepted": len(branches) == 3
        and branch_programs == job["program_order"]
        and all(item.get("status") == "accepted" for item in branches),
        "three_raw_trajectories": raw_count == 3,
        "raw_integrity_fields_complete": raw_integrity,
        "three_debug_videos": video_count == 3,
        "three_family_verifiers": verifier_count == 3,
        "selected_contact_identity_continuity": len(role_checks) == 9
        and all(
            item.get("selected_contact_continuity") is True
            and item.get("selected_contact_actor_identity") is True
            for item in role_checks
        ),
        "prior_slots_and_untouched_roles_preserved": len(role_checks) == 9
        and all(
            item.get("prior_slots_preserved") is True
            and item.get("uncompleted_roles_preserved") is True
            for item in role_checks
        ),
        "all_final_slots_and_common_x_preserved": len(branch_final_checks) == 3
        and all(
            item.get("all_final_slots") is True
            and item.get("common_x_preserved") is True
            for item in branch_final_checks
        ),
        "gripper_open_and_arm_neutral": len(branch_final_checks) == 3
        and all(
            item.get("selected_gripper_open") is True
            and item.get("selected_arm_neutral_position") is True
            and item.get("selected_arm_neutral_orientation") is True
            for item in branch_final_checks
        ),
        "branch_execution_planner_delta_zero": frozen_execution_zero,
        "root_finalizer_accepted": root_finalization.get("accepted") is True,
        "same_current_anchor_prefix": all(
            root_finalization.get("checks", {}).get(key) is True
            for key in (
                "branch_current_matches_reference",
                "branch_anchor_equivalent",
                "one_executed_prefix_action_hash",
                "prefix_start_anchor_equivalent",
                "prefix_end_state_equivalent",
            )
        ),
        "final_state_equivalence": root_finalization.get("checks", {}).get(
            "final_state_equivalence"
        )
        is True,
        "planner_total_136": root.get("planner_query_count_total") == 136,
        "canonical_prefix_planner_10": root.get("canonical_prefix_planner_query_count") == 10,
        "suffix_planner_total_126": root.get("suffix_planner_query_count_total") == 126,
        "fresh_scenes_11": len(cleanup) == 11,
        "robot_action_scenes_7": action_scenes == 7,
        "cleanup_orphan_pass": cleanup_pass,
        "root_receipt_file_present": (output / "development_root/root_receipt.json").is_file(),
    }
    accepted = all(checks.values())
    finalizer = {
        "schema_version": "cmf_f4_development_root_v2_finalizer_v1",
        "accepted": accepted,
        "checks": checks,
        "counts": {
            "planner_queries": root.get("planner_query_count_total"),
            "fresh_scenes": len(cleanup),
            "robot_action_scenes": action_scenes,
            "suffix_prefix_replays": root.get("suffix_prefix_replay_count"),
            "branch_prefix_replays": root.get("branch_prefix_replay_count"),
            "total_prefix_replays": total_prefix_replays,
            "branch_executions": root.get("branch_execution_attempt_count"),
            "raw_trajectories": raw_count,
            "videos": video_count,
            "accepted_development_roots": 1 if accepted else 0,
            "accepted_development_trajectories": 3 if accepted else 0,
            "formal_trajectories": 0,
        },
        "failure": None
        if accepted
        else next((key for key, passed in checks.items() if not passed), "unknown"),
    }
    finalizer["receipt_sha256"] = canonical_hash(finalizer)
    return finalizer


def write_new(path: Path, value) -> None:
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = canonical_jsonable(value)
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
    parser.add_argument("--preflight-runner-entry", action="store_true")
    parser.add_argument("--allow-lifecycle-fixture", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_runner_entry:
        receipt = select_f4_dispatch_runner_entry(
            args.manifest,
            args.job_id,
            allow_lifecycle_fixture=args.allow_lifecycle_fixture,
        )
        print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))
        return 0
    if args.allow_lifecycle_fixture:
        raise PermissionError("F4 lifecycle fixture can never execute a root")
    validated = load_and_validate_manifest_job(
        args.manifest,
        args.job_id,
        phase=RUNNER_ENTRY,
        require_execution_authorized=True,
        environment=os.environ,
    )
    if os.environ.get("LD_LIBRARY_PATH"):
        raise RuntimeError("F4 runner inherited forbidden LD_LIBRARY_PATH")
    output = Path(validated["job"]["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    start = {
        "schema_version": "cmf_f4_development_root_v2_job_start_v1",
        "run_id": validated["manifest"]["run_id"],
        "job_id": args.job_id,
        "manifest_sha256": validated["manifest_sha256"],
        "physical_gpu_index": int(os.environ["CMF_GPU_GUARD_PHYSICAL_INDEX"]),
        "gpu_uuid": os.environ["CUDA_VISIBLE_DEVICES"],
    }
    start["receipt_sha256"] = canonical_hash(start)
    write_new(output / "job_start.json", start)
    base = _load_base_runner()
    result = None
    error = None
    finalizer = None
    try:
        result = base.run_f4_development_r_pc_root(
            validated["job"],
            output,
            validated["manifest"]["implementation_source_sha256"],
        )
        result = canonical_jsonable(result)
        finalizer = finalize_f4_root_result(result, validated["job"], output=output)
    except BaseException as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    terminal = canonical_jsonable(
        {
            "schema_version": "cmf_f4_development_root_v2_job_terminal_v1",
            "run_id": validated["manifest"]["run_id"],
            "job_id": args.job_id,
            "manifest_sha256": validated["manifest_sha256"],
            "result": result,
            "root_finalizer": finalizer,
            "error": error,
            "pass": error is None
            and isinstance(finalizer, dict)
            and finalizer.get("accepted") is True,
            "formal_data": False,
            "stage1_authorized": False,
        }
    )
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0 if terminal["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
