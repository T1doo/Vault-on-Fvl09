"""Runtime-v3_3 root orchestration with one canonical prefix artifact."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

import numpy as np

from .anchor import compare_anchors
from .candidate_freezer import freeze_candidate_universe
from .canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import (
    SameCurrentMismatch,
    hash_json,
    require_same_current,
)
from .family_runners_v3_3 import install_frozen_suffix_controls
from .frozen_suffix_artifact_v1 import (
    build_frozen_suffix_artifact,
    load_frozen_suffix_artifact,
    write_frozen_suffix_artifact,
)
from .raw_writer import write_raw_attempt
from .root_orchestrator_v1_1 import (
    CandidateMutationError,
    CleanupUncertain,
    RealSapienPilotRootOrchestratorV1_1,
    TaskPhysicalFeasibilityError,
    _immutable_copy,
    _json_compatible,
    _require_unchanged,
    _save_partial_trace_if_available,
    _validate_task_physical_receipt,
    _write_json,
    finalize_three_branch_root_v1_1,
    validate_executed_prefix_evidence,
)
from .schemas import validate_exactly_three_programs


IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
ROOT_SCHEMA_VERSION = "cmf_real_sapien_strict_prefix_root_orchestrator_v1_2"


class PrefixArtifactError(RuntimeError):
    pass


class SuffixPlannerError(RuntimeError):
    pass


class SuffixImplementationError(RuntimeError):
    pass


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short write while sealing JSON receipt")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def _require_same_current_and_persist(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    receipt_path: Path,
    phase: str,
    program_id: str | None,
    scene_instance_id: str | None,
) -> None:
    try:
        require_same_current(reference, candidate)
    except SameCurrentMismatch as exc:
        payload = dict(exc.receipt)
        payload.pop("receipt_sha256", None)
        payload.update(
            {
                "phase": phase,
                "program_id": program_id,
                "scene_instance_id": scene_instance_id,
                "saved_before_scene_cleanup": True,
            }
        )
        payload["receipt_sha256"] = hash_json(payload)
        _write_json_atomic(receipt_path, payload)
        raise


def _persist_prefix_gate_failure(
    scene,
    *,
    receipt_path: Path,
    trace_path: Path,
    phase: str,
    error_type: str,
    error: str,
    replay: Mapping[str, Any] | None,
    replay_physical: Mapping[str, Any] | None,
) -> dict:
    failure = {
        "schema_version": "cmf_prefix_replay_failure_receipt_v1",
        "status": "failed_prefix_replay_gate",
        "phase": phase,
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "error_type": error_type,
        "error": error,
        "prefix_end_equivalent": None
        if replay is None
        else replay.get("prefix_end_equivalent"),
        "actual_prefix_end_qpos_sha256": None
        if replay is None
        else replay.get("actual_prefix_end_qpos_sha256"),
        "reference_event_boundaries": None
        if replay is None
        else replay.get("reference_event_boundaries"),
        "replayed_prefix_physical_acceptance": None
        if replay_physical is None
        else dict(replay_physical),
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
    }
    if hasattr(scene, "save_trace"):
        try:
            trace = dict(scene.save_trace(trace_path))
            trace["sha256"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
            failure["partial_trace_source"] = trace
        except BaseException as trace_exc:
            failure["partial_trace_save_error"] = {
                "type": type(trace_exc).__name__,
                "message": str(trace_exc),
            }
    failure["failure_receipt_sha256"] = hash_json(failure)
    _write_json_atomic(receipt_path, failure)
    return failure


def _build_suffix_preflight_boundary_receipt(
    scene,
    *,
    phase: str,
    program_id: str,
    reference_current_sha256: str,
    preflight_current_sha256: str,
    start_anchor_equivalence: Mapping[str, Any],
    replay: Mapping[str, Any],
    replay_physical: Mapping[str, Any],
) -> dict:
    """Seal positive current/anchor/prefix evidence before suffix planning."""

    payload = _json_compatible(
        {
            "schema_version": "cmf_suffix_preflight_boundary_receipt_v1",
            "status": "passed_suffix_preflight_boundary",
            "phase": phase,
            "program_id": program_id,
            "scene_instance_id": getattr(
                scene, "_cmf_scene_instance_id", None
            ),
            "reference_current_sha256": reference_current_sha256,
            "preflight_current_sha256": preflight_current_sha256,
            "same_current_pass": (
                preflight_current_sha256 == reference_current_sha256
            ),
            "preflight_start_anchor_equivalence": dict(
                start_anchor_equivalence
            ),
            "prefix_replay": dict(replay),
            "actual_prefix_end_qpos_sha256": replay.get(
                "actual_prefix_end_qpos_sha256"
            ),
            "actual_dual_prefix_end_qpos_sha256": replay.get(
                "actual_dual_prefix_end_qpos_sha256"
            ),
            "replayed_prefix_physical_acceptance": dict(replay_physical),
            "planner_query_delta_before_suffix_planner": 0,
            "saved_before_suffix_planner": True,
            "saved_before_scene_cleanup": True,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
        }
    )
    payload["boundary_receipt_sha256"] = hash_json(payload)
    return payload


def _persist_suffix_preflight_failure(
    scene,
    *,
    receipt_path: Path,
    trace_path: Path,
    phase: str,
    program_id: str,
    error: BaseException,
    planner_query_count: int,
    planner_query_start_index: int,
    boundary_receipt: Mapping[str, Any] | None,
) -> dict:
    """Persist suffix-construction/planner exceptions before scene cleanup."""

    query_table = getattr(scene, "planner_queries", [])
    planner_query_table_error = None
    try:
        planner_query_receipts = _json_compatible(
            [
                dict(item)
                for item in list(query_table)[
                    int(planner_query_start_index) :
                ]
            ]
        )
    except BaseException as query_exc:
        planner_query_receipts = []
        planner_query_table_error = {
            "type": type(query_exc).__name__,
            "message": str(query_exc),
        }

    controller_partial = getattr(
        scene, "_cmf_suffix_preflight_partial_receipt", None
    )
    if isinstance(controller_partial, Mapping):
        controller_partial = _json_compatible(dict(controller_partial))
    elif controller_partial is not None:
        controller_partial = {
            "invalid_type": type(controller_partial).__name__,
            "repr": repr(controller_partial),
        }

    boundary = (
        None
        if boundary_receipt is None
        else _json_compatible(dict(boundary_receipt))
    )
    failure = {
        "schema_version": "cmf_suffix_preflight_failure_receipt_v1",
        "status": "failed_implementation_error",
        "failure_stage": "suffix_implementation_error",
        "phase": phase,
        "program_id": program_id,
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "error_type": type(error).__name__,
        "error": str(error),
        "traceback": traceback.format_exc(),
        "planner_query_count": int(planner_query_count),
        "planner_query_receipts": planner_query_receipts,
        "planner_query_table_error": planner_query_table_error,
        "preflight_boundary_receipt": boundary,
        "actual_prefix_end_qpos_sha256": None
        if boundary is None
        else boundary.get("actual_prefix_end_qpos_sha256"),
        "controller_partial_evidence": controller_partial,
        "partial_output_status": "evidence_saved_before_cleanup",
        "saved_before_scene_cleanup": True,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
    }
    if hasattr(scene, "save_trace"):
        try:
            trace = dict(scene.save_trace(trace_path))
            trace["sha256"] = hashlib.sha256(
                trace_path.read_bytes()
            ).hexdigest()
            failure["partial_trace_source"] = _json_compatible(trace)
            failure["partial_output_status"] = (
                "partial_trace_and_evidence_saved_before_cleanup"
            )
        except BaseException as trace_exc:
            failure["partial_trace_save_error"] = {
                "type": type(trace_exc).__name__,
                "message": str(trace_exc),
            }
    failure = _json_compatible(failure)
    failure["failure_receipt_sha256"] = hash_json(failure)
    _write_json_atomic(receipt_path, failure)
    return failure


def _step_hashes(actions: np.ndarray) -> list[str]:
    return [
        hashlib.sha256(np.ascontiguousarray(row).tobytes(order="C")).hexdigest()
        for row in np.asarray(actions, dtype=np.float64)
    ]


def _validate_prefix_reference_result(value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping):
        raise PrefixArtifactError("prefix reference result must be structured")
    required = (
        "arrays",
        "semantic_prefix_end_anchor",
        "acceptance_prefix_end_anchor",
        "planner_query_receipts",
        "planner_source_hash",
        "settling_step_count",
        "settling_policy",
        "prefix_physical_acceptance",
    )
    missing = [key for key in required if key not in value]
    if missing:
        raise PrefixArtifactError(f"prefix reference result missing {missing}")
    return dict(value)


def _validate_suffix_planner_receipt(value: Mapping[str, Any], program_id: str) -> dict:
    if not isinstance(value, Mapping):
        raise SuffixPlannerError("suffix planner receipt must be structured")
    receipt = dict(value)
    required = (
        "planner_solvable",
        "planner_query_count",
        "failure_type",
        "evidence",
        "actual_prefix_end_qpos_sha256",
    )
    missing = [key for key in required if key not in receipt]
    if missing:
        raise SuffixPlannerError(f"suffix planner receipt missing {missing}")
    if receipt["planner_solvable"] not in (True, False):
        raise SuffixPlannerError("suffix planner_solvable must be boolean")
    if not isinstance(receipt["planner_query_count"], int) or receipt["planner_query_count"] < 0:
        raise SuffixPlannerError("suffix planner query count must be nonnegative")
    if receipt["planner_solvable"] and not isinstance(receipt.get("execution_spec"), Mapping):
        raise SuffixPlannerError("solvable suffix must freeze execution_spec")
    receipt["program_id"] = program_id
    receipt["status"] = "passed" if receipt["planner_solvable"] else "failed"
    return receipt


class RealSapienStrictPrefixRootOrchestratorV1_2(
    RealSapienPilotRootOrchestratorV1_1
):
    """Freeze once, generate one prefix, replay it in three fresh branches."""

    def __init__(self, adapter, *, implementation_version=IMPLEMENTATION_VERSION):
        if (
            implementation_version == IMPLEMENTATION_VERSION
            and type(adapter).__name__
            in (
                "RoboTwinRealSapienStrictPrefixAdapterV1_4",
                "F3GraspDiagnosticAdapterV10",
            )
        ):
            implementation_version = "controlled_multi_future_runtime_v3_4"
        super().__init__(adapter, implementation_version=implementation_version)

    def run_nonformal_root(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        realization_spec_by_program: Mapping[str, Mapping[str, Any]],
    ) -> dict:
        started = time.time()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        planned_spec = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned_spec)
        receipt: dict[str, Any] = {
            "schema_version": ROOT_SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": self.implementation_version,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "planned_root_slot_spec_sha256": planned_hash,
            "freeze_call_count": 0,
            "canonical_prefix_generation_count": 0,
            "task_physical_feasibility_receipts": [],
            "suffix_planner_receipts": [],
            "suffix_planner_query_count_total": 0,
            "canonical_prefix_planner_query_count": 0,
            "planner_query_count_total": 0,
            "canonical_prefix_reference_execution_count": 0,
            "suffix_prefix_replay_count": 0,
            "branch_prefix_replay_count": 0,
            "branch_execution_attempt_count": 0,
            "branch_receipts": [],
            "cleanup_records": [],
            "append_only_event_log": "root_events.jsonl",
        }
        self._event_log_path = output_dir / "root_events.jsonl"
        self._append_event(
            {
                "event": "root_started",
                "implementation_version": IMPLEMENTATION_VERSION,
                "planned_root_slot_spec_sha256": planned_hash,
            }
        )
        _write_json(output_dir / "planned_root_slot_spec.json", planned_spec)
        terminal = "failed_execution"
        try:
            def pristine_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                anchor = dict(self.adapter.capture_anchor(scene))
                programs_value = _immutable_copy(list(self.adapter.build_programs(scene)))
                validate_exactly_three_programs(programs_value)
                trees_input = _immutable_copy(programs_value)
                trees_hash = hash_json(trees_input)
                trees = _immutable_copy(self.adapter.task_trees(trees_input))
                _require_unchanged(trees_input, trees_hash, "programs passed to task_trees")
                prefix_input = _immutable_copy(programs_value)
                prefix_input_hash = hash_json(prefix_input)
                prefix_contract = _immutable_copy(
                    self.adapter.canonical_prefix_contract(prefix_input)
                )
                _require_unchanged(
                    prefix_input,
                    prefix_input_hash,
                    "programs passed to canonical_prefix_contract",
                )
                return current, anchor, programs_value, trees, prefix_contract

            reference_current, reference_anchor, programs, trees, prefix_contract = self._scene_call(
                receipt=receipt,
                planned_spec=planned_spec,
                planned_spec_sha256=planned_hash,
                phase="pristine",
                program=None,
                program_sha256=None,
                callback=pristine_callback,
            )
            if set(trees) != {"observable", "oracle"}:
                raise ValueError("task trees must contain observable and oracle")
            program_hashes = {
                program["program_id"]: hash_json(program) for program in programs
            }
            provisional = {
                "schema_version": "cmf_provisional_programs_v1_2",
                "programs": programs,
                "program_sha256": program_hashes,
            }
            provisional["provisional_programs_sha256"] = hash_json(provisional)
            _write_json(output_dir / "reference_current_hashes.json", reference_current)
            _write_json(output_dir / "reference_anchor.json", reference_anchor)
            _write_json(output_dir / "provisional_programs.json", provisional)
            _write_json(
                output_dir / "provisional_task_tree.json",
                {"schema_version": "cmf_provisional_task_trees_v1_2", **trees},
            )
            _write_json(
                output_dir / "provisional_prefix_contract.json",
                {
                    "schema_version": "cmf_provisional_prefix_contract_v1",
                    "prefix_contract": prefix_contract,
                    "prefix_contract_sha256": hash_json(prefix_contract),
                },
            )

            task_all_pass = True
            for program in programs:
                program_id = program["program_id"]

                def task_callback(scene, candidate):
                    task_current = dict(self.adapter.capture_current(scene))
                    _require_same_current_and_persist(
                        reference_current,
                        task_current,
                        receipt_path=output_dir
                        / "task_physical_feasibility"
                        / program_id
                        / "same_current_mismatch_receipt.json",
                        phase=f"task_physical_feasibility:{program_id}",
                        program_id=program_id,
                        scene_instance_id=getattr(
                            scene, "_cmf_scene_instance_id", None
                        ),
                    )
                    anchor_result = compare_anchors(
                        reference_anchor, dict(self.adapter.capture_anchor(scene))
                    )
                    if not anchor_result["equivalent"]:
                        raise ValueError(
                            f"task/physical anchor mismatch: {anchor_result['failures']}"
                        )
                    return _validate_task_physical_receipt(
                        self.adapter.audit_task_physical_feasibility(scene, candidate),
                        program_id,
                    )

                try:
                    item = self._scene_call(
                        receipt=receipt,
                        planned_spec=planned_spec,
                        planned_spec_sha256=planned_hash,
                        phase=f"task_physical_feasibility:{program_id}",
                        program=program,
                        program_sha256=program_hashes[program_id],
                        callback=task_callback,
                    )
                except (CleanupUncertain, CandidateMutationError):
                    raise
                except BaseException as exc:
                    item = {
                        "program_id": program_id,
                        "status": "failed",
                        "task_feasible": False,
                        "physical_feasible": False,
                        "planner_solvable": None,
                        "failure_type": type(exc).__name__,
                        "evidence": {"error": str(exc)},
                    }
                receipt["task_physical_feasibility_receipts"].append(item)
                self._append_event({"event": "task_physical_receipt", "receipt": item})
                task_all_pass = task_all_pass and item["status"] == "passed"
            if not task_all_pass:
                terminal = "failed_task_physical_feasibility"
                raise TaskPhysicalFeasibilityError(
                    "not all candidates passed task/physical feasibility"
                )

            _require_unchanged(planned_spec, planned_hash, "planned_root_slot_spec")
            for program in programs:
                _require_unchanged(
                    program,
                    program_hashes[program["program_id"]],
                    f"program:{program['program_id']}",
                )
            frozen = freeze_candidate_universe(
                planned_root_slot_spec=planned_spec,
                programs=programs,
                observable_task_tree=trees["observable"],
                oracle_task_tree=trees["oracle"],
                implementation_version=IMPLEMENTATION_VERSION,
            )
            receipt["freeze_call_count"] = 1
            _write_json(output_dir / "candidate_frozen_root_spec.json", frozen)

            prefix_runtime = {"planner_query_count": 0}

            def prefix_reference_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                _require_same_current_and_persist(
                    reference_current,
                    current,
                    receipt_path=output_dir
                    / "canonical_prefix_same_current_mismatch_receipt.json",
                    phase="canonical_prefix_reference",
                    program_id=None,
                    scene_instance_id=getattr(
                        scene, "_cmf_scene_instance_id", None
                    ),
                )
                start_anchor = dict(self.adapter.capture_anchor(scene))
                start_result = compare_anchors(reference_anchor, start_anchor)
                if not start_result["equivalent"]:
                    raise PrefixArtifactError(
                        f"prefix reference start anchor mismatch: {start_result['failures']}"
                    )
                receipt["canonical_prefix_reference_execution_count"] = 1
                planner_before = int(getattr(scene, "planner_query_count", 0))
                prefix_call = _immutable_copy(prefix_contract)
                prefix_call_hash = hash_json(prefix_call)
                try:
                    try:
                        result = _validate_prefix_reference_result(
                            self.adapter.plan_and_execute_canonical_prefix(
                                scene, prefix_call
                            )
                        )
                    except BaseException as exc:
                        failure = {
                            "schema_version": "cmf_canonical_prefix_failure_receipt_v1",
                            "status": "failed_canonical_prefix_reference",
                            "family": getattr(
                                self.adapter, "family", planned_spec["family"]
                            ),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "planner_query_count": int(
                                getattr(scene, "planner_query_count", 0)
                            )
                            - planner_before,
                            "structured_gate_evidence": getattr(
                                scene, "_cmf_prefix_failure_receipt", None
                            ),
                            "formal_data": False,
                            "stage0_data": False,
                            "stage0_authorized": False,
                        }
                        if hasattr(scene, "save_trace"):
                            partial_path = (
                                output_dir
                                / "canonical_prefix_reference_partial_trace.npz"
                            )
                            try:
                                partial = dict(scene.save_trace(partial_path))
                                partial["sha256"] = hashlib.sha256(
                                    partial_path.read_bytes()
                                ).hexdigest()
                                failure["partial_trace_source"] = partial
                            except BaseException as trace_exc:
                                failure["partial_trace_save_error"] = {
                                    "type": type(trace_exc).__name__,
                                    "message": str(trace_exc),
                                }
                        failure["failure_receipt_sha256"] = hash_json(failure)
                        _write_json_atomic(
                            output_dir / "canonical_prefix_failure_receipt.json",
                            failure,
                        )
                        receipt["canonical_prefix_failure_receipt"] = failure
                        raise
                finally:
                    _require_unchanged(
                        prefix_call,
                        prefix_call_hash,
                        "canonical prefix contract passed to adapter",
                    )
                    prefix_runtime["planner_query_count"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - planner_before
                if len(result["planner_query_receipts"]) != int(
                    prefix_runtime["planner_query_count"]
                ):
                    raise PrefixArtifactError(
                        "canonical-prefix planner API count differs from its receipt table"
                    )
                if hasattr(scene, "save_trace"):
                    trace_path = output_dir / "canonical_prefix_reference_trace.npz"
                    info = dict(scene.save_trace(trace_path))
                    result["trace_source"] = {
                        **info,
                        "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                    }
                return result

            try:
                prefix_result = self._scene_call(
                    receipt=receipt,
                    planned_spec=planned_spec,
                    planned_spec_sha256=planned_hash,
                    phase="canonical_prefix_reference",
                    program=None,
                    program_sha256=None,
                    callback=prefix_reference_callback,
                )
            finally:
                receipt["canonical_prefix_planner_query_count"] = int(
                    prefix_runtime["planner_query_count"]
                )
                receipt["planner_query_count_total"] = int(
                    receipt["canonical_prefix_planner_query_count"]
                ) + int(receipt["suffix_planner_query_count_total"])
            manifest, prefix_arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned_spec["slot_id"]),
                family=str(planned_spec["family"]),
                reference_current_sha256=reference_current["aggregate_sha256"],
                reference_anchor=reference_anchor,
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
                output_dir / "canonical_prefix_artifact", manifest, prefix_arrays
            )
            receipt["canonical_prefix_generation_count"] = 1
            receipt["canonical_prefix_artifact_sha256"] = manifest["artifact_sha256"]
            candidate_prefix_link = {
                "schema_version": "cmf_candidate_prefix_link_receipt_v1",
                "candidate_frozen_root_spec_sha256": frozen[
                    "frozen_spec_sha256"
                ],
                "candidate_universe_sha256": frozen[
                    "candidate_universe_sha256"
                ],
                "observable_task_tree_sha256": frozen[
                    "observable_task_tree_sha256"
                ],
                "oracle_task_tree_sha256": frozen[
                    "oracle_task_tree_sha256"
                ],
                "canonical_prefix_artifact_sha256": manifest[
                    "artifact_sha256"
                ],
                "prefix_contract_sha256": manifest[
                    "prefix_contract_sha256"
                ],
                "formal_data": False,
                "stage0_data": False,
            }
            candidate_prefix_link["link_receipt_sha256"] = hash_json(
                candidate_prefix_link
            )
            receipt["candidate_prefix_link"] = candidate_prefix_link
            _write_json(
                output_dir / "candidate_prefix_link_receipt.json",
                candidate_prefix_link,
            )
            self._append_event(
                {
                    "event": "canonical_prefix_artifact_sealed",
                    "artifact_sha256": manifest["artifact_sha256"],
                    "prefix_action_sha256": manifest["prefix_action_sha256"],
                    "prefix_step_count": manifest["prefix_step_count"],
                }
            )

            expected_ids = {program["program_id"] for program in programs}
            if set(realization_spec_by_program) != expected_ids:
                raise ValueError("realization specs must cover the frozen programs")

            # Gate all three suffix planners before any suffix execution.
            suffix_artifact_dirs = {}
            suffix_public_receipts = {}
            suffix_all_pass = True
            for program in programs:
                program_id = program["program_id"]
                preflight_dir = output_dir / "suffix_preflight" / program_id
                preflight_dir.mkdir(parents=True, exist_ok=False)

                suffix_runtime = {
                    "planner_query_count": 0,
                    "prefix_replay_failure": None,
                    "preflight_current_sha256": None,
                    "same_current_pass": False,
                    "preflight_start_anchor_equivalence": None,
                    "prefix_replay": None,
                    "actual_prefix_end_qpos_sha256": None,
                    "replayed_prefix_physical_acceptance": None,
                    "preflight_boundary_receipt": None,
                    "failure_receipt": None,
                    "failure_persistence_error": None,
                }

                def suffix_preflight_callback(scene, candidate):
                    preflight_current = dict(self.adapter.capture_current(scene))
                    suffix_runtime["preflight_current_sha256"] = (
                        preflight_current.get("aggregate_sha256")
                    )
                    _require_same_current_and_persist(
                        reference_current,
                        preflight_current,
                        receipt_path=preflight_dir
                        / "same_current_mismatch_receipt.json",
                        phase=f"suffix_preflight:{program_id}",
                        program_id=program_id,
                        scene_instance_id=getattr(
                            scene, "_cmf_scene_instance_id", None
                        ),
                    )
                    suffix_runtime["same_current_pass"] = True
                    preflight_anchor = dict(self.adapter.capture_anchor(scene))
                    start_anchor_result = compare_anchors(
                        reference_anchor, preflight_anchor
                    )
                    suffix_runtime[
                        "preflight_start_anchor_equivalence"
                    ] = start_anchor_result
                    if not start_anchor_result["equivalent"]:
                        raise ValueError(
                            f"suffix preflight start anchor mismatch: {start_anchor_result['failures']}"
                        )
                    self.adapter.initialize_prefix_replay_trace(scene)
                    receipt["suffix_prefix_replay_count"] += 1
                    replay = replay_canonical_prefix(
                        scene,
                        manifest=manifest,
                        arrays=prefix_arrays,
                        reference_current=reference_current,
                        capture_current=self.adapter.capture_current,
                        capture_anchor=self.adapter.capture_anchor,
                    )
                    suffix_runtime["prefix_replay"] = replay
                    suffix_runtime["actual_prefix_end_qpos_sha256"] = (
                        replay.get("actual_prefix_end_qpos_sha256")
                    )
                    if replay["prefix_end_equivalent"] is not True:
                        suffix_runtime["prefix_replay_failure"] = _persist_prefix_gate_failure(
                            scene,
                            receipt_path=preflight_dir
                            / "prefix_replay_failure_receipt.json",
                            trace_path=preflight_dir
                            / "prefix_replay_failure_trace.npz",
                            phase=f"suffix_preflight:{program_id}",
                            error_type="PrefixArtifactError",
                            error="suffix preflight prefix-end state is not equivalent",
                            replay=replay,
                            replay_physical=None,
                        )
                        raise PrefixArtifactError(
                            "suffix preflight prefix-end state is not equivalent"
                        )
                    replay_physical = dict(
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    replay["replayed_prefix_physical_acceptance"] = replay_physical
                    suffix_runtime[
                        "replayed_prefix_physical_acceptance"
                    ] = replay_physical
                    if replay_physical.get("pass") is not True:
                        suffix_runtime["prefix_replay_failure"] = _persist_prefix_gate_failure(
                            scene,
                            receipt_path=preflight_dir
                            / "prefix_replay_failure_receipt.json",
                            trace_path=preflight_dir
                            / "prefix_replay_failure_trace.npz",
                            phase=f"suffix_preflight:{program_id}",
                            error_type="PrefixArtifactError",
                            error="suffix preflight replayed prefix physical Gate failed",
                            replay=replay,
                            replay_physical=replay_physical,
                        )
                        raise PrefixArtifactError(
                            "suffix preflight replayed prefix physical Gate failed"
                        )
                    boundary_receipt = _build_suffix_preflight_boundary_receipt(
                        scene,
                        phase=f"suffix_preflight:{program_id}",
                        program_id=program_id,
                        reference_current_sha256=reference_current[
                            "aggregate_sha256"
                        ],
                        preflight_current_sha256=preflight_current[
                            "aggregate_sha256"
                        ],
                        start_anchor_equivalence=start_anchor_result,
                        replay=replay,
                        replay_physical=replay_physical,
                    )
                    _write_json_atomic(
                        preflight_dir / "preflight_boundary_receipt.json",
                        boundary_receipt,
                    )
                    suffix_runtime[
                        "preflight_boundary_receipt"
                    ] = boundary_receipt
                    self._append_event(
                        {
                            "event": "suffix_preflight_boundary_sealed",
                            "program_id": program_id,
                            "boundary_receipt_sha256": boundary_receipt[
                                "boundary_receipt_sha256"
                            ],
                            "actual_prefix_end_qpos_sha256": boundary_receipt[
                                "actual_prefix_end_qpos_sha256"
                            ],
                        }
                    )
                    planner_before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        try:
                            suffix = _validate_suffix_planner_receipt(
                                self.adapter.plan_suffix_from_actual_prefix_end_state(
                                    scene, candidate, replay
                                ),
                                program_id,
                            )
                            controller_partial = getattr(
                                scene,
                                "_cmf_suffix_preflight_partial_receipt",
                                None,
                            )
                            if isinstance(controller_partial, Mapping):
                                controller_partial = _json_compatible(
                                    dict(controller_partial)
                                )
                                suffix[
                                    "controller_partial_evidence"
                                ] = controller_partial
                                _write_json_atomic(
                                    preflight_dir
                                    / "controller_partial_evidence.json",
                                    controller_partial,
                                )
                        finally:
                            suffix_runtime["planner_query_count"] = int(
                                getattr(scene, "planner_query_count", 0)
                            ) - planner_before
                        if suffix["planner_query_count"] != int(
                            suffix_runtime["planner_query_count"]
                        ):
                            raise SuffixPlannerError(
                                "suffix planner API count differs from its reported count"
                            )
                        if (
                            suffix["actual_prefix_end_qpos_sha256"]
                            != replay["actual_prefix_end_qpos_sha256"]
                        ):
                            raise SuffixPlannerError(
                                "suffix planner did not start from actual replay-end qpos"
                            )
                        controls = suffix.pop("_execution_controls", None)
                        actual_qpos = suffix.pop("_actual_prefix_end_qpos", None)
                        suffix["preflight_current_sha256"] = preflight_current[
                            "aggregate_sha256"
                        ]
                        suffix["preflight_start_anchor_equivalence"] = start_anchor_result
                        suffix["preflight_boundary_receipt"] = boundary_receipt
                        suffix["prefix_replay"] = replay
                        suffix["failure_stage"] = (
                            None
                            if suffix["planner_solvable"] is True
                            else "suffix_planner"
                        )
                        if suffix["planner_solvable"] is True:
                            suffix_manifest, suffix_arrays = build_frozen_suffix_artifact(
                                root_slot_id=str(planned_spec["slot_id"]),
                                family=str(planned_spec["family"]),
                                program_id=program_id,
                                candidate_universe_sha256=frozen[
                                    "candidate_universe_sha256"
                                ],
                                prefix_artifact_sha256=manifest["artifact_sha256"],
                                actual_prefix_end_qpos=actual_qpos,
                                execution_spec=suffix["execution_spec"],
                                controls=controls,
                                planner_query_receipts=getattr(
                                    scene, "planner_queries", []
                                ),
                            )
                            written = write_frozen_suffix_artifact(
                                output_dir / "suffix_artifacts" / program_id,
                                suffix_manifest,
                                suffix_arrays,
                            )
                            suffix["suffix_artifact_sha256"] = written[
                                "artifact_sha256"
                            ]
                        if hasattr(scene, "save_trace"):
                            trace_path = preflight_dir / "trace_source.npz"
                            info = dict(scene.save_trace(trace_path))
                            trace_hash = hashlib.sha256(trace_path.read_bytes()).hexdigest()
                            suffix["trace_source"] = {**info, "sha256": trace_hash}
                        _write_json(preflight_dir / "receipt.json", suffix)
                        return suffix
                    except BaseException as exc:
                        try:
                            suffix_runtime[
                                "failure_receipt"
                            ] = _persist_suffix_preflight_failure(
                                scene,
                                receipt_path=preflight_dir
                                / "suffix_preflight_failure_receipt.json",
                                trace_path=preflight_dir
                                / "partial_trace_source.npz",
                                phase=f"suffix_preflight:{program_id}",
                                program_id=program_id,
                                error=exc,
                                planner_query_count=int(
                                    suffix_runtime["planner_query_count"]
                                ),
                                planner_query_start_index=planner_before,
                                boundary_receipt=boundary_receipt,
                            )
                        except BaseException as persistence_exc:
                            suffix_runtime[
                                "failure_persistence_error"
                            ] = {
                                "type": type(persistence_exc).__name__,
                                "message": str(persistence_exc),
                            }
                        raise
                    finally:
                        suffix_runtime["planner_query_count"] = int(
                            getattr(scene, "planner_query_count", 0)
                        ) - planner_before

                try:
                    suffix_public = self._scene_call(
                        receipt=receipt,
                        planned_spec=planned_spec,
                        planned_spec_sha256=planned_hash,
                        phase=f"suffix_preflight:{program_id}",
                        program=program,
                        program_sha256=program_hashes[program_id],
                        callback=suffix_preflight_callback,
                    )
                except (CleanupUncertain, CandidateMutationError):
                    raise
                except BaseException as exc:
                    prefix_failure = suffix_runtime[
                        "prefix_replay_failure"
                    ]
                    failure_stage = (
                        "prefix_replay_gate"
                        if prefix_failure is not None
                        else "suffix_implementation_error"
                    )
                    suffix_public = {
                        "program_id": program_id,
                        "status": "failed",
                        "planner_solvable": False,
                        "planner_query_count": int(
                            suffix_runtime["planner_query_count"]
                        ),
                        "failure_type": type(exc).__name__,
                        "failure_stage": failure_stage,
                        "evidence": {
                            "error": str(exc),
                            "prefix_replay_failure": prefix_failure,
                            "suffix_preflight_failure": suffix_runtime[
                                "failure_receipt"
                            ],
                            "failure_persistence_error": suffix_runtime[
                                "failure_persistence_error"
                            ],
                        },
                        "preflight_current_sha256": suffix_runtime[
                            "preflight_current_sha256"
                        ],
                        "same_current_pass": suffix_runtime[
                            "same_current_pass"
                        ],
                        "preflight_start_anchor_equivalence": suffix_runtime[
                            "preflight_start_anchor_equivalence"
                        ],
                        "preflight_boundary_receipt": suffix_runtime[
                            "preflight_boundary_receipt"
                        ],
                        "prefix_replay": suffix_runtime["prefix_replay"],
                        "replayed_prefix_physical_acceptance": suffix_runtime[
                            "replayed_prefix_physical_acceptance"
                        ],
                        "actual_prefix_end_qpos_sha256": suffix_runtime[
                            "actual_prefix_end_qpos_sha256"
                        ],
                        "partial_output_status": (
                            "suffix_preflight_failure_evidence_saved"
                            if suffix_runtime["failure_receipt"] is not None
                            else "suffix_preflight_failure_evidence_incomplete"
                        ),
                    }
                    _write_json(preflight_dir / "receipt.json", suffix_public)
                receipt["suffix_planner_receipts"].append(suffix_public)
                receipt["suffix_planner_query_count_total"] += int(
                    suffix_public.get("planner_query_count", 0)
                )
                receipt["planner_query_count_total"] = int(
                    receipt["canonical_prefix_planner_query_count"]
                ) + int(receipt["suffix_planner_query_count_total"])
                self._append_event(
                    {"event": "suffix_planner_receipt", "receipt": suffix_public}
                )
                suffix_public_receipts[program_id] = suffix_public
                passed = suffix_public.get("planner_solvable") is True
                suffix_all_pass = suffix_all_pass and passed
                if passed:
                    suffix_artifact_dirs[program_id] = (
                        output_dir / "suffix_artifacts" / program_id
                    )

            family_suffix_gate = dict(
                self.adapter.validate_family_suffix_gate(
                    receipt["suffix_planner_receipts"]
                )
            )
            receipt["family_suffix_gate"] = family_suffix_gate
            _write_json(output_dir / "family_suffix_gate.json", family_suffix_gate)
            if not suffix_all_pass:
                stages = {
                    item.get("failure_stage")
                    for item in receipt["suffix_planner_receipts"]
                }
                if "prefix_replay_gate" in stages:
                    terminal = "failed_prefix_replay_gate"
                    raise SuffixPlannerError(
                        "at least one suffix preflight failed its prefix replay Gate"
                    )
                if "suffix_implementation_error" in stages:
                    terminal = "failed_implementation_error"
                    raise SuffixImplementationError(
                        "at least one suffix preflight raised an implementation error"
                    )
                terminal = "failed_planner"
                raise SuffixPlannerError(
                    "not all three suffix planners passed from actual replay-end qpos"
                )
            if family_suffix_gate.get("pass") is not True:
                terminal = "failed_family_suffix_gate"
                raise SuffixPlannerError("family comparative suffix Gate failed")

            # Only after 3/3 planner Gate: replay in three fresh execution scenes.
            for program in programs:
                program_id = program["program_id"]
                suffix_manifest, _, suffix_controls = load_frozen_suffix_artifact(
                    suffix_artifact_dirs[program_id]
                )
                execution_spec = dict(suffix_manifest["execution_spec"])
                execution_spec["control_cache_key"] = suffix_manifest[
                    "execution_spec_sha256"
                ]
                execution_spec_hash = hash_json(execution_spec)
                branch_dir = output_dir / "branches" / program_id
                branch_dir.mkdir(parents=True, exist_ok=False)
                branch: dict[str, Any] = {
                    "schema_version": "cmf_strict_prefix_branch_receipt_v1_2",
                    "program_id": program_id,
                    "formal_data": False,
                    "stage0_data": False,
                    "status": "failed_execution",
                    "partial_output_status": "none",
                    "reference_current_sha256": reference_current[
                        "aggregate_sha256"
                    ],
                    "candidate_universe_sha256": frozen[
                        "candidate_universe_sha256"
                    ],
                    "prefix_artifact_sha256": manifest["artifact_sha256"],
                    "prefix_sha256": manifest["artifact_sha256"],
                    "suffix_artifact_sha256": suffix_manifest["artifact_sha256"],
                }

                def branch_callback(scene, candidate):
                    branch_current = dict(self.adapter.capture_current(scene))
                    branch["branch_current"] = branch_current
                    _require_same_current_and_persist(
                        reference_current,
                        branch_current,
                        receipt_path=branch_dir
                        / "same_current_mismatch_receipt.json",
                        phase=f"strict_prefix_branch:{program_id}",
                        program_id=program_id,
                        scene_instance_id=getattr(
                            scene, "_cmf_scene_instance_id", None
                        ),
                    )
                    branch_anchor = dict(self.adapter.capture_anchor(scene))
                    branch_anchor_result = compare_anchors(
                        reference_anchor, branch_anchor
                    )
                    if not branch_anchor_result["equivalent"]:
                        raise ValueError(
                            f"branch start anchor mismatch: {branch_anchor_result['failures']}"
                        )
                    self.adapter.initialize_prefix_replay_trace(scene)
                    receipt["branch_prefix_replay_count"] += 1
                    replay = replay_canonical_prefix(
                        scene,
                        manifest=manifest,
                        arrays=prefix_arrays,
                        reference_current=reference_current,
                        capture_current=self.adapter.capture_current,
                        capture_anchor=self.adapter.capture_anchor,
                    )
                    if replay["prefix_end_equivalent"] is not True:
                        branch["prefix_replay_failure"] = _persist_prefix_gate_failure(
                            scene,
                            receipt_path=branch_dir
                            / "prefix_replay_failure_receipt.json",
                            trace_path=branch_dir
                            / "prefix_replay_failure_trace.npz",
                            phase=f"strict_prefix_branch:{program_id}",
                            error_type="PrefixArtifactError",
                            error="branch prefix-end state is not equivalent",
                            replay=replay,
                            replay_physical=None,
                        )
                        raise PrefixArtifactError(
                            "branch prefix-end state is not equivalent"
                        )
                    replay_physical = dict(
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    replay["replayed_prefix_physical_acceptance"] = replay_physical
                    if replay_physical.get("pass") is not True:
                        branch["prefix_replay_failure"] = _persist_prefix_gate_failure(
                            scene,
                            receipt_path=branch_dir
                            / "prefix_replay_failure_receipt.json",
                            trace_path=branch_dir
                            / "prefix_replay_failure_trace.npz",
                            phase=f"strict_prefix_branch:{program_id}",
                            error_type="PrefixArtifactError",
                            error="branch replayed prefix physical Gate failed",
                            replay=replay,
                            replay_physical=replay_physical,
                        )
                        raise PrefixArtifactError(
                            "branch replayed prefix physical Gate failed"
                        )
                    if (
                        replay["actual_prefix_end_qpos_sha256"]
                        != suffix_manifest["actual_prefix_end_qpos_sha256"]
                    ):
                        raise SuffixPlannerError(
                            "execution replay-end qpos differs from suffix planner start qpos"
                        )
                    install_frozen_suffix_controls(
                        scene, execution_spec, suffix_controls
                    )
                    realization = _immutable_copy(
                        realization_spec_by_program[program_id]
                    )
                    realization_hash = hash_json(realization)
                    planner_before_execution = int(
                        getattr(scene, "planner_query_count", 0)
                    )
                    receipt["branch_execution_attempt_count"] += 1
                    try:
                        try:
                            result = dict(
                                self.adapter.execute_frozen_suffix_spec(
                                    scene,
                                    candidate,
                                    execution_spec,
                                    replay,
                                    realization,
                                )
                            )
                        finally:
                            _require_unchanged(
                                realization,
                                realization_hash,
                                f"realization spec:{program_id}",
                            )
                            _require_unchanged(
                                execution_spec,
                                execution_spec_hash,
                                f"frozen suffix execution spec:{program_id}",
                            )
                    except BaseException:
                        planner_after_failure = int(
                            getattr(scene, "planner_query_count", 0)
                        )
                        execution_planner_delta = (
                            planner_after_failure - planner_before_execution
                        )
                        branch["suffix_execution_planner_query_delta"] = int(
                            execution_planner_delta
                        )
                        receipt["planner_query_count_total"] += int(
                            execution_planner_delta
                        )
                        branch.update(
                            {
                                "branch_current": branch_current,
                                "anchor_equivalence": branch_anchor_result,
                                "prefix_replay": replay,
                                "suffix_planner": suffix_public_receipts[program_id],
                                "structured_family_failure_evidence": {
                                    "f2_inside_pre_release_settle_v6": getattr(
                                        scene,
                                        "_cmf_f2_inside_pre_release_settle_v6",
                                        None,
                                    ),
                                    "f2_inside_xy_tracking_compensation_v8": getattr(
                                        scene,
                                        "_cmf_f2_inside_xy_tracking_compensation_v8",
                                        None,
                                    ),
                                    "f2_inside_alignment_diagnostic_v7": getattr(
                                        scene,
                                        "_cmf_f2_inside_alignment_diagnostic_v7",
                                        None,
                                    ),
                                    "f2_balanced_preload_release_v9": getattr(
                                        scene,
                                        "_cmf_f2_balanced_preload_release_v9",
                                        None,
                                    ),
                                    "f3_pre_open_gate_v5": getattr(
                                        scene,
                                        "_cmf_f3_pre_open_gate_v5",
                                        None,
                                    ),
                                    "f3_release_boundary_v5": getattr(
                                        scene,
                                        "_cmf_f3_release_boundary_v5",
                                        None,
                                    ),
                                    "f3_release_geometry_v6": getattr(
                                        scene,
                                        "_cmf_f3_release_geometry_v6",
                                        None,
                                    ),
                                    "f3_realized_events_before_release_v8": getattr(
                                        scene,
                                        "_cmf_f3_realized_events_before_release_v8",
                                        None,
                                    ),
                                    "f3_symmetric_staged_release_v9": getattr(
                                        scene,
                                        "_cmf_f3_symmetric_staged_release_v9",
                                        None,
                                    ),
                                    "f4_preclose_boundary_v5": getattr(
                                        scene,
                                        "_cmf_f4_a_preclose_boundary_v5",
                                        None,
                                    ),
                                    "f4_micro_lift_gate_v5": getattr(
                                        scene,
                                        "_cmf_f4_a_micro_lift_gate_v5",
                                        None,
                                    ),
                                    "f4_micro_lift_role_input_v7": getattr(
                                        scene,
                                        "_cmf_f4_micro_lift_role_input_v7",
                                        None,
                                    ),
                                    "f4_micro_noninterference_v5": getattr(
                                        scene,
                                        "_cmf_f4_micro_noninterference_v5",
                                        None,
                                    ),
                                },
                            }
                        )
                        _save_partial_trace_if_available(
                            scene, branch_dir, branch
                        )
                        _write_json(branch_dir / "receipt.json", branch)
                        if execution_planner_delta != 0:
                            raise SuffixPlannerError(
                                "failed frozen suffix execution invoked planner"
                            )
                        raise
                    planner_after_execution = int(
                        getattr(scene, "planner_query_count", 0)
                    )
                    execution_planner_delta = (
                        planner_after_execution - planner_before_execution
                    )
                    branch["suffix_execution_planner_query_delta"] = int(
                        execution_planner_delta
                    )
                    receipt["planner_query_count_total"] += int(
                        execution_planner_delta
                    )
                    if execution_planner_delta != 0:
                        raise SuffixPlannerError(
                            "frozen suffix execution invoked planner"
                        )
                    if hasattr(scene, "save_trace"):
                        trace_path = branch_dir / "trace_source.npz"
                        info = dict(scene.save_trace(trace_path))
                        trace_hash = hashlib.sha256(trace_path.read_bytes()).hexdigest()
                        branch["trace_source"] = {**info, "sha256": trace_hash}
                        result.setdefault("provenance", {})[
                            "trace_source_sha256"
                        ] = trace_hash
                        result["provenance"][
                            "trace_source_relative_path"
                        ] = "../trace_source.npz"
                    actions = np.asarray(
                        result["streams"]["controller_effective_setpoint"],
                        dtype=np.float64,
                    )
                    boundary = int(manifest["prefix_step_count"])
                    executed_prefix = {
                        "executed_prefix_action_sha256": replay[
                            "executed_prefix_action_sha256"
                        ],
                        "executed_prefix_step_count": boundary,
                        "executed_prefix_start_state_sha256": replay[
                            "start_anchor_equivalence"
                        ]["candidate_sha256"],
                        "executed_prefix_end_state_sha256": replay[
                            "semantic_prefix_end_anchor"
                        ]["anchor_sha256"],
                        "executed_prefix_start_anchor": branch_anchor,
                        "executed_prefix_end_anchor": replay[
                            "semantic_prefix_end_anchor"
                        ],
                        "executed_prefix_acceptance_end_state_sha256": replay[
                            "acceptance_prefix_end_anchor"
                        ]["anchor_sha256"],
                        "executed_prefix_acceptance_end_anchor": replay[
                            "acceptance_prefix_end_anchor"
                        ],
                        "canonical_prefix_end_step": boundary,
                        "first_post_prefix_divergence_step": boundary,
                        "neutral_confirmation_step_count": 0,
                        "neutral_confirmation_minimum_required_steps": 0,
                        "post_prefix_action_step_sha256": _step_hashes(
                            actions[boundary:]
                        ),
                        "semantic_prefix_end_anchor": replay[
                            "semantic_prefix_end_anchor"
                        ],
                        "settling_step_count_excluded_from_semantic_prefix": replay[
                            "settling_step_count_excluded_from_semantic_prefix"
                        ],
                        "target_role_visible_during_prefix": False,
                    }
                    validate_executed_prefix_evidence(executed_prefix)
                    result["executed_prefix"] = executed_prefix
                    raw_manifest = write_raw_attempt(
                        branch_dir / "raw",
                        result["streams"],
                        result["audit_streams"],
                        result["provenance"],
                    )
                    branch.update(
                        {
                            "branch_current": branch_current,
                            "anchor_equivalence": branch_anchor_result,
                            "prefix_replay": replay,
                            "suffix_planner": suffix_public_receipts[program_id],
                            "suffix_artifact": {
                                "artifact_sha256": suffix_manifest[
                                    "artifact_sha256"
                                ],
                                "actual_prefix_end_qpos_sha256": suffix_manifest[
                                    "actual_prefix_end_qpos_sha256"
                                ],
                            },
                            "executed_prefix": executed_prefix,
                            "raw_manifest": raw_manifest,
                            "partial_output_status": "raw_saved_verifier_pending",
                            "final_state_equivalence_payload": result.get(
                                "final_state_equivalence_payload"
                            ),
                        }
                    )
                    _write_json(branch_dir / "receipt.json", branch)
                    verifier = dict(self.adapter.verify(scene, candidate, result))
                    branch["verifier"] = verifier
                    branch["partial_output_status"] = "raw_and_verifier_complete"
                    branch["status"] = (
                        "accepted" if verifier.get("pass") is True else "failed_verifier"
                    )
                    return None

                try:
                    self._scene_call(
                        receipt=receipt,
                        planned_spec=planned_spec,
                        planned_spec_sha256=planned_hash,
                        phase=f"strict_prefix_branch:{program_id}",
                        program=program,
                        program_sha256=program_hashes[program_id],
                        callback=branch_callback,
                    )
                except (CleanupUncertain, CandidateMutationError):
                    raise
                except BaseException as exc:
                    mismatch_path = (
                        branch_dir / "same_current_mismatch_receipt.json"
                    )
                    if mismatch_path.is_file():
                        branch["same_current_mismatch_receipt"] = {
                            "relative_path": mismatch_path.name,
                            "sha256": hashlib.sha256(
                                mismatch_path.read_bytes()
                            ).hexdigest(),
                            "saved_before_scene_cleanup": True,
                        }
                    branch.update(
                        {
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": getattr(exc, "cmf_traceback", None)
                            or traceback.format_exc(),
                        }
                    )
                receipt["branch_receipts"].append(branch)
                _write_json(branch_dir / "receipt.json", branch)
                self._append_event(
                    {"event": "branch_terminal_receipt", "receipt": branch}
                )

            root_cleanup_pass = all(
                item.get("cleanup_safety_pass") is True
                and item.get("orphan_process_count") == 0
                for item in receipt["cleanup_records"]
            )
            finalization = finalize_three_branch_root_v1_1(
                receipt["branch_receipts"],
                reference_current_sha256=reference_current["aggregate_sha256"],
                root_cleanup_pass=root_cleanup_pass,
            )
            expected_gripper_hashes = {
                key: manifest["array_hashes"][key]
                for key in (
                    "left_gripper_joint_drive_targets",
                    "right_gripper_joint_drive_targets",
                    "left_gripper_joint_drive_velocity_targets",
                    "right_gripper_joint_drive_velocity_targets",
                )
            }
            branch_gripper_hashes = [
                item.get("prefix_replay", {}).get(
                    "executed_gripper_drive_array_sha256"
                )
                for item in receipt["branch_receipts"]
            ]
            link_payload = dict(candidate_prefix_link)
            link_hash = link_payload.pop("link_receipt_sha256", None)
            v3_3_checks = {
                "three_replayed_gripper_drive_hashes_match_artifact": len(
                    branch_gripper_hashes
                )
                == 3
                and all(
                    item == expected_gripper_hashes
                    for item in branch_gripper_hashes
                ),
                "candidate_prefix_link_receipt_integrity": isinstance(
                    link_hash, str
                )
                and hash_json(link_payload) == link_hash,
                "candidate_prefix_link_matches_frozen_spec": candidate_prefix_link[
                    "candidate_frozen_root_spec_sha256"
                ]
                == frozen["frozen_spec_sha256"],
            }
            finalization.setdefault("checks", {}).update(v3_3_checks)
            finalization["runtime_v3_3_independent_checks"] = v3_3_checks
            finalization["accepted"] = all(
                finalization["checks"].values()
            )
            receipt["root_finalization"] = finalization
            terminal = "accepted" if finalization.get("accepted") else "failed_verifier"
        except CleanupUncertain as exc:
            terminal = "failed_cleanup_uncertain"
            receipt.update(
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        except CandidateMutationError as exc:
            terminal = "failed_candidate_mutation"
            receipt.update(
                {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        except BaseException as exc:
            receipt.setdefault("error_type", type(exc).__name__)
            receipt.setdefault("error", str(exc))
            receipt.setdefault("traceback", traceback.format_exc())
        receipt["status"] = terminal
        receipt["budget_counts"] = {
            "planner_query_count": int(receipt["planner_query_count_total"]),
            "execution_attempt_count": int(
                receipt["branch_execution_attempt_count"]
            ),
            "recovery_attempt_count": 0,
        }
        self._append_event(
            {
                "event": "root_terminal",
                "status": terminal,
                "budget_counts": receipt["budget_counts"],
                "branch_receipt_count": len(receipt["branch_receipts"]),
            }
        )
        if self._event_log_path.is_file():
            receipt["append_only_event_log_sha256"] = hashlib.sha256(
                self._event_log_path.read_bytes()
            ).hexdigest()
        receipt["elapsed_seconds"] = time.time() - started
        _write_json(output_dir / "root_receipt.json", receipt)
        return receipt
