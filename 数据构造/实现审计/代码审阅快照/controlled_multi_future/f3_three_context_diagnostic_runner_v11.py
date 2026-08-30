"""Canonical-ID three-context F3 diagnostic runner/finalizer."""

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


PROGRAM_IDS = ("F3-VVHH", "F3-VHVH", "F3-VHHV")
SCHEMA_VERSION = "cmf_f3_three_context_diagnostic_runner_v11"


def finalize_f3_three_context_diagnostics_v11(
    branch_receipts: Sequence[Mapping[str, Any]],
    *,
    cleanup_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    branches = list(branch_receipts)
    ids = [item.get("program_id") for item in branches]
    prefix_hashes = {
        item.get("prefix_replay", {}).get("executed_prefix_action_sha256")
        for item in branches
    }
    checks = {
        "exact_three_canonical_programs": ids == list(PROGRAM_IDS),
        "three_contexts_pass": len(branches) == 3
        and all(item.get("status") == "passed" for item in branches),
        "same_canonical_prefix_action_hash": len(prefix_hashes) == 1
        and None not in prefix_hashes,
        "fresh_scene_per_context": len(
            {
                item.get("scene_instance_id") for item in branches
            }
        )
        == 3,
        "diagnostic_metadata_not_program_id": len(branches) == 3
        and all(
            item.get("diagnostic_context_id")
            == "grasp_context_" + item["program_id"].split("-", 1)[1]
            for item in branches
        ),
        "release_never_executed": len(branches) == 3
        and all(item.get("release_executed") is False for item in branches),
        "diagnostic_nonroot": len(branches) == 3
        and all(item.get("diagnostic_nonroot") is True for item in branches),
        "all_cleanup_pass": bool(cleanup_records)
        and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in cleanup_records
        ),
    }
    result = {
        "schema_version": "cmf_f3_three_context_diagnostic_finalizer_v11",
        "program_ids": ids,
        "checks": checks,
        "pass": all(checks.values()),
        "accepted_root_increment": 0,
        "generic_root_final_state_equivalence_called": False,
        "final_state_equivalence_required": False,
    }
    result["receipt_sha256"] = hash_json(result)
    return result


class F3ThreeContextDiagnosticRunnerV11:
    def __init__(self, adapter):
        if adapter.family != "F3":
            raise ValueError("F3 diagnostic runner requires F3 adapter")
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(adapter)

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4_1",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "diagnostic_nonroot": True,
            "accepted_root_increment": 0,
            "status": "running",
            "pass": False,
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
            "branch_receipts": [],
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
                if [item["program_id"] for item in programs] != list(PROGRAM_IDS):
                    raise ValueError("F3 canonical program IDs changed")
                prefix = _immutable_copy(
                    self.adapter.canonical_prefix_contract(programs)
                )
                return current, anchor, programs, prefix

            current, anchor, programs, prefix_contract = self.helper._scene_call(
                receipt=receipt,
                planned_spec=planned,
                planned_spec_sha256=planned_hash,
                phase="f3_diagnostic_pristine",
                program=None,
                program_sha256=None,
                callback=pristine_callback,
            )
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)
            _write_json(output_dir / "canonical_programs.json", programs)
            prefix_runtime = {"queries": 0}

            def prefix_callback(scene, _program):
                require_same_current(current, dict(self.adapter.capture_current(scene)))
                if not compare_anchors(
                    anchor, dict(self.adapter.capture_anchor(scene))
                )["equivalent"]:
                    raise ValueError("F3 diagnostic prefix anchor mismatch")
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
                    phase="f3_diagnostic_prefix_reference",
                    program=None,
                    program_sha256=None,
                    callback=prefix_callback,
                )
            finally:
                receipt["planner_query_count"] += prefix_runtime["queries"]
            manifest, arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family="F3",
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
            for program in programs:
                program_id = program["program_id"]
                context = program_id.split("-", 1)[1]
                branch_dir = output_dir / f"context_{context}"
                branch_dir.mkdir(parents=True, exist_ok=False)
                preflight_runtime = {"queries": 0}

                def preflight_callback(scene, _program):
                    require_same_current(
                        current, dict(self.adapter.capture_current(scene))
                    )
                    if not compare_anchors(
                        anchor, dict(self.adapter.capture_anchor(scene))
                    )["equivalent"]:
                        raise ValueError("F3 diagnostic preflight anchor mismatch")
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
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    if physical.get("pass") is not True:
                        raise ValueError("F3 diagnostic replay physical Gate failed")
                    before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        suffix = _validate_suffix_planner_receipt(
                            self.adapter.controller_v3_3.plan_f3_first_suffix_event_diagnostic_v11(
                                scene, program, replay
                            ),
                            program_id,
                        )
                    finally:
                        preflight_runtime["queries"] = int(
                            getattr(scene, "planner_query_count", 0)
                        ) - before
                    controls = suffix.pop("_execution_controls", None)
                    qpos = suffix.pop("_actual_prefix_end_qpos", None)
                    if suffix.get("planner_solvable") is not True:
                        _write_json(branch_dir / "preflight_receipt.json", suffix)
                        raise RuntimeError("F3 targeted first suffix planner failed")
                    suffix_manifest, suffix_arrays = build_frozen_suffix_artifact(
                        root_slot_id=str(planned["slot_id"]),
                        family="F3",
                        program_id=program_id,
                        candidate_universe_sha256=candidate_hash,
                        prefix_artifact_sha256=manifest["artifact_sha256"],
                        actual_prefix_end_qpos=qpos,
                        execution_spec=suffix["execution_spec"],
                        controls=controls,
                        planner_query_receipts=list(scene.planner_queries),
                    )
                    write_frozen_suffix_artifact(
                        branch_dir / "suffix_artifact",
                        suffix_manifest,
                        suffix_arrays,
                    )
                    _write_json(branch_dir / "preflight_receipt.json", suffix)
                    return suffix

                try:
                    suffix_receipt = self.helper._scene_call(
                        receipt=receipt,
                        planned_spec=planned,
                        planned_spec_sha256=planned_hash,
                        phase=f"f3_diagnostic_preflight:{program_id}",
                        program=program,
                        program_sha256=hash_json(program),
                        callback=preflight_callback,
                    )
                finally:
                    receipt["planner_query_count"] += preflight_runtime[
                        "queries"
                    ]
                suffix_manifest, _, controls = load_frozen_suffix_artifact(
                    branch_dir / "suffix_artifact"
                )
                spec = dict(suffix_manifest["execution_spec"])
                spec["control_cache_key"] = suffix_manifest[
                    "execution_spec_sha256"
                ]
                spec["expected_canonical_prefix_action_sha256"] = manifest[
                    "prefix_action_sha256"
                ]

                def execution_callback(scene, _program):
                    require_same_current(
                        current, dict(self.adapter.capture_current(scene))
                    )
                    if not compare_anchors(
                        anchor, dict(self.adapter.capture_anchor(scene))
                    )["equivalent"]:
                        raise ValueError("F3 diagnostic execution anchor mismatch")
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
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    if physical.get("pass") is not True:
                        raise ValueError("F3 diagnostic execution prefix Gate failed")
                    install_frozen_suffix_controls(scene, spec, controls)
                    receipt["execution_attempt_count"] += 1
                    result = self.adapter.controller_v3_3.execute_grasp_robustness_diagnostic_v10(
                        scene,
                        program,
                        spec,
                        replay,
                        {
                            "realization": "grasp_context_v11",
                            "diagnostic_context_id": f"grasp_context_{context}",
                            "diagnostic_mode": (
                                "stop_after_shared_v_plus_first_suffix_event"
                            ),
                            "formal_data": False,
                            "stage0_data": False,
                        },
                    )
                    trace_path = branch_dir / "trace_source.npz"
                    trace = dict(scene.save_trace(trace_path))
                    trace["sha256"] = hashlib.sha256(
                        trace_path.read_bytes()
                    ).hexdigest()
                    result.setdefault("provenance", {})[
                        "trace_source_sha256"
                    ] = trace["sha256"]
                    raw = write_raw_attempt(
                        branch_dir / "raw",
                        result["streams"],
                        result["audit_streams"],
                        result["provenance"],
                    )
                    verifier = self.adapter.verify(scene, program, result)
                    diagnostic = result["semantic_verifier"][
                        "grasp_robustness_diagnostic_v10"
                    ]
                    return {
                        "status": "passed"
                        if verifier.get("pass") is True
                        else "failed_verifier",
                        "program_id": program_id,
                        "diagnostic_context_id": f"grasp_context_{context}",
                        "diagnostic_mode": (
                            "stop_after_shared_v_plus_first_suffix_event"
                        ),
                        "diagnostic_nonroot": True,
                        "release_executed": False,
                        "scene_instance_id": getattr(
                            scene, "_cmf_scene_instance_id", None
                        )
                        or receipt["cleanup_records"][-1].get(
                            "scene_instance_id"
                        )
                        if receipt["cleanup_records"]
                        else None,
                        "prefix_replay": replay,
                        "suffix_planner": suffix_receipt,
                        "diagnostic": diagnostic,
                        "semantic_verifier": result["semantic_verifier"],
                        "verifier": verifier,
                        "raw_manifest": raw,
                        "trace_source": trace,
                    }

                branch = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase=f"f3_diagnostic_execution:{program_id}",
                    program=program,
                    program_sha256=hash_json(program),
                    callback=execution_callback,
                )
                # Bind the unique scene ID from the just-completed cleanup.
                branch["scene_instance_id"] = receipt["cleanup_records"][-1][
                    "scene_instance_id"
                ]
                _write_json(branch_dir / "receipt.json", branch)
                receipt["branch_receipts"].append(branch)
                if branch.get("status") != "passed":
                    break
            finalizer = finalize_f3_three_context_diagnostics_v11(
                receipt["branch_receipts"],
                cleanup_records=receipt["cleanup_records"],
            )
            receipt["diagnostic_finalizer"] = finalizer
            receipt["pass"] = finalizer["pass"]
            receipt["status"] = (
                "passed_f3_three_context_diagnostic_v11"
                if finalizer["pass"]
                else "failed_f3_three_context_diagnostic_v11"
            )
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            receipt["status"] = "failed_f3_three_context_diagnostic_v11"
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
    "F3ThreeContextDiagnosticRunnerV11",
    "finalize_f3_three_context_diagnostics_v11",
]
