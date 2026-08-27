"""Dense realized trace capture for audited RoboTwin probe scenes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..raw_writer import pack_effective_setpoint


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
            return np.asarray(value, dtype=np.float64).reshape(3)
    return np.zeros(3, dtype=np.float64)


def is_selected_gripper_contact(actor_name, selected_gripper_links, body_pair):
    names = set(body_pair)
    return actor_name in names and bool(names.intersection(set(selected_gripper_links)))


class DenseTraceMixin:
    trace_frequency_hz = 250

    def initialize_trace(self, actor, arm="left"):
        self.trace_actor = actor
        if arm not in ("left", "right"):
            raise ValueError("trace arm must be left or right")
        self.trace_arm = arm
        self.trace = []
        self.markers = {}
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
        self._gripper_command = list(self.robot.get_normal_real_gripper_val())
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
        qpos = np.asarray(self.robot.left_entity.get_qpos(), dtype=np.float64)
        qvel = np.asarray(self.robot.left_entity.get_qvel(), dtype=np.float64)
        pairs, selected_contact_count, selected_impulse = self._contacts()
        effective = pack_effective_setpoint(
            self._effective_position["left"], self._effective_velocity["left"], self._gripper_command[0],
            self._effective_position["right"], self._effective_velocity["right"], self._gripper_command[1],
        )
        eef_array = np.asarray(eef, dtype=np.float64)
        actor_array = np.asarray(actor_pose.p.tolist() + actor_pose.q.tolist(), dtype=np.float64)
        if self.trace:
            dt = 1.0 / self.trace_frequency_hz
            eef_linear = (eef_array[:3] - self.trace[-1]["eef"][:3]) / dt
            actor_linear_fallback = (actor_array[:3] - self.trace[-1]["actor_pose"][:3]) / dt
        else:
            eef_linear = np.zeros(3)
            actor_linear_fallback = np.zeros(3)
        actor_linear = _rigid_velocity(self.trace_actor, "linear_velocity")
        if not np.any(actor_linear):
            actor_linear = actor_linear_fallback
        self.trace.append({
            "step_index": self._step_index,
            "timestamp": self._step_index / self.trace_frequency_hz,
            "effective_setpoint": effective,
            "requested_command": effective.copy(),
            "planner_target": effective.copy(),
            "joint_qpos": qpos,
            "joint_qvel": qvel,
            "eef": eef_array,
            "eef_linear_velocity": eef_linear,
            "eef_angular_velocity": np.zeros(3),
            "actor_pose": actor_array,
            "actor_linear_velocity": actor_linear,
            "actor_angular_velocity": _rigid_velocity(self.trace_actor, "angular_velocity"),
            "gripper_command": np.asarray(self._gripper_command, dtype=np.float64),
            "gripper_aperture": np.asarray(self.robot.get_normal_real_gripper_val(), dtype=np.float64),
            "selected_gripper_links": self.selected_gripper_links(),
            "selected_gripper_contact": selected_contact_count > 0,
            "selected_gripper_contact_count": selected_contact_count,
            "selected_gripper_contact_impulse": selected_impulse,
            "contact_pairs": pairs,
            "initial_state": bool(initial_state),
        })
        self._step_index += 1

    def left_move_to_pose(self, *args, **kwargs):
        self.planner_query_count += 1
        return super().left_move_to_pose(*args, **kwargs)

    def right_move_to_pose(self, *args, **kwargs):
        self.planner_query_count += 1
        return super().right_move_to_pose(*args, **kwargs)

    def take_dense_action(self, control_seq, save_freq=-1):
        if not hasattr(self, "_gripper_command"):
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
            if left_arm is not None and index < left_arm["position"].shape[0]:
                self._effective_position["left"] = np.asarray(left_arm["position"][index], dtype=np.float64)
                self._effective_velocity["left"] = np.asarray(left_arm["velocity"][index], dtype=np.float64)
                self.robot.set_arm_joints(left_arm["position"][index], left_arm["velocity"][index], "left")
            if left_gripper is not None and index < left_gripper["num_step"]:
                self._gripper_command[0] = float(left_gripper["result"][index])
                self.robot.set_gripper(left_gripper["result"][index], "left", left_gripper["per_step"])
            if right_arm is not None and index < right_arm["position"].shape[0]:
                self._effective_position["right"] = np.asarray(right_arm["position"][index], dtype=np.float64)
                self._effective_velocity["right"] = np.asarray(right_arm["velocity"][index], dtype=np.float64)
                self.robot.set_arm_joints(right_arm["position"][index], right_arm["velocity"][index], "right")
            if right_gripper is not None and index < right_gripper["num_step"]:
                self._gripper_command[1] = float(right_gripper["result"][index])
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
            "joint_qpos": np.asarray([row["joint_qpos"] for row in rows], dtype=np.float64),
            "joint_qvel": np.asarray([row["joint_qvel"] for row in rows], dtype=np.float64),
            "eef_pose": np.asarray([row["eef"] for row in rows], dtype=np.float64),
            "eef_linear_velocity": np.asarray([row["eef_linear_velocity"] for row in rows], dtype=np.float64),
            "eef_angular_velocity": np.asarray([row["eef_angular_velocity"] for row in rows], dtype=np.float64),
            "object_pose": np.asarray([row["actor_pose"] for row in rows], dtype=np.float64),
            "object_linear_velocity": np.asarray([row["actor_linear_velocity"] for row in rows], dtype=np.float64),
            "object_angular_velocity": np.asarray([row["actor_angular_velocity"] for row in rows], dtype=np.float64),
            "gripper_command": np.asarray([row["gripper_command"] for row in rows], dtype=np.float64),
            "gripper_aperture": np.asarray([row["gripper_aperture"] for row in rows], dtype=np.float64),
            "selected_gripper_contact": np.asarray([row["selected_gripper_contact"] for row in rows], dtype=bool),
            "selected_gripper_contact_count": np.asarray([row["selected_gripper_contact_count"] for row in rows], dtype=np.int64),
            "selected_gripper_contact_impulse": np.asarray([row["selected_gripper_contact_impulse"] for row in rows], dtype=np.float64),
            "event_markers_json": np.asarray(json.dumps(self.markers, sort_keys=True)),
            "selected_gripper_links_json": np.asarray(json.dumps(self.selected_gripper_links(), sort_keys=True)),
            "contact_pairs_json": np.asarray([json.dumps(row["contact_pairs"], sort_keys=True) for row in rows]),
        }
        np.savez_compressed(path, **arrays)
        return {"path": str(path), "sample_count": len(rows), "fields": sorted(arrays)}
