"""One-program fresh-scene strict-prefix diagnostic Gate.

Used by runtime-v3_4 F2 to test only ``inside`` before a complete three-branch
root is permitted.  It preserves the same-current/anchor/prefix/raw/cleanup
contracts without pretending that one passing branch is a root.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import time

from .anchor import compare_anchors
from .canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import hash_json, require_same_current
from .family_runners_v3_3 import install_frozen_suffix_controls
from .frozen_suffix_artifact_v1 import (
    build_frozen_suffix_artifact,
    load_frozen_suffix_artifact,
    write_frozen_suffix_artifact,
)
from .raw_writer import write_raw_attempt
from .root_orchestrator_v1_1 import _immutable_copy, _write_json
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _validate_prefix_reference_result,
    _validate_suffix_planner_receipt,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_single_program_strict_prefix_gate_v1"


class SingleProgramStrictPrefixGateV1:
    def __init__(self, adapter, *, program_id: str, gate_id: str):
        self.adapter = adapter
        self.program_id = str(program_id)
        self.gate_id = str(gate_id)
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(adapter)

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4",
            "gate_id": self.gate_id,
            "family": self.adapter.family,
            "program_id": self.program_id,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "pass": False,
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
            "reference_prefix_generation_count": 1,
            "prefix_replay_count": 0,
            "cleanup_records": [],
            "started_unix_seconds": time.time(),
        }
        self.helper._event_log_path = output_dir / "events.jsonl"
        _write_json(output_dir / "planned_root_slot_spec.json", planned)

        def pristine_callback(scene, _program):
            current = dict(self.adapter.capture_current(scene))
            anchor = dict(self.adapter.capture_anchor(scene))
            programs = _immutable_copy(list(self.adapter.build_programs(scene)))
            validate_exactly_three_programs(programs)
            selected = [item for item in programs if item["program_id"] == self.program_id]
            if len(selected) != 1:
                raise ValueError("single-program Gate did not find exactly one program")
            prefix = _immutable_copy(self.adapter.canonical_prefix_contract(programs))
            return current, anchor, programs, selected[0], prefix

        current, anchor, programs, program, prefix_contract = self.helper._scene_call(
            receipt=receipt,
            planned_spec=planned,
            planned_spec_sha256=planned_hash,
            phase=f"{self.gate_id}:pristine",
            program=None,
            program_sha256=None,
            callback=pristine_callback,
        )
        _write_json(output_dir / "reference_current.json", current)
        _write_json(output_dir / "reference_anchor.json", anchor)
        _write_json(output_dir / "provisional_programs.json", programs)

        prefix_runtime = {"queries": 0}

        def prefix_callback(scene, _program):
            require_same_current(current, dict(self.adapter.capture_current(scene)))
            start = compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))
            if not start["equivalent"]:
                raise ValueError("single-program prefix reference anchor mismatch")
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
            if len(result["planner_query_receipts"]) != prefix_runtime["queries"]:
                raise ValueError("prefix planner count differs from receipt")
            trace_path = output_dir / "prefix_reference_trace.npz"
            info = dict(scene.save_trace(trace_path))
            result["trace_source"] = {
                **info,
                "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            }
            return result

        try:
            prefix_result = self.helper._scene_call(
                receipt=receipt,
                planned_spec=planned,
                planned_spec_sha256=planned_hash,
                phase=f"{self.gate_id}:prefix_reference",
                program=None,
                program_sha256=None,
                callback=prefix_callback,
            )
        finally:
            receipt["planner_query_count"] += prefix_runtime["queries"]
        manifest, arrays = build_canonical_prefix_artifact(
            root_slot_id=str(planned["slot_id"]),
            family=self.adapter.family,
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
        candidate_hash = hash_json(programs)
        preflight_runtime = {"queries": 0}

        def preflight_callback(scene, _program):
            require_same_current(current, dict(self.adapter.capture_current(scene)))
            if not compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))["equivalent"]:
                raise ValueError("single-program preflight anchor mismatch")
            self.adapter.initialize_prefix_replay_trace(scene)
            receipt["prefix_replay_count"] += 1
            replay = replay_canonical_prefix(
                scene,
                manifest=manifest,
                arrays=arrays,
                reference_current=current,
                capture_current=self.adapter.capture_current,
                capture_anchor=self.adapter.capture_anchor,
            )
            physical = dict(self.adapter.validate_replayed_prefix_physical(scene, replay))
            replay["replayed_prefix_physical_acceptance"] = physical
            if physical.get("pass") is not True:
                raise ValueError("single-program preflight prefix physical Gate failed")
            before = int(getattr(scene, "planner_query_count", 0))
            try:
                suffix = _validate_suffix_planner_receipt(
                    self.adapter.plan_suffix_from_actual_prefix_end_state(
                        scene, _immutable_copy(program), replay
                    ),
                    self.program_id,
                )
            finally:
                preflight_runtime["queries"] = int(
                    getattr(scene, "planner_query_count", 0)
                ) - before
            controls = suffix.pop("_execution_controls", None)
            qpos = suffix.pop("_actual_prefix_end_qpos", None)
            if suffix["planner_query_count"] != preflight_runtime["queries"]:
                raise ValueError("single-program suffix planner count differs from receipt")
            if suffix["planner_solvable"] is not True:
                trace_path = output_dir / "preflight_trace_source.npz"
                trace = dict(scene.save_trace(trace_path))
                trace["sha256"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
                suffix["trace_source"] = trace
                _write_json(output_dir / "preflight_receipt.json", suffix)
                raise RuntimeError("single-program suffix planner failed")
            suffix_manifest, suffix_arrays = build_frozen_suffix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family=self.adapter.family,
                program_id=self.program_id,
                candidate_universe_sha256=candidate_hash,
                prefix_artifact_sha256=manifest["artifact_sha256"],
                actual_prefix_end_qpos=qpos,
                execution_spec=suffix["execution_spec"],
                controls=controls,
                planner_query_receipts=list(scene.planner_queries),
            )
            write_frozen_suffix_artifact(
                output_dir / "suffix_artifact", suffix_manifest, suffix_arrays
            )
            _write_json(output_dir / "preflight_receipt.json", suffix)
            return suffix

        try:
            suffix_receipt = self.helper._scene_call(
                receipt=receipt,
                planned_spec=planned,
                planned_spec_sha256=planned_hash,
                phase=f"{self.gate_id}:preflight",
                program=program,
                program_sha256=hash_json(program),
                callback=preflight_callback,
            )
        finally:
            receipt["planner_query_count"] += preflight_runtime["queries"]

        suffix_manifest, _, controls = load_frozen_suffix_artifact(
            output_dir / "suffix_artifact"
        )
        spec = dict(suffix_manifest["execution_spec"])
        spec["control_cache_key"] = suffix_manifest["execution_spec_sha256"]

        def execution_callback(scene, _program):
            require_same_current(current, dict(self.adapter.capture_current(scene)))
            if not compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))["equivalent"]:
                raise ValueError("single-program execution anchor mismatch")
            self.adapter.initialize_prefix_replay_trace(scene)
            receipt["prefix_replay_count"] += 1
            replay = replay_canonical_prefix(
                scene,
                manifest=manifest,
                arrays=arrays,
                reference_current=current,
                capture_current=self.adapter.capture_current,
                capture_anchor=self.adapter.capture_anchor,
            )
            physical = dict(self.adapter.validate_replayed_prefix_physical(scene, replay))
            replay["replayed_prefix_physical_acceptance"] = physical
            if physical.get("pass") is not True:
                raise ValueError("single-program execution prefix physical Gate failed")
            if replay["actual_prefix_end_qpos_sha256"] != suffix_manifest[
                "actual_prefix_end_qpos_sha256"
            ]:
                raise ValueError("single-program replay-end qpos mismatch")
            install_frozen_suffix_controls(scene, spec, controls)
            before = int(getattr(scene, "planner_query_count", 0))
            receipt["execution_attempt_count"] += 1
            try:
                result = self.adapter.execute_frozen_suffix_spec(
                    scene,
                    program,
                    spec,
                    replay,
                    {"realization": "diagnostic", "formal_data": False, "stage0_data": False},
                )
            except BaseException as exc:
                partial_path = output_dir / "partial_trace_source.npz"
                partial = dict(scene.save_trace(partial_path))
                partial["sha256"] = hashlib.sha256(
                    partial_path.read_bytes()
                ).hexdigest()
                failure = {
                    "status": "failed_execution",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "partial_trace_source": partial,
                    "structured_family_failure_evidence": {
                        "f2_balanced_preload_release_v9": getattr(
                            scene, "_cmf_f2_balanced_preload_release_v9", None
                        ),
                        "f2_release_safety_gate_v10": getattr(
                            scene, "_cmf_f2_release_safety_gate_v10", None
                        ),
                        "f2_final_inside_success_gate_v10": getattr(
                            scene, "_cmf_f2_final_inside_success_gate_v10", None
                        ),
                    },
                    "formal_data": False,
                    "stage0_data": False,
                    "stage0_authorized": False,
                }
                _write_json(output_dir / "program_receipt.json", failure)
                raise
            if int(getattr(scene, "planner_query_count", 0)) != before:
                raise ValueError("single-program frozen execution invoked planner")
            trace_path = output_dir / "trace_source.npz"
            trace = dict(scene.save_trace(trace_path))
            trace["sha256"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
            result.setdefault("provenance", {})["trace_source_sha256"] = trace["sha256"]
            result["provenance"]["trace_source_relative_path"] = "../trace_source.npz"
            raw = write_raw_attempt(
                output_dir / "raw",
                result["streams"],
                result["audit_streams"],
                result["provenance"],
            )
            verifier = self.adapter.verify(scene, program, result)
            return {
                "status": "passed" if verifier.get("pass") is True else "failed_verifier",
                "prefix_replay": replay,
                "suffix_planner": suffix_receipt,
                "semantic_verifier": result["semantic_verifier"],
                "verifier": verifier,
                "raw_manifest": raw,
                "trace_source": trace,
            }

        result = self.helper._scene_call(
            receipt=receipt,
            planned_spec=planned,
            planned_spec_sha256=planned_hash,
            phase=f"{self.gate_id}:execution",
            program=program,
            program_sha256=hash_json(program),
            callback=execution_callback,
        )
        _write_json(output_dir / "program_receipt.json", result)
        receipt["status"] = result["status"]
        receipt["pass"] = result["status"] == "passed"
        receipt["program_receipt_sha256"] = hash_json(result)
        receipt["budget_counts"] = {
            "planner_query_count": receipt["planner_query_count"],
            "execution_attempt_count": receipt["execution_attempt_count"],
            "recovery_attempt_count": 0,
        }
        receipt["ended_unix_seconds"] = time.time()
        receipt["receipt_sha256"] = hash_json(receipt)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt


__all__ = ["SingleProgramStrictPrefixGateV1"]
