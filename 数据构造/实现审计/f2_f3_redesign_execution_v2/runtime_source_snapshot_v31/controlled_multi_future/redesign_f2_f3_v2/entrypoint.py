"""Minimum real-entry lifecycle; hooks remain explicit and instance-local."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .canonical import atomic_write_json


class EntrypointError(RuntimeError):
    """Raised when a lifecycle phase is missing or runs out of order."""


PHASES = ("construct", "readback", "settle", "current_anchor", "trace", "planner", "execute", "save", "verifier", "finalizer", "cleanup")


def run_job(*, job_id: str, output_dir: str | Path, hooks: Mapping[str, Callable[[dict[str, Any]], Any]], metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    context: dict[str, Any] = {
        "schema_version": "cmf_f2_f3_run_receipt_v1",
        "job_id": job_id,
        "pid": os.getpid(),
        "started_monotonic": time.monotonic(),
        "metadata": dict(metadata or {}),
        "phases": [],
        "counters": {"solver_problems": 0, "fresh_scenes": 1, "action_scenes": 0, "collection_attempts": 0, "gpu_lease_seconds": 0},
        "status": "RUNNING",
    }
    receipt_path = root / "run_receipt.json"
    error: BaseException | None = None
    try:
        for phase in PHASES[:-2]:
            if phase not in hooks:
                raise EntrypointError(f"missing required hook: {phase}")
            if phase == "current_anchor" and set(context["phases"]) != {"construct", "readback", "settle"}:
                raise EntrypointError("current/anchor must follow construct, readback, settle")
            if phase == "trace" and "current_anchor" not in context["phases"]:
                raise EntrypointError("trace must be initialized before planner or action")
            result = hooks[phase](context)
            if result is not None:
                context[phase] = result
            context["phases"].append(phase)
        context["status"] = "SUCCEEDED"
    except BaseException as exc:
        error = exc
        context["status"] = "FAILED"
        context["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            if "save" not in context["phases"] and "save" in hooks:
                hooks["save"](context)
                context["phases"].append("save")
            if "verifier" in hooks and "verifier" not in context["phases"]:
                hooks["verifier"](context)
                context["phases"].append("verifier")
            if "finalizer" in hooks:
                hooks["finalizer"](context)
                context["phases"].append("finalizer")
            if "cleanup" in hooks:
                hooks["cleanup"](context)
                context["phases"].append("cleanup")
            context["owned_cleanup_pass"] = bool("cleanup" in context["phases"])
            context["finished_monotonic"] = time.monotonic()
            atomic_write_json(receipt_path, context)
        except BaseException as finalizer_error:
            context["status"] = "FINALIZER_FAILED"
            context["finalizer_error"] = {"type": type(finalizer_error).__name__, "message": str(finalizer_error)}
            atomic_write_json(receipt_path, context)
            if error is None:
                error = finalizer_error
    if error is not None:
        raise error
    return context
