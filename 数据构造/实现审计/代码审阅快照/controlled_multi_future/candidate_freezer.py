"""Immutable candidate-universe and task-tree freezing helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .current_hasher import hash_json
from .schemas import validate_exactly_three_programs


def freeze_candidate_universe(
    *,
    planned_root_slot_spec: Mapping[str, Any],
    programs: Sequence[Mapping[str, Any]],
    observable_task_tree: Mapping[str, Any],
    oracle_task_tree: Mapping[str, Any],
    implementation_version: str,
) -> dict:
    validate_exactly_three_programs(programs)
    payload = {
        "schema_version": "candidate_frozen_root_spec_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": implementation_version,
        "planned_root_slot_spec": deepcopy(dict(planned_root_slot_spec)),
        "programs": deepcopy(list(programs)),
        "observable_task_tree": deepcopy(dict(observable_task_tree)),
        "oracle_task_tree": deepcopy(dict(oracle_task_tree)),
    }
    payload["candidate_universe_sha256"] = hash_json(payload["programs"])
    payload["observable_task_tree_sha256"] = hash_json(payload["observable_task_tree"])
    payload["oracle_task_tree_sha256"] = hash_json(payload["oracle_task_tree"])
    payload["frozen_spec_sha256"] = hash_json(payload)
    return payload


def require_frozen_candidate_match(reference: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    keys = ("candidate_universe_sha256", "observable_task_tree_sha256", "oracle_task_tree_sha256")
    if any(reference.get(key) != candidate.get(key) for key in keys):
        raise ValueError("candidate universe or task tree changed across fresh reconstruction")
