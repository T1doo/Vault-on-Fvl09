"""Bounded F3 physical closure probe using the new vertical asset.

This is a qualification attempt, never a pilot collection run.  It records
the full grasp/lift/V/H/return/open sequence and leaves acceptance to the
V2.1 verifier in the coordinator receipt.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from envs.utils.action import ArmTag
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from ..family_runners_v3_1 import _execute_control, _must_action, _move_arm, _wait_and_record
from .scene import RedesignF3Scene
from .canonical import atomic_write_json


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def _eef(scene):
    return np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)


def _event_rows(scene, start: int, end: int):
    return scene.trace[start : end + 1]


def run(output: str | Path) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f3_redesign_closure_probe_v1",
        "family": "F3",
        "purpose": "qualification",
        "collection": False,
        "formal_data": False,
        "stage0_data": False,
        "status": "running",
        "action_scene_count": 0,
        "solver_problem_count": 0,
        "event_order": ["grasp", "micro_lift", "V", "H", "return_support", "open_separate", "empty_hand_exit"],
    }
    started = time.monotonic()
    initialize_cleanup_fields(receipt)
    args = _args("F3", output / "scene")
    args.update({"seed": 20260908, "task_name": "cmf_f3_redesign_closure", "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    try:
        with managed_scene(RedesignF3Scene, args, receipt, "f3-redesign-closure") as scene:
            scene.initialize_trace(scene.bottle, "left", scene.role_actors)
            scene.mark("current")
            current = {"bottle": _pose(scene.bottle).tolist(), "eef": _eef(scene).tolist(), "asset": scene._cmf_redesign_asset_spec}
            scene.mark("anchor")
            anchor = {"bottle": _pose(scene.bottle).tolist(), "eef": _eef(scene).tolist()}
            receipt["current"] = current
            receipt["anchor"] = anchor

            grasp_actions = scene.grasp_actor(scene.bottle, ArmTag("left"), pre_grasp_dis=0.09, grasp_dis=0.0, gripper_pos=0.0, contact_point_id=0)
            _must_action(scene, grasp_actions, "f3_grasp")
            receipt["action_scene_count"] += len(grasp_actions[1])
            _wait_and_record(scene, 250)
            grasp_end = len(scene.trace) - 1

            eef_before_lift = _eef(scene)
            lifted = eef_before_lift.copy()
            lifted[2] += 0.025
            _move_arm(scene, lifted, "f3_micro_lift")
            receipt["action_scene_count"] += 1
            _wait_and_record(scene, 50)
            lift_end = len(scene.trace) - 1

            def delta(dx, dz, label):
                _must_action(scene, scene.move_by_displacement(ArmTag("left"), x=dx, z=dz), label)
                receipt["action_scene_count"] += 1
                _wait_and_record(scene, 20)

            v_start = len(scene.trace) - 1
            delta(0.0, -0.05, "f3_V_negative")
            delta(0.0, 0.10, "f3_V_positive")
            delta(0.0, -0.05, "f3_V_return")
            v_end = len(scene.trace) - 1
            h_start = len(scene.trace) - 1
            delta(-0.05, 0.0, "f3_H_negative")
            delta(0.10, 0.0, "f3_H_positive")
            delta(-0.05, 0.0, "f3_H_return")
            h_end = len(scene.trace) - 1

            _move_arm(scene, lifted, "f3_return_height")
            receipt["action_scene_count"] += 1
            _wait_and_record(scene, 20)
            _move_arm(scene, eef_before_lift, "f3_return_support")
            receipt["action_scene_count"] += 1
            _wait_and_record(scene, 50)
            support_end = len(scene.trace) - 1
            _must_action(scene, scene.open_gripper(ArmTag("left"), pos=1.0), "f3_open_exit")
            receipt["action_scene_count"] += 1
            _wait_and_record(scene, 50)
            open_end = len(scene.trace) - 1
            open_eef = _eef(scene)
            exit_target = open_eef.copy()
            exit_target[2] += 0.05
            exit_target[0] += 0.10
            _move_arm(scene, exit_target, "f3_empty_hand_exit")
            receipt["action_scene_count"] += 1
            _wait_and_record(scene, 50)
            exit_end = len(scene.trace) - 1

            rows = scene.trace
            grasp_rows = _event_rows(scene, max(0, grasp_end - 49), grasp_end)
            lift_rows = _event_rows(scene, max(0, lift_end - 49), lift_end)
            v_rows = _event_rows(scene, v_start, v_end)
            h_rows = _event_rows(scene, h_start, h_end)
            support_rows = _event_rows(scene, max(0, support_end - 49), support_end)
            exit_rows = _event_rows(scene, max(0, exit_end - 49), exit_end)
            baseline_bottle = np.asarray(anchor["bottle"][:3], dtype=np.float64)
            lift_bottle = np.asarray([row["actor_pose"][:3] for row in lift_rows], dtype=np.float64)
            lift_rise = float(np.max(lift_bottle[:, 2] - baseline_bottle[2])) if len(lift_bottle) else 0.0
            lift_delta = lift_bottle - lift_bottle[0] if len(lift_bottle) else np.zeros((0, 3))
            def support_contact(row):
                for pair in row.get("contact_pairs", []):
                    bodies = {str(pair.get("body_a", "")), str(pair.get("body_b", ""))}
                    if "f3_redesign_bottle" in bodies and "f3_redesign_support_pad" in bodies:
                        return True
                return False

            def actor_axis_range(rows, axis):
                values = [float(row["actor_pose"][axis]) for row in rows]
                return (max(values) - min(values)) if values else 0.0

            receipt["events"] = {
                "grasp": {"rows": len(grasp_rows), "selected_contact_fraction": float(np.mean([row.get("selected_gripper_contact", False) for row in grasp_rows])) if grasp_rows else 0.0},
                "micro_lift": {"rows": len(lift_rows), "rise_m": lift_rise, "max_translation_drift_m": float(np.max(np.linalg.norm(lift_delta, axis=1))) if len(lift_delta) else None},
                "V": {"rows": len(v_rows), "eef_min_z": float(min(row["eef"][2] for row in v_rows)), "eef_max_z": float(max(row["eef"][2] for row in v_rows)), "actor_range_m": actor_axis_range(v_rows, 2)},
                "H": {"rows": len(h_rows), "eef_min_x": float(min(row["eef"][0] for row in h_rows)), "eef_max_x": float(max(row["eef"][0] for row in h_rows)), "actor_range_m": actor_axis_range(h_rows, 0)},
                "return_support": {"rows": len(support_rows), "support_contact_fraction": float(np.mean([support_contact(row) for row in support_rows])) if support_rows else 0.0},
                "open_separate": {"rows": open_end - max(0, open_end - 49), "selected_contact_fraction": float(np.mean([row.get("selected_gripper_contact", False) for row in _event_rows(scene, max(0, open_end - 49), open_end)])) if open_end >= 0 else 0.0},
                "empty_hand_exit": {"rows": len(exit_rows), "selected_contact_fraction": float(np.mean([row.get("selected_gripper_contact", False) for row in exit_rows])) if exit_rows else 0.0},
            }
            receipt["gates"] = {
                "planner_and_grasp_trace": len(grasp_rows) >= 50,
                "real_rise_at_least_20mm": lift_rise >= 0.020,
                "lift_translation_within_5mm": receipt["events"]["micro_lift"]["max_translation_drift_m"] is not None and receipt["events"]["micro_lift"]["max_translation_drift_m"] <= 0.005,
                "V_and_H_realized": len(v_rows) >= 3 and len(h_rows) >= 3 and receipt["events"]["V"]["actor_range_m"] >= 0.02 and receipt["events"]["H"]["actor_range_m"] >= 0.02,
                "return_support_identity": len(support_rows) >= 20 and receipt["events"]["return_support"]["support_contact_fraction"] >= 0.8,
                # V2.1 permits legal fingertip contact while the jaws are
                # opening; the hard release gate is empty-hand contact-free
                # exit after the opening window.
                "release_disengaged": receipt["events"]["empty_hand_exit"]["selected_contact_fraction"] == 0.0,
            }
            receipt["solver_problem_count"] = int(getattr(scene, "planner_query_count", 0))
            trace_path = output / "trace.npz"
            receipt["trace"] = scene.save_trace(trace_path)
            receipt["trace_path"] = str(trace_path)
            receipt["status"] = "qualification_pass" if all(receipt["gates"].values()) else "qualification_failed_gates"
    except BaseException as exc:
        receipt["status"] = "qualification_failed_execution"
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        receipt["status"] = cleanup_status(receipt, receipt["status"])
        receipt["elapsed_seconds"] = time.monotonic() - started
        atomic_write_json(output / "f3_closure_receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(args.output)
    raise SystemExit(0 if result.get("status") == "qualification_pass" else 1)


if __name__ == "__main__":
    main()
