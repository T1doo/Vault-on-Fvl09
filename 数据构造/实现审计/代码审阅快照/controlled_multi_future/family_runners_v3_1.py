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
    quaternion_orientation_error,
    relative_pose,
    swept_path_collisions,
    transform_local_point,
    world_axis_offset_pose,
    world_z_yaw_pose,
)
from .probes.runtime_trace import _rigid_velocity, trace_rows_to_raw_streams
from .runtime_v2_contracts import PLASTICBOX_BASE3_CAVITY, PROVISIONAL_RUNTIME_THRESHOLDS, TRAY_BASE0_SUPPORT_REGION
from .runtime_v3_1_contracts import (
    F2_CANDIDATE_IDS,
    F4_ROUTE_ORDER,
    classify_f3_release_dynamics_v3_1,
    minimum_f4_safe_carry_height,
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
MINIMUM_NEUTRAL_CONFIRMATION_STEPS = 1


class FamilyRunnerError(RuntimeError):
    pass


class PlannerChainFailure(FamilyRunnerError):
    pass


def _arm_tag_left():
    from envs.utils.action import ArmTag

    return ArmTag("left")


def _entity(actor):
    return actor.actor if hasattr(actor, "actor") else actor


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _position_map(actors):
    return {name: np.asarray(actor.get_pose().p, dtype=np.float64).copy() for name, actor in actors.items()}


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


def _execute_control(scene, control, label):
    if not isinstance(control, Mapping) or control.get("status") != "Success":
        raise PlannerChainFailure(f"planner control failed at {label}")
    scene.take_dense_action({"left_arm": control, "left_gripper": None, "right_arm": None, "right_gripper": None})


def _move_left(scene, pose, label):
    control = scene.left_move_to_pose(pose=np.asarray(pose, dtype=np.float64).tolist())
    _execute_control(scene, control, label)
    return control


def _planner_reset(scene, *, planner_seed: int, variant_id: str) -> dict:
    robot = scene.robot
    reset_source = None
    if getattr(robot, "communication_flag", False):
        robot.left_conn.send({"cmd": "reset"})
        response = robot.left_conn.recv()
        if response != "ok":
            raise PlannerChainFailure(f"left planner reset failed: {response}")
        reset_source = "RoboTwin planner worker cmd=reset -> MotionGen.reset(reset_seed=True)"
        planner_identity = f"worker-pid:{getattr(robot, 'left_proc', None).pid}"
    else:
        planner = getattr(robot, "left_planner", None)
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
        "reset_evidence": reset_payload,
    }


def _ensure_planner_trace_fields(scene, limit):
    if not hasattr(scene, "planner_queries"):
        scene.planner_queries = []
    if not hasattr(scene, "planner_query_count"):
        scene.planner_query_count = 0
    scene.planner_query_limit = int(limit)


def _plan_left(scene, pose, *, last_qpos, source):
    _ensure_planner_trace_fields(scene, getattr(scene, "planner_query_limit", 16))
    query_id = scene._reserve_planner_query()
    pose = np.asarray(pose, dtype=np.float64).reshape(7)
    result = scene.robot.left_plan_path(pose.tolist(), last_qpos=last_qpos)
    status = result.get("status") if isinstance(result, Mapping) else "Fail"
    item = {
        "query_id": query_id,
        "arm": "left",
        "source": source,
        "goal_eef_pose": pose.tolist(),
        "status": status,
        "start_step": None,
        "end_step": None,
    }
    scene.planner_queries.append(item)
    if isinstance(result, dict):
        result["_cmf_planner_query"] = dict(item)
    return result


def _merge_left_arm_terminal_qpos(scene, full_start_qpos, terminal_arm_qpos):
    full = np.asarray(full_start_qpos, dtype=np.float64).reshape(-1).copy()
    terminal = np.asarray(terminal_arm_qpos, dtype=np.float64).reshape(-1)
    if terminal.size == full.size:
        return terminal.copy()
    active_joints = list(scene.robot.left_entity.get_active_joints())
    index_by_name = {joint.get_name(): index for index, joint in enumerate(active_joints)}
    arm_names = [joint.get_name() for joint in scene.robot.left_arm_joints]
    if terminal.size != len(arm_names) or any(name not in index_by_name for name in arm_names):
        raise PlannerChainFailure("planner terminal qpos cannot be mapped into full left articulation state")
    for value, name in zip(terminal, arm_names):
        full[index_by_name[name]] = value
    return full


def _plan_chain(scene, targets: Sequence[Mapping[str, Any]], *, query_limit: int) -> dict:
    _ensure_planner_trace_fields(scene, query_limit)
    last_qpos = np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64).reshape(-1)
    segment_receipts = []
    controls = []
    for target in targets:
        start_hash = hash_array(last_qpos)
        control = _plan_left(scene, target["pose"], last_qpos=last_qpos, source=target["segment_id"])
        status = control.get("status") if isinstance(control, Mapping) else "Fail"
        if status == "Success":
            positions = np.asarray(control["position"], dtype=np.float64)
            if positions.ndim != 2 or positions.shape[0] < 1:
                raise PlannerChainFailure(f"planner returned no qpos path at {target['segment_id']}")
            end_qpos = _merge_left_arm_terminal_qpos(scene, last_qpos, positions[-1])
            end_hash = hash_array(end_qpos)
        else:
            end_qpos = last_qpos.copy()
            end_hash = hash_array(end_qpos)
        segment_receipts.append(
            {
                "segment_id": target["segment_id"],
                "start_qpos_sha256": start_hash,
                "end_qpos_sha256": end_hash,
                "planner_status": status,
                "executed": False,
                "goal_eef_pose": np.asarray(target["pose"], dtype=np.float64).tolist(),
            }
        )
        controls.append(control)
        if status != "Success":
            return {"pass": False, "segment_receipts": segment_receipts, "controls": controls, "planner_query_count": scene.planner_query_count}
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


def _raw_result(scene, *, program, realization_spec, executed_prefix, semantic_verifier, extra=None):
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
            "implementation_version": "controlled_multi_future_runtime_v3_1",
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


def _actor_half_extents(actor, fallback=BLOCK_HALF_EXTENTS):
    config = getattr(actor, "config", None) or {}
    if "extents" in config and "scale" in config:
        return np.asarray(config["extents"], dtype=np.float64) * np.asarray(config["scale"], dtype=np.float64) / 2.0
    return np.asarray(fallback, dtype=np.float64)


def _left_gripper_below_eef_envelope(scene, *, conservative_link_margin_m=0.03):
    robot = scene.robot
    names = set(robot.left_fix_gripper_name)
    names.update(joint[0].child_link.get_name() for joint in robot.left_gripper)
    links = {link.get_name(): link for link in robot.left_entity.get_links()}
    missing = sorted(names - set(links))
    if missing:
        raise ValueError(f"selected left-gripper links missing from articulation: {missing}")
    eef_z = float(np.asarray(robot.get_left_ee_pose(), dtype=np.float64)[2])
    link_z = {name: float(links[name].get_pose().p[2]) for name in sorted(names)}
    below = max(0.0, eef_z - min(link_z.values())) + float(conservative_link_margin_m)
    return {
        "selected_gripper_links": sorted(names),
        "eef_world_z_m": eef_z,
        "link_world_z_m": link_z,
        "conservative_link_margin_m": float(conservative_link_margin_m),
        "gripper_below_eef_envelope_m": float(below),
        "source": "runtime selected left-gripper link poses plus frozen conservative link margin",
    }


def _stable_and_support(scene, actor, support, frames=None):
    frames = int(frames or PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
    rows = scene.trace[-frames:]
    speeds = [float(np.linalg.norm(row["actor_linear_velocity"])) for row in rows]
    actor_name = _entity(actor).get_name()
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
        planned = _plan_chain(scene, targets, query_limit=FAMILY_PLANNER_LIMITS[self.family])
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
        checks = {
            "roles": set(scene.role_actors) == expected,
            "target_role": role in ("red", "green", "blue"),
            "same_block_half_extents": all(np.allclose(_actor_half_extents(getattr(scene, name)), BLOCK_HALF_EXTENTS) for name in ("red", "green", "blue")),
            "box_cavity_larger_than_block": np.all(
                np.asarray(PLASTICBOX_BASE3_CAVITY["upper_m"]) - np.asarray(PLASTICBOX_BASE3_CAVITY["lower_m"]) > 2 * BLOCK_HALF_EXTENTS
            ),
            "initial_blocks_pairwise_separated": all(
                np.linalg.norm(block_positions[left] - block_positions[right]) >= 0.08
                for left in range(3)
                for right in range(left + 1, 3)
            ),
        }
        passed = base["task_feasible"] and all(checks.values())
        base.update({"task_feasible": passed, "physical_feasible": passed, "failure_type": None if passed else "f1_task_physical_contract", "evidence": checks})
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
        lift = world_axis_offset_pose(grasp, 0.12)
        safe = lift.copy()
        safe[2] = max(float(lift[2]), 1.02)
        above = preplace.copy()
        above[2] = safe[2]
        targets = [
            {"segment_id": "common_cluster_neutral", "pose": neutral},
            {"segment_id": "target_pregrasp", "pose": pregrasp},
            {"segment_id": "target_grasp", "pose": grasp},
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
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.12), f"lift_{role}")
        stages["after_lift"] = _position_map(non_targets)
        for target in spec["targets"][4:8]:
            _move_left(scene, target["pose"], target["segment_id"])
        stages["after_transport"] = _position_map(non_targets)
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "release")
        _wait_and_record(scene, 75)
        stages["after_release"] = _position_map(non_targets)
        _move_left(scene, spec["targets"][8]["pose"], "retreat")
        stages["after_retreat"] = _position_map(non_targets)
        _move_left(scene, spec["targets"][9]["pose"], "rest")
        _wait_and_record(scene, 75)
        stages["after_rest"] = _position_map(non_targets)
        inside = verify_true_cavity_obb(_pose(actor), BLOCK_HALF_EXTENTS, _pose(scene.box), PLASTICBOX_BASE3_CAVITY)
        non_target = verify_staged_non_target_displacement(baseline, stages, PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"])
        _, speeds, contacts = _stable_and_support(scene, actor, scene.box)
        rest = np.asarray(spec["targets"][9]["pose"], dtype=np.float64)
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
        cavity_size = np.asarray(PLASTICBOX_BASE3_CAVITY["upper_m"], dtype=np.float64) - np.asarray(
            PLASTICBOX_BASE3_CAVITY["lower_m"], dtype=np.float64
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
            "can_fits_box_cavity": bool(np.all(cavity_size > 2.0 * can_half)),
            "scale_functional_point_exists": scale_point is not None and np.all(np.isfinite(np.asarray(scale_point, dtype=np.float64))),
            "beside_targets_on_table": all(-0.45 <= target[0] <= 0.45 and -0.35 <= target[1] <= 0.20 for target in beside_targets),
            "beside_targets_clear_box_scale": all(
                np.linalg.norm(target - box_xy) >= 0.10 and np.linalg.norm(target - scale_xy) >= 0.10
                for target in beside_targets
            ),
        }
        passed = base["task_feasible"] and all(checks.values())
        base.update({"task_feasible": passed, "physical_feasible": passed, "failure_type": None if passed else "f2_task_physical_contract", "evidence": checks})
        return base

    def _target_actor(self, scene, program, variant):
        actor_pose = _pose(scene.can)
        target = actor_pose.copy()
        relation = program["steps"][1]["relation"]
        if relation == "inside":
            target[:3] = transform_local_point(_pose(scene.box), PLASTICBOX_BASE3_CAVITY["target_center_local_m"])
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
        inside = verify_true_cavity_obb(can_pose, can_half, _pose(scene.box), PLASTICBOX_BASE3_CAVITY)["pass_true_cavity_obb"]
        scale_target = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
        on = top_surface_region(can_pose[:3], scale_target[:3], [0.07, 0.07], 0.06)
        radial = float(np.linalg.norm(can_pose[:2] - np.asarray(scene.stand.get_pose().p[:2])))
        beside = bool(0.12 <= radial <= 0.23 and can_pose[2] <= 0.83)
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
        for _ in range(required):
            scene.scene.step()
            linear, _ = _rigid_velocity(scene.bottle, "linear_velocity")
            angular, _ = _rigid_velocity(scene.bottle, "angular_velocity")
            linear_speeds.append(float(np.linalg.norm(linear)))
            angular_speeds.append(float(np.linalg.norm(angular)))
            pad_contacts.append(
                any(
                    bottle_name in (contact.bodies[0].entity.name, contact.bodies[1].entity.name)
                    and pad_name in (contact.bodies[0].entity.name, contact.bodies[1].entity.name)
                    for contact in scene.scene.get_contacts()
                )
            )
        footprint = footprint_inside_local_region(
            _pose(scene.bottle),
            _actor_half_extents(scene.bottle),
            _pose(scene.pad),
            [-0.07, -0.07, -0.01],
            [0.07, 0.07, 0.02],
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
        # The currently proposed finite GPU diagnostic is V->H plus return,
        # not a formal VVHH/VHVH/VHHV root rollout.
        axes = "VH"
        for event_index, axis in enumerate(axes):
            vector = np.asarray([0.05, 0, 0]) if axis == "H" else np.asarray([0, 0, 0.05])
            targets.extend(
                [
                    {"segment_id": f"event_{event_index}_{axis}_positive", "pose": np.concatenate((central[:3] + vector, central[3:]))},
                    {"segment_id": f"event_{event_index}_{axis}_negative", "pose": np.concatenate((central[:3] - vector, central[3:]))},
                    {"segment_id": f"event_{event_index}_{axis}_return", "pose": central},
                ]
            )
        actor_at_central = compose_pose(central, relative_pose(grasp, start_actor))
        release = actor_target_to_eef_pose(central, actor_at_central, start_actor)
        preplace = world_axis_offset_pose(release, 0.10)
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        targets.extend(
            [
                {"segment_id": "return_preplace", "pose": preplace},
                {"segment_id": "return_release", "pose": release},
                {"segment_id": "return_retreat", "pose": preplace},
                {"segment_id": "rest", "pose": rest},
            ]
        )
        return targets, {"execution_scope": "f3_release_diagnosis_VH_only", "event_order": axes, "target_actor_pose": start_actor.tolist(), "full_program_id": program["program_id"]}

    @staticmethod
    def _execute_event(scene, axis, event_index, metrics):
        center_eef = np.asarray(scene.robot.get_left_ee_pose()[:3], dtype=np.float64)
        center_actor = _pose(scene.bottle)[:3]
        scene.mark(f"event_{event_index}_{axis}_start")
        vector = (0.05, 0, 0) if axis == "H" else (0, 0, 0.05)
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
            [-0.07, -0.07, -0.01],
            [0.07, 0.07, 0.02],
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
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F3"]
        rollout_reset = _planner_reset(scene, planner_seed=20260828, variant_id="f3_VH_diagnosis")
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        _must_action(scene, scene.grasp_actor(scene.bottle, arm_tag=_arm_tag_left(), pre_grasp_dis=0.09), "prefix_grasp")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.12), "prefix_lift")
        held_eef_initial = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        held_actor_initial = _pose(scene.bottle)
        spec = realization_spec["planner_execution_spec"]
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
            "pass": False,
            "repair_probe_pass": repair_probe_pass,
            "full_f3_program_complete": False,
            "failure_reason": "runtime-v3_1 probe scope is V->H diagnosis only; formal F3 program was not executed",
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
            extra={"rollout_planner_reset_receipt": rollout_reset},
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

    def _object_place_targets(self, scene, actor, slot, prefix):
        pregrasp, grasp = scene.choose_grasp_pose(actor, arm_tag=_arm_tag_left(), pre_dis=0.09, target_dis=0)
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
        ]

    def build_targets(self, scene, program, planner_variant):
        common_pregrasp, common_grasp = scene.choose_grasp_pose(scene.common_x, arm_tag=_arm_tag_left(), pre_dis=0.09, target_dis=0)
        common_lift = world_axis_offset_pose(common_grasp, 0.10)
        target_actor = _pose(scene.common_x)
        target_actor[:3] = transform_local_point(_pose(scene.tray), TRAY_BASE0_SUPPORT_REGION["target_center_local_m"])
        common_release = actor_target_to_eef_pose(common_grasp, _pose(scene.common_x), target_actor)
        common_preplace = world_axis_offset_pose(common_release, 0.10)
        obstacle_tops = [float(_pose(getattr(scene, role))[2] + BLOCK_HALF_EXTENTS[2]) for role in ("a", "b", "c")]
        gripper_envelope = _left_gripper_below_eef_envelope(scene)
        envelope = minimum_f4_safe_carry_height(
            obstacle_tops,
            actor_half_height_m=0.022,
            gripper_below_eef_envelope_m=gripper_envelope["gripper_below_eef_envelope_m"],
            frozen_clearance_m=0.03,
        )
        safe = common_lift.copy()
        safe[2] = envelope["safe_eef_or_actor_center_z"]
        center = safe.copy()
        center[0] = -0.02
        above = common_preplace.copy()
        above[2] = safe[2]
        neutral = np.concatenate(([-0.15, -0.04, 0.95], np.asarray(common_grasp)[3:]))
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
        # The current bounded repair is common-X only.  Full A/B/C planner
        # chains remain implemented below for a later version, but are not
        # included in the unapproved 16-query route envelope.
        targets = list(common_targets)
        order = [step["object"] for step in program["steps"][1:]]
        return targets, {
            "execution_scope": "f4_common_x_route_repair_only",
            "route_id": planner_variant["variant_id"],
            "carry_envelope_version": envelope["carry_envelope_version"],
            "carry_envelope": envelope,
            "gripper_envelope_evidence": gripper_envelope,
            "tray_pose_changed": False,
            "object_order": order,
            "common_target_actor_pose": target_actor.tolist(),
        }

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        scene.initialize_trace(scene.common_x, "left", role_actors=scene.role_actors)
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F4"]
        rollout_reset = _planner_reset(
            scene,
            planner_seed=20260828,
            variant_id=realization_spec["planner_execution_spec"]["variant_id"],
        )
        non_targets = {"A": scene.a, "B": scene.b, "C": scene.c}
        non_target_baseline = _position_map(non_targets)
        non_target_stages = {"initial": _position_map(non_targets)}
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        spec = realization_spec["planner_execution_spec"]
        targets = spec["targets"]
        _must_action(scene, scene.grasp_actor(scene.common_x, arm_tag=_arm_tag_left(), pre_grasp_dis=0.09), "common_grasp")
        non_target_stages["after_common_grasp"] = _position_map(non_targets)
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.10), "common_lift")
        non_target_stages["after_common_lift"] = _position_map(non_targets)
        for target in targets[3:8]:
            _move_left(scene, target["pose"], target["segment_id"])
        non_target_stages["after_common_transport"] = _position_map(non_targets)
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "common_release")
        _wait_and_record(scene, 125)
        non_target_stages["after_common_release"] = _position_map(non_targets)
        _move_left(scene, targets[8]["pose"], "common_neutral")
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
        realized_eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
        neutral_position_error = float(np.linalg.norm(realized_eef[:3] - neutral_target[:3]))
        neutral_orientation_error = quaternion_orientation_error(realized_eef[3:], neutral_target[3:])
        eef_linear_speed = float(np.linalg.norm(scene.trace[-1]["eef_linear_velocity"]))
        eef_angular_speed = float(np.linalg.norm(scene.trace[-1]["eef_angular_velocity"]))
        common_checks = {
            "tray_footprint": footprint["pass_support_footprint"],
            "stable_window": bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "support_contact_window": bool(contacts) and all(contacts),
            "non_target_stability": non_target["pass"],
            "gripper_open": bool(scene.is_left_gripper_open()),
            "neutral_position": neutral_position_error <= PROVISIONAL_RUNTIME_THRESHOLDS["neutral_position_error_m"],
            "neutral_orientation": neutral_orientation_error <= PROVISIONAL_RUNTIME_THRESHOLDS["orientation_error"],
            "eef_linear_stationary": eef_linear_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_linear_speed_mps"],
            "eef_angular_stationary": eef_angular_speed <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
        }
        common_probe_pass = all(common_checks.values())
        semantic = {
            "pass": False,
            "common_x_repair_probe_pass": common_probe_pass,
            "common_x_checks": common_checks,
            "full_f4_program_complete": False,
            "failure_reason": "runtime-v3_1 route budget covers common-X only; A/B/C program was not executed",
            "common_tray_footprint": footprint,
            "support_contact_window": contacts,
            "stable_speed_window_mps": speeds,
            "non_target_verifier": non_target,
            "neutral_position_error_m": neutral_position_error,
            "neutral_orientation_error_rad": neutral_orientation_error,
            "route_id": spec["route_id"],
            "carry_envelope_version": spec["carry_envelope_version"],
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=executed_prefix,
            semantic_verifier=semantic,
            extra={"rollout_planner_reset_receipt": rollout_reset},
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
