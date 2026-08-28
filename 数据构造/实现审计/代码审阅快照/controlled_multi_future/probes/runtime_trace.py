"""Dense realized trace capture for audited RoboTwin probe scenes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..geometry import quaternion_angular_velocity
from ..raw_writer import ACTION_LAYOUT_DIMENSIONS, ACTION_LAYOUT_VERSION, pack_effective_setpoint


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


def _pose_array(value):
    if value is None:
        return np.full(7, np.nan, dtype=np.float64)
    if hasattr(value, "p") and hasattr(value, "q"):
        value = value.p.tolist() + value.q.tolist()
    return np.asarray(value, dtype=np.float64).reshape(7)


def is_selected_gripper_contact(actor_name, selected_gripper_links, body_pair):
    names = set(body_pair)
    return actor_name in names and bool(names.intersection(set(selected_gripper_links)))


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
    streams = {
        "controller_effective_setpoint": np.asarray([row["effective_setpoint"] for row in actions], dtype=np.float64),
        "requested_command": np.asarray([row["requested_command"] for row in actions], dtype=np.float64).copy(),
        "planner_target": np.asarray([row["planner_target"] for row in actions], dtype=np.float64),
        "gripper_command": np.asarray([row["gripper_command"] for row in actions], dtype=np.float64),
        "timestamps": np.asarray([row["timestamp"] for row in actions], dtype=np.float64),
        "component_masks": np.asarray([row["component_mask"] for row in actions], dtype=bool),
        "realized_qpos": np.asarray([row["joint_qpos"] for row in rows], dtype=np.float64),
        "realized_qvel": np.asarray([row["joint_qvel"] for row in rows], dtype=np.float64),
        "realized_eef": np.asarray([row["dual_eef"] for row in rows], dtype=np.float64),
        "field_metadata": {
            "controller_effective_setpoint": {"status": "measured", "source": "runtime joint drive targets plus normalized gripper drive targets"},
            "requested_command": {"status": "commanded", "source": "runtime Base_Task.take_dense_action control_seq"},
            "planner_target": {"status": "commanded", "source": "runtime left/right move_to_pose direct API arguments"},
            "realized_qpos": {"status": "measured", "source": "runtime complete dual-arm articulation get_qpos"},
            "realized_qvel": {"status": "measured", "source": "runtime complete dual-arm articulation get_qvel"},
            "realized_eef": {"status": "measured", "source": "runtime dual-arm EEF pose API"},
            "gripper_command": {"status": "commanded", "source": "runtime normalized gripper command"},
            "timestamps": {"status": "derived", "source": "runtime 250 Hz step index"},
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
        "gripper_aperture": np.asarray([row["gripper_aperture"] for row in rows], dtype=np.float64),
        "selected_gripper_contact": np.asarray([row["selected_gripper_contact"] for row in rows], dtype=bool),
        "selected_gripper_contact_count": np.asarray([row["selected_gripper_contact_count"] for row in rows], dtype=np.int64),
        "selected_gripper_contact_impulse": np.asarray([row["selected_gripper_contact_impulse"] for row in rows], dtype=np.float64),
        "contact_count": np.asarray([len(row["contact_pairs"]) for row in rows], dtype=np.int64),
        "planner_target_available": np.asarray([row["planner_target_available"] for row in actions], dtype=bool),
        "contact_pairs_json": np.asarray([json.dumps(row["contact_pairs"], sort_keys=True) for row in rows]),
        "field_metadata": {
            "object_pose": {"status": "measured", "source": "runtime SAPIEN actor pose API"},
            "object_linear_velocity": {"status": "mixed", "source": "runtime rigid component or 250 Hz position difference with measured mask"},
            "object_linear_velocity_measured": {"status": "derived", "source": "runtime rigid-component availability mask"},
            "object_angular_velocity": {"status": "mixed", "source": "runtime rigid component or 250 Hz quaternion difference with measured mask"},
            "object_angular_velocity_measured": {"status": "derived", "source": "runtime rigid-component availability mask"},
            "eef_linear_velocity": {"status": "derived", "source": "runtime 250 Hz EEF position difference"},
            "eef_angular_velocity": {"status": "derived", "source": "runtime 250 Hz EEF quaternion difference"},
            "gripper_aperture": {"status": "measured", "source": "runtime normalized gripper joint drive targets"},
            "selected_gripper_contact": {"status": "measured", "source": "runtime SAPIEN contact restricted to selected arm gripper links"},
            "selected_gripper_contact_count": {"status": "measured", "source": "runtime selected-arm SAPIEN contact-pair count"},
            "selected_gripper_contact_impulse": {"status": "measured", "source": "runtime selected-arm SAPIEN contact point impulse sum"},
            "contact_count": {"status": "measured", "source": "runtime all SAPIEN scene contact-pair count"},
            "planner_target_available": {"status": "derived", "source": "runtime per-arm direct planner-target presence"},
            "contact_pairs_json": {"status": "measured", "source": "runtime all SAPIEN scene contact body pairs"},
        },
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

    def initialize_trace(self, actor, arm="left"):
        self.trace_actor = actor
        if arm not in ("left", "right"):
            raise ValueError("trace arm must be left or right")
        self.trace_arm = arm
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
        self._planner_target = {"left": np.full(7, np.nan), "right": np.full(7, np.nan)}
        self._planner_target_available = {"left": False, "right": False}
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
        actor_name = _entity(self.trace_actor).get_name()
        selected = set(self.selected_gripper_links())
        pairs = []
        selected_count = 0
        selected_impulse = 0.0
        for contact in self.scene.get_contacts():
            names = [contact.bodies[0].entity.name, contact.bodies[1].entity.name]
            point_impulse = 0.0
            for point in getattr(contact, "points", []):
                impulse = getattr(point, "impulse", None)
                if impulse is not None:
                    point_impulse += float(np.linalg.norm(np.asarray(impulse, dtype=np.float64)))
            pairs.append({"body_a": names[0], "body_b": names[1], "point_count": len(getattr(contact, "points", [])), "impulse_norm_sum": point_impulse})
            if is_selected_gripper_contact(actor_name, selected, names):
                selected_count += 1
                selected_impulse += point_impulse
        return pairs, selected_count, selected_impulse

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
            dt = 1.0 / self.trace_frequency_hz
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
            "timestamp": self._step_index / self.trace_frequency_hz,
            "effective_setpoint": effective,
            "requested_command": requested,
            "planner_target": np.concatenate((self._planner_target["left"], self._planner_target["right"])),
            "planner_target_available": np.asarray((self._planner_target_available["left"], self._planner_target_available["right"]), dtype=bool),
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
            "gripper_aperture": np.asarray(effective_gripper, dtype=np.float64),
            "selected_gripper_links": self.selected_gripper_links(),
            "selected_gripper_contact": selected_contact_count > 0,
            "selected_gripper_contact_count": selected_contact_count,
            "selected_gripper_contact_impulse": selected_impulse,
            "contact_pairs": pairs,
            "initial_state": bool(initial_state),
        })
        self._step_index += 1

    def left_move_to_pose(self, *args, **kwargs):
        self._reserve_planner_query()
        pose = kwargs.get("pose", args[0] if args else None)
        self._planner_target["left"] = _pose_array(pose)
        self._planner_target_available["left"] = pose is not None
        result = super().left_move_to_pose(*args, **kwargs)
        status = result.get("status") if isinstance(result, dict) else "Failed"
        self.planner_queries.append({"query_index": self.planner_query_count, "arm": "left", "target_pose": self._planner_target["left"].tolist(), "status": status})
        return result

    def right_move_to_pose(self, *args, **kwargs):
        self._reserve_planner_query()
        pose = kwargs.get("pose", args[0] if args else None)
        self._planner_target["right"] = _pose_array(pose)
        self._planner_target_available["right"] = pose is not None
        result = super().right_move_to_pose(*args, **kwargs)
        status = result.get("status") if isinstance(result, dict) else "Failed"
        self.planner_queries.append({"query_index": self.planner_query_count, "arm": "right", "target_pose": self._planner_target["right"].tolist(), "status": status})
        return result

    def preflight_left_pose(self, pose):
        """Run a bounded planner query without mutating Base_Task.plan_success."""

        self._reserve_planner_query()
        self._planner_target["left"] = _pose_array(pose)
        self._planner_target_available["left"] = pose is not None
        result = self.robot.left_plan_path(self._planner_target["left"].tolist()) if pose is not None else None
        status = result.get("status") if isinstance(result, dict) else "Failed"
        self.planner_queries.append({
            "query_index": self.planner_query_count,
            "arm": "left",
            "query_type": "nonexecuting_preflight",
            "target_pose": self._planner_target["left"].tolist(),
            "status": status,
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
            if left_arm is not None and index < left_arm["position"].shape[0]:
                self._requested_position["left"] = np.asarray(left_arm["position"][index], dtype=np.float64)
                self._requested_velocity["left"] = np.asarray(left_arm["velocity"][index], dtype=np.float64)
                self._component_mask[0:6] = True
                self._component_mask[12:18] = True
                self.robot.set_arm_joints(left_arm["position"][index], left_arm["velocity"][index], "left")
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
            if right_gripper is not None and index < right_gripper["num_step"]:
                self._requested_gripper[1] = float(right_gripper["result"][index])
                self._component_mask[25] = True
                self.robot.set_gripper(right_gripper["result"][index], "right", right_gripper["per_step"])
            self.scene.step()
            self._record()
        return True

    def save_trace(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = getattr(self, "trace", [])
        arrays = {
            "step_index": np.asarray([row["step_index"] for row in rows], dtype=np.int64),
            "timestamp": np.asarray([row["timestamp"] for row in rows], dtype=np.float64),
            "controller_effective_setpoint": np.asarray([row["effective_setpoint"] for row in rows], dtype=np.float64),
            "requested_command": np.asarray([row["requested_command"] for row in rows], dtype=np.float64),
            "planner_target": np.asarray([row["planner_target"] for row in rows], dtype=np.float64),
            "planner_target_available": np.asarray([row["planner_target_available"] for row in rows], dtype=bool),
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
            "gripper_aperture": np.asarray([row["gripper_aperture"] for row in rows], dtype=np.float64),
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
                "timestamp": {"status": "derived", "source": "step_index divided by 250 Hz"},
                "controller_effective_setpoint": {"status": "measured", "source": "joint drive targets plus normalized gripper drive targets"},
                "requested_command": {"status": "commanded", "source": "Base_Task.take_dense_action control_seq"},
                "planner_target": {"status": "commanded", "source": "left_move_to_pose/right_move_to_pose pose argument"},
                "planner_target_available": {"status": "derived", "source": "per-arm direct planner target presence"},
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
                "gripper_aperture": {"status": "measured", "source": "normalized gripper joint drive targets"},
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
