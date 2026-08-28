"""Fail-closed root-level orchestration contract for real SAPIEN pilots.

The implementation is intentionally nonformal and Stage-0-disabled.  A real
adapter must be supplied later; CPU tests use a deterministic synthetic adapter
to verify ordering, freeze-once behavior, fresh-scene reconstruction, and the
3/3 root finalizer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping, Sequence

from .anchor import compare_anchors
from .candidate_freezer import freeze_candidate_universe
from .current_hasher import hash_json, require_same_current
from .raw_writer import write_raw_attempt
from .schemas import validate_exactly_three_programs


class RealSapienPilotRootAdapterV1(ABC):
    """Adapter boundary; every returned scene must be a cleanup-safe context."""

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
    def audit_feasibility(self, disposable_scene, program):
        raise NotImplementedError

    @abstractmethod
    def rollout(self, fresh_scene, program, realization_spec):
        raise NotImplementedError

    @abstractmethod
    def verify(self, fresh_scene, program, rollout_result):
        raise NotImplementedError

    @abstractmethod
    def last_scene_cleanup_audit(self):
        raise NotImplementedError


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_three_branch_root(branch_receipts: Sequence[Mapping[str, Any]], *, root_cleanup_pass: bool) -> dict:
    if len(branch_receipts) != 3:
        return {"accepted": False, "reason": "root_requires_exactly_three_branch_receipts"}
    program_ids = [item.get("program_id") for item in branch_receipts]
    if len(set(program_ids)) != 3 or None in program_ids:
        return {"accepted": False, "reason": "branch_program_ids_must_be_three_unique_values"}
    accepted = [item.get("status") == "accepted" for item in branch_receipts]
    current_hashes = {item.get("reference_current_sha256") for item in branch_receipts}
    candidate_hashes = {item.get("candidate_universe_sha256") for item in branch_receipts}
    prefix_hashes = {item.get("prefix_sha256") for item in branch_receipts}
    checks = {
        "three_of_three_branches_accepted": all(accepted),
        "one_reference_current": None not in current_hashes and len(current_hashes) == 1,
        "one_candidate_universe": None not in candidate_hashes and len(candidate_hashes) == 1,
        "one_prefix": None not in prefix_hashes and len(prefix_hashes) == 1,
        "root_cleanup": bool(root_cleanup_pass),
    }
    return {"accepted": all(checks.values()), "checks": checks, "program_ids": program_ids}


class RealSapienPilotRootOrchestratorV1:
    """Prepare/freeze one root once, then run three fresh branch scenes."""

    stage0_authorized = False
    formal_data = False
    stage0_data = False

    def __init__(self, adapter: RealSapienPilotRootAdapterV1, implementation_version: str):
        self.adapter = adapter
        self.implementation_version = implementation_version

    @staticmethod
    def _require_cleanup(cleanup: Mapping[str, Any], phase: str) -> None:
        if cleanup.get("scene_cleanup_succeeded") is not True or cleanup.get("orphan_process_count") != 0:
            raise RuntimeError(f"{phase} cleanup/orphan audit failed: {dict(cleanup)}")

    def run_nonformal_root(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        realization_spec_by_program: Mapping[str, Mapping[str, Any]],
    ) -> dict:
        started = time.time()
        output_dir.mkdir(parents=True, exist_ok=False)
        receipt = {
            "schema_version": "cmf_real_sapien_root_orchestrator_v1",
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": self.implementation_version,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "freeze_call_count": 0,
            "reference_capture_order": [],
            "feasibility_receipts": [],
            "branch_receipts": [],
            "cleanup_records": [],
        }
        _write_json(output_dir / "planned_root_slot_spec.json", planned_root_slot_spec)
        terminal = "failed_execution"
        try:
            # The pristine current/anchor are captured before any feasibility
            # method is called.  build_programs must be declarative.
            with self.adapter.scene(planned_root_slot_spec, phase="pristine") as pristine:
                reference_current = dict(self.adapter.capture_current(pristine))
                receipt["reference_capture_order"].append("capture_pristine_current")
                reference_anchor = dict(self.adapter.capture_anchor(pristine))
                receipt["reference_capture_order"].append("capture_pristine_anchor")
                programs = list(self.adapter.build_programs(pristine))
                validate_exactly_three_programs(programs)
                receipt["reference_capture_order"].append("build_declarative_programs")
                trees = dict(self.adapter.task_trees(programs))
                prefix = dict(self.adapter.canonical_prefix(programs))
            cleanup = dict(self.adapter.last_scene_cleanup_audit())
            receipt["cleanup_records"].append({"phase": "pristine", **cleanup})
            self._require_cleanup(cleanup, "pristine")

            _write_json(output_dir / "reference_current_hashes.json", reference_current)
            _write_json(output_dir / "reference_anchor.json", reference_anchor)

            # Every candidate gets a disposable fresh scene.  Any mutation made
            # by feasibility is discarded with that scene.
            feasibility_all_pass = True
            for program in programs:
                program_id = program["program_id"]
                feasibility_receipt = {"program_id": program_id, "status": "running"}
                try:
                    with self.adapter.scene(planned_root_slot_spec, phase="feasibility", program=program) as disposable:
                        candidate_current = dict(self.adapter.capture_current(disposable))
                        require_same_current(reference_current, candidate_current)
                        candidate_anchor = dict(self.adapter.capture_anchor(disposable))
                        anchor = compare_anchors(reference_anchor, candidate_anchor)
                        if not anchor["equivalent"]:
                            raise ValueError(f"feasibility anchor mismatch: {anchor['failures']}")
                        result = self.adapter.audit_feasibility(disposable, program)
                        if result is not True:
                            raise ValueError("candidate feasibility returned non-true")
                    cleanup = dict(self.adapter.last_scene_cleanup_audit())
                    receipt["cleanup_records"].append({"phase": "feasibility", "program_id": program_id, **cleanup})
                    self._require_cleanup(cleanup, f"feasibility:{program_id}")
                    feasibility_receipt["status"] = "passed"
                except BaseException as exc:
                    feasibility_all_pass = False
                    feasibility_receipt.update({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
                receipt["feasibility_receipts"].append(feasibility_receipt)

            if not feasibility_all_pass:
                terminal = "failed_planner"
                raise RuntimeError("not all three candidates passed disposable-scene feasibility")

            frozen = freeze_candidate_universe(
                planned_root_slot_spec=planned_root_slot_spec,
                programs=programs,
                observable_task_tree=trees["observable"],
                oracle_task_tree=trees["oracle"],
                implementation_version=self.implementation_version,
            )
            receipt["freeze_call_count"] += 1
            prefix["prefix_sha256"] = hash_json(prefix)
            _write_json(output_dir / "candidate_frozen_root_spec.json", frozen)
            _write_json(output_dir / "canonical_prefix.json", prefix)

            expected_program_ids = {program["program_id"] for program in programs}
            if set(realization_spec_by_program) != expected_program_ids:
                raise ValueError("realization specs must cover exactly the frozen three programs")

            # Branch failures are preserved, and later preregistered branches
            # still run unless cleanup becomes uncertain.
            for program in programs:
                program_id = program["program_id"]
                branch_dir = output_dir / "branches" / program_id
                branch_dir.mkdir(parents=True, exist_ok=False)
                branch = {
                    "schema_version": "cmf_root_branch_receipt_v1",
                    "program_id": program_id,
                    "formal_data": False,
                    "stage0_data": False,
                    "status": "failed_execution",
                    "reference_current_sha256": reference_current.get("aggregate_sha256"),
                    "candidate_universe_sha256": frozen["candidate_universe_sha256"],
                    "prefix_sha256": prefix["prefix_sha256"],
                }
                try:
                    with self.adapter.scene(planned_root_slot_spec, phase="rollout", program=program) as fresh:
                        branch_current = dict(self.adapter.capture_current(fresh))
                        require_same_current(reference_current, branch_current)
                        branch_anchor = dict(self.adapter.capture_anchor(fresh))
                        anchor = compare_anchors(reference_anchor, branch_anchor)
                        if not anchor["equivalent"]:
                            raise ValueError(f"rollout anchor mismatch: {anchor['failures']}")
                        rollout = dict(self.adapter.rollout(fresh, program, realization_spec_by_program[program_id]))
                        raw_manifest = write_raw_attempt(branch_dir / "raw", rollout["streams"], rollout["audit_streams"], rollout["provenance"])
                        verifier = dict(self.adapter.verify(fresh, program, rollout))
                        if verifier.get("pass") is not True:
                            branch["status"] = "failed_verifier"
                        else:
                            branch["status"] = "accepted"
                        branch.update({"raw_manifest": raw_manifest, "verifier": verifier, "branch_current": branch_current, "anchor_equivalence": anchor})
                    cleanup = dict(self.adapter.last_scene_cleanup_audit())
                    receipt["cleanup_records"].append({"phase": "rollout", "program_id": program_id, **cleanup})
                    self._require_cleanup(cleanup, f"rollout:{program_id}")
                except BaseException as exc:
                    branch.update({"error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
                    cleanup = dict(self.adapter.last_scene_cleanup_audit())
                    receipt["cleanup_records"].append({"phase": "rollout_exception", "program_id": program_id, **cleanup})
                    if cleanup.get("scene_cleanup_succeeded") is not True or cleanup.get("orphan_process_count") != 0:
                        branch["status"] = "failed_cleanup_uncertain"
                        receipt["branch_receipts"].append(branch)
                        _write_json(branch_dir / "receipt.json", branch)
                        raise RuntimeError("cleanup uncertain; stop all later root branches")
                receipt["branch_receipts"].append(branch)
                _write_json(branch_dir / "receipt.json", branch)

            root_cleanup_pass = all(
                item.get("scene_cleanup_succeeded") is True and item.get("orphan_process_count") == 0
                for item in receipt["cleanup_records"]
            )
            finalization = finalize_three_branch_root(receipt["branch_receipts"], root_cleanup_pass=root_cleanup_pass)
            receipt["root_finalization"] = finalization
            terminal = "accepted" if finalization["accepted"] else "failed_verifier"
        except BaseException as exc:
            receipt.setdefault("error_type", type(exc).__name__)
            receipt.setdefault("error", str(exc))
            receipt.setdefault("traceback", traceback.format_exc())
        receipt["status"] = terminal
        receipt["elapsed_seconds"] = time.time() - started
        _write_json(output_dir / "root_receipt.json", receipt)
        return receipt
