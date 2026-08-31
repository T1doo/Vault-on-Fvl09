"""Exactly three-scene, same-prefix, no-suffix F3 diagnostic.

The first fresh scene generates and executes the repaired canonical prefix.
The other two fresh scenes replay the immutable action bytes.  No suffix
planner, suffix control, release, raw formal attempt, or accepted root is
created by this diagnostic.
"""

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
from .f3_contact_preserving_prefix_v11 import (
    IMPLEMENTATION_VERSION,
    PROGRAM_IDS,
    REPAIR_ID,
    validate_f3_contact_preserving_prefix_contract_v11,
)
from .f3_common_grasp_prefix_v2 import (
    IMPLEMENTATION_VERSION as CLOSURE_IMPLEMENTATION_VERSION,
    validate_f3_common_grasp_prefix_v2,
)
from .root_orchestrator_v1_1 import (
    CleanupUncertain,
    _immutable_copy,
    _write_json,
)
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _validate_prefix_reference_result,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_f3_shared_prefix_no_suffix_diagnostic_v1"


def finalize_f3_shared_prefix_no_suffix_diagnostic_v1(
    contexts: Sequence[Mapping[str, Any]],
    *,
    cleanup_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    values = [dict(item) for item in contexts]
    cleanups = [dict(item) for item in cleanup_records]
    ids = [item.get("program_id") for item in values]
    prefix_hashes = {
        item.get("executed_prefix_action_sha256") for item in values
    }
    scene_ids = [item.get("scene_instance_id") for item in values]
    checks = {
        "exactly_three_fresh_scenes": len(values) == 3
        and len(set(scene_ids)) == 3
        and None not in scene_ids,
        "canonical_context_order": ids == list(PROGRAM_IDS),
        "all_three_prefixes_pass": len(values) == 3
        and all(item.get("pass") is True for item in values),
        "same_immutable_prefix_action_hash": len(prefix_hashes) == 1
        and None not in prefix_hashes,
        "one_reference_plus_two_exact_replays": len(values) == 3
        and [item.get("execution_mode") for item in values]
        == ["reference_generation", "exact_replay", "exact_replay"],
        "suffix_planner_never_called": len(values) == 3
        and all(int(item.get("suffix_planner_query_count", -1)) == 0 for item in values),
        "suffix_never_executed": len(values) == 3
        and all(item.get("suffix_executed") is False for item in values),
        "release_never_executed": len(values) == 3
        and all(item.get("release_executed") is False for item in values),
        "diagnostic_nonroot": len(values) == 3
        and all(item.get("diagnostic_nonroot") is True for item in values),
        "exactly_three_cleanup_records": len(cleanups) == 3,
        "all_cleanup_pass": len(cleanups) == 3
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in cleanups
        ),
    }
    result = {
        "schema_version": "cmf_f3_shared_prefix_no_suffix_finalizer_v1",
        "repair_id": REPAIR_ID,
        "program_ids": ids,
        "scene_instance_ids": scene_ids,
        "prefix_action_sha256": next(iter(prefix_hashes))
        if len(prefix_hashes) == 1
        else None,
        "checks": checks,
        "pass": all(checks.values()),
        "diagnostic_nonroot": True,
        "accepted_root_increment": 0,
        "suffix_planner_query_count": 0,
        "suffix_execution_count": 0,
        "release_execution_count": 0,
    }
    result["receipt_sha256"] = hash_json(result)
    return result


class F3SharedPrefixNoSuffixDiagnosticV1:
    def __init__(self, adapter):
        if adapter.family != "F3":
            raise ValueError("F3 prefix diagnostic requires family F3")
        repair_v2 = getattr(adapter.controller_v3_3, "f3_common_grasp_prefix_v2", None)
        if repair_v2 is not None:
            self.repair = validate_f3_common_grasp_prefix_v2(repair_v2)
            self.implementation_version = CLOSURE_IMPLEMENTATION_VERSION
            self.schema_version = "cmf_f3_common_grasp_prefix_v2_diagnostic"
        else:
            repair = getattr(adapter.controller_v3_3, "f3_shared_prefix_repair_v11", None)
            self.repair = validate_f3_contact_preserving_prefix_contract_v11(repair)
            self.implementation_version = IMPLEMENTATION_VERSION
            self.schema_version = SCHEMA_VERSION
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(
            adapter, implementation_version=self.implementation_version
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
            "schema_version": self.schema_version,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": self.implementation_version,
            "repair_contract": self.repair,
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
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
            "suffix_planner_query_count": 0,
            "suffix_execution_count": 0,
            "release_execution_count": 0,
            "contexts": [],
            "cleanup_records": [],
        }
        self.helper._event_log_path = output_dir / "events.jsonl"
        _write_json(output_dir / "planned_root_slot_spec.json", planned)
        _write_json(output_dir / "repair_contract.json", self.repair)
        try:
            reference_dir = output_dir / "context_VVHH"
            reference_dir.mkdir(parents=True, exist_ok=False)
            reference_runtime = {"queries": 0}

            def reference_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                anchor = dict(self.adapter.capture_anchor(scene))
                programs = _immutable_copy(list(self.adapter.build_programs(scene)))
                validate_exactly_three_programs(programs)
                if [item["program_id"] for item in programs] != list(PROGRAM_IDS):
                    raise ValueError("F3 canonical programs changed")
                prefix_contract = _immutable_copy(
                    self.adapter.canonical_prefix_contract(programs)
                )
                if prefix_contract.get("shared_prefix_repair_v11") != self.repair:
                    raise ValueError("F3 repaired prefix contract is not bound")
                before = int(getattr(scene, "planner_query_count", 0))
                receipt["execution_attempt_count"] += 1
                try:
                    prefix = _validate_prefix_reference_result(
                        self.adapter.plan_and_execute_canonical_prefix(
                            scene, prefix_contract
                        )
                    )
                    if prefix.get("prefix_physical_acceptance", {}).get("pass") is not True:
                        raise RuntimeError("F3 repaired reference prefix physical Gate failed")
                    trace = self._trace(
                        scene, reference_dir / "prefix_reference_trace.npz"
                    )
                    prefix["trace_source"] = trace
                    return current, anchor, programs, prefix_contract, prefix
                except BaseException as exc:
                    failure = {
                        "status": "failed_reference_prefix",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "controller_prefix_failure_receipt": getattr(
                            scene, "_cmf_prefix_failure_receipt", None
                        ),
                    }
                    try:
                        failure["partial_trace_source"] = self._trace(
                            scene, reference_dir / "partial_trace.npz"
                        )
                    except BaseException as trace_exc:
                        failure["partial_trace_error"] = {
                            "type": type(trace_exc).__name__,
                            "message": str(trace_exc),
                        }
                    _write_json(reference_dir / "failure_receipt.json", failure)
                    raise
                finally:
                    reference_runtime["queries"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - before

            try:
                current, anchor, programs, prefix_contract, prefix = (
                    self.helper._scene_call(
                        receipt=receipt,
                        planned_spec=planned,
                        planned_spec_sha256=planned_hash,
                        phase="f3_prefix_no_suffix_reference",
                        program=None,
                        program_sha256=None,
                        callback=reference_callback,
                    )
                )
            finally:
                receipt["planner_query_count"] += reference_runtime["queries"]
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)
            _write_json(output_dir / "canonical_programs.json", programs)
            _write_json(output_dir / "prefix_contract.json", prefix_contract)
            manifest, arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family="F3",
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
            reference_context = {
                "program_id": PROGRAM_IDS[0],
                "execution_mode": "reference_generation",
                "diagnostic_nonroot": True,
                "pass": True,
                "scene_instance_id": receipt["cleanup_records"][-1]["scene_instance_id"],
                "executed_prefix_action_sha256": manifest["prefix_action_sha256"],
                "prefix_physical_acceptance": prefix["prefix_physical_acceptance"],
                "trace_source": prefix["trace_source"],
                "suffix_planner_query_count": 0,
                "suffix_executed": False,
                "release_executed": False,
            }
            _write_json(reference_dir / "receipt.json", reference_context)
            receipt["contexts"].append(reference_context)

            for program in programs[1:]:
                program_id = str(program["program_id"])
                context_dir = output_dir / ("context_" + program_id.split("-", 1)[1])
                context_dir.mkdir(parents=True, exist_ok=False)

                def replay_callback(scene, _program):
                    require_same_current(
                        current, dict(self.adapter.capture_current(scene))
                    )
                    start_anchor = dict(self.adapter.capture_anchor(scene))
                    anchor_equivalence = compare_anchors(anchor, start_anchor)
                    if anchor_equivalence["equivalent"] is not True:
                        raise ValueError("F3 no-suffix replay anchor mismatch")
                    self.adapter.initialize_prefix_replay_trace(scene)
                    receipt["execution_attempt_count"] += 1
                    try:
                        replay = replay_canonical_prefix(
                            scene,
                            manifest=manifest,
                            arrays=arrays,
                            reference_current=current,
                            capture_current=self.adapter.capture_current,
                            capture_anchor=self.adapter.capture_anchor,
                        )
                        physical = dict(
                            self.adapter.validate_replayed_prefix_physical(
                                scene, replay
                            )
                        )
                        if physical.get("pass") is not True:
                            raise RuntimeError(
                                "F3 no-suffix replay physical Gate failed"
                            )
                        trace = self._trace(
                            scene, context_dir / "prefix_replay_trace.npz"
                        )
                        return {
                            "program_id": program_id,
                            "execution_mode": "exact_replay",
                            "diagnostic_nonroot": True,
                            "pass": True,
                            "executed_prefix_action_sha256": replay[
                                "executed_prefix_action_sha256"
                            ],
                            "prefix_replay": replay,
                            "prefix_physical_acceptance": physical,
                            "trace_source": trace,
                            "suffix_planner_query_count": 0,
                            "suffix_executed": False,
                            "release_executed": False,
                        }
                    except BaseException as exc:
                        failure = {
                            "status": "failed_prefix_replay",
                            "program_id": program_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                        try:
                            failure["partial_trace_source"] = self._trace(
                                scene, context_dir / "partial_trace.npz"
                            )
                        except BaseException as trace_exc:
                            failure["partial_trace_error"] = {
                                "type": type(trace_exc).__name__,
                                "message": str(trace_exc),
                            }
                        _write_json(context_dir / "failure_receipt.json", failure)
                        raise

                context = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase=f"f3_prefix_no_suffix_replay:{program_id}",
                    program=program,
                    program_sha256=hash_json(program),
                    callback=replay_callback,
                )
                context["scene_instance_id"] = receipt["cleanup_records"][-1][
                    "scene_instance_id"
                ]
                _write_json(context_dir / "receipt.json", context)
                receipt["contexts"].append(context)

            finalizer = finalize_f3_shared_prefix_no_suffix_diagnostic_v1(
                receipt["contexts"], cleanup_records=receipt["cleanup_records"]
            )
            receipt["finalizer"] = finalizer
            receipt["pass"] = finalizer["pass"]
            receipt["status"] = (
                "passed_f3_shared_prefix_no_suffix_diagnostic_v1"
                if finalizer["pass"]
                else "failed_f3_shared_prefix_no_suffix_diagnostic_v1"
            )
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            receipt["status"] = "failed_f3_shared_prefix_no_suffix_diagnostic_v1"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        receipt["budget_counts"] = {
            "planner_query_count": int(receipt["planner_query_count"]),
            "execution_attempt_count": int(receipt["execution_attempt_count"]),
            "recovery_attempt_count": 0,
        }
        receipt["elapsed_seconds"] = time.time() - started
        payload = dict(receipt)
        payload.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = hash_json(payload)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = [
    "F3SharedPrefixNoSuffixDiagnosticV1",
    "finalize_f3_shared_prefix_no_suffix_diagnostic_v1",
]
