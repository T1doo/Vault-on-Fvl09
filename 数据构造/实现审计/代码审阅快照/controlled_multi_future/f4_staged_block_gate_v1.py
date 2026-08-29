"""F4 A/B/C/AB staged execution Gate before a full three-program root."""

from __future__ import annotations

import hashlib
import json
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
    _validate_prefix_reference_result,
    _validate_suffix_planner_receipt,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_f4_staged_block_execution_gate_v1"
GATE_SEQUENCE = (("A",), ("B",), ("C",), ("A", "B"))


class F4StagedBlockExecutionGateV1:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 staged Gate requires an F4 adapter")
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
            "status": "running",
            "gate_sequence": [list(item) for item in GATE_SEQUENCE],
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "reference_prefix_generation_count": 1,
            "prefix_replay_count": 0,
            "recovery_attempt_count": 0,
            "gate_receipts": [],
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
                phase="f4_staged_pristine",
                program=None,
                program_sha256=None,
                callback=pristine_callback,
            )
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)

            prefix_runtime = {"queries": 0}

            def prefix_callback(scene, _program):
                require_same_current(current, dict(self.adapter.capture_current(scene)))
                start = compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))
                if not start["equivalent"]:
                    raise ValueError("F4 staged prefix reference anchor mismatch")
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
                if hasattr(scene, "save_trace"):
                    path = output_dir / "prefix_reference_trace.npz"
                    info = dict(scene.save_trace(path))
                    result["trace_source"] = {
                        **info,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                return result

            try:
                prefix_result = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_staged_prefix_reference",
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

            for roles in GATE_SEQUENCE:
                gate_id = "".join(roles)
                gate_dir = output_dir / f"gate_{gate_id}"
                gate_dir.mkdir(parents=True, exist_ok=False)
                diagnostic_program = {
                    "program_id": f"F4-DIAG-{gate_id}",
                    "steps": [
                        {"operation": "place", "object_role": role}
                        for role in roles
                    ],
                }
                runtime = {"queries": 0}

                def preflight_callback(scene, _program):
                    require_same_current(current, dict(self.adapter.capture_current(scene)))
                    start = compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))
                    if not start["equivalent"]:
                        raise ValueError(f"F4 {gate_id} preflight anchor mismatch")
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
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    replay["replayed_prefix_physical_acceptance"] = replay_physical
                    if replay_physical.get("pass") is not True:
                        raise ValueError(f"F4 {gate_id} preflight prefix physical Gate failed")
                    before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        try:
                            suffix = _validate_suffix_planner_receipt(
                                self.adapter.controller_v3_3.plan_diagnostic_blocks_from_actual_prefix_end_state(
                                    scene, roles, replay
                                ),
                                diagnostic_program["program_id"],
                            )
                        except BaseException:
                            if hasattr(scene, "save_trace"):
                                partial_path = gate_dir / "preflight_partial_trace_source.npz"
                                partial = dict(scene.save_trace(partial_path))
                                partial["sha256"] = hashlib.sha256(
                                    partial_path.read_bytes()
                                ).hexdigest()
                                _write_json(
                                    gate_dir / "preflight_receipt.json",
                                    {
                                        "status": "failed_planner_exception",
                                        "roles": list(roles),
                                        "partial_trace_source": partial,
                                        "formal_data": False,
                                        "stage0_data": False,
                                    },
                                )
                            raise
                    finally:
                        runtime["queries"] = int(
                            getattr(scene, "planner_query_count", 0)
                        ) - before
                    controls = suffix.pop("_execution_controls", None)
                    qpos = suffix.pop("_actual_prefix_end_qpos", None)
                    if suffix["planner_solvable"] is not True:
                        if hasattr(scene, "save_trace"):
                            trace_path = gate_dir / "preflight_trace_source.npz"
                            trace = dict(scene.save_trace(trace_path))
                            trace["sha256"] = hashlib.sha256(
                                trace_path.read_bytes()
                            ).hexdigest()
                            suffix["trace_source"] = trace
                        _write_json(
                            gate_dir / "preflight_receipt.json", suffix
                        )
                        raise RuntimeError(f"F4 staged {gate_id} planner failed")
                    suffix_manifest, suffix_arrays = build_frozen_suffix_artifact(
                        root_slot_id=str(planned["slot_id"]),
                        family="F4",
                        program_id=diagnostic_program["program_id"],
                        candidate_universe_sha256=candidate_hash,
                        prefix_artifact_sha256=manifest["artifact_sha256"],
                        actual_prefix_end_qpos=qpos,
                        execution_spec=suffix["execution_spec"],
                        controls=controls,
                        planner_query_receipts=list(scene.planner_queries),
                    )
                    written = write_frozen_suffix_artifact(
                        gate_dir / "suffix_artifact", suffix_manifest, suffix_arrays
                    )
                    _write_json(
                        gate_dir / "preflight_receipt.json", suffix
                    )
                    return suffix, written

                try:
                    suffix_receipt, _ = self.helper._scene_call(
                        receipt=receipt,
                        planned_spec=planned,
                        planned_spec_sha256=planned_hash,
                        phase=f"f4_staged_preflight:{gate_id}",
                        program=diagnostic_program,
                        program_sha256=hash_json(diagnostic_program),
                        callback=preflight_callback,
                    )
                finally:
                    receipt["planner_query_count"] += int(runtime["queries"])

                suffix_manifest, _, controls = load_frozen_suffix_artifact(
                    gate_dir / "suffix_artifact"
                )
                spec = dict(suffix_manifest["execution_spec"])
                spec["control_cache_key"] = suffix_manifest[
                    "execution_spec_sha256"
                ]

                def execution_callback(scene, _program):
                    require_same_current(current, dict(self.adapter.capture_current(scene)))
                    start = compare_anchors(anchor, dict(self.adapter.capture_anchor(scene)))
                    if not start["equivalent"]:
                        raise ValueError(f"F4 {gate_id} execution anchor mismatch")
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
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    replay["replayed_prefix_physical_acceptance"] = replay_physical
                    if replay_physical.get("pass") is not True:
                        raise ValueError(f"F4 {gate_id} execution prefix physical Gate failed")
                    if replay["actual_prefix_end_qpos_sha256"] != suffix_manifest[
                        "actual_prefix_end_qpos_sha256"
                    ]:
                        raise ValueError(f"F4 {gate_id} replay-end qpos mismatch")
                    install_frozen_suffix_controls(scene, spec, controls)
                    before = int(getattr(scene, "planner_query_count", 0))
                    receipt["execution_attempt_count"] += 1
                    try:
                        result = self.adapter.execute_frozen_suffix_spec(
                            scene,
                            diagnostic_program,
                            spec,
                            replay,
                            {"realization": "diagnostic", "formal_data": False, "stage0_data": False},
                        )
                    except BaseException:
                        if hasattr(scene, "save_trace"):
                            partial_path = gate_dir / "partial_trace_source.npz"
                            partial = dict(scene.save_trace(partial_path))
                            partial["sha256"] = hashlib.sha256(
                                partial_path.read_bytes()
                            ).hexdigest()
                            _write_json(
                                gate_dir / "receipt.json",
                                {
                                    "status": "failed_execution",
                                    "roles": list(roles),
                                    "partial_trace_source": partial,
                                    "formal_data": False,
                                    "stage0_data": False,
                                },
                            )
                        raise
                    if int(getattr(scene, "planner_query_count", 0)) != before:
                        raise ValueError("F4 staged frozen execution invoked planner")
                    if hasattr(scene, "save_trace"):
                        path = gate_dir / "trace_source.npz"
                        trace = dict(scene.save_trace(path))
                        trace["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                        result.setdefault("provenance", {})[
                            "trace_source_sha256"
                        ] = trace["sha256"]
                        result["provenance"][
                            "trace_source_relative_path"
                        ] = "../trace_source.npz"
                    else:
                        raise ValueError("F4 staged execution lacks trace persistence")
                    raw = write_raw_attempt(
                        gate_dir / "raw",
                        result["streams"],
                        result["audit_streams"],
                        result["provenance"],
                    )
                    try:
                        verifier = self.adapter.verify(
                            scene, diagnostic_program, result
                        )
                    except BaseException as exc:
                        _write_json(
                            gate_dir / "receipt.json",
                            {
                                "status": "failed_verifier_exception",
                                "roles": list(roles),
                                "raw_manifest": raw,
                                "trace_source": trace,
                                "semantic_verifier": result.get(
                                    "semantic_verifier"
                                ),
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "formal_data": False,
                                "stage0_data": False,
                            },
                        )
                        raise
                    return {
                        "status": "passed"
                        if verifier.get("pass") is True
                        else "failed_verifier",
                        "roles": list(roles),
                        "prefix_replay": replay,
                        "suffix_planner": suffix_receipt,
                        "semantic_verifier": result["semantic_verifier"],
                        "verifier": verifier,
                        "raw_manifest": raw,
                        "trace_source": trace,
                    }

                gate_receipt = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase=f"f4_staged_execution:{gate_id}",
                    program=diagnostic_program,
                    program_sha256=hash_json(diagnostic_program),
                    callback=execution_callback,
                )
                receipt["gate_receipts"].append(gate_receipt)
                _write_json(gate_dir / "receipt.json", gate_receipt)
                if gate_receipt.get("status") != "passed":
                    raise ValueError(
                        f"F4 staged {gate_id} semantic verifier failed"
                    )

            receipt["status"] = (
                "passed_f4_staged_block_gate"
                if len(receipt["gate_receipts"]) == len(GATE_SEQUENCE)
                and all(item.get("status") == "passed" for item in receipt["gate_receipts"])
                else "failed_f4_staged_block_gate"
            )
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            if receipt["status"] == "running":
                receipt["status"] = "failed_f4_staged_block_gate"
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
        _write_json(output_dir / "receipt.json", receipt)
        return receipt
