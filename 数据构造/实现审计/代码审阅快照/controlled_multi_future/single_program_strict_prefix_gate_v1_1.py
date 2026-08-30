"""Fail-closed receipt propagation wrapper for one-program diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import traceback

from .common_scope_counter_schema_v3_4_1 import (
    build_execution_attempt_counts,
    build_planner_query_counts,
    build_primary_failure_cleanup_receipt,
)
from .current_hasher import hash_json
from .root_orchestrator_v1_1 import _write_json
from .single_program_strict_prefix_gate_v1 import (
    SingleProgramStrictPrefixGateV1,
)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _cleanup_records(path: Path):
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if value.get("event") == "scene_cleanup":
            records.append(dict(value["record"]))
    return records


def _prefix_counts(prefix_manifest: dict) -> tuple[int, int]:
    target = 0
    canonical = 0
    for item in prefix_manifest.get("planner_query_receipts", []):
        if item.get("query_type") == "batched_grasp_target_selection":
            target += 1
        else:
            canonical += 1
    return canonical, target


class SingleProgramStrictPrefixGateV1_1:
    def __init__(self, adapter, *, program_id: str, gate_id: str):
        self.base = SingleProgramStrictPrefixGateV1(
            adapter, program_id=program_id, gate_id=gate_id
        )
        self.program_id = program_id
        self.gate_id = gate_id

    def run(self, *, output_dir: Path, planned_root_slot_spec):
        output_dir = Path(output_dir)
        error = None
        result = None
        try:
            result = self.base.run(
                output_dir=output_dir,
                planned_root_slot_spec=planned_root_slot_spec,
            )
        except BaseException as exc:
            error = exc
        events = _cleanup_records(output_dir / "events.jsonl")
        prefix_path = output_dir / "prefix_artifact/canonical_prefix_artifact.json"
        preflight_path = output_dir / "preflight_receipt.json"
        program_path = output_dir / "program_receipt.json"
        prefix = _read(prefix_path) if prefix_path.is_file() else {}
        preflight = _read(preflight_path) if preflight_path.is_file() else {}
        program = _read(program_path) if program_path.is_file() else {}
        canonical_count, target_count = _prefix_counts(prefix)
        suffix_count = int(preflight.get("planner_query_count", 0) or 0)
        planner_counts = build_planner_query_counts(
            canonical_prefix=canonical_count,
            target_construction=target_count,
            suffix_control_chain=suffix_count,
            diagnostic_only=0,
        )
        execution_cleanup = any(
            str(item.get("phase", "")).endswith(":execution")
            for item in events
        )
        controller_entered = bool(
            program.get("partial_trace_source")
            or program.get("raw_manifest")
            or (result and int(result.get("execution_attempt_count", 0)) > 0)
        )
        execution_counts = build_execution_attempt_counts(
            dispatch_started=1 if execution_cleanup or controller_entered else 0,
            controller_entered=1 if controller_entered else 0,
            terminal_receipt_written=1 if program_path.is_file() else 0,
        )
        cleanup_pass = bool(events) and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count") or 0) == 0
            for item in events
        )
        primary = None
        if error is not None:
            primary = {
                "stage": "controller_execution"
                if controller_entered
                else "single_program_gate",
                "type": type(error).__name__,
                "message": str(error),
            }
        failure_cleanup = build_primary_failure_cleanup_receipt(
            primary_failure=primary,
            cleanup_status={
                "attempted": bool(events),
                "passed": cleanup_pass,
                "uncertainty": not cleanup_pass,
            },
            receipt_propagation_status=(
                "propagated_from_inner_failure_without_overwriting_primary"
                if error is not None
                else "normal_return"
            ),
        )
        terminal = dict(result or {})
        terminal.update(
            {
                "schema_version": "cmf_single_program_strict_prefix_gate_v1_1",
                "implementation_version": (
                    "controlled_multi_future_runtime_v3_4_1"
                ),
                "gate_id": self.gate_id,
                "program_id": self.program_id,
                "formal_data": False,
                "stage0_data": False,
                "stage0_authorized": False,
                "status": (
                    terminal.get("status", "failed_execution")
                    if error is None
                    else "failed_execution"
                ),
                "pass": bool(terminal.get("pass", False))
                and error is None,
                "planner_query_counts": planner_counts,
                "execution_attempt_counts": execution_counts,
                "budget_counts": {
                    "planner_query_count": planner_counts["scope_total"],
                    "execution_attempt_count": execution_counts[
                        "dispatch_started"
                    ],
                    "recovery_attempt_count": 0,
                },
                "primary_failure_cleanup": failure_cleanup,
                "cleanup_records": events,
                "scene_cleanup_succeeded": cleanup_pass,
                "orphan_process_count": sum(
                    int(item.get("orphan_process_count") or 0)
                    for item in events
                ),
                "inner_program_receipt": program,
                "traceback": None
                if error is None
                else getattr(error, "cmf_traceback", None)
                or "".join(traceback.format_exception(error)),
            }
        )
        payload = dict(terminal)
        payload.pop("receipt_sha256", None)
        terminal["receipt_sha256"] = hash_json(payload)
        _write_json(output_dir / "receipt.json", terminal)
        return terminal


__all__ = ["SingleProgramStrictPrefixGateV1_1"]
