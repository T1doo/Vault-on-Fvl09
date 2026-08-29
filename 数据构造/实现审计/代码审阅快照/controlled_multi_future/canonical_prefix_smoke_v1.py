"""Bounded real-SAPIEN smoke for canonical-prefix generation and exact replay."""

from __future__ import annotations

import hashlib
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .anchor import compare_anchors
from .canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import hash_json, require_same_current
from .root_orchestrator_v1_1 import (
    CleanupUncertain,
    _immutable_copy,
    _write_json,
)
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _validate_prefix_reference_result,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_canonical_prefix_real_smoke_v1"


def _best_effort_trace(scene, path: Path) -> dict:
    if not hasattr(scene, "save_trace"):
        return {
            "status": "unavailable",
            "error_type": "MissingTraceWriter",
            "error": "scene does not expose save_trace",
        }
    try:
        info = dict(scene.save_trace(path))
        return {
            "status": "saved",
            **info,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    except BaseException as exc:
        return {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


class CanonicalPrefixRealSmokeV1:
    """Generate once and replay in three fresh scenes; never execute a suffix."""

    def __init__(self, adapter):
        self.adapter = adapter
        self.scene_helper = RealSapienStrictPrefixRootOrchestratorV1_2(adapter)

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
    ) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_3",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "planned_root_slot_spec_sha256": planned_hash,
            "planner_query_count": 0,
            "execution_attempt_count": 1,
            "reference_prefix_generation_count": 1,
            "prefix_replay_count": 0,
            "candidate_suffix_execution_count": 0,
            "recovery_attempt_count": 0,
            "cleanup_records": [],
        }
        self.scene_helper._event_log_path = output_dir / "events.jsonl"
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

            current, anchor, programs, prefix_contract = self.scene_helper._scene_call(
                receipt=receipt,
                planned_spec=planned,
                planned_spec_sha256=planned_hash,
                phase="canonical_prefix_smoke_pristine",
                program=None,
                program_sha256=None,
                callback=pristine_callback,
            )
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)
            _write_json(output_dir / "programs.json", {"programs": programs})
            _write_json(output_dir / "prefix_contract.json", prefix_contract)

            reference_runtime = {"planner_query_count": 0}

            def reference_callback(scene, _program):
                planner_before = int(getattr(scene, "planner_query_count", 0))
                try:
                    require_same_current(
                        current, dict(self.adapter.capture_current(scene))
                    )
                    start = compare_anchors(
                        anchor, dict(self.adapter.capture_anchor(scene))
                    )
                    if not start["equivalent"]:
                        raise ValueError(
                            f"prefix smoke reference anchor mismatch: {start['failures']}"
                        )
                    result = _validate_prefix_reference_result(
                        self.adapter.plan_and_execute_canonical_prefix(
                            scene, _immutable_copy(prefix_contract)
                        )
                    )
                    trace_path = output_dir / "reference_trace.npz"
                    trace_info = _best_effort_trace(scene, trace_path)
                    if trace_info.get("status") != "saved":
                        raise RuntimeError(
                            f"canonical prefix reference trace save failed: {trace_info}"
                        )
                    result["trace_source"] = trace_info
                    return result
                except BaseException:
                    receipt["reference_partial_trace"] = _best_effort_trace(
                        scene, output_dir / "reference_partial_trace.npz"
                    )
                    raise
                finally:
                    reference_runtime["planner_query_count"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - planner_before

            try:
                result = self.scene_helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="canonical_prefix_smoke_reference",
                    program=None,
                    program_sha256=None,
                    callback=reference_callback,
                )
            finally:
                receipt["planner_query_count"] = int(
                    reference_runtime["planner_query_count"]
                )
            manifest, arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family=str(planned["family"]),
                reference_current_sha256=current["aggregate_sha256"],
                reference_anchor=anchor,
                prefix_contract=prefix_contract,
                planner_seed=int(result.get("planner_seed", 20260828)),
                planner_query_receipts=result["planner_query_receipts"],
                planner_source_hash=result["planner_source_hash"],
                arrays=result["arrays"],
                semantic_prefix_end_anchor=result["semantic_prefix_end_anchor"],
                acceptance_prefix_end_anchor=result["acceptance_prefix_end_anchor"],
                settling_step_count=int(result["settling_step_count"]),
                settling_policy=result["settling_policy"],
                prefix_physical_acceptance=result[
                    "prefix_physical_acceptance"
                ],
                reference_trace_source=result["trace_source"],
                reference_event_boundaries=result.get(
                    "reference_event_boundaries", {}
                ),
            )
            manifest = write_canonical_prefix_artifact(
                output_dir / "artifact", manifest, arrays
            )
            if receipt["planner_query_count"] != len(
                result["planner_query_receipts"]
            ):
                raise ValueError(
                    "prefix smoke planner query delta/table count mismatch"
                )
            receipt["canonical_prefix_artifact_sha256"] = manifest[
                "artifact_sha256"
            ]

            replays = []
            for replay_index in range(1, 4):
                def replay_callback(scene, _program, replay_index=replay_index):
                    try:
                        require_same_current(
                            current, dict(self.adapter.capture_current(scene))
                        )
                        replay_start = compare_anchors(
                            anchor, dict(self.adapter.capture_anchor(scene))
                        )
                        if not replay_start["equivalent"]:
                            raise ValueError(
                                f"prefix smoke replay anchor mismatch: {replay_start['failures']}"
                            )
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
                        if replay["prefix_end_equivalent"] is not True:
                            raise ValueError(
                                "canonical prefix exact replay end state mismatch"
                            )
                        physical = dict(
                            self.adapter.validate_replayed_prefix_physical(
                                scene, replay
                            )
                        )
                        replay["replayed_prefix_physical_acceptance"] = physical
                        if physical.get("pass") is not True:
                            raise ValueError(
                                "canonical prefix smoke replay physical Gate failed"
                            )
                        trace_path = output_dir / f"replay_{replay_index}_trace.npz"
                        trace_info = _best_effort_trace(scene, trace_path)
                        if trace_info.get("status") != "saved":
                            raise RuntimeError(
                                f"canonical replay trace save failed: {trace_info}"
                            )
                        replay["trace_source"] = trace_info
                        return replay
                    except BaseException:
                        receipt.setdefault("replay_partial_traces", []).append(
                            {
                                "replay_index": replay_index,
                                "trace": _best_effort_trace(
                                    scene,
                                    output_dir
                                    / f"replay_{replay_index}_partial_trace.npz",
                                ),
                            }
                        )
                        raise

                replays.append(
                    self.scene_helper._scene_call(
                        receipt=receipt,
                        planned_spec=planned,
                        planned_spec_sha256=planned_hash,
                        phase=f"canonical_prefix_smoke_replay_{replay_index}",
                        program=None,
                        program_sha256=None,
                        callback=replay_callback,
                    )
                )
            receipt["replays"] = replays
            receipt["three_replays_share_action_hash"] = (
                len(
                    {
                        item["executed_prefix_action_sha256"]
                        for item in replays
                    }
                )
                == 1
                and next(iter({item["executed_prefix_action_sha256"] for item in replays}))
                == manifest["prefix_action_sha256"]
            )
            if receipt["three_replays_share_action_hash"] is not True:
                raise ValueError("canonical prefix smoke replay hashes differ")
            receipt["status"] = "passed_canonical_prefix_real_smoke"
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            receipt["status"] = "failed_canonical_prefix_real_smoke"
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
