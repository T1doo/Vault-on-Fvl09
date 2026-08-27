"""Model-visible sample projection that excludes answer-bearing path metadata."""

from __future__ import annotations

from typing import Any, Mapping


FORBIDDEN_KEYS = frozenset({"path", "file_path", "branch_id", "intent_id", "candidate_id", "instance_id", "planner_phase", "verifier_truth"})
ALLOWED_KEYS = frozenset({"current_rgb", "current_robot_state", "future_effective_setpoints", "candidate_program_semantics", "visible_referring_expressions"})


def build_model_view(sample: Mapping[str, Any]) -> dict:
    leaked = FORBIDDEN_KEYS.intersection(sample)
    if leaked:
        raise ValueError(f"forbidden model-visible metadata: {sorted(leaked)}")
    missing = ALLOWED_KEYS.difference(sample)
    if missing:
        raise ValueError(f"missing model-visible fields: {sorted(missing)}")
    return {key: sample[key] for key in sorted(ALLOWED_KEYS)}
