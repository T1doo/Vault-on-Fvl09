"""Read-only replay of the four sealed F3 V2.1 physical traces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

from gate import canonical_hash, evaluate_preclose_sequence


WORKSPACE = Path("/nfs_share/lijunhui")
TRACE_ROOT = WORKSPACE / "Robotwin2/datasets/cmf_f3_v21_pathsafe_r1"
CASE_DIRECTORIES = (
    "retained_r0005",
    "candidate_01_f3-final-pose-v3-r1505",
    "candidate_02_f3-final-pose-v3-r2180",
    "candidate_03_f3-final-pose-v3-r3677",
)
ACTION_LAYOUT_VERSION = "controller_effective_setpoint_v1_layout_v2_1"
ACTION_LAYOUT_DIMENSIONS = tuple(
    [f"left_joint_{index}_position_target" for index in range(6)]
    + [f"right_joint_{index}_position_target" for index in range(6)]
    + [f"left_joint_{index}_velocity_target" for index in range(6)]
    + [f"right_joint_{index}_velocity_target" for index in range(6)]
    + ["left_gripper_normalized_target", "right_gripper_normalized_target"]
)

# Exact Aloha-AgileX active-joint indices in the sealed 38-D articulation
# stream.  The planner terminal uses the same complete articulation layout.
ARM_QPOS_INDICES = {
    "left": np.asarray([6, 14, 18, 22, 26, 30], dtype=np.int64),
    "right": np.asarray([7, 15, 19, 23, 27, 31], dtype=np.int64),
}
ARM_ACTION_INDICES = {
    "left": np.asarray([0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17]),
    "right": np.asarray([6, 7, 8, 9, 10, 11, 18, 19, 20, 21, 22, 23]),
}


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside_workspace(path: Path) -> Path:
    result = Path(path).resolve()
    if not str(result).startswith(str(WORKSPACE) + "/"):
        raise ValueError("replay path is outside workspace")
    return result


def _load_self_hashed(path: Path, hash_key: str) -> tuple[dict, str]:
    path = _inside_workspace(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop(hash_key, None)
    if digest != canonical_hash(payload):
        raise ValueError(f"self-hash mismatch: {path}")
    return value, file_sha(path)


def _read_contact_rows(npz_path: Path, row_indices: list[int]) -> dict[int, list]:
    """Read sparse rows without allocating the multi-gigabyte Unicode array."""

    result = {}
    with zipfile.ZipFile(npz_path) as archive:
        with archive.open("contact_pairs_json.npy") as handle:
            version = np.lib.format.read_magic(handle)
            shape, fortran, dtype = np.lib.format._read_array_header(handle, version)
            if fortran or len(shape) != 1 or dtype.kind != "U":
                raise ValueError("unexpected contact_pairs_json NPY layout")
            base = handle.tell()
            for index in sorted(set(row_indices)):
                if index < 0 or index >= shape[0]:
                    raise IndexError("contact row is outside trace")
                handle.seek(base + index * dtype.itemsize)
                raw = handle.read(dtype.itemsize)
                if len(raw) != dtype.itemsize:
                    raise EOFError("contact row is truncated")
                encoded = np.frombuffer(raw, dtype=dtype, count=1)[0]
                pairs = json.loads(str(encoded))
                if not isinstance(pairs, list):
                    raise ValueError("contact row is not a JSON list")
                result[index] = pairs
    return result


def _segment_snapshot(
    *,
    stage: str,
    execution: dict,
    target: dict,
    planner_segment: dict,
    arm: str,
    eef_pose: np.ndarray,
    object_pose: np.ndarray,
    joint_qpos: np.ndarray,
    component_masks: np.ndarray,
    contact_pairs: list,
    selected_links: list[str],
) -> dict:
    end = int(execution["end_trace_row"])
    start = int(execution["start_trace_row"])
    if execution["segment_id"] != target["segment_id"]:
        raise ValueError("execution/target segment mismatch")
    if planner_segment["segment_id"] != execution["segment_id"]:
        raise ValueError("execution/planner segment mismatch")
    selected_action_indices = ARM_ACTION_INDICES[arm]
    opposite = "right" if arm == "left" else "left"
    opposite_action_indices = ARM_ACTION_INDICES[opposite]
    segment_masks = component_masks[start + 1 : end + 1]
    if not len(segment_masks):
        raise ValueError("executed segment has no action rows")
    qpos_indices = ARM_QPOS_INDICES[arm]
    planned_full = np.asarray(planner_segment["end_qpos"], dtype=np.float64)
    if joint_qpos.shape[1] != planned_full.size:
        raise ValueError("planned/realized complete qpos dimensions differ")
    return {
        "stage": stage,
        "arm": arm,
        "planned_selected_arm_qpos": planned_full[qpos_indices].tolist(),
        "realized_selected_arm_qpos": joint_qpos[end, qpos_indices].tolist(),
        "planner_goal_eef_pose": target["pose"],
        "realized_eef_pose": eef_pose[end].tolist(),
        "initial_bottle_position_m": object_pose[0, :3].tolist(),
        "realized_bottle_position_m": object_pose[end, :3].tolist(),
        "contact_pairs": contact_pairs,
        "selected_gripper_links": selected_links,
        "bottle_actor_name": "f3_main_bottle",
        "support_actor_names": ["table", "f3_original_pad"],
        "selected_arm_commanded": bool(
            np.any(segment_masks[:, selected_action_indices])
        ),
        "opposite_arm_commanded": bool(
            np.any(segment_masks[:, opposite_action_indices])
        ),
    }


def replay_case(case_directory: str) -> dict:
    if case_directory not in CASE_DIRECTORIES:
        raise ValueError("case is not one of the sealed four-trace cohort")
    case = _inside_workspace(TRACE_ROOT / case_directory)
    scene_path = case / "physical/scene_receipt.json"
    spec_path = case / "physical_spec.json"
    trace_path = case / "physical/physical_trace.npz"
    scene, scene_file_sha = _load_self_hashed(scene_path, "receipt_sha256")
    spec, spec_file_sha = _load_self_hashed(spec_path, "spec_sha256")
    if scene.get("error") is not None or scene.get("pass") is not True:
        raise ValueError("sealed physical scene did not finish successfully")
    trace_receipt = scene.get("trace")
    if not isinstance(trace_receipt, dict):
        raise ValueError("scene trace receipt is missing")
    trace_file_sha = file_sha(trace_path)
    if trace_file_sha != trace_receipt.get("sha256"):
        raise ValueError("trace file hash differs from scene receipt")

    physical = scene["result"]["physical_result"]
    executions = physical["execution_receipts"]
    planners = physical["planner_result"]["segment_receipts"]
    if len(executions) != 7 or len(planners) != 7:
        raise ValueError("physical chain is not the sealed seven segments")
    targets_by_id = {item["segment_id"]: item for item in spec["ordered_targets"]}
    if len(targets_by_id) != 7:
        raise ValueError("physical spec does not contain seven unique targets")
    pre_execution, grasp_execution = executions[:2]
    pre_end = int(pre_execution["end_trace_row"])
    grasp_end = int(grasp_execution["end_trace_row"])
    contact_rows = _read_contact_rows(trace_path, [pre_end, grasp_end])

    with np.load(trace_path, allow_pickle=False) as archive:
        layout = str(archive["action_layout_version"].tolist())
        dimensions = tuple(
            json.loads(str(archive["action_layout_dimensions_json"].tolist()))
        )
        if layout != ACTION_LAYOUT_VERSION or dimensions != ACTION_LAYOUT_DIMENSIONS:
            raise ValueError("sealed trace action layout changed")
        selected_links = list(
            json.loads(str(archive["selected_gripper_links_json"].tolist()))
        )
        arrays = {
            name: np.asarray(archive[name])
            for name in ("eef_pose", "object_pose", "joint_qpos", "component_masks")
        }

    arm = str(spec["arm"])
    pre_snapshot = _segment_snapshot(
        stage="pregrasp",
        execution=pre_execution,
        target=targets_by_id[pre_execution["segment_id"]],
        planner_segment=planners[0],
        arm=arm,
        contact_pairs=contact_rows[pre_end],
        selected_links=selected_links,
        **arrays,
    )
    grasp_snapshot = _segment_snapshot(
        stage="grasp",
        execution=grasp_execution,
        target=targets_by_id[grasp_execution["segment_id"]],
        planner_segment=planners[1],
        arm=arm,
        contact_pairs=contact_rows[grasp_end],
        selected_links=selected_links,
        **arrays,
    )
    gate = evaluate_preclose_sequence(pre_snapshot, grasp_snapshot)
    result = {
        "schema_version": "cmf_f3_preclose_real_trace_replay_case_v1",
        "case_directory": case_directory,
        "recipe_id": spec["recipe"]["recipe_id"],
        "recipe_sha256": spec["recipe_sha256"],
        "arm": arm,
        "source_bindings": {
            "scene_receipt_path": str(scene_path.resolve()),
            "scene_receipt_file_sha256": scene_file_sha,
            "scene_receipt_sha256": scene["receipt_sha256"],
            "physical_spec_path": str(spec_path.resolve()),
            "physical_spec_file_sha256": spec_file_sha,
            "physical_spec_sha256": spec["spec_sha256"],
            "physical_trace_path": str(trace_path.resolve()),
            "physical_trace_file_sha256": trace_file_sha,
            "sample_count": int(trace_receipt["sample_count"]),
        },
        "action_layout_version": layout,
        "action_layout_dimensions": list(dimensions),
        "gate": gate,
        "rejected_before_close": gate["stop_before_close"],
        "earliest_failure_stage": gate["earliest_failure_stage"],
        "earliest_failure_code": gate["earliest_failure_code"],
        "gpu_used_by_replay": False,
        "scene_created_by_replay": False,
        "planner_called_by_replay": False,
        "physical_action_executed_by_replay": False,
        "output_modified_by_replay": False,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def replay_sealed_cohort() -> dict:
    rows = [replay_case(case) for case in CASE_DIRECTORIES]
    result = {
        "schema_version": "cmf_f3_preclose_real_trace_replay_cohort_v1",
        "trace_root": str(TRACE_ROOT.resolve()),
        "ordered_cases": list(CASE_DIRECTORIES),
        "rows": rows,
        "case_count": len(rows),
        "rejected_before_close_count": sum(
            row["rejected_before_close"] is True for row in rows
        ),
        "all_four_rejected_before_close": len(rows) == 4
        and all(row["rejected_before_close"] is True for row in rows),
        "all_earliest_failures_pregrasp": all(
            row["earliest_failure_stage"] == "pregrasp" for row in rows
        ),
        "gpu_used": False,
        "scene_created": False,
        "planner_called": False,
        "physical_action_executed": False,
        "source_artifact_modified": False,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


__all__ = [
    "ACTION_LAYOUT_DIMENSIONS",
    "ACTION_LAYOUT_VERSION",
    "CASE_DIRECTORIES",
    "TRACE_ROOT",
    "file_sha",
    "replay_case",
    "replay_sealed_cohort",
]
