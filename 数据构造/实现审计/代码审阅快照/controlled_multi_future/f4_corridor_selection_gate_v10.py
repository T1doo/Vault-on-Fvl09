"""Planner-only fixed-order F4 corridor selection before A execution."""

from __future__ import annotations

import hashlib
from pathlib import Path
import time
import traceback

from .anchor import compare_anchors
from .canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import hash_json, require_same_current
from .f4_carry_corridor_v10 import (
    audit_f4_corridor_planner_results_v10,
    build_f4_fixed_order_corridors_v10,
)
from .families import F4SubtaskOrder
from .root_orchestrator_v1_1 import CleanupUncertain, _immutable_copy, _write_json
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _validate_prefix_reference_result,
    _validate_suffix_planner_receipt,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_f4_corridor_selection_gate_v10"


class F4CorridorSelectionGateV10:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 corridor selection requires F4 adapter")
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(adapter)

    @staticmethod
    def _candidate_receipt(candidate_id, suffix, cleanup_pass):
        segments = list(suffix.get("evidence", {}).get("segment_receipts", []))
        normalized = []
        previous_end = None
        for item in segments:
            start = item.get("start_qpos_sha256")
            end = item.get("end_qpos_sha256")
            continuity = previous_end is None or start == previous_end
            normalized.append(
                {
                    "segment_id": item.get("segment_id"),
                    "endpoint_ik_pass": item.get("planner_status") == "Success",
                    "collision_pass": item.get("planner_status") == "Success",
                    "joint_margin_pass": item.get(
                        "terminal_qpos_within_joint_limits"
                    )
                    is True,
                    "chain_continuity_pass": continuity,
                    "start_qpos_sha256": start,
                    "end_qpos_sha256": end,
                    "planner_status": item.get("planner_status"),
                }
            )
            previous_end = end
        return {
            "candidate_id": candidate_id,
            "fresh_scene": True,
            "cleanup_pass": cleanup_pass,
            "execution_attempt_count": 0,
            "planner_query_count": int(suffix.get("planner_query_count", 0)),
            "segment_receipts": normalized,
            "source_suffix_receipt_sha256": hash_json(suffix),
        }

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "pass": False,
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
            "candidate_receipts": [],
            "cleanup_records": [],
        }
        self.helper._event_log_path = output_dir / "events.jsonl"
        _write_json(output_dir / "planned_root_slot_spec.json", planned)
        try:
            def pristine_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                anchor = dict(self.adapter.capture_anchor(scene))
                programs = _immutable_copy(list(self.adapter.build_programs(scene)))
                validate_exactly_three_programs(programs)
                prefix = _immutable_copy(self.adapter.canonical_prefix_contract(programs))
                base_program = F4SubtaskOrder().checked_provisional_programs()[0]
                all_targets, extra = self.adapter.controller_v3_3._top_down_full_targets_v8(
                    scene, base_program
                )
                reference_a = next(
                    group["targets"]
                    for group in extra["object_target_groups"]
                    if group["role"] == "A"
                )
                contract = build_f4_fixed_order_corridors_v10(reference_a)
                return current, anchor, programs, prefix, contract

            current, anchor, programs, prefix_contract, corridor_contract = (
                self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_corridor_pristine",
                    program=None,
                    program_sha256=None,
                    callback=pristine_callback,
                )
            )
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)
            _write_json(output_dir / "corridor_contract.json", corridor_contract)

            prefix_runtime = {"queries": 0}

            def prefix_callback(scene, _program):
                require_same_current(current, dict(self.adapter.capture_current(scene)))
                if not compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))["equivalent"]:
                    raise ValueError("F4 corridor prefix reference anchor mismatch")
                before = int(getattr(scene, "planner_query_count", 0))
                try:
                    result = _validate_prefix_reference_result(
                        self.adapter.plan_and_execute_canonical_prefix(
                            scene, _immutable_copy(prefix_contract)
                        )
                    )
                finally:
                    prefix_runtime["queries"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - before
                path = output_dir / "prefix_reference_trace.npz"
                trace = dict(scene.save_trace(path))
                result["trace_source"] = {
                    **trace,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                return result

            try:
                prefix_result = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_corridor_prefix_reference",
                    program=None,
                    program_sha256=None,
                    callback=prefix_callback,
                )
            finally:
                receipt["planner_query_count"] += prefix_runtime["queries"]
            manifest, arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family="F4",
                reference_current_sha256=current["aggregate_sha256"],
                reference_anchor=anchor,
                prefix_contract=prefix_contract,
                planner_seed=int(prefix_result.get("planner_seed", 20260828)),
                planner_query_receipts=prefix_result["planner_query_receipts"],
                planner_source_hash=prefix_result["planner_source_hash"],
                arrays=prefix_result["arrays"],
                semantic_prefix_end_anchor=prefix_result["semantic_prefix_end_anchor"],
                acceptance_prefix_end_anchor=prefix_result["acceptance_prefix_end_anchor"],
                settling_step_count=int(prefix_result["settling_step_count"]),
                settling_policy=prefix_result["settling_policy"],
                prefix_physical_acceptance=prefix_result["prefix_physical_acceptance"],
                reference_trace_source=prefix_result["trace_source"],
                reference_event_boundaries=prefix_result.get("reference_event_boundaries", {}),
            )
            manifest = write_canonical_prefix_artifact(
                output_dir / "prefix_artifact", manifest, arrays
            )
            public_candidates = []
            for candidate in corridor_contract["candidates"]:
                candidate_id = candidate["candidate_id"]
                candidate_dir = output_dir / f"candidate_{candidate['priority']}"
                candidate_dir.mkdir(parents=True, exist_ok=False)
                runtime = {"queries": 0}
                diagnostic_program = {
                    "program_id": f"F4-DIAG-A-CORRIDOR-{candidate_id}",
                    "steps": [{"operation": "place", "object_role": "A"}],
                }

                def candidate_callback(scene, _program):
                    require_same_current(current, dict(self.adapter.capture_current(scene)))
                    if not compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))["equivalent"]:
                        raise ValueError("F4 corridor candidate anchor mismatch")
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
                        raise ValueError("F4 corridor candidate prefix physical Gate failed")
                    before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        suffix = _validate_suffix_planner_receipt(
                            self.adapter.controller_v3_3.plan_a_corridor_candidate_from_actual_prefix_end_state_v10(
                                scene, replay, candidate_id
                            ),
                            diagnostic_program["program_id"],
                        )
                    finally:
                        runtime["queries"] = int(
                            getattr(scene, "planner_query_count", 0)
                        ) - before
                    suffix.pop("_execution_controls", None)
                    suffix.pop("_actual_prefix_end_qpos", None)
                    path = candidate_dir / "preflight_trace_source.npz"
                    trace = dict(scene.save_trace(path))
                    suffix["trace_source"] = {
                        **trace,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    _write_json(candidate_dir / "preflight_receipt.json", suffix)
                    return suffix

                suffix = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase=f"f4_corridor_candidate:{candidate_id}",
                    program=diagnostic_program,
                    program_sha256=hash_json(diagnostic_program),
                    callback=candidate_callback,
                )
                receipt["planner_query_count"] += runtime["queries"]
                cleanup_pass = receipt["cleanup_records"][-1].get(
                    "cleanup_safety_pass"
                ) is True
                public = self._candidate_receipt(
                    candidate_id, suffix, cleanup_pass
                )
                public_candidates.append(public)
                receipt["candidate_receipts"].append(public)
                if suffix.get("planner_solvable") is True:
                    break
            audit = audit_f4_corridor_planner_results_v10(
                corridor_contract, public_candidates
            )
            receipt["corridor_planner_audit"] = audit
            receipt["selected_corridor_id"] = audit["selected_candidate_id"]
            receipt["status"] = (
                "passed_f4_corridor_selection_gate_v10"
                if audit["pass"]
                else "failed_f4_corridor_selection_gate_v10"
            )
            receipt["pass"] = audit["pass"]
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            receipt["status"] = "failed_f4_corridor_selection_gate_v10"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        receipt["budget_counts"] = {
            "planner_query_count": receipt["planner_query_count"],
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        }
        receipt["elapsed_seconds"] = time.time() - started
        payload = dict(receipt)
        payload.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = hash_json(payload)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["F4CorridorSelectionGateV10"]
