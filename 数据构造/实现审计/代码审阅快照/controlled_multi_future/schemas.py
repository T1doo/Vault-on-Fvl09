"""Small dependency-free schema checks used before runtime implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence


VALID_FAMILIES = frozenset({"F1", "F2", "F3", "F4"})
VALID_PROBE_PURPOSES = frozenset({"implementation_audit", "nonformal_feasibility"})
TERMINAL_ATTEMPT_STATUSES = frozenset({
    "accepted",
    "failed_planner",
    "failed_execution",
    "failed_verifier",
    "failed_current_hash",
    "failed_anchor_equivalence",
    "failed_cleanup",
    "failed_cleanup_uncertain",
    "timeout",
    "aborted_with_reason",
})


def validate_exactly_three_programs(programs: Sequence[Mapping[str, Any]]) -> None:
    if not isinstance(programs, (list, tuple)) or len(programs) != 3:
        raise ValueError("a family must expose exactly three provisional programs")
    ids = []
    for program in programs:
        if not isinstance(program, Mapping):
            raise TypeError("each program must be a mapping")
        program_id = program.get("program_id")
        steps = program.get("steps")
        if not isinstance(program_id, str) or not program_id:
            raise ValueError("each program needs a non-empty program_id")
        if not isinstance(steps, list) or not steps:
            raise ValueError("each program needs a non-empty ordered steps list")
        ids.append(program_id)
    if len(set(ids)) != 3:
        raise ValueError("program IDs must be unique")


def validate_probe_receipt(receipt: Mapping[str, Any], output_root: Path) -> None:
    if receipt.get("formal_data") is not False or receipt.get("stage0_data") is not False:
        raise ValueError("audit probes must explicitly be non-formal and non-Stage-0")
    if receipt.get("purpose") not in VALID_PROBE_PURPOSES:
        raise ValueError("unsupported probe purpose")
    timeout = receipt.get("timeout_seconds")
    attempts = receipt.get("attempt_limit")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("probe timeout must be finite and positive")
    if not isinstance(attempts, int) or not 1 <= attempts <= 3:
        raise ValueError("audit probe attempt_limit must be in [1,3]")
    declared = Path(receipt.get("output_root", "")).resolve()
    if declared != output_root.resolve():
        raise ValueError("probe output must use the audited probe_outputs root")


def validate_attempt_counts(counts: Mapping[str, Any]) -> None:
    required = (
        "feasibility_query_count",
        "planner_query_count",
        "execution_attempt_count",
        "recovery_attempt_count",
    )
    for key in required:
        value = counts.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer")


def validate_primary_stream(actions, states, *, frequency_hz=250, action_dim=26) -> None:
    import numpy as np

    action_array = np.asarray(actions)
    state_array = np.asarray(states)
    if frequency_hz != 250 or action_dim != 26:
        raise ValueError("primary stream contract is fixed at 250 Hz and 26 dimensions")
    if action_array.ndim != 2 or action_array.shape[1] != action_dim:
        raise ValueError("primary actions must have shape [N, 26]")
    if state_array.ndim < 2 or state_array.shape[0] != action_array.shape[0] + 1:
        raise ValueError("primary stream requires N actions and N+1 states")
