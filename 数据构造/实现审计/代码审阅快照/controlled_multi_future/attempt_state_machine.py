"""Explicit pilot attempt lifecycle; no implicit retry transitions."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import TERMINAL_ATTEMPT_STATUSES


TRANSITIONS = {
    "planned": {
        "scene_built",
        "failed_implementation_error",
        "aborted_with_reason",
    },
    "scene_built": {
        "candidates_frozen",
        "failed_implementation_error",
        "failed_planner",
        "failed_cleanup",
        "timeout",
    },
    "candidates_frozen": {
        "anchor_reconstructed",
        "failed_implementation_error",
        "failed_current_hash",
        "failed_anchor_equivalence",
        "failed_cleanup",
        "timeout",
    },
    "anchor_reconstructed": {
        "rolling_out",
        "failed_implementation_error",
        "failed_current_hash",
        "failed_anchor_equivalence",
        "failed_cleanup",
        "timeout",
    },
    "rolling_out": {
        "raw_saved",
        "failed_implementation_error",
        "failed_planner",
        "failed_execution",
        "failed_cleanup",
        "timeout",
    },
    "raw_saved": {
        "verified",
        "failed_implementation_error",
        "failed_verifier",
        "failed_cleanup",
    },
    "verified": {
        "accepted",
        "failed_implementation_error",
        "failed_cleanup",
    },
}


@dataclass
class AttemptStateMachine:
    state: str = "planned"

    def transition(self, target: str) -> None:
        if self.state in TERMINAL_ATTEMPT_STATUSES:
            raise RuntimeError("terminal attempt cannot transition")
        if target not in TRANSITIONS.get(self.state, set()):
            raise ValueError(f"invalid attempt transition {self.state!r} -> {target!r}")
        self.state = target

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_ATTEMPT_STATUSES
