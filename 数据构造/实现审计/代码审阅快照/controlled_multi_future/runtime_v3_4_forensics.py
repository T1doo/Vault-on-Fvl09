"""Immutable Revision-9 forensics for runtime-v3_4 diagnosis-first work.

This module is deliberately CPU-only.  It reads already immutable nonformal
artifacts, derives compact causal evidence, and writes new files with
``O_EXCL``.  It never imports SAPIEN, initializes CUDA, changes an old
namespace, or authorizes collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .f2_inside_tracking_compensation_v7 import (
    R6_CAN_HALF_EXTENTS_M,
    R6_CAN_LOCAL_GEOMETRY_CENTER_M,
)
from .f3_physical_contact_signal_v8 import (
    classify_contact_pair_physical_hit_v8,
)
from .geometry import compose_pose, obb_corners, pose_matrix, relative_pose
from .runtime_v3_2_contracts import F2_PLASTICBOX_BASE2_CAVITY


DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_4"
STRATEGY = "diagnosis_first_multi_gpu_convergence"
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
DEFAULT_VAULT_ROOT = WORKSPACE_ROOT / "Vault-on-Fvl09"
AUDIT_ROOT_RELATIVE = Path("数据构造/实现审计")
PROBE_ROOT_RELATIVE = AUDIT_ROOT_RELATIVE / "probe_outputs"

F2_NAMESPACE = "nonformal_runtime_v3_3_f2_root_seed20260829_revision9_run1_gpu0"
F3_R8_NAMESPACE = "nonformal_runtime_v3_3_f3_root_seed20260829_revision8_run1_anygpu"
F3_R9_NAMESPACE = "nonformal_runtime_v3_3_f3_root_seed20260829_revision9_run1_gpu0"
F4_R4_NAMESPACE = "nonformal_runtime_v3_3_f4_staged_full_root_seed20260829_revision4_run1_gpu6"
F4_R9_NAMESPACE = "nonformal_runtime_v3_3_f4_staged_full_root_seed20260829_revision9_run1_gpu0"
F3_PROGRAMS = ("F3-VVHH", "F3-VHVH", "F3-VHHV")


def _require_workspace(path: Path, label: str) -> Path:
    result = Path(path).resolve()
    if result != WORKSPACE_ROOT and not str(result).startswith(
        str(WORKSPACE_ROOT) + "/"
    ):
        raise ValueError(f"{label} must remain under {WORKSPACE_ROOT}")
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _seal_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    result["output_sha256_scope"] = (
        "canonical JSON of this artifact with output_sha256 removed"
    )
    result["output_sha256"] = _canonical_sha256(result)
    return result


def validate_sealed_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    result = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    digest = result.pop("output_sha256", None)
    if not isinstance(digest, str) or digest != _canonical_sha256(result):
        raise ValueError("forensic artifact output_sha256 mismatch")
    result["output_sha256"] = digest
    return result


def _relative(path: Path, root: Path) -> str:
    return _require_workspace(path, "artifact path").relative_to(
        _require_workspace(root, "artifact root")
    ).as_posix()


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def _first_different_row(first: np.ndarray, second: np.ndarray) -> int | None:
    if first.ndim == 0 or second.ndim == 0:
        return 0 if not np.array_equal(first, second) else None
    count = min(len(first), len(second))
    for index in range(count):
        if not np.array_equal(first[index], second[index]):
            return index
    return count if len(first) != len(second) else None


def _array_comparison(first: np.ndarray, second: np.ndarray) -> dict[str, Any]:
    index = _first_different_row(first, second)
    result: dict[str, Any] = {
        "revision8_shape": list(first.shape),
        "revision9_shape": list(second.shape),
        "revision8_dtype": str(first.dtype),
        "revision9_dtype": str(second.dtype),
        "revision8_array_sha256": _array_sha256(first),
        "revision9_array_sha256": _array_sha256(second),
        "byte_equal": bool(np.array_equal(first, second)),
        "first_different_row": index,
    }
    if index is not None and first.ndim > 0 and second.ndim > 0:
        if index < min(len(first), len(second)) and np.issubdtype(
            first.dtype, np.number
        ) and np.issubdtype(second.dtype, np.number):
            result["maximum_absolute_difference_at_first_row"] = float(
                np.max(
                    np.abs(
                        np.asarray(first[index], dtype=np.float64)
                        - np.asarray(second[index], dtype=np.float64)
                    )
                )
            )
    return result


def _compare_npz(first_path: Path, second_path: Path) -> dict[str, Any]:
    with np.load(first_path, allow_pickle=False) as first, np.load(
        second_path, allow_pickle=False
    ) as second:
        common = sorted(set(first.files) & set(second.files))
        return {
            "revision8_file_sha256": _sha256_file(first_path),
            "revision9_file_sha256": _sha256_file(second_path),
            "revision8_fields": list(first.files),
            "revision9_fields": list(second.files),
            "common_field_comparisons": {
                key: _array_comparison(first[key], second[key]) for key in common
            },
        }


def _physical_contact_summary(
    pairs: Sequence[Mapping[str, Any]],
    first_names: set[str],
    second_names: set[str],
) -> dict[str, Any]:
    relevant = []
    for pair in pairs:
        bodies = {str(pair.get("body_a")), str(pair.get("body_b"))}
        if bodies & first_names and bodies & second_names:
            relevant.append(classify_contact_pair_physical_hit_v8(pair))
    return {
        "pair_count": len(relevant),
        "evidence_complete": bool(relevant)
        and all(item["evidence_complete"] is True for item in relevant),
        "physical_hit": any(
            item["physical_hit_for_gate"] is True for item in relevant
        ),
    }


def _linear_slope(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=np.float64)
    if len(array) < 2:
        return 0.0
    return float(np.polyfit(np.arange(len(array), dtype=np.float64), array, 1)[0])


def _f2_geometry_row(can_pose: np.ndarray, box_pose: np.ndarray) -> dict[str, Any]:
    geometry_pose = compose_pose(
        can_pose,
        [*R6_CAN_LOCAL_GEOMETRY_CENTER_M, 1.0, 0.0, 0.0, 0.0],
    )
    corners_world = obb_corners(geometry_pose, R6_CAN_HALF_EXTENTS_M)
    homogeneous = np.concatenate(
        (corners_world, np.ones((len(corners_world), 1), dtype=np.float64)),
        axis=1,
    )
    local = (np.linalg.inv(pose_matrix(box_pose)) @ homogeneous.T).T[:, :3]
    lower = np.asarray(F2_PLASTICBOX_BASE2_CAVITY["lower_m"], dtype=np.float64)
    upper = np.asarray(F2_PLASTICBOX_BASE2_CAVITY["upper_m"], dtype=np.float64)
    minimum = local.min(axis=0)
    maximum = local.max(axis=0)
    lower_margin = minimum - lower
    upper_margin = upper - maximum
    all_margin = np.concatenate((lower_margin, upper_margin))
    opening_axes = (0, 2)
    opening_margin = np.concatenate(
        (lower_margin[list(opening_axes)], upper_margin[list(opening_axes)])
    )
    geometry_local = relative_pose(box_pose, geometry_pose)
    opening_center_margin = np.concatenate(
        (
            geometry_local[list(opening_axes)] - lower[list(opening_axes)],
            upper[list(opening_axes)] - geometry_local[list(opening_axes)],
        )
    )
    opening_overlap = np.concatenate(
        (
            maximum[list(opening_axes)] - lower[list(opening_axes)],
            upper[list(opening_axes)] - minimum[list(opening_axes)],
        )
    )
    return {
        "can_geometry_center_box_local_m": geometry_local[:3].tolist(),
        "local_corner_min_m": minimum.tolist(),
        "local_corner_max_m": maximum.tolist(),
        "true_cavity_signed_margin_m": float(np.min(all_margin)),
        "true_cavity_obb": bool(np.min(all_margin) >= 0.0),
        "opening_projection_signed_margin_m": float(np.min(opening_margin)),
        "opening_projection_inside": bool(np.min(opening_margin) >= 0.0),
        "opening_center_signed_margin_m": float(np.min(opening_center_margin)),
        "opening_center_inside": bool(np.min(opening_center_margin) >= 0.0),
        "opening_projection_overlap_signed_m": float(np.min(opening_overlap)),
        "opening_projection_overlaps": bool(np.min(opening_overlap) > 0.0),
        "vertical_lower_margin_m": float(lower_margin[1]),
        "vertical_upper_margin_m": float(upper_margin[1]),
        "can_to_box_relative_orientation_rad": float(
            quaternion_angular_error(
                geometry_local[3:],
                [1.0, 0.0, 0.0, 0.0],
            )
        ),
    }


def build_f2_release_timeseries(vault_root: Path = DEFAULT_VAULT_ROOT) -> dict[str, Any]:
    vault = _require_workspace(vault_root, "Vault root")
    audit = vault / AUDIT_ROOT_RELATIVE
    namespace = vault / PROBE_ROOT_RELATIVE / F2_NAMESPACE
    raw_path = namespace / "root/branches/F2-inside/partial_trace_source.npz"
    receipt_path = namespace / "root/branches/F2-inside/receipt.json"
    manifest_path = audit / "F2_ROOT_RUNTIME_V3_3_REVISION9_FAILURE_EVIDENCE_MANIFEST_20260830.json"
    receipt = _load_json(receipt_path)
    recorded = receipt["structured_family_failure_evidence"][
        "f2_balanced_preload_release_v9"
    ]
    with np.load(raw_path, allow_pickle=False) as raw:
        markers = json.loads(str(raw["event_markers_json"]))
        start = int(markers["f2_inside_balanced_preload_start"])
        end = int(markers["f2_inside_balanced_preload_hold_end"])
        selected_rows = list(range(start, end + 1))
        selected_fingers = set(json.loads(str(raw["selected_gripper_links_json"])))
        can_name = "f2_main_can"
        box_name = "f2_plasticbox"
        # NPZ members are compressed independently.  Materialize each selected
        # member once; indexing ``raw[key]`` in the loop would decompress the
        # same 60–100 MB member hundreds of times.
        step_index = np.asarray(raw["step_index"])
        timestamp = np.asarray(raw["timestamp"])
        can_poses = np.asarray(raw["role_object_pose__main_can"])
        box_poses = np.asarray(raw["role_object_pose__box"])
        can_linear = np.asarray(raw["role_object_linear_velocity__main_can"])
        can_angular = np.asarray(raw["role_object_angular_velocity__main_can"])
        finger_qpos = np.asarray(raw["realized_left_gripper_joint_qpos"])
        finger_target = np.asarray(raw["left_gripper_joint_drive_target"])
        finger_qvel = np.asarray(raw["realized_left_gripper_joint_qvel"])
        finger_qf = np.asarray(raw["realized_left_gripper_joint_qf"])
        contact_json = np.asarray(raw["contact_pairs_json"])
        rows = []
        initial_relative = None
        for index in selected_rows:
            can_pose = can_poses[index]
            box_pose = box_poses[index]
            geometry = _f2_geometry_row(can_pose, box_pose)
            relative = relative_pose(box_pose, can_pose)
            if initial_relative is None:
                initial_relative = relative
            pairs = json.loads(str(contact_json[index]))
            finger = _physical_contact_summary(
                pairs, {can_name}, selected_fingers
            )
            box = _physical_contact_summary(pairs, {can_name}, {box_name})
            rows.append(
                {
                    "trace_row": index,
                    "step_index": int(step_index[index]),
                    "timestamp_seconds": float(timestamp[index]),
                    "linear_speed_mps": float(
                        np.linalg.norm(can_linear[index])
                    ),
                    "angular_speed_rps": float(
                        np.linalg.norm(can_angular[index])
                    ),
                    "can_pose": can_pose.tolist(),
                    "can_relative_translation_from_partial_start_m": (
                        relative[:3] - initial_relative[:3]
                    ).tolist(),
                    "can_relative_orientation_from_partial_start_rad": float(
                        quaternion_angular_error(relative[3:], initial_relative[3:])
                    ),
                    "actual_left_finger_qpos_m": np.asarray(
                        finger_qpos[index]
                    ).tolist(),
                    "left_finger_drive_target_m": np.asarray(
                        finger_target[index]
                    ).tolist(),
                    "left_finger_qvel_mps": np.asarray(
                        finger_qvel[index]
                    ).tolist(),
                    "left_finger_qf_audit_only": np.asarray(
                        finger_qf[index]
                    ).tolist(),
                    "finger_contact": finger,
                    "box_contact": box,
                    **geometry,
                }
            )
    last_50 = rows[-50:]
    last_10 = rows[-10:]
    finger_loss = next(
        (
            item["trace_row"]
            for item in rows
            if item["finger_contact"]["physical_hit"] is False
        ),
        None,
    )
    metrics = {
        "partial_window_row_count": len(rows),
        "first_no_physical_finger_contact_trace_row": finger_loss,
        "maximum_linear_speed_mps": max(item["linear_speed_mps"] for item in rows),
        "maximum_angular_speed_rps": max(item["angular_speed_rps"] for item in rows),
        "last_50_maximum_linear_speed_mps": max(
            item["linear_speed_mps"] for item in last_50
        ),
        "last_50_maximum_angular_speed_rps": max(
            item["angular_speed_rps"] for item in last_50
        ),
        "last_50_linear_speed_slope_mps_per_frame": _linear_slope(
            [item["linear_speed_mps"] for item in last_50]
        ),
        "last_50_angular_speed_slope_rps_per_frame": _linear_slope(
            [item["angular_speed_rps"] for item in last_50]
        ),
        "last_50_true_cavity_margin_slope_m_per_frame": _linear_slope(
            [item["true_cavity_signed_margin_m"] for item in last_50]
        ),
        "last_50_opening_margin_slope_m_per_frame": _linear_slope(
            [item["opening_projection_signed_margin_m"] for item in last_50]
        ),
        "final_true_cavity_signed_margin_m": rows[-1][
            "true_cavity_signed_margin_m"
        ],
        "final_opening_projection_signed_margin_m": rows[-1][
            "opening_projection_signed_margin_m"
        ],
        "final_opening_center_signed_margin_m": rows[-1][
            "opening_center_signed_margin_m"
        ],
        "final_opening_projection_overlap_signed_m": rows[-1][
            "opening_projection_overlap_signed_m"
        ],
        "last_10_fingers_detached": all(
            item["finger_contact"]["physical_hit"] is False for item in last_10
        ),
        "last_10_continuous_box_contact": all(
            item["box_contact"]["physical_hit"] is True for item in last_10
        ),
        "final_true_cavity_obb": rows[-1]["true_cavity_obb"],
        "final_opening_projection_inside": rows[-1]["opening_projection_inside"],
        "final_opening_center_inside": rows[-1]["opening_center_inside"],
        "final_opening_projection_overlaps": rows[-1][
            "opening_projection_overlaps"
        ],
    }
    conclusion = {
        "classification": "revision9_gate_conflated_release_safety_with_final_inside_success",
        "evidence": {
            "finger_disengagement_complete": metrics["last_10_fingers_detached"],
            "box_contact_continuous": metrics["last_10_continuous_box_contact"],
            "opening_safety_envelope_at_gate": bool(
                metrics["final_opening_center_inside"]
                and metrics["final_opening_projection_overlaps"]
            ),
            "strict_opening_projection_not_yet_inside": not metrics[
                "final_opening_projection_inside"
            ],
            "final_true_cavity_not_yet_satisfied": not metrics[
                "final_true_cavity_obb"
            ],
            "final_angular_stability_not_yet_satisfied": recorded["gate"][
                "checks"
            ]["stable_angular_window"]
            is False,
        },
        "next_frozen_test": (
            "safety gate permits full-open without requiring final cavity/stability; "
            "final success is evaluated only after exactly 250 settle frames"
        ),
    }
    payload = {
        "schema_version": "cmf_runtime_v3_4_forensic_f2_release_timeseries_v1",
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_strategy": STRATEGY,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "source_raw_path": _relative(raw_path, vault),
        "source_raw_sha256": _sha256_file(raw_path),
        "source_receipt_path": _relative(receipt_path, vault),
        "source_receipt_sha256": _sha256_file(receipt_path),
        "source_manifest_path": _relative(manifest_path, vault),
        "source_manifest_sha256": _sha256_file(manifest_path),
        "selected_row_indices": {
            "start": start,
            "end_inclusive": end,
            "count": len(rows),
            "event_markers": markers,
        },
        "selected_fields": [
            "step_index",
            "timestamp",
            "role_object_pose__main_can",
            "role_object_linear_velocity__main_can",
            "role_object_angular_velocity__main_can",
            "role_object_pose__box",
            "realized_left_gripper_joint_qpos/qvel/qf",
            "left_gripper_joint_drive_target",
            "contact_pairs_json",
        ],
        "derived_metric_formula": {
            "speed": "Euclidean norm of pose-derived 250 Hz linear/angular velocity",
            "true_cavity_margin": "minimum signed margin of all can OBB corners to all six cavity planes",
            "opening_projection_margin": "minimum signed margin on box-local axes 0 and 2",
            "opening_safety_envelope": "can geometry center inside the cavity opening rectangle and can OBB projection still overlaps that rectangle; this is not final full-OBB inside",
            "contact": "physical iff impulse_norm_sum > 1e-10 or any signed separation <= 0; missing signal fails closed",
            "relative_orientation": "sign-invariant quaternion angular error in box frame",
            "trend": "ordinary least-squares slope versus trace frame index",
        },
        "timeseries": rows,
        "derived_metrics": metrics,
        "forensic_conclusion": conclusion,
    }
    return _seal_payload(payload)


def _artifact_summary(path: Path) -> dict[str, Any]:
    value = _load_json(path)
    return {
        "path": str(path),
        "file_sha256": _sha256_file(path),
        "artifact_sha256": value.get("artifact_sha256"),
        "prefix_action_sha256": value.get("prefix_action_sha256"),
        "prefix_step_count": value.get("prefix_step_count"),
        "semantic_prefix_step_count": value.get("semantic_prefix_step_count"),
        "arrays_file_sha256": value.get(
            "prefix_arrays_npz_sha256", value.get("arrays_file_sha256")
        ),
        "execution_spec_sha256": value.get("execution_spec_sha256"),
        "planner_query_receipts_sha256": _canonical_sha256(
            {"planner_query_receipts": value.get("planner_query_receipts", [])}
        ),
        "reference_event_boundaries": value.get("reference_event_boundaries"),
    }


def _trace_boundary_sample(raw: Any, index: int) -> dict[str, Any]:
    eef = np.asarray(raw["eef_pose"][index], dtype=np.float64)
    bottle = np.asarray(raw["role_object_pose__bottle"][index], dtype=np.float64)
    return {
        "trace_row": int(index),
        "controller_effective_setpoint": np.asarray(
            raw["controller_effective_setpoint"][index]
        ).tolist(),
        "eef_pose": eef.tolist(),
        "bottle_pose": bottle.tolist(),
        "T_eef_actor": relative_pose(eef, bottle).tolist(),
        "left_gripper_joint_drive_target": np.asarray(
            raw["left_gripper_joint_drive_target"][index]
        ).tolist(),
        "realized_left_gripper_joint_qpos": np.asarray(
            raw["realized_left_gripper_joint_qpos"][index]
        ).tolist(),
        "realized_left_gripper_joint_qf": (
            np.asarray(raw["realized_left_gripper_joint_qf"][index]).tolist()
            if "realized_left_gripper_joint_qf" in raw.files
            else None
        ),
        "selected_gripper_contact": bool(raw["selected_gripper_contact"][index]),
    }


def _git_source_diff(vault: Path) -> dict[str, Any]:
    revision8 = "0e8b27f142a35129cef77744d1cd72b4168e7eaa"
    revision9 = "2320369546bffd9df37da0c16644c14ab8663f0c"
    command = [
        "git",
        "diff",
        "--name-only",
        revision8,
        revision9,
        "--",
        "数据构造/实现审计/代码审阅快照/controlled_multi_future",
    ]
    completed = subprocess.run(
        command,
        cwd=vault,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    files = [line for line in completed.stdout.splitlines() if line]
    return {
        "revision8_content_commit": revision8,
        "revision9_content_commit": revision9,
        "command": command,
        "changed_files": files,
        "changed_files_sha256": _canonical_sha256({"files": files}),
    }


def build_f3_rev8_rev9_diff(vault_root: Path = DEFAULT_VAULT_ROOT) -> dict[str, Any]:
    vault = _require_workspace(vault_root, "Vault root")
    audit = vault / AUDIT_ROOT_RELATIVE
    r8 = vault / PROBE_ROOT_RELATIVE / F3_R8_NAMESPACE / "root"
    r9 = vault / PROBE_ROOT_RELATIVE / F3_R9_NAMESPACE / "root"
    manifest_paths = {
        "revision8": audit / "F3_ROOT_RUNTIME_V3_3_REVISION8_FAILURE_EVIDENCE_MANIFEST_20260830.json",
        "revision9": audit / "F3_ROOT_RUNTIME_V3_3_REVISION9_FAILURE_EVIDENCE_MANIFEST_20260830.json",
    }
    prefix_json = {
        "revision8": r8 / "canonical_prefix_artifact/canonical_prefix_artifact.json",
        "revision9": r9 / "canonical_prefix_artifact/canonical_prefix_artifact.json",
    }
    prefix_npz = {
        "revision8": r8 / "canonical_prefix_artifact/prefix_arrays.npz",
        "revision9": r9 / "canonical_prefix_artifact/prefix_arrays.npz",
    }
    prefix_comparison = _compare_npz(prefix_npz["revision8"], prefix_npz["revision9"])
    prefix_controller_fields = (
        "effective_setpoint_actions",
        "requested_commands",
        "component_masks",
        "left_gripper_joint_drive_targets",
    )
    prefix_mismatch_candidates = [
        prefix_comparison["common_field_comparisons"][field][
            "first_different_row"
        ]
        for field in prefix_controller_fields
        if prefix_comparison["common_field_comparisons"][field][
            "first_different_row"
        ]
        is not None
    ]
    prefix_first_controller_mismatch = (
        min(prefix_mismatch_candidates) if prefix_mismatch_candidates else None
    )
    per_program = {}
    earliest_controller_mismatch: int | None = None
    source_raw_path = {}
    source_raw_sha256 = {}
    selected_rows = {}
    for program in F3_PROGRAMS:
        r8_trace = r8 / f"branches/{program}/trace_source.npz"
        r9_trace = r9 / f"branches/{program}/partial_trace_source.npz"
        source_raw_path[program] = {
            "revision8": _relative(r8_trace, vault),
            "revision9": _relative(r9_trace, vault),
        }
        source_raw_sha256[program] = {
            "revision8": _sha256_file(r8_trace),
            "revision9": _sha256_file(r9_trace),
        }
        with np.load(r8_trace, allow_pickle=False) as first, np.load(
            r9_trace, allow_pickle=False
        ) as second:
            markers8 = json.loads(str(first["event_markers_json"]))
            markers9 = json.loads(str(second["event_markers_json"]))
            preopen8 = int(markers8["f3_open_command_start"] - 1)
            preopen9 = len(second["step_index"]) - 1
            chosen8 = sorted(
                set([0, preopen8, *[int(v) for v in markers8.values()]])
            )
            chosen9 = sorted(
                set([0, preopen9, *[int(v) for v in markers9.values()]])
            )
            selected_rows[program] = {
                "revision8": chosen8,
                "revision9": chosen9,
                "revision8_preopen_row": preopen8,
                "revision9_preopen_row": preopen9,
            }
            fields = (
                "controller_effective_setpoint",
                "requested_command",
                "component_masks",
                "joint_qpos",
                "eef_pose",
                "role_object_pose__bottle",
                "left_gripper_joint_drive_target",
                "realized_left_gripper_joint_qpos",
                "selected_gripper_contact",
            )
            trace_comparison = {
                field: _array_comparison(first[field], second[field])
                for field in fields
            }
            controller_fields = (
                "controller_effective_setpoint",
                "requested_command",
                "component_masks",
                "left_gripper_joint_drive_target",
            )
            candidates = [
                trace_comparison[field]["first_different_row"]
                for field in controller_fields
                if trace_comparison[field]["first_different_row"] is not None
            ]
            mismatch = min(candidates) if candidates else None
            if mismatch is not None:
                earliest_controller_mismatch = (
                    mismatch
                    if earliest_controller_mismatch is None
                    else min(earliest_controller_mismatch, mismatch)
                )
            boundary = {
                "revision8_prefix_end": _trace_boundary_sample(
                    first, int(markers8["canonical_prefix_end"])
                ),
                "revision9_prefix_end": _trace_boundary_sample(
                    second, int(markers9["canonical_prefix_end"])
                ),
                "revision8_preopen": _trace_boundary_sample(first, preopen8),
                "revision9_preopen": _trace_boundary_sample(second, preopen9),
            }
        suffix_json8 = r8 / f"suffix_artifacts/{program}/frozen_suffix_artifact.json"
        suffix_json9 = r9 / f"suffix_artifacts/{program}/frozen_suffix_artifact.json"
        suffix_npz8 = r8 / f"suffix_artifacts/{program}/suffix_controls.npz"
        suffix_npz9 = r9 / f"suffix_artifacts/{program}/suffix_controls.npz"
        per_program[program] = {
            "trace_event_boundaries": {
                "revision8": markers8,
                "revision9": markers9,
            },
            "trace_field_comparison": trace_comparison,
            "first_preopen_controller_mismatch_row": mismatch,
            "boundary_samples": boundary,
            "suffix_artifact": {
                "revision8": _artifact_summary(suffix_json8),
                "revision9": _artifact_summary(suffix_json9),
            },
            "suffix_control_comparison": _compare_npz(suffix_npz8, suffix_npz9),
        }
    classification = (
        "A_input_or_control_changed"
        if earliest_controller_mismatch is not None
        else "C_insufficient_evidence"
    )
    payload = {
        "schema_version": "cmf_runtime_v3_4_forensic_f3_revision8_revision9_diff_v1",
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_strategy": STRATEGY,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "source_raw_path": source_raw_path,
        "source_raw_sha256": source_raw_sha256,
        "source_manifest_path": {
            key: _relative(path, vault) for key, path in manifest_paths.items()
        },
        "source_manifest_sha256": {
            key: _sha256_file(path) for key, path in manifest_paths.items()
        },
        "selected_row_indices": selected_rows,
        "selected_fields": [
            "controller_effective_setpoint",
            "requested_command",
            "component_masks",
            "joint_qpos",
            "eef_pose",
            "role_object_pose__bottle",
            "left_gripper_joint_drive_target",
            "realized_left_gripper_joint_qpos",
            "realized_left_gripper_joint_qf when available",
            "selected_gripper_contact",
            "event_markers_json",
        ],
        "derived_metric_formula": {
            "array_identity": "SHA-256 over C-contiguous dtype-preserving array bytes",
            "first_mismatch": "first row where np.array_equal is false; length-only mismatch is common length",
            "T_eef_actor": "inverse(T_world_eef) @ T_world_actor",
            "orientation": "sign-invariant quaternion angular error",
        },
        "prefix_artifact": {
            "revision8": _artifact_summary(prefix_json["revision8"]),
            "revision9": _artifact_summary(prefix_json["revision9"]),
        },
        "prefix_control_comparison": prefix_comparison,
        "per_program": per_program,
        "source_diff": _git_source_diff(vault),
        "first_preopen_mismatch_step": (
            prefix_first_controller_mismatch
            if prefix_first_controller_mismatch is not None
            else earliest_controller_mismatch
        ),
        "first_saved_trace_state_mismatch_row": earliest_controller_mismatch,
        "causal_classification": classification,
        "causal_conclusion": (
            "Revision 8 and Revision 9 did not replay byte-identical pre-open inputs. "
            "The canonical prefix effective/requested control differs at row 0, so "
            "the observed grasp outcome cannot be classified as same-input contact nondeterminism."
        ),
        "next_frozen_test": (
            "one common geometry-derived grasp contract is applied to all three fresh "
            "diagnostic scenes; each stops before release after shared V plus one suffix event"
        ),
    }
    return _seal_payload(payload)


def _find_targets(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, dict):
        targets = value.get("targets")
        if isinstance(targets, list) and any(
            isinstance(item, dict) and item.get("segment_id") == "A_carry_mid"
            for item in targets
        ):
            return targets
        for item in value.values():
            found = _find_targets(item)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_targets(item)
            if found is not None:
                return found
    return None


def _segment(receipt: Mapping[str, Any], segment_id: str) -> dict[str, Any]:
    for item in receipt["evidence"]["segment_receipts"]:
        if item.get("segment_id") == segment_id:
            return item
    raise KeyError(segment_id)


def build_f4_carry_pose_comparison(vault_root: Path = DEFAULT_VAULT_ROOT) -> dict[str, Any]:
    vault = _require_workspace(vault_root, "Vault root")
    audit = vault / AUDIT_ROOT_RELATIVE
    r4 = vault / PROBE_ROOT_RELATIVE / F4_R4_NAMESPACE
    r9 = vault / PROBE_ROOT_RELATIVE / F4_R9_NAMESPACE
    receipt_paths = {
        "revision4": r4 / "f4_staged_gate/gate_A/preflight_receipt.json",
        "revision9": r9 / "f4_staged_gate/gate_A/preflight_receipt.json",
    }
    raw_paths = {
        "revision4": r4 / "f4_staged_gate/gate_A/trace_source.npz",
        "revision9": r9 / "f4_staged_gate/gate_A/preflight_trace_source.npz",
    }
    manifest_paths = {
        "revision4": audit / "F4_ROOT_RUNTIME_V3_3_REVISION4_FAILURE_EVIDENCE_MANIFEST_20260830.json",
        "revision9": audit / "F4_ROOT_RUNTIME_V3_3_REVISION9_FAILURE_EVIDENCE_MANIFEST_20260830.json",
    }
    receipts = {key: _load_json(path) for key, path in receipt_paths.items()}
    targets4 = receipts["revision4"]["execution_spec"]["targets"]
    targets9 = _find_targets(receipts["revision9"])
    if targets9 is None:
        raise ValueError("Revision-9 F4 preflight lacks frozen A targets")
    pose4 = np.asarray(
        next(item["pose"] for item in targets4 if item["segment_id"] == "A_carry_mid"),
        dtype=np.float64,
    )
    pose9 = np.asarray(
        next(item["pose"] for item in targets9 if item["segment_id"] == "A_carry_mid"),
        dtype=np.float64,
    )
    segment4 = _segment(receipts["revision4"], "A_carry_mid")
    segment9 = _segment(receipts["revision9"], "A_carry_mid")
    start4 = np.asarray(segment4["start_qpos"], dtype=np.float64)
    start9 = np.asarray(segment9["start_qpos"], dtype=np.float64)
    trace_rows = {}
    for key, path in raw_paths.items():
        with np.load(path, allow_pickle=False) as raw:
            trace_rows[key] = {
                "start": 0,
                "end_inclusive": len(raw["step_index"]) - 1,
                "count": len(raw["step_index"]),
            }
    comparison = {
        "revision4_successful_carry_mid_pose": pose4.tolist(),
        "revision9_failed_carry_mid_pose": pose9.tolist(),
        "position_delta_revision9_minus_revision4_m": (pose9[:3] - pose4[:3]).tolist(),
        "position_delta_norm_m": float(np.linalg.norm(pose9[:3] - pose4[:3])),
        "height_delta_m": float(pose9[2] - pose4[2]),
        "orientation_delta_rad": float(quaternion_angular_error(pose9[3:], pose4[3:])),
        "start_qpos_sha256": {
            "revision4": segment4["start_qpos_sha256"],
            "revision9": segment9["start_qpos_sha256"],
        },
        "start_qpos_l2_difference": float(np.linalg.norm(start9 - start4)),
        "planner_status": {
            "revision4": segment4["planner_status"],
            "revision9": segment9["planner_status"],
        },
        "revision4_planned_end_qpos_sha256": segment4.get("end_qpos_sha256"),
        "revision9_failure_record_end_qpos_sha256": segment9.get("end_qpos_sha256"),
        "revision9_failed_endpoint_terminal_qpos_available": False,
        "saved_chain_minimum_terminal_joint_limit_margin_rad": {
            "revision4": receipts["revision4"]["evidence"].get(
                "minimum_terminal_joint_limit_margin_rad"
            ),
            "revision9_successful_prefix_only": receipts["revision9"]["evidence"].get(
                "minimum_terminal_joint_limit_margin_rad"
            ),
        },
        "collision_check_source": {
            "revision4": receipts["revision4"]["evidence"].get(
                "planner_collision_check_source"
            ),
            "revision9": receipts["revision9"]["evidence"].get(
                "planner_collision_check_source"
            ),
        },
        "revision9_motiongen_failure": segment9["planner_query_receipt"].get(
            "motiongen_result_side_channel"
        ),
    }
    corridor_candidates = [
        {
            "priority": 1,
            "candidate_id": "r4_successful_carry_orientation_and_corridor",
            "rule": "reuse Revision-4 successful carry-mid orientation and corridor geometry",
        },
        {
            "priority": 2,
            "candidate_id": "proven_branch_neutral_carry_pose",
            "rule": "chain lift to the frozen branch-neutral carry pose before preplace",
        },
        {
            "priority": 3,
            "candidate_id": "lower_carry_height",
            "rule": "retain current top-down orientation but use the minimum obstacle-derived carry height",
        },
        {
            "priority": 4,
            "candidate_id": "intermediate_corridor_waypoint",
            "rule": "add one fixed intermediate waypoint; endpoint IK remains mandatory",
        },
    ]
    payload = {
        "schema_version": "cmf_runtime_v3_4_forensic_f4_carry_pose_comparison_v1",
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_strategy": STRATEGY,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "source_raw_path": {
            key: _relative(path, vault) for key, path in raw_paths.items()
        },
        "source_raw_sha256": {
            key: _sha256_file(path) for key, path in raw_paths.items()
        },
        "source_manifest_path": {
            key: _relative(path, vault) for key, path in manifest_paths.items()
        },
        "source_manifest_sha256": {
            key: _sha256_file(path) for key, path in manifest_paths.items()
        },
        "source_receipt_path": {
            key: _relative(path, vault) for key, path in receipt_paths.items()
        },
        "source_receipt_sha256": {
            key: _sha256_file(path) for key, path in receipt_paths.items()
        },
        "selected_row_indices": trace_rows,
        "selected_fields": [
            "execution_spec.targets",
            "segment_receipts.A_carry_mid.start_qpos/end_qpos",
            "planner status and MotionGen side channel",
            "minimum terminal joint-limit margin",
            "planner collision-check source",
        ],
        "derived_metric_formula": {
            "position_delta": "Revision9 xyz minus Revision4 xyz",
            "position_norm": "Euclidean norm of carry-mid xyz delta",
            "orientation_delta": "sign-invariant quaternion angular error",
            "start_qpos_delta": "Euclidean norm over the saved complete articulation qpos",
        },
        "comparison": comparison,
        "fixed_order_corridor_candidates": corridor_candidates,
        "forensic_conclusion": (
            "The frozen layout/right arm is not proven infeasible. Revision 9 changed "
            "carry height and orientation relative to the Revision-4 successful endpoint; "
            "its A_carry_mid endpoint itself had no IK solution."
        ),
        "next_frozen_test": (
            "planner-only fixed-order corridor list; choose the first chained candidate "
            "that proves endpoint IK, collision, joint margin, and qpos continuity"
        ),
    }
    return _seal_payload(payload)


def _render_markdown(value: Mapping[str, Any], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"- design_version: `{value['design_version']}`",
        f"- implementation_version: `{value['implementation_version']}`",
        f"- formal_data: `{str(value['formal_data']).lower()}`",
        f"- stage0_data: `{str(value['stage0_data']).lower()}`",
        f"- output_sha256: `{value['output_sha256']}`",
        "",
        "## 机器可读正文",
        "",
        "```json",
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def _write_exclusive(path: Path, data: bytes) -> None:
    output = _require_workspace(path, "forensic output")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def write_forensic_pair(
    value: Mapping[str, Any], json_path: Path, markdown_path: Path, title: str
) -> dict[str, Any]:
    validated = validate_sealed_payload(value)
    json_data = (
        json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    markdown_data = _render_markdown(validated, title).encode("utf-8")
    _write_exclusive(json_path, json_data)
    try:
        _write_exclusive(markdown_path, markdown_data)
    except BaseException:
        # Preserve the already-created JSON as partial immutable evidence.
        raise
    return {
        "json_path": str(json_path),
        "json_file_sha256": hashlib.sha256(json_data).hexdigest(),
        "markdown_path": str(markdown_path),
        "markdown_file_sha256": hashlib.sha256(markdown_data).hexdigest(),
        "output_sha256": validated["output_sha256"],
    }


def build_all(vault_root: Path = DEFAULT_VAULT_ROOT) -> dict[str, dict[str, Any]]:
    return {
        "F2": build_f2_release_timeseries(vault_root),
        "F3": build_f3_rev8_rev9_diff(vault_root),
        "F4": build_f4_carry_pose_comparison(vault_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = _require_workspace(args.output_dir, "forensic output directory")
    values = build_all(args.vault_root)
    specs = {
        "F2": (
            "RUNTIME_V3_4_FORENSIC_F2_RELEASE_TIMESERIES",
            "runtime-v3_4 F2 release timeseries forensic",
        ),
        "F3": (
            "RUNTIME_V3_4_FORENSIC_F3_REV8_REV9_DIFF",
            "runtime-v3_4 F3 Revision 8–9 causal diff",
        ),
        "F4": (
            "RUNTIME_V3_4_FORENSIC_F4_CARRY_POSE_COMPARISON",
            "runtime-v3_4 F4 carry-pose comparison",
        ),
    }
    receipts = {}
    for family, value in values.items():
        stem, title = specs[family]
        receipts[family] = write_forensic_pair(
            value, output / f"{stem}.json", output / f"{stem}.md", title
        )
    print(json.dumps(receipts, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
