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
from .probes.runtime_trace import trace_rows_to_raw_streams
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
            end_qpos = positions[-1].copy()
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


def _execute_target_sequence(scene, execution_spec):
    segment_receipts = []
    previous_end = hash_array(np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64))
    for target in execution_spec["targets"]:
        control = _move_left(scene, target["pose"], target["segment_id"])
        current = np.asarray(control["position"], dtype=np.float64)[-1]
        end_hash = hash_array(current)
        segment_receipts.append(
            {
                "segment_id": target["segment_id"],
                "start_qpos_sha256": previous_end,
                "end_qpos_sha256": end_hash,
                "planner_status": "Success",
                "executed": True,
            }
        )
        previous_end = end_hash
    return segment_receipts


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
        checks = {
            "roles": set(scene.role_actors) == expected,
            "target_role": role in ("red", "green", "blue"),
            "same_block_half_extents": all(np.allclose(_actor_half_extents(getattr(scene, name)), BLOCK_HALF_EXTENTS) for name in ("red", "green", "blue")),
            "box_cavity_larger_than_block": np.all(
                np.asarray(PLASTICBOX_BASE3_CAVITY["upper_m"]) - np.asarray(PLASTICBOX_BASE3_CAVITY["lower_m"]) > 2 * BLOCK_HALF_EXTENTS
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
        role = program["target_role"]
        actor = getattr(scene, role)
        non_targets = {name: getattr(scene, name) for name in ("red", "green", "blue") if name != role}
        baseline = _position_map(non_targets)
        scene.initialize_trace(actor, "left", role_actors=scene.role_actors)
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F1"]
        prefix_start = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "prefix_open")
        spec = realization_spec["planner_execution_spec"]
        _move_left(scene, spec["targets"][0]["pose"], "common_cluster_neutral")
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        prefix_end_action = len(scene.trace) - 1
        prefix_end = anchor_capture(scene)
        executed_prefix = _prefix_evidence(
            scene,
            target_role=role,
            prefix_start_action_index=prefix_start_action,
            prefix_end_action_index=prefix_end_action,
            start_anchor=prefix_start,
            end_anchor=prefix_end,
        )
        _must_action(scene, scene.grasp_actor(actor, arm_tag=_arm_tag_left(), pre_grasp_dis=0.09), f"grasp_{role}")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.12), f"lift_{role}")
        for target in spec["targets"][4:8]:
            _move_left(scene, target["pose"], target["segment_id"])
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "release")
        _wait_and_record(scene, 75)
        _move_left(scene, spec["targets"][8]["pose"], "retreat")
        _move_left(scene, spec["targets"][9]["pose"], "rest")
        _wait_and_record(scene, 75)
        inside = verify_true_cavity_obb(_pose(actor), BLOCK_HALF_EXTENTS, _pose(scene.box), PLASTICBOX_BASE3_CAVITY)
        stages = {"final": _position_map(non_targets)}
        non_target = verify_staged_non_target_displacement(baseline, stages, PROVISIONAL_RUNTIME_THRESHOLDS["non_target_displacement_m"])
        _, speeds, contacts = _stable_and_support(scene, actor, scene.box)
        checks = {
            "true_inside": inside["pass_true_cavity_obb"],
            "non_target": non_target["pass"],
            "stable": bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "continuous_box_contact": bool(contacts) and all(contacts),
            "gripper_open": bool(scene.is_left_gripper_open()),
        }
        return _raw_result(
            scene,
            program=program,
            realization_spec=realization_spec,
            executed_prefix=executed_prefix,
            semantic_verifier={"pass": all(checks.values()), "checks": checks, "inside": inside, "non_target": non_target},
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
        checks = {
            "roles": set(scene.role_actors) == {"main_can", "box", "scale", "stand"},
            "same_object": program["steps"][0].get("object") == "main_object",
            "left_arm_fixed": True,
            "relation": program["steps"][1].get("relation") in ("inside", "on", "beside"),
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
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        _must_action(scene, scene.grasp_actor(scene.can, arm_tag=_arm_tag_left(), pre_grasp_dis=0.08), "prefix_grasp_can")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.12), "prefix_lift_can")
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        prefix_end_action = len(scene.trace) - 1
        end_anchor = anchor_capture(scene)
        executed_prefix = _prefix_evidence(scene, target_role=program["program_id"], prefix_start_action_index=prefix_start_action, prefix_end_action_index=prefix_end_action, start_anchor=start_anchor, end_anchor=end_anchor)
        spec = realization_spec["planner_execution_spec"]
        for target in spec["targets"][3:5]:
            _move_left(scene, target["pose"], target["segment_id"])
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
        semantic = {
            "pass": exclusive[relation] and sum(bool(value) for value in exclusive.values()) == 1 and bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "exclusive_relations": exclusive,
            "target_relation": relation,
            "support_window": support,
        }
        return _raw_result(scene, program=program, realization_spec=realization_spec, executed_prefix=executed_prefix, semantic_verifier=semantic)


class F3RunnerV3_1(BaseFamilyRunnerV3_1):
    family = "F3"

    def canonical_prefix(self, programs):
        return {"prefix_id": "f3_grasp_central_shared_first_v_v1_1", "ops": ["grasp_bottle", "lift", "central", "V"], "shared_first_V": True}

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

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        start_actor = _pose(scene.bottle)
        scene.initialize_trace(scene.bottle, "left", role_actors=scene.role_actors)
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F3"]
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
        before_release_pose = _pose(scene.bottle)
        target_pose = np.asarray(spec["target_actor_pose"], dtype=np.float64)
        samples = {
            "before_release": {
                "bottle_position_error_m": float(np.linalg.norm(before_release_pose[:3] - target_pose[:3])),
                "bottle_orientation_error_rad": quaternion_angular_error(before_release_pose[3:], target_pose[3:]),
                "eef_tracking_error_m": float(np.linalg.norm(np.asarray(scene.robot.get_left_ee_pose()[:3]) - np.asarray(return_release["pose"][:3]))),
                "bottle_footprint_inside_pad": True,
                "stable_window_pass": False,
                "support_pass": False,
            }
        }
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "release")
        sample_steps = {1, 5, 10, 25, 50, 125, 250}
        for step in range(1, 251):
            _wait_and_record(scene, 1)
            if step in sample_steps:
                pose = _pose(scene.bottle)
                samples[f"after_release_{step}"] = {
                    "bottle_position_error_m": float(np.linalg.norm(pose[:3] - target_pose[:3])),
                    "bottle_orientation_error_rad": quaternion_angular_error(pose[3:], target_pose[3:]),
                    "eef_tracking_error_m": 0.0,
                    "bottle_footprint_inside_pad": footprint_inside_local_region(pose, _actor_half_extents(scene.bottle), _pose(scene.pad), [-0.07, -0.07, -0.01], [0.07, 0.07, 0.02], (0, 1))["pass_support_footprint"],
                    "stable_window_pass": False,
                    "support_pass": any("f3_original_pad" in (item["body_a"], item["body_b"]) for item in scene.trace[-1]["contact_pairs"]),
                }
        _move_left(scene, return_retreat["pose"], "return_retreat")
        _move_left(scene, rest["pose"], "rest")
        _wait_and_record(scene, 75)
        final_pose = _pose(scene.bottle)
        _, speeds, contacts = _stable_and_support(scene, scene.bottle, scene.pad)
        samples["after_rest"] = {
            "bottle_position_error_m": float(np.linalg.norm(final_pose[:3] - target_pose[:3])),
            "bottle_orientation_error_rad": quaternion_angular_error(final_pose[3:], target_pose[3:]),
            "eef_tracking_error_m": 0.0,
            "bottle_footprint_inside_pad": footprint_inside_local_region(final_pose, _actor_half_extents(scene.bottle), _pose(scene.pad), [-0.07, -0.07, -0.01], [0.07, 0.07, 0.02], (0, 1))["pass_support_footprint"],
            "stable_window_pass": bool(speeds) and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "support_pass": bool(contacts) and all(contacts),
        }
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
        repair_probe_pass = diagnosis["final_return_equivalence"] and motion["pass"]
        semantic = {
            "pass": False,
            "repair_probe_pass": repair_probe_pass,
            "full_f3_program_complete": False,
            "failure_reason": "runtime-v3_1 probe scope is V->H diagnosis only; formal F3 program was not executed",
            "diagnosis": diagnosis,
            "grasp_transform": grasp,
            "samples": samples,
            "realized_motion": motion,
        }
        return _raw_result(scene, program=program, realization_spec=realization_spec, executed_prefix=executed_prefix, semantic_verifier=semantic)


class F4RunnerV3_1(BaseFamilyRunnerV3_1):
    family = "F4"

    def canonical_prefix(self, programs):
        return {"prefix_id": "f4_common_x_to_tray_neutral_v1_1", "ops": ["place_common_X_in_tray", "return_branch_neutral"], "programs": [item["program_id"] for item in programs]}

    def planner_audit_variants(self, frozen_program):
        return [{"variant_id": route_id} for route_id in F4_ROUTE_ORDER]

    def audit_task_physical_feasibility(self, scene, program):
        base = super().audit_task_physical_feasibility(scene, program)
        checks = {
            "roles": set(scene.role_actors) == {"common_x", "A", "B", "C", "common_tray", "slot_A", "slot_B", "slot_C"},
            "common_first": program["steps"][0].get("object") == "common_X",
            "order": "".join(step["object"] for step in program["steps"][1:]) in ("ABC", "ACB", "BAC"),
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
        envelope = minimum_f4_safe_carry_height(obstacle_tops, actor_half_height_m=0.022, gripper_below_eef_envelope_m=0.06, frozen_clearance_m=0.03)
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
        role_map = {"A": (scene.a, scene.slot_a), "B": (scene.b, scene.slot_b), "C": (scene.c, scene.slot_c)}
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
            "tray_pose_changed": False,
            "object_order": order,
            "common_target_actor_pose": target_actor.tolist(),
        }

    def rollout(self, scene, program, realization_spec, *, anchor_capture):
        scene.initialize_trace(scene.common_x, "left", role_actors=scene.role_actors)
        scene.planner_query_limit = FAMILY_PLANNER_LIMITS["F4"]
        start_anchor = anchor_capture(scene)
        prefix_start_action = len(scene.trace) - 1
        spec = realization_spec["planner_execution_spec"]
        targets = spec["targets"]
        _must_action(scene, scene.grasp_actor(scene.common_x, arm_tag=_arm_tag_left(), pre_grasp_dis=0.09), "common_grasp")
        _must_action(scene, scene.move_by_displacement(arm_tag=_arm_tag_left(), z=0.10), "common_lift")
        for target in targets[3:8]:
            _move_left(scene, target["pose"], target["segment_id"])
        _must_action(scene, scene.open_gripper(_arm_tag_left(), pos=1.0), "common_release")
        _wait_and_record(scene, 125)
        _move_left(scene, targets[8]["pose"], "common_neutral")
        _wait_and_record(scene, MINIMUM_NEUTRAL_CONFIRMATION_STEPS)
        prefix_end_action = len(scene.trace) - 1
        end_anchor = anchor_capture(scene)
        executed_prefix = _prefix_evidence(scene, target_role=program["program_id"], prefix_start_action_index=prefix_start_action, prefix_end_action_index=prefix_end_action, start_anchor=start_anchor, end_anchor=end_anchor)
        _wait_and_record(scene, 75)
        footprint = footprint_inside_local_region(
            _pose(scene.common_x), BLOCK_HALF_EXTENTS, _pose(scene.tray),
            TRAY_BASE0_SUPPORT_REGION["lower_m"], TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        _, speeds, contacts = _stable_and_support(scene, scene.common_x, scene.tray)
        common_probe_pass = (
            footprint["pass_support_footprint"]
            and bool(speeds)
            and max(speeds) <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"]
            and bool(contacts)
            and all(contacts)
        )
        semantic = {
            "pass": False,
            "common_x_repair_probe_pass": common_probe_pass,
            "full_f4_program_complete": False,
            "failure_reason": "runtime-v3_1 route budget covers common-X only; A/B/C program was not executed",
            "common_tray_footprint": footprint,
            "support_contact_window": contacts,
            "stable_speed_window_mps": speeds,
            "route_id": spec["route_id"],
            "carry_envelope_version": spec["carry_envelope_version"],
        }
        return _raw_result(scene, program=program, realization_spec=realization_spec, executed_prefix=executed_prefix, semantic_verifier=semantic)


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
