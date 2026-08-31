"""F4 new-layout endpoint-IK and three-program planner-only audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import time
import traceback
from typing import Any, Mapping, Sequence

from .anchor import compare_anchors
from .canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import hash_json, require_same_current
from .f4_post_stage0_layout_v1 import (
    SELECTED_EXISTING_CORRIDOR_ID,
)
from .real_sapien_adapter_post_stage0_f4_v1 import IMPLEMENTATION_VERSION
from .root_orchestrator_v1_1 import CleanupUncertain, _immutable_copy, _write_json
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _validate_prefix_reference_result,
    _validate_suffix_planner_receipt,
)
from .schemas import validate_exactly_three_programs


PROGRAM_IDS = ("F4-ABC", "F4-ACB", "F4-BAC")
SCHEMA_VERSION = "cmf_f4_post_stage0_planner_only_v1"


def _dispatch_endpoint_ik_planner(adapter, scene, program, replay):
    """Single audited call site that must enter the real endpoint planner."""
    return adapter.plan_suffix_from_actual_prefix_end_state(scene, program, replay)


def _segment_chain_audit(segments: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [dict(item) for item in segments]
    chain = True
    for previous, current in zip(values, values[1:]):
        if previous.get("end_qpos_sha256") != current.get("start_qpos_sha256"):
            chain = False
    checks = {
        "nonempty": bool(values),
        "all_endpoint_ik_and_collision_success": bool(values)
        and all(item.get("planner_status") == "Success" for item in values),
        "joint_limit_evidence_complete": bool(values)
        and all(item.get("joint_limit_evidence_complete") is True for item in values),
        "all_terminal_qpos_within_limits": bool(values)
        and all(item.get("terminal_qpos_within_joint_limits") is True for item in values),
        "qpos_chain_continuous": chain,
        "all_unexecuted": bool(values)
        and all(item.get("executed") is False for item in values),
    }
    return {
        "segment_count": len(values),
        "segment_ids": [item.get("segment_id") for item in values],
        "minimum_terminal_joint_limit_margin_rad": min(
            float(item["minimum_terminal_joint_limit_margin_rad"])
            for item in values
            if isinstance(item.get("minimum_terminal_joint_limit_margin_rad"), (int, float))
        )
        if values
        else None,
        "checks": checks,
        "pass": all(checks.values()),
    }


def finalize_f4_post_stage0_planner_only_v1(
    program_receipts: Sequence[Mapping[str, Any]],
    *,
    cleanup_records: Sequence[Mapping[str, Any]],
    canonical_neutral_pose_sha256: str,
) -> dict[str, Any]:
    values = [dict(item) for item in program_receipts]
    cleanups = [dict(item) for item in cleanup_records]
    ids = [item.get("program_id") for item in values]
    hashes = {item.get("executed_prefix_action_sha256") for item in values}
    scenes = [item.get("scene_instance_id") for item in values]
    checks = {
        "exact_three_programs": ids == list(PROGRAM_IDS),
        "all_three_complete_chains_pass": len(values) == 3
        and all(item.get("pass") is True for item in values),
        "same_prefix_action_hash": len(hashes) == 1 and None not in hashes,
        "three_unique_program_scenes": len(set(scenes)) == 3 and None not in scenes,
        "same_canonical_neutral": len(values) == 3
        and all(
            item.get("canonical_neutral_pose_sha256")
            == canonical_neutral_pose_sha256
            for item in values
        ),
        "existing_corridor_only": len(values) == 3
        and all(
            item.get("selected_corridor_id") == SELECTED_EXISTING_CORRIDOR_ID
            for item in values
        ),
        "suffix_execution_zero": len(values) == 3
        and all(int(item.get("suffix_execution_attempt_count", -1)) == 0 for item in values),
        "release_execution_zero": len(values) == 3
        and all(int(item.get("release_execution_count", -1)) == 0 for item in values),
        "one_reference_plus_three_program_cleanups": len(cleanups) == 4,
        "all_cleanup_pass": len(cleanups) == 4
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in cleanups
        ),
    }
    result = {
        "schema_version": "cmf_f4_post_stage0_planner_only_finalizer_v1",
        "program_ids": ids,
        "program_scene_instance_ids": scenes,
        "prefix_action_sha256": next(iter(hashes)) if len(hashes) == 1 else None,
        "canonical_neutral_pose_sha256": canonical_neutral_pose_sha256,
        "selected_existing_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
        "checks": checks,
        "pass": all(checks.values()),
        "diagnostic_nonroot": True,
        "accepted_root_increment": 0,
        "suffix_execution_attempt_count": 0,
        "release_execution_count": 0,
    }
    result["receipt_sha256"] = hash_json(result)
    return result


class F4PostStage0PlannerOnlyV1:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 planner-only audit requires family F4")
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(
            adapter, implementation_version=IMPLEMENTATION_VERSION
        )

    @staticmethod
    def _trace(scene, path: Path) -> dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = dict(scene.save_trace(path))
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return value

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": IMPLEMENTATION_VERSION,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "stage0_reopened": False,
            "stage1_authorized": False,
            "diagnostic_nonroot": True,
            "accepted_root_increment": 0,
            "status": "running",
            "pass": False,
            "planner_query_count": 0,
            "canonical_prefix_reference_execution_count": 0,
            "suffix_execution_attempt_count": 0,
            "release_execution_count": 0,
            "recovery_attempt_count": 0,
            "program_receipts": [],
            "cleanup_records": [],
        }
        self.helper._event_log_path = output_dir / "events.jsonl"
        _write_json(output_dir / "planned_root_slot_spec.json", planned)
        try:
            reference_dir = output_dir / "prefix_reference"
            reference_dir.mkdir(parents=True, exist_ok=False)
            runtime = {"queries": 0}

            def reference_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                anchor = dict(self.adapter.capture_anchor(scene))
                programs = _immutable_copy(list(self.adapter.build_programs(scene)))
                validate_exactly_three_programs(programs)
                if [item["program_id"] for item in programs] != list(PROGRAM_IDS):
                    raise ValueError("F4 canonical programs changed")
                prefix_contract = _immutable_copy(
                    self.adapter.canonical_prefix_contract(programs)
                )
                before = int(getattr(scene, "planner_query_count", 0))
                receipt["canonical_prefix_reference_execution_count"] += 1
                try:
                    prefix = _validate_prefix_reference_result(
                        self.adapter.plan_and_execute_canonical_prefix(
                            scene, prefix_contract
                        )
                    )
                    if prefix.get("prefix_physical_acceptance", {}).get("pass") is not True:
                        raise RuntimeError("F4 new-layout prefix physical Gate failed")
                    trace = self._trace(
                        scene, reference_dir / "prefix_reference_trace.npz"
                    )
                    prefix["trace_source"] = trace
                    return current, anchor, programs, prefix_contract, prefix
                finally:
                    runtime["queries"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - before

            try:
                current, anchor, programs, prefix_contract, prefix = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_post_stage0_prefix_reference",
                    program=None,
                    program_sha256=None,
                    callback=reference_callback,
                )
            finally:
                receipt["planner_query_count"] += runtime["queries"]
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)
            _write_json(output_dir / "canonical_programs.json", programs)
            _write_json(output_dir / "prefix_contract.json", prefix_contract)
            neutral_pose = prefix["prefix_physical_acceptance"][
                "actual_open_contact_boundary_v5"
            ]["target_neutral_pose"]
            neutral_sha = hash_json(neutral_pose)
            _write_json(
                output_dir / "post_stage0_canonical_neutral.json",
                {
                    "source": "new_layout_canonical_prefix_target_neutral_pose",
                    "pose": neutral_pose,
                    "pose_sha256": neutral_sha,
                },
            )
            manifest, arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family="F4",
                reference_current_sha256=current["aggregate_sha256"],
                reference_anchor=anchor,
                prefix_contract=prefix_contract,
                planner_seed=int(prefix.get("planner_seed", 20260828)),
                planner_query_receipts=prefix["planner_query_receipts"],
                planner_source_hash=prefix["planner_source_hash"],
                arrays=prefix["arrays"],
                semantic_prefix_end_anchor=prefix["semantic_prefix_end_anchor"],
                acceptance_prefix_end_anchor=prefix["acceptance_prefix_end_anchor"],
                settling_step_count=int(prefix["settling_step_count"]),
                settling_policy=prefix["settling_policy"],
                prefix_physical_acceptance=prefix["prefix_physical_acceptance"],
                reference_trace_source=prefix["trace_source"],
                reference_event_boundaries=prefix.get("reference_event_boundaries", {}),
            )
            manifest = write_canonical_prefix_artifact(
                output_dir / "prefix_artifact", manifest, arrays
            )
            for program in programs:
                program_id = str(program["program_id"])
                program_dir = output_dir / ("program_" + program_id.split("-", 1)[1])
                program_dir.mkdir(parents=True, exist_ok=False)
                program_runtime = {"queries": 0}

                def planner_callback(scene, _program):
                    require_same_current(current, dict(self.adapter.capture_current(scene)))
                    start_anchor = dict(self.adapter.capture_anchor(scene))
                    if compare_anchors(anchor, start_anchor)["equivalent"] is not True:
                        raise ValueError("F4 planner-only start anchor mismatch")
                    self.adapter.initialize_prefix_replay_trace(scene)
                    replay = replay_canonical_prefix(
                        scene,
                        manifest=manifest,
                        arrays=arrays,
                        reference_current=current,
                        capture_current=self.adapter.capture_current,
                        capture_anchor=self.adapter.capture_anchor,
                    )
                    physical = dict(
                        self.adapter.validate_replayed_prefix_physical(scene, replay)
                    )
                    if physical.get("pass") is not True:
                        raise RuntimeError("F4 planner-only prefix physical Gate failed")
                    scene._cmf_post_stage0_f4_canonical_neutral_pose = list(neutral_pose)
                    before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        suffix = _validate_suffix_planner_receipt(
                            _dispatch_endpoint_ik_planner(
                                self.adapter, scene, program, replay
                            ),
                            program_id,
                        )
                    finally:
                        program_runtime["queries"] = int(
                            getattr(scene, "planner_query_count", 0)
                        ) - before
                    suffix.pop("_execution_controls", None)
                    suffix.pop("_actual_prefix_end_qpos", None)
                    segments = suffix.get("evidence", {}).get("segment_receipts", [])
                    chain = _segment_chain_audit(segments)
                    selected = suffix.get("evidence", {}).get(
                        "block_carry_route_audit", {}
                    )
                    passed = (
                        suffix.get("planner_solvable") is True
                        and chain["pass"] is True
                        and selected.get("selected_candidate", {}).get("candidate_id")
                        == SELECTED_EXISTING_CORRIDOR_ID
                    )
                    trace = self._trace(
                        scene, program_dir / "prefix_replay_trace.npz"
                    )
                    return {
                        "program_id": program_id,
                        "pass": passed,
                        "scene_instance_id": None,
                        "executed_prefix_action_sha256": replay[
                            "executed_prefix_action_sha256"
                        ],
                        "canonical_neutral_pose_sha256": neutral_sha,
                        "selected_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
                        "prefix_replay": replay,
                        "prefix_physical_acceptance": physical,
                        "planner_receipt": suffix,
                        "segment_chain_audit": chain,
                        "suffix_execution_attempt_count": 0,
                        "release_execution_count": 0,
                        "trace_source": trace,
                    }

                try:
                    program_receipt = self.helper._scene_call(
                        receipt=receipt,
                        planned_spec=planned,
                        planned_spec_sha256=planned_hash,
                        phase=f"f4_post_stage0_planner_only:{program_id}",
                        program=program,
                        program_sha256=hash_json(program),
                        callback=planner_callback,
                    )
                finally:
                    receipt["planner_query_count"] += program_runtime["queries"]
                program_receipt["scene_instance_id"] = receipt["cleanup_records"][-1][
                    "scene_instance_id"
                ]
                _write_json(program_dir / "receipt.json", program_receipt)
                receipt["program_receipts"].append(program_receipt)
                if program_receipt.get("pass") is not True:
                    break
            finalizer = finalize_f4_post_stage0_planner_only_v1(
                receipt["program_receipts"],
                cleanup_records=receipt["cleanup_records"],
                canonical_neutral_pose_sha256=neutral_sha,
            )
            receipt["finalizer"] = finalizer
            receipt["pass"] = finalizer["pass"]
            receipt["status"] = (
                "passed_f4_post_stage0_planner_only_v1"
                if finalizer["pass"]
                else "failed_f4_post_stage0_planner_only_v1"
            )
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            receipt["status"] = "failed_f4_post_stage0_planner_only_v1"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        receipt["budget_counts"] = {
            "planner_query_count": int(receipt["planner_query_count"]),
            "canonical_prefix_reference_execution_count": int(
                receipt["canonical_prefix_reference_execution_count"]
            ),
            "suffix_execution_attempt_count": 0,
            "release_execution_count": 0,
            "recovery_attempt_count": 0,
        }
        receipt["elapsed_seconds"] = time.time() - started
        payload = dict(receipt)
        payload.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = hash_json(payload)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = [
    "F4PostStage0PlannerOnlyV1",
    "finalize_f4_post_stage0_planner_only_v1",
]
