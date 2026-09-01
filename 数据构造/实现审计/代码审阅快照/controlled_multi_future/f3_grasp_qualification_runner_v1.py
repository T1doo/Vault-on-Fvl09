"""Planner and physical execution for bounded F3 grasp qualification."""

from __future__ import annotations

import hashlib
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_write_json
from .family_runners_v3_3 import (
    _arm_tag_left,
    _audited_planner_assisted_target_construction,
)
from .f3_grasp_qualification_v1 import (
    REQUIRED_PHYSICAL_GATES,
    build_f3_grasp_qualification_v1,
    build_f3_selected_grasp_contract_v1,
    select_f3_physical_candidates_v1,
)


class F3GraspQualificationRunnerV1:
    def __init__(self, adapter):
        if adapter.family != "F3":
            raise ValueError("F3 grasp qualification runner requires F3 adapter")
        self.adapter = adapter
        self.qualification = build_f3_grasp_qualification_v1()

    @staticmethod
    def _trace(scene, path: Path) -> dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = dict(scene.save_trace(path))
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return value

    def planner_screen(
        self, *, output_dir: Path, planned_root_slot_spec: Mapping[str, Any]
    ) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        context = self.adapter.scene(
            planned_root_slot_spec,
            phase="f3_grasp_qualification_v1_planner_screen",
            program=None,
        )
        scene = None
        audits = {}
        receipt = {
            "schema_version": "cmf_f3_grasp_planner_screen_v1",
            "qualification_contract_sha256": self.qualification[
                "qualification_contract_sha256"
            ],
            "candidate_receipts": [],
            "physical_selection_terminal": None,
            "planner_query_count": 0,
            "physical_execution_count": 0,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
            "status": "running",
        }
        try:
            with context as handle:
                scene = handle.scene
                self.adapter.capture_current(scene)
                self.adapter.controller_v3_3.initialize_prefix_replay_trace(scene)
                scene.planner_query_limit = 8
                for contact_id in (0, 3):
                    _, audit = _audited_planner_assisted_target_construction(
                        scene,
                        scene.bottle,
                        arm="left",
                        variant_id=f"f3_grasp_qv1_planner_screen_contact{contact_id}",
                        callback=lambda contact_id=contact_id: scene.choose_grasp_pose(
                            scene.bottle,
                            arm_tag=_arm_tag_left(),
                            pre_dis=0.09,
                            target_dis=0,
                            contact_point_id=contact_id,
                        ),
                        fixed_contact_point_ids=(contact_id,),
                    )
                    audits[contact_id] = audit
                for candidate in self.qualification["candidates"]:
                    batch = audits[candidate["contact_point_id"]]["batch_receipts"][0]
                    index = int(candidate["rotation_candidate_index"])
                    value = {
                        "candidate_id": candidate["candidate_id"],
                        "candidate_sha256": candidate["candidate_sha256"],
                        "rank": candidate["rank"],
                        "contact_point_id": candidate["contact_point_id"],
                        "rotation_candidate_index": index,
                        "ordered_goal_pose": batch["ordered_goal_poses"][index],
                        "ordered_goal_pose_batch_sha256": batch[
                            "ordered_goal_pose_sha256"
                        ],
                        "planner_status": batch["candidate_statuses"][index],
                        "planner_success": batch["candidate_statuses"][index]
                        == "Success",
                    }
                    value["receipt_sha256"] = canonical_hash_json(value)
                    receipt["candidate_receipts"].append(value)
                receipt["physical_selection_terminal"] = (
                    select_f3_physical_candidates_v1(receipt["candidate_receipts"])
                )
                receipt["planner_query_count"] = int(
                    getattr(scene, "planner_query_count", 0)
                )
                receipt["status"] = "planner_screen_completed"
        except BaseException as exc:
            receipt["status"] = "planner_screen_failed"
            receipt["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        cleanup = context.cleanup_receipt
        receipt["cleanup"] = cleanup
        receipt["cleanup_safety_pass"] = (
            isinstance(cleanup, Mapping)
            and cleanup.get("cleanup_safety_pass") is True
            and int(cleanup.get("orphan_process_count", -1)) == 0
        )
        receipt["elapsed_seconds"] = time.time() - started
        receipt["pass"] = (
            receipt["status"] == "planner_screen_completed"
            and receipt["cleanup_safety_pass"]
        )
        receipt["receipt_sha256"] = canonical_hash_json(receipt)
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        return receipt

    def physical_candidate(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        candidate: Mapping[str, Any],
    ) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        selected_contract = build_f3_selected_grasp_contract_v1(candidate)
        if self.adapter.selected_grasp_contract_v1 != selected_contract:
            raise ValueError("F3 adapter candidate differs from physical request")
        context = self.adapter.scene(
            planned_root_slot_spec,
            phase=f"f3_grasp_qualification_v1_physical:{candidate['candidate_id']}",
            program=None,
        )
        scene = None
        receipt: dict[str, Any] = {
            "schema_version": "cmf_f3_grasp_physical_candidate_v1",
            "qualification_contract_sha256": self.qualification[
                "qualification_contract_sha256"
            ],
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "candidate_rank": candidate["rank"],
            "selected_grasp_contract": selected_contract,
            "qualification_sequence_complete": False,
            "planner_query_count": 0,
            "physical_execution_count": 1,
            "suffix_planner_query_count": 0,
            "suffix_execution_count": 0,
            "release_execution_count": 0,
            "gates": {name: False for name in REQUIRED_PHYSICAL_GATES},
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
            "status": "running",
        }
        try:
            with context as handle:
                scene = handle.scene
                receipt["current"] = self.adapter.capture_current(scene)
                receipt["anchor"] = self.adapter.capture_anchor(scene)
                programs = list(self.adapter.build_programs(scene))
                task = self.adapter.audit_task_physical_feasibility(scene, programs[0])
                receipt["task_physical_receipt"] = task
                if not (
                    task.get("task_feasible") is True
                    and task.get("physical_feasible") is True
                ):
                    raise RuntimeError("F3 grasp qualification task/physical feasibility failed")
                prefix_contract = self.adapter.canonical_prefix_contract(programs)
                prefix = self.adapter.plan_and_execute_canonical_prefix(
                    scene, prefix_contract
                )
                physical = prefix["prefix_physical_acceptance"]
                checks = physical["checks"]
                event_checks = physical["shared_first_v_gate"]["event_checks"][
                    "event_0_V"
                ]
                receipt["gates"] = {
                    "planner_success": True,
                    "selected_gripper_contact_continuity": checks[
                        "selected_gripper_contact"
                    ]
                    and physical["selected_gripper_contact_fraction"] >= 1.0,
                    "grasp_transform_translation_stable": checks[
                        "grasp_transform_translation_stable"
                    ],
                    "grasp_transform_orientation_stable": checks[
                        "grasp_transform_orientation_stable"
                    ],
                    "bottle_off_support_after_lift": checks[
                        "shared_v_free_space_support_contact"
                    ]
                    and physical["pre_shared_v_boundary_gate"][
                        "free_space_contact_pass"
                    ],
                    "bottle_linear_stability": checks["bottle_linear_stationary"],
                    "bottle_angular_stability": checks[
                        "bottle_angular_stationary"
                    ],
                    "shared_v_realized_amplitude": all(
                        event_checks[name]
                        for name in (
                            "bottle_negative_amplitude",
                            "bottle_positive_amplitude",
                            "eef_negative_amplitude",
                            "eef_positive_amplitude",
                        )
                    ),
                    "shared_v_closed_loop_return": event_checks["bottle_return"]
                    and event_checks["eef_return"],
                    "eef_tracking": event_checks["eef_off_axis"]
                    and checks["eef_linear_stationary"]
                    and checks["eef_angular_stationary"],
                }
                receipt["prefix_contract"] = prefix_contract
                receipt["prefix_physical_acceptance"] = physical
                receipt["target_construction_planner_audit"] = prefix[
                    "target_construction_planner_audit"
                ]
                receipt["trace_source"] = self._trace(
                    scene, output_dir / "qualification_trace.npz"
                )
                receipt["planner_query_count"] = int(
                    getattr(scene, "planner_query_count", 0)
                )
                receipt["qualification_sequence_complete"] = bool(
                    physical.get("pass") is True
                    and all(receipt["gates"].values())
                )
                receipt["status"] = (
                    "physical_candidate_pass"
                    if receipt["qualification_sequence_complete"]
                    else "physical_candidate_failed_gates"
                )
        except BaseException as exc:
            receipt["status"] = "physical_candidate_failed_execution"
            receipt["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            if scene is not None and hasattr(scene, "trace"):
                receipt["partial_trace_source"] = self._trace(
                    scene, output_dir / "partial_trace.npz"
                )
                receipt["planner_query_count"] = int(
                    getattr(scene, "planner_query_count", 0)
                )
        cleanup = context.cleanup_receipt
        receipt["cleanup"] = cleanup
        receipt["cleanup_safety_pass"] = (
            isinstance(cleanup, Mapping)
            and cleanup.get("cleanup_safety_pass") is True
            and int(cleanup.get("orphan_process_count", -1)) == 0
        )
        receipt["orphan_process_count"] = (
            int(cleanup.get("orphan_process_count", -1))
            if isinstance(cleanup, Mapping)
            else -1
        )
        if not receipt["cleanup_safety_pass"]:
            receipt["status"] = "physical_candidate_failed_cleanup_uncertain"
        receipt["pass"] = (
            receipt["qualification_sequence_complete"]
            and receipt["cleanup_safety_pass"]
        )
        receipt["elapsed_seconds"] = time.time() - started
        receipt["receipt_sha256"] = canonical_hash_json(receipt)
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        return receipt


__all__ = ["F3GraspQualificationRunnerV1"]
