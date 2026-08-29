"""Dense realized trace capture for audited RoboTwin probe scenes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..geometry import quaternion_angular_velocity
from ..raw_writer import ACTION_LAYOUT_DIMENSIONS, ACTION_LAYOUT_VERSION, pack_effective_setpoint


TRACE_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS = 1e-9


class PlannerQueryLimitExceeded(RuntimeError):
    pass


def _scalar(value, default=0.0):
    try:
        return float(np.asarray(value).reshape(-1)[0])
    except BaseException:
        return float(default)


def _joint_values(joints, getter):
    return np.asarray([_scalar(getattr(joint, getter)()) for joint in joints], dtype=np.float64)


def _entity(actor):
    return actor.actor if hasattr(actor, "actor") else actor


def _rigid_velocity(actor, attr):
    entity = _entity(actor)
    for component in entity.get_components():
        if hasattr(component, attr):
            value = getattr(component, attr)
            value = value() if callable(value) else value
            return np.asarray(value, dtype=np.float64).reshape(3), True
    return np.zeros(3, dtype=np.float64), False


def _dual_entity_values(robot, getter):
    """Read the complete realized articulation state without duplicating it."""

    left = np.asarray(getattr(robot.left_entity, getter)(), dtype=np.float64).reshape(-1)
    if robot.left_entity is robot.right_entity:
        return left
    right = np.asarray(getattr(robot.right_entity, getter)(), dtype=np.float64).reshape(-1)
    return np.concatenate((left, right))


def _gripper_joint_qpos(robot, arm):
    entity = robot.left_entity if arm == "left" else robot.right_entity
    gripper = robot.left_gripper if arm == "left" else robot.right_gripper
    qpos = np.asarray(entity.get_qpos(), dtype=np.float64).reshape(-1)
    active_joints = list(entity.get_active_joints())
    index_by_name = {joint.get_name(): index for index, joint in enumerate(active_joints)}
    values = []
    for joint_spec in gripper:
        name = joint_spec[0].get_name()
        if name not in index_by_name:
            raise ValueError(f"gripper joint {name!r} is absent from active articulation qpos")
        values.append(qpos[index_by_name[name]])
    if not values:
        raise ValueError(f"{arm} gripper has no auditable active joints")
    return np.asarray(values, dtype=np.float64)


def _pose_array(value):
    if value is None:
        return np.full(7, np.nan, dtype=np.float64)
    if hasattr(value, "p") and hasattr(value, "q"):
        value = value.p.tolist() + value.q.tolist()
    return np.asarray(value, dtype=np.float64).reshape(7)


def is_selected_gripper_contact(actor_name, selected_gripper_links, body_pair):
    names = set(body_pair)
    return actor_name in names and bool(names.intersection(set(selected_gripper_links)))


def _trace_arrays_sha256(streams, audit_streams) -> str:
    digest = hashlib.sha256()
    for namespace, values in (("stream", streams), ("audit", audit_streams)):
        for key in sorted(item for item in values if item != "field_metadata"):
            array = np.ascontiguousarray(values[key])
            digest.update(namespace.encode("utf-8"))
            digest.update(key.encode("utf-8"))
            digest.update(str(array.dtype).encode("ascii"))
            digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
            digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _planner_interval_arrays(actions):
    n = len(actions)
    active = np.asarray([row.get("planner_goal_active", [False, False]) for row in actions], dtype=bool).reshape(n, 2)
    query_ids = np.asarray([row.get("planner_query_id", [-1, -1]) for row in actions], dtype=np.int64).reshape(n, 2)
    sources = np.asarray([row.get("planner_goal_source", ["", ""]) for row in actions]).astype(str).reshape(n, 2)
    starts = np.full((n, 2), -1, dtype=np.int64)
    ends = np.full((n, 2), -1, dtype=np.int64)
    for arm_index in range(2):
        for query_id in sorted(set(int(value) for value in query_ids[:, arm_index] if int(value) >= 0)):
            indices = np.flatnonzero(active[:, arm_index] & (query_ids[:, arm_index] == query_id))
            if indices.size == 0:
                continue
            if not np.array_equal(indices, np.arange(indices[0], indices[-1] + 1)):
                raise ValueError("planner query active interval must be contiguous")
            starts[indices, arm_index] = int(indices[0])
            ends[indices, arm_index] = int(indices[-1] + 1)
    if np.any((~active) & (query_ids != -1)):
        raise ValueError("inactive planner rows must use query_id=-1")
    if np.any((~active) & (sources != "")):
        raise ValueError("inactive planner rows must use an empty source")
    return active, query_ids, sources, starts, ends


def trace_rows_to_raw_streams(rows):
    """Convert runtime-v2 trace rows into the N/N+1 raw contract.

    Row zero must be the pre-action realized state.  Every later row represents
    one applied controller step and its resulting state.
    """

    rows = list(rows)
    if len(rows) < 2 or rows[0].get("initial_state") is not True:
        raise ValueError("trace requires one explicit initial state followed by actions")
    if any(row.get("initial_state") for row in rows[1:]):
        raise ValueError("only trace row zero may be an initial state")
    actions = rows[1:]
    state_timestamps = np.asarray([row["timestamp"] for row in rows], dtype=np.float64)
    planner_active, planner_query_ids, planner_sources, planner_starts, planner_ends = _planner_interval_arrays(actions)
    streams = {
        "controller_effective_setpoint": np.asarray([row["effective_setpoint"] for row in actions], dtype=np.float64),
        "requested_command": np.asarray([row["requested_command"] for row in actions], dtype=np.float64).copy(),
        "planner_goal_eef_pose": np.asarray([row["planner_goal_eef_pose"] for row in actions], dtype=np.float64),
        "gripper_command": np.asarray([row["gripper_command"] for row in actions], dtype=np.float64),
        "action_interval_start_timestamps": state_timestamps[:-1],
        "action_interval_end_timestamps": state_timestamps[1:],
        "state_timestamps": state_timestamps,
        "component_masks": np.asarray([row["component_mask"] for row in actions], dtype=bool),
        "realized_qpos": np.asarray([row["joint_qpos"] for row in rows], dtype=np.float64),
        "realized_qvel": np.asarray([row["joint_qvel"] for row in rows], dtype=np.float64),
        "realized_eef": np.asarray([row["dual_eef"] for row in rows], dtype=np.float64),
        "field_metadata": {
            "controller_effective_setpoint": {"status": "measured", "source": "runtime joint drive targets plus normalized gripper drive targets"},
            "requested_command": {"status": "commanded", "source": "runtime Base_Task.take_dense_action control_seq"},
            "planner_goal_eef_pose": {"status": "commanded", "source": "runtime left/right move_to_pose direct EEF goal arguments"},
            "realized_qpos": {"status": "measured", "source": "runtime complete dual-arm articulation get_qpos"},
            "realized_qvel": {"status": "measured", "source": "runtime complete dual-arm articulation get_qvel"},
            "realized_eef": {"status": "measured", "source": "runtime dual-arm EEF pose API"},
            "gripper_command": {"status": "commanded", "source": "runtime normalized gripper command"},
            "action_interval_start_timestamps": {"status": "derived", "source": "runtime state_timestamps[:-1]"},
            "action_interval_end_timestamps": {"status": "derived", "source": "runtime state_timestamps[1:]"},
            "state_timestamps": {"status": "derived", "source": "runtime 250 Hz state step index"},
            "component_masks": {"status": "derived", "source": "runtime commanded component availability"},
        },
    }
    audit_streams = {
        "object_pose": np.asarray([row["actor_pose"] for row in rows], dtype=np.float64),
        "object_linear_velocity": np.asarray([row["actor_linear_velocity"] for row in rows], dtype=np.float64),
        "object_linear_velocity_measured": np.asarray([row.get("actor_linear_velocity_measured", False) for row in rows], dtype=bool),
        "object_angular_velocity": np.asarray([row["actor_angular_velocity"] for row in rows], dtype=np.float64),
        "object_angular_velocity_measured": np.asarray([row.get("actor_angular_velocity_measured", False) for row in rows], dtype=bool),
        "eef_linear_velocity": np.asarray([row["eef_linear_velocity"] for row in rows], dtype=np.float64),
        "eef_angular_velocity": np.asarray([row["eef_angular_velocity"] for row in rows], dtype=np.float64),
        "gripper_drive_target_readback": np.asarray([row["gripper_drive_target_readback"] for row in rows], dtype=np.float64),
        "realized_left_gripper_joint_qpos": np.asarray([row["realized_left_gripper_joint_qpos"] for row in rows], dtype=np.float64),
        "realized_right_gripper_joint_qpos": np.asarray([row["realized_right_gripper_joint_qpos"] for row in rows], dtype=np.float64),
        "selected_gripper_contact": np.asarray([row["selected_gripper_contact"] for row in rows], dtype=bool),
        "selected_gripper_contact_count": np.asarray([row["selected_gripper_contact_count"] for row in rows], dtype=np.int64),
        "selected_gripper_contact_impulse": np.asarray([row["selected_gripper_contact_impulse"] for row in rows], dtype=np.float64),
        "contact_count": np.asarray([len(row["contact_pairs"]) for row in rows], dtype=np.int64),
        "planner_goal_available": planner_active.copy(),
        "planner_query_id": planner_query_ids,
        "planner_goal_active": planner_active,
        "planner_goal_source": planner_sources,
        "planner_goal_start_step": planner_starts,
        "planner_goal_end_step": planner_ends,
        "contact_pairs_json": np.asarray([json.dumps(row["contact_pairs"], sort_keys=True) for row in rows]),
        "field_metadata": {
            "object_pose": {"status": "measured", "source": "runtime SAPIEN actor pose API"},
            "object_linear_velocity": {"status": "mixed", "source": "runtime rigid component or 250 Hz position difference with measured mask"},
            "object_linear_velocity_measured": {"status": "derived", "source": "runtime rigid-component availability mask"},
            "object_angular_velocity": {"status": "mixed", "source": "runtime rigid component or 250 Hz quaternion difference with measured mask"},
            "object_angular_velocity_measured": {"status": "derived", "source": "runtime rigid-component availability mask"},
            "eef_linear_velocity": {"status": "derived", "source": "runtime 250 Hz EEF position difference"},
            "eef_angular_velocity": {"status": "derived", "source": "runtime 250 Hz EEF quaternion difference"},
            "gripper_drive_target_readback": {"status": "measured", "source": "runtime normalized gripper joint drive targets; not physical aperture"},
            "realized_left_gripper_joint_qpos": {"status": "measured", "source": "runtime left articulation active-joint qpos"},
            "realized_right_gripper_joint_qpos": {"status": "measured", "source": "runtime right articulation active-joint qpos"},
            "selected_gripper_contact": {"status": "measured", "source": "runtime SAPIEN contact restricted to selected arm gripper links"},
            "selected_gripper_contact_count": {"status": "measured", "source": "runtime selected-arm SAPIEN contact-pair count"},
            "selected_gripper_contact_impulse": {"status": "measured", "source": "runtime selected-arm SAPIEN contact point impulse sum"},
            "contact_count": {"status": "measured", "source": "runtime all SAPIEN scene contact-pair count"},
            "planner_goal_available": {"status": "derived", "source": "runtime per-arm direct planner-goal presence"},
            "planner_query_id": {"status": "derived", "source": "runtime planner query ID active on each action interval"},
            "planner_goal_active": {"status": "derived", "source": "runtime planner control active on each action interval"},
            "planner_goal_source": {"status": "derived", "source": "runtime move API that produced the active planner control"},
            "planner_goal_start_step": {"status": "derived", "source": "first action interval carrying the planner query ID"},
            "planner_goal_end_step": {"status": "derived", "source": "exclusive last action interval carrying the planner query ID"},
            "contact_pairs_json": {"status": "measured", "source": "runtime all SAPIEN scene contact body pairs"},
        },
    }
    role_names = sorted({role for row in rows for role in row.get("role_actor_poses", {})})
    for role in role_names:
        field = f"role_object_pose__{role}"
        if any(role not in row.get("role_actor_poses", {}) for row in rows):
            raise ValueError(f"role actor {role} is not present in every trace row")
        audit_streams[field] = np.asarray([row["role_actor_poses"][role] for row in rows], dtype=np.float64)
        audit_streams["field_metadata"][field] = {
            "status": "measured",
            "source": f"runtime SAPIEN pose API for scene role {role}",
        }
    return streams, audit_streams


class DenseTraceMixin:
    trace_frequency_hz = 250

    def _reserve_planner_query(self):
        limit = getattr(self, "planner_query_limit", None)
        current = getattr(self, "planner_query_count", 0)
        if limit is not None and current >= int(limit):
            raise PlannerQueryLimitExceeded(f"planner query limit exhausted: {current}/{limit}")
        self.planner_query_count = current + 1
        return self.planner_query_count

    def initialize_trace(self, actor, arm="left", role_actors=None):
        self.trace_actor = actor
        self.trace_contact_actor = actor
        if arm not in ("left", "right"):
            raise ValueError("trace arm must be left or right")
        self.trace_arm = arm
        self.trace_role_actors = dict(role_actors or {})
        self.trace = []
        self.markers = {}
        self.planner_queries = []
        self.planner_query_count = 0
        self._step_index = 0
        self._effective_position = {
            "left": _joint_values(self.robot.left_arm_joints, "get_drive_target"),
            "right": _joint_values(self.robot.right_arm_joints, "get_drive_target"),
        }
        self._effective_velocity = {
            "left": _joint_values(self.robot.left_arm_joints, "get_drive_velocity_target"),
            "right": _joint_values(self.robot.right_arm_joints, "get_drive_velocity_target"),
        }
        self._requested_position = {key: value.copy() for key, value in self._effective_position.items()}
        self._requested_velocity = {key: value.copy() for key, value in self._effective_velocity.items()}
        self._requested_gripper = list(self.robot.get_normal_real_gripper_val())
        if not hasattr(self.scene, "get_timestep"):
            raise RuntimeError("SAPIEN scene does not expose get_timestep")
        self.simulator_timestep_seconds = float(self.scene.get_timestep())
        self.control_steps_per_action = 1
        self.effective_action_interval_seconds = self.simulator_timestep_seconds * self.control_steps_per_action
        if not np.isclose(
            self.simulator_timestep_seconds,
            1.0 / self.trace_frequency_hz,
            rtol=0.0,
            atol=TRACE_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
        ):
            raise RuntimeError(
                f"scene timestep {self.simulator_timestep_seconds} does not match frozen 250 Hz"
            )
        self.scene_timestep_source = "SAPIEN Scene.get_timestep() after Base_Task.setup_scene"
        self._active_planner_query = {"left": None, "right": None}
        self._component_mask = np.zeros(26, dtype=bool)
        self.mark("trace_start")
        self._record(initial_state=True)

    def mark(self, name):
        if hasattr(self, "trace"):
            self.markers[name] = max(0, len(self.trace) - 1)

    def selected_gripper_links(self):
        if self.trace_arm == "left":
            joints = self.robot.left_gripper
            fixed = self.robot.left_fix_gripper_name
        else:
            joints = self.robot.right_gripper
            fixed = self.robot.right_fix_gripper_name
        return sorted(set(list(fixed) + [joint[0].child_link.get_name() for joint in joints]))

    def _contacts(self):
        actor_name = _entity(self.trace_contact_actor).get_name()
        selected = set(self.selected_gripper_links())
        pairs = []
        selected_count = 0
        selected_impulse = 0.0
        for contact in self.scene.get_contacts():
            names = [contact.bodies[0].entity.name, contact.bodies[1].entity.name]
            point_impulse = 0.0
            point_normals = []
            point_positions = []
            for point in getattr(contact, "points", []):
                impulse = getattr(point, "impulse", None)
                if impulse is not None:
                    point_impulse += float(np.linalg.norm(np.asarray(impulse, dtype=np.float64)))
                normal = getattr(point, "normal", None)
                if normal is not None:
                    point_normals.append(np.asarray(normal, dtype=np.float64).reshape(3).tolist())
                position = getattr(point, "position", None)
                if position is not None:
                    point_positions.append(np.asarray(position, dtype=np.float64).reshape(3).tolist())
            pairs.append({
                "body_a": names[0],
                "body_b": names[1],
                "point_count": len(getattr(contact, "points", [])),
                "impulse_norm_sum": point_impulse,
                "point_normals": point_normals,
                "point_positions": point_positions,
            })
            if is_selected_gripper_contact(actor_name, selected, names):
                selected_count += 1
                selected_impulse += point_impulse
        return pairs, selected_count, selected_impulse

    def set_trace_contact_actor(self, actor):
        """Switch contact subject without changing the object_pose stream identity."""

        self.trace_contact_actor = actor

    def _record(self, initial_state=False):
        if not hasattr(self, "trace_actor"):
            return
        eef = self.robot.get_left_ee_pose() if self.trace_arm == "left" else self.robot.get_right_ee_pose()
        actor_pose = self.trace_actor.get_pose()
        qpos = _dual_entity_values(self.robot, "get_qpos")
        qvel = _dual_entity_values(self.robot, "get_qvel")
        pairs, selected_contact_count, selected_impulse = self._contacts()
        effective_position = {
            "left": _joint_values(self.robot.left_arm_joints, "get_drive_target"),
            "right": _joint_values(self.robot.right_arm_joints, "get_drive_target"),
        }
        effective_velocity = {
            "left": _joint_values(self.robot.left_arm_joints, "get_drive_velocity_target"),
            "right": _joint_values(self.robot.right_arm_joints, "get_drive_velocity_target"),
        }
        effective_gripper = list(self.robot.get_normal_real_gripper_val())
        effective = pack_effective_setpoint(
            effective_position["left"], effective_velocity["left"], effective_gripper[0],
            effective_position["right"], effective_velocity["right"], effective_gripper[1],
        )
        requested = pack_effective_setpoint(
            self._requested_position["left"], self._requested_velocity["left"], self._requested_gripper[0],
            self._requested_position["right"], self._requested_velocity["right"], self._requested_gripper[1],
        )
        eef_array = np.asarray(eef, dtype=np.float64)
        dual_eef = np.concatenate((np.asarray(self.robot.get_left_ee_pose(), dtype=np.float64), np.asarray(self.robot.get_right_ee_pose(), dtype=np.float64)))
        actor_array = np.asarray(actor_pose.p.tolist() + actor_pose.q.tolist(), dtype=np.float64)
        if self.trace:
            dt = self.simulator_timestep_seconds
            eef_linear = (eef_array[:3] - self.trace[-1]["eef"][:3]) / dt
            eef_angular = quaternion_angular_velocity(self.trace[-1]["eef"][3:], eef_array[3:], dt)
            actor_linear_fallback = (actor_array[:3] - self.trace[-1]["actor_pose"][:3]) / dt
            actor_angular_fallback = quaternion_angular_velocity(self.trace[-1]["actor_pose"][3:], actor_array[3:], dt)
        else:
            eef_linear = np.zeros(3)
            eef_angular = np.zeros(3)
            actor_linear_fallback = np.zeros(3)
            actor_angular_fallback = np.zeros(3)
        actor_linear, actor_linear_measured = _rigid_velocity(self.trace_actor, "linear_velocity")
        if not actor_linear_measured:
            actor_linear = actor_linear_fallback
        actor_angular, actor_angular_measured = _rigid_velocity(self.trace_actor, "angular_velocity")
        if not actor_angular_measured:
            actor_angular = actor_angular_fallback
        self.trace.append({
            "step_index": self._step_index,
            "timestamp": self._step_index * self.simulator_timestep_seconds,
            "effective_setpoint": effective,
            "requested_command": requested,
            "planner_goal_eef_pose": np.concatenate(tuple(
                np.asarray(self._active_planner_query[arm]["goal_eef_pose"], dtype=np.float64)
                if self._active_planner_query[arm] is not None else np.full(7, np.nan)
                for arm in ("left", "right")
            )),
            "planner_goal_available": np.asarray(tuple(self._active_planner_query[arm] is not None for arm in ("left", "right")), dtype=bool),
            "planner_goal_active": np.asarray(tuple(self._active_planner_query[arm] is not None for arm in ("left", "right")), dtype=bool),
            "planner_query_id": np.asarray(tuple(
                int(self._active_planner_query[arm]["query_id"])
                if self._active_planner_query[arm] is not None else -1
                for arm in ("left", "right")
            ), dtype=np.int64),
            "planner_goal_source": tuple(
                str(self._active_planner_query[arm]["source"])
                if self._active_planner_query[arm] is not None else ""
                for arm in ("left", "right")
            ),
            "component_mask": self._component_mask.copy(),
            "joint_qpos": qpos,
            "joint_qvel": qvel,
            "eef": eef_array,
            "dual_eef": dual_eef,
            "eef_linear_velocity": eef_linear,
            "eef_angular_velocity": eef_angular,
            "actor_pose": actor_array,
            "actor_linear_velocity": actor_linear,
            "actor_linear_velocity_measured": actor_linear_measured,
            "actor_angular_velocity": actor_angular,
            "actor_angular_velocity_measured": actor_angular_measured,
            "gripper_command": np.asarray(self._requested_gripper, dtype=np.float64),
            "gripper_drive_target_readback": np.asarray(effective_gripper, dtype=np.float64),
            "realized_left_gripper_joint_qpos": _gripper_joint_qpos(self.robot, "left"),
            "realized_right_gripper_joint_qpos": _gripper_joint_qpos(self.robot, "right"),
            "selected_gripper_links": self.selected_gripper_links(),
            "selected_gripper_contact": selected_contact_count > 0,
            "selected_gripper_contact_count": selected_contact_count,
            "selected_gripper_contact_impulse": selected_impulse,
            "contact_pairs": pairs,
            "role_actor_poses": {role: _pose_array(actor.get_pose()) for role, actor in self.trace_role_actors.items()},
            "initial_state": bool(initial_state),
        })
        self._step_index += 1

    def left_move_to_pose(self, *args, **kwargs):
        query_id = self._reserve_planner_query()
        pose = kwargs.get("pose", args[0] if args else None)
        goal = _pose_array(pose)
        result = super().left_move_to_pose(*args, **kwargs)
        status = result.get("status") if isinstance(result, dict) else "Failed"
        item = {"query_id": query_id, "arm": "left", "source": "left_move_to_pose", "goal_eef_pose": goal.tolist(), "status": status, "start_step": None, "end_step": None}
        self.planner_queries.append(item)
        if isinstance(result, dict):
            result["_cmf_planner_query"] = dict(item)
        return result

    def right_move_to_pose(self, *args, **kwargs):
        query_id = self._reserve_planner_query()
        pose = kwargs.get("pose", args[0] if args else None)
        goal = _pose_array(pose)
        result = super().right_move_to_pose(*args, **kwargs)
        status = result.get("status") if isinstance(result, dict) else "Failed"
        item = {"query_id": query_id, "arm": "right", "source": "right_move_to_pose", "goal_eef_pose": goal.tolist(), "status": status, "start_step": None, "end_step": None}
        self.planner_queries.append(item)
        if isinstance(result, dict):
            result["_cmf_planner_query"] = dict(item)
        return result

    def preflight_left_pose(self, pose):
        """Run a bounded planner query without mutating Base_Task.plan_success."""

        query_id = self._reserve_planner_query()
        goal = _pose_array(pose)
        result = self.robot.left_plan_path(goal.tolist()) if pose is not None else None
        status = result.get("status") if isinstance(result, dict) else "Failed"
        self.planner_queries.append({
            "query_id": query_id,
            "arm": "left",
            "query_type": "nonexecuting_preflight",
            "source": "preflight_left_pose",
            "goal_eef_pose": goal.tolist(),
            "status": status,
            "start_step": None,
            "end_step": None,
        })
        return result

    def take_dense_action(self, control_seq, save_freq=-1):
        if not hasattr(self, "_requested_gripper"):
            return super().take_dense_action(control_seq, save_freq=save_freq)
        left_arm, left_gripper, right_arm, right_gripper = (
            control_seq["left_arm"], control_seq["left_gripper"], control_seq["right_arm"], control_seq["right_gripper"]
        )
        max_len = 0
        if left_arm is not None:
            max_len = max(max_len, left_arm["position"].shape[0])
        if left_gripper is not None:
            max_len = max(max_len, left_gripper["num_step"])
        if right_arm is not None:
            max_len = max(max_len, right_arm["position"].shape[0])
        if right_gripper is not None:
            max_len = max(max_len, right_gripper["num_step"])
        for index in range(max_len):
            self._component_mask = np.zeros(26, dtype=bool)
            self._active_planner_query = {"left": None, "right": None}
            if left_arm is not None and index < left_arm["position"].shape[0]:
                self._requested_position["left"] = np.asarray(left_arm["position"][index], dtype=np.float64)
                self._requested_velocity["left"] = np.asarray(left_arm["velocity"][index], dtype=np.float64)
                self._component_mask[0:6] = True
                self._component_mask[12:18] = True
                self.robot.set_arm_joints(left_arm["position"][index], left_arm["velocity"][index], "left")
                self._active_planner_query["left"] = left_arm.get("_cmf_planner_query")
            if left_gripper is not None and index < left_gripper["num_step"]:
                self._requested_gripper[0] = float(left_gripper["result"][index])
                self._component_mask[24] = True
                self.robot.set_gripper(left_gripper["result"][index], "left", left_gripper["per_step"])
            if right_arm is not None and index < right_arm["position"].shape[0]:
                self._requested_position["right"] = np.asarray(right_arm["position"][index], dtype=np.float64)
                self._requested_velocity["right"] = np.asarray(right_arm["velocity"][index], dtype=np.float64)
                self._component_mask[6:12] = True
                self._component_mask[18:24] = True
                self.robot.set_arm_joints(right_arm["position"][index], right_arm["velocity"][index], "right")
                self._active_planner_query["right"] = right_arm.get("_cmf_planner_query")
            if right_gripper is not None and index < right_gripper["num_step"]:
                self._requested_gripper[1] = float(right_gripper["result"][index])
                self._component_mask[25] = True
                self.robot.set_gripper(right_gripper["result"][index], "right", right_gripper["per_step"])
            self.scene.step()
            self._record()
            action_step = len(self.trace) - 2
            for arm in ("left", "right"):
                active_query = self._active_planner_query[arm]
                if active_query is None:
                    continue
                for query in self.planner_queries:
                    if query["query_id"] == active_query["query_id"] and query["arm"] == arm:
                        if query["start_step"] is None:
                            query["start_step"] = action_step
                        query["end_step"] = action_step + 1
                        break
        self._component_mask = np.zeros(26, dtype=bool)
        self._active_planner_query = {"left": None, "right": None}
        return True

    def trace_provenance(self):
        streams, audit_streams = trace_rows_to_raw_streams(self.trace)
        return {
            "simulator_timing": {
                "simulator_timestep_seconds": self.simulator_timestep_seconds,
                "control_steps_per_action": self.control_steps_per_action,
                "effective_action_interval_seconds": self.effective_action_interval_seconds,
                "scene_timestep_source": self.scene_timestep_source,
            },
            "planner_queries": [dict(item) for item in self.planner_queries],
            "trace_source_sha256": _trace_arrays_sha256(streams, audit_streams),
        }

    def save_trace(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = getattr(self, "trace", [])
        arrays = {
            "step_index": np.asarray([row["step_index"] for row in rows], dtype=np.int64),
            "timestamp": np.asarray([row["timestamp"] for row in rows], dtype=np.float64),
            "controller_effective_setpoint": np.asarray([row["effective_setpoint"] for row in rows], dtype=np.float64),
            "requested_command": np.asarray([row["requested_command"] for row in rows], dtype=np.float64),
            "planner_goal_eef_pose": np.asarray([row["planner_goal_eef_pose"] for row in rows], dtype=np.float64),
            "planner_goal_available": np.asarray([row["planner_goal_available"] for row in rows], dtype=bool),
            "planner_goal_active": np.asarray([row["planner_goal_active"] for row in rows], dtype=bool),
            "planner_query_id": np.asarray([row["planner_query_id"] for row in rows], dtype=np.int64),
            "planner_goal_source": np.asarray([row["planner_goal_source"] for row in rows]),
            "component_masks": np.asarray([row["component_mask"] for row in rows], dtype=bool),
            "joint_qpos": np.asarray([row["joint_qpos"] for row in rows], dtype=np.float64),
            "joint_qvel": np.asarray([row["joint_qvel"] for row in rows], dtype=np.float64),
            "eef_pose": np.asarray([row["eef"] for row in rows], dtype=np.float64),
            "dual_eef_pose": np.asarray([row["dual_eef"] for row in rows], dtype=np.float64),
            "eef_linear_velocity": np.asarray([row["eef_linear_velocity"] for row in rows], dtype=np.float64),
            "eef_angular_velocity": np.asarray([row["eef_angular_velocity"] for row in rows], dtype=np.float64),
            "object_pose": np.asarray([row["actor_pose"] for row in rows], dtype=np.float64),
            "object_linear_velocity": np.asarray([row["actor_linear_velocity"] for row in rows], dtype=np.float64),
            "object_linear_velocity_measured": np.asarray([row["actor_linear_velocity_measured"] for row in rows], dtype=bool),
            "object_angular_velocity": np.asarray([row["actor_angular_velocity"] for row in rows], dtype=np.float64),
            "object_angular_velocity_measured": np.asarray([row["actor_angular_velocity_measured"] for row in rows], dtype=bool),
            "gripper_command": np.asarray([row["gripper_command"] for row in rows], dtype=np.float64),
            "gripper_drive_target_readback": np.asarray([row["gripper_drive_target_readback"] for row in rows], dtype=np.float64),
            "realized_left_gripper_joint_qpos": np.asarray([row["realized_left_gripper_joint_qpos"] for row in rows], dtype=np.float64),
            "realized_right_gripper_joint_qpos": np.asarray([row["realized_right_gripper_joint_qpos"] for row in rows], dtype=np.float64),
            "selected_gripper_contact": np.asarray([row["selected_gripper_contact"] for row in rows], dtype=bool),
            "selected_gripper_contact_count": np.asarray([row["selected_gripper_contact_count"] for row in rows], dtype=np.int64),
            "selected_gripper_contact_impulse": np.asarray([row["selected_gripper_contact_impulse"] for row in rows], dtype=np.float64),
            "event_markers_json": np.asarray(json.dumps(self.markers, sort_keys=True)),
            "selected_gripper_links_json": np.asarray(json.dumps(self.selected_gripper_links(), sort_keys=True)),
            "contact_pairs_json": np.asarray([json.dumps(row["contact_pairs"], sort_keys=True) for row in rows]),
            "initial_state": np.asarray([row["initial_state"] for row in rows], dtype=bool),
            "action_layout_version": np.asarray(ACTION_LAYOUT_VERSION),
            "action_layout_dimensions_json": np.asarray(json.dumps(ACTION_LAYOUT_DIMENSIONS)),
            "planner_queries_json": np.asarray(json.dumps(self.planner_queries, sort_keys=True)),
            "field_sources_json": np.asarray(json.dumps({
                "step_index": {"status": "derived", "source": "monotonic runtime trace counter"},
                "timestamp": {"status": "derived", "source": "step_index multiplied by SAPIEN Scene.get_timestep()"},
                "controller_effective_setpoint": {"status": "measured", "source": "joint drive targets plus normalized gripper drive targets"},
                "requested_command": {"status": "commanded", "source": "Base_Task.take_dense_action control_seq"},
                "planner_goal_eef_pose": {"status": "commanded", "source": "left_move_to_pose/right_move_to_pose direct EEF goal argument"},
                "planner_goal_available": {"status": "derived", "source": "per-arm direct planner goal presence"},
                "planner_goal_active": {"status": "derived", "source": "planner control active on the current action interval"},
                "planner_query_id": {"status": "derived", "source": "planner query ID attached to the executed control"},
                "planner_goal_source": {"status": "derived", "source": "move API that created the executed planner control"},
                "component_masks": {"status": "derived", "source": "per-step commanded component presence"},
                "joint_qpos": {"status": "measured", "source": "complete dual-arm articulation get_qpos"},
                "joint_qvel": {"status": "measured", "source": "complete dual-arm articulation get_qvel"},
                "eef_pose": {"status": "measured", "source": "robot EEF pose API"},
                "dual_eef_pose": {"status": "measured", "source": "left and right robot EEF pose APIs"},
                "eef_linear_velocity": {"status": "derived", "source": "250 Hz position difference"},
                "eef_angular_velocity": {"status": "derived", "source": "250 Hz quaternion difference"},
                "object_pose": {"status": "measured", "source": "SAPIEN actor pose API"},
                "object_linear_velocity": {"status": "measured_or_derived", "source": "rigid component when available, otherwise 250 Hz position difference; per-row mask saved"},
                "object_angular_velocity": {"status": "measured_or_derived", "source": "rigid component when available, otherwise 250 Hz quaternion difference; per-row mask saved"},
                "gripper_command": {"status": "commanded", "source": "normalized take_dense_action gripper request"},
                "gripper_drive_target_readback": {"status": "measured", "source": "normalized gripper joint drive targets; not physical aperture"},
                "realized_left_gripper_joint_qpos": {"status": "measured", "source": "left articulation active-joint qpos"},
                "realized_right_gripper_joint_qpos": {"status": "measured", "source": "right articulation active-joint qpos"},
                "selected_gripper_contact": {"status": "measured", "source": "SAPIEN body-pair contacts restricted to selected arm links"},
                "selected_gripper_contact_count": {"status": "measured", "source": "SAPIEN contact pair count for selected arm"},
                "selected_gripper_contact_impulse": {"status": "measured", "source": "SAPIEN contact point impulses when available"},
                "contact_pairs_json": {"status": "measured", "source": "all SAPIEN scene contact body pairs"},
                "event_markers_json": {"status": "derived", "source": "explicit runtime event markers"},
                "selected_gripper_links_json": {"status": "configured", "source": "selected robot arm gripper link names"},
                "initial_state": {"status": "derived", "source": "trace lifecycle marker"},
            }, sort_keys=True)),
        }
        np.savez_compressed(path, **arrays)
        return {"path": str(path), "sample_count": len(rows), "fields": sorted(arrays)}
