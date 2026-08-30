"""One finite real-SAPIEN F4 revision-5 common-boundary/A micro-lift Gate."""

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
from .family_runners_v3_3 import install_frozen_suffix_controls
from .frozen_suffix_artifact_v1 import (
    build_frozen_suffix_artifact,
    load_frozen_suffix_artifact,
    write_frozen_suffix_artifact,
)
from .raw_writer import write_raw_attempt
from .root_orchestrator_v1_1 import CleanupUncertain, _immutable_copy, _write_json
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _persist_prefix_gate_failure,
    _require_same_current_and_persist,
    _validate_prefix_reference_result,
    _validate_suffix_planner_receipt,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_f4_common_boundary_a_micro_lift_gate_v5"
DIAGNOSTIC_PROGRAM = {
    "program_id": "F4-DIAG-A-MICRO-LIFT",
    "steps": [
        {"operation": "grasp", "object_role": "A"},
        {"operation": "micro_lift", "axis": "world_z", "distance_m": 0.020},
    ],
}


class F4CommonBoundaryAndMicroLiftGateV5:
    """Stop after one A 20 mm lift; never run B/C/ABC/ACB/BAC here."""

    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 micro-lift Gate requires an F4 adapter")
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(adapter)

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_3",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "diagnostic_only": True,
            "full_f4_program_executed": False,
            "status": "running",
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
            "reference_prefix_generation_count": 1,
            "prefix_replay_count": 0,
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
                prefix_contract = _immutable_copy(
                    self.adapter.canonical_prefix_contract(programs)
                )
                return current, anchor, programs, prefix_contract

            current, anchor, programs, prefix_contract = self.helper._scene_call(
                receipt=receipt,
                planned_spec=planned,
                planned_spec_sha256=planned_hash,
                phase="f4_r5_micro_pristine",
                program=None,
                program_sha256=None,
                callback=pristine_callback,
            )
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)

            prefix_runtime = {"queries": 0}

            def prefix_callback(scene, _program):
                candidate_current = dict(self.adapter.capture_current(scene))
                _require_same_current_and_persist(
                    current,
                    candidate_current,
                    receipt_path=output_dir
                    / "prefix_reference_same_current_mismatch.json",
                    phase="f4_r5_micro_prefix_reference",
                    program_id=None,
                    scene_instance_id=getattr(
                        scene, "_cmf_scene_instance_id", None
                    ),
                )
                start = compare_anchors(
                    anchor, dict(self.adapter.capture_anchor(scene))
                )
                if not start["equivalent"]:
                    raise ValueError("F4 r5 prefix reference anchor mismatch")
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
                if len(result["planner_query_receipts"]) != int(
                    prefix_runtime["queries"]
                ):
                    raise ValueError(
                        "F4 r5 prefix planner API count differs from receipt table"
                    )
                if hasattr(scene, "save_trace"):
                    path = output_dir / "prefix_reference_trace.npz"
                    info = dict(scene.save_trace(path))
                    result["trace_source"] = {
                        **info,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                if result["prefix_physical_acceptance"].get("pass") is not True:
                    _persist_prefix_gate_failure(
                        scene,
                        receipt_path=output_dir
                        / "prefix_reference_failure_receipt.json",
                        trace_path=output_dir
                        / "prefix_reference_failure_trace.npz",
                        phase="f4_r5_micro_prefix_reference",
                        error_type="PrefixArtifactError",
                        error="F4 r5 reference prefix physical Gate failed",
                        replay=None,
                        replay_physical=result[
                            "prefix_physical_acceptance"
                        ],
                    )
                    raise ValueError("F4 r5 reference prefix physical Gate failed")
                return result

            try:
                prefix_result = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_r5_micro_prefix_reference",
                    program=None,
                    program_sha256=None,
                    callback=prefix_callback,
                )
            finally:
                receipt["planner_query_count"] += int(prefix_runtime["queries"])
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
                semantic_prefix_end_anchor=prefix_result[
                    "semantic_prefix_end_anchor"
                ],
                acceptance_prefix_end_anchor=prefix_result[
                    "acceptance_prefix_end_anchor"
                ],
                settling_step_count=int(prefix_result["settling_step_count"]),
                settling_policy=prefix_result["settling_policy"],
                prefix_physical_acceptance=prefix_result[
                    "prefix_physical_acceptance"
                ],
                reference_trace_source=prefix_result["trace_source"],
                reference_event_boundaries=prefix_result.get(
                    "reference_event_boundaries", {}
                ),
            )
            manifest = write_canonical_prefix_artifact(
                output_dir / "prefix_artifact", manifest, arrays
            )
            candidate_hash = hash_json(programs)
            program = _immutable_copy(DIAGNOSTIC_PROGRAM)
            program_hash = hash_json(program)
            preflight_runtime = {"queries": 0}

            def preflight_callback(scene, _program):
                candidate_current = dict(self.adapter.capture_current(scene))
                _require_same_current_and_persist(
                    current,
                    candidate_current,
                    receipt_path=output_dir
                    / "preflight_same_current_mismatch.json",
                    phase="f4_r5_micro_preflight",
                    program_id=program["program_id"],
                    scene_instance_id=getattr(
                        scene, "_cmf_scene_instance_id", None
                    ),
                )
                start = compare_anchors(
                    anchor, dict(self.adapter.capture_anchor(scene))
                )
                if not start["equivalent"]:
                    raise ValueError("F4 r5 micro preflight anchor mismatch")
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
                replay_physical = dict(
                    self.adapter.validate_replayed_prefix_physical(scene, replay)
                )
                if replay_physical.get("pass") is not True:
                    _persist_prefix_gate_failure(
                        scene,
                        receipt_path=output_dir
                        / "preflight_prefix_failure_receipt.json",
                        trace_path=output_dir
                        / "preflight_prefix_failure_trace.npz",
                        phase="f4_r5_micro_preflight",
                        error_type="PrefixArtifactError",
                        error="F4 r5 micro preflight prefix Gate failed",
                        replay=replay,
                        replay_physical=replay_physical,
                    )
                    raise ValueError("F4 r5 micro preflight prefix Gate failed")
                before = int(getattr(scene, "planner_query_count", 0))
                try:
                    suffix = _validate_suffix_planner_receipt(
                        self.adapter.controller_v3_3.plan_a_micro_lift_from_actual_prefix_end_state(
                            scene, replay
                        ),
                        program["program_id"],
                    )
                finally:
                    preflight_runtime["queries"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - before
                if suffix["planner_query_count"] != preflight_runtime["queries"]:
                    raise ValueError("F4 r5 micro planner count mismatch")
                suffix["execution_spec"][
                    "parent_scientific_candidate_universe_sha256"
                ] = candidate_hash
                suffix["execution_spec"][
                    "diagnostic_program_sha256"
                ] = program_hash
                suffix["execution_spec"][
                    "candidate_linkage_scope"
                ] = "parent_three_program_scientific_universe"
                controls = suffix.pop("_execution_controls", None)
                qpos = suffix.pop("_actual_prefix_end_qpos", None)
                if suffix["planner_solvable"] is not True:
                    if hasattr(scene, "save_trace"):
                        path = output_dir / "preflight_failure_trace.npz"
                        info = dict(scene.save_trace(path))
                        suffix["trace_source"] = {
                            **info,
                            "sha256": hashlib.sha256(
                                path.read_bytes()
                            ).hexdigest(),
                        }
                    _write_json(
                        output_dir / "preflight_receipt.json", suffix
                    )
                    raise RuntimeError("F4 r5 micro-lift planner failed")
                suffix_manifest, suffix_arrays = build_frozen_suffix_artifact(
                    root_slot_id=str(planned["slot_id"]),
                    family="F4",
                    program_id=program["program_id"],
                    candidate_universe_sha256=candidate_hash,
                    prefix_artifact_sha256=manifest["artifact_sha256"],
                    actual_prefix_end_qpos=qpos,
                    execution_spec=suffix["execution_spec"],
                    controls=controls,
                    planner_query_receipts=list(scene.planner_queries),
                )
                write_frozen_suffix_artifact(
                    output_dir / "suffix_artifact",
                    suffix_manifest,
                    suffix_arrays,
                )
                _write_json(output_dir / "preflight_receipt.json", suffix)
                return suffix

            try:
                preflight = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_r5_micro_preflight",
                    program=program,
                    program_sha256=program_hash,
                    callback=preflight_callback,
                )
            finally:
                receipt["planner_query_count"] += int(preflight_runtime["queries"])

            suffix_manifest, _, controls = load_frozen_suffix_artifact(
                output_dir / "suffix_artifact"
            )
            spec = dict(suffix_manifest["execution_spec"])
            spec["control_cache_key"] = suffix_manifest[
                "execution_spec_sha256"
            ]

            def execution_callback(scene, _program):
                candidate_current = dict(self.adapter.capture_current(scene))
                _require_same_current_and_persist(
                    current,
                    candidate_current,
                    receipt_path=output_dir
                    / "execution_same_current_mismatch.json",
                    phase="f4_r5_micro_execution",
                    program_id=program["program_id"],
                    scene_instance_id=getattr(
                        scene, "_cmf_scene_instance_id", None
                    ),
                )
                start = compare_anchors(
                    anchor, dict(self.adapter.capture_anchor(scene))
                )
                if not start["equivalent"]:
                    raise ValueError("F4 r5 micro execution anchor mismatch")
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
                replay_physical = dict(
                    self.adapter.validate_replayed_prefix_physical(scene, replay)
                )
                if replay_physical.get("pass") is not True:
                    _persist_prefix_gate_failure(
                        scene,
                        receipt_path=output_dir
                        / "execution_prefix_failure_receipt.json",
                        trace_path=output_dir
                        / "execution_prefix_failure_trace.npz",
                        phase="f4_r5_micro_execution",
                        error_type="PrefixArtifactError",
                        error="F4 r5 micro execution prefix Gate failed",
                        replay=replay,
                        replay_physical=replay_physical,
                    )
                    raise ValueError("F4 r5 micro execution prefix Gate failed")
                if replay["actual_prefix_end_qpos_sha256"] != suffix_manifest[
                    "actual_prefix_end_qpos_sha256"
                ]:
                    raise ValueError("F4 r5 micro replay-end qpos mismatch")
                install_frozen_suffix_controls(scene, spec, controls)
                before = int(getattr(scene, "planner_query_count", 0))
                receipt["execution_attempt_count"] += 1
                try:
                    result = self.adapter.controller_v3_3.execute_a_micro_lift_diagnostic(
                        scene,
                        program,
                        spec,
                        replay,
                        {
                            "realization": "diagnostic",
                            "formal_data": False,
                            "stage0_data": False,
                        },
                    )
                except BaseException as exc:
                    partial = {
                        "status": "failed_execution",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "preclose_boundary": getattr(
                            scene, "_cmf_f4_a_preclose_boundary_v5", None
                        ),
                        "micro_lift_gate": getattr(
                            scene, "_cmf_f4_a_micro_lift_gate_v5", None
                        ),
                        "micro_lift_role_input_v7": getattr(
                            scene,
                            "_cmf_f4_micro_lift_role_input_v7",
                            None,
                        ),
                        "noninterference_gate": getattr(
                            scene, "_cmf_f4_micro_noninterference_v5", None
                        ),
                        "formal_data": False,
                        "stage0_data": False,
                    }
                    if hasattr(scene, "save_trace"):
                        path = output_dir / "partial_trace_source.npz"
                        info = dict(scene.save_trace(path))
                        partial["trace_source"] = {
                            **info,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        }
                    _write_json(output_dir / "execution_receipt.json", partial)
                    raise
                if int(getattr(scene, "planner_query_count", 0)) != before:
                    raise ValueError("F4 r5 frozen execution invoked planner")
                path = output_dir / "trace_source.npz"
                trace = dict(scene.save_trace(path))
                trace["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                result.setdefault("provenance", {})[
                    "trace_source_sha256"
                ] = trace["sha256"]
                result["provenance"]["trace_source_relative_path"] = (
                    "../trace_source.npz"
                )
                raw = write_raw_attempt(
                    output_dir / "raw",
                    result["streams"],
                    result["audit_streams"],
                    result["provenance"],
                )
                terminal = {
                    "status": "passed"
                    if result["semantic_verifier"].get("pass") is True
                    else "failed_verifier",
                    "prefix_replay": replay,
                    "suffix_planner": preflight,
                    "semantic_verifier": result["semantic_verifier"],
                    "raw_manifest": raw,
                    "trace_source": trace,
                    "formal_data": False,
                    "stage0_data": False,
                }
                _write_json(output_dir / "execution_receipt.json", terminal)
                return terminal

            execution = self.helper._scene_call(
                receipt=receipt,
                planned_spec=planned,
                planned_spec_sha256=planned_hash,
                phase="f4_r5_micro_execution",
                program=program,
                program_sha256=program_hash,
                callback=execution_callback,
            )
            receipt["execution_receipt"] = execution
            receipt["status"] = (
                "passed_f4_r5_common_boundary_a_micro_lift_gate"
                if execution.get("status") == "passed"
                else "failed_f4_r5_common_boundary_a_micro_lift_gate"
            )
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            if receipt["status"] == "running":
                receipt["status"] = (
                    "failed_f4_r5_common_boundary_a_micro_lift_gate"
                )
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        receipt["scene_cleanup_succeeded"] = bool(receipt["cleanup_records"]) and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in receipt["cleanup_records"]
        )
        receipt["orphan_process_count"] = sum(
            int(item.get("orphan_process_count") or 0)
            for item in receipt["cleanup_records"]
        )
        receipt["elapsed_seconds"] = time.time() - started
        receipt["budget_counts"] = {
            "planner_query_count": int(receipt["planner_query_count"]),
            "execution_attempt_count": int(receipt["execution_attempt_count"]),
            "recovery_attempt_count": 0,
        }
        failure_artifacts = []
        for path in sorted(output_dir.rglob("*")):
            if (
                path.is_file()
                and path.name != "receipt.json"
                and any(
                    token in path.name
                    for token in ("failure", "mismatch", "partial_trace")
                )
            ):
                failure_artifacts.append(
                    {
                        "relative_path": path.relative_to(output_dir).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
        receipt["failure_artifacts"] = failure_artifacts
        _write_json(output_dir / "receipt.json", receipt)
        return receipt
