"""Runtime-v3_3 root orchestration with one canonical prefix artifact."""

from __future__ import annotations

import hashlib
import json
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
from .current_hasher import hash_json, require_same_current
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

    def __init__(self, adapter):
        super().__init__(adapter, implementation_version=IMPLEMENTATION_VERSION)

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
            "implementation_version": IMPLEMENTATION_VERSION,
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
                    require_same_current(
                        reference_current, dict(self.adapter.capture_current(scene))
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
                require_same_current(reference_current, current)
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
                    result = _validate_prefix_reference_result(
                        self.adapter.plan_and_execute_canonical_prefix(
                            scene, prefix_call
                        )
                    )
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

                suffix_runtime = {"planner_query_count": 0}

                def suffix_preflight_callback(scene, candidate):
                    preflight_current = dict(self.adapter.capture_current(scene))
                    require_same_current(reference_current, preflight_current)
                    preflight_anchor = dict(self.adapter.capture_anchor(scene))
                    start_anchor_result = compare_anchors(
                        reference_anchor, preflight_anchor
                    )
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
                    if replay["prefix_end_equivalent"] is not True:
                        raise PrefixArtifactError(
                            "suffix preflight prefix-end state is not equivalent"
                        )
                    replay_physical = dict(
                        self.adapter.validate_replayed_prefix_physical(
                            scene, replay
                        )
                    )
                    replay["replayed_prefix_physical_acceptance"] = replay_physical
                    if replay_physical.get("pass") is not True:
                        raise PrefixArtifactError(
                            "suffix preflight replayed prefix physical Gate failed"
                        )
                    planner_before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        suffix = _validate_suffix_planner_receipt(
                            self.adapter.plan_suffix_from_actual_prefix_end_state(
                                scene, candidate, replay
                            ),
                            program_id,
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
                    suffix["prefix_replay"] = replay
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
                    suffix_public = {
                        "program_id": program_id,
                        "status": "failed",
                        "planner_solvable": False,
                        "planner_query_count": int(
                            suffix_runtime["planner_query_count"]
                        ),
                        "failure_type": type(exc).__name__,
                        "evidence": {"error": str(exc)},
                        "actual_prefix_end_qpos_sha256": None,
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
                    require_same_current(reference_current, branch_current)
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
