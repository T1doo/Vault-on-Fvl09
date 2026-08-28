"""Fail-closed runtime-v3_1 root orchestration.

This module is additive.  It does not authorize a GPU probe, Stage 0, or
formal collection.  The v1_1 contract separates task/physical feasibility
from planner solvability, binds cleanup evidence to a unique scene instance,
freezes pristine provisional artifacts before feasibility, and rejects any
adapter mutation of a program or planned-root specification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
import json
from pathlib import Path
import time
import traceback
from typing import Any, Callable, Mapping, MutableMapping, Sequence

from .anchor import compare_anchors
from .candidate_freezer import freeze_candidate_universe
from .current_hasher import hash_json, require_same_current
from .raw_writer import write_raw_attempt
from .schemas import validate_exactly_three_programs


DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_1"


class CleanupUncertain(RuntimeError):
    """A scene lacks unique, successful cleanup/orphan evidence."""


class CandidateMutationError(RuntimeError):
    """An adapter mutated a planned spec, program, task tree, or prefix."""


class TaskPhysicalFeasibilityError(RuntimeError):
    """At least one preregistered candidate is not task/physically feasible."""


class PlannerSolvabilityError(RuntimeError):
    """At least one frozen candidate failed the bounded planner audit."""


class SceneHandleV1_1:
    """Per-scene handle whose cleanup receipt cannot be reused by another scene."""

    def __init__(self, *, scene_instance_id: str, scene: Any = None):
        if not isinstance(scene_instance_id, str) or not scene_instance_id:
            raise ValueError("scene_instance_id must be a non-empty string")
        self.scene_instance_id = scene_instance_id
        self.scene = scene
        self.cleanup_receipt: dict[str, Any] | None = None


class RealSapienPilotRootAdapterV1_1(ABC):
    """Concrete adapters must return a context yielding ``SceneHandleV1_1``."""

    @abstractmethod
    def scene(self, planned_root_slot_spec, *, phase, program=None):
        raise NotImplementedError

    @abstractmethod
    def capture_current(self, scene):
        raise NotImplementedError

    @abstractmethod
    def capture_anchor(self, scene):
        raise NotImplementedError

    @abstractmethod
    def build_programs(self, pristine_scene):
        raise NotImplementedError

    @abstractmethod
    def task_trees(self, programs):
        raise NotImplementedError

    @abstractmethod
    def canonical_prefix(self, programs):
        raise NotImplementedError

    @abstractmethod
    def audit_task_physical_feasibility(self, disposable_scene, program):
        raise NotImplementedError

    @abstractmethod
    def audit_planner_solvability(self, disposable_scene, frozen_program, planner_variant):
        raise NotImplementedError

    def planner_audit_variants(self, frozen_program):
        """Return preregistered fresh-scene planner variants in fixed order."""

        return [{"variant_id": "default"}]

    @abstractmethod
    def rollout(self, fresh_scene, frozen_program, realization_spec):
        raise NotImplementedError

    @abstractmethod
    def verify(self, fresh_scene, frozen_program, rollout_result):
        raise NotImplementedError


def _write_json(path: Path, value: Mapping[str, Any] | Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _immutable_copy(value: Any) -> Any:
    """Return a detached JSON copy so adapters never receive canonical objects."""

    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def _require_unchanged(value: Any, expected_sha256: str, label: str) -> None:
    if hash_json(value) != expected_sha256:
        raise CandidateMutationError(f"adapter mutated immutable {label}")


def _cleanup_receipt_from(context: Any, handle: SceneHandleV1_1 | None) -> Mapping[str, Any] | None:
    if handle is not None and handle.cleanup_receipt is not None:
        return handle.cleanup_receipt
    return getattr(context, "cleanup_receipt", None)


def _validate_cleanup_receipt(
    cleanup: Mapping[str, Any] | None,
    *,
    expected_scene_instance_id: str | None,
    seen_scene_instance_ids: set[str],
    phase: str,
) -> dict:
    if not isinstance(cleanup, Mapping):
        raise CleanupUncertain(f"{phase} emitted no scene-bound cleanup receipt")
    record = dict(cleanup)
    scene_instance_id = record.get("scene_instance_id")
    if not isinstance(scene_instance_id, str) or not scene_instance_id:
        raise CleanupUncertain(f"{phase} cleanup receipt has no scene_instance_id")
    if expected_scene_instance_id is not None and scene_instance_id != expected_scene_instance_id:
        raise CleanupUncertain(f"{phase} cleanup receipt belongs to a different scene")
    if scene_instance_id in seen_scene_instance_ids:
        raise CleanupUncertain(f"{phase} reused cleanup receipt for {scene_instance_id}")
    seen_scene_instance_ids.add(scene_instance_id)
    if record.get("cleanup_safety_pass") is not True:
        raise CleanupUncertain(f"{phase} cleanup_safety_pass is not true")
    if record.get("orphan_process_count") != 0:
        raise CleanupUncertain(f"{phase} orphan_process_count is not zero")
    if record.get("scene_created") is True:
        if record.get("scene_cleanup_attempted") is not True or record.get("scene_cleanup_succeeded") is not True:
            raise CleanupUncertain(f"{phase} created scene was not certainly cleaned")
    elif record.get("scene_created") is not False:
        raise CleanupUncertain(f"{phase} scene_created must be explicit")
    return record


def _validate_task_physical_receipt(value: Mapping[str, Any], program_id: str) -> dict:
    receipt = dict(value)
    required = ("task_feasible", "physical_feasible", "planner_solvable", "failure_type", "evidence")
    missing = [key for key in required if key not in receipt]
    if missing:
        raise ValueError(f"task/physical receipt for {program_id} missing {missing}")
    if receipt["task_feasible"] not in (True, False) or receipt["physical_feasible"] not in (True, False):
        raise ValueError("task/physical feasibility values must be boolean")
    if receipt["planner_solvable"] is not None:
        raise ValueError("task/physical audit may not decide planner solvability")
    if not isinstance(receipt["evidence"], Mapping):
        raise ValueError("task/physical feasibility evidence must be structured")
    receipt["program_id"] = program_id
    receipt["status"] = "passed" if receipt["task_feasible"] and receipt["physical_feasible"] else "failed"
    return receipt


def _validate_planner_receipt(value: Mapping[str, Any], program_id: str) -> dict:
    receipt = dict(value)
    required = ("planner_solvable", "failure_type", "evidence", "planner_query_count")
    missing = [key for key in required if key not in receipt]
    if missing:
        raise ValueError(f"planner receipt for {program_id} missing {missing}")
    if receipt["planner_solvable"] not in (True, False):
        raise ValueError("planner_solvable must be boolean")
    if not isinstance(receipt["evidence"], Mapping):
        raise ValueError("planner evidence must be structured")
    if not isinstance(receipt["planner_query_count"], int) or receipt["planner_query_count"] < 0:
        raise ValueError("planner_query_count must be a nonnegative integer")
    receipt["program_id"] = program_id
    if receipt["planner_solvable"] and not isinstance(receipt.get("execution_spec"), Mapping):
        raise ValueError("a solvable planner receipt must freeze an execution_spec")
    receipt["status"] = "passed" if receipt["planner_solvable"] else "failed"
    return receipt


def validate_executed_prefix_evidence(value: Mapping[str, Any]) -> dict:
    receipt = dict(value)
    required = (
        "executed_prefix_action_sha256",
        "executed_prefix_step_count",
        "executed_prefix_start_state_sha256",
        "executed_prefix_end_state_sha256",
        "executed_prefix_start_anchor",
        "executed_prefix_end_anchor",
        "canonical_prefix_end_step",
        "first_post_prefix_divergence_step",
        "neutral_confirmation_step_count",
        "neutral_confirmation_minimum_required_steps",
    )
    missing = [key for key in required if key not in receipt]
    if missing:
        raise ValueError(f"executed-prefix evidence missing {missing}")
    if not isinstance(receipt["executed_prefix_action_sha256"], str):
        raise ValueError("executed prefix requires an action hash")
    step_count = receipt["executed_prefix_step_count"]
    end_step = receipt["canonical_prefix_end_step"]
    divergence = receipt["first_post_prefix_divergence_step"]
    if not all(isinstance(item, int) and item >= 0 for item in (step_count, end_step, divergence)):
        raise ValueError("executed prefix step fields must be nonnegative integers")
    if step_count != end_step or divergence < end_step:
        raise ValueError("executed prefix boundary is inconsistent")
    neutral_steps = receipt["neutral_confirmation_step_count"]
    minimum_steps = receipt["neutral_confirmation_minimum_required_steps"]
    if neutral_steps != minimum_steps:
        raise ValueError("extra branch-neutral hold frames may not extend formal P")
    return receipt


def finalize_three_branch_root_v1_1(
    branch_receipts: Sequence[Mapping[str, Any]],
    *,
    reference_current_sha256: str,
    root_cleanup_pass: bool,
) -> dict:
    if len(branch_receipts) != 3:
        return {"accepted": False, "reason": "root_requires_exactly_three_branch_receipts"}
    program_ids = [item.get("program_id") for item in branch_receipts]
    if len(set(program_ids)) != 3 or None in program_ids:
        return {"accepted": False, "reason": "branch_program_ids_must_be_three_unique_values"}

    prefix_items = []
    prefix_error = None
    try:
        prefix_items = [validate_executed_prefix_evidence(item.get("executed_prefix", {})) for item in branch_receipts]
    except BaseException as exc:
        prefix_error = str(exc)
    action_hashes = {item.get("executed_prefix_action_sha256") for item in prefix_items}
    step_counts = {item.get("executed_prefix_step_count") for item in prefix_items}
    start_hashes = {item.get("executed_prefix_start_state_sha256") for item in prefix_items}
    prefix_anchor_checks = []
    if prefix_error is None:
        reference_start_anchor = prefix_items[0]["executed_prefix_start_anchor"]
        reference_end_anchor = prefix_items[0]["executed_prefix_end_anchor"]
        for item in prefix_items:
            prefix_anchor_checks.append(
                {
                    "start": compare_anchors(reference_start_anchor, item["executed_prefix_start_anchor"]),
                    "end": compare_anchors(reference_end_anchor, item["executed_prefix_end_anchor"]),
                }
            )

    direct_current_checks = [
        item.get("branch_current", {}).get("aggregate_sha256") == reference_current_sha256
        and item.get("reference_current_sha256") == reference_current_sha256
        for item in branch_receipts
    ]
    anchor_checks = [item.get("anchor_equivalence", {}).get("equivalent") is True for item in branch_receipts]
    candidate_hashes = {item.get("candidate_universe_sha256") for item in branch_receipts}
    prefix_hashes = {item.get("prefix_sha256") for item in branch_receipts}
    checks = {
        "three_of_three_branches_accepted": all(item.get("status") == "accepted" for item in branch_receipts),
        "branch_current_matches_reference": all(direct_current_checks),
        "branch_anchor_equivalent": all(anchor_checks),
        "one_candidate_universe": None not in candidate_hashes and len(candidate_hashes) == 1,
        "one_prefix_spec": None not in prefix_hashes and len(prefix_hashes) == 1,
        "executed_prefix_schema": prefix_error is None,
        "one_executed_prefix_action_hash": prefix_error is None and None not in action_hashes and len(action_hashes) == 1,
        "one_executed_prefix_step_count": prefix_error is None and None not in step_counts and len(step_counts) == 1,
        "one_executed_prefix_start_state": prefix_error is None and None not in start_hashes and len(start_hashes) == 1,
        "prefix_start_anchor_equivalent": prefix_error is None and all(item["start"]["equivalent"] for item in prefix_anchor_checks),
        "prefix_end_state_equivalent": prefix_error is None and all(item["end"]["equivalent"] for item in prefix_anchor_checks),
        "root_cleanup": bool(root_cleanup_pass),
    }
    result = {"accepted": all(checks.values()), "checks": checks, "program_ids": program_ids, "prefix_anchor_checks": prefix_anchor_checks}
    if prefix_error is not None:
        result["executed_prefix_error"] = prefix_error
    return result


class RealSapienPilotRootOrchestratorV1_1:
    """Prepare/freeze once and execute three immutable fresh-scene branches."""

    stage0_authorized = False
    gpu_probe_authorized = False
    formal_data = False
    stage0_data = False

    def __init__(self, adapter: RealSapienPilotRootAdapterV1_1, implementation_version: str = IMPLEMENTATION_VERSION):
        self.adapter = adapter
        self.implementation_version = implementation_version
        self._seen_scene_instance_ids: set[str] = set()

    def _scene_call(
        self,
        *,
        receipt: MutableMapping[str, Any],
        planned_spec: Mapping[str, Any],
        planned_spec_sha256: str,
        phase: str,
        program: Mapping[str, Any] | None,
        program_sha256: str | None,
        callback: Callable[[Any, Mapping[str, Any] | None], Any],
    ) -> Any:
        planned_copy = _immutable_copy(planned_spec)
        program_copy = _immutable_copy(program) if program is not None else None
        context = self.adapter.scene(planned_copy, phase=phase, program=program_copy)
        handle: SceneHandleV1_1 | None = None
        result = None
        body_error: BaseException | None = None
        body_traceback = None
        try:
            with context as entered:
                if not isinstance(entered, SceneHandleV1_1):
                    raise TypeError("adapter scene context must yield SceneHandleV1_1")
                handle = entered
                try:
                    result = callback(handle.scene, program_copy)
                finally:
                    _require_unchanged(planned_copy, planned_spec_sha256, "planned_root_slot_spec")
                    if program_copy is not None and program_sha256 is not None:
                        _require_unchanged(program_copy, program_sha256, f"program:{program.get('program_id')}")
        except BaseException as exc:
            body_error = exc
            body_traceback = traceback.format_exc()

        expected_id = handle.scene_instance_id if handle is not None else None
        cleanup_raw = _cleanup_receipt_from(context, handle)
        try:
            cleanup = _validate_cleanup_receipt(
                cleanup_raw,
                expected_scene_instance_id=expected_id,
                seen_scene_instance_ids=self._seen_scene_instance_ids,
                phase=phase,
            )
            receipt["cleanup_records"].append({"phase": phase, **cleanup})
        except CleanupUncertain:
            if isinstance(cleanup_raw, Mapping):
                receipt["cleanup_records"].append({"phase": phase, **dict(cleanup_raw), "cleanup_validation_pass": False})
            raise

        if body_error is not None:
            setattr(body_error, "cmf_traceback", body_traceback)
            raise body_error
        return result

    def run_nonformal_root(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        realization_spec_by_program: Mapping[str, Mapping[str, Any]],
    ) -> dict:
        started = time.time()
        output_dir.mkdir(parents=True, exist_ok=False)
        planned_spec = _immutable_copy(planned_root_slot_spec)
        planned_spec_sha256 = hash_json(planned_spec)
        receipt: dict[str, Any] = {
            "schema_version": "cmf_real_sapien_root_orchestrator_v1_1",
            "design_version": DESIGN_VERSION,
            "implementation_version": self.implementation_version,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "gpu_probe_authorized": False,
            "status": "running",
            "planned_root_slot_spec_sha256": planned_spec_sha256,
            "freeze_call_count": 0,
            "reference_capture_order": [],
            "task_physical_feasibility_receipts": [],
            "planner_solvability_receipts": [],
            "planner_solvability_query_count_total": 0,
            "branch_receipts": [],
            "cleanup_records": [],
        }
        _write_json(output_dir / "planned_root_slot_spec.json", planned_spec)
        terminal = "failed_execution"
        try:
            def pristine_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                receipt["reference_capture_order"].append("capture_pristine_current")
                anchor = dict(self.adapter.capture_anchor(scene))
                receipt["reference_capture_order"].append("capture_pristine_anchor")
                programs_value = list(self.adapter.build_programs(scene))
                validate_exactly_three_programs(programs_value)
                programs_value = _immutable_copy(programs_value)
                receipt["reference_capture_order"].append("build_declarative_programs")
                trees_input = _immutable_copy(programs_value)
                trees_input_hash = hash_json(trees_input)
                trees_value = _immutable_copy(self.adapter.task_trees(trees_input))
                _require_unchanged(trees_input, trees_input_hash, "programs passed to task_trees")
                prefix_input = _immutable_copy(programs_value)
                prefix_input_hash = hash_json(prefix_input)
                prefix_value = _immutable_copy(self.adapter.canonical_prefix(prefix_input))
                _require_unchanged(prefix_input, prefix_input_hash, "programs passed to canonical_prefix")
                return current, anchor, programs_value, trees_value, prefix_value

            reference_current, reference_anchor, programs, trees, prefix = self._scene_call(
                receipt=receipt,
                planned_spec=planned_spec,
                planned_spec_sha256=planned_spec_sha256,
                phase="pristine",
                program=None,
                program_sha256=None,
                callback=pristine_callback,
            )
            if set(trees) != {"observable", "oracle"}:
                raise ValueError("task_trees must contain exactly observable and oracle")

            program_hashes = {program["program_id"]: hash_json(program) for program in programs}
            provisional = {
                "schema_version": "cmf_provisional_programs_v1_1",
                "planned_root_slot_spec_sha256": planned_spec_sha256,
                "programs": programs,
                "program_sha256": program_hashes,
            }
            provisional["provisional_programs_sha256"] = hash_json(provisional)
            provisional_trees = {
                "schema_version": "cmf_provisional_task_trees_v1_1",
                "observable": trees["observable"],
                "oracle": trees["oracle"],
            }
            provisional_trees["provisional_task_trees_sha256"] = hash_json(provisional_trees)
            provisional_prefix = {
                "schema_version": "cmf_provisional_prefix_v1_1",
                "prefix": prefix,
            }
            provisional_prefix["provisional_prefix_sha256"] = hash_json(provisional_prefix)
            _write_json(output_dir / "reference_current_hashes.json", reference_current)
            _write_json(output_dir / "reference_anchor.json", reference_anchor)
            _write_json(output_dir / "provisional_programs.json", provisional)
            _write_json(output_dir / "provisional_task_tree.json", provisional_trees)
            _write_json(output_dir / "provisional_prefix_spec.json", provisional_prefix)

            # Task/physical feasibility is audited before candidate freezing and
            # may not contain a planner-solvability decision.
            task_physical_all_pass = True
            for program in programs:
                program_id = program["program_id"]
                program_hash = program_hashes[program_id]

                def task_physical_callback(scene, candidate):
                    candidate_current = dict(self.adapter.capture_current(scene))
                    require_same_current(reference_current, candidate_current)
                    candidate_anchor = dict(self.adapter.capture_anchor(scene))
                    anchor_result = compare_anchors(reference_anchor, candidate_anchor)
                    if not anchor_result["equivalent"]:
                        raise ValueError(f"task/physical anchor mismatch: {anchor_result['failures']}")
                    value = self.adapter.audit_task_physical_feasibility(scene, candidate)
                    return _validate_task_physical_receipt(value, program_id)

                try:
                    item = self._scene_call(
                        receipt=receipt,
                        planned_spec=planned_spec,
                        planned_spec_sha256=planned_spec_sha256,
                        phase=f"task_physical_feasibility:{program_id}",
                        program=program,
                        program_sha256=program_hash,
                        callback=task_physical_callback,
                    )
                except CleanupUncertain:
                    raise
                except CandidateMutationError:
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
                task_physical_all_pass = task_physical_all_pass and item["status"] == "passed"
                receipt["task_physical_feasibility_receipts"].append(item)

            if not task_physical_all_pass:
                terminal = "failed_task_physical_feasibility"
                raise TaskPhysicalFeasibilityError("not all candidates passed task/physical feasibility")

            # Recheck every pristine artifact immediately before the one freeze.
            _require_unchanged(planned_spec, planned_spec_sha256, "planned_root_slot_spec")
            for program in programs:
                _require_unchanged(program, program_hashes[program["program_id"]], f"program:{program['program_id']}")
            frozen = freeze_candidate_universe(
                planned_root_slot_spec=planned_spec,
                programs=programs,
                observable_task_tree=trees["observable"],
                oracle_task_tree=trees["oracle"],
                implementation_version=self.implementation_version,
            )
            receipt["freeze_call_count"] += 1
            prefix = _immutable_copy(prefix)
            prefix["prefix_sha256"] = hash_json(prefix)
            _write_json(output_dir / "candidate_frozen_root_spec.json", frozen)
            _write_json(output_dir / "canonical_prefix.json", prefix)

            # Planner solvability is a separate, post-freeze, disposable-scene
            # audit.  It cannot change membership in the frozen universe.
            planner_all_pass = True
            planner_execution_specs = {}
            for program in programs:
                program_id = program["program_id"]
                program_hash = program_hashes[program_id]
                variants_input = _immutable_copy(program)
                variants_input_hash = hash_json(variants_input)
                variants = _immutable_copy(self.adapter.planner_audit_variants(variants_input))
                _require_unchanged(variants_input, variants_input_hash, f"program passed to planner_audit_variants:{program_id}")
                if not isinstance(variants, list) or not variants:
                    raise ValueError(f"planner variants missing for {program_id}")
                variant_ids = [item.get("variant_id") for item in variants if isinstance(item, Mapping)]
                if len(variant_ids) != len(variants) or None in variant_ids or len(set(variant_ids)) != len(variant_ids):
                    raise ValueError(f"planner variants must have unique IDs for {program_id}")
                selected_item = None
                for variant in variants:
                    variant_hash = hash_json(variant)
                    variant_id = variant["variant_id"]

                    def planner_callback(scene, candidate, variant_value=variant, expected_variant_hash=variant_hash):
                        candidate_current = dict(self.adapter.capture_current(scene))
                        require_same_current(reference_current, candidate_current)
                        candidate_anchor = dict(self.adapter.capture_anchor(scene))
                        anchor_result = compare_anchors(reference_anchor, candidate_anchor)
                        if not anchor_result["equivalent"]:
                            raise ValueError(f"planner anchor mismatch: {anchor_result['failures']}")
                        variant_copy = _immutable_copy(variant_value)
                        value = self.adapter.audit_planner_solvability(scene, candidate, variant_copy)
                        _require_unchanged(variant_copy, expected_variant_hash, f"planner_variant:{program_id}:{variant_id}")
                        item_value = _validate_planner_receipt(value, program_id)
                        item_value["variant_id"] = variant_id
                        item_value["scene_current_sha256"] = candidate_current["aggregate_sha256"]
                        item_value["scene_anchor_equivalence"] = anchor_result
                        return item_value

                    try:
                        item = self._scene_call(
                            receipt=receipt,
                            planned_spec=planned_spec,
                            planned_spec_sha256=planned_spec_sha256,
                            phase=f"planner_solvability:{program_id}:{variant_id}",
                            program=program,
                            program_sha256=program_hash,
                            callback=planner_callback,
                        )
                    except CleanupUncertain:
                        raise
                    except CandidateMutationError:
                        raise
                    except BaseException as exc:
                        item = {
                            "program_id": program_id,
                            "variant_id": variant_id,
                            "status": "failed",
                            "planner_solvable": False,
                            "failure_type": type(exc).__name__,
                            "evidence": {"error": str(exc)},
                            "planner_query_count": 0,
                        }
                    receipt["planner_solvability_receipts"].append(item)
                    receipt["planner_solvability_query_count_total"] += int(item.get("planner_query_count", 0))
                    if planned_spec.get("family") == "F2" and receipt["planner_solvability_query_count_total"] > 16:
                        terminal = "failed_budget_exhausted"
                        raise PlannerSolvabilityError("F2 planner query total exceeded 16")
                    if item["status"] == "passed":
                        selected_item = item
                        break
                planner_all_pass = planner_all_pass and selected_item is not None
                if selected_item is not None:
                    planner_execution_specs[program_id] = _immutable_copy(selected_item["execution_spec"])

            if not planner_all_pass:
                terminal = "failed_planner"
                raise PlannerSolvabilityError("not all frozen candidates passed planner solvability")

            planner_execution_artifact = {
                "schema_version": "cmf_planner_frozen_execution_specs_v1_1",
                "candidate_universe_sha256": frozen["candidate_universe_sha256"],
                "execution_specs": planner_execution_specs,
            }
            planner_execution_artifact["planner_execution_specs_sha256"] = hash_json(planner_execution_artifact)
            _write_json(output_dir / "planner_frozen_execution_specs.json", planner_execution_artifact)

            expected_program_ids = {program["program_id"] for program in programs}
            if set(realization_spec_by_program) != expected_program_ids:
                raise ValueError("realization specs must cover exactly the frozen three programs")

            for program in programs:
                program_id = program["program_id"]
                program_hash = program_hashes[program_id]
                branch_dir = output_dir / "branches" / program_id
                branch_dir.mkdir(parents=True, exist_ok=False)
                branch: dict[str, Any] = {
                    "schema_version": "cmf_root_branch_receipt_v1_1",
                    "program_id": program_id,
                    "formal_data": False,
                    "stage0_data": False,
                    "status": "failed_execution",
                    "partial_output_status": "none",
                    "reference_current_sha256": reference_current.get("aggregate_sha256"),
                    "candidate_universe_sha256": frozen["candidate_universe_sha256"],
                    "prefix_sha256": prefix["prefix_sha256"],
                }

                def rollout_callback(scene, candidate):
                    branch_current = dict(self.adapter.capture_current(scene))
                    require_same_current(reference_current, branch_current)
                    branch_anchor = dict(self.adapter.capture_anchor(scene))
                    anchor_result = compare_anchors(reference_anchor, branch_anchor)
                    if not anchor_result["equivalent"]:
                        raise ValueError(f"rollout anchor mismatch: {anchor_result['failures']}")
                    realization_spec = _immutable_copy(realization_spec_by_program[program_id])
                    realization_spec["planner_execution_spec"] = _immutable_copy(planner_execution_specs[program_id])
                    rollout_result = dict(
                        self.adapter.rollout(
                            scene,
                            candidate,
                            realization_spec,
                        )
                    )
                    executed_prefix = validate_executed_prefix_evidence(rollout_result.get("executed_prefix", {}))
                    raw_manifest = write_raw_attempt(
                        branch_dir / "raw",
                        rollout_result["streams"],
                        rollout_result["audit_streams"],
                        rollout_result["provenance"],
                    )
                    branch.update(
                        {
                            "raw_manifest": raw_manifest,
                            "rollout_planner_query_count": len(raw_manifest.get("provenance", {}).get("planner_queries", [])),
                            "partial_output_status": "raw_saved_verifier_pending",
                            "branch_current": branch_current,
                            "anchor_equivalence": anchor_result,
                            "executed_prefix": executed_prefix,
                        }
                    )
                    _write_json(branch_dir / "receipt.json", branch)
                    verifier = dict(self.adapter.verify(scene, candidate, rollout_result))
                    branch["verifier"] = verifier
                    branch["partial_output_status"] = "raw_and_verifier_complete"
                    branch["status"] = "accepted" if verifier.get("pass") is True else "failed_verifier"
                    return None

                try:
                    self._scene_call(
                        receipt=receipt,
                        planned_spec=planned_spec,
                        planned_spec_sha256=planned_spec_sha256,
                        phase=f"rollout:{program_id}",
                        program=program,
                        program_sha256=program_hash,
                        callback=rollout_callback,
                    )
                except CleanupUncertain as exc:
                    branch.update(
                        {
                            "status": "failed_cleanup_uncertain",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    )
                    receipt["branch_receipts"].append(branch)
                    _write_json(branch_dir / "receipt.json", branch)
                    terminal = "failed_cleanup_uncertain"
                    raise
                except CandidateMutationError as exc:
                    branch.update(
                        {
                            "status": "failed_candidate_mutation",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                    )
                    receipt["branch_receipts"].append(branch)
                    _write_json(branch_dir / "receipt.json", branch)
                    terminal = "failed_candidate_mutation"
                    raise
                except BaseException as exc:
                    branch.update(
                        {
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                        }
                    )
                    if branch.get("raw_manifest") is not None:
                        branch["status"] = "failed_verifier"
                    # Non-cleanup branch failures are retained and later
                    # preregistered branches still run.
                receipt["branch_receipts"].append(branch)
                _write_json(branch_dir / "receipt.json", branch)

            root_cleanup_pass = all(
                item.get("cleanup_safety_pass") is True and item.get("orphan_process_count") == 0
                for item in receipt["cleanup_records"]
            )
            finalization = finalize_three_branch_root_v1_1(
                receipt["branch_receipts"],
                reference_current_sha256=reference_current["aggregate_sha256"],
                root_cleanup_pass=root_cleanup_pass,
            )
            receipt["root_finalization"] = finalization
            terminal = "accepted" if finalization["accepted"] else "failed_verifier"
        except CleanupUncertain as exc:
            terminal = "failed_cleanup_uncertain"
            receipt.setdefault("error_type", type(exc).__name__)
            receipt.setdefault("error", str(exc))
            receipt.setdefault("traceback", traceback.format_exc())
        except CandidateMutationError as exc:
            terminal = "failed_candidate_mutation"
            receipt.setdefault("error_type", type(exc).__name__)
            receipt.setdefault("error", str(exc))
            receipt.setdefault("traceback", traceback.format_exc())
        except BaseException as exc:
            receipt.setdefault("error_type", type(exc).__name__)
            receipt.setdefault("error", str(exc))
            receipt.setdefault("traceback", traceback.format_exc())
        receipt["status"] = terminal
        receipt["elapsed_seconds"] = time.time() - started
        _write_json(output_dir / "root_receipt.json", receipt)
        return receipt
