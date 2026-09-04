#!/usr/bin/env python3
"""F4 Runtime V2.1 direct runner and independent disk finalizer."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping


RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from manifest_contract import (  # noqa: E402
    EXPECTED_PROGRAMS,
    RUNNER_ENTRY,
    canonical_hash,
    file_sha,
    load_and_validate_manifest_job,
)


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
V2_RUNNER = (
    WORKSPACE
    / "Vault-on-Fvl09/数据构造/实现审计/f4_development_root_runtime_v2/job_runner.py"
)
V2_RUNNER_SHA256 = "e9217b437e360e0fdd2540420ff86b094c5ec4f8e59c1aebd37458aa1e89e175"


def _load_v2_runner():
    if file_sha(V2_RUNNER) != V2_RUNNER_SHA256:
        raise RuntimeError("sealed Runtime V2 runner changed")
    spec = importlib.util.spec_from_file_location("cmf_f4_runtime_v2_sealed_runner", V2_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed Runtime V2 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("_load_base_runner", "_build_bound_specs"):
        if not callable(getattr(module, name, None)):
            raise RuntimeError(f"sealed Runtime V2 runner lacks {name}")
    return module


def _canonical_jsonable(value: Any) -> Any:
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    return canonical_jsonable(value)


def _read_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except BaseException as exc:
        raise RuntimeError(f"{label} cannot be reloaded from disk") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} is not a mapping")
    return dict(value)


def _safe_raw_audit(raw_dir: Path) -> dict[str, Any]:
    from controlled_multi_future.raw_writer import verify_raw_artifact_integrity

    try:
        audit = _canonical_jsonable(verify_raw_artifact_integrity(raw_dir))
        manifest = audit.get("manifest", {}) if isinstance(audit, Mapping) else {}
        sidecar = (
            audit.get("integrity_sidecar", {}) if isinstance(audit, Mapping) else {}
        )
        return {
            "path": str(raw_dir.resolve()),
            "pass": audit.get("pass") is True,
            "checks": audit.get("checks", {}),
            "manifest": manifest,
            "integrity_sidecar": sidecar,
            "labels": {
                "formal_data": manifest.get("formal_data"),
                "stage0_data": manifest.get("stage0_data"),
                "stage0_authorized": manifest.get("stage0_authorized"),
                "development_data": manifest.get("development_data"),
            },
            "raw_streams_file_sha256": file_sha(raw_dir / "raw_streams.npz")
            if (raw_dir / "raw_streams.npz").is_file()
            else None,
            "manifest_file_sha256": file_sha(raw_dir / "manifest.json")
            if (raw_dir / "manifest.json").is_file()
            else None,
            "sidecar_file_sha256": file_sha(raw_dir / "manifest.sha256.json")
            if (raw_dir / "manifest.sha256.json").is_file()
            else None,
        }
    except BaseException as exc:
        return {
            "path": str(raw_dir.resolve()),
            "pass": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _safe_video_audit(receipt: Any, expected_path: Path) -> dict[str, Any]:
    from controlled_multi_future.development_video_capture_v1 import (
        validate_development_trajectory_mp4_receipt_v1,
    )

    try:
        audit = _canonical_jsonable(
            validate_development_trajectory_mp4_receipt_v1(
                receipt, expected_path=expected_path
            )
        )
        return {
            "path": str(expected_path.resolve()),
            "pass": audit.get("pass") is True,
            "checks": audit.get("checks", {}),
            "file_sha256": file_sha(expected_path) if expected_path.is_file() else None,
            "bytes": expected_path.stat().st_size if expected_path.is_file() else None,
        }
    except BaseException as exc:
        return {
            "path": str(expected_path.resolve()),
            "pass": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _phase_category(phase: Any) -> str:
    text = str(phase)
    if text == "pristine":
        return "pristine"
    if text == "canonical_prefix_reference":
        return "canonical_prefix"
    if text.startswith("task_physical_feasibility:"):
        return "task_feasibility"
    if text.startswith("suffix_preflight:"):
        return "suffix_preflight"
    if text.startswith("strict_prefix_branch:"):
        return "strict_prefix_branch"
    return "unknown"


def _suffix_accounting(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for receipt in receipts:
        execution = receipt.get("execution_spec")
        execution = execution if isinstance(execution, Mapping) else {}
        planner_rows = execution.get("planner_query_receipts")
        segments = execution.get("segment_receipts")
        targets = execution.get("targets")
        planner_rows = planner_rows if isinstance(planner_rows, list) else []
        segments = segments if isinstance(segments, list) else []
        targets = targets if isinstance(targets, list) else []
        total = receipt.get("planner_query_count")
        chain = len(segments)
        target_construction = len(planner_rows) - chain
        rows.append(
            {
                "program_id": receipt.get("program_id"),
                "status": receipt.get("status"),
                "planner_solvable": receipt.get("planner_solvable"),
                "reported_total_queries": total,
                "planner_query_receipt_count": len(planner_rows),
                "target_count": len(targets),
                "chain_segment_receipt_count": chain,
                "derived_target_construction_queries": target_construction,
                "pass": receipt.get("status") == "passed"
                and receipt.get("planner_solvable") is True
                and total == 42
                and len(planner_rows) == 42
                and len(targets) == 30
                and chain == 30
                and target_construction == 12,
            }
        )
    return {
        "rows": rows,
        "program_order": [row["program_id"] for row in rows],
        "aggregate_queries": sum(
            int(row["reported_total_queries"])
            for row in rows
            if isinstance(row["reported_total_queries"], int)
        ),
        "pass": len(rows) == 3
        and [row["program_id"] for row in rows] == EXPECTED_PROGRAMS
        and all(row["pass"] for row in rows),
    }


def _minimal_failed_finalizer(failure: str, checks: Mapping[str, bool] | None = None) -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f4_development_root_v2_1_finalizer_v1",
        "accepted": False,
        "checks": dict(checks or {}),
        "counts": {
            "accepted_development_roots": 0,
            "accepted_development_trajectories": 0,
            "formal_trajectories": 0,
        },
        "failure": failure,
    }
    value["receipt_sha256"] = canonical_hash(value)
    return value


def finalize_f4_root_result(result: Any, job: Mapping[str, Any], *, output: Path) -> dict[str, Any]:
    """Reload and independently verify every accepted artifact from disk."""

    value = _canonical_jsonable(result)
    memory_root = value.get("root_receipt") if isinstance(value, Mapping) else None
    if not isinstance(memory_root, Mapping):
        return _minimal_failed_finalizer(
            "missing_structured_root_receipt", {"memory_root_receipt_structured": False}
        )
    root_path = Path(output) / "development_root/root_receipt.json"
    try:
        disk_root = _canonical_jsonable(_read_mapping(root_path, "root receipt"))
    except BaseException:
        return _minimal_failed_finalizer(
            "disk_root_receipt_missing_or_invalid",
            {"memory_root_receipt_structured": True, "disk_root_receipt_loaded": False},
        )
    memory_root = _canonical_jsonable(memory_root)
    root_matches = disk_root == memory_root

    disk_branches = disk_root.get("branch_receipts")
    disk_branches = disk_branches if isinstance(disk_branches, list) else []
    memory_branches = memory_root.get("branch_receipts")
    memory_branches = memory_branches if isinstance(memory_branches, list) else []
    disk_branch_programs = [
        item.get("program_id") if isinstance(item, Mapping) else None
        for item in disk_branches
    ]
    memory_branch_programs = [
        item.get("program_id") if isinstance(item, Mapping) else None
        for item in memory_branches
    ]
    exact_branch_structure = (
        len(disk_branches) == len(EXPECTED_PROGRAMS)
        and len(memory_branches) == len(EXPECTED_PROGRAMS)
        and all(isinstance(item, Mapping) for item in disk_branches)
        and all(isinstance(item, Mapping) for item in memory_branches)
        and disk_branch_programs == EXPECTED_PROGRAMS
        and memory_branch_programs == EXPECTED_PROGRAMS
    )
    disk_by_program = {
        item.get("program_id"): item for item in disk_branches if isinstance(item, Mapping)
    }
    memory_by_program = {
        item.get("program_id"): item for item in memory_branches if isinstance(item, Mapping)
    }
    branch_audits = []
    for program_id in EXPECTED_PROGRAMS:
        branch_dir = Path(output) / "development_root/branches" / program_id
        branch_path = branch_dir / "receipt.json"
        try:
            branch_file = _canonical_jsonable(_read_mapping(branch_path, f"{program_id} branch receipt"))
            file_loaded = True
        except BaseException as exc:
            branch_file = {}
            file_loaded = False
            branch_error = {"type": type(exc).__name__, "message": str(exc)}
        else:
            branch_error = None
        receipt_matches = (
            file_loaded
            and branch_file == disk_by_program.get(program_id)
            and branch_file == memory_by_program.get(program_id)
        )
        raw = _safe_raw_audit(branch_dir / "raw")
        raw_receipt = branch_file.get("raw_manifest")
        raw_receipt = raw_receipt if isinstance(raw_receipt, Mapping) else {}
        raw_receipt_manifest = dict(raw_receipt)
        raw_receipt_manifest_file_sha = raw_receipt_manifest.pop(
            "manifest_file_sha256", None
        )
        raw_receipt_sidecar_name = raw_receipt_manifest.pop(
            "manifest_integrity_sidecar", None
        )
        raw_receipt_sidecar_sha = raw_receipt_manifest.pop(
            "manifest_integrity_sidecar_sha256", None
        )
        raw_manifest_matches_receipt = (
            bool(raw_receipt)
            and raw_receipt_manifest == raw.get("manifest")
        )
        raw_hashes_match_receipt = (
            bool(raw_receipt)
            and raw_receipt.get("raw_streams_npz_sha256")
            == raw.get("raw_streams_file_sha256")
            and raw_receipt_manifest_file_sha == raw.get("manifest_file_sha256")
            and raw_receipt_sidecar_name == "manifest.sha256.json"
            and raw_receipt_sidecar_sha == raw.get("sidecar_file_sha256")
        )
        video_receipt = branch_file.get("development_video_receipt")
        video = _safe_video_audit(
            video_receipt, branch_dir / "video/trajectory.mp4"
        )
        raw_labels = raw.get("labels", {}) if isinstance(raw, Mapping) else {}
        checks = {
            "branch_receipt_loaded": file_loaded,
            "branch_receipt_matches_memory_and_root": receipt_matches,
            "branch_status_accepted": branch_file.get("status") == "accepted",
            "branch_verifier_pass": branch_file.get("verifier", {}).get("pass") is True,
            "branch_execution_planner_delta_zero": branch_file.get(
                "suffix_execution_planner_query_delta"
            )
            == 0,
            "raw_disk_integrity": raw.get("pass") is True,
            "raw_manifest_payload_matches_branch_receipt": raw_manifest_matches_receipt,
            "raw_file_hashes_match_branch_receipt": raw_hashes_match_receipt,
            "raw_development_labels": raw_labels.get("formal_data") is False
            and raw_labels.get("stage0_data") is False
            and raw_labels.get("stage0_authorized") is False,
            "mp4_disk_integrity": video.get("pass") is True,
        }
        branch_audits.append(
            {
                "program_id": program_id,
                "branch_receipt_path": str(branch_path.resolve()),
                "branch_receipt_file_sha256": file_sha(branch_path)
                if branch_path.is_file()
                else None,
                "receipt_error": branch_error,
                "raw_integrity": raw,
                "video_integrity": video,
                "checks": checks,
                "pass": all(checks.values()),
            }
        )

    suffix = disk_root.get("suffix_planner_receipts")
    suffix = suffix if isinstance(suffix, list) else []
    suffix_accounting = _suffix_accounting(suffix)
    cleanup = disk_root.get("cleanup_records")
    cleanup = cleanup if isinstance(cleanup, list) else []
    scene_ids = [item.get("scene_instance_id") for item in cleanup if isinstance(item, Mapping)]
    phases = Counter(_phase_category(item.get("phase")) for item in cleanup if isinstance(item, Mapping))
    expected_phases = Counter(
        {
            "pristine": 1,
            "task_feasibility": 3,
            "canonical_prefix": 1,
            "suffix_preflight": 3,
            "strict_prefix_branch": 3,
        }
    )
    cleanup_pass = len(cleanup) == 11 and all(
        item.get("cleanup_safety_pass") is True
        and item.get("orphan_process_count") == 0
        and item.get("scene_created") is True
        and item.get("scene_cleanup_attempted") is True
        and item.get("scene_cleanup_succeeded") is True
        for item in cleanup
        if isinstance(item, Mapping)
    )
    unique_scenes = (
        len(scene_ids) == 11
        and all(isinstance(item, str) and item for item in scene_ids)
        and len(set(scene_ids)) == 11
    )
    exact_phases = phases == expected_phases

    semantic = [
        item.get("verifier", {}).get("family_semantic_verifier", {})
        for item in disk_branches
        if isinstance(item, Mapping)
    ]
    role_checks = [
        role.get("checks", {})
        for branch in semantic
        if isinstance(branch, Mapping)
        for role in branch.get("role_receipts", [])
        if isinstance(role, Mapping)
    ]
    branch_final_checks = [
        branch.get("checks", {}) for branch in semantic if isinstance(branch, Mapping)
    ]
    root_finalization = disk_root.get("root_finalization")
    root_finalization = root_finalization if isinstance(root_finalization, Mapping) else {}
    root_final_checks = root_finalization.get("checks")
    root_final_checks = root_final_checks if isinstance(root_final_checks, Mapping) else {}
    task_feasibility = disk_root.get("task_physical_feasibility_receipts")
    task_feasibility = task_feasibility if isinstance(task_feasibility, list) else []
    task_feasibility_programs = [
        item.get("program_id") if isinstance(item, Mapping) else None
        for item in task_feasibility
    ]
    total_prefix_replays = int(disk_root.get("suffix_prefix_replay_count", -1)) + int(
        disk_root.get("branch_prefix_replay_count", -1)
    )
    result_counts = {
        "root": value.get("development_accepted_root_count"),
        "trajectory": value.get("development_accepted_trajectory_count"),
    }
    checks = {
        "disk_root_receipt_loaded": True,
        "disk_root_matches_memory_result": root_matches,
        "root_status_accepted": disk_root.get("status") == "accepted",
        "result_development_root_pass": value.get("development_root_pass") is True,
        "result_accepted_counts_one_three": result_counts == {"root": 1, "trajectory": 3},
        "task_feasibility_three_of_three_exact_program_order": len(task_feasibility)
        == len(EXPECTED_PROGRAMS)
        and all(isinstance(item, Mapping) for item in task_feasibility)
        and task_feasibility_programs == EXPECTED_PROGRAMS
        and all(
            item.get("status") == "passed"
            for item in task_feasibility
        ),
        "one_candidate_freeze": disk_root.get("freeze_call_count") == 1,
        "one_canonical_prefix": disk_root.get("canonical_prefix_generation_count") == 1
        and disk_root.get("canonical_prefix_reference_execution_count") == 1,
        "three_suffix_preflights_exact_12_plus_30": suffix_accounting["pass"],
        "suffix_prefix_replays_three": disk_root.get("suffix_prefix_replay_count") == 3,
        "branch_prefix_replays_three": disk_root.get("branch_prefix_replay_count") == 3,
        "total_prefix_replays_six": total_prefix_replays == 6,
        "three_branch_executions": disk_root.get("branch_execution_attempt_count") == 3,
        "branch_receipts_exact_three_ordered_unique_structured": exact_branch_structure,
        "three_disk_branch_receipts": len(branch_audits) == 3
        and all(item["pass"] for item in branch_audits),
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
        "root_finalizer_accepted": root_finalization.get("accepted") is True,
        "same_current_anchor_prefix": all(
            root_final_checks.get(key) is True
            for key in (
                "branch_current_matches_reference",
                "branch_anchor_equivalent",
                "one_executed_prefix_action_hash",
                "prefix_start_anchor_equivalent",
                "prefix_end_state_equivalent",
            )
        ),
        "final_state_equivalence": root_final_checks.get("final_state_equivalence") is True,
        "planner_total_136": disk_root.get("planner_query_count_total") == 136,
        "canonical_prefix_planner_10": disk_root.get("canonical_prefix_planner_query_count") == 10,
        "suffix_planner_total_126": disk_root.get("suffix_planner_query_count_total") == 126
        and suffix_accounting["aggregate_queries"] == 126,
        "fresh_scenes_11_unique": unique_scenes,
        "exact_phase_multiset_1_3_1_3_3": exact_phases,
        "robot_action_scenes_7": phases["canonical_prefix"]
        + phases["suffix_preflight"]
        + phases["strict_prefix_branch"]
        == 7,
        "cleanup_orphan_pass": cleanup_pass,
    }
    accepted = all(checks.values())
    finalizer = {
        "schema_version": "cmf_f4_development_root_v2_1_finalizer_v1",
        "accepted": accepted,
        "checks": checks,
        "counts": {
            "planner_queries": disk_root.get("planner_query_count_total"),
            "fresh_scenes": len(cleanup),
            "unique_scene_ids": len(set(scene_ids)) if scene_ids else 0,
            "robot_action_scenes": phases["canonical_prefix"]
            + phases["suffix_preflight"]
            + phases["strict_prefix_branch"],
            "suffix_prefix_replays": disk_root.get("suffix_prefix_replay_count"),
            "branch_prefix_replays": disk_root.get("branch_prefix_replay_count"),
            "total_prefix_replays": total_prefix_replays,
            "branch_executions": disk_root.get("branch_execution_attempt_count"),
            "raw_trajectories": sum(item["raw_integrity"].get("pass") is True for item in branch_audits),
            "videos": sum(item["video_integrity"].get("pass") is True for item in branch_audits),
            "accepted_development_roots": 1 if accepted else 0,
            "accepted_development_trajectories": 3 if accepted else 0,
            "formal_trajectories": 0,
        },
        "root_receipt": {
            "path": str(root_path.resolve()),
            "file_sha256": file_sha(root_path),
            "matches_memory": root_matches,
        },
        "branch_artifact_audits": branch_audits,
        "suffix_query_accounting": suffix_accounting,
        "scene_phase_counts": dict(sorted(phases.items())),
        "scene_instance_ids": scene_ids,
        "failure": None
        if accepted
        else next((name for name, passed in checks.items() if not passed), "unknown"),
    }
    finalizer["receipt_sha256"] = canonical_hash(finalizer)
    return finalizer


def select_f4_dispatch_runner_entry(
    manifest_path: Path,
    job_id: str,
    *,
    allow_lifecycle_fixture: bool,
) -> dict[str, Any]:
    environment = dict(os.environ)
    lifecycle = environment.get("CMF_F4_CPU_LIFECYCLE_PREFLIGHT") == "1"
    if allow_lifecycle_fixture is not lifecycle:
        raise RuntimeError("F4 lifecycle fixture flag/environment mismatch")
    validated = load_and_validate_manifest_job(
        manifest_path,
        job_id,
        phase=RUNNER_ENTRY,
        require_execution_authorized=True,
        allow_lifecycle_fixture=allow_lifecycle_fixture,
        environment=environment,
        executable_role="runner",
        executable_path=Path(__file__),
    )
    sealed_v2 = _load_v2_runner()
    base = sealed_v2._load_base_runner()
    dispatch = getattr(base, "run_f4_development_r_pc_root")
    bound = sealed_v2._build_bound_specs(validated["job"])
    output = Path(validated["job"]["output_namespace"])
    if output.exists():
        raise RuntimeError("F4 V2.1 runner-entry preflight created output")
    result = {
        "schema_version": "cmf_f4_development_root_v2_1_runner_entry_preflight_v1",
        "manifest_sha256": validated["manifest_sha256"],
        "job_id": job_id,
        "phase": RUNNER_ENTRY,
        "dispatch_function": "run_f4_development_r_pc_root",
        "dispatch_callable": callable(dispatch),
        "runner_executable_identity": validated["executable_identity"],
        "runner_environment_binding": validated["paths"]["phase_validation"],
        **bound,
        "scene_created": False,
        "gpu_context_created": False,
        "output_created": False,
        "nvidia_smi_called": False,
        "real_gpu_lease_acquired": False,
        "planner_called": False,
        "authorization_consumed": False,
        "pass": True,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def write_new(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = _canonical_jsonable(value)
    data = (json.dumps(serializable, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv=None) -> int:
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
        executable_role="runner",
        executable_path=Path(__file__),
    )
    output = Path(validated["job"]["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    start = {
        "schema_version": "cmf_f4_development_root_v2_1_job_start_v1",
        "run_id": validated["manifest"]["run_id"],
        "job_id": args.job_id,
        "family": "F4",
        "manifest_sha256": validated["manifest_sha256"],
        "physical_gpu_index": int(os.environ["CMF_GPU_GUARD_PHYSICAL_INDEX"]),
        "gpu_uuid": os.environ["CUDA_VISIBLE_DEVICES"],
        "lease_path": os.environ["CMF_GPU_LEASE_PATH"],
    }
    start["receipt_sha256"] = canonical_hash(start)
    write_new(output / "job_start.json", start)
    sealed_v2 = _load_v2_runner()
    base = sealed_v2._load_base_runner()
    result = None
    error = None
    finalizer = None
    try:
        result = base.run_f4_development_r_pc_root(
            validated["job"],
            output,
            validated["manifest"]["implementation_source_sha256"],
        )
        result = _canonical_jsonable(result)
        finalizer = finalize_f4_root_result(result, validated["job"], output=output)
    except BaseException as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    passed = (
        error is None
        and isinstance(finalizer, Mapping)
        and finalizer.get("accepted") is True
    )
    terminal = _canonical_jsonable(
        {
            "schema_version": "cmf_f4_development_root_v2_1_job_terminal_v1",
            "run_id": validated["manifest"]["run_id"],
            "job_id": args.job_id,
            "family": "F4",
            "manifest_sha256": validated["manifest_sha256"],
            "physical_gpu_index": int(os.environ["CMF_GPU_GUARD_PHYSICAL_INDEX"]),
            "gpu_uuid": os.environ["CUDA_VISIBLE_DEVICES"],
            "result": result,
            "root_finalizer": finalizer,
            "error": error,
            "accepted_development_root_count": 1 if passed else 0,
            "accepted_development_trajectory_count": 3 if passed else 0,
            "pass": passed,
            "formal_data": False,
            "stage1_authorized": False,
        }
    )
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0 if terminal["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
