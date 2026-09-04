#!/usr/bin/env python3
"""Read-only post-run auditor for the sealed F2 11-query planner Gate.

The runner deliberately exits zero after publishing a scientifically failed
terminal.  Consequently, neither a zero child exit code nor a Guard terminal
whose status is ``completed`` is sufficient evidence of Gate success.  This
auditor validates the immutable job evidence and Guard cleanup together and
prints a self-hashed audit receipt to stdout.  It never writes to the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


WORKSPACE = Path("/nfs_share/lijunhui")
EXPECTED_MANIFEST_PATH = WORKSPACE / (
    "Vault-on-Fvl09/数据构造/实现审计/"
    "F2_CONTROLLED_INSERTION_ROUTE_GATE_APPROVED_RUN1_MANIFEST_V1.json"
)
EXPECTED_MANIFEST_FILE_SHA256 = (
    "3cfe58ea26168d7c1ded0ddfa2d8d72c91223501a18a2463d2caad00eb5a5910"
)
EXPECTED_MANIFEST_SHA256 = (
    "b08933bf17707bfa8b8700f6b384eecf72b9d5e7b5aac7bc38bcb26f875210d8"
)
EXPECTED_RUN_ID = "f2-controlled-insertion-route-gate-run1-20260904"
EXPECTED_JOB_ID = "f2-controlled-insertion-route-gate-run1"
EXPECTED_STATUS = "APPROVED_F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1"
EXPECTED_RUNNER_SHA256 = (
    "376a782ada5ee95b3e45b09a0af5314516004a4c360f4e9a8e3fb9647f5ace26"
)
EXPECTED_GUARD_SHA256 = (
    "bd31e5e1c96190d7b21c27bb775b7346f5127dc7bf0c23e2c4c47edbc50bb1a8"
)
EXPECTED_BINDING_SHA256 = (
    "985515944a97b59621067e662b2e33614ebc08c772de74659c01a1c8ae559f0d"
)
EXPECTED_PREFIX_QPOS_SHA256 = (
    "8d4cb7b0571c0ba740e0406b32d4041f0dc73f48b0879a4b91567e8445f477b9"
)
EXPECTED_INSIDE_TARGETS_SHA256 = (
    "10dd04a9fea671574ddf2cd28209be20938f1df7a3b785c38d7008849539d156"
)
EXPECTED_BESIDE_TARGETS_SHA256 = (
    "24471cdd00cdc9ef2d983717f68b21141404f66ba6cf337b9f6188d934504817"
)

INSIDE_SEGMENTS = (
    "inside_controlled_high_carry",
    "f2_v2_preinsert_30mm",
    "f2_v2_controlled_descend_to_support",
    "f2_v2_retreat_to_preinsert",
    "f2_v2_neutral",
)
BESIDE_SEGMENTS = (
    "beside_asset_bound_carry_hub",
    "beside_asset_bound_preplace",
    "beside_asset_bound_release",
    "beside_asset_bound_retreat",
    "beside_asset_bound_carry_hub_return",
    "f2_rest",
)
GPU_UUIDS = {
    0: "GPU-2c620e6c-9639-2022-b573-9847dfa33769",
    1: "GPU-414c52ba-72c6-fc45-95d6-1e9750bbc21b",
    2: "GPU-4306d28e-0eeb-2e26-bda4-b1b44058f63e",
    3: "GPU-d5b84492-c467-0080-206f-2456cef0c338",
    4: "GPU-6a2b7387-0c6e-f68d-4f88-92e859c27da7",
    5: "GPU-9dd3c02d-192d-3536-b12e-b1be3a605be2",
    6: "GPU-8678470b-2ef8-1672-7c4c-8b55d183216d",
    7: "GPU-4c836e67-fb8e-a993-002c-cb83b10a6ead",
}


class AuditFailure(ValueError):
    """A fail-closed, machine-identifiable audit rejection."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


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


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise AuditFailure(code, message)


def as_mapping(value: Any, code: str, label: str) -> Mapping[str, Any]:
    require(isinstance(value, Mapping), code, f"{label} must be an object")
    return value


def validate_self_hash(value: Mapping[str, Any], key: str, label: str) -> str:
    payload = dict(value)
    digest = payload.pop(key, None)
    require(
        isinstance(digest, str) and digest == canonical_hash(payload),
        f"{label}_self_hash",
        f"{label} self-hash mismatch",
    )
    return digest


def within_workspace(path: Path, label: str) -> Path:
    resolved = Path(path).resolve()
    require(
        str(resolved).startswith(str(WORKSPACE) + "/"),
        f"{label}_outside_workspace",
        f"{label} resolves outside the workspace",
    )
    return resolved


def validate_manifest(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    validate_self_hash(manifest, "manifest_sha256", "manifest")
    require(
        manifest.get("manifest_sha256") == EXPECTED_MANIFEST_SHA256,
        "manifest_identity",
        "manifest is not the sealed F2 11-query manifest",
    )
    require(
        manifest.get("run_id") == EXPECTED_RUN_ID
        and manifest.get("status") == EXPECTED_STATUS
        and manifest.get("approved") is True,
        "manifest_authority",
        "manifest run/status/approval changed",
    )
    require(
        manifest.get("runner_script_sha256") == EXPECTED_RUNNER_SHA256
        and manifest.get("guard_script_sha256") == EXPECTED_GUARD_SHA256,
        "manifest_runtime_identity",
        "manifest-bound runner or Guard identity changed",
    )
    require(
        manifest.get("allowed_physical_gpu_indices") == list(range(8))
        and manifest.get("one_job_per_gpu") is True
        and manifest.get("root_sharding") is False,
        "manifest_gpu_scope",
        "manifest GPU scheduling scope changed",
    )
    require(
        manifest.get("gpu_execution_authorized") is True
        and manifest.get("planner_execution_authorized") is True
        and manifest.get("physical_execution_authorized") is False,
        "manifest_execution_scope",
        "manifest is not planner-only",
    )
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
        require(
            manifest.get(key) is False,
            "manifest_forbidden_stage",
            f"forbidden manifest field enabled: {key}",
        )
    jobs = manifest.get("jobs")
    require(
        isinstance(jobs, list) and len(jobs) == 1,
        "manifest_job_count",
        "manifest must contain exactly one F2 job",
    )
    job = as_mapping(jobs[0], "manifest_job_type", "manifest job")
    exact = {
        "job_id": EXPECTED_JOB_ID,
        "family": "F2",
        "mode": "F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1",
        "planner_query_cap": 11,
        "fresh_planner_scene_cap": 2,
        "inside_planner_query_cap": 5,
        "beside_planner_query_cap": 6,
        "beside_frozen_layout_candidate_index": 2,
        "physical_execution_cap": 0,
        "branch_execution_cap": 0,
        "raw_trajectory_cap": 0,
        "video_cap": 0,
        "accepted_root_cap": 0,
        "formal_trajectory_cap": 0,
    }
    require(
        all(job.get(key) == expected for key, expected in exact.items()),
        "manifest_job_contract",
        "F2 job mode or exact caps changed",
    )
    for key in (
        "automatic_retry",
        "fallback_allowed",
        "target_search_allowed",
        "root_retry_allowed",
        "automatic_continuation",
        "primary_10cm_gravity_drop",
        "open_gripper_during_gate",
    ):
        require(
            job.get(key) is False,
            "manifest_forbidden_behavior",
            f"forbidden F2 behavior enabled: {key}",
        )
    return job


def validate_scene_cleanup(cleanup: Any, relation: str) -> str:
    cleanup = as_mapping(cleanup, "scene_cleanup_type", f"{relation} cleanup")
    require(
        cleanup.get("scene_created") is True
        and cleanup.get("scene_cleanup_attempted") is True
        and cleanup.get("scene_cleanup_succeeded") is True
        and cleanup.get("cleanup_safety_pass") is True,
        "scene_cleanup",
        f"{relation} fresh scene did not cleanly close",
    )
    require(
        cleanup.get("cleanup_error") is None
        and cleanup.get("orphan_process_count") == 0,
        "scene_orphan_cleanup",
        f"{relation} scene has a cleanup error or orphan process",
    )
    require(
        cleanup.get("activity_monitor_restoration_succeeded") is True
        and cleanup.get("activity_monitor_restoration_error") is None,
        "scene_monitor_restoration",
        f"{relation} scene monitor restoration failed",
    )
    scene_id = cleanup.get("scene_instance_id")
    require(
        isinstance(scene_id, str) and bool(scene_id),
        "scene_identity",
        f"{relation} fresh scene lacks an instance ID",
    )
    return scene_id


def validate_planner_row(
    row: Mapping[str, Any],
    *,
    relation: str,
    query_count: int,
    segment_ids: tuple[str, ...],
    expected_targets_sha256: str,
) -> str:
    validate_self_hash(row, "receipt_sha256", f"{relation}_planner_receipt")
    require(
        row.get("relation") == relation
        and row.get("planner_query_cap") == query_count
        and row.get("planner_query_count") == query_count
        and row.get("planner_pass") is True,
        f"{relation}_planner_summary",
        f"{relation} is not an exact {query_count}/{query_count} planner pass",
    )
    require(
        row.get("physical_execution_count") == 0,
        f"{relation}_physical_count",
        f"{relation} unexpectedly reports physical execution",
    )
    restore = as_mapping(
        row.get("state_restore_receipt"),
        f"{relation}_state_restore_type",
        f"{relation} state restore receipt",
    )
    require(
        restore.get("actual_prefix_end_qpos_sha256")
        == EXPECTED_PREFIX_QPOS_SHA256
        and restore.get("target_segment_ids") == list(segment_ids)
        and restore.get("targets_sha256") == expected_targets_sha256,
        f"{relation}_state_restore_binding",
        f"{relation} is not bound to the sealed prefix/targets",
    )
    require(
        restore.get("physical_action_executed") is False
        and restore.get("gripper_opened") is False,
        f"{relation}_state_restore_scope",
        f"{relation} state restore reports a physical/gripper action",
    )
    segments = row.get("segment_receipts")
    require(
        isinstance(segments, list) and len(segments) == query_count,
        f"{relation}_segment_count",
        f"{relation} does not contain exactly {query_count} segment receipts",
    )
    require(
        [item.get("segment_id") for item in segments if isinstance(item, Mapping)]
        == list(segment_ids),
        f"{relation}_segment_order",
        f"{relation} segment order differs from the reviewed chain",
    )
    for index, segment in enumerate(segments, start=1):
        segment = as_mapping(
            segment,
            f"{relation}_segment_type",
            f"{relation} segment {index}",
        )
        segment_id = segment_ids[index - 1]
        query = as_mapping(
            segment.get("planner_query_receipt"),
            f"{relation}_query_receipt_type",
            f"{relation} query {index}",
        )
        require(
            segment.get("planner_status") == "Success"
            and segment.get("executed") is False
            and query.get("status") == "Success"
            and query.get("source") == segment_id
            and query.get("query_id") == index,
            f"{relation}_segment_not_passed",
            f"{relation} segment {index} is not a successful unexecuted planner query",
        )
        if index > 1:
            require(
                segment.get("start_qpos_sha256")
                == segments[index - 2].get("end_qpos_sha256"),
                f"{relation}_chain_discontinuity",
                f"{relation} planner qpos chain is discontinuous at segment {index}",
            )
    require(
        row.get("terminal_qpos_sha256") == segments[-1].get("end_qpos_sha256"),
        f"{relation}_terminal_qpos",
        f"{relation} terminal qpos is not the last segment end",
    )
    return validate_scene_cleanup(row.get("cleanup"), relation)


def validate_job_terminal(
    manifest: Mapping[str, Any],
    job_terminal: Mapping[str, Any],
    planner_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validate_self_hash(job_terminal, "receipt_sha256", "job_terminal")
    require(
        job_terminal.get("schema_version")
        == "cmf_f2_controlled_insertion_route_gate_terminal_v1"
        and job_terminal.get("manifest_sha256") == EXPECTED_MANIFEST_SHA256
        and job_terminal.get("job_id") == EXPECTED_JOB_ID,
        "job_terminal_binding",
        "job terminal schema/manifest/job binding changed",
    )
    require(
        job_terminal.get("error") is None,
        "job_terminal_error",
        "job terminal contains an execution error",
    )
    require(
        job_terminal.get("pass") is True,
        "job_terminal_pass",
        "job_terminal.pass is not true",
    )
    for key in (
        "physical_execution_count",
        "accepted_root_count",
        "formal_trajectory_count",
    ):
        require(
            job_terminal.get(key) == 0,
            "job_terminal_forbidden_count",
            f"job terminal has nonzero {key}",
        )
    require(
        job_terminal.get("automatic_continuation") is False
        and job_terminal.get("formal_data") is False
        and job_terminal.get("stage1_authorized") is False,
        "job_terminal_scope",
        "job terminal enabled continuation, formal data, or Stage 1",
    )
    result = as_mapping(
        job_terminal.get("result"), "job_result_type", "job result"
    )
    require(
        result.get("schema_version")
        == "cmf_f2_controlled_insertion_route_gate_result_v1"
        and result.get("gate_name")
        == "F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1",
        "job_result_identity",
        "job result is not the reviewed F2 Gate",
    )
    require(
        result.get("both_chains_pass") is True,
        "both_chains_pass",
        "result.both_chains_pass is not true",
    )
    require(
        result.get("planner_query_count") == 11
        and result.get("fresh_planner_scene_count") == 2,
        "job_result_accounting",
        "result is not exactly 11 planner queries in two fresh scenes",
    )
    for key in (
        "physical_execution_count",
        "branch_execution_count",
        "raw_trajectory_count",
        "video_count",
        "accepted_root_count",
        "formal_trajectory_count",
    ):
        require(
            result.get(key) == 0,
            "job_result_forbidden_count",
            f"job result has nonzero {key}",
        )
    require(
        result.get("automatic_continuation") is False
        and result.get("separate_external_review_required_before_root") is True
        and result.get("formal_data") is False,
        "job_result_scope",
        "job result violates the no-continuation/review boundary",
    )
    contract = as_mapping(
        result.get("contract"), "job_contract_type", "job result contract"
    )
    require(
        contract.get("selected_binding_sha256") == EXPECTED_BINDING_SHA256
        and contract.get("actual_prefix_end_qpos_sha256")
        == EXPECTED_PREFIX_QPOS_SHA256
        and contract.get("inside_targets_sha256")
        == EXPECTED_INSIDE_TARGETS_SHA256
        and contract.get("beside_targets_sha256")
        == EXPECTED_BESIDE_TARGETS_SHA256
        and contract.get("inside_target_segment_ids") == list(INSIDE_SEGMENTS)
        and contract.get("beside_target_segment_ids") == list(BESIDE_SEGMENTS),
        "job_result_contract_binding",
        "result contract differs from the sealed prefix/targets",
    )
    rows = result.get("planner_rows")
    require(
        isinstance(rows, list) and len(rows) == 2,
        "planner_row_count",
        "result must contain exactly two planner rows",
    )
    require(
        [row.get("relation") for row in rows if isinstance(row, Mapping)]
        == ["inside", "beside"],
        "planner_row_order",
        "planner rows are not in exact inside/beside order",
    )
    require(
        set(planner_receipts) == {"inside", "beside"},
        "planner_receipt_files",
        "both independently published planner receipts are required",
    )
    for relation, row in zip(("inside", "beside"), rows):
        require(
            row == planner_receipts[relation],
            f"{relation}_planner_file_binding",
            f"embedded {relation} row differs from its planner receipt file",
        )
    inside_scene = validate_planner_row(
        rows[0],
        relation="inside",
        query_count=5,
        segment_ids=INSIDE_SEGMENTS,
        expected_targets_sha256=EXPECTED_INSIDE_TARGETS_SHA256,
    )
    beside_scene = validate_planner_row(
        rows[1],
        relation="beside",
        query_count=6,
        segment_ids=BESIDE_SEGMENTS,
        expected_targets_sha256=EXPECTED_BESIDE_TARGETS_SHA256,
    )
    require(
        rows[0].get("planner_query_count")
        + rows[1].get("planner_query_count")
        == result.get("planner_query_count")
        == 11,
        "aggregate_planner_queries",
        "per-chain planner queries do not sum to exactly 11",
    )
    require(
        inside_scene != beside_scene,
        "fresh_scene_uniqueness",
        "inside and beside did not use two distinct fresh scene instances",
    )
    return {
        "job_terminal_receipt_sha256": job_terminal["receipt_sha256"],
        "inside_planner_receipt_sha256": rows[0]["receipt_sha256"],
        "beside_planner_receipt_sha256": rows[1]["receipt_sha256"],
        "inside_planner_pass_count": 5,
        "beside_planner_pass_count": 6,
        "aggregate_planner_query_count": 11,
        "fresh_planner_scene_count": 2,
        "scene_instance_ids": [inside_scene, beside_scene],
    }


def selected_gpu(snapshot: Any, index: int, uuid: str, label: str) -> Mapping[str, Any]:
    snapshot = as_mapping(snapshot, f"{label}_type", label)
    gpus = snapshot.get("gpus")
    require(
        isinstance(gpus, list) and len(gpus) == 8,
        f"{label}_gpu_count",
        f"{label} must contain all eight physical GPUs",
    )
    require(
        {item.get("index") for item in gpus if isinstance(item, Mapping)}
        == set(range(8)),
        f"{label}_gpu_indices",
        f"{label} does not contain exactly GPU0-7",
    )
    matches = [
        item
        for item in gpus
        if isinstance(item, Mapping)
        and item.get("index") == index
        and item.get("uuid") == uuid
    ]
    require(
        len(matches) == 1,
        f"{label}_selected_gpu",
        f"{label} selected GPU index/UUID binding is missing or ambiguous",
    )
    return matches[0]


def gpu_is_idle(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("memory_used_mib", 10**9) <= 64
        and row.get("utilization_gpu_percent") == 0
        and row.get("pstate") in {"P8", "P12"}
        and row.get("compute_processes") == []
    )


def validate_guard(
    manifest: Mapping[str, Any],
    guard_start: Mapping[str, Any],
    guard_terminal: Mapping[str, Any],
    path_state: Mapping[str, Any],
) -> dict[str, Any]:
    validate_self_hash(guard_start, "receipt_sha256", "guard_start")
    validate_self_hash(guard_terminal, "receipt_sha256", "guard_terminal")
    index = guard_terminal.get("physical_gpu_index")
    uuid = guard_terminal.get("gpu_uuid")
    require(
        isinstance(index, int)
        and index in range(8)
        and uuid == GPU_UUIDS[index],
        "guard_gpu_binding",
        "Guard selected GPU index/UUID is not an approved fvl05 binding",
    )
    expected_lease = (
        WORKSPACE
        / "Robotwin2/gpu_leases/production_micro_gate_v1"
        / f"physical_gpu_{index}.lock"
    )
    require(
        guard_start.get("schema_version")
        == "cmf_production_micro_gate_guard_start_v1"
        and guard_start.get("run_id") == EXPECTED_RUN_ID
        and guard_start.get("job_id") == EXPECTED_JOB_ID
        and guard_start.get("family") == "F2"
        and guard_start.get("manifest_sha256") == EXPECTED_MANIFEST_SHA256
        and guard_start.get("physical_gpu_index") == index
        and guard_start.get("gpu_uuid") == uuid
        and guard_start.get("lease_path") == str(expected_lease),
        "guard_start_binding",
        "Guard start receipt is not bound to this run/job/GPU/lease",
    )
    require(
        guard_terminal.get("schema_version")
        == "cmf_production_micro_gate_guard_terminal_v1"
        and guard_terminal.get("run_id") == EXPECTED_RUN_ID
        and guard_terminal.get("job_id") == EXPECTED_JOB_ID
        and guard_terminal.get("family") == "F2"
        and guard_terminal.get("manifest_sha256") == EXPECTED_MANIFEST_SHA256,
        "guard_terminal_binding",
        "Guard terminal is not bound to this run/job/manifest",
    )
    require(
        guard_terminal.get("guard_pid") == guard_start.get("guard_pid")
        and guard_terminal.get("pre_snapshot") == guard_start.get("pre_snapshot"),
        "guard_start_terminal_lineage",
        "Guard start and terminal lineage differs",
    )
    pre = selected_gpu(guard_terminal.get("pre_snapshot"), index, uuid, "pre_snapshot")
    launch = selected_gpu(
        guard_terminal.get("launch_snapshot"), index, uuid, "launch_snapshot"
    )
    require(
        gpu_is_idle(pre) and gpu_is_idle(launch),
        "guard_prelaunch_idle",
        "selected GPU was not independently fresh-idle at pre/launch",
    )
    require(
        guard_terminal.get("child_exit_code") == 0,
        "guard_child_exit",
        "Guard child exit code is not zero",
    )
    require(
        guard_terminal.get("status") == "completed",
        "guard_status",
        "Guard status is not completed",
    )
    require(
        guard_terminal.get("timed_out") is False
        and guard_terminal.get("interrupted") is None,
        "guard_execution_end",
        "Guard timed out or was interrupted",
    )
    require(
        guard_terminal.get("cleanup_errors") == []
        and guard_terminal.get("cache_removed") is True
        and guard_terminal.get("lease_released") is True
        and guard_terminal.get("gpu_returned_to_idle_baseline") is True
        and guard_terminal.get("task_owned_cleanup_pass") is True,
        "guard_cleanup",
        "Guard cleanup/cache/lease/GPU-baseline conjunction failed",
    )
    require(
        guard_terminal.get("output_exists") is True,
        "guard_output",
        "Guard terminal does not report the F2 output",
    )
    post = selected_gpu(
        guard_terminal.get("post_snapshot"), index, uuid, "post_snapshot"
    )
    relative_baseline = bool(
        post.get("memory_used_mib", 10**9)
        <= max(64, int(pre.get("memory_used_mib", 10**9)) + 32)
        and post.get("utilization_gpu_percent") == 0
        and post.get("pstate") in {"P8", "P12"}
        and post.get("compute_processes") == []
    )
    require(
        relative_baseline,
        "gpu_post_baseline",
        "independent post-snapshot recomputation did not return to baseline",
    )
    polls = guard_terminal.get("post_release_poll_snapshots")
    require(
        isinstance(polls, list)
        and bool(polls)
        and polls[-1] == guard_terminal.get("post_snapshot"),
        "gpu_post_poll_lineage",
        "Guard final post snapshot is not the last release poll",
    )
    expected_guard_dir = Path(str(manifest["guard_directory"]))
    expected_stdout = expected_guard_dir / f"{EXPECTED_JOB_ID}.stdout.log"
    expected_stderr = expected_guard_dir / f"{EXPECTED_JOB_ID}.stderr.log"
    require(
        guard_terminal.get("stdout_path") == str(expected_stdout)
        and guard_terminal.get("stderr_path") == str(expected_stderr),
        "guard_log_binding",
        "Guard stdout/stderr paths differ from the manifest-bound directory",
    )
    require(
        path_state.get("stdout_exists") is True
        and path_state.get("stderr_exists") is True
        and path_state.get("cache_job_exists") is False,
        "postrun_path_cleanup",
        "Guard logs are missing or the per-job cache still exists",
    )
    return {
        "guard_start_receipt_sha256": guard_start["receipt_sha256"],
        "guard_terminal_receipt_sha256": guard_terminal["receipt_sha256"],
        "physical_gpu_index": index,
        "gpu_uuid": uuid,
        "child_exit_code": 0,
        "cache_removed": True,
        "lease_released": True,
        "task_owned_cleanup_pass": True,
        "gpu_returned_to_idle_baseline": True,
        "post_selected_gpu": dict(post),
    }


def validate_path_state(path_state: Mapping[str, Any]) -> None:
    require(
        path_state.get("manifest_file_sha256") == EXPECTED_MANIFEST_FILE_SHA256,
        "manifest_file_identity",
        "manifest file bytes changed",
    )
    require(
        path_state.get("runner_script_sha256") == EXPECTED_RUNNER_SHA256
        and path_state.get("guard_script_sha256") == EXPECTED_GUARD_SHA256,
        "runtime_file_identity",
        "runner or Guard file bytes changed",
    )
    for key in (
        "output_exists",
        "job_start_exists",
        "job_terminal_exists",
        "inside_planner_receipt_exists",
        "beside_planner_receipt_exists",
        "guard_start_exists",
        "guard_terminal_exists",
    ):
        require(
            path_state.get(key) is True,
            "required_evidence_path",
            f"required post-run evidence is missing: {key}",
        )
    require(
        path_state.get("forbidden_artifact_paths") == []
        and path_state.get("symlink_paths") == [],
        "forbidden_disk_artifact",
        "F2 planner-only output contains raw/video/root/branch/formal data or symlinks",
    )


def seal_report(report: dict[str, Any]) -> dict[str, Any]:
    result = dict(report)
    result.pop("receipt_sha256", None)
    result["receipt_sha256"] = canonical_hash(result)
    return result


def audit_documents(
    *,
    manifest: Mapping[str, Any],
    job_start: Mapping[str, Any],
    job_terminal: Mapping[str, Any],
    planner_receipts: Mapping[str, Mapping[str, Any]],
    guard_start: Mapping[str, Any],
    guard_terminal: Mapping[str, Any],
    path_state: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        job = validate_manifest(manifest)
        require(
            job_start
            == {
                "manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "job_id": EXPECTED_JOB_ID,
            },
            "job_start_binding",
            "job_start.json is not the exact manifest/job binding",
        )
        validate_path_state(path_state)
        job_evidence = validate_job_terminal(
            manifest, job_terminal, planner_receipts
        )
        guard_evidence = validate_guard(
            manifest, guard_start, guard_terminal, path_state
        )
        report = {
            "schema_version": "cmf_f2_controlled_insertion_route_gate_postrun_audit_v1",
            "status": "VERIFIED_F2_PLANNER_ONLY_GATE_PASS",
            "pass": True,
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "run_id": EXPECTED_RUN_ID,
            "job_id": EXPECTED_JOB_ID,
            "scientific_result": {
                "job_terminal_pass": True,
                "both_chains_pass": True,
                "inside": "5/5",
                "beside": "6/6",
                "planner_query_count": 11,
                "fresh_planner_scene_count": 2,
                "physical_execution_count": 0,
                "branch_execution_count": 0,
                "raw_trajectory_count": 0,
                "video_count": 0,
                "accepted_root_count": 0,
                "formal_trajectory_count": 0,
            },
            "job_evidence": job_evidence,
            "guard_evidence": guard_evidence,
            "path_state": dict(path_state),
            "child_exit_code_alone_was_not_used_as_success": True,
            "automatic_root_continuation_authorized": False,
            "stage1_authorized": False,
            "formal_data": False,
            "failure": None,
        }
    except AuditFailure as exc:
        report = {
            "schema_version": "cmf_f2_controlled_insertion_route_gate_postrun_audit_v1",
            "status": "REJECTED_F2_POSTRUN_EVIDENCE",
            "pass": False,
            "manifest_sha256": manifest.get("manifest_sha256"),
            "run_id": manifest.get("run_id"),
            "job_id": EXPECTED_JOB_ID,
            "child_exit_code_alone_was_not_used_as_success": True,
            "automatic_root_continuation_authorized": False,
            "stage1_authorized": False,
            "formal_data": False,
            "failure": {"code": exc.code, "message": str(exc)},
        }
    return seal_report(report)


def load_json(path: Path, label: str) -> Mapping[str, Any]:
    path = within_workspace(path, label)
    require(path.is_file(), f"{label}_missing", f"{label} is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditFailure(f"{label}_json", f"cannot read {label}: {exc}") from exc
    return as_mapping(value, f"{label}_type", label)


def forbidden_output_paths(output: Path) -> tuple[list[str], list[str]]:
    forbidden = []
    symlinks = []
    forbidden_parts = {"raw", "branch", "branches", "root", "formal", "video", "videos"}
    forbidden_suffixes = {".npz", ".npy", ".hdf5", ".h5", ".pkl", ".mp4", ".avi", ".mov"}
    for path in output.rglob("*"):
        relative = path.relative_to(output)
        if path.is_symlink():
            symlinks.append(relative.as_posix())
            continue
        lowered_parts = {part.lower() for part in relative.parts}
        if lowered_parts & forbidden_parts or path.suffix.lower() in forbidden_suffixes:
            forbidden.append(relative.as_posix())
    return sorted(forbidden), sorted(symlinks)


def audit_from_disk(manifest_path: Path) -> dict[str, Any]:
    manifest_path = within_workspace(manifest_path, "manifest")
    require(
        manifest_path == EXPECTED_MANIFEST_PATH.resolve(),
        "manifest_path_identity",
        "auditor accepts only the sealed F2 manifest path",
    )
    manifest = load_json(manifest_path, "manifest")
    job = validate_manifest(manifest)
    output = within_workspace(Path(str(job["output_namespace"])), "output")
    guard_dir = within_workspace(Path(str(manifest["guard_directory"])), "guard_directory")
    cache_job = within_workspace(
        Path(str(manifest["cache_directory"])) / EXPECTED_JOB_ID, "cache_job"
    )
    job_start_path = output / "job_start.json"
    job_terminal_path = output / "job_terminal.json"
    planner_paths = {
        relation: output / f"{relation}_planner_receipt.json"
        for relation in ("inside", "beside")
    }
    guard_start_path = guard_dir / f"{EXPECTED_JOB_ID}.start.json"
    guard_terminal_path = guard_dir / f"{EXPECTED_JOB_ID}.terminal.json"
    stdout_path = guard_dir / f"{EXPECTED_JOB_ID}.stdout.log"
    stderr_path = guard_dir / f"{EXPECTED_JOB_ID}.stderr.log"
    forbidden, symlinks = forbidden_output_paths(output) if output.is_dir() else ([], [])
    path_state = {
        "manifest_file_sha256": file_sha(manifest_path),
        "runner_script_sha256": file_sha(Path(str(manifest["runner_script_path"]))),
        "guard_script_sha256": file_sha(Path(str(manifest["guard_script_path"]))),
        "output_exists": output.is_dir(),
        "job_start_exists": job_start_path.is_file(),
        "job_terminal_exists": job_terminal_path.is_file(),
        "inside_planner_receipt_exists": planner_paths["inside"].is_file(),
        "beside_planner_receipt_exists": planner_paths["beside"].is_file(),
        "guard_start_exists": guard_start_path.is_file(),
        "guard_terminal_exists": guard_terminal_path.is_file(),
        "stdout_exists": stdout_path.is_file(),
        "stderr_exists": stderr_path.is_file(),
        "cache_job_exists": cache_job.exists(),
        "forbidden_artifact_paths": forbidden,
        "symlink_paths": symlinks,
    }
    report = audit_documents(
        manifest=manifest,
        job_start=load_json(job_start_path, "job_start"),
        job_terminal=load_json(job_terminal_path, "job_terminal"),
        planner_receipts={
            relation: load_json(path, f"{relation}_planner_receipt")
            for relation, path in planner_paths.items()
        },
        guard_start=load_json(guard_start_path, "guard_start"),
        guard_terminal=load_json(guard_terminal_path, "guard_terminal"),
        path_state=path_state,
    )
    report.pop("receipt_sha256", None)
    report["evidence_file_sha256"] = {
        "manifest": file_sha(manifest_path),
        "job_start": file_sha(job_start_path),
        "job_terminal": file_sha(job_terminal_path),
        "inside_planner_receipt": file_sha(planner_paths["inside"]),
        "beside_planner_receipt": file_sha(planner_paths["beside"]),
        "guard_start": file_sha(guard_start_path),
        "guard_terminal": file_sha(guard_terminal_path),
        "guard_stdout": file_sha(stdout_path),
        "guard_stderr": file_sha(stderr_path),
    }
    report["auditor_source_sha256"] = file_sha(Path(__file__))
    return seal_report(report)


def failure_report(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, AuditFailure):
        code = exc.code
    else:
        code = "unexpected_auditor_exception"
    return seal_report(
        {
            "schema_version": "cmf_f2_controlled_insertion_route_gate_postrun_audit_v1",
            "status": "REJECTED_F2_POSTRUN_EVIDENCE",
            "pass": False,
            "manifest_sha256": None,
            "run_id": EXPECTED_RUN_ID,
            "job_id": EXPECTED_JOB_ID,
            "child_exit_code_alone_was_not_used_as_success": True,
            "automatic_root_continuation_authorized": False,
            "stage1_authorized": False,
            "formal_data": False,
            "failure": {"code": code, "message": str(exc)},
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=EXPECTED_MANIFEST_PATH
    )
    args = parser.parse_args(argv)
    try:
        report = audit_from_disk(args.manifest)
    except BaseException as exc:
        report = failure_report(exc)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
