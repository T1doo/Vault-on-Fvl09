"""Fail-closed A0 four-scene orchestration with v2 activity evidence.

The v1_2 orchestrator stores per-scene current, anchor, activity, cleanup, and
artifact hashes separately.  Top-level receipts reference immutable hashes and
never reinterpret diagnostics as a relaxed equivalence Gate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .a0_activity_monitor_v2 import (
    ACTIVITY_SCHEMA_VERSION,
    ActivityMonitorBoundaryError,
    ActivityMonitorError,
    ActivityMonitorInstallationError,
    ActivityMonitorRestorationError,
    validate_activity_receipt_v2,
)
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


A0_PHASES_V1_2 = ("A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3")
A0_ORCHESTRATOR_VERSION = "A0CurrentAnchorOrchestratorV1_2"


class A0CurrentMismatch(RuntimeError):
    pass


class A0AnchorMismatch(RuntimeError):
    pass


class A0ActivityAuditUnbound(RuntimeError):
    pass


class A0ActivityReceiptReuse(RuntimeError):
    pass


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_component_diff(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict:
    if "model_visible_components" in reference and "model_visible_components" in candidate:
        left = reference["model_visible_components"]
        right = candidate["model_visible_components"]
        wrist_left = left.get("wrist_rgb_sha256", {})
        wrist_right = right.get("wrist_rgb_sha256", {})
        reconstruction_left = reference.get("reconstruction_spec_components", {})
        reconstruction_right = candidate.get("reconstruction_spec_components", {})
        values = {
            "head_rgb": left.get("head_rgb_sha256") != right.get("head_rgb_sha256"),
            "left_wrist_rgb": wrist_left.get("left") != wrist_right.get("left"),
            "right_wrist_rgb": wrist_left.get("right") != wrist_right.get("right"),
            "robot_state": left.get("robot_state_sha256") != right.get("robot_state_sha256"),
            "gripper_state": left.get("gripper_actual_state_sha256") != right.get("gripper_actual_state_sha256"),
            "visible_roles": left.get("visible_object_roles_sha256") != right.get("visible_object_roles_sha256"),
            "camera_configuration": left.get("camera_configuration_sha256") != right.get("camera_configuration_sha256"),
            "reconstruction_spec": reconstruction_left != reconstruction_right,
        }
    else:
        left = reference.get("components", {})
        right = candidate.get("components", {})
        values = {
            "head_rgb": left.get("head_rgb_sha256") != right.get("head_rgb_sha256"),
            "left_wrist_rgb": left.get("wrist_rgb_sha256", {}).get("left")
            != right.get("wrist_rgb_sha256", {}).get("left"),
            "right_wrist_rgb": left.get("wrist_rgb_sha256", {}).get("right")
            != right.get("wrist_rgb_sha256", {}).get("right"),
            "robot_state": left.get("robot_state_sha256") != right.get("robot_state_sha256"),
            "gripper_state": left.get("gripper_actual_state_sha256")
            != right.get("gripper_actual_state_sha256"),
            "visible_roles": left.get("object_role_layout_sha256") != right.get("object_role_layout_sha256"),
            "camera_configuration": left.get("camera_config_version_sha256")
            != right.get("camera_config_version_sha256"),
            "reconstruction_spec": left.get("scene_spec_sha256") != right.get("scene_spec_sha256"),
        }
    return {"schema_version": "cmf_a0_current_component_diff_v1", "components_changed": values, "any_changed": any(values.values())}


def _anchor_component_diff(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict:
    comparison = compare_anchors(reference, candidate)
    failures = list(comparison.get("failures", []))

    def changed(*prefixes: str) -> bool:
        return any(any(item == prefix or item.startswith(prefix + ":") for prefix in prefixes) for item in failures)

    values = {
        "robot_qpos": changed("robot_qpos"),
        "robot_qvel": changed("robot_qvel"),
        "drive_target": changed("robot_drive_target"),
        "gripper_joint_qpos": changed("gripper_joint_qpos", "gripper_state"),
        "actor_pose": changed("actor_position", "actor_orientation", "actor_role_set"),
        "actor_velocity": changed("actor_linear_velocity", "actor_angular_velocity"),
        "actor_sleep_state": changed("actor_sleep_state"),
        "facility_pose": changed("facility_position", "facility_orientation", "facility_role_set"),
        "physics_config": changed("physics_config", "source_commit", "metadata"),
    }
    return {
        "schema_version": "cmf_a0_anchor_component_diff_v1",
        "components_changed": values,
        "failures": failures,
        "any_changed": bool(failures),
        "equivalence_result": comparison,
    }


class A0CurrentAnchorOrchestratorV1_2:
    formal_data = False
    stage0_data = False
    stage0_authorized = False
    gpu_probe_authorized = False

    _PROTECTED_METADATA_KEYS = {
        "schema_version",
        "implementation_version",
        "orchestrator_version",
        "formal_data",
        "stage0_data",
        "stage0_authorized",
        "gpu_probe_authorized",
        "planner_query_limit",
        "controlled_action_limit",
        "planned_root_slot_spec_sha256",
        "scene_pattern",
        "status",
        "scenes",
    }

    def __init__(self, adapter: Any, implementation_version: str = IMPLEMENTATION_VERSION):
        self.adapter = adapter
        self.implementation_version = implementation_version
        self._seen_scene_ids: set[str] = set()
        self._seen_activity_hashes: set[str] = set()

    @staticmethod
    def _phase_directory(output_dir: Path, index: int, phase: str) -> Path:
        return output_dir / "scenes" / f"{index:02d}_{phase}"

    @staticmethod
    def _write_scene_artifacts(
        phase_dir: Path,
        *,
        current: Mapping[str, Any] | None,
        anchor: Mapping[str, Any] | None,
        activity: Mapping[str, Any] | None,
        cleanup: Mapping[str, Any] | None,
    ) -> dict:
        values = {"current": current, "anchor": anchor, "activity": activity, "cleanup": cleanup}
        hashes = {}
        for name, value in values.items():
            if isinstance(value, Mapping):
                path = phase_dir / f"{name}.json"
                _write_json(path, value)
                hashes[name] = {"path": path.name, "sha256": _sha256_file(path)}
            else:
                hashes[name] = {"path": None, "sha256": None, "status": "unavailable_partial_failure"}
        artifact = {
            "schema_version": "cmf_a0_scene_artifact_hashes_v1",
            "files": hashes,
        }
        _write_json(phase_dir / "artifact_hashes.json", artifact)
        return {
            "files": hashes,
            "artifact_hashes_path": "artifact_hashes.json",
            "artifact_hashes_sha256": _sha256_file(phase_dir / "artifact_hashes.json"),
        }

    @staticmethod
    def _append_component_diff(phase_dir: Path, scene_record: dict, value: Mapping[str, Any]) -> None:
        path = phase_dir / "component_diff.json"
        _write_json(path, value)
        artifact_path = phase_dir / "artifact_hashes.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["files"]["component_diff"] = {"path": path.name, "sha256": _sha256_file(path)}
        _write_json(artifact_path, artifact)
        scene_record["artifact_hashes"]["files"] = artifact["files"]
        scene_record["artifact_hashes"]["artifact_hashes_sha256"] = _sha256_file(artifact_path)
        scene_record["component_diff"] = {
            "path": f"{scene_record['artifact_directory']}/component_diff.json",
            "sha256": _sha256_file(path),
        }

    def _capture_one_scene(
        self,
        *,
        output_dir: Path,
        index: int,
        receipt: dict,
        planned_spec: Mapping[str, Any],
        planned_spec_sha256: str,
        phase: str,
    ) -> dict:
        phase_dir = self._phase_directory(output_dir, index, phase)
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
                    raise TypeError("A0 adapter context must yield SceneHandleV1_1")
                handle = entered
                current = dict(self.adapter.capture_current(handle.scene))
                anchor = dict(self.adapter.capture_anchor(handle.scene))
                finish = getattr(self.adapter, "finish_a0_activity_monitor", None)
                if not callable(finish):
                    raise A0ActivityAuditUnbound("adapter lacks finish_a0_activity_monitor")
                activity = dict(
                    finish(
                        handle.scene,
                        phase=phase,
                        scene_instance_id=handle.scene_instance_id,
                    )
                )
                _require_unchanged(planned_copy, planned_spec_sha256, "planned_root_slot_spec")
        except BaseException as exc:
            body_error = exc
            body_traceback = traceback.format_exc()
            if activity is None and isinstance(getattr(exc, "receipt", None), Mapping):
                activity = dict(exc.receipt)

        expected_id = handle.scene_instance_id if handle is not None else None
        cleanup_raw = _cleanup_receipt_from(context, handle)
        cleanup = None
        cleanup_error = None
        try:
            cleanup = _validate_cleanup_receipt(
                cleanup_raw,
                expected_scene_instance_id=expected_id,
                seen_scene_instance_ids=self._seen_scene_ids,
                phase=phase,
            )
        except CleanupUncertain as exc:
            cleanup_error = exc
            cleanup = dict(cleanup_raw) if isinstance(cleanup_raw, Mapping) else None

        artifact_hashes = self._write_scene_artifacts(
            phase_dir,
            current=current,
            anchor=anchor,
            activity=activity,
            cleanup=cleanup,
        )
        scene_id = expected_id or (cleanup or {}).get("scene_instance_id")
        scene_record = {
            "phase": phase,
            "scene_instance_id": scene_id,
            "artifact_directory": f"scenes/{index:02d}_{phase}",
            "artifact_hashes": artifact_hashes,
            "current_aggregate_sha256": (current or {}).get("aggregate_sha256"),
            "anchor_sha256": (anchor or {}).get("anchor_sha256"),
            "activity_receipt_sha256": (activity or {}).get("activity_receipt_sha256"),
            "scene_created": (cleanup or {}).get("scene_created"),
            "cleanup_safety_pass": (cleanup or {}).get("cleanup_safety_pass"),
            "orphan_process_count": (cleanup or {}).get("orphan_process_count"),
            "status": "captured",
        }
        receipt["scenes"].append(scene_record)

        if cleanup_error is not None:
            scene_record["status"] = "failed_cleanup_uncertain"
            raise cleanup_error
        if body_error is not None:
            scene_record["status"] = f"failed_{type(body_error).__name__}"
            setattr(body_error, "cmf_traceback", body_traceback)
            raise body_error
        if not isinstance(activity, Mapping):
            raise A0ActivityAuditUnbound("A0 scene emitted no activity receipt")
        if activity.get("scene_instance_id") != scene_id or cleanup.get("scene_instance_id") != scene_id:
            raise A0ActivityAuditUnbound("activity, cleanup, and SceneHandle IDs differ")
        try:
            validated = validate_activity_receipt_v2(
                activity,
                expected_scene_instance_id=scene_id,
                expected_phase=phase,
            )
        except (ActivityMonitorBoundaryError, ActivityMonitorInstallationError, ActivityMonitorRestorationError):
            raise
        except ActivityMonitorError as exc:
            raise ActivityMonitorError(str(exc), receipt=activity) from exc
        activity_hash = validated["activity_receipt_sha256"]
        if activity_hash in self._seen_activity_hashes:
            raise A0ActivityReceiptReuse(f"activity receipt reused: {activity_hash}")
        self._seen_activity_hashes.add(activity_hash)
        scene_record["post_setup_activity"] = dict(validated["post_setup_activity"])
        scene_record["status"] = "validated"
        return {"record": scene_record, "current": current, "anchor": anchor, "activity": validated, "cleanup": cleanup}

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        receipt_metadata: Mapping[str, Any] | None = None,
    ) -> dict:
        started = time.time()
        output_dir = Path(output_dir)
        planned_spec = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned_spec)
        metadata = _immutable_copy(receipt_metadata or {})
        overlap = self._PROTECTED_METADATA_KEYS.intersection(metadata)
        if overlap:
            raise ValueError(f"receipt_metadata may not override protected fields: {sorted(overlap)}")
        output_dir.mkdir(parents=True, exist_ok=False)
        receipt = {
            "schema_version": "cmf_runtime_v3_1_a0_smoke_v1_2",
            "implementation_version": self.implementation_version,
            "implementation_revision": "runtime_v3_1_cpu_hardening_v5",
            "orchestrator_version": A0_ORCHESTRATOR_VERSION,
            "activity_schema_version": ACTIVITY_SCHEMA_VERSION,
            "purpose": "implementation_audit",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "gpu_probe_authorized": False,
            "scene_pattern": list(A0_PHASES_V1_2),
            "planner_query_limit": 0,
            "controlled_action_limit": 0,
            "planned_root_slot_spec_sha256": planned_hash,
            "status": "running",
            "scenes": [],
            **metadata,
        }
        _write_json(output_dir / "planned_root_slot_spec.json", planned_spec)
        reference_current = None
        reference_anchor = None
        try:
            for index, phase in enumerate(A0_PHASES_V1_2):
                captured = self._capture_one_scene(
                    output_dir=output_dir,
                    index=index,
                    receipt=receipt,
                    planned_spec=planned_spec,
                    planned_spec_sha256=planned_hash,
                    phase=phase,
                )
                current = captured["current"]
                anchor = captured["anchor"]
                record = captured["record"]
                phase_dir = self._phase_directory(output_dir, index, phase)
                if index == 0:
                    reference_current = current
                    reference_anchor = anchor
                    receipt["reference_current_sha256"] = current.get("aggregate_sha256")
                    receipt["reference_anchor_sha256"] = anchor.get("anchor_sha256")
                else:
                    try:
                        require_same_current(reference_current, current)
                    except BaseException as exc:
                        diagnostic = {
                            "schema_version": "cmf_a0_component_diff_bundle_v1",
                            "current_component_diff": _current_component_diff(reference_current, current),
                            "anchor_component_diff": _anchor_component_diff(reference_anchor, anchor),
                            "diagnostic_only_does_not_relax_gate": True,
                        }
                        self._append_component_diff(phase_dir, record, diagnostic)
                        raise A0CurrentMismatch(f"{phase} current mismatch: {exc}") from exc
                    comparison = compare_anchors(reference_anchor, anchor)
                    record["anchor_equivalence"] = comparison
                    if not comparison["equivalent"]:
                        diagnostic = {
                            "schema_version": "cmf_a0_component_diff_bundle_v1",
                            "current_component_diff": _current_component_diff(reference_current, current),
                            "anchor_component_diff": _anchor_component_diff(reference_anchor, anchor),
                            "diagnostic_only_does_not_relax_gate": True,
                        }
                        self._append_component_diff(phase_dir, record, diagnostic)
                        raise A0AnchorMismatch(f"{phase} anchor mismatch: {comparison['failures']}")
            receipt["status"] = "passed_nonformal_A0"
        except CleanupUncertain as exc:
            receipt.update({"status": "failed_cleanup_uncertain", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except CandidateMutationError as exc:
            receipt.update({"status": "failed_candidate_mutation", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except ActivityMonitorInstallationError as exc:
            receipt.update({"status": "failed_activity_monitor_installation", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except ActivityMonitorRestorationError as exc:
            receipt.update({"status": "failed_activity_monitor_restoration", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except ActivityMonitorBoundaryError as exc:
            receipt.update({"status": "failed_activity_audit_unbound", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except A0ActivityAuditUnbound as exc:
            receipt.update({"status": "failed_activity_audit_unbound", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except A0ActivityReceiptReuse as exc:
            receipt.update({"status": "failed_activity_receipt_reuse", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except ActivityMonitorError as exc:
            receipt.update({"status": "failed_zero_post_setup_activity", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})
        except A0CurrentMismatch as exc:
            receipt.update({"status": "failed_current_hash", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        except A0AnchorMismatch as exc:
            receipt.update({"status": "failed_anchor_equivalence", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        except BaseException as exc:
            receipt.update({"status": "failed_A0", "error_type": type(exc).__name__, "error": str(exc), "traceback": getattr(exc, "cmf_traceback", None) or traceback.format_exc()})

        receipt["elapsed_seconds"] = time.time() - started
        receipt["scene_created"] = any(item.get("scene_created") is True for item in receipt["scenes"])
        receipt["all_four_scenes_created"] = len(receipt["scenes"]) == 4 and all(
            item.get("scene_created") is True and item.get("cleanup_safety_pass") is True
            for item in receipt["scenes"]
        )
        receipt["scene_cleanup_succeeded"] = bool(receipt["scenes"]) and all(
            item.get("cleanup_safety_pass") is True for item in receipt["scenes"]
        )
        receipt["orphan_process_count"] = sum(
            int(item.get("orphan_process_count") or 0) for item in receipt["scenes"]
        )
        receipt["post_setup_planner_query_count"] = sum(
            int(item.get("post_setup_activity", {}).get("planner_query_delta", 0)) for item in receipt["scenes"]
        )
        receipt["post_setup_controlled_action_count"] = sum(
            int(item.get("post_setup_activity", {}).get("controlled_action_delta", 0)) for item in receipt["scenes"]
        )
        if receipt["status"] == "passed_nonformal_A0" and not (
            receipt["all_four_scenes_created"]
            and receipt["scene_cleanup_succeeded"]
            and receipt["orphan_process_count"] == 0
            and receipt["post_setup_planner_query_count"] == 0
            and receipt["post_setup_controlled_action_count"] == 0
        ):
            receipt["status"] = "failed_A0_summary_invariant"
        _write_json(output_dir / "receipt.json", receipt)
        return receipt
