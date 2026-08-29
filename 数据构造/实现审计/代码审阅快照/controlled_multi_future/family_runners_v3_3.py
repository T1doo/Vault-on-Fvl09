"""Strict-prefix family controllers for runtime-v3_3."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .current_hasher import hash_array, hash_json
from .families import F4SubtaskOrder
from .f2_mutually_exclusive_region_layout_v2 import (
    BESIDE_SECTORS_RELATIVE_XY_M,
    LAYOUT as F2_LAYOUT_V2,
    LAYOUT_VERSION as F2_LAYOUT_VERSION_V2,
)
from .family_runners_v3_1 import (
    BLOCK_HALF_EXTENTS,
    F3_H_NOMINAL_AMPLITUDE_M_V3_3,
    F3_V_NOMINAL_AMPLITUDE_M_V3_3,
    MINIMUM_NEUTRAL_CONFIRMATION_STEPS,
    _actor_half_extents,
    _arm_eef_pose,
    _arm_gripper_open,
    _arm_tag,
    _arm_tag_left,
    _entity,
    _execute_control,
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
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    footprint_inside_local_region,
    quaternion_orientation_error,
    relative_pose,
    world_axis_offset_pose,
    world_z_yaw_pose,
)
from .planner_dtype_v3_2 import planner_array
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
from .signals import closed_loop_event_metrics, top_surface_region
from .verifiers import (
    verify_realized_motion_metrics,
    verify_staged_non_target_displacement,
    verify_true_cavity_obb,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLANNER_SEED = 20260828
SUFFIX_CACHE_ATTRIBUTE = "_cmf_v3_3_suffix_control_cache"


def _raw_result(*args, **kwargs):
    kwargs["implementation_version"] = "controlled_multi_future_runtime_v3_3"
    return _legacy_raw_result(*args, **kwargs)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def planner_source_hash_v3_3() -> str:
    return hash_json(
        {
            "envs/robot/planner.py": _sha256_file(
                PROJECT_ROOT / "envs/robot/planner.py"
            ),
            "family_runners_v3_1.py": _sha256_file(
                Path(__file__).with_name("family_runners_v3_1.py")
            ),
            "family_runners_v3_3.py": _sha256_file(Path(__file__)),
        }
    )


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
        "action_interval_start_timestamps": starts,
        "action_interval_end_timestamps": starts + 1.0 / 250.0,
    }


def _settle_prefix_with_replay_operator(scene, steps: int) -> None:
    if not hasattr(scene, "replay_effective_setpoint_step"):
        raise RuntimeError("prefix settling requires the exact replay transition operator")
    last = scene.trace[-1]
    effective = np.asarray(last["effective_setpoint"], dtype=np.float64).copy()
    requested = np.asarray(last["requested_command"], dtype=np.float64).copy()
    mask = np.asarray(last["component_mask"], dtype=bool).copy()
    for _ in range(int(steps)):
        scene.replay_effective_setpoint_step(
            effective,
            requested_command=requested,
            component_mask=mask,
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
        },
    }
    if extra:
        result.update(dict(extra))
    return result


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
    start_hash = hash_array(raw_actual_qpos)
    reset = _planner_reset(
        scene,
        planner_seed=PLANNER_SEED,
        variant_id=f"v3_3_suffix:{program_id}",
        arm=arm,
    )
    planned = _plan_chain(scene, targets, query_limit=query_limit, arm=arm)
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
        "planner_query_count": int(planned["planner_query_count"]),
        "failure_type": None if planned["pass"] else "chained_suffix_planner_failure",
        "evidence": {
            "planner_reset_receipt": reset,
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
    start_qpos_max_error = float(
        np.max(np.abs(start_qpos - planned_start_qpos))
    )
    if start_qpos_max_error > 1e-5:
        raise RuntimeError(
            f"frozen suffix segment {target['segment_id']} start qpos differs from preflight"
        )
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
    terminal_qpos_max_error = float(
        np.max(np.abs(end_qpos - planned_end_qpos))
    )
    if terminal_qpos_max_error > 0.02:
        raise RuntimeError(
            f"frozen suffix segment {target['segment_id']} terminal qpos tracking failed"
        )
    realized = _arm_eef_pose(scene, arm)
    goal = np.asarray(target["pose"], dtype=np.float64)
    return {
        "segment_id": target["segment_id"],
        "start_qpos_sha256": hash_array(start_qpos),
        "planned_start_qpos_sha256": planned_receipt["start_qpos_sha256"],
        "start_qpos_max_error_rad": start_qpos_max_error,
        "start_qpos_tolerance_rad": 1e-5,
        "actual_terminal_qpos_sha256": hash_array(end_qpos),
        "planned_terminal_qpos_sha256": planned_receipt["end_qpos_sha256"],
        "terminal_qpos_max_error_rad": terminal_qpos_max_error,
        "terminal_qpos_tolerance_rad": 0.02,
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


def _prefix_physical_acceptance(
    scene,
    *,
    roles: Sequence[str],
    require_selected_contact: bool,
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
        if role_pose is None or role_velocity is None:
            raise ValueError(f"F4 completion trace lacks role stream {role}")
        footprint = footprint_inside_local_region(
            role_pose,
            BLOCK_HALF_EXTENTS,
            slot_pose,
            [-0.035, -0.035, -0.01],
            [0.035, 0.035, 0.03],
            (0, 1),
        )["pass_support_footprint"]
        stable = float(np.linalg.norm(role_velocity)) <= float(
            PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
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
        active = bool(footprint and stable and support)
        streak = streak + 1 if active else 0
        frame_evidence.append(
            {
                "trace_row": row_index,
                "footprint": bool(footprint),
                "stable": bool(stable),
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
        "definition": "first post-release frame of a consecutive footprint+stable+table-support window",
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
            comparative[role] = {
                "planner_solvable": item.get("planner_solvable"),
                "terminal_qpos": spec.get("terminal_qpos"),
                "terminal_qpos_sha256": spec.get("terminal_qpos_sha256"),
                "terminal_joint_limit_margin_rad": spec.get(
                    "terminal_joint_limit_margin_rad"
                ),
                "minimum_terminal_joint_limit_margin_rad": spec.get(
                    "minimum_terminal_joint_limit_margin_rad"
                ),
                "terminal_qpos_within_joint_limits": spec.get(
                    "terminal_qpos_within_joint_limits"
                ),
                "planner_collision_check_source": item.get("evidence", {}).get(
                    "planner_collision_check_source"
                ),
                "quantitative_collision_clearance_available": item.get(
                    "evidence", {}
                ).get("quantitative_collision_clearance_available"),
                "comparative_reachability": spec.get(
                    "comparative_reachability"
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
            "uniform_rule": "top-down grasp + common 4cm+4cm lift + common container target construction",
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
        all_targets, extra = self.legacy.build_targets(
            scene, program, {"variant_id": "v3_3_uniform_8cm_lift"}
        )
        targets = all_targets[1:]
        role = program["target_role"]
        actor_pose = _pose(getattr(scene, role))
        grasp_pose = np.asarray(all_targets[2]["pose"], dtype=np.float64)
        eef_to_actor = relative_pose(grasp_pose, actor_pose)
        carried_actor_poses = {
            item["segment_id"]: compose_pose(item["pose"], eef_to_actor)
            for item in all_targets[3:8]
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
        return _cache_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="left",
            targets=targets,
            query_limit=16,
            extra={
                **extra,
                "target_role": role,
                "comparative_reachability": comparative,
            },
        )

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
        execution_receipts = []
        execution_receipts.append(_execute_cached_segment(scene, spec, controls, 0))
        execution_receipts.append(_execute_cached_segment(scene, spec, controls, 1))
        _must_action(
            scene,
            scene.close_gripper(_arm_tag_left(), pos=0.0),
            f"{role}_close_gripper",
        )
        stages["after_grasp"] = _position_map(non_targets)
        for index in range(2, 8):
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, index)
            )
        stages["after_transport"] = _position_map(non_targets)
        _must_action(
            scene, scene.open_gripper(_arm_tag_left(), pos=1.0), f"{role}_release"
        )
        _wait_and_record(scene, 75)
        stages["after_release"] = _position_map(non_targets)
        for index in range(8, 10):
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, index)
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
        _, speeds, contacts = _stable_and_support(scene, actor, scene.box)
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
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
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
            extra_checks={
                "prefix_end_equivalent": replay["prefix_end_equivalent"],
                "grasp_transform_translation_stable": translation_drift <= 0.005,
                "grasp_transform_orientation_stable": orientation_drift <= 0.05,
            },
        )
        result["grasp_transform_translation_drift_m"] = translation_drift
        result["grasp_transform_orientation_drift_rad"] = orientation_drift
        return result

    def _require_layout_v2(self, scene):
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
            "can_xyz": _pose(scene.can)[:3],
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
        return {"layout_version": F2_LAYOUT_VERSION_V2, "layout_sha256": hash_json(expected)}

    def audit_task_physical_feasibility(self, scene, program):
        receipt = dict(super().audit_task_physical_feasibility(scene, program))
        try:
            layout = self._require_layout_v2(scene)
        except BaseException as exc:
            receipt.update(
                {
                    "task_feasible": False,
                    "physical_feasible": False,
                    "failure_type": "f2_frozen_layout_mismatch",
                    "evidence": {"error": str(exc)},
                }
            )
            return receipt
        receipt.setdefault("evidence", {})["frozen_layout"] = layout
        return receipt

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
        _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id="f2_canonical_prefix_once",
            arm="left",
        )
        pregrasp, grasp = scene.choose_grasp_pose(
            scene.can,
            arm_tag=_arm_tag_left(),
            pre_dis=0.08,
            target_dis=0,
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
                "prefix_physical_acceptance": prefix_acceptance,
            },
        )

    def _target_actor(self, scene, program):
        relation = program["steps"][1]["relation"]
        current = _pose(scene.can)
        target = current.copy()
        variant_id = "default"
        if relation == "inside":
            target = compose_pose(
                _pose(scene.box),
                [
                    *F2_PLASTICBOX_BASE2_CAVITY["target_center_local_m"],
                    *F2_INSIDE_LOCAL_QUATERNION_WXYZ,
                ],
            )
            variant_id = "inside_staged_world_z_v1"
        elif relation == "on":
            target[:3] = np.asarray(
                scene.scale.get_functional_point(0), dtype=np.float64
            )[:3]
            variant_id = "on_scale_frozen_target_v1"
        elif relation == "beside":
            target = np.asarray(
                [
                    *(
                        np.asarray(F2_LAYOUT_V2["stand_xyz"][:2], dtype=np.float64)
                        + np.asarray(BESIDE_SECTORS_RELATIVE_XY_M[-1], dtype=np.float64)
                    ),
                    float(F2_LAYOUT_V2["can_xyz"][2]),
                    0.5,
                    0.5,
                    0.5,
                    0.5,
                ],
                dtype=np.float64,
            )
            variant_id = "beside_sector_2_yaw_0_v2"
        else:
            raise ValueError("unknown F2 relation")
        return relation, target, variant_id

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        self._require_layout_v2(scene)
        relation, target_actor, variant_id = self._target_actor(scene, program)
        current_eef = _arm_eef_pose(scene, "left")
        current_actor = _pose(scene.can)
        release = actor_target_to_eef_pose(
            current_eef, current_actor, target_actor
        )
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        if relation == "inside":
            offsets = (0.10, 0.06, 0.03, 0.0)
            targets = [
                {
                    "segment_id": f"inside_descend_{int(offset * 100):02d}cm",
                    "pose": world_axis_offset_pose(release, offset),
                }
                for offset in offsets
            ]
            release_index = len(targets) - 1
            targets.extend(
                {
                    "segment_id": f"inside_retreat_{int(offset * 100):02d}cm",
                    "pose": world_axis_offset_pose(release, offset),
                }
                for offset in (0.03, 0.06, 0.10)
            )
        else:
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
                "variant_id": variant_id,
                "target_actor_pose": target_actor.tolist(),
                "release_target_index": release_index,
                "layout_version": F2_LAYOUT_VERSION_V2,
                "inside_full_obb_verifier_relaxed": False,
            },
        )

    def execute_frozen_suffix_spec(
        self, scene, program, spec, replay, realization_spec
    ):
        def release_sample(label):
            row = scene.trace[-1]
            can_pose_value = _pose(scene.can)
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
                "can_linear_velocity": np.asarray(
                    row["actor_linear_velocity"], dtype=np.float64
                ).tolist(),
                "can_angular_velocity": np.asarray(
                    row["actor_angular_velocity"], dtype=np.float64
                ).tolist(),
                "full_obb_inside": verify_true_cavity_obb(
                    can_pose_value,
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
        execution_receipts = []
        staged_inside_gates = []
        inside_release_samples = {}
        for index in range(release_index + 1):
            execution_receipts.append(
                _execute_cached_segment(scene, spec, controls, index)
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
                            _pose(scene.can),
                            _actor_half_extents(scene.can),
                            _pose(scene.box),
                            F2_PLASTICBOX_BASE2_CAVITY,
                        )["pass_true_cavity_obb"],
                    }
                staged_inside_gates.append(gate)
                if gate["selected_gripper_contact"] is not True:
                    raise RuntimeError(
                        f"F2 inside staged descent lost selected-gripper contact at {gate['segment_id']}"
                    )
                if index == release_index and gate["full_obb_inside"] is not True:
                    raise RuntimeError(
                        "F2 inside staged descent reached release without full OBB inside cavity"
                    )
        if spec["relation"] == "inside":
            inside_release_samples["before_release"] = release_sample(
                "before_release"
            )
        _must_action(
            scene,
            scene.open_gripper(_arm_tag_left(), pos=1.0),
            f"f2_{spec['relation']}_release",
        )
        if spec["relation"] == "inside":
            sample_steps = {1, 5, 10, 25, 50, 125}
            for step in range(1, 126):
                _wait_and_record(scene, 1)
                if step in sample_steps:
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
        can_half = _actor_half_extents(scene.can)
        inside = verify_true_cavity_obb(
            can_pose,
            can_half,
            _pose(scene.box),
            F2_PLASTICBOX_BASE2_CAVITY,
        )["pass_true_cavity_obb"]
        scale_target = np.asarray(
            scene.scale.get_functional_point(0), dtype=np.float64
        )
        on = top_surface_region(
            can_pose[:3], scale_target[:3], [0.07, 0.07], 0.06
        )
        radial = float(
            np.linalg.norm(
                can_pose[:2] - np.asarray(scene.stand.get_pose().p[:2])
            )
        )
        beside = bool(
            0.12 <= radial <= 0.23
            and can_pose[2] <= 0.83
            and not inside
            and not on
        )
        support_actor = scene.box if inside else scene.scale if on else "table"
        _, speeds, support = _stable_and_support(
            scene, scene.can, support_actor
        )
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
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
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
        }
        semantic = {
            "pass": all(checks.values()),
            "checks": checks,
            "exclusive_relations": exclusive,
            "target_relation": relation,
            "staged_inside_gates": staged_inside_gates,
            "suffix_segment_execution_receipts": execution_receipts,
            "preflight_rollout_same_control_cache": True,
            "inside_full_obb_verifier_relaxed": False,
            "inside_release_dynamics_samples": inside_release_samples,
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
        post_close = _replay_boundary_transform(scene, replay, "post_close")
        current = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.bottle)
        )
        translation_drift = float(np.linalg.norm(current[:3] - post_close[:3]))
        orientation_drift = quaternion_angular_error(
            current[3:], post_close[3:]
        )
        result = _prefix_physical_acceptance(
            scene,
            roles=("bottle",),
            require_selected_contact=True,
            extra_checks={
                "prefix_end_equivalent": replay["prefix_end_equivalent"],
                "shared_first_v_realized_motion": motion["pass"],
                "grasp_transform_translation_stable": translation_drift <= 0.005,
                "grasp_transform_orientation_stable": orientation_drift <= 0.05,
            },
        )
        result.update(
            {
                "shared_first_v_metrics": metrics,
                "shared_first_v_gate": motion,
                "grasp_transform_translation_drift_m": translation_drift,
                "grasp_transform_orientation_drift_rad": orientation_drift,
            }
        )
        return result

    def canonical_prefix_contract(self, programs):
        return {
            "prefix_id": "f3_grasp_lift_central_shared_first_v_v3_3",
            "family": "F3",
            "arm": "left",
            "ops": [
                "pregrasp",
                "grasp",
                "close",
                "lift_4cm",
                "lift_8cm",
                "central",
                "shared_first_V",
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
        _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id="f3_canonical_prefix_once",
            arm="left",
        )
        pregrasp, grasp = scene.choose_grasp_pose(
            scene.bottle,
            arm_tag=_arm_tag_left(),
            pre_dis=0.09,
            target_dis=0,
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
        central = np.concatenate(
            ([-0.08, -0.05, 0.95], np.asarray(grasp, dtype=np.float64)[3:])
        )
        _move_left(scene, central, "f3_prefix_central")
        post_central = len(scene.trace) - 1 - start
        v_start = len(scene.trace) - 1 - start
        positive = central.copy()
        positive[2] += F3_V_NOMINAL_AMPLITUDE_M_V3_3
        negative = central.copy()
        negative[2] -= F3_V_NOMINAL_AMPLITUDE_M_V3_3
        scene.mark("event_0_V_start")
        _move_left(scene, positive, "f3_shared_V_positive")
        _move_left(scene, negative, "f3_shared_V_negative")
        _move_left(scene, central, "f3_shared_V_return")
        scene.mark("event_0_V_end")
        v_end = len(scene.trace) - 1 - start
        post_shared = v_end
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
        grasp_translation_drift = float(
            np.linalg.norm(acceptance_transform[:3] - post_close_transform[:3])
        )
        grasp_orientation_drift = quaternion_angular_error(
            acceptance_transform[3:], post_close_transform[3:]
        )
        shared_v_gate = verify_realized_motion_metrics(
            {"event_0_V": first_v_metrics}, PROVISIONAL_RUNTIME_THRESHOLDS
        )
        prefix_acceptance = _prefix_physical_acceptance(
            scene,
            roles=("bottle",),
            require_selected_contact=True,
            extra_checks={
                "shared_first_v_realized_motion": shared_v_gate["pass"],
                "grasp_transform_translation_stable": grasp_translation_drift
                <= 0.005,
                "grasp_transform_orientation_stable": grasp_orientation_drift
                <= 0.05,
            },
        )
        prefix_acceptance.update(
            {
                "shared_first_v_metrics": first_v_metrics,
                "shared_first_v_gate": shared_v_gate,
                "grasp_transform_translation_drift_m": grasp_translation_drift,
                "grasp_transform_orientation_drift_rad": grasp_orientation_drift,
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
                    "post_central": post_central,
                    "shared_first_v_start": v_start,
                    "shared_first_v_end": v_end,
                    "post_shared_V": post_shared,
                },
                "reference_shared_first_v_metrics": first_v_metrics,
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
            vector = np.zeros(3, dtype=np.float64)
            vector[0 if axis == "H" else 2] = amplitude
            positive = center.copy()
            positive[:3] += vector
            negative = center.copy()
            negative[:3] -= vector
            start_index = len(targets)
            targets.extend(
                [
                    {
                        "segment_id": f"suffix_event_{event_index}_{axis}_positive",
                        "pose": positive,
                    },
                    {
                        "segment_id": f"suffix_event_{event_index}_{axis}_negative",
                        "pose": negative,
                    },
                    {
                        "segment_id": f"suffix_event_{event_index}_{axis}_return",
                        "pose": center.copy(),
                    },
                ]
            )
            event_groups.append(
                {
                    "event_index": event_index,
                    "axis": axis,
                    "target_start_index": start_index,
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
        execution_receipts = []
        for group in spec["event_groups"]:
            index = int(group["target_start_index"])
            axis = group["axis"]
            event_index = int(group["event_index"])
            event_center_row = len(scene.trace) - 1
            scene.mark(f"event_{event_index}_{axis}_start")
            for offset in range(3):
                execution_receipts.append(
                    _execute_cached_segment(
                        scene, spec, controls, index + offset
                    )
                )
            scene.mark(f"event_{event_index}_{axis}_end")
            metrics[f"event_{event_index}_{axis}"] = _realized_event_metrics(
                scene.trace[event_center_row:], axis=axis
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
        _, speeds, contacts = _stable_and_support(
            scene, scene.bottle, scene.pad
        )
        samples["after_rest"] = self.legacy._release_sample(
            scene,
            target_pose,
            eef_target=spec["targets"][return_start + 3]["pose"],
            stable_window_pass=bool(speeds)
            and max(speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            support_window_pass=bool(contacts) and all(contacts),
        )
        transforms = {
            name: self._boundary_transform(scene, replay, name).tolist()
            for name in (
                "post_close",
                "post_lift",
                "post_central",
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
            "return_equivalence": diagnosis["final_return_equivalence"],
            "realized_motion": motion["pass"],
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
            },
        )
        return targets, extra

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
        _, common_speeds, common_contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
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
        all_targets, extra = self.legacy.build_targets(
            scene,
            program,
            {"variant_id": "route1_minimum_height_segmented"},
        )
        targets = all_targets[9:]
        return _cache_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="right",
            targets=targets,
            query_limit=64,
            extra={
                "object_order": extra["object_order"],
                "object_target_groups": extra["object_target_groups"],
                "common_prefix_artifact_required": True,
            },
        )

    def plan_diagnostic_blocks_from_actual_prefix_end_state(
        self, scene, roles, replay
    ):
        roles = list(roles)
        if not roles or any(role not in ("A", "B", "C") for role in roles):
            raise ValueError("F4 diagnostic block roles are invalid")
        if len(set(roles)) != len(roles):
            raise ValueError("F4 diagnostic block roles must be unique")
        base_program = F4SubtaskOrder().checked_provisional_programs()[0]
        all_targets, extra = self.legacy.build_targets(
            scene,
            base_program,
            {"variant_id": "route1_minimum_height_segmented"},
        )
        suffix_targets = all_targets[9:]
        group_by_role = {
            group["role"]: (index, group)
            for index, group in enumerate(extra["object_target_groups"])
        }
        targets = []
        groups = []
        for role in roles:
            source_index, source_group = group_by_role[role]
            start = source_index * 6
            targets.extend(suffix_targets[start : start + 6])
            groups.append({**source_group, "target_start_index": len(targets) - 6})
        return _cache_suffix_controls(
            scene,
            program_id="F4-DIAG-" + "".join(roles),
            arm="right",
            targets=targets,
            query_limit=64,
            extra={
                "object_order": roles,
                "object_target_groups": groups,
                "common_prefix_artifact_required": True,
                "diagnostic_block_gate": True,
            },
        )

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
        _, common_speeds, common_contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
        common_checks = {
            "tray_footprint": common_footprint["pass_support_footprint"],
            "stable_window": bool(common_speeds)
            and max(common_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
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
            grasp_contact_rows = scene.trace[grasp_contact_start_row:]
            grasp_contact_flags = [
                bool(row["selected_gripper_contact"])
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
                _execute_cached_segment(scene, spec, controls, cursor + 5)
            )
            _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
            other_after = _position_map(others)
            other_displacement = {
                key: float(np.linalg.norm(other_after[key] - other_before[key]))
                for key in others
            }
            prior = {}
            for previous in completed:
                prior_actor = getattr(scene, previous.lower())
                prior_slot = getattr(scene, f"slot_{previous.lower()}")
                prior[previous] = footprint_inside_local_region(
                    _pose(prior_actor),
                    BLOCK_HALF_EXTENTS,
                    _pose(prior_slot),
                    [-0.035, -0.035, -0.01],
                    [0.035, 0.035, 0.03],
                    (0, 1),
                )["pass_support_footprint"]
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
                "gripper_open_after": _arm_gripper_open(scene, "right"),
                "neutral_position": np.linalg.norm(
                    end_eef[:3]
                    - np.asarray(spec["targets"][cursor + 5]["pose"][:3])
                )
                <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
                "neutral_orientation": quaternion_orientation_error(
                    end_eef[3:],
                    np.asarray(spec["targets"][cursor + 5]["pose"][3:]),
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
                    "completion_step": completion_steps[-1],
                    "completion_receipt": completion,
                    "selected_gripper_contact_fraction": grasp_contact_fraction,
                    "selected_gripper_contact_break_count": int(
                        grasp_contact_break_count
                    ),
                    "common_x_displacement_m": common_x_displacement,
                    "common_x_tray_footprint_after": bool(
                        common_x_current_footprint
                    ),
                    "checks": checks,
                    "pass": all(checks.values()),
                }
            )
            completed.append(role)
            cursor += 6
        order = [item["block_id"] for item in block_receipts]
        expected = spec["object_order"]
        expected_roles = list(spec["object_order"])
        final_slots = {
            role: footprint_inside_local_region(
                _pose(getattr(scene, role.lower())),
                BLOCK_HALF_EXTENTS,
                _pose(getattr(scene, f"slot_{role.lower()}")),
                [-0.035, -0.035, -0.01],
                [0.035, 0.035, 0.03],
                (0, 1),
            )["pass_support_footprint"]
            for role in expected_roles
        }
        final_common_footprint = footprint_inside_local_region(
            _pose(scene.common_x),
            BLOCK_HALF_EXTENTS,
            _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"],
            TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        _, final_common_speeds, final_common_contacts = _stable_and_support(
            scene, scene.common_x, scene.tray
        )
        final_common_checks = {
            "tray_footprint": final_common_footprint["pass_support_footprint"],
            "stable_window": bool(final_common_speeds)
            and max(final_common_speeds)
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
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
