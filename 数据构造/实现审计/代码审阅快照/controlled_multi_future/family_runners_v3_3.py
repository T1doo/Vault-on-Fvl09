"""Strict-prefix family controllers for runtime-v3_3."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .current_hasher import hash_array, hash_json
from .families import F4SubtaskOrder
from .f2_mutually_exclusive_region_layout_v2 import (
    BESIDE_INNER_M,
    BESIDE_OUTER_M,
    BESIDE_SECTORS_RELATIVE_XY_M,
    BOX_INSIDE_CENTER_OFFSET_WORLD_M,
    BOX_INSIDE_HALF_XY_M,
    LAYOUT as F2_LAYOUT_V2,
    LAYOUT_VERSION as F2_LAYOUT_VERSION_V2,
    SCALE_TOP_CENTER_OFFSET_WORLD_M,
    SCALE_TOP_HALF_XY_M,
    TABLE_BOUNDS_XY as F2_TABLE_BOUNDS_XY,
)
from .f2_suffix_routes_v3 import (
    BESIDE_CANDIDATES as F2_BESIDE_CANDIDATES_V3,
    BESIDE_PLANNER_SEED as F2_BESIDE_PLANNER_SEED_V3,
    audit_beside_candidate_receipts,
    audit_f2_held_transport_contacts,
    build_beside_route,
    build_inside_gravity_drop_route,
)
from .f2_beside_historical_safe_route_v4 import (
    HISTORICAL_SAFE_STAND_RELATIVE_XY_M,
    actor_origin_z_for_table_support,
    build_historical_safe_beside_route,
    target_facility_clearance_audit,
)
from .family_runners_v3_1 import (
    BLOCK_HALF_EXTENTS,
    F3_H_NOMINAL_AMPLITUDE_M_V3_3,
    F3_V_NOMINAL_AMPLITUDE_M_V3_3,
    MINIMUM_NEUTRAL_CONFIRMATION_STEPS,
    _actor_half_extents,
    _actor_geometry_center_pose,
    _actor_local_geometry_bounds,
    _arm_eef_pose,
    _arm_gripper_open,
    _arm_tag,
    _arm_tag_left,
    _entity,
    _execute_control,
    _gripper_below_eef_envelope,
    _move_arm,
    _move_left,
    _must_action,
    _plan_chain,
    _planner_reset,
    _pose,
    _position_map,
    _raw_result as _legacy_raw_result,
    _stable_and_support,
    _targets_by_segment_id,
    _wait_and_record,
    get_family_runner,
)
from .f3_clearance_route_v3 import (
    F3_CENTRAL_HOLD_STEPS,
    F3_GRASP_BOUNDARIES,
    F3_PAD_HALF_EXTENTS_M,
    audit_f3_free_space_event_contacts,
    audit_f3_grasp_boundary_stability,
    build_f3_clearance_height_audit,
    build_f3_clearance_route_targets,
    frozen_f3_grasp_contract,
    time_dilate_f3_carry_control_2x,
)
from .f3_pre_v_evidence_v4 import (
    F3PreVBoundaryGateFailure,
    build_f3_pre_v_evidence_v4,
    require_f3_pre_v_gate,
)
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    footprint_inside_local_region,
    obb_corners,
    pose_matrix,
    quaternion_orientation_error,
    quaternion_angular_velocity,
    relative_pose,
    world_axis_offset_pose,
    world_z_yaw_pose,
)
from .f1_uniform_carry_hub_v2 import (
    F1_CARRY_HUB_VERSION,
    REVISION2_SEGMENT_ORDER as F1_REVISION2_SEGMENT_ORDER,
    build_uniform_carry_hub_targets,
)
from .f4_uniform_block_carry_midpoint_v3 import (
    F4_SEGMENTED_BLOCK_SUFFIXES,
    F4_UNIFORM_BLOCK_CARRY_VERSION,
    expand_uniform_f4_block_carry_targets,
    validate_uniform_f4_block_carry_targets,
)
from .f4_uniform_tilted_grasp_v4 import (
    ROUTE_VERSION as F4_TILTED_ROUTE_VERSION,
    audit_uniform_tilted_f4_geometry,
    build_uniform_tilted_f4_block_groups,
)
from .planner_dtype_v3_2 import planner_array
from .probes.runtime_trace import _rigid_velocity_with_provenance
from .runtime_v2_contracts import (
    PLASTICBOX_BASE3_CAVITY,
    PROVISIONAL_RUNTIME_THRESHOLDS,
    TRAY_BASE0_SUPPORT_REGION,
)
from .runtime_v3_1_contracts import classify_f3_release_dynamics_v3_1
from .runtime_v3_2_contracts import (
    F2_INSIDE_LOCAL_QUATERNION_WXYZ,
    F2_PLASTICBOX_BASE2_CAVITY,
)
from .signals import closed_loop_event_metrics
from .verifiers import (
    verify_realized_motion_metrics,
    verify_staged_non_target_displacement,
    verify_true_cavity_obb,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLANNER_SEED = 20260828
SUFFIX_CACHE_ATTRIBUTE = "_cmf_v3_3_suffix_control_cache"
F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2 = 50
F3_CLOSED_LOOP_PRIMITIVE_VERSION = "f3_pose_consistent_time_dilated_closed_loop_v2"


def _raw_result(*args, **kwargs):
    kwargs["implementation_version"] = "controlled_multi_future_runtime_v3_3"
    return _legacy_raw_result(*args, **kwargs)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def planner_source_hash_v3_3() -> str:
    return hash_json(
        {
            "envs/_base_task.py": _sha256_file(
                PROJECT_ROOT / "envs/_base_task.py"
            ),
            "envs/robot/robot.py": _sha256_file(
                PROJECT_ROOT / "envs/robot/robot.py"
            ),
            "envs/robot/planner.py": _sha256_file(
                PROJECT_ROOT / "envs/robot/planner.py"
            ),
            "f1_uniform_carry_hub_v2.py": _sha256_file(
                Path(__file__).with_name("f1_uniform_carry_hub_v2.py")
            ),
            "f2_suffix_routes_v3.py": _sha256_file(
                Path(__file__).with_name("f2_suffix_routes_v3.py")
            ),
            "f2_beside_historical_safe_route_v4.py": _sha256_file(
                Path(__file__).with_name("f2_beside_historical_safe_route_v4.py")
            ),
            "f3_clearance_route_v3.py": _sha256_file(
                Path(__file__).with_name("f3_clearance_route_v3.py")
            ),
            "f3_pre_v_evidence_v4.py": _sha256_file(
                Path(__file__).with_name("f3_pre_v_evidence_v4.py")
            ),
            "f4_uniform_block_carry_midpoint_v3.py": _sha256_file(
                Path(__file__).with_name("f4_uniform_block_carry_midpoint_v3.py")
            ),
            "f4_uniform_tilted_grasp_v4.py": _sha256_file(
                Path(__file__).with_name("f4_uniform_tilted_grasp_v4.py")
            ),
            "project_cube_grasp_pose_v1.py": _sha256_file(
                Path(__file__).with_name("project_cube_grasp_pose_v1.py")
            ),
            "family_runners_v3_1.py": _sha256_file(
                Path(__file__).with_name("family_runners_v3_1.py")
            ),
            "family_runners_v3_3.py": _sha256_file(Path(__file__)),
        }
    )


def _audited_planner_assisted_target_construction(
    scene,
    actor,
    *,
    arm: str,
    variant_id: str,
    callback: Callable[[], Any],
) -> tuple[Any, dict]:
    """Count and receipt every official batch-planner call used to select a grasp."""

    if arm not in ("left", "right"):
        raise ValueError("target-construction arm must be left or right")
    if not hasattr(scene, "_reserve_planner_query") or not hasattr(
        scene, "planner_queries"
    ):
        raise RuntimeError("target construction requires initialized planner audit state")
    contact_point_ids = [int(index) for index, _ in actor.iter_contact_points()]
    if not contact_point_ids:
        raise RuntimeError("planner-assisted target construction has no contact points")
    target_reset = _planner_reset(
        scene,
        planner_seed=PLANNER_SEED,
        variant_id=variant_id,
        arm=arm,
    )
    robot = scene.robot
    method_name = f"{arm}_plan_multi_path"
    original = getattr(robot, method_name)
    had_instance_override = method_name in vars(robot)
    prior_instance_value = vars(robot).get(method_name)
    batch_receipts = []

    def audited_batch(target_list, *args, **kwargs):
        call_index = len(batch_receipts)
        if call_index >= len(contact_point_ids):
            raise RuntimeError("grasp target construction made excess batch-planner calls")
        candidate_poses = [
            np.asarray(pose, dtype=np.float64).reshape(7).tolist()
            for pose in target_list
        ]
        query_id = scene._reserve_planner_query()
        start_qpos = np.asarray(
            getattr(robot, f"{arm}_entity").get_qpos(), dtype=np.float64
        )
        base_receipt = {
            "query_id": int(query_id),
            "arm": arm,
            "query_type": "batched_grasp_target_selection",
            "source": f"Base_Task.choose_grasp_pose->{method_name}",
            "contact_point_id": contact_point_ids[call_index],
            "batch_call_index": call_index,
            "batch_size": len(candidate_poses),
            "ordered_goal_pose_sha256": hash_json(candidate_poses),
            "ordered_goal_poses": candidate_poses,
            "start_qpos_sha256": hash_array(start_qpos),
            "start_step": None,
            "end_step": None,
        }
        try:
            result = original(target_list, *args, **kwargs)
        except BaseException as exc:
            receipt = {
                **base_receipt,
                "candidate_statuses": [],
                "successful_candidate_indices": [],
                "selected_candidate_index_within_batch": None,
                "status": "Exception",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            batch_receipts.append(receipt)
            scene.planner_queries.append(dict(receipt))
            raise
        statuses = (
            [str(value) for value in result.get("status", [])]
            if isinstance(result, Mapping)
            else []
        )
        if len(statuses) != len(candidate_poses):
            receipt = {
                **base_receipt,
                "candidate_statuses": statuses,
                "successful_candidate_indices": [],
                "selected_candidate_index_within_batch": None,
                "status": "InvalidStatusCount",
                "error": {
                    "expected": len(candidate_poses),
                    "actual": len(statuses),
                },
            }
            batch_receipts.append(receipt)
            scene.planner_queries.append(dict(receipt))
            raise RuntimeError("batch grasp planner status count differs from candidate count")
        successful = [index for index, value in enumerate(statuses) if value == "Success"]
        receipt = {
            **base_receipt,
            "candidate_statuses": statuses,
            "successful_candidate_indices": successful,
            "selected_candidate_index_within_batch": (
                successful[0] if successful else None
            ),
            "status": "Success" if successful else "Fail",
        }
        batch_receipts.append(receipt)
        scene.planner_queries.append(dict(receipt))
        return result

    setattr(robot, method_name, audited_batch)
    restoration_error = None
    callback_error = None
    value = None
    try:
        value = callback()
    except BaseException as exc:
        callback_error = exc
    finally:
        try:
            if had_instance_override:
                setattr(robot, method_name, prior_instance_value)
            else:
                delattr(robot, method_name)
        except BaseException as exc:
            restoration_error = f"{type(exc).__name__}: {exc}"
    if restoration_error is not None:
        raise RuntimeError(
            f"target-construction planner wrapper restoration failed: {restoration_error}"
        ) from callback_error
    if callback_error is not None:
        raise callback_error
    if len(batch_receipts) != len(contact_point_ids):
        raise RuntimeError(
            "planner-assisted grasp target construction did not audit every contact point"
        )
    if any(item["batch_size"] != 10 for item in batch_receipts):
        raise RuntimeError("runtime-v3_3 requires frozen ROTATE_NUM=10 batch size")
    callback_pregrasp = None
    callback_matches = []
    if (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and value[0] is not None
    ):
        candidate_value = np.asarray(value[0])
        if candidate_value.size == 7:
            try:
                callback_pregrasp = np.asarray(
                    candidate_value, dtype=np.float64
                ).reshape(7)
            except (TypeError, ValueError):
                callback_pregrasp = None
        if callback_pregrasp is not None:
            for batch in batch_receipts:
                for candidate_index, candidate_pose in enumerate(
                    batch["ordered_goal_poses"]
                ):
                    if np.allclose(
                        callback_pregrasp,
                        np.asarray(candidate_pose, dtype=np.float64),
                        rtol=0.0,
                        atol=1e-9,
                    ):
                        callback_matches.append(
                            {
                                "contact_point_id": batch["contact_point_id"],
                                "batch_call_index": batch["batch_call_index"],
                                "candidate_index_within_batch": candidate_index,
                                "candidate_planner_status": batch[
                                    "candidate_statuses"
                                ][candidate_index],
                            }
                        )
    return value, {
        "schema_version": "cmf_planner_assisted_target_construction_audit_v1",
        "variant_id": variant_id,
        "arm": arm,
        "actor_name": _entity(actor).get_name(),
        "planner_reset_receipt": target_reset,
        "contact_point_ids": contact_point_ids,
        "batch_call_count": len(batch_receipts),
        "internal_pose_candidate_count": sum(
            item["batch_size"] for item in batch_receipts
        ),
        "planner_counting_unit": "one official batch planner API call",
        "batch_receipts": batch_receipts,
        "callback_selected_pregrasp_pose": None
        if callback_pregrasp is None
        else callback_pregrasp.tolist(),
        "callback_selected_pregrasp_pose_sha256": None
        if callback_pregrasp is None
        else hash_array(callback_pregrasp),
        "callback_selected_pose_matches": callback_matches,
        "callback_selected_pose_match_count": len(callback_matches),
        "callback_selected_contact_point_id": callback_matches[0][
            "contact_point_id"
        ]
        if len(callback_matches) == 1
        else None,
        "callback_selected_candidate_index_within_batch": callback_matches[0][
            "candidate_index_within_batch"
        ]
        if len(callback_matches) == 1
        else None,
        "callback_selected_candidate_planner_status": callback_matches[0][
            "candidate_planner_status"
        ]
        if len(callback_matches) == 1
        else None,
        "wrapper_restoration_succeeded": True,
    }


def _prefix_arrays(scene, *, start_action: int, semantic_end_action: int) -> dict:
    rows = scene.trace[start_action + 1 : semantic_end_action + 1]
    if not rows:
        raise ValueError("canonical prefix produced no semantic actions")
    n = len(rows)
    starts = np.arange(n, dtype=np.float64) / 250.0
    return {
        "effective_setpoint_actions": np.asarray(
            [row["effective_setpoint"] for row in rows], dtype=np.float64
        ),
        "requested_commands": np.asarray(
            [row["requested_command"] for row in rows], dtype=np.float64
        ),
        "component_masks": np.asarray(
            [row["component_mask"] for row in rows], dtype=bool
        ),
        "left_gripper_joint_drive_targets": np.asarray(
            [row["left_gripper_joint_drive_target"] for row in rows],
            dtype=np.float64,
        ),
        "right_gripper_joint_drive_targets": np.asarray(
            [row["right_gripper_joint_drive_target"] for row in rows],
            dtype=np.float64,
        ),
        "left_gripper_joint_drive_velocity_targets": np.asarray(
            [row["left_gripper_joint_drive_velocity_target"] for row in rows],
            dtype=np.float64,
        ),
        "right_gripper_joint_drive_velocity_targets": np.asarray(
            [row["right_gripper_joint_drive_velocity_target"] for row in rows],
            dtype=np.float64,
        ),
        "action_interval_start_timestamps": starts,
        "action_interval_end_timestamps": starts + 1.0 / 250.0,
    }


def _settle_prefix_with_replay_operator(scene, steps: int) -> None:
    if not hasattr(scene, "replay_effective_setpoint_step"):
        raise RuntimeError("prefix settling requires the exact replay transition operator")
    last = scene.trace[-1]
    effective = np.asarray(last["effective_setpoint"], dtype=np.float64).copy()
    requested = np.asarray(last["requested_command"], dtype=np.float64).copy()
    mask = np.zeros(26, dtype=bool)
    for _ in range(int(steps)):
        scene.replay_effective_setpoint_step(
            effective,
            requested_command=requested,
            component_mask=mask,
            left_gripper_joint_drive_target=last[
                "left_gripper_joint_drive_target"
            ],
            right_gripper_joint_drive_target=last[
                "right_gripper_joint_drive_target"
            ],
            left_gripper_joint_drive_velocity_target=last[
                "left_gripper_joint_drive_velocity_target"
            ],
            right_gripper_joint_drive_velocity_target=last[
                "right_gripper_joint_drive_velocity_target"
            ],
        )


def _prefix_reference_result(
    scene,
    *,
    start_action: int,
    semantic_end_action: int,
    semantic_end_anchor: Mapping[str, Any],
    acceptance_end_anchor: Mapping[str, Any],
    settling_steps: int,
    extra: Mapping[str, Any] | None = None,
) -> dict:
    result = {
        "arrays": _prefix_arrays(
            scene,
            start_action=start_action,
            semantic_end_action=semantic_end_action,
        ),
        "semantic_prefix_end_anchor": dict(semantic_end_anchor),
        "acceptance_prefix_end_anchor": dict(acceptance_end_anchor),
        "planner_seed": PLANNER_SEED,
        "planner_query_receipts": [dict(item) for item in scene.planner_queries],
        "planner_source_hash": planner_source_hash_v3_3(),
        "settling_step_count": int(settling_steps),
        "settling_policy": {
            "mode": "hold_last_effective_setpoint",
            "semantic": False,
            "reason": "physical prefix-end acceptance window",
            "component_mask_policy": "all_false_no_new_control_command",
            "transition_operator": "replay_effective_setpoint_step_v1_1",
        },
    }
    if extra:
        result.update(dict(extra))
    return result


def _cache_preplanned_suffix_controls(
    scene,
    *,
    program_id: str,
    arm: str,
    targets: Sequence[Mapping[str, Any]],
    raw_actual_qpos: np.ndarray,
    planner_input_qpos: np.ndarray,
    reset: Mapping[str, Any],
    planned: Mapping[str, Any],
    planner_query_count: int,
    extra: Mapping[str, Any] | None = None,
) -> dict:
    """Seal one already-planned chain without issuing another planner query."""

    raw_actual_qpos = np.ascontiguousarray(
        np.asarray(raw_actual_qpos, dtype=np.float64).reshape(-1)
    )
    planner_input_qpos = np.ascontiguousarray(
        np.asarray(planner_input_qpos).reshape(-1)
    )
    start_hash = hash_array(raw_actual_qpos)
    terminal_qpos = np.asarray(planned["terminal_qpos"], dtype=np.float64)
    active_joints = list(getattr(scene.robot, f"{arm}_entity").get_active_joints())
    if len(active_joints) != len(terminal_qpos):
        raise ValueError("suffix terminal qpos does not match active-joint count")
    joint_limits = np.asarray(
        [np.asarray(joint.get_limits(), dtype=np.float64).reshape(-1, 2)[0] for joint in active_joints],
        dtype=np.float64,
    )
    joint_margins = np.minimum(
        terminal_qpos - joint_limits[:, 0], joint_limits[:, 1] - terminal_qpos
    )
    finite_margin = np.isfinite(joint_margins)
    serialized_joint_margins = [
        float(value) if np.isfinite(value) else None for value in joint_margins
    ]
    minimum_joint_margin = (
        float(np.min(joint_margins[finite_margin]))
        if np.any(finite_margin)
        else None
    )
    within_joint_limits = bool(
        np.all(
            (~np.isfinite(joint_limits[:, 0]))
            | (terminal_qpos >= joint_limits[:, 0])
        )
        and np.all(
            (~np.isfinite(joint_limits[:, 1]))
            | (terminal_qpos <= joint_limits[:, 1])
        )
    )
    planner_query_receipts = [
        dict(item)
        for item in getattr(scene, "planner_queries", [])[-int(planner_query_count):]
    ] if int(planner_query_count) else []
    if len(planner_query_receipts) != int(planner_query_count):
        raise RuntimeError("suffix planner query table is shorter than live query delta")
    spec = {
        "schema_version": "cmf_frozen_suffix_execution_spec_v1",
        "program_id": program_id,
        "arm": arm,
        "actual_prefix_end_qpos_sha256": start_hash,
        "planner_input_prefix_end_qpos_sha256": hash_array(
            planner_input_qpos
        ),
        "actual_prefix_end_qpos_dtype": str(raw_actual_qpos.dtype),
        "planner_input_prefix_end_qpos_dtype": str(planner_input_qpos.dtype),
        "targets": [
            {
                "segment_id": item["segment_id"],
                "pose": np.asarray(item["pose"], dtype=np.float64).tolist(),
            }
            for item in targets
        ],
        "segment_receipts": planned["segment_receipts"],
        "planner_reset_receipt": reset,
        "planner_query_receipts": planner_query_receipts,
        "terminal_qpos": terminal_qpos.tolist(),
        "terminal_qpos_sha256": hash_array(terminal_qpos),
        "terminal_joint_limit_margin_rad": serialized_joint_margins,
        "minimum_terminal_joint_limit_margin_rad": minimum_joint_margin,
        "terminal_qpos_within_joint_limits": within_joint_limits,
    }
    if extra:
        spec.update(dict(extra))
    cache_key = hash_json(spec)
    spec["control_cache_key"] = cache_key
    cache = getattr(scene, SUFFIX_CACHE_ATTRIBUTE, None)
    if cache is None:
        cache = {}
        setattr(scene, SUFFIX_CACHE_ATTRIBUTE, cache)
    if cache_key in cache:
        raise RuntimeError("suffix control cache key collision")
    cache[cache_key] = planned["controls"]
    return {
        "planner_solvable": bool(planned["pass"]),
        "planner_query_count": int(planner_query_count),
        "failure_type": None if planned["pass"] else "chained_suffix_planner_failure",
        "evidence": {
            "planner_reset_receipt": reset,
            "planner_query_receipts": planner_query_receipts,
            "segment_receipts": planned["segment_receipts"],
            "terminal_qpos": terminal_qpos.tolist(),
            "terminal_qpos_sha256": hash_array(terminal_qpos),
            "terminal_joint_limit_margin_rad": serialized_joint_margins,
            "minimum_terminal_joint_limit_margin_rad": minimum_joint_margin,
            "terminal_qpos_within_joint_limits": within_joint_limits,
            "planner_collision_check_source": "official CuRobo planner success/failure per frozen segment",
            "quantitative_collision_clearance_available": False,
            "preflight_and_execution_share_control_cache": True,
        },
        "actual_prefix_end_qpos_sha256": start_hash,
        "execution_spec": spec if planned["pass"] else None,
        "_execution_controls": planned["controls"] if planned["pass"] else None,
        "_actual_prefix_end_qpos": raw_actual_qpos if planned["pass"] else None,
    }


def _cache_suffix_controls(
    scene,
    *,
    program_id: str,
    arm: str,
    targets: Sequence[Mapping[str, Any]],
    query_limit: int,
    extra: Mapping[str, Any] | None = None,
) -> dict:
    raw_actual_qpos = np.ascontiguousarray(
        np.asarray(
            getattr(scene.robot, f"{arm}_entity").get_qpos(),
            dtype=np.float64,
        ).reshape(-1)
    )
    planner_input_qpos = planner_array(
        raw_actual_qpos,
        label=f"{program_id} planner-input prefix-end qpos",
    ).reshape(-1)
    reset = _planner_reset(
        scene,
        planner_seed=PLANNER_SEED,
        variant_id=f"v3_3_suffix:{program_id}",
        arm=arm,
    )
    before = int(getattr(scene, "planner_query_count", 0))
    planned = _plan_chain(scene, targets, query_limit=query_limit, arm=arm)
    planner_query_count = int(getattr(scene, "planner_query_count", 0)) - before
    if planner_query_count != len(planned["segment_receipts"]):
        raise RuntimeError("suffix live planner delta differs from segment receipts")
    return _cache_preplanned_suffix_controls(
        scene,
        program_id=program_id,
        arm=arm,
        targets=targets,
        raw_actual_qpos=raw_actual_qpos,
        planner_input_qpos=planner_input_qpos,
        reset=reset,
        planned=planned,
        planner_query_count=planner_query_count,
        extra=extra,
    )


def _cached_controls(scene, spec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    cache = getattr(scene, SUFFIX_CACHE_ATTRIBUTE, {})
    key = spec.get("control_cache_key")
    controls = cache.get(key)
    if not isinstance(controls, list) or len(controls) != len(spec.get("targets", [])):
        raise RuntimeError("frozen suffix controls are missing or inconsistent")
    return controls


def install_frozen_suffix_controls(
    scene, spec: Mapping[str, Any], controls: Sequence[Mapping[str, Any]]
) -> None:
    key = spec.get("control_cache_key")
    if not isinstance(key, str) or not key:
        raise ValueError("frozen suffix spec lacks a cache key")
    cache = getattr(scene, SUFFIX_CACHE_ATTRIBUTE, None)
    if cache is None:
        cache = {}
        setattr(scene, SUFFIX_CACHE_ATTRIBUTE, cache)
    if key in cache:
        raise RuntimeError("frozen suffix controls already installed")
    query_table = []
    seen_queries = set()
    for control in controls:
        query = control.get("_cmf_planner_query") if isinstance(control, Mapping) else None
        if not isinstance(query, Mapping):
            raise ValueError("frozen suffix control lacks planner-query provenance")
        item = dict(query)
        query_key = (item.get("query_id"), item.get("arm"))
        if (
            not isinstance(query_key[0], int)
            or query_key[0] <= 0
            or query_key[1] not in ("left", "right")
            or query_key in seen_queries
        ):
            raise ValueError("frozen suffix planner-query provenance is invalid")
        seen_queries.add(query_key)
        item["start_step"] = None
        item["end_step"] = None
        item["replayed_from_frozen_suffix_artifact"] = True
        query_table.append(item)
    if getattr(scene, "planner_queries", None):
        raise RuntimeError("fresh suffix execution scene has a nonempty planner query table")
    scene.planner_queries = query_table
    scene._cmf_frozen_planner_query_table_installed = True
    scene._cmf_previous_suffix_actual_end_qpos = None
    cache[key] = list(controls)


def _execute_cached_segment(
    scene,
    spec: Mapping[str, Any],
    controls: Sequence[Mapping[str, Any]],
    index: int,
) -> dict:
    target = spec["targets"][index]
    planned_receipt = spec["segment_receipts"][index]
    arm = spec["arm"]
    start_qpos = np.asarray(
        getattr(scene.robot, f"{arm}_entity").get_qpos(), dtype=np.float64
    )
    planned_start_qpos = np.asarray(
        planned_receipt["start_qpos"], dtype=np.float64
    )
    if start_qpos.shape != planned_start_qpos.shape:
        raise RuntimeError("frozen suffix actual/planned start qpos shapes differ")
    active_joints = list(
        getattr(scene.robot, f"{arm}_entity").get_active_joints()
    )
    index_by_name = {
        joint.get_name(): joint_index
        for joint_index, joint in enumerate(active_joints)
    }
    arm_joint_names = [
        joint.get_name() for joint in getattr(scene.robot, f"{arm}_arm_joints")
    ]
    if any(name not in index_by_name for name in arm_joint_names):
        raise RuntimeError("selected arm joints are absent from execution articulation")
    arm_indices = np.asarray(
        [index_by_name[name] for name in arm_joint_names], dtype=np.int64
    )
    start_arm_qpos = start_qpos[arm_indices]
    planned_start_arm_qpos = planned_start_qpos[arm_indices]
    start_qpos_max_error = float(
        np.max(np.abs(start_arm_qpos - planned_start_arm_qpos))
    )
    previous_actual = getattr(
        scene, "_cmf_previous_suffix_actual_end_qpos", None
    )
    if index == 0:
        if start_qpos_max_error > 1e-5:
            raise RuntimeError(
                f"frozen suffix segment {target['segment_id']} initial qpos differs from replay-end preflight"
            )
        actual_chain_continuity_pass = True
    else:
        if previous_actual is None:
            raise RuntimeError("frozen suffix actual chain state is missing")
        previous_actual = np.asarray(previous_actual, dtype=np.float64)
        if previous_actual.shape != start_qpos.shape:
            raise RuntimeError("frozen suffix actual qpos chain shape changed")
        inter_segment_actual_qpos_delta_rad = float(
            np.max(
                np.abs(
                    start_qpos[arm_indices] - previous_actual[arm_indices]
                )
            )
        )
        # Gripper/hold actions may legitimately occur between planned arm
        # segments.  Their continuous 250 Hz states remain in the raw trace;
        # do not require the later segment to start at the theoretical
        # preflight terminal or pretend those intervening dynamics did not
        # happen.
        actual_chain_continuity_pass = True
    _execute_control(
        scene,
        controls[index],
        target["segment_id"],
        arm=arm,
    )
    end_qpos = np.asarray(
        getattr(scene.robot, f"{arm}_entity").get_qpos(), dtype=np.float64
    )
    planned_end_qpos = np.asarray(planned_receipt["end_qpos"], dtype=np.float64)
    if end_qpos.shape != planned_end_qpos.shape:
        raise RuntimeError("frozen suffix actual/planned terminal qpos shapes differ")
    end_arm_qpos = end_qpos[arm_indices]
    planned_end_arm_qpos = planned_end_qpos[arm_indices]
    terminal_qpos_max_error = float(
        np.max(np.abs(end_arm_qpos - planned_end_arm_qpos))
    )
    terminal_audit_tolerance_rad = 0.10
    scene._cmf_previous_suffix_actual_end_qpos = end_qpos.copy()
    realized = _arm_eef_pose(scene, arm)
    goal = np.asarray(target["pose"], dtype=np.float64)
    return {
        "segment_id": target["segment_id"],
        "start_qpos_sha256": hash_array(start_qpos),
        "actual_start_arm_qpos": start_arm_qpos.tolist(),
        "actual_start_arm_qpos_sha256": hash_array(start_arm_qpos),
        "planned_start_qpos_sha256": planned_receipt["start_qpos_sha256"],
        "planned_start_arm_qpos": planned_start_arm_qpos.tolist(),
        "planned_start_arm_qpos_sha256": hash_array(planned_start_arm_qpos),
        "start_qpos_max_error_rad": start_qpos_max_error,
        "initial_start_qpos_tolerance_rad": 1e-5,
        "actual_chain_continuity_pass": actual_chain_continuity_pass,
        "inter_segment_actual_qpos_delta_rad": 0.0
        if index == 0
        else inter_segment_actual_qpos_delta_rad,
        "intervening_control_trace_is_authoritative": True,
        "actual_terminal_qpos_sha256": hash_array(end_qpos),
        "actual_terminal_arm_qpos": end_arm_qpos.tolist(),
        "actual_terminal_arm_qpos_sha256": hash_array(end_arm_qpos),
        "planned_terminal_qpos_sha256": planned_receipt["end_qpos_sha256"],
        "planned_terminal_arm_qpos": planned_end_arm_qpos.tolist(),
        "planned_terminal_arm_qpos_sha256": hash_array(planned_end_arm_qpos),
        "terminal_qpos_max_error_rad": terminal_qpos_max_error,
        "terminal_qpos_audit_tolerance_rad": terminal_audit_tolerance_rad,
        "terminal_qpos_within_provisional_audit_tolerance": terminal_qpos_max_error
        <= terminal_audit_tolerance_rad,
        "terminal_qpos_tolerance_is_semantic_verifier": False,
        "tracking_error_scope": "selected executing arm joints only; gripper/other joints remain separate realized raw streams",
        "goal_pose": goal.tolist(),
        "planner_status": controls[index].get("status"),
        "execution_status": "executed",
        "tracking_position_error_m": float(np.linalg.norm(realized[:3] - goal[:3])),
        "tracking_orientation_error_rad": quaternion_orientation_error(
            realized[3:], goal[3:]
        ),
    }


def _realized_event_metrics(rows, *, axis: str) -> dict:
    if not rows:
        raise ValueError("realized F3 event has no trace rows")
    main_axis = 0 if axis == "H" else 2
    eef = np.asarray([row["eef"][:3] for row in rows], dtype=np.float64)
    actor = np.asarray(
        [row["actor_pose"][:3] for row in rows], dtype=np.float64
    )
    eef_metrics = closed_loop_event_metrics(eef, eef[0], main_axis)
    actor_metrics = closed_loop_event_metrics(actor, actor[0], main_axis)
    contacts = [bool(row["selected_gripper_contact"]) for row in rows]
    breaks = sum(
        previous and not current
        for previous, current in zip(contacts, contacts[1:])
    )
    return {
        **{f"eef_{key}": value for key, value in eef_metrics.items()},
        **{f"bottle_{key}": value for key, value in actor_metrics.items()},
        "bottle_orientation_drift": max(
            quaternion_angular_error(
                rows[0]["actor_pose"][3:], row["actor_pose"][3:]
            )
            for row in rows
        ),
        "selected_gripper_contact_fraction": float(np.mean(contacts)),
        "contact_break_count": int(breaks),
        "event_duration": len(rows) / 250.0,
    }


def _time_dilated_closed_loop_event_targets(
    center: np.ndarray,
    *,
    axis: str,
    amplitude_m: float,
    segment_prefix: str,
) -> list[dict]:
    if axis not in ("V", "H") or not np.isfinite(amplitude_m) or amplitude_m <= 0:
        raise ValueError("F3 closed-loop event specification is invalid")
    center = np.asarray(center, dtype=np.float64).reshape(7)
    dimension = 2 if axis == "V" else 0

    def offset(fraction: float) -> np.ndarray:
        pose = center.copy()
        pose[dimension] += float(fraction) * float(amplitude_m)
        return pose

    values = (
        ("positive_half", 0.5),
        ("positive", 1.0),
        ("center_after_positive", 0.0),
        ("negative_half", -0.5),
        ("negative", -1.0),
        ("return_half", -0.5),
        ("return", 0.0),
    )
    return [
        {
            "segment_id": f"{segment_prefix}_{label}",
            "pose": offset(fraction),
        }
        for label, fraction in values
    ]


def _f2_dynamic_post_settle_checks(
    *,
    planned_can_xyz,
    can_pose,
    table_support_height_m: float,
    pose_linear_speeds,
    pose_angular_speeds,
    table_contact_window,
    sleep_state,
    required: bool,
) -> dict:
    if not required:
        return {}
    planned = np.asarray(planned_can_xyz, dtype=np.float64).reshape(3)
    pose = np.asarray(can_pose, dtype=np.float64).reshape(7)
    linear = [float(value) for value in pose_linear_speeds]
    angular = [float(value) for value in pose_angular_speeds]
    contacts = [bool(value) for value in table_contact_window]
    required_frames = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
    return {
        "post_settle_xy_within_5mm_of_spawn": float(
            np.linalg.norm(pose[:2] - planned[:2])
        )
        <= 0.005,
        "post_settle_z_drop_nonnegative_bounded_10cm": 0.0
        <= float(planned[2] - pose[2])
        <= 0.10,
        "post_settle_upright_orientation": quaternion_orientation_error(
            pose[3:], [0.5, 0.5, 0.5, 0.5]
        )
        <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
        "post_settle_table_support_height_band": abs(
            float(pose[2]) - float(table_support_height_m)
        )
        <= 0.02,
        "post_settle_sleeping": sleep_state is True,
        "pose_velocity_stable_window_length": len(linear) == required_frames
        and len(angular) == required_frames,
        "pose_derived_linear_stationary": bool(linear)
        and max(linear)
        <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
        "pose_derived_angular_stationary": bool(angular)
        and max(angular)
        <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        "continuous_table_contact": bool(contacts) and all(contacts),
    }


def _prefix_physical_acceptance(
    scene,
    *,
    roles: Sequence[str],
    require_selected_contact: bool,
    expected_contact_actor_name: str | None = None,
    extra_checks: Mapping[str, bool] | None = None,
) -> dict:
    required = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
    rows = scene.trace[-required:]
    checks: dict[str, bool] = {"stable_window_length": len(rows) == required}
    checks["eef_linear_stationary"] = bool(rows) and max(
        float(np.linalg.norm(row["eef_linear_velocity"])) for row in rows
    ) <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"]
    checks["eef_angular_stationary"] = bool(rows) and max(
        float(np.linalg.norm(row["eef_angular_velocity"])) for row in rows
    ) <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"]
    role_metrics = {}
    for role in roles:
        if any(role not in row.get("role_actor_linear_velocities", {}) for row in rows):
            checks[f"{role}_velocity_stream"] = False
            continue
        linear = [
            float(np.linalg.norm(row["role_actor_linear_velocities"][role]))
            for row in rows
        ]
        angular = [
            float(np.linalg.norm(row["role_actor_angular_velocities"][role]))
            for row in rows
        ]
        role_metrics[role] = {
            "maximum_linear_speed_mps": max(linear),
            "maximum_angular_speed_rps": max(angular),
        }
        checks[f"{role}_linear_stationary"] = max(linear) <= float(
            PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
        )
        checks[f"{role}_angular_stationary"] = max(angular) <= float(
            PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"]
        )
    if require_selected_contact:
        contact_fraction = float(
            np.mean([bool(row["selected_gripper_contact"]) for row in rows])
        ) if rows else 0.0
        checks["selected_gripper_contact"] = contact_fraction >= float(
            PROVISIONAL_RUNTIME_THRESHOLDS["motion_min_contact_fraction"]
        )
        checks["selected_contact_actor_identity"] = isinstance(
            expected_contact_actor_name, str
        ) and all(
            str(row["selected_contact_actor_name"])
            == expected_contact_actor_name
            for row in rows
        )
    else:
        contact_fraction = None
    if extra_checks:
        checks.update({str(key): bool(value) for key, value in extra_checks.items()})
    return {
        "schema_version": "cmf_prefix_physical_acceptance_v1",
        "pass": bool(checks) and all(checks.values()),
        "checks": checks,
        "stable_window_frames": len(rows),
        "role_metrics": role_metrics,
        "selected_gripper_contact_fraction": contact_fraction,
        "thresholds": {
            "stable_linear_speed_mps": PROVISIONAL_RUNTIME_THRESHOLDS[
                "stable_linear_speed_mps"
            ],
            "stationary_angular_speed_rps": PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "selected_contact_fraction": PROVISIONAL_RUNTIME_THRESHOLDS[
                "motion_min_contact_fraction"
            ],
        },
    }


def _first_stable_slot_completion(
    scene,
    *,
    role: str,
    actor,
    slot,
    start_row: int,
    required_frames: int,
) -> dict:
    actor_name = _entity(actor).get_name()
    slot_pose = _pose(slot)
    streak = 0
    first_index = None
    frame_evidence = []
    for row_index in range(int(start_row), len(scene.trace)):
        row = scene.trace[row_index]
        role_pose = row.get("role_actor_poses", {}).get(role)
        role_velocity = row.get("role_actor_linear_velocities", {}).get(role)
        role_angular_velocity = row.get("role_actor_angular_velocities", {}).get(role)
        if role_pose is None or role_velocity is None or role_angular_velocity is None:
            raise ValueError(f"F4 completion trace lacks role stream {role}")
        footprint = footprint_inside_local_region(
            role_pose,
            BLOCK_HALF_EXTENTS,
            slot_pose,
            [-0.035, -0.035, -0.01],
            [0.035, 0.035, 0.03],
            (0, 1),
        )["pass_support_footprint"]
        linear_stable = float(np.linalg.norm(role_velocity)) <= float(
            PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
        )
        angular_stable = float(np.linalg.norm(role_angular_velocity)) <= float(
            PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"]
        )
        support = any(
            actor_name in (item["body_a"], item["body_b"])
            and any(
                "table" in str(body).lower()
                for body in (item["body_a"], item["body_b"])
                if body != actor_name
            )
            for item in row["contact_pairs"]
        )
        active = bool(footprint and linear_stable and angular_stable and support)
        streak = streak + 1 if active else 0
        frame_evidence.append(
            {
                "trace_row": row_index,
                "footprint": bool(footprint),
                "linear_stable": bool(linear_stable),
                "angular_stable": bool(angular_stable),
                "table_support": bool(support),
            }
        )
        if streak >= int(required_frames):
            first_index = row_index - int(required_frames) + 1
            break
    return {
        "pass": first_index is not None,
        "completion_trace_row": first_index,
        "required_stable_frames": int(required_frames),
        "evaluated_frame_count": len(frame_evidence),
        "first_window_evidence": frame_evidence[-int(required_frames):]
        if first_index is not None
        else frame_evidence[-min(len(frame_evidence), int(required_frames)):],
        "definition": "first post-release frame of a consecutive footprint+linear-stable+angular-stable+table-support window",
    }


def _replay_boundary_transform(scene, replay, name):
    boundary = int(replay["reference_event_boundaries"][name])
    row_index = int(replay["trace_replay_start_row"] + boundary - 1)
    row = scene.trace[row_index]
    return relative_pose(row["eef"], row["actor_pose"])


class FamilyControllerV3_3:
    family = None
    arm = None

    def __init__(self):
        self.legacy = get_family_runner(self.family)

    def audit_task_physical_feasibility(self, scene, program):
        return self.legacy.audit_task_physical_feasibility(scene, program)

    def canonical_prefix_contract(self, programs):
        raise NotImplementedError

    def initialize_prefix_replay_trace(self, scene):
        raise NotImplementedError

    def plan_and_execute_canonical_prefix(
        self, scene, prefix_contract, *, capture_anchor
    ):
        raise NotImplementedError

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        raise NotImplementedError

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization_spec
    ):
        raise NotImplementedError

    def validate_family_suffix_gate(self, receipts):
        values = [dict(item) for item in receipts]
        checks = {
            "three_programs": len(values) == 3,
            "three_planner_solvable": len(values) == 3
            and all(item.get("planner_solvable") is True for item in values),
            "actual_prefix_end_qpos_recorded": len(values) == 3
            and all(
                isinstance(item.get("actual_prefix_end_qpos_sha256"), str)
                for item in values
            ),
        }
        return {
            "schema_version": "cmf_family_suffix_gate_v1",
            "family": self.family,
            "checks": checks,
            "pass": all(checks.values()),
        }

    def validate_replayed_prefix_physical(self, scene, replay):
        raise NotImplementedError


class F1ControllerV3_3(FamilyControllerV3_3):
    family = "F1"
    arm = "left"

    def validate_replayed_prefix_physical(self, scene, replay):
        return _prefix_physical_acceptance(
            scene,
            roles=("red", "green", "blue"),
            require_selected_contact=False,
            extra_checks={
                "prefix_end_equivalent": replay["prefix_end_equivalent"]
            },
        )

    def validate_family_suffix_gate(self, receipts):
        base = super().validate_family_suffix_gate(receipts)
        values = [dict(item) for item in receipts]
        roles = {
            item["program_id"].split("-", 1)[1].lower(): item
            for item in values
            if isinstance(item.get("program_id"), str)
        }
        comparative = {}
        for role in ("red", "green", "blue"):
            item = roles.get(role, {})
            spec = item.get("execution_spec", {})
            if not isinstance(spec, Mapping):
                spec = {}
            evidence = item.get("evidence", {})
            if not isinstance(evidence, Mapping):
                evidence = {}
            comparative[role] = {
                "planner_solvable": item.get("planner_solvable"),
                "terminal_qpos": spec.get(
                    "terminal_qpos", evidence.get("terminal_qpos")
                ),
                "terminal_qpos_sha256": spec.get(
                    "terminal_qpos_sha256", evidence.get("terminal_qpos_sha256")
                ),
                "terminal_joint_limit_margin_rad": spec.get(
                    "terminal_joint_limit_margin_rad",
                    evidence.get("terminal_joint_limit_margin_rad"),
                ),
                "minimum_terminal_joint_limit_margin_rad": spec.get(
                    "minimum_terminal_joint_limit_margin_rad",
                    evidence.get("minimum_terminal_joint_limit_margin_rad"),
                ),
                "terminal_qpos_within_joint_limits": spec.get(
                    "terminal_qpos_within_joint_limits",
                    evidence.get("terminal_qpos_within_joint_limits"),
                ),
                "planner_collision_check_source": evidence.get(
                    "planner_collision_check_source"
                ),
                "quantitative_collision_clearance_available": evidence.get(
                    "quantitative_collision_clearance_available"
                ),
                "comparative_reachability": spec.get(
                    "comparative_reachability",
                    evidence.get("comparative_reachability"),
                ),
            }
        checks = {
            **base["checks"],
            "all_roles_present": set(roles) == {"red", "green", "blue"},
            "terminal_qpos_values_available": all(
                isinstance(comparative[role]["terminal_qpos"], list)
                and comparative[role]["terminal_qpos"]
                for role in comparative
            ),
            "joint_limit_margin_available": all(
                isinstance(
                    comparative[role]["minimum_terminal_joint_limit_margin_rad"],
                    (int, float),
                )
                for role in comparative
            ),
            "all_terminal_qpos_within_limits": all(
                comparative[role]["terminal_qpos_within_joint_limits"] is True
                for role in comparative
            ),
            "official_planner_collision_pass": all(
                comparative[role]["planner_solvable"] is True
                and isinstance(
                    comparative[role]["planner_collision_check_source"], str
                )
                for role in comparative
            ),
            "non_target_waypoint_clearance_positive": all(
                isinstance(
                    comparative[role].get("comparative_reachability"), Mapping
                )
                and float(
                    comparative[role]["comparative_reachability"].get(
                        "minimum_non_target_waypoint_clearance_m", -1.0
                    )
                )
                > 0.0
                for role in comparative
            ),
        }
        return {
            "schema_version": "cmf_f1_three_object_planner_comparative_gate_v1",
            "family": "F1",
            "uniform_rule": "official planner-assisted top-down grasp + common 4cm+4cm lift + frozen cluster-center carry hub + common container target construction",
            "role_order": ["red", "green", "blue"],
            "comparative": comparative,
            "checks": checks,
            "pass": all(checks.values()),
            "quantitative_collision_clearance_status": "non-target carried-block waypoint AABB clearance recorded; full robot-path collision status from official CuRobo per segment",
        }

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f1_cluster_neutral_v3_3",
            "family": "F1",
            "arm": "left",
            "ops": ["open_gripper", "move_cluster_neutral"],
            "target_role_read": False,
            "settling_excluded_from_semantic_P": True,
        }

    def initialize_prefix_replay_trace(self, scene):
        scene.initialize_trace(scene.red, "left", role_actors=scene.role_actors)

    def plan_and_execute_canonical_prefix(
        self, scene, prefix_contract, *, capture_anchor
    ):
        self.initialize_prefix_replay_trace(scene)
        scene.planner_query_limit = 16
        _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id="f1_canonical_prefix_once",
            arm="left",
        )
        start = len(scene.trace) - 1
        _must_action(
            scene,
            scene.open_gripper(_arm_tag_left(), pos=1.0),
            "f1_prefix_open",
        )
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        neutral = np.concatenate(([-0.11, 0.02, 0.95], rest[3:]))
        _move_left(scene, neutral, "f1_cluster_neutral")
        semantic_end = len(scene.trace) - 1
        semantic_anchor = capture_anchor(scene)
        settling = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
        _settle_prefix_with_replay_operator(scene, settling)
        acceptance_anchor = capture_anchor(scene)
        prefix_acceptance = _prefix_physical_acceptance(
            scene,
            roles=("red", "green", "blue"),
            require_selected_contact=False,
        )
        return _prefix_reference_result(
            scene,
            start_action=start,
            semantic_end_action=semantic_end,
            semantic_end_anchor=semantic_anchor,
            acceptance_end_anchor=acceptance_anchor,
            settling_steps=settling,
            extra={"prefix_physical_acceptance": prefix_acceptance},
        )

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        built, target_construction_audit = (
            _audited_planner_assisted_target_construction(
                scene,
                getattr(scene, program["target_role"]),
                arm="left",
                variant_id=f"f1_target_construction:{program['program_id']}",
                callback=lambda: self.legacy.build_targets(
                    scene,
                    program,
                    {"variant_id": "v3_3_uniform_8cm_lift"},
                ),
            )
        )
        legacy_targets, extra = built
        all_targets, carry_hub_audit = build_uniform_carry_hub_targets(
            legacy_targets
        )
        targets = all_targets[1:]
        role = program["target_role"]
        actor_pose = _pose(getattr(scene, role))
        grasp_pose = np.asarray(all_targets[2]["pose"], dtype=np.float64)
        eef_to_actor = relative_pose(grasp_pose, actor_pose)
        carried_segment_ids = {
            "target_lift_mid",
            "target_lift",
            "carry_hub_low",
            "carry_hub_high",
            "safe_horizontal",
            "preplace",
            "release",
        }
        carried_actor_poses = {
            item["segment_id"]: compose_pose(item["pose"], eef_to_actor)
            for item in all_targets
            if item["segment_id"] in carried_segment_ids
        }
        non_targets = {
            name: _pose(getattr(scene, name))
            for name in ("red", "green", "blue")
            if name != role
        }
        waypoint_clearances = {}
        for segment_id, carried_pose in carried_actor_poses.items():
            per_object = {}
            for name, other_pose in non_targets.items():
                axis_gap = (
                    np.abs(carried_pose[:3] - other_pose[:3])
                    - 2.0 * BLOCK_HALF_EXTENTS
                )
                per_object[name] = float(
                    np.linalg.norm(np.maximum(axis_gap, 0.0))
                )
            waypoint_clearances[segment_id] = per_object
        minimum_waypoint_clearance = min(
            value
            for item in waypoint_clearances.values()
            for value in item.values()
        )
        comparative = {
            "target_role": role,
            "object_pose": actor_pose.tolist(),
            "pregrasp_pose": np.asarray(all_targets[1]["pose"], dtype=np.float64).tolist(),
            "grasp_pose": grasp_pose.tolist(),
            "lift_mid_pose": np.asarray(all_targets[3]["pose"], dtype=np.float64).tolist(),
            "lift_pose": np.asarray(all_targets[4]["pose"], dtype=np.float64).tolist(),
            "non_target_waypoint_clearance_m": waypoint_clearances,
            "minimum_non_target_waypoint_clearance_m": minimum_waypoint_clearance,
            "clearance_scope": "carried block AABB at frozen transport waypoints; official CuRobo status covers full robot path collision",
        }
        result = _cache_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="left",
            targets=targets,
            query_limit=16,
            extra={
                **extra,
                "target_role": role,
                "comparative_reachability": comparative,
                "target_construction_planner_audit": target_construction_audit,
                "carry_hub_audit": carry_hub_audit,
            },
        )
        result["evidence"]["target_construction_planner_audit"] = (
            target_construction_audit
        )
        result["evidence"]["comparative_reachability"] = comparative
        result["evidence"]["carry_hub_audit"] = carry_hub_audit
        return result

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization_spec
    ):
        role = program["target_role"]
        actor = getattr(scene, role)
        scene.set_trace_contact_actor(actor)
        non_targets = {
            name: getattr(scene, name)
            for name in ("red", "green", "blue")
            if name != role
        }
        baseline = _position_map(non_targets)
        stages = {"prefix_boundary": _position_map(non_targets)}
        controls = _cached_controls(scene, spec)
        index_by_segment = {
            item["segment_id"]: index for index, item in enumerate(spec["targets"])
        }
        expected = tuple(item["segment_id"] for item in spec["targets"])
        if expected != F1_REVISION2_SEGMENT_ORDER[1:]:
            raise RuntimeError("F1 frozen revision-2 suffix segment order changed")
        execution_receipts = []
        execution_receipts.append(_execute_cached_segment(scene, spec, controls, 0))
        execution_receipts.append(_execute_cached_segment(scene, spec, controls, 1))
        _must_action(
            scene,
            scene.close_gripper(_arm_tag_left(), pos=0.0),
            f"{role}_close_gripper",
        )
        stages["after_grasp"] = _position_map(non_targets)
        for segment_id in (
            "target_lift_mid",
            "target_lift",
            "carry_hub_low",
            "carry_hub_high",
            "safe_horizontal",
            "preplace",
            "release",
        ):
            execution_receipts.append(
                _execute_cached_segment(
                    scene, spec, controls, index_by_segment[segment_id]
                )
            )
        stages["after_transport"] = _position_map(non_targets)
        _must_action(
            scene, scene.open_gripper(_arm_tag_left(), pos=1.0), f"{role}_release"
        )
        _wait_and_record(scene, 75)
        stages["after_release"] = _position_map(non_targets)
        for segment_id in ("retreat", "rest"):
            execution_receipts.append(
                _execute_cached_segment(
                    scene, spec, controls, index_by_segment[segment_id]
                )
            )
        _wait_and_record(scene, 75)
        stages["after_rest"] = _position_map(non_targets)
        inside = verify_true_cavity_obb(
            _pose(actor),
            BLOCK_HALF_EXTENTS,
            _pose(scene.box),
            PLASTICBOX_BASE3_CAVITY,
        )
        non_target = verify_staged_non_target_displacement(
            baseline,
            stages,
            PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"],
        )
        stable_rows, speeds, contacts = _stable_and_support(scene, actor, scene.box)
        angular_speeds = [
            float(
                np.linalg.norm(
                    row["role_actor_angular_velocities"][role]
                )
            )
            for row in stable_rows
        ]
        rest = np.asarray(spec["targets"][-1]["pose"], dtype=np.float64)
        realized = _arm_eef_pose(scene, "left")
        rest_position_error = float(np.linalg.norm(realized[:3] - rest[:3]))
        rest_orientation_error = quaternion_orientation_error(
            realized[3:], rest[3:]
        )
        eef_linear_speed = float(
            np.linalg.norm(scene.trace[-1]["eef_linear_velocity"])
        )
        eef_angular_speed = float(
            np.linalg.norm(scene.trace[-1]["eef_angular_velocity"])
        )
        checks = {
            "true_inside": inside["pass_true_cavity_obb"],
            "non_target": non_target["pass"],
            "stable": bool(speeds)
            and max(speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
            and bool(angular_speeds)
            and max(angular_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "continuous_box_contact": bool(contacts) and all(contacts),
            "gripper_open": _arm_gripper_open(scene, "left"),
            "rest_position": rest_position_error
            <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            "rest_orientation": rest_orientation_error
            <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": eef_linear_speed
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": eef_angular_speed
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        semantic = {
            "pass": all(checks.values()),
            "checks": checks,
            "inside": inside,
            "non_target": non_target,
            "suffix_segment_execution_receipts": execution_receipts,
            "preflight_rollout_same_control_cache": True,
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=replay,
            semantic_verifier=semantic,
            extra={
                "audit_role_mapping": {
                    "target_role": role,
                    "target_role_pose_field": f"role_object_pose__{role}",
                }
            },
        )


class F2ControllerV3_3(FamilyControllerV3_3):
    family = "F2"
    arm = "left"

    def validate_replayed_prefix_physical(self, scene, replay):
        post_close = _replay_boundary_transform(
            scene, replay, "post_close"
        )
        current = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.can)
        )
        translation_drift = float(np.linalg.norm(current[:3] - post_close[:3]))
        orientation_drift = quaternion_angular_error(
            current[3:], post_close[3:]
        )
        result = _prefix_physical_acceptance(
            scene,
            roles=("main_can",),
            require_selected_contact=True,
            expected_contact_actor_name=_entity(scene.can).get_name(),
            extra_checks={
                "prefix_end_equivalent": replay["prefix_end_equivalent"],
                "grasp_transform_translation_stable": translation_drift <= 0.005,
                "grasp_transform_orientation_stable": orientation_drift <= 0.05,
            },
        )
        result["grasp_transform_translation_drift_m"] = translation_drift
        result["grasp_transform_orientation_drift_rad"] = orientation_drift
        return result

    def _require_layout_v2(self, scene, *, require_dynamic_stability=False):
        planned = getattr(scene, "_cmf_planned_root_slot_spec", {})
        layout = planned.get("scene_layout")
        if not isinstance(layout, Mapping):
            raise ValueError("F2 v3_3 requires an explicit frozen scene_layout")
        expected = {
            key: F2_LAYOUT_V2[key]
            for key in (
                "layout_version",
                "can_xyz",
                "box_xyz",
                "scale_xyz",
                "stand_xyz",
                "stand_q_wxyz",
            )
        }
        if hash_json(layout) != hash_json(expected):
            raise ValueError("F2 planned scene layout differs from frozen layout v2")
        realized = {
            "box_xyz": _pose(scene.box)[:3],
            "scale_xyz": _pose(scene.scale)[:3],
            "stand_xyz": _pose(scene.stand)[:3],
        }
        for key, value in realized.items():
            if not np.allclose(
                value, np.asarray(expected[key], dtype=np.float64), rtol=0.0, atol=1e-6
            ):
                raise ValueError(f"F2 realized {key} differs from frozen layout v2")
        if quaternion_orientation_error(
            _pose(scene.stand)[3:], expected["stand_q_wxyz"]
        ) > 1e-6:
            raise ValueError("F2 realized stand orientation differs from layout v2")
        can_pose = _pose(scene.can)
        pose_linear_speeds = []
        pose_angular_speeds = []
        table_contact_window = []
        can_name = _entity(scene.can).get_name()
        if require_dynamic_stability:
            timestep = float(scene.scene.get_timestep())
            if not np.isclose(timestep, 1.0 / 250.0, rtol=0.0, atol=1e-9):
                raise ValueError(
                    "F2 post-settle dynamic pose contract requires 250 Hz timestep"
                )
            previous_pose = can_pose.copy()
            for _ in range(
                int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
            ):
                scene.scene.step()
                current_pose = _pose(scene.can)
                pose_linear_speeds.append(
                    float(
                        np.linalg.norm(
                            (current_pose[:3] - previous_pose[:3]) / timestep
                        )
                    )
                )
                pose_angular_speeds.append(
                    float(
                        np.linalg.norm(
                            quaternion_angular_velocity(
                                previous_pose[3:], current_pose[3:], timestep
                            )
                        )
                    )
                )
                table_contact_window.append(
                    any(
                        can_name
                        in (
                            contact.bodies[0].entity.name,
                            contact.bodies[1].entity.name,
                        )
                        and any(
                            "table" in str(body).lower()
                            for body in (
                                contact.bodies[0].entity.name,
                                contact.bodies[1].entity.name,
                            )
                            if body != can_name
                        )
                        for contact in scene.scene.get_contacts()
                    )
                )
                previous_pose = current_pose
            can_pose = previous_pose
        planned_can_xyz = np.asarray(expected["can_xyz"], dtype=np.float64)
        can_xy_drift = float(np.linalg.norm(can_pose[:2] - planned_can_xyz[:2]))
        can_settle_drop = float(planned_can_xyz[2] - can_pose[2])
        can_orientation_error = quaternion_orientation_error(
            can_pose[3:], [0.5, 0.5, 0.5, 0.5]
        )
        table_support_height = 0.74 + float(scene.table_z_bias)
        can_support_height_error = abs(float(can_pose[2]) - table_support_height)
        linear, linear_measured, linear_provenance = _rigid_velocity_with_provenance(
            scene.can, "linear_velocity"
        )
        angular, angular_measured, angular_provenance = _rigid_velocity_with_provenance(
            scene.can, "angular_velocity"
        )
        sleep_state = None
        for component in _entity(scene.can).get_components():
            value = getattr(component, "is_sleeping", None)
            if value is None:
                continue
            value = value() if callable(value) else value
            if isinstance(value, (bool, np.bool_)):
                sleep_state = bool(value)
                break
        dynamic_checks = _f2_dynamic_post_settle_checks(
            planned_can_xyz=planned_can_xyz,
            can_pose=can_pose,
            table_support_height_m=table_support_height,
            pose_linear_speeds=pose_linear_speeds,
            pose_angular_speeds=pose_angular_speeds,
            table_contact_window=table_contact_window,
            sleep_state=sleep_state,
            required=bool(require_dynamic_stability),
        )
        if require_dynamic_stability and not all(dynamic_checks.values()):
            raise ValueError(
                "F2 dynamic can post-settle contract failed: "
                + str(dynamic_checks)
            )
        return {
            "layout_version": F2_LAYOUT_VERSION_V2,
            "layout_sha256": hash_json(expected),
            "dynamic_pose_contract_version": "f2_post_settle_dynamic_pose_contract_v3",
            "planned_spawn_can_xyz": planned_can_xyz.tolist(),
            "post_settle_can_pose": can_pose.tolist(),
            "post_settle_can_xyz_delta_m": (
                can_pose[:3] - planned_can_xyz
            ).tolist(),
            "post_settle_can_xy_drift_m": can_xy_drift,
            "post_settle_can_z_drop_m": can_settle_drop,
            "post_settle_can_orientation_error_rad": can_orientation_error,
            "table_support_height_m": table_support_height,
            "post_settle_can_support_height_error_m": can_support_height_error,
            "post_settle_table_contact": table_contact_window,
            "post_settle_component_linear_velocity_mps": linear.tolist(),
            "post_settle_component_angular_velocity_rps": angular.tolist(),
            "post_settle_component_velocity_provenance": {
                "linear": linear_provenance,
                "angular": angular_provenance,
            },
            "post_settle_component_velocity_available_audit_only": {
                "linear": linear_measured,
                "angular": angular_measured,
            },
            "post_settle_pose_linear_speed_mps": pose_linear_speeds,
            "post_settle_pose_angular_speed_rps": pose_angular_speeds,
            "gate_velocity_source": "250 Hz finite difference of the same saved actor pose",
            "post_settle_sleep_state": sleep_state,
            "checks": dynamic_checks,
            "dynamic_post_settle_gate_applied": bool(
                require_dynamic_stability
            ),
        }

    def audit_task_physical_feasibility(self, scene, program):
        try:
            layout = self._require_layout_v2(
                scene, require_dynamic_stability=True
            )
        except BaseException as exc:
            return {
                "task_feasible": False,
                "physical_feasible": False,
                "planner_solvable": None,
                "failure_type": "f2_frozen_layout_mismatch",
                "evidence": {"error": str(exc)},
            }
        roles_ok = set(getattr(scene, "role_actors", {})) == {
            "main_can",
            "box",
            "scale",
            "stand",
        }
        poses_finite = roles_ok and all(
            np.all(np.isfinite(_pose(actor)))
            for actor in scene.role_actors.values()
        )
        program_family = str(program.get("program_id", "")).startswith("F2-")
        can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
        inside_route = build_inside_gravity_drop_route(
            current_eef_pose=_arm_eef_pose(scene, "left"),
            current_actor_pose=_pose(scene.can),
            box_pose=_pose(scene.box),
            can_half_extents_m=can_half,
            can_local_geometry_center_m=can_local_center,
            rest_eef_pose=np.asarray(
                scene.robot.left_original_pose, dtype=np.float64
            ),
        )
        support_z = actor_origin_z_for_table_support(
            table_plane_z_m=0.74 + float(scene.table_z_bias),
            actor_quaternion_wxyz=[0.5, 0.5, 0.5, 0.5],
            can_local_geometry_center_m=can_local_center,
            can_half_extents_m=can_half,
        )
        stand_pose = _pose(scene.stand)
        beside_target = np.asarray(
            [
                stand_pose[0] + HISTORICAL_SAFE_STAND_RELATIVE_XY_M[0],
                stand_pose[1] + HISTORICAL_SAFE_STAND_RELATIVE_XY_M[1],
                support_z,
                0.5,
                0.5,
                0.5,
                0.5,
            ],
            dtype=np.float64,
        )
        beside_clearance = target_facility_clearance_audit(
            target_actor_pose=beside_target,
            can_local_geometry_center_m=can_local_center,
            can_half_extents_m=can_half,
            facility_aabbs=self._facility_world_aabbs(scene),
        )
        beside_xy = beside_target[:2]
        inside_center = (
            np.asarray(F2_LAYOUT_V2["box_xyz"][:2], dtype=np.float64)
            + BOX_INSIDE_CENTER_OFFSET_WORLD_M[:2]
        )
        scale_center = (
            np.asarray(F2_LAYOUT_V2["scale_xyz"][:2], dtype=np.float64)
            + SCALE_TOP_CENTER_OFFSET_WORLD_M[:2]
        )
        beside_radial = float(np.linalg.norm(beside_xy - stand_pose[:2]))
        beside_predicate_audit = {
            "radial_distance_m": beside_radial,
            "inside": bool(
                np.all(
                    np.abs(beside_xy - inside_center)
                    <= BOX_INSIDE_HALF_XY_M
                )
            ),
            "on": bool(
                np.all(
                    np.abs(beside_xy - scale_center) <= SCALE_TOP_HALF_XY_M
                )
            ),
            "within_table": bool(
                F2_TABLE_BOUNDS_XY[0, 0]
                <= beside_xy[0]
                <= F2_TABLE_BOUNDS_XY[1, 0]
                and F2_TABLE_BOUNDS_XY[0, 1]
                <= beside_xy[1]
                <= F2_TABLE_BOUNDS_XY[1, 1]
            ),
        }
        beside_predicate_audit["beside"] = bool(
            BESIDE_INNER_M <= beside_radial <= BESIDE_OUTER_M
            and not beside_predicate_audit["inside"]
            and not beside_predicate_audit["on"]
        )
        scale_point = scene.scale.get_functional_point(0)
        checks = {
            "roles": roles_ok,
            "poses_finite": poses_finite,
            "program_family": program_family,
            "same_object": program["steps"][0].get("object") == "main_object",
            "left_arm_fixed": True,
            "relation": program["steps"][1].get("relation")
            in ("inside", "on", "beside"),
            "center_aware_can_fits_box_cavity": inside_route["gates"]
            ["final_target_full_obb_inside"],
            "inside_route_geometry_audit": inside_route["audit"]["pass"],
            "scale_functional_point_exists": scale_point is not None
            and np.all(np.isfinite(np.asarray(scale_point, dtype=np.float64))),
            "historical_safe_beside_target_predicate": beside_predicate_audit[
                "beside"
            ]
            and beside_predicate_audit["within_table"],
            "historical_safe_beside_target_clearance": beside_clearance[
                "pass"
            ],
            "center_aware_beside_support_z": abs(
                support_z - layout["post_settle_can_pose"][2]
            )
            <= 0.005,
        }
        passed = all(checks.values())
        return {
            "task_feasible": passed,
            "physical_feasible": passed,
            "planner_solvable": None,
            "failure_type": None if passed else "f2_task_physical_contract_v3",
            "evidence": {
                **checks,
                "frozen_layout": layout,
                "can_local_geometry_center_m": can_local_center.tolist(),
                "can_half_extents_m": can_half.tolist(),
                "inside_route_geometry": inside_route,
                "historical_safe_beside_target_actor_pose": beside_target.tolist(),
                "historical_safe_beside_predicate_audit": beside_predicate_audit,
                "historical_safe_beside_clearance_audit": beside_clearance,
            },
        }

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f2_same_can_grasp_lift_v3_3",
            "family": "F2",
            "arm": "left",
            "ops": ["pregrasp", "grasp", "close", "lift_12cm"],
            "target_role_read": False,
            "main_object": "071_can/base1",
            "settling_excluded_from_semantic_P": True,
        }

    def initialize_prefix_replay_trace(self, scene):
        scene.initialize_trace(scene.can, "left", role_actors=scene.role_actors)

    def plan_and_execute_canonical_prefix(
        self, scene, prefix_contract, *, capture_anchor
    ):
        self._require_layout_v2(scene)
        self.initialize_prefix_replay_trace(scene)
        scene.planner_query_limit = 24
        selected, target_construction_audit = (
            _audited_planner_assisted_target_construction(
                scene,
                scene.can,
                arm="left",
                variant_id="f2_prefix_target_construction",
                callback=lambda: scene.choose_grasp_pose(
                    scene.can,
                    arm_tag=_arm_tag_left(),
                    pre_dis=0.08,
                    target_dis=0,
                ),
            )
        )
        pregrasp, grasp = selected
        prefix_planner_reset = _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id="f2_canonical_prefix_once",
            arm="left",
        )
        start = len(scene.trace) - 1
        _move_left(scene, pregrasp, "f2_prefix_pregrasp")
        _move_left(scene, grasp, "f2_prefix_grasp")
        _must_action(
            scene,
            scene.close_gripper(_arm_tag_left(), pos=0.0),
            "f2_prefix_close",
        )
        post_close = len(scene.trace) - 1 - start
        post_close_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.can)
        )
        lift = world_axis_offset_pose(_arm_eef_pose(scene, "left"), 0.12)
        _move_left(scene, lift, "f2_prefix_lift_12cm")
        post_lift = len(scene.trace) - 1 - start
        semantic_end = len(scene.trace) - 1
        semantic_anchor = capture_anchor(scene)
        settling = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
        _settle_prefix_with_replay_operator(scene, settling)
        acceptance_anchor = capture_anchor(scene)
        acceptance_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.can)
        )
        grasp_translation_drift = float(
            np.linalg.norm(acceptance_transform[:3] - post_close_transform[:3])
        )
        grasp_orientation_drift = quaternion_angular_error(
            acceptance_transform[3:], post_close_transform[3:]
        )
        prefix_acceptance = _prefix_physical_acceptance(
            scene,
            roles=("main_can",),
            require_selected_contact=True,
            expected_contact_actor_name=_entity(scene.can).get_name(),
            extra_checks={
                "grasp_transform_translation_stable": grasp_translation_drift
                <= 0.005,
                "grasp_transform_orientation_stable": grasp_orientation_drift
                <= 0.05,
            },
        )
        prefix_acceptance["grasp_transform_translation_drift_m"] = (
            grasp_translation_drift
        )
        prefix_acceptance["grasp_transform_orientation_drift_rad"] = (
            grasp_orientation_drift
        )
        return _prefix_reference_result(
            scene,
            start_action=start,
            semantic_end_action=semantic_end,
            semantic_end_anchor=semantic_anchor,
            acceptance_end_anchor=acceptance_anchor,
            settling_steps=settling,
            extra={
                "reference_event_boundaries": {
                    "post_close": post_close,
                    "post_lift": post_lift,
                },
                "target_construction_planner_audit": target_construction_audit,
                "prefix_planner_reset_receipt": prefix_planner_reset,
                "prefix_physical_acceptance": prefix_acceptance,
            },
        )

    @staticmethod
    def _terminal_qpos_within_limits(scene, terminal_qpos, *, arm="left"):
        terminal = np.asarray(terminal_qpos, dtype=np.float64).reshape(-1)
        joints = list(getattr(scene.robot, f"{arm}_entity").get_active_joints())
        if len(joints) != len(terminal):
            return False
        limits = np.asarray(
            [
                np.asarray(joint.get_limits(), dtype=np.float64).reshape(-1, 2)[0]
                for joint in joints
            ],
            dtype=np.float64,
        )
        return bool(
            np.all((~np.isfinite(limits[:, 0])) | (terminal >= limits[:, 0]))
            and np.all((~np.isfinite(limits[:, 1])) | (terminal <= limits[:, 1]))
        )

    @staticmethod
    def _facility_world_aabbs(scene):
        facilities = {
            "box": scene.box,
            "scale": scene.scale,
            "stand": scene.stand,
        }
        result = {}
        for role, actor in facilities.items():
            corners = obb_corners(
                _actor_geometry_center_pose(actor), _actor_half_extents(actor)
            )
            result[role] = {
                "lower": np.min(corners, axis=0).tolist(),
                "upper": np.max(corners, axis=0).tolist(),
            }
        return result

    @staticmethod
    def _carried_can_waypoint_envelope_audit(scene, route):
        """Necessary waypoint envelope; not a claim about curved joint-space motion."""

        current_eef = _arm_eef_pose(scene, "left")
        current_actor = _pose(scene.can)
        eef_to_actor = relative_pose(current_eef, current_actor)
        held_eef_waypoints = [current_eef] + [
            np.asarray(item["pose"], dtype=np.float64)
            for item in route["targets"][:4]
        ]
        actor_origin_waypoints = [
            compose_pose(eef_pose, eef_to_actor) for eef_pose in held_eef_waypoints
        ]
        can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
        local_center_pose = np.asarray(
            [*can_local_center, 1.0, 0.0, 0.0, 0.0], dtype=np.float64
        )
        actor_waypoints = [
            compose_pose(actor_pose, local_center_pose)
            for actor_pose in actor_origin_waypoints
        ]
        can_orientation_invariant_radius = float(np.linalg.norm(can_half))
        facility_aabbs = {
            role: {
                "lower": np.asarray(bounds["lower"], dtype=np.float64),
                "upper": np.asarray(bounds["upper"], dtype=np.float64),
            }
            for role, bounds in F2ControllerV3_3._facility_world_aabbs(
                scene
            ).items()
        }
        margin = 0.005
        segments = []
        collisions = []
        for index, (start_actor, end_actor) in enumerate(
            zip(actor_waypoints, actor_waypoints[1:])
        ):
            start_corners = obb_corners(start_actor, can_half)
            end_corners = obb_corners(end_actor, can_half)
            endpoint_obb_lower = np.minimum(
                np.min(start_corners, axis=0), np.min(end_corners, axis=0)
            )
            endpoint_obb_upper = np.maximum(
                np.max(start_corners, axis=0), np.max(end_corners, axis=0)
            )
            swept_lower = (
                np.minimum(start_actor[:3], end_actor[:3])
                - can_orientation_invariant_radius
            )
            swept_upper = (
                np.maximum(start_actor[:3], end_actor[:3])
                + can_orientation_invariant_radius
            )
            segment_collisions = []
            for role, bounds in facility_aabbs.items():
                overlap = bool(
                    np.all(swept_upper >= bounds["lower"] - margin)
                    and np.all(swept_lower <= bounds["upper"] + margin)
                )
                if overlap:
                    segment_collisions.append(role)
                    collisions.append(
                        {"segment_index": index, "facility_role": role}
                    )
            segments.append(
                {
                    "segment_index": index,
                    "eef_segment_id": route["targets"][index]["segment_id"],
                    "swept_actor_aabb_lower": swept_lower.tolist(),
                    "swept_actor_aabb_upper": swept_upper.tolist(),
                    "endpoint_obb_union_lower_audit_only": endpoint_obb_lower.tolist(),
                    "endpoint_obb_union_upper_audit_only": endpoint_obb_upper.tolist(),
                    "facility_collisions": segment_collisions,
                }
            )
        return {
            "schema_version": "cmf_f2_carried_can_waypoint_envelope_audit_v1",
            "method": (
                "actor-center segment expanded on every axis by the can's "
                "orientation-invariant half-diagonal bounding-sphere radius, "
                "tested against frozen facility world AABBs with 5mm margin"
            ),
            "can_half_extents_m": can_half.tolist(),
            "can_local_geometry_center_m": can_local_center.tolist(),
            "can_orientation_invariant_bounding_sphere_radius_m": (
                can_orientation_invariant_radius
            ),
            "facility_aabbs": {
                role: {
                    "lower": bounds["lower"].tolist(),
                    "upper": bounds["upper"].tolist(),
                }
                for role, bounds in facility_aabbs.items()
            },
            "margin_m": margin,
            "segments": segments,
            "collisions": collisions,
            "official_curobo_whole_robot_collision_still_required": True,
            "curved_planned_path_covered": False,
            "actual_execution_contact_gate_required": True,
            "pass": not collisions,
        }

    def _plan_fixed_beside_candidates(self, scene, program):
        raw_actual_qpos = np.ascontiguousarray(
            np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64).reshape(-1)
        )
        planner_input_qpos = planner_array(
            raw_actual_qpos,
            label=f"{program['program_id']} beside planner-input prefix-end qpos",
        ).reshape(-1)
        start_hash = hash_array(raw_actual_qpos)
        planner_input_start_hash = hash_array(planner_input_qpos)
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        candidate_receipts = []
        selected = None
        selected_route = None
        selected_reset = None
        selected_planned = None
        total_queries = 0
        for candidate in F2_BESIDE_CANDIDATES_V3:
            route = build_beside_route(
                candidate.candidate_id,
                current_eef_pose=_arm_eef_pose(scene, "left"),
                current_actor_pose=_pose(scene.can),
                stand_pose=_pose(scene.stand),
                rest_eef_pose=rest,
            )
            if route["audit"]["pass"] is not True:
                raise ValueError(
                    f"F2 beside candidate {candidate.candidate_id} failed CPU route audit"
                )
            waypoint_audit = self._carried_can_waypoint_envelope_audit(
                scene, route
            )
            reset = _planner_reset(
                scene,
                planner_seed=F2_BESIDE_PLANNER_SEED_V3,
                variant_id=f"f2_beside_fixed_candidate:{candidate.candidate_id}",
                arm="left",
            )
            before = int(getattr(scene, "planner_query_count", 0))
            planned = _plan_chain(
                scene, route["targets"], query_limit=96, arm="left"
            )
            query_delta = int(getattr(scene, "planner_query_count", 0)) - before
            if query_delta != len(planned["segment_receipts"]):
                raise RuntimeError(
                    "F2 beside candidate live planner delta differs from segment receipts"
                )
            total_queries += query_delta
            within_limits = self._terminal_qpos_within_limits(
                scene, planned["terminal_qpos"], arm="left"
            )
            receipt = {
                "candidate_id": candidate.candidate_id,
                "main_object": "071_can/base1",
                "arm": "left",
                "reference": "074_displaystand/base3",
                "planner_seed": F2_BESIDE_PLANNER_SEED_V3,
                "planner_start_state_sha256": start_hash,
                "rng_state_after_reset_sha256": reset[
                    "rng_state_after_reset_sha256"
                ],
                "planner_reset_performed": reset["reset_performed"] is True,
                "planner_reset_receipt": reset,
                "planner_instance_id": reset["planner_instance_id"],
                "route": route,
                "route_audit_pass": route["audit"]["pass"] is True,
                "upright_axis_audited": True,
                "terminal_qpos_within_joint_limits": within_limits,
                "waypoint_envelope_pass": waypoint_audit["pass"] is True,
                "waypoint_envelope_audit": waypoint_audit,
                "actual_held_transport_contact_gate_required": True,
                "facility_distance_pass": all(
                    route["audit"]["checks"][key]
                    for key in (
                        "target_inside_table",
                        "target_in_beside_annulus",
                        "target_excludes_inside_on",
                    )
                ),
                "planner_query_count": query_delta,
                "segment_receipts": planned["segment_receipts"],
                "planner_input_prefix_end_qpos_sha256": planner_input_start_hash,
                "first_segment_start_matches_planner_input_prefix_end": bool(
                    planned["segment_receipts"]
                    and planned["segment_receipts"][0]["start_qpos_sha256"]
                    == planner_input_start_hash
                ),
            }
            candidate_receipts.append(receipt)
            decision = audit_beside_candidate_receipts(candidate_receipts)
            if decision["pass"]:
                selected = candidate.candidate_id
                selected_route = route
                selected_reset = reset
                selected_planned = planned
                break
        decision = audit_beside_candidate_receipts(candidate_receipts)
        if selected is None:
            return {
                "planner_solvable": False,
                "planner_query_count": int(total_queries),
                "failure_type": decision["terminal_if_exhausted"]
                or "f2_beside_fixed_candidate_prefix_failed",
                "evidence": {
                    "candidate_decision": decision,
                    "candidate_receipts": candidate_receipts,
                    "planner_collision_check_source": (
                        "official CuRobo planner success/failure per frozen segment"
                    ),
                    "quantitative_collision_clearance_available": False,
                },
                "actual_prefix_end_qpos_sha256": start_hash,
                "execution_spec": None,
                "_execution_controls": None,
                "_actual_prefix_end_qpos": None,
            }
        return _cache_preplanned_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="left",
            targets=selected_route["targets"],
            raw_actual_qpos=raw_actual_qpos,
            planner_input_qpos=planner_input_qpos,
            reset=selected_reset,
            planned=selected_planned,
            planner_query_count=total_queries,
            extra={
                "relation": "beside",
                "variant_id": "beside_fixed_six_candidate_routes_v3",
                "target_actor_pose": selected_route["target_actor_pose"],
                "release_target_index": selected_route["release_target_index"],
                "layout_version": F2_LAYOUT_VERSION_V2,
                "selected_beside_candidate_id": selected,
                "beside_candidate_decision": decision,
                "beside_candidate_receipts": candidate_receipts,
                "inside_full_obb_verifier_relaxed": False,
            },
        )

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        self._require_layout_v2(scene)
        relation = program["steps"][1]["relation"]
        current_eef = _arm_eef_pose(scene, "left")
        current_actor = _pose(scene.can)
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        if relation == "inside":
            can_local_center, can_half_extents = _actor_local_geometry_bounds(
                scene.can
            )
            route = build_inside_gravity_drop_route(
                current_eef_pose=current_eef,
                current_actor_pose=current_actor,
                box_pose=_pose(scene.box),
                can_half_extents_m=can_half_extents,
                can_local_geometry_center_m=can_local_center,
                rest_eef_pose=rest,
            )
            if route["audit"]["pass"] is not True:
                raise ValueError("F2 inside gravity-drop CPU route audit failed")
            return _cache_suffix_controls(
                scene,
                program_id=program["program_id"],
                arm="left",
                targets=route["targets"],
                query_limit=24,
                extra={
                    "relation": relation,
                    "variant_id": "inside_gravity_drop_10cm_v3",
                    "target_actor_pose": route["target_actor_pose"],
                    "release_target_index": route["release_target_index"],
                    "layout_version": F2_LAYOUT_VERSION_V2,
                    "inside_gravity_drop_route": route,
                    "inside_full_obb_verifier_relaxed": False,
                },
            )
        if relation == "beside":
            can_local_center, can_half_extents = _actor_local_geometry_bounds(
                scene.can
            )
            route = build_historical_safe_beside_route(
                current_eef_pose=current_eef,
                current_actor_pose=current_actor,
                stand_pose=_pose(scene.stand),
                rest_eef_pose=rest,
                can_local_geometry_center_m=can_local_center,
                can_half_extents_m=can_half_extents,
                facility_aabbs=self._facility_world_aabbs(scene),
                table_plane_z_m=0.74 + float(scene.table_z_bias),
            )
            if route["audit"]["pass"] is not True:
                raise ValueError("F2 historical-safe beside route CPU audit failed")
            return _cache_suffix_controls(
                scene,
                program_id=program["program_id"],
                arm="left",
                targets=route["targets"],
                query_limit=24,
                extra={
                    "relation": "beside",
                    "variant_id": "beside_historical_safe_support_route_v4",
                    "target_actor_pose": route["target_actor_pose"],
                    "release_target_index": route["release_target_index"],
                    "layout_version": F2_LAYOUT_VERSION_V2,
                    "historical_safe_beside_route": route,
                    "candidate_search_enabled": False,
                    "inside_full_obb_verifier_relaxed": False,
                },
            )
        if relation == "on":
            target_actor = current_actor.copy()
            target_actor[:3] = np.asarray(
                scene.scale.get_functional_point(0), dtype=np.float64
            )[:3]
            release = actor_target_to_eef_pose(
                current_eef, current_actor, target_actor
            )
            preplace = world_axis_offset_pose(release, 0.10)
            targets = [
                {"segment_id": f"{relation}_preplace", "pose": preplace},
                {"segment_id": f"{relation}_release", "pose": release},
                {"segment_id": f"{relation}_retreat", "pose": preplace},
            ]
            release_index = 1
            targets.append({"segment_id": "f2_rest", "pose": rest})
            return _cache_suffix_controls(
                scene,
                program_id=program["program_id"],
                arm="left",
                targets=targets,
                query_limit=24,
                extra={
                    "relation": relation,
                    "variant_id": "on_scale_frozen_target_v1",
                    "target_actor_pose": target_actor.tolist(),
                    "release_target_index": release_index,
                    "layout_version": F2_LAYOUT_VERSION_V2,
                    "inside_full_obb_verifier_relaxed": False,
                },
            )
        raise ValueError("unknown F2 relation")

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization_spec
    ):
        def release_sample(label):
            row = scene.trace[-1]
            can_pose_value = _pose(scene.can)
            can_geometry_pose_value = _actor_geometry_center_pose(scene.can)
            actor_name = _entity(scene.can).get_name()
            box_name = _entity(scene.box).get_name()
            can_box_contacts = [
                item
                for item in row["contact_pairs"]
                if actor_name in (item["body_a"], item["body_b"])
                and box_name in (item["body_a"], item["body_b"])
            ]
            table_clearance = min(
                can_pose_value[0] - (-0.45),
                0.45 - can_pose_value[0],
                can_pose_value[1] - (-0.35),
                0.20 - can_pose_value[1],
            )
            return {
                "label": label,
                "trace_row": len(scene.trace) - 1,
                "can_pose": can_pose_value.tolist(),
                "can_geometry_center_pose": can_geometry_pose_value.tolist(),
                "can_linear_velocity": np.asarray(
                    row["actor_linear_velocity"], dtype=np.float64
                ).tolist(),
                "can_angular_velocity": np.asarray(
                    row["actor_angular_velocity"], dtype=np.float64
                ).tolist(),
                "full_obb_inside": verify_true_cavity_obb(
                    can_geometry_pose_value,
                    _actor_half_extents(scene.can),
                    _pose(scene.box),
                    F2_PLASTICBOX_BASE2_CAVITY,
                ),
                "can_box_contact_count": len(can_box_contacts),
                "can_box_contacts": can_box_contacts,
                "can_box_contact_impulse_sum": float(
                    sum(item.get("impulse_norm_sum", 0.0) for item in can_box_contacts)
                ),
                "eef_pose": np.asarray(row["eef"], dtype=np.float64).tolist(),
                "eef_release_tracking_position_error_m": float(
                    np.linalg.norm(
                        np.asarray(row["eef"][:3], dtype=np.float64)
                        - np.asarray(spec["targets"][release_index]["pose"][:3], dtype=np.float64)
                    )
                ),
                "gripper_actual_qpos": np.asarray(
                    row["realized_left_gripper_joint_qpos"], dtype=np.float64
                ).tolist(),
                "selected_gripper_contact": bool(row["selected_gripper_contact"]),
                "table_edge_clearance_m": float(table_clearance),
            }

        controls = _cached_controls(scene, spec)
        release_index = int(spec["release_target_index"])

        def current_inside_drop_opening_gate():
            can_geometry_pose = _actor_geometry_center_pose(scene.can)
            can_corners_world = obb_corners(
                can_geometry_pose, _actor_half_extents(scene.can)
            )
            homogeneous = np.concatenate(
                (
                    can_corners_world,
                    np.ones((len(can_corners_world), 1), dtype=np.float64),
                ),
                axis=1,
            )
            local = (
                np.linalg.inv(pose_matrix(_pose(scene.box))) @ homogeneous.T
            ).T[:, :3]
            lower = np.asarray(
                F2_PLASTICBOX_BASE2_CAVITY["lower_m"], dtype=np.float64
            )
            upper = np.asarray(
                F2_PLASTICBOX_BASE2_CAVITY["upper_m"], dtype=np.float64
            )
            opening_axes = (0, 2)
            rim_clearance = float(np.min(local[:, 1]) - upper[1])
            projection_inside = bool(
                np.all(
                    np.min(local[:, opening_axes], axis=0)
                    >= lower[list(opening_axes)]
                )
                and np.all(
                    np.max(local[:, opening_axes], axis=0)
                    <= upper[list(opening_axes)]
                )
            )
            return {
                "opening_projection_inside": projection_inside,
                "rim_clearance_m": rim_clearance,
                "rim_clearance_pass": rim_clearance >= 0.02,
                "can_geometry_center_pose": can_geometry_pose.tolist(),
            }

        execution_receipts = []
        staged_inside_gates = []
        inside_release_samples = {}
        inside_drop_route = spec.get("inside_gravity_drop_route")
        held_transport_start_row = len(scene.trace) - 1
        held_segment_trace_windows = []
        for index in range(release_index + 1):
            segment_start_row = len(scene.trace) - 1
            execution_receipt = _execute_cached_segment(
                scene, spec, controls, index
            )
            segment_end_row = len(scene.trace) - 1
            execution_receipts.append(execution_receipt)
            held_segment_trace_windows.append(
                {
                    "segment_id": spec["targets"][index]["segment_id"],
                    "start_trace_row": segment_start_row,
                    "end_trace_row": segment_end_row,
                    "start_relative_to_held_transport": segment_start_row
                    - held_transport_start_row,
                    "end_relative_to_held_transport": segment_end_row
                    - held_transport_start_row,
                }
            )
            if spec["relation"] == "inside":
                row = scene.trace[-1]
                gate = {
                        "segment_id": spec["targets"][index]["segment_id"],
                        "selected_gripper_contact": bool(
                            row["selected_gripper_contact"]
                        ),
                        "can_pose": _pose(scene.can).tolist(),
                        "can_speed_mps": float(
                            np.linalg.norm(row["actor_linear_velocity"])
                        ),
                        "full_obb_inside": verify_true_cavity_obb(
                            _actor_geometry_center_pose(scene.can),
                            _actor_half_extents(scene.can),
                            _pose(scene.box),
                            F2_PLASTICBOX_BASE2_CAVITY,
                        )["pass_true_cavity_obb"],
                    }
                if inside_drop_route is not None:
                    opening_gate = current_inside_drop_opening_gate()
                    gate.update(
                        {
                            "inside_drop_opening_projection_inside": opening_gate[
                                "opening_projection_inside"
                            ],
                            "inside_drop_rim_clearance_m": opening_gate[
                                "rim_clearance_m"
                            ],
                            "inside_drop_rim_clearance_pass": opening_gate[
                                "rim_clearance_pass"
                            ],
                            "inside_drop_geometry_center_pose": opening_gate[
                                "can_geometry_center_pose"
                            ],
                            "inside_drop_route_audit_pass": inside_drop_route[
                                "audit"
                            ]["pass"]
                            is True,
                        }
                    )
                staged_inside_gates.append(gate)
                if gate["selected_gripper_contact"] is not True:
                    raise RuntimeError(
                        f"F2 inside staged descent lost selected-gripper contact at {gate['segment_id']}"
                    )
                if index == release_index:
                    if inside_drop_route is None and gate["full_obb_inside"] is not True:
                        raise RuntimeError(
                            "F2 inside staged descent reached release without full OBB inside cavity"
                        )
                    if inside_drop_route is not None and not all(
                        gate[key]
                        for key in (
                            "inside_drop_opening_projection_inside",
                            "inside_drop_rim_clearance_pass",
                            "inside_drop_route_audit_pass",
                        )
                    ):
                        raise RuntimeError(
                            "F2 inside gravity-drop pre-release opening/rim Gate failed"
                        )
        held_transport_rows = scene.trace[held_transport_start_row:]
        can_name = _entity(scene.can).get_name()
        facility_names = {
            _entity(scene.box).get_name(),
            _entity(scene.scale).get_name(),
            _entity(scene.stand).get_name(),
        }
        selected_gripper_bodies = set(
            _gripper_below_eef_envelope(scene, arm="left")[
                "selected_gripper_links"
            ]
        )
        relation_support_bodies = (
            {_entity(scene.scale).get_name()}
            if spec["relation"] == "on"
            else {"table"}
            if spec["relation"] == "beside"
            else set()
        )
        support_contact_start_relative_row = (
            held_segment_trace_windows[release_index][
                "start_relative_to_held_transport"
            ]
            if relation_support_bodies
            else None
        )
        transport_contact_gate = audit_f2_held_transport_contacts(
            held_transport_rows,
            relation=spec["relation"],
            can_actor_name=can_name,
            selected_gripper_body_names=selected_gripper_bodies,
            named_facility_body_names=facility_names,
            relation_support_body_names=relation_support_bodies,
            support_contact_start_relative_row=support_contact_start_relative_row,
            held_segment_trace_windows=held_segment_trace_windows,
        )
        if transport_contact_gate["pass"] is not True:
            raise RuntimeError("F2 held transport contact/identity Gate failed")
        if spec["relation"] == "inside":
            if inside_drop_route is not None:
                _wait_and_record(scene, 50)
                hold_rows = scene.trace[-50:]
                hold_linear = [
                    float(np.linalg.norm(row["actor_linear_velocity"]))
                    for row in hold_rows
                ]
                hold_angular = [
                    float(np.linalg.norm(row["actor_angular_velocity"]))
                    for row in hold_rows
                ]
                hold_contacts = [
                    bool(row["selected_gripper_contact"]) for row in hold_rows
                ]
                hold_actor_names = [
                    str(row["selected_contact_actor_name"]) for row in hold_rows
                ]
                release_geometry_gate = current_inside_drop_opening_gate()
                pre_release_hold = {
                    "schema_version": "cmf_f2_inside_pre_release_hold_gate_v1",
                    "step_count": 50,
                    "maximum_linear_speed_mps": max(hold_linear),
                    "maximum_angular_speed_rps": max(hold_angular),
                    "selected_gripper_contact_fraction": float(
                        np.mean(hold_contacts)
                    ),
                    "selected_contact_actor_names": hold_actor_names,
                    "release_frame_geometry_gate": release_geometry_gate,
                    "checks": {
                        "linear_stationary": max(hold_linear)
                        <= PROVISIONAL_RUNTIME_THRESHOLDS[
                            "stable_linear_speed_mps"
                        ],
                        "angular_stationary": max(hold_angular)
                        <= PROVISIONAL_RUNTIME_THRESHOLDS[
                            "eef_stationary_angular_speed_rps"
                        ],
                        "selected_gripper_contact_continuous": all(
                            hold_contacts
                        ),
                        "selected_contact_actor_identity": all(
                            name == _entity(scene.can).get_name()
                            for name in hold_actor_names
                        ),
                        "release_frame_opening_projection_inside": (
                            release_geometry_gate["opening_projection_inside"]
                        ),
                        "release_frame_rim_clearance": release_geometry_gate[
                            "rim_clearance_pass"
                        ],
                    },
                }
                pre_release_hold["pass"] = all(
                    pre_release_hold["checks"].values()
                )
                staged_inside_gates.append(
                    {
                        "segment_id": "inside_drop_pre_release_hold_50",
                        "pre_release_hold_gate": pre_release_hold,
                        "pass": pre_release_hold["pass"],
                    }
                )
                inside_release_samples[
                    "pre_release_hold_gate"
                ] = pre_release_hold
                if pre_release_hold["pass"] is not True:
                    raise RuntimeError(
                        "F2 inside gravity-drop pre-release stability/contact Gate failed"
                    )
            inside_release_samples["before_release"] = release_sample(
                "before_release"
            )
        _must_action(
            scene,
            scene.open_gripper(_arm_tag_left(), pos=1.0),
            f"f2_{spec['relation']}_release",
        )
        if spec["relation"] == "inside":
            configured_steps = (
                set(inside_drop_route["sample_steps"])
                if inside_drop_route is not None
                else {1, 5, 10, 25, 50, 125}
            )
            settle_steps = (
                int(inside_drop_route["settle_steps"])
                if inside_drop_route is not None
                else 125
            )
            for step in range(1, settle_steps + 1):
                _wait_and_record(scene, 1)
                if step in configured_steps:
                    inside_release_samples[f"after_release_{step}"] = release_sample(
                        f"after_release_{step}"
                    )
        else:
            _wait_and_record(scene, 100)
        for index in range(release_index + 1, len(spec["targets"]) - 1):
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, index)
            )
        if spec["relation"] == "inside":
            inside_release_samples["after_retreat"] = release_sample(
                "after_retreat"
            )
        execution_receipts.append(
            _execute_cached_segment(
                scene, spec, controls, len(spec["targets"]) - 1
            )
        )
        _wait_and_record(scene, 75)
        if spec["relation"] == "inside":
            inside_release_samples["after_rest"] = release_sample("after_rest")
        can_pose = _pose(scene.can)
        can_geometry_pose = _actor_geometry_center_pose(scene.can)
        can_half = _actor_half_extents(scene.can)
        inside = verify_true_cavity_obb(
            can_geometry_pose,
            can_half,
            _pose(scene.box),
            F2_PLASTICBOX_BASE2_CAVITY,
        )["pass_true_cavity_obb"]
        scale_target = np.asarray(
            scene.scale.get_functional_point(0), dtype=np.float64
        )
        can_corners = obb_corners(can_geometry_pose, can_half)
        on_footprint = bool(
            np.all(
                np.abs(can_corners[:, :2] - scale_target[None, :2])
                <= np.asarray([0.07, 0.07], dtype=np.float64)[None, :]
            )
        )
        on_bottom_height_error = float(
            abs(np.min(can_corners[:, 2]) - scale_target[2])
        )
        on_height = bool(on_bottom_height_error <= 0.02)
        on = bool(on_footprint and on_height)
        stand_geometry_pose = _actor_geometry_center_pose(scene.stand)
        radial = float(
            np.linalg.norm(
                can_geometry_pose[:2] - stand_geometry_pose[:2]
            )
        )
        beside = bool(
            0.12 <= radial <= 0.23
            and can_pose[2] <= 0.83
            and not inside
            and not on
        )
        support_actor = scene.box if inside else scene.scale if on else "table"
        stable_rows, speeds, support = _stable_and_support(
            scene, scene.can, support_actor
        )
        angular_speeds = [
            float(np.linalg.norm(row["actor_angular_velocity"]))
            for row in stable_rows
        ]
        exclusive = {"inside": inside, "on": on, "beside": beside}
        relation = spec["relation"]
        rest = np.asarray(spec["targets"][-1]["pose"], dtype=np.float64)
        realized = _arm_eef_pose(scene, "left")
        checks = {
            "target_relation": exclusive[relation],
            "exclusive_relation": sum(bool(value) for value in exclusive.values())
            == 1,
            "stable_window": bool(speeds)
            and max(speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
            and bool(angular_speeds)
            and max(angular_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "support_contact_window": bool(support) and all(support),
            "gripper_open": _arm_gripper_open(scene, "left"),
            "rest_position": np.linalg.norm(realized[:3] - rest[:3])
            <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            "rest_orientation": quaternion_orientation_error(
                realized[3:], rest[3:]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": np.linalg.norm(
                scene.trace[-1]["eef_linear_velocity"]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": np.linalg.norm(
                scene.trace[-1]["eef_angular_velocity"]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
            "held_transport_contact_gate": transport_contact_gate["pass"],
        }
        semantic = {
            "pass": all(checks.values()),
            "checks": checks,
            "exclusive_relations": exclusive,
            "on_scale_full_obb_footprint": on_footprint,
            "on_scale_center_height": on_height,
            "on_scale_bottom_height_error_m": on_bottom_height_error,
            "target_relation": relation,
            "staged_inside_gates": staged_inside_gates,
            "suffix_segment_execution_receipts": execution_receipts,
            "preflight_rollout_same_control_cache": True,
            "inside_full_obb_verifier_relaxed": False,
            "inside_release_dynamics_samples": inside_release_samples,
            "held_transport_contact_gate": transport_contact_gate,
            "final_can_actor_origin_pose": can_pose.tolist(),
            "final_can_geometry_center_pose": can_geometry_pose.tolist(),
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=replay,
            semantic_verifier=semantic,
        )


class F3ControllerV3_3(FamilyControllerV3_3):
    family = "F3"
    arm = "left"

    def validate_replayed_prefix_physical(self, scene, replay):
        start_row = int(replay["trace_replay_start_row"])
        v_start = int(replay["reference_event_boundaries"]["shared_first_v_start"])
        v_end = int(replay["reference_event_boundaries"]["shared_first_v_end"])
        metrics = _realized_event_metrics(
            scene.trace[
                max(start_row, start_row + v_start - 1) : start_row + v_end
            ],
            axis="V",
        )
        motion = verify_realized_motion_metrics(
            {"event_0_V": metrics}, PROVISIONAL_RUNTIME_THRESHOLDS
        )
        transforms = {
            name: _replay_boundary_transform(scene, replay, name)
            for name in F3_GRASP_BOUNDARIES
            if name != "acceptance_end"
        }
        transforms["acceptance_end"] = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        boundary_audit = audit_f3_grasp_boundary_stability(transforms)
        event_rows = scene.trace[
            max(start_row, start_row + v_start - 1) : start_row + v_end
        ]
        gripper_evidence = _gripper_below_eef_envelope(scene, arm="left")
        contact_audit = audit_f3_free_space_event_contacts(
            [row["contact_pairs"] for row in event_rows],
            bottle_actor_name=_entity(scene.bottle).get_name(),
            selected_gripper_link_names=gripper_evidence[
                "selected_gripper_links"
            ],
            support_actor_names=("table", _entity(scene.pad).get_name()),
        )
        pre_v_boundary = int(
            replay["reference_event_boundaries"]["pre_shared_V"]
        )
        pre_v_end_row_exclusive = start_row + pre_v_boundary
        pre_v_rows = scene.trace[
            pre_v_end_row_exclusive
            - F3_CENTRAL_HOLD_STEPS : pre_v_end_row_exclusive
        ]
        if len(pre_v_rows) != F3_CENTRAL_HOLD_STEPS:
            raise RuntimeError("F3 replay pre-V hold window length changed")
        pre_v_contact_audit = audit_f3_free_space_event_contacts(
            [row["contact_pairs"] for row in pre_v_rows],
            bottle_actor_name=_entity(scene.bottle).get_name(),
            selected_gripper_link_names=gripper_evidence[
                "selected_gripper_links"
            ],
            support_actor_names=("table", _entity(scene.pad).get_name()),
        )
        pre_v_replay_gate = {
            "schema_version": "cmf_f3_replay_pre_shared_v_gate_v1",
            "hold_step_count": len(pre_v_rows),
            "maximum_eef_linear_speed_mps": max(
                float(np.linalg.norm(row["eef_linear_velocity"]))
                for row in pre_v_rows
            ),
            "maximum_eef_angular_speed_rps": max(
                float(np.linalg.norm(row["eef_angular_velocity"]))
                for row in pre_v_rows
            ),
            "maximum_bottle_linear_speed_mps": max(
                float(np.linalg.norm(row["actor_linear_velocity"]))
                for row in pre_v_rows
            ),
            "maximum_bottle_angular_speed_rps": max(
                float(np.linalg.norm(row["actor_angular_velocity"]))
                for row in pre_v_rows
            ),
            "free_space_contact_audit": pre_v_contact_audit,
            "checks": {},
        }
        pre_v_replay_gate["checks"] = {
            "eef_linear_stationary": pre_v_replay_gate[
                "maximum_eef_linear_speed_mps"
            ]
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_linear_speed_mps"
            ],
            "eef_angular_stationary": pre_v_replay_gate[
                "maximum_eef_angular_speed_rps"
            ]
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "bottle_linear_stationary": pre_v_replay_gate[
                "maximum_bottle_linear_speed_mps"
            ]
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "bottle_angular_stationary": pre_v_replay_gate[
                "maximum_bottle_angular_speed_rps"
            ]
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "selected_gripper_contact_continuous": all(
                bool(row["selected_gripper_contact"]) for row in pre_v_rows
            ),
            "selected_contact_actor_identity": all(
                str(row["selected_contact_actor_name"])
                == _entity(scene.bottle).get_name()
                for row in pre_v_rows
            ),
            "free_space_support_contact": pre_v_contact_audit["pass"],
        }
        pre_v_replay_gate["pass"] = all(
            pre_v_replay_gate["checks"].values()
        )
        translation_drift = boundary_audit["maximum_translation_drift_m"]
        orientation_drift = boundary_audit["maximum_orientation_drift_rad"]
        result = _prefix_physical_acceptance(
            scene,
            roles=("bottle",),
            require_selected_contact=True,
            expected_contact_actor_name=_entity(scene.bottle).get_name(),
            extra_checks={
                "prefix_end_equivalent": replay["prefix_end_equivalent"],
                "shared_first_v_realized_motion": motion["pass"],
                "grasp_transform_translation_stable": boundary_audit["checks"]
                ["all_translation_boundaries_stable"],
                "grasp_transform_orientation_stable": boundary_audit["checks"]
                ["all_orientation_boundaries_stable"],
                "shared_v_free_space_support_contact": contact_audit["pass"],
                "pre_shared_v_replay_gate": pre_v_replay_gate["pass"],
            },
        )
        result.update(
            {
                "shared_first_v_metrics": metrics,
                "shared_first_v_gate": motion,
                "grasp_transform_translation_drift_m": translation_drift,
                "grasp_transform_orientation_drift_rad": orientation_drift,
                "grasp_boundary_stability_audit": boundary_audit,
                "shared_v_free_space_contact_audit": contact_audit,
                "pre_shared_v_replay_gate": pre_v_replay_gate,
                "boundary_grasp_transforms": {
                    name: value.tolist() for name, value in transforms.items()
                },
                "selected_gripper_envelope_evidence": gripper_evidence,
            }
        )
        return result

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f3_grasp_lift_clearance_carry_shared_first_v_v3_3_r3",
            "family": "F3",
            "arm": "left",
            "ops": [
                "pregrasp",
                "grasp",
                "close",
                "lift_4cm",
                "lift_8cm",
                "clearance_raise",
                "same_height_center_carry_2x",
                "central_hold_50",
                "shared_first_V_time_dilated_endpoint_holds",
            ],
            "shared_v_nominal_amplitude_m": F3_V_NOMINAL_AMPLITUDE_M_V3_3,
            "target_role_read": False,
            "settling_excluded_from_semantic_P": True,
        }

    def initialize_prefix_replay_trace(self, scene):
        scene.initialize_trace(
            scene.bottle, "left", role_actors=scene.role_actors
        )

    def plan_and_execute_canonical_prefix(
        self, scene, prefix_contract, *, capture_anchor
    ):
        self.initialize_prefix_replay_trace(scene)
        scene.planner_query_limit = 32
        selected, target_construction_audit = (
            _audited_planner_assisted_target_construction(
                scene,
                scene.bottle,
                arm="left",
                variant_id="f3_prefix_target_construction",
                callback=lambda: scene.choose_grasp_pose(
                    scene.bottle,
                    arm_tag=_arm_tag_left(),
                    pre_dis=0.09,
                    target_dis=0,
                ),
            )
        )
        pregrasp, grasp = selected
        frozen_grasp = frozen_f3_grasp_contract()
        if (
            target_construction_audit["callback_selected_pose_match_count"] != 1
            or target_construction_audit["callback_selected_contact_point_id"]
            != frozen_grasp["contact_point_id"]
            or target_construction_audit[
                "callback_selected_candidate_index_within_batch"
            ]
            != frozen_grasp["rotation_candidate_index"]
            or target_construction_audit[
                "callback_selected_candidate_planner_status"
            ]
            != "Success"
        ):
            raise RuntimeError(
                "F3 official chooser no longer selects frozen contact3/candidate0"
            )
        target_construction_audit["frozen_grasp_contract"] = frozen_grasp
        target_construction_audit["frozen_selection_verified"] = True
        target_construction_audit["query_mode"] = (
            "audit every official contact-point batch; use chooser result only if "
            "the callback-selected pregrasp uniquely matches frozen contact3/candidate0"
        )
        prefix_planner_reset = _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id="f3_canonical_prefix_once",
            arm="left",
        )
        start = len(scene.trace) - 1
        _move_left(scene, pregrasp, "f3_prefix_pregrasp")
        _move_left(scene, grasp, "f3_prefix_grasp")
        _must_action(
            scene,
            scene.close_gripper(_arm_tag_left(), pos=0.0),
            "f3_prefix_close",
        )
        post_close = len(scene.trace) - 1 - start
        post_close_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        for distance, label in (
            (0.04, "f3_prefix_lift_4cm"),
            (0.04, "f3_prefix_lift_8cm"),
        ):
            goal = world_axis_offset_pose(_arm_eef_pose(scene, "left"), distance)
            _move_left(scene, goal, label)
        post_lift = len(scene.trace) - 1 - start
        post_lift_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        post_lift_eef = _arm_eef_pose(scene, "left")
        bottle_corners = obb_corners(
            _actor_geometry_center_pose(scene.bottle),
            _actor_half_extents(scene.bottle),
        )
        gripper_evidence = _gripper_below_eef_envelope(scene, arm="left")
        clearance_audit = build_f3_clearance_height_audit(
            table_top_z_m=0.74 + float(scene.table_z_bias),
            pad_top_z_m=float(
                _pose(scene.pad)[2] + F3_PAD_HALF_EXTENTS_M[2]
            ),
            post_lift_eef_z_m=float(post_lift_eef[2]),
            bottle_below_eef_m=float(
                post_lift_eef[2] - np.min(bottle_corners[:, 2])
            ),
            gripper_below_eef_m=gripper_evidence[
                "gripper_below_eef_envelope_m"
            ],
        )
        if clearance_audit["pass"] is not True:
            raise RuntimeError("F3 held-envelope clearance audit failed")
        carry_route = build_f3_clearance_route_targets(
            post_lift_eef, clearance_audit
        )
        if carry_route["pass"] is not True:
            raise RuntimeError("F3 clearance carry route audit failed")
        carry_planned = _plan_chain(
            scene, carry_route["segments"], query_limit=32, arm="left"
        )
        if carry_planned["pass"] is not True or len(carry_planned["controls"]) != 2:
            raise RuntimeError("F3 clearance carry planner failed")
        _execute_control(
            scene,
            carry_planned["controls"][0],
            carry_route["segments"][0]["segment_id"],
            arm="left",
        )
        post_clearance_raise = len(scene.trace) - 1 - start
        post_clearance_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        dilated_center_control = time_dilate_f3_carry_control_2x(
            carry_planned["controls"][1]
        )
        _execute_control(
            scene,
            dilated_center_control,
            carry_route["segments"][1]["segment_id"],
            arm="left",
        )
        post_center_high = len(scene.trace) - 1 - start
        post_center_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        _wait_and_record(scene, F3_CENTRAL_HOLD_STEPS)
        pre_shared_v = len(scene.trace) - 1 - start
        pre_shared_v_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        pre_v_rows = scene.trace[-F3_CENTRAL_HOLD_STEPS:]
        pre_v_transforms = {
            "post_close": post_close_transform,
            "post_lift": post_lift_transform,
            "post_clearance_raise": post_clearance_transform,
            "post_center_high": post_center_transform,
            "pre_shared_V": pre_shared_v_transform,
        }
        pre_v_gate = build_f3_pre_v_evidence_v4(
            hold_rows=pre_v_rows,
            boundary_transforms=pre_v_transforms,
            thresholds={
                "eef_linear_speed_mps": PROVISIONAL_RUNTIME_THRESHOLDS[
                    "eef_stationary_linear_speed_mps"
                ],
                "eef_angular_speed_rps": PROVISIONAL_RUNTIME_THRESHOLDS[
                    "eef_stationary_angular_speed_rps"
                ],
                "bottle_linear_speed_mps": PROVISIONAL_RUNTIME_THRESHOLDS[
                    "stable_linear_speed_mps"
                ],
                "bottle_angular_speed_rps": PROVISIONAL_RUNTIME_THRESHOLDS[
                    "eef_stationary_angular_speed_rps"
                ],
                "grasp_translation_drift_m": 0.005,
                "grasp_orientation_drift_rad": 0.05,
            },
            expected_actor_name=_entity(scene.bottle).get_name(),
            selected_gripper_link_names=gripper_evidence[
                "selected_gripper_links"
            ],
            support_actor_names=("table", _entity(scene.pad).get_name()),
            planner_metadata={
                "planner_query_count_at_pre_v": int(
                    getattr(scene, "planner_query_count", 0)
                ),
                "target_construction_planner_audit": target_construction_audit,
                "prefix_planner_reset_receipt": prefix_planner_reset,
                "clearance_carry_segment_receipts": carry_planned[
                    "segment_receipts"
                ],
            },
            route_metadata={
                "clearance_height_audit": clearance_audit,
                "clearance_carry_route": carry_route,
                "center_carry_time_dilation": dilated_center_control[
                    "_cmf_time_dilation"
                ],
            },
        )
        try:
            pre_v_gate = require_f3_pre_v_gate(pre_v_gate)
        except F3PreVBoundaryGateFailure as exc:
            scene._cmf_prefix_failure_receipt = exc.to_receipt()
            raise
        central = np.asarray(carry_route["segments"][1]["pose"], dtype=np.float64)
        v_start = len(scene.trace) - 1 - start
        shared_v_targets = _time_dilated_closed_loop_event_targets(
            central,
            axis="V",
            amplitude_m=F3_V_NOMINAL_AMPLITUDE_M_V3_3,
            segment_prefix="f3_shared_V",
        )
        scene.mark("event_0_V_start")
        for target in shared_v_targets:
            _move_left(scene, target["pose"], target["segment_id"])
            _wait_and_record(
                scene, F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2
            )
        scene.mark("event_0_V_end")
        v_end = len(scene.trace) - 1 - start
        post_shared = v_end
        post_shared_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        event_rows = scene.trace[start + v_start : start + 1 + v_end]
        first_v_metrics = _realized_event_metrics(event_rows, axis="V")
        semantic_end = len(scene.trace) - 1
        semantic_anchor = capture_anchor(scene)
        settling = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
        _settle_prefix_with_replay_operator(scene, settling)
        acceptance_anchor = capture_anchor(scene)
        acceptance_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        boundary_transforms = {
            "post_close": post_close_transform,
            "post_lift": post_lift_transform,
            "post_clearance_raise": post_clearance_transform,
            "post_center_high": post_center_transform,
            "pre_shared_V": pre_shared_v_transform,
            "post_shared_V": post_shared_transform,
            "acceptance_end": acceptance_transform,
        }
        boundary_audit = audit_f3_grasp_boundary_stability(boundary_transforms)
        grasp_translation_drift = boundary_audit["maximum_translation_drift_m"]
        grasp_orientation_drift = boundary_audit[
            "maximum_orientation_drift_rad"
        ]
        shared_v_gate = verify_realized_motion_metrics(
            {"event_0_V": first_v_metrics}, PROVISIONAL_RUNTIME_THRESHOLDS
        )
        shared_v_contact_audit = audit_f3_free_space_event_contacts(
            [row["contact_pairs"] for row in event_rows],
            bottle_actor_name=_entity(scene.bottle).get_name(),
            selected_gripper_link_names=gripper_evidence[
                "selected_gripper_links"
            ],
            support_actor_names=("table", _entity(scene.pad).get_name()),
        )
        prefix_acceptance = _prefix_physical_acceptance(
            scene,
            roles=("bottle",),
            require_selected_contact=True,
            expected_contact_actor_name=_entity(scene.bottle).get_name(),
            extra_checks={
                "shared_first_v_realized_motion": shared_v_gate["pass"],
                "grasp_transform_translation_stable": boundary_audit["checks"]
                ["all_translation_boundaries_stable"],
                "grasp_transform_orientation_stable": boundary_audit["checks"]
                ["all_orientation_boundaries_stable"],
                "shared_v_free_space_support_contact": shared_v_contact_audit[
                    "pass"
                ],
                "pre_shared_v_boundary_gate": pre_v_gate["pass"],
            },
        )
        prefix_acceptance.update(
            {
                "shared_first_v_metrics": first_v_metrics,
                "shared_first_v_gate": shared_v_gate,
                "grasp_transform_translation_drift_m": grasp_translation_drift,
                "grasp_transform_orientation_drift_rad": grasp_orientation_drift,
                "grasp_boundary_stability_audit": boundary_audit,
                "shared_v_free_space_contact_audit": shared_v_contact_audit,
                "clearance_height_audit": clearance_audit,
                "clearance_carry_route": carry_route,
                "pre_shared_v_boundary_gate": pre_v_gate,
                "selected_gripper_envelope_evidence": gripper_evidence,
                "boundary_grasp_transforms": {
                    name: value.tolist()
                    for name, value in boundary_transforms.items()
                },
            }
        )
        return _prefix_reference_result(
            scene,
            start_action=start,
            semantic_end_action=semantic_end,
            semantic_end_anchor=semantic_anchor,
            acceptance_end_anchor=acceptance_anchor,
            settling_steps=settling,
            extra={
                "reference_event_boundaries": {
                    "post_close": post_close,
                    "post_lift": post_lift,
                    "post_clearance_raise": post_clearance_raise,
                    "post_center_high": post_center_high,
                    "pre_shared_V": pre_shared_v,
                    "shared_first_v_start": v_start,
                    "shared_first_v_end": v_end,
                    "post_shared_V": post_shared,
                },
                "reference_shared_first_v_metrics": first_v_metrics,
                "closed_loop_primitive_version": F3_CLOSED_LOOP_PRIMITIVE_VERSION,
                "event_endpoint_hold_steps": F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2,
                "central_hold_steps": F3_CENTRAL_HOLD_STEPS,
                "clearance_height_audit": clearance_audit,
                "clearance_carry_route": carry_route,
                "pre_shared_v_boundary_gate": pre_v_gate,
                "clearance_carry_segment_receipts": carry_planned[
                    "segment_receipts"
                ],
                "center_carry_time_dilation": dilated_center_control[
                    "_cmf_time_dilation"
                ],
                "shared_v_target_count": len(shared_v_targets),
                "target_construction_planner_audit": target_construction_audit,
                "prefix_planner_reset_receipt": prefix_planner_reset,
                "prefix_physical_acceptance": prefix_acceptance,
            },
        )

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        axes = "".join(step["axis"] for step in program["steps"])
        if axes not in ("VVHH", "VHVH", "VHHV") or axes[0] != "V":
            raise ValueError("F3 program is outside the frozen universe")
        center = _arm_eef_pose(scene, "left")
        targets = []
        event_groups = []
        for event_index, axis in enumerate(axes[1:], start=1):
            amplitude = (
                F3_H_NOMINAL_AMPLITUDE_M_V3_3
                if axis == "H"
                else F3_V_NOMINAL_AMPLITUDE_M_V3_3
            )
            start_index = len(targets)
            event_targets = _time_dilated_closed_loop_event_targets(
                center,
                axis=axis,
                amplitude_m=amplitude,
                segment_prefix=f"suffix_event_{event_index}_{axis}",
            )
            targets.extend(event_targets)
            event_groups.append(
                {
                    "event_index": event_index,
                    "axis": axis,
                    "target_start_index": start_index,
                    "target_count": len(event_targets),
                    "endpoint_hold_steps": F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2,
                }
            )
        start_actor = np.asarray(
            replay["start_anchor"]["actor_states"]["bottle"]["pose"],
            dtype=np.float64,
        )
        current_actor = _pose(scene.bottle)
        release = actor_target_to_eef_pose(center, current_actor, start_actor)
        preplace = world_axis_offset_pose(release, 0.10)
        return_start = len(targets)
        targets.extend(
            [
                {"segment_id": "f3_return_preplace", "pose": preplace},
                {"segment_id": "f3_return_release", "pose": release},
                {"segment_id": "f3_return_retreat", "pose": preplace},
                {
                    "segment_id": "f3_rest",
                    "pose": np.asarray(
                        scene.robot.left_original_pose, dtype=np.float64
                    ),
                },
            ]
        )
        return _cache_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="left",
            targets=targets,
            query_limit=42,
            extra={
                "event_order": axes,
                "event_groups": event_groups,
                "return_start_index": return_start,
                "target_bottle_pose": start_actor.tolist(),
                "closed_loop_primitive_version": F3_CLOSED_LOOP_PRIMITIVE_VERSION,
            },
        )

    @staticmethod
    def _boundary_transform(scene, replay, name):
        return _replay_boundary_transform(scene, replay, name)

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization_spec
    ):
        controls = _cached_controls(scene, spec)
        metrics = {}
        start_row = int(replay["trace_replay_start_row"])
        v_start = int(replay["reference_event_boundaries"]["shared_first_v_start"])
        v_end = int(replay["reference_event_boundaries"]["shared_first_v_end"])
        metrics["event_0_V"] = _realized_event_metrics(
            scene.trace[
                max(start_row, start_row + v_start - 1) : start_row + v_end
            ],
            axis="V",
        )
        gripper_evidence = _gripper_below_eef_envelope(scene, arm="left")
        support_names = ("table", _entity(scene.pad).get_name())
        event_contact_audits = {
            "event_0_V": audit_f3_free_space_event_contacts(
                [
                    row["contact_pairs"]
                    for row in scene.trace[
                        max(start_row, start_row + v_start - 1) : start_row
                        + v_end
                    ]
                ],
                bottle_actor_name=_entity(scene.bottle).get_name(),
                selected_gripper_link_names=gripper_evidence[
                    "selected_gripper_links"
                ],
                support_actor_names=support_names,
            )
        }
        execution_receipts = []
        for group in spec["event_groups"]:
            index = int(group["target_start_index"])
            axis = group["axis"]
            event_index = int(group["event_index"])
            event_center_row = len(scene.trace) - 1
            scene.mark(f"event_{event_index}_{axis}_start")
            target_count = int(group["target_count"])
            if target_count != 7:
                raise RuntimeError("F3 time-dilated event target count changed")
            hold_steps = int(group["endpoint_hold_steps"])
            if hold_steps != F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2:
                raise RuntimeError("F3 event endpoint hold contract changed")
            for offset in range(target_count):
                execution_receipts.append(
                    _execute_cached_segment(
                        scene, spec, controls, index + offset
                    )
                )
                _wait_and_record(scene, hold_steps)
            scene.mark(f"event_{event_index}_{axis}_end")
            event_key = f"event_{event_index}_{axis}"
            event_rows = scene.trace[event_center_row:]
            metrics[event_key] = _realized_event_metrics(
                event_rows, axis=axis
            )
            event_contact_audits[event_key] = audit_f3_free_space_event_contacts(
                [row["contact_pairs"] for row in event_rows],
                bottle_actor_name=_entity(scene.bottle).get_name(),
                selected_gripper_link_names=gripper_evidence[
                    "selected_gripper_links"
                ],
                support_actor_names=support_names,
            )
        return_start = int(spec["return_start_index"])
        execution_receipts.append(
            _execute_cached_segment(scene, spec, controls, return_start)
        )
        execution_receipts.append(
            _execute_cached_segment(scene, spec, controls, return_start + 1)
        )
        before_eef = _arm_eef_pose(scene, "left")
        before_actor = _pose(scene.bottle)
        target_pose = np.asarray(spec["target_bottle_pose"], dtype=np.float64)
        samples = {
            "before_release": self.legacy._release_sample(
                scene,
                target_pose,
                eef_target=spec["targets"][return_start + 1]["pose"],
            )
        }
        _must_action(
            scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "f3_release"
        )
        sample_steps = {1, 5, 10, 25, 50, 125, 250}
        for step in range(1, 251):
            _wait_and_record(scene, 1)
            if step in sample_steps:
                samples[f"after_release_{step}"] = self.legacy._release_sample(
                    scene, target_pose
                )
        execution_receipts.append(
            _execute_cached_segment(scene, spec, controls, return_start + 2)
        )
        execution_receipts.append(
            _execute_cached_segment(scene, spec, controls, return_start + 3)
        )
        _wait_and_record(scene, 75)
        stable_rows, speeds, contacts = _stable_and_support(
            scene, scene.bottle, scene.pad
        )
        angular_speeds = [
            float(np.linalg.norm(row["actor_angular_velocity"]))
            for row in stable_rows
        ]
        stable_motion_pass = (
            bool(speeds)
            and max(speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
            and bool(angular_speeds)
            and max(angular_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ]
        )
        samples["after_rest"] = self.legacy._release_sample(
            scene,
            target_pose,
            eef_target=spec["targets"][return_start + 3]["pose"],
            stable_window_pass=stable_motion_pass,
            support_window_pass=bool(contacts) and all(contacts),
        )
        samples["after_rest"]["stable_linear_speed_max_mps"] = (
            max(speeds) if speeds else None
        )
        samples["after_rest"]["stable_angular_speed_max_rps"] = (
            max(angular_speeds) if angular_speeds else None
        )
        samples["after_rest"]["stable_motion_gate_includes_angular"] = True
        transforms = {
            name: self._boundary_transform(scene, replay, name).tolist()
            for name in (
                "post_close",
                "post_lift",
                "post_clearance_raise",
                "post_center_high",
                "pre_shared_V",
                "post_shared_V",
            )
        }
        transforms["before_release"] = relative_pose(
            before_eef, before_actor
        ).tolist()
        base = np.asarray(transforms["post_close"], dtype=np.float64)
        translation_drifts = {
            name: float(np.linalg.norm(np.asarray(value)[:3] - base[:3]))
            for name, value in transforms.items()
        }
        orientation_drifts = {
            name: quaternion_angular_error(np.asarray(value)[3:], base[3:])
            for name, value in transforms.items()
        }
        grasp = {
            "initial_T_eef_actor": transforms["post_close"],
            "before_release_T_eef_actor": transforms["before_release"],
            "grasp_transform_translation_drift": max(
                translation_drifts.values()
            ),
            "grasp_transform_orientation_drift": max(
                orientation_drifts.values()
            ),
            "grasp_transform_stable": max(translation_drifts.values())
            <= 0.005
            and max(orientation_drifts.values()) <= 0.05,
            "boundary_transforms": transforms,
            "boundary_translation_drift_m": translation_drifts,
            "boundary_orientation_drift_rad": orientation_drifts,
        }
        diagnosis = classify_f3_release_dynamics_v3_1(
            samples,
            grasp,
            position_tolerance_m=PROVISIONAL_RUNTIME_THRESHOLDS[
                "position_error_m"
            ],
            orientation_tolerance_rad=PROVISIONAL_RUNTIME_THRESHOLDS[
                "orientation_error"
            ],
            eef_tracking_tolerance_m=PROVISIONAL_RUNTIME_THRESHOLDS[
                "rest_position_error_m"
            ],
            grasp_translation_drift_tolerance_m=0.005,
            grasp_orientation_drift_tolerance_rad=0.05,
        )
        motion = verify_realized_motion_metrics(
            metrics, PROVISIONAL_RUNTIME_THRESHOLDS
        )
        rest_target = np.asarray(
            spec["targets"][return_start + 3]["pose"], dtype=np.float64
        )
        realized_rest = _arm_eef_pose(scene, "left")
        final_checks = {
            "event_order_matches_program": spec["event_order"]
            == "".join(step["axis"] for step in program["steps"]),
            "return_equivalence": diagnosis["final_return_equivalence"],
            "realized_motion": motion["pass"],
            "all_events_free_of_pad_table_contact": all(
                item["pass"] for item in event_contact_audits.values()
            ),
            "grasp_transform_stable": grasp["grasp_transform_stable"],
            "gripper_open": _arm_gripper_open(scene, "left"),
            "rest_position": np.linalg.norm(
                realized_rest[:3] - rest_target[:3]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            "rest_orientation": quaternion_orientation_error(
                realized_rest[3:], rest_target[3:]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": np.linalg.norm(
                scene.trace[-1]["eef_linear_velocity"]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": np.linalg.norm(
                scene.trace[-1]["eef_angular_velocity"]
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        semantic = {
            "pass": all(final_checks.values()),
            "full_f3_program_complete": all(final_checks.values()),
            "executed_event_order": spec["event_order"],
            "expected_event_order": "".join(
                step["axis"] for step in program["steps"]
            ),
            "diagnosis": diagnosis,
            "grasp_transform": grasp,
            "samples": samples,
            "realized_motion": motion,
            "event_metrics": metrics,
            "event_free_space_contact_audits": event_contact_audits,
            "selected_gripper_envelope_evidence": gripper_evidence,
            "final_checks": final_checks,
            "suffix_segment_execution_receipts": execution_receipts,
            "preflight_rollout_same_control_cache": True,
            "shared_first_v_replayed_from_artifact": True,
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=replay,
            semantic_verifier=semantic,
            extra={
                "final_state_equivalence_payload": {
                    "bottle_pose": _pose(scene.bottle).tolist(),
                    "left_eef_pose": _arm_eef_pose(scene, "left").tolist(),
                    "left_gripper_open": _arm_gripper_open(scene, "left"),
                    "target_bottle_pose": target_pose.tolist(),
                }
            },
        )


class F4ControllerV3_3(FamilyControllerV3_3):
    family = "F4"
    arm = "right"
    COMMON_SEGMENT_IDS = (
        "common_pregrasp",
        "common_grasp",
        "common_lift",
        "common_safe_vertical",
        "common_center_high",
        "common_above_tray",
        "common_preplace",
        "common_release",
        "common_neutral",
    )

    @staticmethod
    def _slot_state_receipt(scene, *, role, actor, slot):
        footprint = footprint_inside_local_region(
            _pose(actor),
            BLOCK_HALF_EXTENTS,
            _pose(slot),
            [-0.035, -0.035, -0.01],
            [0.035, 0.035, 0.03],
            (0, 1),
        )["pass_support_footprint"]
        rows, linear_speeds, support_contacts = _stable_and_support(
            scene, actor, "table"
        )
        angular_speeds = [
            float(np.linalg.norm(row["role_actor_angular_velocities"][role]))
            for row in rows
        ]
        checks = {
            "slot_footprint": bool(footprint),
            "linear_stable": bool(linear_speeds)
            and max(linear_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "angular_stable": bool(angular_speeds)
            and max(angular_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "continuous_table_support": bool(support_contacts)
            and all(support_contacts),
        }
        return {
            "role": role,
            "checks": checks,
            "maximum_linear_speed_mps": max(linear_speeds)
            if linear_speeds
            else None,
            "maximum_angular_speed_rps": max(angular_speeds)
            if angular_speeds
            else None,
            "support_contact_fraction": float(np.mean(support_contacts))
            if support_contacts
            else 0.0,
            "pass": all(checks.values()),
        }

    @classmethod
    def _validate_f4_target_structure(
        cls, targets, extra, *, require_three_groups: bool
    ):
        ids = tuple(item.get("segment_id") for item in targets)
        if ids[:9] != cls.COMMON_SEGMENT_IDS:
            raise ValueError("F4 common target segment structure changed")
        if extra.get("execution_arm") != "right":
            raise ValueError("F4 execution arm must remain right")
        common_contract = extra.get("common_grasp_contract")
        if (
            not isinstance(common_contract, Mapping)
            or common_contract.get("arm") != "right"
        ):
            raise ValueError("F4 common-X explicit grasp contract is invalid")
        groups = extra.get("object_target_groups")
        if not isinstance(groups, list):
            raise ValueError("F4 object target groups are missing")
        if not require_three_groups:
            if len(targets) != 9 or groups:
                raise ValueError("F4 common-prefix target scope must contain exactly 9 targets")
            return
        order = list(extra.get("object_order", []))
        if len(groups) != 3 or [group.get("role") for group in groups] != order:
            raise ValueError("F4 object target group order differs from program order")
        flattened = []
        for group in groups:
            role = group["role"]
            group_targets = group.get("targets")
            expected = tuple(
                f"{role}_{suffix}"
                for suffix in F4_SEGMENTED_BLOCK_SUFFIXES
            )
            if (
                not isinstance(group_targets, list)
                or len(group_targets) != len(F4_SEGMENTED_BLOCK_SUFFIXES)
                or tuple(item.get("segment_id") for item in group_targets)
                != expected
            ):
                raise ValueError(f"F4 {role} target group structure changed")
            flattened.extend(expected)
        if len(targets) != 9 + 3 * len(F4_SEGMENTED_BLOCK_SUFFIXES) or ids[9:] != tuple(flattened):
            raise ValueError("F4 flattened target sequence differs from grouped targets")

    def validate_replayed_prefix_physical(self, scene, replay):
        footprint = footprint_inside_local_region(
            _pose(scene.common_x),
            BLOCK_HALF_EXTENTS,
            _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"],
            TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        _, speeds, contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
        return _prefix_physical_acceptance(
            scene,
            roles=("common_x",),
            require_selected_contact=False,
            extra_checks={
                "prefix_end_equivalent": replay["prefix_end_equivalent"],
                "common_x_tray_footprint": footprint[
                    "pass_support_footprint"
                ],
                "common_x_support_contact": bool(contacts) and all(contacts),
                "common_x_stable": bool(speeds)
                and max(speeds)
                <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
                "right_gripper_open": _arm_gripper_open(scene, "right"),
            },
        )

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f4_common_x_tray_neutral_v3_3",
            "family": "F4",
            "arm": "right",
            "ops": ["common_X_to_tray", "branch_neutral"],
            "target_role_read": False,
            "settling_excluded_from_semantic_P": True,
        }

    def initialize_prefix_replay_trace(self, scene):
        scene.initialize_trace(
            scene.common_x, "right", role_actors=scene.role_actors
        )

    def _common_targets(self, scene):
        program = F4SubtaskOrder().checked_provisional_programs()[0]
        targets, extra = self.legacy.build_targets(
            scene,
            program,
            {
                "variant_id": "route1_minimum_height_segmented",
                "execution_scope": "common_x_route_repair",
                "common_grasp_mode": "project_cube_grasp_v1",
            },
        )
        self._validate_f4_target_structure(
            targets, extra, require_three_groups=False
        )
        return targets, extra

    def _tilted_full_targets(self, scene, program):
        legacy_targets, extra = self.legacy.build_targets(
            scene,
            program,
            {
                "variant_id": "route1_minimum_height_segmented",
                "common_grasp_mode": "project_cube_grasp_v1",
            },
        )
        self._validate_f4_target_structure(
            legacy_targets[:9],
            {**extra, "object_target_groups": []},
            require_three_groups=False,
        )
        order = [step["object"] for step in program["steps"][1:]]
        if order != list(extra["object_order"]):
            raise ValueError("F4 tilted route program order differs from legacy common build")
        planned = getattr(scene, "_cmf_planned_root_slot_spec", {})
        layout = planned.get("scene_layout", {}) if isinstance(planned, Mapping) else {}
        neutral = np.asarray(layout.get("branch_neutral_pose"), dtype=np.float64)
        if neutral.shape != (7,):
            raise ValueError("F4 tilted route requires the frozen branch-neutral pose")
        object_poses = {
            role: _pose(getattr(scene, role.lower())).tolist()
            for role in ("A", "B", "C")
        }
        target_actor_poses = {}
        for role in ("A", "B", "C"):
            target = _pose(getattr(scene, role.lower()))
            target[:3] = np.asarray(
                getattr(scene, f"slot_{role.lower()}").get_pose().p,
                dtype=np.float64,
            ) + np.asarray([0.0, 0.0, BLOCK_HALF_EXTENTS[2]])
            target_actor_poses[role] = target.tolist()
        tilted = build_uniform_tilted_f4_block_groups(
            object_poses=object_poses,
            target_actor_poses=target_actor_poses,
            neutral_pose=neutral,
            object_order=order,
            arm="right",
        )
        geometry = audit_uniform_tilted_f4_geometry(
            object_poses=object_poses,
            target_actor_poses=target_actor_poses,
            neutral_pose=neutral,
            object_order=order,
            table_top_z_m=0.74 + float(scene.table_z_bias),
        )
        if geometry["pass"] is not True:
            raise ValueError("F4 uniform tilted route geometry audit failed")
        revised_extra = dict(extra)
        revised_extra.update(
            {
                "object_order": order,
                "object_target_groups": tilted["object_target_groups"],
                "block_carry_route_version": F4_TILTED_ROUTE_VERSION,
                "block_carry_route_audit": {
                    "group_set": tilted["audit"],
                    "geometry": geometry,
                },
                "uniform_tilted_grasp_contract": tilted["grasp_contract"],
                "scene_layout_changed": False,
                "tray_pose_changed": False,
                "program_changed": False,
                "verifier_changed": False,
            }
        )
        all_targets = list(legacy_targets[:9]) + list(tilted["flattened_targets"])
        self._validate_f4_target_structure(
            all_targets, revised_extra, require_three_groups=True
        )
        return all_targets, revised_extra

    def plan_and_execute_canonical_prefix(
        self, scene, prefix_contract, *, capture_anchor
    ):
        self.initialize_prefix_replay_trace(scene)
        scene.planner_query_limit = 24
        targets, extra = self._common_targets(scene)
        reset = _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id="f4_canonical_prefix_once",
            arm="right",
        )
        planned = _plan_chain(scene, targets, query_limit=24, arm="right")
        if not planned["pass"]:
            raise RuntimeError("F4 canonical common-X prefix planner failed")
        start = len(scene.trace) - 1
        controls = planned["controls"]
        for index in (0, 1):
            _execute_control(
                scene, controls[index], targets[index]["segment_id"], arm="right"
            )
        _must_action(
            scene,
            scene.close_gripper(_arm_tag("right"), pos=0.0),
            "f4_common_close_gripper",
        )
        for index in range(2, 8):
            _execute_control(
                scene, controls[index], targets[index]["segment_id"], arm="right"
            )
        _must_action(
            scene,
            scene.open_gripper(_arm_tag("right"), pos=1.0),
            "f4_common_release",
        )
        _execute_control(
            scene, controls[8], targets[8]["segment_id"], arm="right"
        )
        semantic_end = len(scene.trace) - 1
        semantic_anchor = capture_anchor(scene)
        settling = 75
        _settle_prefix_with_replay_operator(scene, settling)
        acceptance_anchor = capture_anchor(scene)
        common_footprint = footprint_inside_local_region(
            _pose(scene.common_x),
            BLOCK_HALF_EXTENTS,
            _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"],
            TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        common_rows, common_speeds, common_contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
        common_angular_speeds = [
            float(np.linalg.norm(row["actor_angular_velocity"]))
            for row in common_rows
        ]
        prefix_acceptance = _prefix_physical_acceptance(
            scene,
            roles=("common_x",),
            require_selected_contact=False,
            extra_checks={
                "common_x_tray_footprint": common_footprint[
                    "pass_support_footprint"
                ],
                "common_x_support_contact": bool(common_contacts)
                and all(common_contacts),
                "common_x_stable": bool(common_speeds)
                and max(common_speeds)
                <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
                "right_gripper_open": _arm_gripper_open(scene, "right"),
            },
        )
        return _prefix_reference_result(
            scene,
            start_action=start,
            semantic_end_action=semantic_end,
            semantic_end_anchor=semantic_anchor,
            acceptance_end_anchor=acceptance_anchor,
            settling_steps=settling,
            extra={
                "planner_reset_receipt": reset,
                "prefix_segment_receipts": planned["segment_receipts"],
                "common_execution_extra": extra,
                "prefix_physical_acceptance": prefix_acceptance,
            },
        )

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        all_targets, extra = self._tilted_full_targets(scene, program)
        targets = all_targets[9:]
        result = _cache_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="right",
            targets=targets,
            query_limit=64,
            extra={
                "object_order": extra["object_order"],
                "object_target_groups": extra["object_target_groups"],
                "block_carry_route_version": extra[
                    "block_carry_route_version"
                ],
                "block_carry_route_audit": extra[
                    "block_carry_route_audit"
                ],
                "common_prefix_artifact_required": True,
            },
        )
        return result

    def plan_diagnostic_blocks_from_actual_prefix_end_state(
        self, scene, roles, replay
    ):
        roles = list(roles)
        if not roles or any(role not in ("A", "B", "C") for role in roles):
            raise ValueError("F4 diagnostic block roles are invalid")
        if len(set(roles)) != len(roles):
            raise ValueError("F4 diagnostic block roles must be unique")
        base_program = F4SubtaskOrder().checked_provisional_programs()[0]
        all_targets, extra = self._tilted_full_targets(scene, base_program)
        suffix_targets = all_targets[9:]
        group_by_role = {
            group["role"]: group for group in extra["object_target_groups"]
        }
        targets = []
        groups = []
        for role in roles:
            source_group = group_by_role[role]
            start = int(source_group["target_start_index"])
            width = len(F4_SEGMENTED_BLOCK_SUFFIXES)
            targets.extend(suffix_targets[start : start + width])
            groups.append({**source_group, "target_start_index": len(targets) - width})
        result = _cache_suffix_controls(
            scene,
            program_id="F4-DIAG-" + "".join(roles),
            arm="right",
            targets=targets,
            query_limit=64,
            extra={
                "object_order": roles,
                "object_target_groups": groups,
                "block_carry_route_version": extra[
                    "block_carry_route_version"
                ],
                "block_carry_route_audit": extra[
                    "block_carry_route_audit"
                ],
                "common_prefix_artifact_required": True,
                "diagnostic_block_gate": True,
            },
        )
        return result

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization_spec
    ):
        controls = _cached_controls(scene, spec)
        common_footprint = footprint_inside_local_region(
            _pose(scene.common_x),
            BLOCK_HALF_EXTENTS,
            _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"],
            TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        common_rows, common_speeds, common_contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
        common_angular_speeds = [
            float(np.linalg.norm(row["actor_angular_velocity"]))
            for row in common_rows
        ]
        common_checks = {
            "tray_footprint": common_footprint["pass_support_footprint"],
            "stable_window": bool(common_speeds)
            and max(common_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
            and bool(common_angular_speeds)
            and max(common_angular_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "support_contact_window": bool(common_contacts)
            and all(common_contacts),
            "gripper_open": _arm_gripper_open(scene, "right"),
            "prefix_end_equivalent": replay["prefix_end_equivalent"],
        }
        execution_receipts = []
        block_receipts = []
        completion_steps = []
        completed = []
        common_x_prefix_end_pose = _pose(scene.common_x)
        cursor = 0
        for group in spec["object_target_groups"]:
            role = group["role"]
            actor = getattr(scene, role.lower())
            slot = getattr(scene, f"slot_{role.lower()}")
            scene.set_trace_contact_actor(actor)
            others = {
                other: getattr(scene, other.lower())
                for other in ("A", "B", "C")
                if other != role
            }
            other_before = _position_map(others)
            start_eef = _arm_eef_pose(scene, "right")
            object_initial = _pose(actor)
            slot_before = footprint_inside_local_region(
                object_initial,
                BLOCK_HALF_EXTENTS,
                _pose(slot),
                [-0.035, -0.035, -0.01],
                [0.035, 0.035, 0.03],
                (0, 1),
            )["pass_support_footprint"]
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor)
            )
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor + 1)
            )
            _must_action(
                scene,
                scene.close_gripper(_arm_tag("right"), pos=0.0),
                f"{role}_close_gripper",
            )
            grasp_contact_start_row = len(scene.trace) - 1
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor + 2)
            )
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor + 3)
            )
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor + 4)
            )
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor + 5)
            )
            grasp_contact_rows = scene.trace[grasp_contact_start_row:]
            grasp_contact_flags = [
                bool(row["selected_gripper_contact"])
                for row in grasp_contact_rows
            ]
            grasp_contact_actor_names = [
                str(row["selected_contact_actor_name"])
                for row in grasp_contact_rows
            ]
            grasp_contact_fraction = float(np.mean(grasp_contact_flags))
            grasp_contact_break_count = sum(
                previous and not current
                for previous, current in zip(
                    grasp_contact_flags, grasp_contact_flags[1:]
                )
            )
            _must_action(
                scene,
                scene.open_gripper(_arm_tag("right"), pos=1.0),
                f"{role}_release",
            )
            release_trace_row = len(scene.trace) - 1
            _wait_and_record(
                scene, PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]
            )
            completion = _first_stable_slot_completion(
                scene,
                role=role,
                actor=actor,
                slot=slot,
                start_row=release_trace_row,
                required_frames=int(
                    PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]
                ),
            )
            object_final = _pose(actor)
            slot_after = footprint_inside_local_region(
                object_final,
                BLOCK_HALF_EXTENTS,
                _pose(slot),
                [-0.035, -0.035, -0.01],
                [0.035, 0.035, 0.03],
                (0, 1),
            )["pass_support_footprint"]
            completion_steps.append(completion["completion_trace_row"])
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, cursor + 6)
            )
            _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
            other_after = _position_map(others)
            other_displacement = {
                key: float(np.linalg.norm(other_after[key] - other_before[key]))
                for key in others
            }
            prior = {}
            prior_details = {}
            for previous in completed:
                prior_actor = getattr(scene, previous.lower())
                prior_slot = getattr(scene, f"slot_{previous.lower()}")
                prior_details[previous] = self._slot_state_receipt(
                    scene,
                    role=previous,
                    actor=prior_actor,
                    slot=prior_slot,
                )
                prior[previous] = prior_details[previous]["pass"]
            end_eef = _arm_eef_pose(scene, "right")
            _, block_speeds, block_support = _stable_and_support(
                scene, actor, "table"
            )
            common_x_current_footprint = footprint_inside_local_region(
                _pose(scene.common_x),
                BLOCK_HALF_EXTENTS,
                _pose(scene.tray),
                TRAY_BASE0_SUPPORT_REGION["lower_m"],
                TRAY_BASE0_SUPPORT_REGION["upper_m"],
                TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
            )["pass_support_footprint"]
            common_x_displacement = float(
                np.linalg.norm(
                    _pose(scene.common_x)[:3] - common_x_prefix_end_pose[:3]
                )
            )
            end_linear_speed = float(
                np.linalg.norm(scene.trace[-1]["eef_linear_velocity"])
            )
            end_angular_speed = float(
                np.linalg.norm(scene.trace[-1]["eef_angular_velocity"])
            )
            checks = {
                "slot_false_before": not bool(slot_before),
                "slot_true_after": bool(slot_after),
                "slot_completion_window": completion["pass"],
                "stable_after_release": bool(block_speeds)
                and max(block_speeds)
                <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
                "table_support_after_release": bool(block_support)
                and all(block_support),
                "selected_gripper_contact_continuity": grasp_contact_fraction
                >= PROVISIONAL_RUNTIME_THRESHOLDS[
                    "motion_min_contact_fraction"
                ]
                and grasp_contact_break_count
                <= PROVISIONAL_RUNTIME_THRESHOLDS[
                    "motion_max_contact_break_count"
                ],
                "selected_contact_actor_identity": bool(
                    grasp_contact_actor_names
                )
                and all(
                    name == _entity(actor).get_name()
                    for name in grasp_contact_actor_names
                ),
                "gripper_open_after": _arm_gripper_open(scene, "right"),
                "neutral_position": np.linalg.norm(
                    end_eef[:3]
                    - np.asarray(spec["targets"][cursor + 6]["pose"][:3])
                )
                <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
                "neutral_orientation": quaternion_orientation_error(
                    end_eef[3:],
                    np.asarray(spec["targets"][cursor + 6]["pose"][3:]),
                )
                <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
                "neutral_linear_stationary": end_linear_speed
                <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
                "neutral_angular_stationary": end_angular_speed
                <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
                "other_objects_stable": all(
                    value
                    <= PROVISIONAL_RUNTIME_THRESHOLDS[
                        "non_target_displacement_m"
                    ]
                    for value in other_displacement.values()
                ),
                "prior_slots_preserved": all(prior.values()),
                "common_x_preserved": bool(common_x_current_footprint)
                and common_x_displacement
                <= PROVISIONAL_RUNTIME_THRESHOLDS[
                    "non_target_displacement_m"
                ],
            }
            block_receipts.append(
                {
                    "block_id": role,
                    "start_eef_pose": start_eef.tolist(),
                    "end_eef_pose": end_eef.tolist(),
                    "object_initial_pose": object_initial.tolist(),
                    "object_final_pose": object_final.tolist(),
                    "slot_predicate_before": bool(slot_before),
                    "slot_predicate_after": bool(slot_after),
                    "other_object_displacement_m": other_displacement,
                    "prior_slot_predicates_after": prior,
                    "prior_slot_state_receipts_after": prior_details,
                    "completion_step": completion_steps[-1],
                    "completion_receipt": completion,
                    "selected_gripper_contact_fraction": grasp_contact_fraction,
                    "selected_gripper_contact_break_count": int(
                        grasp_contact_break_count
                    ),
                    "selected_contact_actor_names": grasp_contact_actor_names,
                    "common_x_displacement_m": common_x_displacement,
                    "common_x_tray_footprint_after": bool(
                        common_x_current_footprint
                    ),
                    "checks": checks,
                    "pass": all(checks.values()),
                }
            )
            completed.append(role)
            cursor += len(F4_SEGMENTED_BLOCK_SUFFIXES)
        order = [item["block_id"] for item in block_receipts]
        expected = spec["object_order"]
        expected_roles = list(spec["object_order"])
        final_slot_receipts = {
            role: self._slot_state_receipt(
                scene,
                role=role,
                actor=getattr(scene, role.lower()),
                slot=getattr(scene, f"slot_{role.lower()}"),
            )
            for role in expected_roles
        }
        final_slots = {
            role: receipt["pass"]
            for role, receipt in final_slot_receipts.items()
        }
        final_common_footprint = footprint_inside_local_region(
            _pose(scene.common_x),
            BLOCK_HALF_EXTENTS,
            _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"],
            TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        final_common_rows, final_common_speeds, final_common_contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
        final_common_angular_speeds = [
            float(np.linalg.norm(row["actor_angular_velocity"]))
            for row in final_common_rows
        ]
        final_common_checks = {
            "tray_footprint": final_common_footprint["pass_support_footprint"],
            "stable_window": bool(final_common_speeds)
            and max(final_common_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
            and bool(final_common_angular_speeds)
            and max(final_common_angular_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "support_contact_window": bool(final_common_contacts)
            and all(final_common_contacts),
            "displacement": float(
                np.linalg.norm(
                    _pose(scene.common_x)[:3] - common_x_prefix_end_pose[:3]
                )
            )
            <= PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"],
        }
        checks = {
            "common_prefix": all(common_checks.values()),
            "expected_blocks_executed": len(block_receipts)
            == len(expected_roles),
            "block_order": order == expected,
            "all_blocks_pass": all(item["pass"] for item in block_receipts),
            "all_expected_final_slots": all(final_slots.values()),
            "common_x_preserved_after_all_blocks": all(
                final_common_checks.values()
            ),
            "completion_strictly_ordered": all(
                isinstance(item, int) for item in completion_steps
            )
            and all(
                left < right
                for left, right in zip(completion_steps, completion_steps[1:])
            ),
            "noninterference": all(
                item["checks"]["prior_slots_preserved"]
                for item in block_receipts
            ),
        }
        semantic = {
            "pass": all(checks.values()),
            "checks": checks,
            "common_x_checks": common_checks,
            "common_tray_footprint": common_footprint,
            "common_support_window": common_contacts,
            "final_common_x_checks": final_common_checks,
            "final_common_tray_footprint": final_common_footprint,
            "block_receipts": block_receipts,
            "final_slot_predicates": final_slots,
            "final_slot_state_receipts": final_slot_receipts,
            "suffix_segment_execution_receipts": execution_receipts,
            "preflight_rollout_same_control_cache": True,
            "common_prefix_replayed_from_artifact": True,
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=replay,
            semantic_verifier=semantic,
            extra={
                "final_state_equivalence_payload": {
                    "common_x_pose": _pose(scene.common_x).tolist(),
                    "A_pose": _pose(scene.a).tolist(),
                    "B_pose": _pose(scene.b).tolist(),
                    "C_pose": _pose(scene.c).tolist(),
                    "executing_eef_pose": _arm_eef_pose(
                        scene, "right"
                    ).tolist(),
                    "executing_gripper_open": _arm_gripper_open(
                        scene, "right"
                    ),
                    "execution_arm": "right",
                }
            },
        )


CONTROLLERS = {
    "F1": F1ControllerV3_3(),
    "F2": F2ControllerV3_3(),
    "F3": F3ControllerV3_3(),
    "F4": F4ControllerV3_3(),
}


def get_family_controller_v3_3(family: str) -> FamilyControllerV3_3:
    if family not in CONTROLLERS:
        raise ValueError(f"runtime-v3_3 controller not implemented for {family}")
    return CONTROLLERS[family]
