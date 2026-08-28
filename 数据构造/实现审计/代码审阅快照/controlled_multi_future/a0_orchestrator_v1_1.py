"""Adapter-agnostic, zero-action A0 current/anchor smoke orchestration.

The A0 gate is deliberately narrower than a family feasibility probe.  It
constructs one pristine scene and three deterministic fresh reconstructions,
captures only current/anchor state, and fails closed if any planner query or
controlled action is observed.  Importing this module does not initialize a
renderer or GPU and does not authorize A0, Stage 0, or formal collection.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .anchor import compare_anchors
from .current_hasher import hash_json, require_same_current
from .root_orchestrator_v1_1 import (
    CandidateMutationError,
    CleanupUncertain,
    IMPLEMENTATION_VERSION,
    SceneHandleV1_1,
    _cleanup_receipt_from,
    _immutable_copy,
    _require_unchanged,
    _validate_cleanup_receipt,
)


A0_PHASES = ("A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3")


class A0CurrentMismatch(RuntimeError):
    """A fresh reconstruction changed the model-visible current."""


class A0AnchorMismatch(RuntimeError):
    """A fresh reconstruction changed the hidden physical anchor."""


class A0ActivityViolation(RuntimeError):
    """A supposedly zero-action scene performed planning or an action."""


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _validate_activity_audit(value: Mapping[str, Any], *, phase: str) -> dict:
    if not isinstance(value, Mapping):
        raise A0ActivityViolation(f"{phase} emitted no structured activity audit")
    record = dict(value)
    required = (
        "planner_query_count",
        "planner_query_record_count",
        "action_execution_count",
        "trace_row_count",
        "canonical_settle_steps",
        "canonical_settle_is_control_action",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise A0ActivityViolation(f"{phase} activity audit missing {missing}")
    for key in required[:5]:
        if not isinstance(record[key], int) or record[key] < 0:
            raise A0ActivityViolation(f"{phase} activity field {key} must be a nonnegative integer")
    if record["canonical_settle_is_control_action"] is not False:
        raise A0ActivityViolation(f"{phase} setup settling must be distinguished from controlled actions")
    if record["planner_query_count"] != record["planner_query_record_count"]:
        raise A0ActivityViolation(f"{phase} planner counters disagree")
    if record["planner_query_count"] != 0 or record["action_execution_count"] != 0:
        raise A0ActivityViolation(
            f"{phase} violated zero-action A0: planner={record['planner_query_count']} "
            f"actions={record['action_execution_count']}"
        )
    return record


class A0CurrentAnchorOrchestratorV1_1:
    """Run the four-scene, zero-action A0 contract against any reviewed adapter."""

    formal_data = False
    stage0_data = False
    stage0_authorized = False
    gpu_probe_authorized = False

    _PROTECTED_METADATA_KEYS = {
        "schema_version",
        "implementation_version",
        "purpose",
        "formal_data",
        "stage0_data",
        "stage0_authorized",
        "gpu_probe_authorized",
        "planner_query_limit",
        "planner_query_count",
        "action_execution_limit",
        "action_execution_count",
        "status",
        "scenes",
        "cleanup_records",
    }

    def __init__(self, adapter: Any, implementation_version: str = IMPLEMENTATION_VERSION):
        self.adapter = adapter
        self.implementation_version = implementation_version
        self._seen_scene_instance_ids: set[str] = set()

    def _capture_one_scene(
        self,
        *,
        receipt: dict,
        planned_spec: Mapping[str, Any],
        planned_spec_sha256: str,
        phase: str,
    ) -> dict:
        planned_copy = _immutable_copy(planned_spec)
        context = self.adapter.scene(planned_copy, phase=phase, program=None)
        handle: SceneHandleV1_1 | None = None
        current = None
        anchor = None
        activity = None
        body_error: BaseException | None = None
        body_traceback = None
        try:
            with context as entered:
                if not isinstance(entered, SceneHandleV1_1):
                    raise TypeError("A0 adapter scene context must yield SceneHandleV1_1")
                handle = entered
                current = dict(self.adapter.capture_current(handle.scene))
                anchor = dict(self.adapter.capture_anchor(handle.scene))
                activity_hook = getattr(self.adapter, "capture_a0_activity_audit", None)
                if not callable(activity_hook):
                    raise A0ActivityViolation("adapter does not implement capture_a0_activity_audit")
                activity_raw = activity_hook(handle.scene)
                activity = dict(activity_raw) if isinstance(activity_raw, Mapping) else None
                activity = _validate_activity_audit(activity_raw, phase=phase)
                _require_unchanged(planned_copy, planned_spec_sha256, "planned_root_slot_spec")
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
                receipt["cleanup_records"].append(
                    {"phase": phase, **dict(cleanup_raw), "cleanup_validation_pass": False}
                )
            raise

        scene_record = {
            "phase": phase,
            "scene_instance_id": cleanup["scene_instance_id"],
            "current": current,
            "anchor": anchor,
            "activity_audit": activity,
            "cleanup": cleanup,
        }
        receipt["scenes"].append(scene_record)
        if body_error is not None:
            setattr(body_error, "cmf_traceback", body_traceback)
            raise body_error
        return scene_record

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        receipt_metadata: Mapping[str, Any] | None = None,
    ) -> dict:
        """Run A0 in a new immutable output directory and always write a receipt."""

        started = time.time()
        output_dir = Path(output_dir)
        planned_spec = _immutable_copy(planned_root_slot_spec)
        planned_spec_sha256 = hash_json(planned_spec)
        metadata = _immutable_copy(receipt_metadata or {})
        overlap = self._PROTECTED_METADATA_KEYS.intersection(metadata)
        if overlap:
            raise ValueError(f"receipt_metadata may not override protected fields: {sorted(overlap)}")
        output_dir.mkdir(parents=True, exist_ok=False)
        receipt = {
            "schema_version": "cmf_runtime_v3_1_a0_smoke_v1_1",
            "implementation_version": self.implementation_version,
            "purpose": "implementation_audit",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "gpu_probe_authorized": False,
            "planner_query_limit": 0,
            "planner_query_count": 0,
            "action_execution_limit": 0,
            "action_execution_count": 0,
            "planned_root_slot_spec_sha256": planned_spec_sha256,
            "status": "running",
            "scenes": [],
            "cleanup_records": [],
            **metadata,
        }
        _write_json(output_dir / "planned_root_slot_spec.json", planned_spec)
        reference_current = None
        reference_anchor = None
        try:
            for index, phase in enumerate(A0_PHASES):
                scene_record = self._capture_one_scene(
                    receipt=receipt,
                    planned_spec=planned_spec,
                    planned_spec_sha256=planned_spec_sha256,
                    phase=phase,
                )
                current = scene_record["current"]
                anchor = scene_record["anchor"]
                phase_dir = output_dir / "scenes" / f"{index:02d}_{phase}"
                _write_json(phase_dir / "current.json", current)
                _write_json(phase_dir / "anchor.json", anchor)
                if index == 0:
                    reference_current = current
                    reference_anchor = anchor
                    _write_json(output_dir / "reference_current.json", reference_current)
                    _write_json(output_dir / "reference_anchor.json", reference_anchor)
                else:
                    try:
                        require_same_current(reference_current, current)
                    except BaseException as exc:
                        raise A0CurrentMismatch(f"{phase} current mismatch: {exc}") from exc
                    comparison = compare_anchors(reference_anchor, anchor)
                    scene_record["anchor_equivalence"] = comparison
                    if not comparison["equivalent"]:
                        raise A0AnchorMismatch(f"{phase} anchor mismatch: {comparison['failures']}")
            receipt["status"] = "passed_nonformal_A0"
        except CleanupUncertain as exc:
            receipt.update(
                {
                    "status": "failed_cleanup_uncertain",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                }
            )
        except CandidateMutationError as exc:
            receipt.update(
                {
                    "status": "failed_candidate_mutation",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                }
            )
        except A0CurrentMismatch as exc:
            receipt.update(
                {
                    "status": "failed_current_hash",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                }
            )
        except A0AnchorMismatch as exc:
            receipt.update(
                {
                    "status": "failed_anchor_equivalence",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                }
            )
        except A0ActivityViolation as exc:
            receipt.update(
                {
                    "status": "failed_zero_action_contract",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                }
            )
        except BaseException as exc:
            receipt.update(
                {
                    "status": "failed_A0",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc(),
                }
            )

        receipt["elapsed_seconds"] = time.time() - started
        receipt["planner_query_count"] = sum(
            int((item.get("activity_audit") or {}).get("planner_query_count") or 0)
            for item in receipt["scenes"]
        )
        receipt["action_execution_count"] = sum(
            int((item.get("activity_audit") or {}).get("action_execution_count") or 0)
            for item in receipt["scenes"]
        )
        receipt["scene_created"] = any(
            item.get("cleanup", {}).get("scene_created") is True for item in receipt["scenes"]
        )
        receipt["all_four_scenes_created"] = len(receipt["scenes"]) == len(A0_PHASES) and all(
            item.get("cleanup", {}).get("scene_created") is True for item in receipt["scenes"]
        )
        receipt["scene_cleanup_succeeded"] = bool(receipt["cleanup_records"]) and all(
            item.get("cleanup_safety_pass") is True for item in receipt["cleanup_records"]
        )
        receipt["orphan_process_count"] = sum(
            int(item.get("orphan_process_count") or 0) for item in receipt["cleanup_records"]
        )
        if receipt["status"] == "passed_nonformal_A0" and not (
            receipt["all_four_scenes_created"]
            and receipt["scene_cleanup_succeeded"]
            and receipt["planner_query_count"] == 0
            and receipt["action_execution_count"] == 0
            and receipt["orphan_process_count"] == 0
        ):
            receipt["status"] = "failed_A0_summary_invariant"
        _write_json(output_dir / "receipt.json", receipt)
        return receipt
