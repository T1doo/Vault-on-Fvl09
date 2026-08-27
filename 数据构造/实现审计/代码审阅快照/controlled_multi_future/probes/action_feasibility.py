"""Finite nonformal F1--F4 action probes with realized-state traces."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

import numpy as np
import sapien

from envs.utils.action import ArmTag
from .scene_inspection import F1Scene, F2Scene, F3Scene, F4Scene, _args
from ..signals import closed_loop_event_metrics


class TraceMixin:
    def start_trace(self, actor, arm="left"):
        self.trace_actor = actor
        self.trace_arm = ArmTag(arm)
        self.trace = []
        self.markers = {}
        self.mark("trace_start")

    def mark(self, name):
        if hasattr(self, "trace"):
            self.markers[name] = len(self.trace)

    def _contact(self):
        actor_name = self.trace_actor.get_name()
        grippers = set(self.robot.gripper_name)
        for contact in self.scene.get_contacts():
            names = [contact.bodies[0].entity.name, contact.bodies[1].entity.name]
            if actor_name in names and any(name in grippers for name in names):
                return True
        return False

    def _record(self):
        if not hasattr(self, "trace_actor"):
            return
        eef = self.robot.get_left_ee_pose() if self.trace_arm == "left" else self.robot.get_right_ee_pose()
        actor_pose = self.trace_actor.get_pose()
        self.trace.append({
            "eef": eef,
            "actor": actor_pose.p.tolist() + actor_pose.q.tolist(),
            "gripper": self.robot.get_normal_real_gripper_val(),
            "contact": self._contact(),
        })

    def take_dense_action(self, control_seq, save_freq=-1):
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
                self.robot.set_arm_joints(left_arm["position"][index], left_arm["velocity"][index], "left")
            if left_gripper is not None and index < left_gripper["num_step"]:
                self.robot.set_gripper(left_gripper["result"][index], "left", left_gripper["per_step"])
            if right_arm is not None and index < right_arm["position"].shape[0]:
                self.robot.set_arm_joints(right_arm["position"][index], right_arm["velocity"][index], "right")
            if right_gripper is not None and index < right_gripper["num_step"]:
                self.robot.set_gripper(right_gripper["result"][index], "right", right_gripper["per_step"])
            self.scene.step()
            self._record()
        return True

    def save_trace(self, path: Path):
        if not self.trace:
            np.savez_compressed(path, eef=np.empty((0, 7)), actor=np.empty((0, 7)), gripper=np.empty((0, 2)), contact=np.empty((0,), dtype=bool))
            return
        np.savez_compressed(
            path,
            eef=np.asarray([row["eef"] for row in self.trace]),
            actor=np.asarray([row["actor"] for row in self.trace]),
            gripper=np.asarray([row["gripper"] for row in self.trace]),
            contact=np.asarray([row["contact"] for row in self.trace], dtype=bool),
        )


class TraceF1(TraceMixin, F1Scene):
    pass


class TraceF2(TraceMixin, F2Scene):
    pass


class TraceF3(TraceMixin, F3Scene):
    pass


class TraceF4(TraceMixin, F4Scene):
    pass


def _base_receipt(family, physical_index, uuid):
    timeout = {"F1": 900, "F2": 2700, "F3": 1800, "F4": 1200}[family]
    return {"schema_version": "cmf_action_feasibility_v1", "purpose": "nonformal_feasibility", "formal_data": False, "stage0_data": False, "attempt_limit": 1, "timeout_seconds": timeout, "family": family, "physical_gpu_index": physical_index, "expected_gpu_uuid": uuid, "pid": os.getpid(), "status": "running"}


def _run_f1(output: Path):
    scene = TraceF1()
    scene.setup_demo(**_args("F1", output))
    initial = {name: actor.get_pose().p.copy() for name, actor in (("red", scene.red), ("green", scene.green), ("blue", scene.blue))}
    scene.start_trace(scene.red, "left")
    arm = ArmTag("left")
    scene.mark("grasp_start")
    scene.move(scene.grasp_actor(scene.red, arm_tag=arm, pre_grasp_dis=0.09))
    scene.move(scene.move_by_displacement(arm_tag=arm, z=0.10))
    scene.mark("place_start")
    scene.move(scene.place_actor(scene.red, arm_tag=arm, target_pose=scene.box.get_functional_point(0), functional_point_id=0, constrain="free", pre_dis=0.08, dis=0.02))
    scene.move(scene.move_by_displacement(arm_tag=arm, z=0.08))
    scene.move(scene.back_to_origin(arm_tag=arm))
    target_xy = np.asarray(scene.box.get_functional_point(0)[:2])
    result = {
        "plan_success": bool(scene.plan_success),
        "red_to_box_xy_error": float(np.linalg.norm(scene.red.get_pose().p[:2] - target_xy)),
        "green_displacement": float(np.linalg.norm(scene.green.get_pose().p - initial["green"])),
        "blue_displacement": float(np.linalg.norm(scene.blue.get_pose().p - initial["blue"])),
        "left_gripper_open": bool(scene.is_left_gripper_open()),
        "trace_steps": len(scene.trace),
        "markers": scene.markers,
    }
    scene.save_trace(output / "trace.npz")
    scene.close_env(clear_cache=True)
    return result


def _run_f2(output: Path):
    results = {}
    for relation in ("inside", "on", "beside"):
        relation_dir = output / relation
        relation_dir.mkdir(parents=True, exist_ok=False)
        scene = TraceF2()
        scene.setup_demo(**_args("F2", relation_dir))
        scene.start_trace(scene.can, "left")
        arm = ArmTag("left")
        scene.move(scene.grasp_actor(scene.can, arm_tag=arm, pre_grasp_dis=0.08))
        scene.move(scene.move_by_displacement(arm_tag=arm, z=0.10))
        if relation == "inside":
            target = scene.box.get_functional_point(0)
        elif relation == "on":
            target = scene.scale.get_functional_point(0)
        else:
            reference = scene.stand.get_pose()
            target = [reference.p[0] - 0.13, reference.p[1], 0.76] + scene.can.get_pose().q.tolist()
        scene.mark(f"{relation}_place_start")
        scene.move(scene.place_actor(scene.can, arm_tag=arm, target_pose=target, constrain="free", pre_dis=0.08, dis=0.01))
        scene.move(scene.move_by_displacement(arm_tag=arm, z=0.08))
        scene.move(scene.back_to_origin(arm_tag=arm))
        can = scene.can.get_pose().p
        if relation == "inside":
            error = float(np.linalg.norm(can[:2] - np.asarray(scene.box.get_functional_point(0)[:2])))
            passed = error < 0.05
        elif relation == "on":
            fp = np.asarray(scene.scale.get_functional_point(0)[:3])
            error = float(np.linalg.norm(can[:2] - fp[:2]))
            passed = error < 0.05 and can[2] >= fp[2] - 0.02
        else:
            ref = scene.stand.get_pose().p
            error = float(np.linalg.norm(can[:2] - ref[:2]))
            passed = 0.08 <= error <= 0.20 and can[2] <= 0.82
        results[relation] = {"plan_success": bool(scene.plan_success), "predicate_pass_provisional": bool(passed), "predicate_measurement": error, "left_gripper_open": bool(scene.is_left_gripper_open()), "modelname": "071_can", "model_id": 1, "arm": "left", "trace_steps": len(scene.trace), "markers": scene.markers}
        scene.save_trace(relation_dir / "trace.npz")
        scene.close_env(clear_cache=True)
        if not results[relation]["plan_success"]:
            break
    return {"plan_success": len(results) == 3 and all(item["plan_success"] for item in results.values()), "relations": results}


def _run_f3(output: Path):
    scene = TraceF3()
    scene.setup_demo(**_args("F3", output))
    bottle_start = scene.bottle.get_pose()
    scene.start_trace(scene.bottle, "left")
    arm = ArmTag("left")
    scene.move(scene.grasp_actor(scene.bottle, arm_tag=arm, pre_grasp_dis=0.09))
    scene.move(scene.move_by_displacement(arm_tag=arm, z=0.12))
    now = scene.robot.get_left_ee_pose()
    neutral = [-0.08, -0.05, 0.95] + now[3:]
    scene.move(scene.move_to_pose(arm_tag=arm, target_pose=neutral))
    center = np.asarray(scene.robot.get_left_ee_pose()[:3])

    def event(name, axis):
        scene.mark(name + "_start")
        if axis == "V":
            scene.move(scene.move_by_displacement(arm_tag=arm, z=0.05))
            scene.move(scene.move_by_displacement(arm_tag=arm, z=-0.10))
            scene.move(scene.move_by_displacement(arm_tag=arm, z=0.05))
        else:
            scene.move(scene.move_by_displacement(arm_tag=arm, x=0.05))
            scene.move(scene.move_by_displacement(arm_tag=arm, x=-0.10))
            scene.move(scene.move_by_displacement(arm_tag=arm, x=0.05))
        scene.mark(name + "_end")
        start, end = scene.markers[name + "_start"], scene.markers[name + "_end"]
        samples = np.asarray([row["eef"][:3] for row in scene.trace[start:end]])
        contacts = [row["contact"] for row in scene.trace[start:end]]
        metrics = closed_loop_event_metrics(samples, center, 2 if axis == "V" else 0)
        metrics["contact_fraction"] = float(np.mean(contacts)) if contacts else 0.0
        return metrics

    metrics = {"single_V": event("single_V", "V"), "single_H": event("single_H", "H"), "VH_V": event("VH_V", "V"), "VH_H": event("VH_H", "H")}
    scene.mark("return_place_start")
    scene.move(scene.place_actor(scene.bottle, arm_tag=arm, target_pose=bottle_start.p.tolist() + bottle_start.q.tolist(), constrain="free", pre_dis=0.08, dis=0.01))
    scene.move(scene.move_by_displacement(arm_tag=arm, z=0.08))
    scene.move(scene.back_to_origin(arm_tag=arm))
    final = scene.bottle.get_pose()
    result = {"plan_success": bool(scene.plan_success), "metrics": metrics, "bottle_return_position_error": float(np.linalg.norm(final.p - bottle_start.p)), "left_gripper_open": bool(scene.is_left_gripper_open()), "trace_steps": len(scene.trace), "markers": scene.markers}
    scene.save_trace(output / "trace.npz")
    scene.close_env(clear_cache=True)
    return result


def _run_f4(output: Path):
    scene = TraceF4()
    scene.setup_demo(**_args("F4", output))
    scene.start_trace(scene.a, "left")
    arm = ArmTag("left")
    q = scene.robot.get_left_ee_pose()[3:]
    neutral = [-0.15, -0.04, 0.95] + q
    scene.move(scene.move_to_pose(arm_tag=arm, target_pose=neutral))
    neutral_realized = np.asarray(scene.robot.get_left_ee_pose()[:3])
    scene.mark("block_start")
    scene.move(scene.grasp_actor(scene.a, arm_tag=arm, pre_grasp_dis=0.09))
    scene.move(scene.move_by_displacement(arm_tag=arm, z=0.08))
    target = [-0.15, -0.17, 0.764, 0, 1, 0, 0]
    scene.move(scene.place_actor(scene.a, arm_tag=arm, target_pose=target, functional_point_id=0, constrain="align", pre_dis=0.08, dis=0.02))
    scene.move(scene.move_by_displacement(arm_tag=arm, z=0.08))
    scene.move(scene.move_to_pose(arm_tag=arm, target_pose=neutral))
    scene.mark("block_end")
    final_eef = np.asarray(scene.robot.get_left_ee_pose()[:3])
    slot_error = float(np.linalg.norm(scene.a.get_pose().p[:2] - np.asarray(target[:2])))
    other_initial_roles_unchanged = {role: scene.role_actors[role].get_pose().p.tolist() for role in ("B", "C")}
    result = {"plan_success": bool(scene.plan_success), "slot_xy_error": slot_error, "slot_predicate_pass_provisional": slot_error < 0.04, "neutral_return_error": float(np.linalg.norm(final_eef - neutral_realized)), "left_gripper_open": bool(scene.is_left_gripper_open()), "trace_steps": len(scene.trace), "markers": scene.markers, "other_object_final_positions": other_initial_roles_unchanged}
    scene.save_trace(output / "trace.npz")
    scene.close_env(clear_cache=True)
    return result


RUNNERS = {"F1": _run_f1, "F2": _run_f2, "F3": _run_f3, "F4": _run_f4}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=tuple(RUNNERS), required=True)
    parser.add_argument("--physical-index", type=int, choices=(4, 5, 6, 7), required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    receipt = _base_receipt(args.family, args.physical_index, args.expected_uuid)
    try:
        if os.environ.get("CUDA_VISIBLE_DEVICES") != args.expected_uuid:
            raise RuntimeError("CUDA_VISIBLE_DEVICES does not match expected UUID")
        args.output.mkdir(parents=True, exist_ok=False)
        result = RUNNERS[args.family](args.output)
        receipt.update({"status": "passed_nonformal_action_probe" if result.get("plan_success", False) else "failed_nonformal_action_probe", "result": result})
        code = 0 if result.get("plan_success", False) else 1
    except BaseException as exc:
        receipt.update({"status": "failed_nonformal_action_probe", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        code = 1
    finally:
        receipt["elapsed_seconds"] = time.time() - started
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
