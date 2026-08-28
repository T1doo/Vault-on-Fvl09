"""Single-program repair orchestration for F2/F3/F4 runtime-v3_1 probes."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .anchor import compare_anchors
from .current_hasher import hash_json, require_same_current
from .raw_writer import write_raw_attempt
from .root_orchestrator_v1_1 import CleanupUncertain, SceneHandleV1_1


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


class FamilyRepairOrchestratorV1_1:
    """Fail-closed repair runner; it never accepts a formal/root trajectory."""

    def __init__(self, adapter):
        if adapter.family not in ("F2", "F3", "F4"):
            raise ValueError("single repair orchestrator is restricted to F2/F3/F4")
        self.adapter = adapter
        self.seen_scene_ids = set()

    def _run_scene(self, *, receipt, planned, planned_hash, phase, program, callback):
        planned_copy = _copy(planned)
        program_copy = _copy(program)
        program_hash = hash_json(program)
        context = self.adapter.scene(planned_copy, phase=phase, program=program_copy)
        handle = None
        result = None
        body_error = None
        try:
            with context as handle:
                if not isinstance(handle, SceneHandleV1_1):
                    raise TypeError("adapter did not yield SceneHandleV1_1")
                try:
                    result = callback(handle.scene, program_copy)
                finally:
                    if hash_json(planned_copy) != planned_hash or hash_json(program_copy) != program_hash:
                        raise RuntimeError("failed_candidate_mutation")
        except BaseException as exc:
            body_error = exc
        cleanup = handle.cleanup_receipt if handle is not None else getattr(context, "cleanup_receipt", None)
        if not isinstance(cleanup, Mapping):
            raise CleanupUncertain(f"{phase}: missing scene-bound cleanup receipt")
        cleanup = dict(cleanup)
        scene_id = cleanup.get("scene_instance_id")
        if not isinstance(scene_id, str) or scene_id in self.seen_scene_ids:
            raise CleanupUncertain(f"{phase}: missing or reused scene_instance_id")
        self.seen_scene_ids.add(scene_id)
        receipt["cleanup_records"].append({"phase": phase, **cleanup})
        if cleanup.get("cleanup_safety_pass") is not True or cleanup.get("orphan_process_count") != 0:
            raise CleanupUncertain(f"{phase}: cleanup/orphan uncertainty")
        if body_error is not None:
            raise body_error
        return result

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        program: Mapping[str, Any],
        repair_mode: str = "diagnosis",
        correction_spec: Mapping[str, Any] | None = None,
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _copy(planned_root_slot_spec)
        program = _copy(program)
        planned_hash = hash_json(planned)
        receipt = {
            "schema_version": "cmf_family_repair_orchestrator_v1_1",
            "implementation_version": "controlled_multi_future_runtime_v3_1",
            "family": self.adapter.family,
            "program_id": program["program_id"],
            "repair_mode": repair_mode,
            "correction_spec": _copy(correction_spec) if correction_spec is not None else None,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "task_physical_receipt": None,
            "planner_variant_receipts": [],
            "planner_solvability_query_count_total": 0,
            "rollout_planner_query_count": None,
            "raw_manifest": None,
            "verifier": None,
            "partial_output_status": "none",
            "cleanup_records": [],
        }
        _write(output_dir / "planned_root_slot_spec.json", planned)
        variants_input = _copy(program)
        variants = _copy(self.adapter.planner_audit_variants(variants_input))
        preflight_error = None
        if correction_spec is not None:
            try:
                if self.adapter.family != "F3" or repair_mode != "deterministic_correction":
                    raise ValueError("correction_spec is allowed only for F3 deterministic correction")
                correction_payload = _copy(correction_spec)
                sealed = dict(correction_payload)
                expected_hash = sealed.pop("correction_spec_sha256", None)
                if expected_hash != hash_json(sealed):
                    raise ValueError("F3 correction spec hash mismatch")
                if correction_payload.get("maximum_correction_attempt_count") != 1:
                    raise ValueError("F3 correction spec must enforce one attempt")
                for variant in variants:
                    variant["correction_spec"] = _copy(correction_payload)
            except BaseException as exc:
                preflight_error = exc
        variants_input_mutated = hash_json(variants_input) != hash_json(program)
        _write(output_dir / "provisional_program.json", {"program": program, "program_sha256": hash_json(program)})
        _write(output_dir / "provisional_planner_variants.json", {"variants": variants, "variants_sha256": hash_json(variants)})
        terminal = "failed_execution"
        try:
            if preflight_error is not None:
                raise preflight_error
            if variants_input_mutated:
                raise RuntimeError("failed_candidate_mutation")
            reference_current, reference_anchor = self._run_scene(
                receipt=receipt,
                planned=planned,
                planned_hash=planned_hash,
                phase="repair_pristine",
                program=program,
                callback=lambda scene, _: (self.adapter.capture_current(scene), self.adapter.capture_anchor(scene)),
            )
            _write(output_dir / "reference_current.json", reference_current)
            _write(output_dir / "reference_anchor.json", reference_anchor)
            receipt["reference_current_sha256"] = reference_current.get("aggregate_sha256")
            receipt["reference_anchor_sha256"] = reference_anchor.get("anchor_sha256")

            def task_callback(scene, candidate):
                require_same_current(reference_current, self.adapter.capture_current(scene))
                anchor = compare_anchors(reference_anchor, self.adapter.capture_anchor(scene))
                if not anchor["equivalent"]:
                    raise ValueError(f"task/physical anchor mismatch: {anchor['failures']}")
                value = dict(self.adapter.audit_task_physical_feasibility(scene, candidate))
                if value.get("planner_solvable") is not None:
                    raise ValueError("task/physical receipt may not decide planner solvability")
                return value

            task_receipt = self._run_scene(
                receipt=receipt,
                planned=planned,
                planned_hash=planned_hash,
                phase="repair_task_physical",
                program=program,
                callback=task_callback,
            )
            receipt["task_physical_receipt"] = task_receipt
            if task_receipt.get("task_feasible") is not True or task_receipt.get("physical_feasible") is not True:
                terminal = "failed_task_physical_feasibility"
                raise RuntimeError("repair task/physical feasibility failed")

            selected = None
            for variant in variants:
                variant_hash = hash_json(variant)

                def planner_callback(scene, candidate, variant_value=variant):
                    require_same_current(reference_current, self.adapter.capture_current(scene))
                    anchor = compare_anchors(reference_anchor, self.adapter.capture_anchor(scene))
                    if not anchor["equivalent"]:
                        raise ValueError(f"planner anchor mismatch: {anchor['failures']}")
                    variant_copy = _copy(variant_value)
                    value = dict(self.adapter.audit_planner_solvability(scene, candidate, variant_copy))
                    if hash_json(variant_copy) != variant_hash:
                        raise RuntimeError("failed_candidate_mutation")
                    value["variant_id"] = variant_value["variant_id"]
                    value["scene_current_sha256"] = reference_current["aggregate_sha256"]
                    value["scene_anchor_equivalence"] = anchor
                    return value

                item = self._run_scene(
                    receipt=receipt,
                    planned=planned,
                    planned_hash=planned_hash,
                    phase=f"repair_planner:{variant['variant_id']}",
                    program=program,
                    callback=planner_callback,
                )
                receipt["planner_variant_receipts"].append(item)
                receipt["planner_solvability_query_count_total"] += int(item.get("planner_query_count", 0))
                if self.adapter.family == "F2" and receipt["planner_solvability_query_count_total"] > 16:
                    terminal = "failed_budget_exhausted"
                    raise RuntimeError("F2 planner query total exceeded 16")
                if item.get("planner_solvable") is True:
                    selected = item
                    break
            if selected is None:
                terminal = "failed_planner"
                if self.adapter.family == "F2":
                    receipt["next_gate"] = "f2_stand_layout_impact_review_v5"
                elif self.adapter.family == "F4":
                    receipt["next_gate"] = "f4_tray_layout_impact_review_v4"
                raise RuntimeError("all preregistered repair planner variants failed")
            _write(output_dir / "selected_execution_spec.json", selected["execution_spec"])

            def rollout_callback(scene, candidate):
                current = self.adapter.capture_current(scene)
                require_same_current(reference_current, current)
                anchor = compare_anchors(reference_anchor, self.adapter.capture_anchor(scene))
                if not anchor["equivalent"]:
                    raise ValueError(f"rollout anchor mismatch: {anchor['failures']}")
                rollout = dict(
                    self.adapter.rollout(
                        scene,
                        candidate,
                        {
                            "realization": "repair_probe",
                            "repair_mode": repair_mode,
                            "formal_data": False,
                            "stage0_data": False,
                            "planner_execution_spec": _copy(selected["execution_spec"]),
                        },
                    )
                )
                if hasattr(scene, "save_trace"):
                    trace_path = output_dir / "trace_source.npz"
                    trace_info = dict(scene.save_trace(trace_path))
                    trace_sha256 = hashlib.sha256(trace_path.read_bytes()).hexdigest()
                    rollout.setdefault("provenance", {})["trace_source_sha256"] = trace_sha256
                    rollout["provenance"]["trace_source_relative_path"] = "../trace_source.npz"
                    receipt["trace_source"] = {**trace_info, "sha256": trace_sha256}
                raw_manifest = write_raw_attempt(output_dir / "raw", rollout["streams"], rollout["audit_streams"], rollout["provenance"])
                receipt["raw_manifest"] = raw_manifest
                receipt["rollout_planner_query_count"] = len(raw_manifest.get("provenance", {}).get("planner_queries", []))
                receipt["partial_output_status"] = "raw_saved_verifier_pending"
                _write(output_dir / "receipt.json", receipt)
                verifier = dict(self.adapter.verify(scene, candidate, rollout))
                receipt["verifier"] = verifier
                receipt["semantic_verifier"] = rollout["semantic_verifier"]
                receipt["executed_prefix"] = rollout["executed_prefix"]
                receipt["partial_output_status"] = "raw_and_verifier_complete"
                return rollout

            rollout = self._run_scene(
                receipt=receipt,
                planned=planned,
                planned_hash=planned_hash,
                phase="repair_rollout",
                program=program,
                callback=rollout_callback,
            )
            semantic = rollout["semantic_verifier"]
            if self.adapter.family == "F2":
                repair_pass = semantic.get("pass") is True
                terminal = "passed_nonformal_repair_probe" if repair_pass else "failed_verifier"
            elif self.adapter.family == "F3":
                repair_pass = semantic.get("repair_probe_pass") is True
                terminal = "passed_nonformal_repair_probe_full_program_incomplete" if repair_pass else "failed_verifier"
            else:
                repair_pass = semantic.get("common_x_repair_probe_pass") is True
                terminal = "passed_nonformal_repair_probe_full_program_incomplete" if repair_pass else "failed_verifier"
            receipt["repair_probe_pass"] = repair_pass
            receipt["full_family_program_complete"] = self.adapter.family == "F2" and repair_pass
        except CleanupUncertain as exc:
            terminal = "failed_cleanup_uncertain"
            receipt.update({"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        except BaseException as exc:
            receipt.setdefault("error_type", type(exc).__name__)
            receipt.setdefault("error", str(exc))
            receipt.setdefault("traceback", traceback.format_exc())
        receipt["status"] = terminal
        receipt["elapsed_seconds"] = time.time() - started
        _write(output_dir / "receipt.json", receipt)
        return receipt
