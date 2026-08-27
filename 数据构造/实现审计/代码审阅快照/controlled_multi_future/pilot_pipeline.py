"""Minimal fail-closed Stage-0-shaped pipeline, disabled for formal collection."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .anchor import compare_anchors
from .attempt_state_machine import AttemptStateMachine
from .candidate_freezer import freeze_candidate_universe
from .current_hasher import hash_json, require_same_current
from .finalizer import finalize_nonformal_integration
from .raw_writer import write_raw_attempt
from .receipts import initial_attempt_receipt, write_receipt


class CurrentHashMismatch(RuntimeError):
    pass


class AnchorMismatch(RuntimeError):
    pass


class FeasibilityFailure(RuntimeError):
    pass


class VerifierFailure(RuntimeError):
    pass


class PilotPipelineAdapter(ABC):
    """Runtime adapter contract. ``scene`` must return a cleanup-safe context manager."""

    @abstractmethod
    def scene(self, planned_root_slot_spec, *, phase, program=None):
        raise NotImplementedError

    @abstractmethod
    def build_programs(self, scene):
        raise NotImplementedError

    @abstractmethod
    def audit_feasibility(self, scene, program):
        raise NotImplementedError

    @abstractmethod
    def capture_current(self, scene):
        raise NotImplementedError

    @abstractmethod
    def capture_anchor(self, scene):
        raise NotImplementedError

    @abstractmethod
    def task_trees(self, programs):
        raise NotImplementedError

    @abstractmethod
    def canonical_prefix(self, programs):
        raise NotImplementedError

    @abstractmethod
    def rollout(self, scene, program, realization_spec):
        raise NotImplementedError

    @abstractmethod
    def verify(self, scene, program, rollout_result):
        raise NotImplementedError

    @abstractmethod
    def cleanup_audit(self):
        raise NotImplementedError


def _write_json(path: Path, value: Mapping[str, Any]):
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class PilotAttemptPipeline:
    """One branch/realization attempt with fresh reconstruction and immutable evidence.

    This implementation intentionally emits ``formal_data=false`` and
    ``stage0_data=false``. Enabling formal collection requires a separately
    reviewed authorization gate and is not exposed by this class.
    """

    stage0_authorized = False

    def __init__(self, adapter: PilotPipelineAdapter, implementation_version: str):
        self.adapter = adapter
        self.implementation_version = implementation_version

    def run_nonformal_attempt(self, *, output_dir: Path, planned_root_slot_spec: Mapping[str, Any], program_id: str, realization_spec: Mapping[str, Any]):
        started = time.time()
        receipt = initial_attempt_receipt(family=str(planned_root_slot_spec["family"]), namespace=output_dir.name, purpose="implementation_audit")
        receipt["planned_root_slot_spec"] = dict(planned_root_slot_spec)
        receipt["program_id"] = program_id
        receipt["realization_spec"] = dict(realization_spec)
        machine = AttemptStateMachine()
        terminal = "aborted_with_reason"
        output_dir.mkdir(parents=True, exist_ok=False)
        _write_json(output_dir / "planned_root_slot_spec.json", planned_root_slot_spec)
        try:
            with self.adapter.scene(planned_root_slot_spec, phase="provisional") as provisional:
                machine.transition("scene_built")
                programs = list(self.adapter.build_programs(provisional))
                for program in programs:
                    receipt["attempt_counts"]["feasibility_query_count"] += 1
                    if self.adapter.audit_feasibility(provisional, program) is not True:
                        raise FeasibilityFailure(f"physical/planner feasibility failed for {program.get('program_id')}")
                trees = self.adapter.task_trees(programs)
                frozen = freeze_candidate_universe(
                    planned_root_slot_spec=planned_root_slot_spec,
                    programs=programs,
                    observable_task_tree=trees["observable"],
                    oracle_task_tree=trees["oracle"],
                    implementation_version=self.implementation_version,
                )
                prefix = dict(self.adapter.canonical_prefix(programs))
                prefix["prefix_sha256"] = hash_json(prefix)
                reference_current = self.adapter.capture_current(provisional)
                reference_anchor = self.adapter.capture_anchor(provisional)
            machine.transition("candidates_frozen")
            _write_json(output_dir / "candidate_frozen_root_spec.json", frozen)
            _write_json(output_dir / "canonical_prefix.json", prefix)
            _write_json(output_dir / "reference_current_hashes.json", reference_current)
            _write_json(output_dir / "reference_anchor.json", reference_anchor)
            selected = next((program for program in programs if program.get("program_id") == program_id), None)
            if selected is None:
                raise ValueError(f"program_id not in frozen candidate universe: {program_id}")
            with self.adapter.scene(planned_root_slot_spec, phase="fresh_reconstruction", program=selected) as fresh:
                candidate_current = self.adapter.capture_current(fresh)
                try:
                    require_same_current(reference_current, candidate_current)
                except ValueError as exc:
                    raise CurrentHashMismatch(str(exc)) from exc
                candidate_anchor = self.adapter.capture_anchor(fresh)
                anchor_result = compare_anchors(reference_anchor, candidate_anchor)
                if not anchor_result["equivalent"]:
                    raise AnchorMismatch(str(anchor_result["failures"]))
                machine.transition("anchor_reconstructed")
                machine.transition("rolling_out")
                receipt["attempt_counts"]["execution_attempt_count"] += 1
                rollout_result = self.adapter.rollout(fresh, selected, realization_spec)
                raw_manifest = write_raw_attempt(output_dir / "raw", rollout_result["streams"], rollout_result["audit_streams"], rollout_result["provenance"])
                machine.transition("raw_saved")
                verifier = dict(self.adapter.verify(fresh, selected, rollout_result))
                if verifier.get("pass") is not True:
                    raise VerifierFailure(str(verifier))
                machine.transition("verified")
            cleanup = dict(self.adapter.cleanup_audit())
            receipt.update({
                "scene_created": True,
                "scene_cleanup_attempted": True,
                "scene_cleanup_succeeded": cleanup.get("scene_cleanup_succeeded") is True,
                "cleanup_error": cleanup.get("cleanup_error"),
                "orphan_process_count": int(cleanup.get("orphan_process_count", -1)),
                "gpu_postcheck": cleanup.get("gpu_postcheck", "not_applicable_cpu_dry_run"),
                "partial_output_status": "raw_and_verifier_complete",
                "current_hashes": {"reference": reference_current, "fresh": candidate_current},
                "anchor_equivalence": anchor_result,
                "candidate_universe_sha256": frozen["candidate_universe_sha256"],
                "prefix_sha256": prefix["prefix_sha256"],
                "raw_manifest": raw_manifest,
                "verifier": verifier,
            })
            checks = {
                "same_current_pass": True,
                "anchor_equivalence_pass": True,
                "candidate_freeze_pass": True,
                "prefix_freeze_pass": True,
                "raw_contract_pass": True,
                "family_verifier_pass": True,
                "cleanup_pass": cleanup.get("scene_cleanup_succeeded") is True,
                "orphan_audit_pass": cleanup.get("orphan_process_count") == 0,
            }
            finalization = finalize_nonformal_integration(checks)
            receipt["finalization"] = finalization
            if not finalization["accepted"]:
                terminal = "failed_cleanup" if not checks["cleanup_pass"] or not checks["orphan_audit_pass"] else "failed_verifier"
            else:
                machine.transition("accepted")
                terminal = "accepted"
        except CurrentHashMismatch as exc:
            terminal = "failed_current_hash"
            receipt["error"] = str(exc)
        except AnchorMismatch as exc:
            terminal = "failed_anchor_equivalence"
            receipt["error"] = str(exc)
        except FeasibilityFailure as exc:
            terminal = "failed_planner"
            receipt["error"] = str(exc)
        except VerifierFailure as exc:
            terminal = "failed_verifier"
            receipt["error"] = str(exc)
        except BaseException as exc:
            terminal = "failed_execution"
            receipt.update({"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        try:
            cleanup = dict(self.adapter.cleanup_audit())
            receipt.update({
                "scene_created": cleanup.get("scene_created", receipt.get("scene_created", False)),
                "scene_cleanup_attempted": cleanup.get("scene_cleanup_attempted", True),
                "scene_cleanup_succeeded": cleanup.get("scene_cleanup_succeeded") is True,
                "cleanup_error": cleanup.get("cleanup_error"),
                "orphan_process_count": int(cleanup.get("orphan_process_count", -1)),
                "gpu_postcheck": cleanup.get("gpu_postcheck", receipt.get("gpu_postcheck")),
            })
            if receipt["scene_created"] and (not receipt["scene_cleanup_succeeded"] or receipt["orphan_process_count"] != 0):
                terminal = "failed_cleanup_uncertain"
        except BaseException as cleanup_exc:
            receipt.update({"scene_cleanup_attempted": True, "scene_cleanup_succeeded": False, "cleanup_error": {"type": type(cleanup_exc).__name__, "message": str(cleanup_exc)}})
            terminal = "failed_cleanup_uncertain"
        receipt["status"] = terminal
        receipt["elapsed_seconds"] = time.time() - started
        write_receipt(output_dir / "receipt.json", receipt)
        return receipt
