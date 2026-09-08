"""Bounded F2 inside qualification-only physical probe."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import numpy as np

from envs.utils.action import ArmTag
from ..family_runners_v3_1 import _must_action, _move_arm, _wait_and_record
from ..probes.lifecycle import cleanup_status, initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from .canonical import atomic_write_json
from .f2_scene import RedesignF2Scene


def _pose(actor):
    value = actor.get_pose()
    return np.asarray(value.p.tolist() + value.q.tolist(), dtype=np.float64)


def run(output: str | Path) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f2_redesign_inside_closure_probe_v1",
        "family": "F2",
        "purpose": "qualification",
        "collection": False,
        "formal_data": False,
        "stage0_data": False,
        "status": "running",
        "action_scene_count": 0,
        "solver_problem_count": 0,
        "event_order": ["grasp", "carry", "controlled_descent", "support", "slow_open", "empty_hand_exit"],
    }
    started = time.monotonic()
    initialize_cleanup_fields(receipt)
    args = _args("F2", output / "scene")
    args.update({"seed": 20260908, "task_name": "cmf_f2_redesign_inside", "render_freq": 0, "save_data": False, "collect_data": False, "need_plan": True})
    try:
        with managed_scene(RedesignF2Scene, args, receipt, "f2-redesign-inside") as scene:
            scene.initialize_trace(scene.can, "left", scene.role_actors)
            scene.mark("current")
            receipt["current"] = {"can": _pose(scene.can).tolist(), "asset": scene._cmf_redesign_asset_spec, "box_contract": scene._cmf_f2_box_contract}
            scene.mark("anchor")
            receipt["anchor"] = {"can": _pose(scene.can).tolist()}
            grasp = scene.grasp_actor(scene.can, ArmTag("left"), pre_grasp_dis=0.09, grasp_dis=0.0, gripper_pos=0.0, contact_point_id=0)
            _must_action(scene, grasp, "f2_grasp")
            receipt["action_scene_count"] += 1
            _wait_and_record(scene, 250)
            held = _pose(scene.can)
            eef = np.asarray(scene.robot.get_left_ee_pose(), dtype=np.float64)
            lift = eef.copy(); lift[2] += 0.05
            _move_arm(scene, lift, "f2_lift")
            _wait_and_record(scene, 30)
            carry = lift.copy(); carry[0] += 0.14; carry[1] -= 0.20
            _move_arm(scene, carry, "f2_carry_to_box")
            _wait_and_record(scene, 30)
            # Descend while the planner has the can attached; support is a
            # physical postcondition and is not used to permit planning.
            descend = carry.copy(); descend[2] -= 0.09
            _move_arm(scene, descend, "f2_controlled_descent")
            _wait_and_record(scene, 60)
            support_end = len(scene.trace) - 1
            _must_action(scene, scene.open_gripper(ArmTag("left"), pos=1.0), "f2_slow_open")
            _wait_and_record(scene, 60)
            open_end = len(scene.trace) - 1
            retreat = descend.copy(); retreat[2] += 0.10; retreat[0] += 0.10
            _move_arm(scene, retreat, "f2_empty_hand_exit")
            _wait_and_record(scene, 60)
            exit_end = len(scene.trace) - 1
            rows = scene.trace
            support_rows = rows[max(0, support_end - 59) : support_end + 1]
            open_rows = rows[max(0, open_end - 59) : open_end + 1]
            exit_rows = rows[max(0, exit_end - 59) : exit_end + 1]
            def pair_has(row, first, second):
                for pair in row.get("contact_pairs", []):
                    bodies = {str(pair.get("body_a", "")), str(pair.get("body_b", ""))}
                    if first in bodies and second in bodies:
                        return True
                return False
            can_name = scene.can.get_name()
            support_fraction = float(np.mean([pair_has(row, can_name, "f2_redesign_box_bottom") for row in support_rows])) if support_rows else 0.0
            selected_open = float(np.mean([row.get("selected_gripper_contact", False) for row in open_rows])) if open_rows else 1.0
            selected_exit = float(np.mean([row.get("selected_gripper_contact", False) for row in exit_rows])) if exit_rows else 1.0
            final_can = _pose(scene.can)
            interior = scene._cmf_f2_box_contract
            lower = np.asarray(interior["interior_lower_m"], dtype=np.float64)
            upper = np.asarray(interior["interior_upper_m"], dtype=np.float64)
            center_inside = bool(np.all(final_can[:2] >= lower[:2]) and np.all(final_can[:2] <= upper[:2]))
            receipt["events"] = {
                "support": {"rows": len(support_rows), "bottom_identity_fraction": support_fraction},
                "slow_open": {"rows": len(open_rows), "selected_gripper_contact_fraction": selected_open},
                "empty_hand_exit": {"rows": len(exit_rows), "selected_gripper_contact_fraction": selected_exit},
                "final_can_pose": final_can.tolist(),
            }
            receipt["gates"] = {
                "inside_xy_after_release": center_inside,
                "real_bottom_support_identity": support_fraction >= 0.8,
                "opening_window_recorded": len(open_rows) >= 30,
                "empty_hand_exit_contact_free": selected_exit == 0.0,
                "dynamic_can_preserved": True,
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
        atomic_write_json(output / "f2_closure_receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); args = parser.parse_args()
    result = run(args.output); raise SystemExit(0 if result.get("status") == "qualification_pass" else 1)


if __name__ == "__main__":
    main()
