"""Bounded no-action right-arm IK audit for F4 procedural cubes."""

from __future__ import annotations

import json
from pathlib import Path
import time
import traceback

import numpy as np

from .anchor import compare_anchors
from .current_hasher import hash_array, require_same_current
from .family_runners_v3_1 import _plan_chain, _planner_reset


SCHEMA_VERSION = "cmf_f4_cube_grasp_no_action_ik_audit_v1"


def joint_limit_margin(terminal_qpos, limits) -> dict:
    qpos = np.asarray(terminal_qpos, dtype=np.float64).reshape(-1)
    bounds = np.asarray(limits, dtype=np.float64).reshape(-1, 2)
    if len(qpos) != len(bounds) or not np.all(np.isfinite(qpos)):
        raise ValueError("terminal qpos and joint limits are inconsistent")
    margins = np.minimum(qpos - bounds[:, 0], bounds[:, 1] - qpos)
    return {
        "per_joint_margin_rad": margins.tolist(),
        "minimum_joint_limit_margin_rad": float(np.min(margins)),
        "within_limits": bool(np.all(margins >= 0.0)),
    }


def _right_arm_limits(scene) -> np.ndarray:
    values = []
    for joint in scene.robot.right_arm_joints:
        limit = np.asarray(joint.get_limits(), dtype=np.float64).reshape(-1, 2)
        if len(limit) < 1:
            raise ValueError(f"joint {joint.get_name()} has no finite limit")
        values.append(limit[0])
    return np.asarray(values, dtype=np.float64)


class F4CubeGraspIKAuditV1:
    def __init__(self, adapter):
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_3",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "planner_query_limit": 24,
            "execution_attempt_count": 0,
            "planner_query_count": 0,
            "roles": [],
            "cleanup_records": [],
            "status": "running",
        }
        (output_dir / "planned_root_slot_spec.json").write_text(
            json.dumps(planned_root_slot_spec, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        reference_current = None
        reference_anchor = None
        try:
            pristine = self.adapter.scene(
                planned_root_slot_spec, phase="f4_cube_ik_pristine", program=None
            )
            handle = None
            with pristine as handle:
                reference_current = dict(
                    self.adapter.capture_current(handle.scene)
                )
                reference_anchor = dict(
                    self.adapter.capture_anchor(handle.scene)
                )
            cleanup = handle.cleanup_receipt
            receipt["cleanup_records"].append(
                {"phase": "pristine", **dict(cleanup)}
            )
            if cleanup.get("cleanup_safety_pass") is not True:
                raise RuntimeError("F4 cube IK pristine cleanup uncertain")
            (output_dir / "reference_current.json").write_text(
                json.dumps(reference_current, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            (output_dir / "reference_anchor.json").write_text(
                json.dumps(reference_anchor, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )

            for role in ("A", "B", "C"):
                context = self.adapter.scene(
                    planned_root_slot_spec,
                    phase=f"f4_cube_ik:{role}",
                    program=None,
                )
                handle = None
                role_receipt = {"role": role, "status": "failed"}
                role_runtime = {"planner_query_count": 0}
                try:
                    with context as handle:
                        scene = handle.scene
                        planner_before = int(
                            getattr(scene, "planner_query_count", 0)
                        )
                        current = dict(self.adapter.capture_current(scene))
                        require_same_current(reference_current, current)
                        anchor = dict(self.adapter.capture_anchor(scene))
                        anchor_result = compare_anchors(reference_anchor, anchor)
                        if not anchor_result["equivalent"]:
                            raise ValueError(
                                f"F4 cube IK anchor mismatch: {anchor_result['failures']}"
                            )
                        actor = getattr(scene, role.lower())
                        slot = getattr(scene, f"slot_{role.lower()}")
                        targets, contract = self.adapter.controller_v3_3.legacy._object_place_targets(
                            scene, actor, slot, role, arm="right"
                        )
                        _planner_reset(
                            scene,
                            planner_seed=20260828,
                            variant_id=f"f4_cube_ik:{role}",
                            arm="right",
                        )
                        try:
                            planned = _plan_chain(
                                scene, targets[:2], query_limit=8, arm="right"
                            )
                        finally:
                            role_runtime["planner_query_count"] = int(
                                getattr(scene, "planner_query_count", 0)
                            ) - planner_before
                        terminal = None
                        margin = None
                        if planned["pass"]:
                            terminal = np.asarray(
                                planned["controls"][-1]["position"][-1],
                                dtype=np.float64,
                            )
                            margin = joint_limit_margin(
                                terminal, _right_arm_limits(scene)
                            )
                        role_receipt = {
                            "role": role,
                            "status": "passed"
                            if planned["pass"] and margin["within_limits"]
                            else "failed",
                            "current_sha256": current["aggregate_sha256"],
                            "anchor_equivalence": anchor_result,
                            "grasp_contract": contract,
                            "pregrasp_pose": targets[0]["pose"].tolist(),
                            "grasp_pose": targets[1]["pose"].tolist(),
                            "segment_receipts": planned["segment_receipts"],
                            "planner_query_count": planned["planner_query_count"],
                            "terminal_qpos": None
                            if terminal is None
                            else terminal.tolist(),
                            "terminal_qpos_sha256": None
                            if terminal is None
                            else hash_array(terminal),
                            "joint_limit_margin": margin,
                            "execution_attempt_count": 0,
                        }
                except BaseException as exc:
                    role_receipt.update(
                        {
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                            "planner_query_count": int(
                                role_runtime["planner_query_count"]
                            ),
                        }
                    )
                cleanup = handle.cleanup_receipt if handle is not None else context.cleanup_receipt
                receipt["cleanup_records"].append(
                    {"phase": f"role:{role}", **dict(cleanup)}
                )
                if cleanup.get("cleanup_safety_pass") is not True:
                    receipt["status"] = "failed_cleanup_uncertain"
                    receipt["roles"].append(role_receipt)
                    break
                receipt["roles"].append(role_receipt)
                receipt["planner_query_count"] += int(
                    role_receipt.get("planner_query_count", 0)
                )
            if receipt["status"] == "running":
                receipt["status"] = (
                    "passed_f4_cube_grasp_no_action_ik"
                    if len(receipt["roles"]) == 3
                    and all(item["status"] == "passed" for item in receipt["roles"])
                    and len(
                        {
                            item["grasp_contract"]["grasp_contract_sha256"]
                            for item in receipt["roles"]
                        }
                    )
                    == 1
                    else "failed_f4_cube_grasp_no_action_ik"
                )
        except BaseException as exc:
            if receipt["status"] == "running":
                receipt["status"] = "failed_f4_cube_grasp_no_action_ik"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        receipt["scene_cleanup_succeeded"] = bool(receipt["cleanup_records"]) and all(
            item.get("cleanup_safety_pass") is True
            and item.get("orphan_process_count") == 0
            for item in receipt["cleanup_records"]
        )
        receipt["orphan_process_count"] = sum(
            int(item.get("orphan_process_count") or 0)
            for item in receipt["cleanup_records"]
        )
        receipt["elapsed_seconds"] = time.time() - started
        (output_dir / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return receipt
