"""Concrete, bounded RoboTwin family runners for runtime-v3_1.

The runners are wired to real ``Base_Task``/planner/actor APIs but are not
authorized to execute yet.  CPU tests exercise their immutable routing and
chained-planner helpers with fakes; real SAPIEN evidence remains absent until a
later explicit A0/action-probe authorization.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .current_hasher import hash_array, hash_json
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    footprint_inside_local_region,
    quaternion_angular_velocity,
    quaternion_orientation_error,
    relative_pose,
    swept_path_collisions,
    transform_local_point,
    world_axis_offset_pose,
    world_z_yaw_pose,
)
from .probes.runtime_trace import _rigid_velocity, trace_rows_to_raw_streams
from .planner_dtype_v3_2 import normalize_planner_control, planner_array, planner_dtype_receipt
from .project_cube_grasp_pose_v1 import build_project_cube_grasp_poses
from .runtime_v2_contracts import PLASTICBOX_BASE3_CAVITY, PROVISIONAL_RUNTIME_THRESHOLDS, TRAY_BASE0_SUPPORT_REGION
from .runtime_v3_1_contracts import (
    F2_CANDIDATE_IDS,
    F3_PAD_HALF_SIZE_M,
    F4_ROUTE_ORDER,
    classify_f3_release_dynamics_v3_1,
    minimum_f4_safe_carry_height,
)
from .runtime_v3_2_contracts import (
    F2_INSIDE_LOCAL_QUATERNION_WXYZ,
    F2_PLASTICBOX_BASE2_CAVITY,
)
from .signals import closed_loop_event_metrics, top_surface_region
from .verifiers import (
    verify_beside_final_state,
    verify_common_prefix,
    verify_realized_motion_metrics,
    verify_return_equivalence,
    verify_staged_non_target_displacement,
    verify_true_cavity_obb,
)


BLOCK_HALF_EXTENTS = np.asarray([0.022, 0.022, 0.022], dtype=np.float64)
FAMILY_PLANNER_LIMITS = {"F1": 12, "F2": 16, "F3": 16, "F4": 16}
FAMILY_FULL_PROGRAM_PLANNER_LIMITS = {"F3": 32, "F4": 32}
MINIMUM_NEUTRAL_CONFIRMATION_STEPS = 1
F3_V_NOMINAL_AMPLITUDE_M_V3_3 = 0.055
F3_H_NOMINAL_AMPLITUDE_M_V3_3 = 0.05


class FamilyRunnerError(RuntimeError):
    pass


class PlannerChainFailure(FamilyRunnerError):
    pass


def _arm_tag_left():
    from envs.utils.action import ArmTag

    return ArmTag("left")


def _arm_tag(arm: str):
    from envs.utils.action import ArmTag

    if arm not in ("left", "right"):
        raise ValueError("execution arm must be left or right")
    return ArmTag(arm)


def _execution_arm(scene) -> str:
    planned = getattr(scene, "_cmf_planned_root_slot_spec", {})
    arm = planned.get("arm", "left") if isinstance(planned, Mapping) else "left"
    if arm not in ("left", "right"):
        raise ValueError("planned root execution arm must be left or right")
    return arm


def _arm_entity(scene, arm: str):
    return getattr(scene.robot, f"{arm}_entity")


def _arm_original_pose(scene, arm: str):
    return np.asarray(getattr(scene.robot, f"{arm}_original_pose"), dtype=np.float64)


def _arm_eef_pose(scene, arm: str):
    return np.asarray(getattr(scene.robot, f"get_{arm}_ee_pose")(), dtype=np.float64)


def _arm_gripper_open(scene, arm: str) -> bool:
    return bool(getattr(scene, f"is_{arm}_gripper_open")())


def _entity(actor):
    return actor.actor if hasattr(actor, "actor") else actor


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _position_map(actors):
    return {name: np.asarray(actor.get_pose().p, dtype=np.float64).copy() for name, actor in actors.items()}


def _targets_by_segment_id(targets):
    result = {item["segment_id"]: item for item in targets}
    if len(result) != len(targets):
        raise ValueError("planner execution targets require unique segment IDs")
    return result


def _settle(scene, frames=60):
    for _ in range(frames):
        scene.scene.step()


def _wait_and_record(scene, frames):
    for _ in range(frames):
        scene.scene.step()
        scene._record()


def _must_action(scene, action, label):
    if not scene.move(action) or not scene.plan_success:
        raise PlannerChainFailure(f"planner/execution failed at {label}")


def _execute_control(scene, control, label, *, arm="left"):
    if not isinstance(control, Mapping) or control.get("status") != "Success":
        raise PlannerChainFailure(f"planner control failed at {label}")
    normalized = normalize_planner_control(control)
    control_seq = {"left_arm": None, "left_gripper": None, "right_arm": None, "right_gripper": None}
    control_seq[f"{arm}_arm"] = normalized
    scene.take_dense_action(control_seq)


def _move_arm(scene, pose, label, *, arm="left"):
    control = getattr(scene, f"{arm}_move_to_pose")(
        pose=planner_array(pose, shape=(7,), label=f"{label} goal pose")
    )
    _execute_control(scene, control, label, arm=arm)
    return control


def _move_left(scene, pose, label):
    return _move_arm(scene, pose, label, arm="left")


def _planner_reset(scene, *, planner_seed: int, variant_id: str, arm="left") -> dict:
    robot = scene.robot
    reset_source = None
    if getattr(robot, "communication_flag", False):
        connection = getattr(robot, f"{arm}_conn")
        connection.send({"cmd": "reset"})
        response = connection.recv()
        if response != "ok":
            raise PlannerChainFailure(f"left planner reset failed: {response}")
        reset_source = "RoboTwin planner worker cmd=reset -> MotionGen.reset(reset_seed=True)"
        planner_identity = f"worker-pid:{getattr(robot, f'{arm}_proc', None).pid}"
    else:
        planner = getattr(robot, f"{arm}_planner", None)
        motion_gen = getattr(planner, "motion_gen", None)
        if motion_gen is None or not hasattr(motion_gen, "reset"):
            raise PlannerChainFailure("left planner exposes no audited RNG reset")
        motion_gen.reset(reset_seed=True)
        reset_source = "CuroboPlanner.motion_gen.reset(reset_seed=True)"
        planner_identity = f"inprocess:{type(planner).__name__}:{id(planner)}"
    reset_payload = {
        "planner_seed": int(planner_seed),
        "reset_source": reset_source,
        "reset_seed_argument": True,
    }
    return {
        "reset_performed": True,
        "planner_seed": int(planner_seed),
        "rng_state_after_reset_sha256": hash_json(reset_payload),
        "planner_instance_id": planner_identity,
        "variant_id": variant_id,
        "arm": arm,
        "reset_evidence": reset_payload,
    }


def _ensure_planner_trace_fields(scene, limit):
    if not hasattr(scene, "planner_queries"):
        scene.planner_queries = []
    if not hasattr(scene, "planner_query_count"):
        scene.planner_query_count = 0
    scene.planner_query_limit = int(limit)


def _motiongen_audit_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if np.isfinite(value):
            return value
        return {
            "kind": "nonfinite",
            "value": "nan"
            if np.isnan(value)
            else "+inf"
            if value > 0
            else "-inf",
        }
    if isinstance(value, Mapping):
        return {
            str(key): _motiongen_audit_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_motiongen_audit_value(item) for item in value]
    current = value
    for method in ("detach", "cpu"):
        callback = getattr(current, method, None)
        if callable(callback):
            current = callback()
    item = getattr(current, "item", None)
    if callable(item):
        try:
            return _motiongen_audit_value(item())
        except (ValueError, RuntimeError):
            pass
    tolist = getattr(current, "tolist", None)
    if callable(tolist):
        try:
            return _motiongen_audit_value(tolist())
        except (ValueError, RuntimeError):
            pass
    return str(current)


def _motiongen_result_audit(result):
    fields = (
        "success",
        "status",
        "valid_query",
        "attempts",
        "used_graph",
        "position_error",
        "rotation_error",
        "solve_time",
        "total_time",
    )
    return {
        "schema_version": "cmf_motiongen_result_side_channel_v1",
        "fields": {
            field: _motiongen_audit_value(getattr(result, field, None))
            for field in fields
        },
        "source": "additive temporary wrapper around CuroboPlanner.motion_gen.plan_single",
    }


def _plan_arm(scene, pose, *, last_qpos, source, arm="left"):
    _ensure_planner_trace_fields(scene, getattr(scene, "planner_query_limit", 16))
    query_id = scene._reserve_planner_query()
    pose = planner_array(pose, shape=(7,), label=f"{source} goal pose")
    planner_qpos = planner_array(last_qpos, label=f"{source} start qpos").reshape(-1)
    planner = getattr(scene.robot, f"{arm}_planner", None)
    motion_gen = getattr(planner, "motion_gen", None)
    original_plan_single = getattr(motion_gen, "plan_single", None)
    motiongen_audits = []
    wrapper_installed = callable(original_plan_single)
    motiongen_wrapper_installation_error = None
    had_instance_override = bool(
        motion_gen is not None
        and hasattr(motion_gen, "__dict__")
        and "plan_single" in vars(motion_gen)
    )
    prior_instance_value = (
        vars(motion_gen).get("plan_single") if had_instance_override else None
    )
    motiongen_wrapper_restoration_succeeded = not wrapper_installed
    if wrapper_installed:
        def audited_plan_single(*args, **kwargs):
            result_value = original_plan_single(*args, **kwargs)
            motiongen_audits.append(_motiongen_result_audit(result_value))
            return result_value

        try:
            setattr(motion_gen, "plan_single", audited_plan_single)
        except BaseException as exc:
            wrapper_installed = False
            motiongen_wrapper_installation_error = (
                f"{type(exc).__name__}: {exc}"
            )
    body_error = None
    result = None
    try:
        result = getattr(scene.robot, f"{arm}_plan_path")(
            pose, last_qpos=planner_qpos
        )
    except BaseException as exc:
        body_error = exc
    finally:
        restoration_error = None
        if wrapper_installed:
            try:
                if had_instance_override:
                    setattr(motion_gen, "plan_single", prior_instance_value)
                else:
                    delattr(motion_gen, "plan_single")
                current_has_override = bool(
                    hasattr(motion_gen, "__dict__")
                    and "plan_single" in vars(motion_gen)
                )
                topology_restored = (
                    current_has_override == had_instance_override
                )
                callable_restored = callable(getattr(motion_gen, "plan_single", None))
                if not topology_restored or not callable_restored:
                    raise RuntimeError(
                        "MotionGen wrapper restoration topology mismatch"
                    )
                motiongen_wrapper_restoration_succeeded = True
            except BaseException as exc:
                restoration_error = exc
        if restoration_error is not None:
            raise PlannerChainFailure(
                "MotionGen side-channel wrapper restoration failed"
            ) from body_error
    if body_error is not None:
        raise body_error
    if isinstance(result, Mapping):
        result = normalize_planner_control(result)
    status = result.get("status") if isinstance(result, Mapping) else "Fail"
    item = {
        "query_id": query_id,
        "arm": arm,
        "source": source,
        "goal_eef_pose": pose.tolist(),
        "status": status,
        "start_step": None,
        "end_step": None,
        "dtype_contract": planner_dtype_receipt(
            qpos=planner_qpos,
            goal_pose=pose,
            control=result if isinstance(result, Mapping) else None,
        ),
        "motiongen_result_side_channel": motiongen_audits,
        "motiongen_side_channel_available": wrapper_installed,
        "motiongen_side_channel_call_count": len(motiongen_audits),
        "motiongen_wrapper_installation_error": motiongen_wrapper_installation_error,
        "motiongen_wrapper_had_instance_override": had_instance_override,
        "motiongen_wrapper_restoration_succeeded": (
            motiongen_wrapper_restoration_succeeded
        ),
    }
    scene.planner_queries.append(item)
    if isinstance(result, dict):
        result["_cmf_planner_query"] = dict(item)
    return result


def _plan_left(scene, pose, *, last_qpos, source):
    return _plan_arm(scene, pose, last_qpos=last_qpos, source=source, arm="left")


def _merge_arm_terminal_qpos(scene, full_start_qpos, terminal_arm_qpos, *, arm="left"):
    full = planner_array(full_start_qpos, label="full start qpos").reshape(-1).copy()
    terminal = planner_array(terminal_arm_qpos, label="terminal arm qpos").reshape(-1)
    if terminal.size == full.size:
        return terminal.copy()
    active_joints = list(_arm_entity(scene, arm).get_active_joints())
    index_by_name = {joint.get_name(): index for index, joint in enumerate(active_joints)}
    arm_names = [joint.get_name() for joint in getattr(scene.robot, f"{arm}_arm_joints")]
    if terminal.size != len(arm_names) or any(name not in index_by_name for name in arm_names):
        raise PlannerChainFailure("planner terminal qpos cannot be mapped into full left articulation state")
    for value, name in zip(terminal, arm_names):
        full[index_by_name[name]] = value
    return full


def _merge_left_arm_terminal_qpos(scene, full_start_qpos, terminal_arm_qpos):
    return _merge_arm_terminal_qpos(scene, full_start_qpos, terminal_arm_qpos, arm="left")


def _plan_chain(scene, targets: Sequence[Mapping[str, Any]], *, query_limit: int, arm="left") -> dict:
    _ensure_planner_trace_fields(scene, query_limit)
    # RoboTwin's CuRobo worker builds a tensor directly from these NumPy
    # scalars.  Preserve float32 so it cannot infer a Double start state
    # against a Float motion-generation model.
    last_qpos = planner_array(_arm_entity(scene, arm).get_qpos(), label=f"initial {arm} qpos").reshape(-1)
    segment_receipts = []
    controls = []
    for target in targets:
        start_hash = hash_array(last_qpos)
        control = _plan_arm(
            scene,
            target["pose"],
            last_qpos=last_qpos,
            source=target["segment_id"],
            arm=arm,
        )
        status = control.get("status") if isinstance(control, Mapping) else "Fail"
        if status == "Success":
            positions = planner_array(control["position"], label=f"{target['segment_id']} trajectory position")
            if positions.ndim != 2 or positions.shape[0] < 1:
                raise PlannerChainFailure(f"planner returned no qpos path at {target['segment_id']}")
            end_qpos = _merge_arm_terminal_qpos(scene, last_qpos, positions[-1], arm=arm)
            end_hash = hash_array(end_qpos)
        else:
            end_qpos = last_qpos.copy()
            end_hash = hash_array(end_qpos)
        segment_receipts.append(
            {
                "segment_id": target["segment_id"],
                "start_qpos_sha256": start_hash,
                "end_qpos_sha256": end_hash,
                "start_qpos": np.asarray(last_qpos, dtype=np.float32).tolist(),
                "end_qpos": np.asarray(end_qpos, dtype=np.float32).tolist(),
                "planner_status": status,
                "executed": False,
                "goal_eef_pose": np.asarray(target["pose"], dtype=np.float64).tolist(),
                "planner_query_receipt": dict(control["_cmf_planner_query"])
                if isinstance(control, Mapping)
                and isinstance(control.get("_cmf_planner_query"), Mapping)
                else None,
            }
        )
        controls.append(control)
        if status != "Success":
            return {
                "pass": False,
                "segment_receipts": segment_receipts,
                "controls": controls,
                "planner_query_count": scene.planner_query_count,
                "terminal_qpos": np.asarray(last_qpos, dtype=np.float32).tolist(),
                "terminal_qpos_sha256": hash_array(last_qpos),
            }
        last_qpos = end_qpos
    chain = all(
        segment_receipts[index]["start_qpos_sha256"] == segment_receipts[index - 1]["end_qpos_sha256"]
        for index in range(1, len(segment_receipts))
    )
    return {
        "pass": chain,
        "segment_receipts": segment_receipts,
        "controls": controls,
        "planner_query_count": scene.planner_query_count,
        "terminal_qpos": np.asarray(last_qpos, dtype=np.float32).tolist(),
        "terminal_qpos_sha256": hash_array(last_qpos),
    }


def _hash_prefix_actions(scene, start_action_index, end_action_index):
    rows = scene.trace[1:]
    values = np.asarray([row["effective_setpoint"] for row in rows[start_action_index:end_action_index]], dtype=np.float64)
    digest = hashlib.sha256()
    digest.update(str(values.dtype).encode("ascii"))
    digest.update(str(values.shape).encode("ascii"))
    digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _prefix_evidence(
    scene,
    *,
    target_role,
    prefix_start_action_index,
    prefix_end_action_index,
    start_anchor,
    end_anchor,
):
    return {
        "target_role": target_role,
        "target_role_visible_during_prefix": False,
        "executed_prefix_action_sha256": _hash_prefix_actions(scene, prefix_start_action_index, prefix_end_action_index),
        "executed_prefix_step_count": int(prefix_end_action_index - prefix_start_action_index),
        "executed_prefix_start_state_sha256": start_anchor["anchor_sha256"],
        "executed_prefix_end_state_sha256": end_anchor["anchor_sha256"],
        "executed_prefix_start_anchor": start_anchor,
        "executed_prefix_end_anchor": end_anchor,
        "canonical_prefix_end_step": int(prefix_end_action_index - prefix_start_action_index),
        "first_post_prefix_divergence_step": int(prefix_end_action_index - prefix_start_action_index),
        "neutral_confirmation_step_count": MINIMUM_NEUTRAL_CONFIRMATION_STEPS,
        "neutral_confirmation_minimum_required_steps": MINIMUM_NEUTRAL_CONFIRMATION_STEPS,
    }


def _raw_result(
    scene,
    *,
    program,
    realization_spec,
    executed_prefix,
    semantic_verifier,
    extra=None,
    implementation_version="controlled_multi_future_runtime_v3_1",
):
    streams, audit_streams = trace_rows_to_raw_streams(scene.trace)
    executed_prefix = dict(executed_prefix)
    prefix_end = int(executed_prefix["canonical_prefix_end_step"])
    actions = np.asarray(streams["controller_effective_setpoint"], dtype=np.float64)
    executed_prefix["post_prefix_action_step_sha256"] = [
        hashlib.sha256(np.ascontiguousarray(row).tobytes(order="C")).hexdigest()
        for row in actions[prefix_end:]
    ]
    provenance = scene.trace_provenance()
    provenance.update(
        {
            "synthetic": False,
            "program_id": program["program_id"],
            "family": program["program_id"].split("-", 1)[0],
            "realization_spec": dict(realization_spec),
            "implementation_version": implementation_version,
        }
    )
    if extra and "rollout_planner_reset_receipt" in extra:
        provenance["rollout_planner_reset_receipt"] = dict(extra["rollout_planner_reset_receipt"])
    if extra and "audit_role_mapping" in extra:
        provenance["audit_role_mapping"] = dict(extra["audit_role_mapping"])
    result = {
        "streams": streams,
        "audit_streams": audit_streams,
        "provenance": provenance,
        "executed_prefix": executed_prefix,
        "semantic_verifier": semantic_verifier,
    }
    if extra:
        result.update(extra)
    return result


def _actor_local_geometry_bounds(actor, fallback=BLOCK_HALF_EXTENTS):
    """Return asset-local AABB center and half extents in scaled metres."""

    declared = getattr(actor, "_cmf_half_extents", None)
    if declared is not None:
        value = np.asarray(declared, dtype=np.float64).reshape(3)
        if np.all(np.isfinite(value)) and np.all(value > 0):
            center = np.asarray(
                getattr(actor, "_cmf_local_geometry_center", np.zeros(3)),
                dtype=np.float64,
            ).reshape(3)
            if not np.all(np.isfinite(center)):
                raise ValueError("project procedural actor has invalid local geometry center")
            return center.copy(), value.copy()
        raise ValueError("project procedural actor has invalid declared half extents")
    config = getattr(actor, "config", None) or {}
    if "extents" in config and "scale" in config:
        scale = np.asarray(config["scale"], dtype=np.float64).reshape(3)
        half = np.asarray(config["extents"], dtype=np.float64).reshape(3) * scale / 2.0
        center = np.asarray(config.get("center", np.zeros(3)), dtype=np.float64).reshape(3) * scale
        if (
            not np.all(np.isfinite(center))
            or not np.all(np.isfinite(half))
            or not np.all(half > 0)
        ):
            raise ValueError("asset actor has invalid scaled local AABB bounds")
        return center, half
    return np.zeros(3, dtype=np.float64), np.asarray(fallback, dtype=np.float64)


def _actor_half_extents(actor, fallback=BLOCK_HALF_EXTENTS):
    return _actor_local_geometry_bounds(actor, fallback=fallback)[1]


def _actor_geometry_center_pose(actor, *, actor_pose=None, fallback=BLOCK_HALF_EXTENTS):
    center, _ = _actor_local_geometry_bounds(actor, fallback=fallback)
    pose = _pose(actor) if actor_pose is None else np.asarray(actor_pose, dtype=np.float64).reshape(7)
    return compose_pose(pose, [*center, 1.0, 0.0, 0.0, 0.0])


def _gripper_below_eef_envelope(scene, *, arm="left", conservative_link_margin_m=0.03):
    robot = scene.robot
    names = set(getattr(robot, f"{arm}_fix_gripper_name"))
    names.update(joint[0].child_link.get_name() for joint in getattr(robot, f"{arm}_gripper"))
    links = {link.get_name(): link for link in _arm_entity(scene, arm).get_links()}
    missing = sorted(names - set(links))
    if missing:
        raise ValueError(f"selected left-gripper links missing from articulation: {missing}")
    eef_z = float(_arm_eef_pose(scene, arm)[2])
    link_z = {name: float(links[name].get_pose().p[2]) for name in sorted(names)}
    below = max(0.0, eef_z - min(link_z.values())) + float(conservative_link_margin_m)
    return {
        "selected_gripper_links": sorted(names),
        "eef_world_z_m": eef_z,
        "link_world_z_m": link_z,
        "conservative_link_margin_m": float(conservative_link_margin_m),
        "gripper_below_eef_envelope_m": float(below),
        "arm": arm,
        "source": f"runtime selected {arm}-gripper link poses plus frozen conservative link margin",
    }


def _left_gripper_below_eef_envelope(scene, *, conservative_link_margin_m=0.03):
    return _gripper_below_eef_envelope(
        scene,
        arm="left",
        conservative_link_margin_m=conservative_link_margin_m,
    )


def _stable_and_support(scene, actor, support, frames=None):
    frames = int(frames or PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
    rows = scene.trace[-frames:]
    actor_name = _entity(actor).get_name()
    role = next(
        (
            key
            for key, role_actor in getattr(scene, "trace_role_actors", {}).items()
            if _entity(role_actor).get_name() == actor_name
        ),
        None,
    )
    if role is not None:
        if any(
            role not in row.get("role_actor_linear_velocities", {})
            for row in rows
        ):
            raise ValueError(f"trace lacks velocity history for role {role}")
        speeds = [
            float(np.linalg.norm(row["role_actor_linear_velocities"][role]))
            for row in rows
        ]
    elif _entity(scene.trace_actor).get_name() == actor_name:
        speeds = [
            float(np.linalg.norm(row["actor_linear_velocity"])) for row in rows
        ]
    else:
        raise ValueError(
            f"stable verifier cannot identify trace velocity stream for {actor_name}"
        )
    support_name = str(support) if isinstance(support, str) else _entity(support).get_name()
    contacts = []
    for row in rows:
        contacts.append(any(
            actor_name in (item["body_a"], item["body_b"])
            and any(support_name.lower() in str(body).lower() for body in (item["body_a"], item["body_b"]) if body != actor_name)
            for item in row["contact_pairs"]
        ))
    return rows, speeds, contacts


class BaseFamilyRunnerV3_1:
    family = None

    def build_targets(self, scene, program, planner_variant):
        raise NotImplementedError

    def planner_audit_variants(self, frozen_program):
        return [{"variant_id": "default"}]

    def audit_task_physical_feasibility(self, scene, program):
        roles_ok = isinstance(getattr(scene, "role_actors", None), Mapping) and bool(scene.role_actors)
        poses_finite = roles_ok and all(np.all(np.isfinite(_pose(actor))) for actor in scene.role_actors.values())
        program_family = str(program.get("program_id", "")).startswith(f"{self.family}-")
        passed = roles_ok and poses_finite and program_family
        return {
            "task_feasible": passed,
            "physical_feasible": passed,
            "planner_solvable": None,
            "failure_type": None if passed else "invalid_scene_roles_or_program",
            "evidence": {"roles": sorted(scene.role_actors) if roles_ok else [], "poses_finite": poses_finite, "program_family": program_family},
        }

    def audit_planner_solvability(self, scene, frozen_program, planner_variant):
        targets, extra = self.build_targets(scene, frozen_program, planner_variant)
        reset = _planner_reset(scene, planner_seed=20260828, variant_id=planner_variant["variant_id"])
        full_program = str(extra.get("execution_scope", "")).endswith("full_program_nonformal_root")
        query_limit = (
            FAMILY_FULL_PROGRAM_PLANNER_LIMITS[self.family]
            if full_program and self.family in FAMILY_FULL_PROGRAM_PLANNER_LIMITS
            else FAMILY_PLANNER_LIMITS[self.family]
        )
        planned = _plan_chain(scene, targets, query_limit=query_limit)
        execution_spec = None
        if planned["pass"]:
            execution_spec = {
                "variant_id": planner_variant["variant_id"],
                "targets": [{"segment_id": item["segment_id"], "pose": np.asarray(item["pose"], dtype=np.float64).tolist()} for item in targets],
                "planner_reset_receipt": reset,
                "preflight_segment_receipts": planned["segment_receipts"],
                **extra,
            }
        return {
            "planner_solvable": bool(planned["pass"]),
            "failure_type": None if planned["pass"] else "chained_planner_failure",
            "evidence": {"planner_reset_receipt": reset, "segment_receipts": planned["segment_receipts"]},
            "planner_query_count": int(planned["planner_query_count"]),
            "execution_spec": execution_spec,
        }

    def verify(self, fresh_scene, frozen_program, rollout_result):
        semantic = rollout_result.get("semantic_verifier")
        if not isinstance(semantic, Mapping):
            raise ValueError("family rollout emitted no semantic verifier")
        return {"pass": semantic.get("pass") is True, "family_semantic_verifier": dict(semantic)}


class F1RunnerV3_1(BaseFamilyRunnerV3_1):
    family = "F1"

    def canonical_prefix(self, programs):
        return {
            "prefix_id": "f1_cluster_common_pregrasp_v1_1",
            "target_role_visible": False,
            "ops": ["open_left_gripper", "move_left_cluster_neutral", "minimum_neutral_confirmation"],
            "extra_hold_frames_count_toward_P": False,
        }

    def audit_task_physical_feasibility(self, scene, program):
        base = super().audit_task_physical_feasibility(scene, program)
        role = program.get("target_role")
        expected = {"red", "green", "blue", "common_box"}
        block_positions = [np.asarray(getattr(scene, name).get_pose().p[:2], dtype=np.float64) for name in ("red", "green", "blue")]
        block_half_extents = {
            name: _actor_half_extents(getattr(scene, name)) for name in ("red", "green", "blue")
        }
        checks = {
            "roles": set(scene.role_actors) == expected,
            "target_role": role in ("red", "green", "blue"),
            "same_block_half_extents": all(
                np.allclose(block_half_extents[name], BLOCK_HALF_EXTENTS)
                for name in ("red", "green", "blue")
            ),
            "box_cavity_larger_than_block": bool(np.all(
                np.asarray(PLASTICBOX_BASE3_CAVITY["upper_m"]) - np.asarray(PLASTICBOX_BASE3_CAVITY["lower_m"]) > 2 * BLOCK_HALF_EXTENTS
            )),
            "initial_blocks_pairwise_separated": all(
                np.linalg.norm(block_positions[left] - block_positions[right]) >= 0.08
                for left in range(3)
                for right in range(left + 1, 3)
            ),
        }
        passed = base["task_feasible"] and all(checks.values())
        base.update({
            "task_feasible": passed,
            "physical_feasible": passed,
            "failure_type": None if passed else "f1_task_physical_contract",
            "evidence": {
                **checks,
                "block_half_extents_m": {
                    name: value.tolist() for name, value in block_half_extents.items()
                },
                "block_geometry_source": {
                    name: getattr(getattr(scene, name), "_cmf_geometry_source", "actor config extents/scale")
                    for name in ("red", "green", "blue")
                },
            },
        })
        return base

    def build_targets(self, scene, program, planner_variant):
        role = program["target_role"]
        actor = getattr(scene, role)
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        neutral = np.concatenate(([-0.11, 0.02, 0.95], rest[3:]))
        pregrasp, grasp = scene.choose_grasp_pose(actor, arm_tag=_arm_tag_left(), pre_dis=0.09, target_dis=0)
        actor_pose = _pose(actor)
        target_actor = actor_pose.copy()
        target_actor[:3] = transform_local_point(_pose(scene.box), PLASTICBOX_BASE3_CAVITY["target_center_local_m"])
        release = actor_target_to_eef_pose(grasp, actor_pose, target_actor)
        preplace = world_axis_offset_pose(release, 0.10)
        lift_mid = world_axis_offset_pose(grasp, 0.04)
        lift = world_axis_offset_pose(grasp, 0.08)
        safe = lift.copy()
        safe[2] = max(float(lift[2]), 1.02)
        above = preplace.copy()
        above[2] = safe[2]
        targets = [
            {"segment_id": "common_cluster_neutral", "pose": neutral},
            {"segment_id": "target_pregrasp", "pose": pregrasp},
            {"segment_id": "target_grasp", "pose": grasp},
            {"segment_id": "target_lift_mid", "pose": lift_mid},
            {"segment_id": "target_lift", "pose": lift},
            {"segment_id": "safe_vertical", "pose": safe},
            {"segment_id": "safe_horizontal", "pose": above},
            {"segment_id": "preplace", "pose": preplace},
            {"segment_id": "release", "pose": release},
            {"segment_id": "retreat", "pose": preplace},
            {"segment_id": "rest", "pose": rest},
        ]
        return targets, {"target_role": role, "target_actor_pose": target_actor.tolist()}

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        # Do not inspect target_role before the actual prefix boundary.  The
        # fixed red actor only identifies the generic object_pose audit stream;
        # per-role streams record all blocks and prefix commands are role-free.
        scene.initialize_trace(scene.red, "left", role_actors=scene.role_actors)
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F1"]
        rollout_reset = _planner_reset(scene, planner_seed=20260828, variant_id="f1_actual_prefix_and_branch")
        all_block_baseline = _position_map({name: getattr(scene, name) for name in ("red", "green", "blue")})
        prefix_start = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "prefix_open")
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        canonical_neutral = np.concatenate(([-0.11, 0.02, 0.95], rest[3:]))
        _move_left(scene, canonical_neutral, "common_cluster_neutral")
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        prefix_end_action = len(scene.trace) - 1
        prefix_end = anchor_capture(scene)
        role = program["target_role"]
        actor = getattr(scene, role)
        spec = realization_spec["planner_execution_spec"]
        scene.set_trace_contact_actor(actor)
        non_targets = {name: getattr(scene, name) for name in ("red", "green", "blue") if name != role}
        baseline = {name: all_block_baseline[name] for name in non_targets}
        stages = {"prefix_boundary": _position_map(non_targets)}
        executed_prefix = _prefix_evidence(
            scene,
            target_role=role,
            prefix_start_action_index=prefix_start_action,
            prefix_end_action_index=prefix_end_action,
            start_anchor=prefix_start,
            end_anchor=prefix_end,
        )
        _must_action(scene, scene.grasp_actor(actor, arm_tag=_arm_tag_left(), pre_grasp_dis=0.09), f"grasp_{role}")
        stages["after_grasp"] = _position_map(non_targets)
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.04), f"lift_mid_{role}")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.04), f"lift_final_{role}")
        stages["after_lift"] = _position_map(non_targets)
        targets = _targets_by_segment_id(spec["targets"])
        for segment_id in ("safe_vertical", "safe_horizontal", "preplace", "release"):
            target = targets[segment_id]
            _move_left(scene, target["pose"], target["segment_id"])
        stages["after_transport"] = _position_map(non_targets)
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "release")
        _wait_and_record(scene, 75)
        stages["after_release"] = _position_map(non_targets)
        _move_left(scene, targets["retreat"]["pose"], "retreat")
        stages["after_retreat"] = _position_map(non_targets)
        _move_left(scene, targets["rest"]["pose"], "rest")
        _wait_and_record(scene, 75)
        stages["after_rest"] = _position_map(non_targets)
        inside = verify_true_cavity_obb(_pose(actor), BLOCK_HALF_EXTENTS, _pose(scene.box), PLASTICBOX_BASE3_CAVITY)
        non_target = verify_staged_non_target_displacement(baseline, stages, PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"])
        _, speeds, contacts = _stable_and_support(scene, actor, scene.box)
        rest = np.asarray(targets["rest"]["pose"], dtype=np.float64)
        realized_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        rest_position_error = float(np.linalg.norm(realized_eef[:3] - rest[:3]))
        rest_orientation_error = quaternion_orientation_error(realized_eef[3:], rest[3:])
        eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
        eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
        checks = {
            "true_inside": inside["pass_true_cavity_obb"],
            "non_target": non_target["pass"],
            "stable": bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "continuous_box_contact": bool(contacts) and all(contacts),
            "gripper_open": bool(scene.is_left_gripper_open()),
            "rest_position": rest_position_error <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            "rest_orientation": rest_orientation_error <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": eef_linear_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": eef_angular_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=executed_prefix,
            semantic_verifier={
                "pass": all(checks.values()),
                "checks": checks,
                "inside": inside,
                "non_target": non_target,
                "rest_position_error_m": rest_position_error,
                "rest_orientation_error_rad": rest_orientation_error,
            },
            extra={
                "rollout_planner_reset_receipt": rollout_reset,
                "audit_role_mapping": {
                    "object_pose_primary_role": "red_fixed_across_F1_branches",
                    "target_role": role,
                    "target_role_pose_field": f"role_object_pose__{role}",
                },
            },
        )


class F2RunnerV3_1(BaseFamilyRunnerV3_1):
    family = "F2"
    positions = ([0.00, 0.15], [-0.08, 0.13], [-0.12, 0.10])
    yaws = (0.0, np.pi / 2)

    def canonical_prefix(self, programs):
        return {"prefix_id": "f2_same_can_grasp_lift_v1_1", "ops": ["grasp_main_can", "lift_main_can", "minimum_neutral_confirmation"]}

    def planner_audit_variants(self, frozen_program):
        if frozen_program["program_id"] != "F2-beside":
            return [{"variant_id": "default"}]
        variants = []
        index = 0
        for position in self.positions:
            for yaw in self.yaws:
                variants.append({"variant_id": F2_CANDIDATE_IDS[index], "stand_relative_xy_m": list(position), "yaw_radians": float(yaw), "height_margin_m": 0.08 if index % 2 == 0 else 0.10})
                index += 1
        return variants

    def audit_task_physical_feasibility(self, scene, program):
        base = super().audit_task_physical_feasibility(scene, program)
        can_half = _actor_half_extents(scene.can)
        inside_target = compose_pose(
            _pose(scene.box),
            [
                *F2_PLASTICBOX_BASE2_CAVITY["target_center_local_m"],
                *F2_INSIDE_LOCAL_QUATERNION_WXYZ,
            ],
        )
        inside_fit = verify_true_cavity_obb(
            inside_target,
            can_half,
            _pose(scene.box),
            F2_PLASTICBOX_BASE2_CAVITY,
        )
        scale_point = scene.scale.get_functional_point(0)
        stand_xy = np.asarray(scene.stand.get_pose().p[:2], dtype=np.float64)
        beside_targets = [stand_xy + np.asarray(position, dtype=np.float64) for position in self.positions]
        box_xy = np.asarray(scene.box.get_pose().p[:2], dtype=np.float64)
        scale_xy = np.asarray(scene.scale.get_pose().p[:2], dtype=np.float64)
        checks = {
            "roles": set(scene.role_actors) == {"main_can", "box", "scale", "stand"},
            "same_object": program["steps"][0].get("object") == "main_object",
            "left_arm_fixed": True,
            "relation": program["steps"][1].get("relation") in ("inside", "on", "beside"),
            "can_fits_box_cavity": inside_fit["pass_true_cavity_obb"],
            "scale_functional_point_exists": scale_point is not None and np.all(np.isfinite(np.asarray(scale_point, dtype=np.float64))),
            "beside_targets_on_table": all(-0.45 <= target[0] <= 0.45 and -0.35 <= target[1] <= 0.20 for target in beside_targets),
            "beside_targets_clear_box_scale": all(
                np.linalg.norm(target - box_xy) >= 0.10 and np.linalg.norm(target - scale_xy) >= 0.10
                for target in beside_targets
            ),
        }
        passed = base["task_feasible"] and all(checks.values())
        base.update({
            "task_feasible": passed,
            "physical_feasible": passed,
            "failure_type": None if passed else "f2_task_physical_contract",
            "evidence": {**checks, "inside_fit": inside_fit},
        })
        return base

    def _target_actor(self, scene, program, variant):
        actor_pose = _pose(scene.can)
        target = actor_pose.copy()
        relation = program["steps"][1]["relation"]
        if relation == "inside":
            target = compose_pose(
                _pose(scene.box),
                [
                    *F2_PLASTICBOX_BASE2_CAVITY["target_center_local_m"],
                    *F2_INSIDE_LOCAL_QUATERNION_WXYZ,
                ],
            )
        elif relation == "on":
            scale_point = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
            target[:3] = scale_point[:3]
        else:
            stand = np.asarray(scene.stand.get_pose().p, dtype=np.float64)
            target[:2] = stand[:2] + np.asarray(variant["stand_relative_xy_m"], dtype=np.float64)
            target[2] = actor_pose[2]
            target = world_z_yaw_pose(target, float(variant["yaw_radians"]))
        return target

    def build_targets(self, scene, program, planner_variant):
        pregrasp, grasp = scene.choose_grasp_pose(scene.can, arm_tag=_arm_tag_left(), pre_dis=0.08, target_dis=0)
        lift = world_axis_offset_pose(grasp, 0.12)
        target_actor = self._target_actor(scene, program, planner_variant)
        release = actor_target_to_eef_pose(grasp, _pose(scene.can), target_actor)
        preplace = world_axis_offset_pose(release, float(planner_variant.get("height_margin_m", 0.10)))
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        targets = [
            {"segment_id": "pregrasp", "pose": pregrasp},
            {"segment_id": "grasp", "pose": grasp},
            {"segment_id": "lift", "pose": lift},
            {"segment_id": "preplace", "pose": preplace},
            {"segment_id": "release", "pose": release},
            {"segment_id": "retreat", "pose": preplace},
            {"segment_id": "rest", "pose": rest},
        ]
        return targets, {"relation": program["steps"][1]["relation"], "target_actor_pose": target_actor.tolist()}

    def audit_planner_solvability(self, scene, frozen_program, planner_variant):
        targets, extra = self.build_targets(scene, frozen_program, planner_variant)
        reset = _planner_reset(scene, planner_seed=20260828, variant_id=planner_variant["variant_id"])
        # Candidate fairness concerns the placement endpoints.  Audit exactly
        # start->preplace->release from the same reset start state; grasp/lift
        # are executed only once in the selected real rollout.  This bounds
        # inside(2)+on(2)+six beside candidates(12) at 16 total queries.
        planned = _plan_chain(scene, targets[3:5], query_limit=FAMILY_PLANNER_LIMITS["F2"])
        segments = planned["segment_receipts"]
        execution_spec = None
        if planned["pass"]:
            execution_spec = {
                "variant_id": planner_variant["variant_id"],
                "targets": [{"segment_id": item["segment_id"], "pose": np.asarray(item["pose"], dtype=np.float64).tolist()} for item in targets],
                "planner_reset_receipt": reset,
                "preflight_segment_receipts": segments,
                "preplace_start_qpos_sha256": segments[0]["start_qpos_sha256"],
                "preplace_end_qpos_sha256": segments[0]["end_qpos_sha256"],
                "release_start_qpos_sha256": segments[1]["start_qpos_sha256"],
                "release_end_qpos_sha256": segments[1]["end_qpos_sha256"],
                "chain_continuity_pass": segments[1]["start_qpos_sha256"] == segments[0]["end_qpos_sha256"],
                **extra,
            }
        return {
            "planner_solvable": bool(planned["pass"]),
            "failure_type": None if planned["pass"] else "chained_preplace_release_planner_failure",
            "evidence": {"planner_reset_receipt": reset, "segment_receipts": segments, "query_budget_role": "two placement-chain queries"},
            "planner_query_count": int(planned["planner_query_count"]),
            "execution_spec": execution_spec,
        }

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        scene.initialize_trace(scene.can, "left", role_actors=scene.role_actors)
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F2"]
        rollout_reset = _planner_reset(scene, planner_seed=20260828, variant_id="f2_same_can_prefix")
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        _must_action(scene, scene.grasp_actor(scene.can, arm_tag=_arm_tag_left(), pre_grasp_dis=0.08), "prefix_grasp_can")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.12), "prefix_lift_can")
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        prefix_end_action = len(scene.trace) - 1
        end_anchor = anchor_capture(scene)
        executed_prefix = _prefix_evidence(scene, target_role=program["program_id"], prefix_start_action_index=prefix_start_action, prefix_end_action_index=prefix_end_action, start_anchor=start_anchor, end_anchor=end_anchor)
        spec = realization_spec["planner_execution_spec"]
        preplace_start_qpos = hash_array(np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64))
        _move_left(scene, spec["targets"][3]["pose"], spec["targets"][3]["segment_id"])
        preplace_end_qpos = hash_array(np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64))
        release_start_qpos = hash_array(np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64))
        _move_left(scene, spec["targets"][4]["pose"], spec["targets"][4]["segment_id"])
        release_end_qpos = hash_array(np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64))
        actual_place_chain = {
            "preplace_start_qpos_sha256": preplace_start_qpos,
            "preplace_end_qpos_sha256": preplace_end_qpos,
            "release_start_qpos_sha256": release_start_qpos,
            "release_end_qpos_sha256": release_end_qpos,
            "chain_continuity_pass": preplace_end_qpos == release_start_qpos,
        }
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "release")
        _wait_and_record(scene, 100)
        _move_left(scene, spec["targets"][5]["pose"], "retreat")
        _move_left(scene, spec["targets"][6]["pose"], "rest")
        _wait_and_record(scene, 75)
        can_pose = _pose(scene.can)
        can_half = _actor_half_extents(scene.can)
        inside = verify_true_cavity_obb(
            can_pose,
            can_half,
            _pose(scene.box),
            F2_PLASTICBOX_BASE2_CAVITY,
        )["pass_true_cavity_obb"]
        scale_target = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
        on = top_surface_region(can_pose[:3], scale_target[:3], [0.07, 0.07], 0.06)
        radial = float(np.linalg.norm(can_pose[:2] - np.asarray(scene.stand.get_pose().p[:2])))
        beside = bool(
            0.12 <= radial <= 0.23
            and can_pose[2] <= 0.83
            and not inside
            and not on
        )
        _, speeds, support = _stable_and_support(scene, scene.can, scene.box if inside else scene.scale if on else "table")
        relation = spec["relation"]
        exclusive = {"inside": inside, "on": on, "beside": beside}
        rest = np.asarray(spec["targets"][6]["pose"], dtype=np.float64)
        realized_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        rest_position_error = float(np.linalg.norm(realized_eef[:3] - rest[:3]))
        rest_orientation_error = quaternion_orientation_error(realized_eef[3:], rest[3:])
        eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
        eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
        checks = {
            "target_relation": exclusive[relation],
            "exclusive_relation": sum(bool(value) for value in exclusive.values()) == 1,
            "stable_window": bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "support_contact_window": bool(support) and all(support),
            "gripper_open": bool(scene.is_left_gripper_open()),
            "rest_position": rest_position_error <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            "rest_orientation": rest_orientation_error <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": eef_linear_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": eef_angular_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
            "actual_preplace_release_chain": actual_place_chain["chain_continuity_pass"],
        }
        semantic = {
            "pass": all(checks.values()),
            "checks": checks,
            "exclusive_relations": exclusive,
            "target_relation": relation,
            "support_window": support,
            "rest_position_error_m": rest_position_error,
            "rest_orientation_error_rad": rest_orientation_error,
            "actual_place_chain": actual_place_chain,
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=executed_prefix,
            semantic_verifier=semantic,
            extra={"rollout_planner_reset_receipt": rollout_reset},
        )


class F3RunnerV3_1(BaseFamilyRunnerV3_1):
    family = "F3"

    def canonical_prefix(self, programs):
        return {"prefix_id": "f3_grasp_central_shared_first_v_v1_1", "ops": ["grasp_bottle", "lift", "central", "V"], "shared_first_V": True}

    def audit_task_physical_feasibility(self, scene, program):
        base = super().audit_task_physical_feasibility(scene, program)
        bottle_name = _entity(scene.bottle).get_name()
        pad_name = _entity(scene.pad).get_name()
        linear_speeds = []
        angular_speeds = []
        pad_contacts = []
        required = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
        previous_pose = _pose(scene.bottle)
        timestep = float(scene.scene.get_timestep())
        if not np.isclose(timestep, 1.0 / 250.0, rtol=0.0, atol=1e-9):
            raise ValueError("F3 task/physical pose velocity requires 250 Hz scene timestep")
        component_linear_speeds = []
        component_angular_speeds = []
        for _ in range(required):
            scene.scene.step()
            current_pose = _pose(scene.bottle)
            linear = (current_pose[:3] - previous_pose[:3]) / timestep
            angular = quaternion_angular_velocity(
                previous_pose[3:], current_pose[3:], timestep
            )
            component_linear, _ = _rigid_velocity(
                scene.bottle, "linear_velocity"
            )
            component_angular, _ = _rigid_velocity(
                scene.bottle, "angular_velocity"
            )
            linear_speeds.append(float(np.linalg.norm(linear)))
            angular_speeds.append(float(np.linalg.norm(angular)))
            component_linear_speeds.append(
                float(np.linalg.norm(component_linear))
            )
            component_angular_speeds.append(
                float(np.linalg.norm(component_angular))
            )
            pad_contacts.append(
                any(
                    bottle_name in (contact.bodies[0].entity.name, contact.bodies[1].entity.name)
                    and pad_name in (contact.bodies[0].entity.name, contact.bodies[1].entity.name)
                    for contact in scene.scene.get_contacts()
                )
            )
            previous_pose = current_pose
        footprint = footprint_inside_local_region(
            _pose(scene.bottle),
            _actor_half_extents(scene.bottle),
            _pose(scene.pad),
            [-F3_PAD_HALF_SIZE_M[0], -F3_PAD_HALF_SIZE_M[1], -0.01],
            [F3_PAD_HALF_SIZE_M[0], F3_PAD_HALF_SIZE_M[1], 0.02],
            (0, 1),
        )
        checks = {
            "roles": set(scene.role_actors) == {"original_pad", "bottle", "central_marker"},
            "bottle_footprint_inside_pad": footprint["pass_support_footprint"],
            "continuous_pad_contact": bool(pad_contacts) and all(pad_contacts),
            "linear_stable_window": bool(linear_speeds) and max(linear_speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "angular_stable_window": bool(angular_speeds) and max(angular_speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        passed = base["task_feasible"] and all(checks.values())
        base.update(
            {
                "task_feasible": passed,
                "physical_feasible": passed,
                "failure_type": None if passed else "f3_initial_anchor_not_stable_on_pad",
                "evidence": {
                    "checks": checks,
                    "sample_count": required,
                    "linear_speed_mps": linear_speeds,
                    "angular_speed_rps": angular_speeds,
                    "component_linear_speed_mps_audit_only": component_linear_speeds,
                    "component_angular_speed_rps_audit_only": component_angular_speeds,
                    "gate_velocity_source": "250 Hz finite difference of the same saved actor pose",
                    "pad_contact": pad_contacts,
                    "footprint": footprint,
                },
            }
        )
        return base

    def build_targets(self, scene, program, planner_variant):
        start_actor = _pose(scene.bottle)
        pregrasp, grasp = scene.choose_grasp_pose(scene.bottle, arm_tag=_arm_tag_left(), pre_dis=0.09, target_dis=0)
        lift = world_axis_offset_pose(grasp, 0.12)
        central = np.concatenate(([-0.08, -0.05, 0.95], np.asarray(grasp)[3:]))
        targets = [
            {"segment_id": "pregrasp", "pose": pregrasp},
            {"segment_id": "grasp", "pose": grasp},
            {"segment_id": "lift", "pose": lift},
            {"segment_id": "central", "pose": central},
        ]
        execution_scope = planner_variant.get("execution_scope", "full_three_program_root")
        if execution_scope == "release_diagnosis":
            axes = "VH"
        else:
            axes = "".join(step["axis"] for step in program["steps"])
            if axes not in ("VVHH", "VHVH", "VHHV"):
                raise ValueError("F3 full program order is outside the frozen universe")
        for event_index, axis in enumerate(axes):
            vector = (
                np.asarray([F3_H_NOMINAL_AMPLITUDE_M_V3_3, 0, 0])
                if axis == "H"
                else np.asarray([0, 0, F3_V_NOMINAL_AMPLITUDE_M_V3_3])
            )
            targets.extend(
                [
                    {"segment_id": f"event_{event_index}_{axis}_positive", "pose": np.concatenate((central[:3] + vector, central[3:]))},
                    {"segment_id": f"event_{event_index}_{axis}_negative", "pose": np.concatenate((central[:3] - vector, central[3:]))},
                    {"segment_id": f"event_{event_index}_{axis}_return", "pose": central},
                ]
            )
        actor_at_central = compose_pose(central, relative_pose(grasp, start_actor))
        correction_spec = planner_variant.get("correction_spec")
        if correction_spec is None:
            release = actor_target_to_eef_pose(central, actor_at_central, start_actor)
            preplace = world_axis_offset_pose(release, 0.10)
        else:
            release = np.asarray(correction_spec["corrected_release_eef_pose"], dtype=np.float64).reshape(7)
            preplace = np.asarray(correction_spec["corrected_preplace_eef_pose"], dtype=np.float64).reshape(7)
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        targets.extend(
            [
                {"segment_id": "return_preplace", "pose": preplace},
                {"segment_id": "return_release", "pose": release},
                {"segment_id": "return_retreat", "pose": preplace},
                {"segment_id": "rest", "pose": rest},
            ]
        )
        return targets, {
            "execution_scope": (
                "f3_single_deterministic_correction_VH_only"
                if correction_spec is not None
                else "f3_release_diagnosis_VH_only"
                if execution_scope == "release_diagnosis"
                else "f3_full_program_nonformal_root"
            ),
            "event_order": axes,
            "target_actor_pose": start_actor.tolist(),
            "full_program_id": program["program_id"],
            "correction_spec": correction_spec,
        }

    @staticmethod
    def _execute_event(scene, axis, event_index, metrics):
        center_eef = np.asarray(scene.robot.get_left_ee_pose()[:3], dtype=np.float64)
        center_actor = _pose(scene.bottle)[:3]
        scene.mark(f"event_{event_index}_{axis}_start")
        vector = (
            (F3_H_NOMINAL_AMPLITUDE_M_V3_3, 0, 0)
            if axis == "H"
            else (0, 0, F3_V_NOMINAL_AMPLITUDE_M_V3_3)
        )
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), x=vector[0], y=vector[1], z=vector[2]), f"{axis}_positive")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), x=-2 * vector[0], y=-2 * vector[1], z=-2 * vector[2]), f"{axis}_negative")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), x=vector[0], y=vector[1], z=vector[2]), f"{axis}_return")
        scene.mark(f"event_{event_index}_{axis}_end")
        rows = scene.trace[scene.markers[f"event_{event_index}_{axis}_start"]:scene.markers[f"event_{event_index}_{axis}_end"] + 1]
        main_axis = 0 if axis == "H" else 2
        eef = np.asarray([row["eef"][:3] for row in rows])
        actor = np.asarray([row["actor_pose"][:3] for row in rows])
        contact_values = [bool(row["selected_gripper_contact"]) for row in rows]
        breaks = sum(previous and not current for previous, current in zip(contact_values, contact_values[1:]))
        item = {
            **{f"eef_{key}": value for key, value in closed_loop_event_metrics(eef, center_eef, main_axis).items()},
            **{f"bottle_{key}": value for key, value in closed_loop_event_metrics(actor, center_actor, main_axis).items()},
            "bottle_orientation_drift": max(quaternion_angular_error(rows[0]["actor_pose"][3:], row["actor_pose"][3:]) for row in rows),
            "selected_gripper_contact_fraction": float(np.mean(contact_values)),
            "contact_break_count": int(breaks),
        }
        metrics[f"event_{event_index}_{axis}"] = item

    @staticmethod
    def _release_sample(
        scene,
        target_pose,
        *,
        eef_target=None,
        stable_window_pass=False,
        support_window_pass=None,
    ):
        row = scene.trace[-1]
        pose = _pose(scene.bottle)
        bottle_name = _entity(scene.bottle).get_name()
        pad_name = _entity(scene.pad).get_name()
        pad_pairs = [
            item
            for item in row["contact_pairs"]
            if bottle_name in (item["body_a"], item["body_b"])
            and pad_name in (item["body_a"], item["body_b"])
        ]
        normals = [normal for item in pad_pairs for normal in item.get("point_normals", [])]
        impulse = float(sum(float(item.get("impulse_norm_sum", 0.0)) for item in pad_pairs))
        footprint = footprint_inside_local_region(
            pose,
            _actor_half_extents(scene.bottle),
            _pose(scene.pad),
            [-F3_PAD_HALF_SIZE_M[0], -F3_PAD_HALF_SIZE_M[1], -0.01],
            [F3_PAD_HALF_SIZE_M[0], F3_PAD_HALF_SIZE_M[1], 0.02],
            (0, 1),
        )["pass_support_footprint"]
        if eef_target is None:
            eef_tracking_error = 0.0
            eef_tracking_applicable = False
        else:
            eef_tracking_error = float(
                np.linalg.norm(
                    np.asarray(scene.robot.get_left_ee_pose()[:3], dtype=np.float64)
                    - np.asarray(eef_target[:3], dtype=np.float64)
                )
            )
            eef_tracking_applicable = True
        return {
            "sample_step": int(len(scene.trace) - 2),
            "bottle_position_error_m": float(np.linalg.norm(pose[:3] - target_pose[:3])),
            "bottle_orientation_error_rad": quaternion_angular_error(pose[3:], target_pose[3:]),
            "eef_tracking_error_m": eef_tracking_error,
            "eef_tracking_applicable": eef_tracking_applicable,
            "eef_pose": np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64).tolist(),
            "bottle_pose": pose.tolist(),
            "target_bottle_pose": np.asarray(target_pose, dtype=np.float64).tolist(),
            "commanded_release_eef_pose": None if eef_target is None else np.asarray(eef_target, dtype=np.float64).tolist(),
            "bottle_linear_speed_mps": float(np.linalg.norm(row["actor_linear_velocity"])),
            "bottle_angular_speed_rps": float(np.linalg.norm(row["actor_angular_velocity"])),
            "bottle_footprint_inside_pad": bool(footprint),
            "bottle_pad_contact_count": int(len(pad_pairs)),
            "bottle_pad_contact_normals": normals,
            "bottle_pad_contact_impulse": impulse,
            "selected_gripper_contact": bool(row["selected_gripper_contact"]),
            "actual_gripper_joint_qpos": np.asarray(row["realized_left_gripper_joint_qpos"], dtype=np.float64).tolist(),
            "stable_window_pass": bool(stable_window_pass),
            "support_pass": bool(pad_pairs) if support_window_pass is None else bool(support_window_pass),
        }

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        start_actor = _pose(scene.bottle)
        scene.initialize_trace(scene.bottle, "left", role_actors=scene.role_actors)
        spec = realization_spec["planner_execution_spec"]
        full_program = spec.get("execution_scope") == "f3_full_program_nonformal_root"
        scene.planner_query_limit = (
            FAMILY_FULL_PROGRAM_PLANNER_LIMITS["F3"] if full_program else FAMILY_PLANNER_LIMITS["F3"]
        )
        rollout_reset = _planner_reset(
            scene,
            planner_seed=20260828,
            variant_id="f3_full_program" if full_program else "f3_VH_diagnosis",
        )
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        target_map = _targets_by_segment_id(spec["targets"])
        _move_left(scene, target_map["pregrasp"]["pose"], "prefix_pregrasp")
        _move_left(scene, target_map["grasp"]["pose"], "prefix_grasp_pose")
        _must_action(scene, scene.close_gripper(_arm_tag_left(), pos=0.0), "prefix_close_gripper")
        _wait_and_record(scene, 25)
        for distance, segment_id in (
            (0.04, "prefix_lift_4cm"),
            (0.04, "prefix_lift_8cm"),
        ):
            actual_qpos = planner_array(
                scene.robot.left_entity.get_qpos(),
                label=f"{segment_id} actual post-grasp qpos",
            )
            lift_goal = world_axis_offset_pose(scene.robot.get_left_ee_pose(), distance)
            lift_control = _plan_left(
                scene,
                lift_goal,
                last_qpos=actual_qpos,
                source=segment_id,
            )
            _execute_control(scene, lift_control, segment_id)
            _wait_and_record(scene, 25)
        held_eef_initial = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        held_actor_initial = _pose(scene.bottle)
        _move_left(scene, spec["targets"][3]["pose"], "prefix_central")
        metrics = {}
        axes = spec["event_order"]
        self._execute_event(scene, axes[0], 0, metrics)
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        prefix_end_action = len(scene.trace) - 1
        end_anchor = anchor_capture(scene)
        executed_prefix = _prefix_evidence(scene, target_role=program["program_id"], prefix_start_action_index=prefix_start_action, prefix_end_action_index=prefix_end_action, start_anchor=start_anchor, end_anchor=end_anchor)
        for event_index, axis in enumerate(axes[1:], start=1):
            self._execute_event(scene, axis, event_index, metrics)
        return_preplace, return_release, return_retreat, rest = spec["targets"][-4:]
        _move_left(scene, return_preplace["pose"], "return_preplace")
        _move_left(scene, return_release["pose"], "return_release")
        held_eef_before_release = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        held_actor_before_release = _pose(scene.bottle)
        target_pose = np.asarray(spec["target_actor_pose"], dtype=np.float64)
        samples = {
            "before_release": self._release_sample(
                scene,
                target_pose,
                eef_target=return_release["pose"],
            )
        }
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "release")
        sample_steps = {1, 5, 10, 25, 50, 125, 250}
        for step in range(1, 251):
            _wait_and_record(scene, 1)
            if step in sample_steps:
                samples[f"after_release_{step}"] = self._release_sample(scene, target_pose)
        _move_left(scene, return_retreat["pose"], "return_retreat")
        _move_left(scene, rest["pose"], "rest")
        _wait_and_record(scene, 75)
        _, speeds, contacts = _stable_and_support(scene, scene.bottle, scene.pad)
        samples["after_rest"] = self._release_sample(
            scene,
            target_pose,
            eef_target=rest["pose"],
            stable_window_pass=bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            support_window_pass=bool(contacts) and all(contacts),
        )
        initial_transform = relative_pose(held_eef_initial, held_actor_initial)
        before_transform = relative_pose(held_eef_before_release, held_actor_before_release)
        grasp = {
            "initial_T_eef_actor": initial_transform.tolist(),
            "before_release_T_eef_actor": before_transform.tolist(),
            "grasp_transform_translation_drift": float(np.linalg.norm(initial_transform[:3] - before_transform[:3])),
            "grasp_transform_orientation_drift": quaternion_angular_error(initial_transform[3:], before_transform[3:]),
        }
        grasp["grasp_transform_stable"] = grasp["grasp_transform_translation_drift"] <= 0.005 and grasp["grasp_transform_orientation_drift"] <= 0.05
        diagnosis = classify_f3_release_dynamics_v3_1(
            samples,
            grasp,
            position_tolerance_m=PROVISIONAL_RUNTIME_THRESHOLDS["position_error_m"],
            orientation_tolerance_rad=PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            eef_tracking_tolerance_m=PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            grasp_translation_drift_tolerance_m=0.005,
            grasp_orientation_drift_tolerance_rad=0.05,
        )
        motion = verify_realized_motion_metrics(metrics, PROVISIONAL_RUNTIME_THRESHOLDS)
        realized_rest = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        rest_target = np.asarray(rest["pose"], dtype=np.float64)
        final_checks = {
            "return_equivalence": diagnosis["final_return_equivalence"],
            "realized_motion": motion["pass"],
            "gripper_open": bool(scene.is_left_gripper_open()),
            "rest_position": float(np.linalg.norm(realized_rest[:3] - rest_target[:3])) <= PROVISIONAL_RUNTIME_THRESHOLDS["rest_position_error_m"],
            "rest_orientation": quaternion_orientation_error(realized_rest[3:], rest_target[3:]) <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"])) <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"])) <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        repair_probe_pass = all(final_checks.values())
        semantic = {
            "pass": repair_probe_pass if full_program else False,
            "repair_probe_pass": repair_probe_pass,
            "full_f3_program_complete": full_program and repair_probe_pass,
            "failure_reason": (
                None
                if full_program and repair_probe_pass
                else "full F3 nonformal program verifier failed"
                if full_program
                else "runtime-v3_1 repair scope is V->H diagnosis only"
            ),
            "executed_event_order": axes,
            "expected_event_order": "".join(step["axis"] for step in program["steps"]),
            "diagnosis": diagnosis,
            "grasp_transform": grasp,
            "samples": samples,
            "realized_motion": motion,
            "final_checks": final_checks,
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=executed_prefix,
            semantic_verifier=semantic,
            extra={
                "rollout_planner_reset_receipt": rollout_reset,
                "final_state_equivalence_payload": {
                    "bottle_pose": _pose(scene.bottle).tolist(),
                    "left_eef_pose": np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64).tolist(),
                    "left_gripper_open": bool(scene.is_left_gripper_open()),
                    "target_bottle_pose": target_pose.tolist(),
                },
            },
        )


class F4RunnerV3_1(BaseFamilyRunnerV3_1):
    family = "F4"

    def canonical_prefix(self, programs):
        return {"prefix_id": "f4_common_x_to_tray_neutral_v1_1", "ops": ["place_common_X_in_tray", "return_branch_neutral"], "programs": [item["program_id"] for item in programs]}

    def planner_audit_variants(self, frozen_program):
        return [{"variant_id": route_id} for route_id in F4_ROUTE_ORDER]

    def audit_task_physical_feasibility(self, scene, program):
        base = super().audit_task_physical_feasibility(scene, program)
        tray_lower = np.asarray(TRAY_BASE0_SUPPORT_REGION["lower_m"], dtype=np.float64)
        tray_upper = np.asarray(TRAY_BASE0_SUPPORT_REGION["upper_m"], dtype=np.float64)
        tray_axes = tuple(TRAY_BASE0_SUPPORT_REGION["horizontal_axes"])
        slot_positions = [np.asarray(getattr(scene, f"slot_{role}").get_pose().p[:2], dtype=np.float64) for role in ("a", "b", "c")]
        object_positions = [np.asarray(getattr(scene, role).get_pose().p[:2], dtype=np.float64) for role in ("a", "b", "c")]
        checks = {
            "roles": set(scene.role_actors) == {"common_x", "A", "B", "C", "common_tray", "slot_A", "slot_B", "slot_C"},
            "common_first": program["steps"][0].get("object") == "common_X",
            "order": "".join(step["object"] for step in program["steps"][1:]) in ("ABC", "ACB", "BAC"),
            "tray_region_fits_common_block": all((tray_upper[axis] - tray_lower[axis]) > 2 * BLOCK_HALF_EXTENTS[axis] for axis in tray_axes),
            "slots_pairwise_separated": all(
                np.linalg.norm(slot_positions[left] - slot_positions[right]) >= 0.10
                for left in range(3)
                for right in range(left + 1, 3)
            ),
            "objects_pairwise_separated": all(
                np.linalg.norm(object_positions[left] - object_positions[right]) >= 0.08
                for left in range(3)
                for right in range(left + 1, 3)
            ),
        }
        passed = base["task_feasible"] and all(checks.values())
        base.update({"task_feasible": passed, "physical_feasible": passed, "failure_type": None if passed else "f4_task_physical_contract", "evidence": checks})
        return base

    def _object_place_targets(self, scene, actor, slot, prefix, *, arm):
        pregrasp, grasp, grasp_contract = build_project_cube_grasp_poses(
            _pose(actor),
            cube_half_extents_m=_actor_half_extents(actor),
            arm=arm,
            pregrasp_distance_m=0.09,
        )
        lift = world_axis_offset_pose(grasp, 0.10)
        target_actor = _pose(actor)
        target_actor[:3] = np.asarray(slot.get_pose().p, dtype=np.float64) + np.asarray([0, 0, BLOCK_HALF_EXTENTS[2]])
        release = actor_target_to_eef_pose(grasp, _pose(actor), target_actor)
        preplace = world_axis_offset_pose(release, 0.10)
        return [
            {"segment_id": f"{prefix}_pregrasp", "pose": pregrasp},
            {"segment_id": f"{prefix}_grasp", "pose": grasp},
            {"segment_id": f"{prefix}_lift", "pose": lift},
            {"segment_id": f"{prefix}_preplace", "pose": preplace},
            {"segment_id": f"{prefix}_release", "pose": release},
        ], grasp_contract

    def build_targets(self, scene, program, planner_variant):
        execution_scope = planner_variant.get("execution_scope", "full_three_program_root")
        arm = _execution_arm(scene)
        common_grasp_mode = planner_variant.get("common_grasp_mode")
        if common_grasp_mode == "project_cube_grasp_v1":
            common_pregrasp, common_grasp, common_grasp_contract = (
                build_project_cube_grasp_poses(
                    _pose(scene.common_x),
                    cube_half_extents_m=_actor_half_extents(scene.common_x),
                    arm=arm,
                    pregrasp_distance_m=0.09,
                )
            )
        elif common_grasp_mode in (None, "official_planner_assisted"):
            common_pregrasp, common_grasp = scene.choose_grasp_pose(
                scene.common_x,
                arm_tag=_arm_tag(arm),
                pre_dis=0.09,
                target_dis=0,
            )
            if common_pregrasp is None or common_grasp is None:
                raise ValueError(
                    "F4 common-X planner-assisted grasp target construction failed"
                )
            common_grasp_contract = {
                "contract_version": "official_planner_assisted_choose_grasp_pose",
                "arm": arm,
            }
        else:
            raise ValueError("F4 common grasp mode is outside the frozen implementation universe")
        common_lift = world_axis_offset_pose(common_grasp, 0.10)
        target_actor = _pose(scene.common_x)
        target_actor[:3] = transform_local_point(_pose(scene.tray), TRAY_BASE0_SUPPORT_REGION["target_center_local_m"])
        common_release = actor_target_to_eef_pose(common_grasp, _pose(scene.common_x), target_actor)
        common_preplace = world_axis_offset_pose(common_release, 0.10)
        obstacle_tops = [float(_pose(getattr(scene, role))[2] + BLOCK_HALF_EXTENTS[2]) for role in ("a", "b", "c")]
        gripper_envelope = _gripper_below_eef_envelope(scene, arm=arm)
        envelope = minimum_f4_safe_carry_height(
            obstacle_tops,
            actor_half_height_m=0.022,
            gripper_below_eef_envelope_m=gripper_envelope["gripper_below_eef_envelope_m"],
            frozen_clearance_m=0.03,
        )
        safe = common_lift.copy()
        envelope["computed_obstacle_clearance_height_m"] = envelope["safe_eef_or_actor_center_z"]
        envelope["common_lift_height_m"] = float(common_lift[2])
        safe[2] = max(float(common_lift[2]), envelope["safe_eef_or_actor_center_z"])
        envelope["selected_safe_carry_height_m"] = float(safe[2])
        envelope["selected_height_not_below_lift"] = bool(safe[2] >= common_lift[2])
        center = safe.copy()
        center[:2] = (common_lift[:2] + common_preplace[:2]) / 2.0
        above = common_preplace.copy()
        above[2] = safe[2]
        planned = getattr(scene, "_cmf_planned_root_slot_spec", {})
        layout = planned.get("scene_layout", {}) if isinstance(planned, Mapping) else {}
        neutral_spec = layout.get("branch_neutral_pose")
        neutral = (
            np.asarray(neutral_spec, dtype=np.float64).reshape(7)
            if neutral_spec is not None
            else np.concatenate(([-0.15, -0.04, 0.95], np.asarray(common_grasp)[3:]))
        )
        if planner_variant["variant_id"] == F4_ROUTE_ORDER[0]:
            common_targets = [
                {"segment_id": "common_pregrasp", "pose": common_pregrasp},
                {"segment_id": "common_grasp", "pose": common_grasp},
                {"segment_id": "common_lift", "pose": common_lift},
                {"segment_id": "common_safe_vertical", "pose": safe},
                {"segment_id": "common_center_high", "pose": center},
                {"segment_id": "common_above_tray", "pose": above},
                {"segment_id": "common_preplace", "pose": common_preplace},
                {"segment_id": "common_release", "pose": common_release},
                {"segment_id": "common_neutral", "pose": neutral},
            ]
        else:
            carry_neutral = neutral.copy()
            carry_neutral[2] = safe[2]
            common_targets = [
                {"segment_id": "common_pregrasp", "pose": common_pregrasp},
                {"segment_id": "common_grasp", "pose": common_grasp},
                {"segment_id": "common_lift", "pose": common_lift},
                {"segment_id": "common_carry_neutral", "pose": carry_neutral},
                {"segment_id": "common_center_high", "pose": center},
                {"segment_id": "common_above_tray", "pose": above},
                {"segment_id": "common_preplace", "pose": common_preplace},
                {"segment_id": "common_release", "pose": common_release},
                {"segment_id": "common_neutral", "pose": neutral},
            ]
        targets = list(common_targets)
        order = [step["object"] for step in program["steps"][1:]]
        object_target_groups = []
        if execution_scope != "common_x_route_repair":
            if "".join(order) not in ("ABC", "ACB", "BAC"):
                raise ValueError("F4 full program order is outside the frozen universe")
            for role in order:
                actor = getattr(scene, role.lower())
                slot = getattr(scene, f"slot_{role.lower()}")
                group, grasp_contract = self._object_place_targets(
                    scene, actor, slot, role, arm=arm
                )
                group.append({"segment_id": f"{role}_neutral", "pose": neutral.copy()})
                targets.extend(group)
                object_target_groups.append(
                    {
                        "role": role,
                        "targets": [
                            {"segment_id": item["segment_id"], "pose": np.asarray(item["pose"], dtype=np.float64).tolist()}
                            for item in group
                        ],
                        "grasp_contract": grasp_contract,
                    }
                )
        return targets, {
            "execution_scope": (
                "f4_common_x_route_repair_only"
                if execution_scope == "common_x_route_repair"
                else "f4_full_program_nonformal_root"
            ),
            "route_id": planner_variant["variant_id"],
            "execution_arm": arm,
            "carry_envelope_version": envelope["carry_envelope_version"],
            "carry_envelope": envelope,
            "gripper_envelope_evidence": gripper_envelope,
            "tray_pose_changed": False,
            "object_order": order,
            "object_target_groups": object_target_groups,
            "common_target_actor_pose": target_actor.tolist(),
            "common_grasp_contract": common_grasp_contract,
        }

    def audit_planner_solvability(self, scene, frozen_program, planner_variant):
        targets, extra = self.build_targets(scene, frozen_program, planner_variant)
        arm = extra["execution_arm"]
        reset = _planner_reset(
            scene,
            planner_seed=20260828,
            variant_id=planner_variant["variant_id"],
            arm=arm,
        )
        full_program = str(extra.get("execution_scope", "")).endswith("full_program_nonformal_root")
        query_limit = FAMILY_FULL_PROGRAM_PLANNER_LIMITS["F4"] if full_program else FAMILY_PLANNER_LIMITS["F4"]
        planned = _plan_chain(scene, targets, query_limit=query_limit, arm=arm)
        execution_spec = None
        if planned["pass"]:
            execution_spec = {
                "variant_id": planner_variant["variant_id"],
                "targets": [
                    {"segment_id": item["segment_id"], "pose": np.asarray(item["pose"], dtype=np.float64).tolist()}
                    for item in targets
                ],
                "planner_reset_receipt": reset,
                "preflight_segment_receipts": planned["segment_receipts"],
                **extra,
            }
        return {
            "planner_solvable": bool(planned["pass"]),
            "failure_type": None if planned["pass"] else "chained_planner_failure",
            "evidence": {"planner_reset_receipt": reset, "segment_receipts": planned["segment_receipts"]},
            "planner_query_count": int(planned["planner_query_count"]),
            "execution_spec": execution_spec,
        }

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        spec = realization_spec["planner_execution_spec"]
        arm = spec.get("execution_arm", _execution_arm(scene))
        scene.initialize_trace(scene.common_x, arm, role_actors=scene.role_actors)
        full_program = spec.get("execution_scope") == "f4_full_program_nonformal_root"
        scene.planner_query_limit = (
            FAMILY_FULL_PROGRAM_PLANNER_LIMITS["F4"] if full_program else FAMILY_PLANNER_LIMITS["F4"]
        )
        rollout_reset = _planner_reset(
            scene,
            planner_seed=20260828,
            variant_id=spec["variant_id"],
            arm=arm,
        )
        non_targets = {"A": scene.a, "B": scene.b, "C": scene.c}
        non_target_baseline = _position_map(non_targets)
        non_target_stages = {"initial": _position_map(non_targets)}
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        targets = spec["targets"]
        _must_action(scene, scene.grasp_actor(scene.common_x, arm_tag=_arm_tag(arm), pre_grasp_dis=0.09), "common_grasp")
        non_target_stages["after_common_grasp"] = _position_map(non_targets)
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag(arm), z=0.10), "common_lift")
        non_target_stages["after_common_lift"] = _position_map(non_targets)
        for target in targets[3:8]:
            _move_arm(scene, target["pose"], target["segment_id"], arm=arm)
        non_target_stages["after_common_transport"] = _position_map(non_targets)
        _must_action(scene, scene.open_gripper(_arm_tag(arm), pos=1.0), "common_release")
        _wait_and_record(scene, 125)
        non_target_stages["after_common_release"] = _position_map(non_targets)
        _move_arm(scene, targets[8]["pose"], "common_neutral", arm=arm)
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        non_target_stages["after_common_neutral"] = _position_map(non_targets)
        prefix_end_action = len(scene.trace) - 1
        end_anchor = anchor_capture(scene)
        executed_prefix = _prefix_evidence(scene, target_role=program["program_id"], prefix_start_action_index=prefix_start_action, prefix_end_action_index=prefix_end_action, start_anchor=start_anchor, end_anchor=end_anchor)
        _wait_and_record(scene, 75)
        non_target_stages["after_final_stability"] = _position_map(non_targets)
        footprint = footprint_inside_local_region(
            _pose(scene.common_x), BLOCK_HALF_EXTENTS, _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"], TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        _, speeds, contacts = _stable_and_support(scene, scene.common_x, scene.tray)
        non_target = verify_staged_non_target_displacement(
            non_target_baseline,
            non_target_stages,
            PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"],
        )
        neutral_target = np.asarray(targets[8]["pose"], dtype=np.float64)
        realized_eef = _arm_eef_pose(scene, arm)
        neutral_position_error = float(np.linalg.norm(realized_eef[:3] - neutral_target[:3]))
        neutral_orientation_error = quaternion_orientation_error(realized_eef[3:], neutral_target[3:])
        eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
        eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
        common_checks = {
            "tray_footprint": footprint["pass_support_footprint"],
            "stable_window": bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "support_contact_window": bool(contacts) and all(contacts),
            "non_target_stability": non_target["pass"],
            "gripper_open": _arm_gripper_open(scene, arm),
            "neutral_position": neutral_position_error <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
            "neutral_orientation": neutral_orientation_error <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": eef_linear_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": eef_angular_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        common_probe_pass = all(common_checks.values())

        block_receipts = []
        completion_steps = []
        completed_roles = []
        if full_program:
            for group in spec["object_target_groups"]:
                role = group["role"]
                actor = getattr(scene, role.lower())
                slot = getattr(scene, f"slot_{role.lower()}")
                group_targets = group["targets"]
                other_actors = {
                    other_role: getattr(scene, other_role.lower())
                    for other_role in ("A", "B", "C")
                    if other_role != role
                }
                other_before = _position_map(other_actors)
                start_eef = _arm_eef_pose(scene, arm)
                start_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
                start_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
                start_gripper_open = _arm_gripper_open(scene, arm)
                object_initial_pose = _pose(actor)
                slot_before = footprint_inside_local_region(
                    object_initial_pose,
                    BLOCK_HALF_EXTENTS,
                    _pose(slot),
                    [-0.035, -0.035, -0.01],
                    [0.035, 0.035, 0.03],
                    (0, 1),
                )["pass_support_footprint"]

                _move_arm(
                    scene,
                    group_targets[0]["pose"],
                    group_targets[0]["segment_id"],
                    arm=arm,
                )
                _move_arm(
                    scene,
                    group_targets[1]["pose"],
                    group_targets[1]["segment_id"],
                    arm=arm,
                )
                _must_action(
                    scene,
                    scene.close_gripper(_arm_tag(arm), pos=0.0),
                    f"{role}_close_gripper",
                )
                _move_arm(
                    scene,
                    group_targets[2]["pose"],
                    group_targets[2]["segment_id"],
                    arm=arm,
                )
                _move_arm(scene, group_targets[3]["pose"], group_targets[3]["segment_id"], arm=arm)
                _move_arm(scene, group_targets[4]["pose"], group_targets[4]["segment_id"], arm=arm)
                _must_action(scene, scene.open_gripper(_arm_tag(arm), pos=1.0), f"{role}_release")
                _wait_and_record(scene, PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
                object_final_pose = _pose(actor)
                slot_after = footprint_inside_local_region(
                    object_final_pose,
                    BLOCK_HALF_EXTENTS,
                    _pose(slot),
                    [-0.035, -0.035, -0.01],
                    [0.035, 0.035, 0.03],
                    (0, 1),
                )["pass_support_footprint"]
                _, block_speeds, _ = _stable_and_support(scene, actor, "table")
                completion_step = len(scene.trace) - int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
                completion_steps.append(completion_step)
                _move_arm(scene, group_targets[5]["pose"], group_targets[5]["segment_id"], arm=arm)
                _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
                end_eef = _arm_eef_pose(scene, arm)
                end_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
                end_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
                end_gripper_open = _arm_gripper_open(scene, arm)
                other_after = _position_map(other_actors)
                other_displacement = {
                    key: float(np.linalg.norm(other_after[key] - other_before[key])) for key in other_actors
                }
                prior_slot_preserved = {}
                for previous_role in completed_roles:
                    previous_actor = getattr(scene, previous_role.lower())
                    previous_slot = getattr(scene, f"slot_{previous_role.lower()}")
                    prior_slot_preserved[previous_role] = bool(
                        footprint_inside_local_region(
                            _pose(previous_actor),
                            BLOCK_HALF_EXTENTS,
                            _pose(previous_slot),
                            [-0.035, -0.035, -0.01],
                            [0.035, 0.035, 0.03],
                            (0, 1),
                        )["pass_support_footprint"]
                    )
                checks = {
                    "slot_false_before": not bool(slot_before),
                    "slot_true_after": bool(slot_after),
                    "stable_after_release": bool(block_speeds)
                    and max(block_speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
                    "gripper_open_after": end_gripper_open,
                    "neutral_position": float(np.linalg.norm(end_eef[:3] - np.asarray(group_targets[5]["pose"][:3])))
                    <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
                    "neutral_orientation": quaternion_orientation_error(
                        end_eef[3:], np.asarray(group_targets[5]["pose"][3:])
                    )
                    <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
                    "neutral_linear_stationary": end_linear_speed
                    <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
                    "neutral_angular_stationary": end_angular_speed
                    <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
                    "other_objects_stable": all(
                        value <= PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"]
                        for value in other_displacement.values()
                    ),
                    "prior_slots_preserved": all(prior_slot_preserved.values()),
                }
                block_receipts.append(
                    {
                        "block_id": role,
                        "start_eef_pose": start_eef.tolist(),
                        "end_eef_pose": end_eef.tolist(),
                        "start_eef_linear_speed_mps": start_linear_speed,
                        "end_eef_linear_speed_mps": end_linear_speed,
                        "start_eef_angular_speed_rps": start_angular_speed,
                        "end_eef_angular_speed_rps": end_angular_speed,
                        "start_gripper_open": start_gripper_open,
                        "end_gripper_open": end_gripper_open,
                        "object_initial_pose": object_initial_pose.tolist(),
                        "object_final_pose": object_final_pose.tolist(),
                        "other_object_displacement_m": other_displacement,
                        "slot_predicate_before": bool(slot_before),
                        "slot_predicate_after": bool(slot_after),
                        "prior_slot_predicates_after": prior_slot_preserved,
                        "completion_step": completion_step,
                        "checks": checks,
                        "pass": all(checks.values()),
                    }
                )
                completed_roles.append(role)

        expected_order = list(spec["object_order"])
        realized_order = [item["block_id"] for item in block_receipts]
        final_slot_predicates = {
            role: bool(
                footprint_inside_local_region(
                    _pose(getattr(scene, role.lower())),
                    BLOCK_HALF_EXTENTS,
                    _pose(getattr(scene, f"slot_{role.lower()}")),
                    [-0.035, -0.035, -0.01],
                    [0.035, 0.035, 0.03],
                    (0, 1),
                )["pass_support_footprint"]
            )
            for role in ("A", "B", "C")
        }
        full_checks = {
            "common_prefix": common_probe_pass,
            "three_blocks_executed": len(block_receipts) == 3,
            "block_order": realized_order == expected_order,
            "all_blocks_pass": bool(block_receipts) and all(item["pass"] for item in block_receipts),
            "all_final_slots": all(final_slot_predicates.values()) if full_program else False,
            "completion_strictly_ordered": all(left < right for left, right in zip(completion_steps, completion_steps[1:])),
            "noninterference": bool(block_receipts)
            and all(item["checks"]["prior_slots_preserved"] for item in block_receipts),
        }
        full_program_pass = full_program and all(full_checks.values())
        semantic = {
            "pass": full_program_pass,
            "common_x_repair_probe_pass": common_probe_pass,
            "common_x_checks": common_checks,
            "full_f4_program_complete": full_program_pass,
            "failure_reason": (
                None
                if full_program_pass
                else "full F4 nonformal program verifier failed"
                if full_program
                else "runtime-v3_2 repair scope covers common-X only"
            ),
            "common_tray_footprint": footprint,
            "support_contact_window": contacts,
            "stable_speed_window_mps": speeds,
            "non_target_verifier": non_target,
            "neutral_position_error_m": neutral_position_error,
            "neutral_orientation_error_rad": neutral_orientation_error,
            "route_id": spec["route_id"],
            "carry_envelope_version": spec["carry_envelope_version"],
            "expected_object_order": expected_order,
            "realized_object_order": realized_order,
            "completion_steps": completion_steps,
            "block_receipts": block_receipts,
            "final_slot_predicates": final_slot_predicates,
            "full_program_checks": full_checks,
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=executed_prefix,
            semantic_verifier=semantic,
            extra={
                "rollout_planner_reset_receipt": rollout_reset,
                "final_state_equivalence_payload": {
                    "common_x_pose": _pose(scene.common_x).tolist(),
                    "A_pose": _pose(scene.a).tolist(),
                    "B_pose": _pose(scene.b).tolist(),
                    "C_pose": _pose(scene.c).tolist(),
                    "executing_eef_pose": _arm_eef_pose(scene, arm).tolist(),
                    "executing_gripper_open": _arm_gripper_open(scene, arm),
                    "execution_arm": arm,
                },
            },
        )


RUNNERS = {
    "F1": F1RunnerV3_1(),
    "F2": F2RunnerV3_1(),
    "F3": F3RunnerV3_1(),
    "F4": F4RunnerV3_1(),
}


def get_family_runner(family: str):
    if family not in RUNNERS:
        raise ValueError(f"unknown runtime-v3_1 family {family}")
    return RUNNERS[family]
