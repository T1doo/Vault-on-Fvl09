"""Frozen nonformal F1 five-root batch-pilot plan.

This module plans development roots only.  It never authorizes collection and
never promotes a pilot trajectory into the formal denominator.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json as hash_json


SCHEMA_VERSION = "cmf_f1_batch_generation_pilot_plan_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f1_batch_pilot_v1"
PROGRAM_IDS = ("F1-red", "F1-green", "F1-blue")
ROLE_ORDER = ("red", "green", "blue")
POSITION_SLOTS = {
    "left": [-0.20, 0.02, 0.762],
    "center": [-0.11, 0.02, 0.762],
    "right": [-0.02, 0.02, 0.762],
}
COMMON_BOX_POSE = [-0.08, -0.16, 0.78, 0.5, 0.5, 0.5, 0.5]
PRIMARY_ROOT_COUNT = 5
RESERVE_ROOT_COUNT = 5


_ROLE_SLOT_PERMUTATIONS = (
    ("left", "center", "right"),
    ("right", "left", "center"),
    ("center", "right", "left"),
    ("left", "right", "center"),
    ("center", "left", "right"),
    ("right", "center", "left"),
)
_DISPLAY_PERMUTATIONS = (
    ("F1-red", "F1-green", "F1-blue"),
    ("F1-green", "F1-blue", "F1-red"),
    ("F1-blue", "F1-red", "F1-green"),
    ("F1-red", "F1-blue", "F1-green"),
    ("F1-green", "F1-red", "F1-blue"),
    ("F1-blue", "F1-green", "F1-red"),
)


def _layout(permutation_index: int) -> dict[str, Any]:
    assigned = _ROLE_SLOT_PERMUTATIONS[permutation_index]
    value = {
        "layout_version": "f1_role_position_permutation_v1",
        "position_slots": deepcopy(POSITION_SLOTS),
        "role_to_slot": dict(zip(ROLE_ORDER, assigned)),
        "object_xyz_by_role": {
            role: list(POSITION_SLOTS[slot])
            for role, slot in zip(ROLE_ORDER, assigned)
        },
        "common_box_pose_wxyz": list(COMMON_BOX_POSE),
        "planner_changed": False,
        "verifier_changed": False,
        "canonical_prefix_changed": False,
    }
    value["layout_sha256"] = hash_json(value)
    return value


def _root_spec(*, sequence: int, reserve: bool) -> dict[str, Any]:
    if sequence < 0 or sequence >= RESERVE_ROOT_COUNT:
        raise ValueError("F1 batch root sequence is outside the frozen range")
    permutation_index = sequence if not reserve else (sequence + 1) % 6
    kind = "reserve" if reserve else "primary"
    rank = sequence + 1
    seed = (2026083100 if not reserve else 2026083200) + rank
    layout = _layout(permutation_index)
    display = list(_DISPLAY_PERMUTATIONS[permutation_index])
    value = {
        "schema_version": "cmf_f1_batch_pilot_root_spec_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "slot_id": f"f1-batch-pilot-v1-{kind}-{rank:02d}",
        "family": "F1",
        "arm": "left",
        "seed": seed,
        "generator": "controlled_multi_future_f1_batch_pilot_adapter_v1",
        "origin": "post_stage0_f1_batch_generation_development_pilot",
        "rank": rank,
        "slot_kind": kind,
        "activation_status": "pending_activation" if reserve else "active",
        "scene_layout": layout,
        "scene_layout_sha256": layout["layout_sha256"],
        "candidate_display_order": display,
        "candidate_display_order_sha256": hash_json(display),
        "program_ids": list(PROGRAM_IDS),
        "realization": "r_pc",
        "trajectories_if_accepted": 3,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_root_invocations": 1,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "accepted_root_increment": 0,
        "stop_condition": "terminal three-branch receipt or first safety/source/cleanup uncertainty",
    }
    value["planned_root_slot_spec_sha256"] = hash_json(value)
    return value


def build_f1_batch_pilot_plan_v1() -> dict[str, Any]:
    primaries = [_root_spec(sequence=index, reserve=False) for index in range(5)]
    reserves = [_root_spec(sequence=index, reserve=True) for index in range(5)]
    value = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "target_accepted_root_count": PRIMARY_ROOT_COUNT,
        "target_trajectory_count": 15,
        "trajectories_per_root": 3,
        "realization": "r_pc",
        "primary_slots": primaries,
        "ordered_reserve_slots": reserves,
        "reserve_activation_rule": "activate next rank only after a terminal failed active slot; preserve every failure",
        "selection_rule": "stop after five accepted development roots or reserve exhaustion",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "training_authorized": False,
    }
    value["plan_sha256"] = hash_json(value)
    return value


def validate_f1_batch_pilot_plan_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    plan = deepcopy(dict(value))
    digest = plan.pop("plan_sha256", None)
    primaries = plan.get("primary_slots", [])
    reserves = plan.get("ordered_reserve_slots", [])
    all_slots: Sequence[Mapping[str, Any]] = [*primaries, *reserves]
    slot_hashes = []
    for item in all_slots:
        payload = dict(item)
        claimed = payload.pop("planned_root_slot_spec_sha256", None)
        slot_hashes.append(isinstance(claimed, str) and hash_json(payload) == claimed)
    checks = {
        "schema": plan.get("schema_version") == SCHEMA_VERSION,
        "counts": len(primaries) == 5 and len(reserves) == 5,
        "target": plan.get("target_accepted_root_count") == 5
        and plan.get("target_trajectory_count") == 15,
        "self_hash": isinstance(digest, str) and hash_json(plan) == digest,
        "slot_hashes": len(slot_hashes) == 10 and all(slot_hashes),
        "unique_slot_ids": len({item.get("slot_id") for item in all_slots}) == 10,
        "unique_seeds": len({item.get("seed") for item in all_slots}) == 10,
        "primary_layout_rotation": len(
            {item.get("scene_layout_sha256") for item in primaries}
        ) == 5,
        "primary_display_rotation": len(
            {item.get("candidate_display_order_sha256") for item in primaries}
        ) == 5,
        "candidate_permutations": all(
            set(item.get("candidate_display_order", [])) == set(PROGRAM_IDS)
            for item in all_slots
        ),
        "development_only": all(
            item.get("formal_data") is False
            and item.get("stage0_data") is False
            and item.get("stage1_authorized") is False
            and item.get("accepted_root_increment") == 0
            for item in all_slots
        ),
        "single_attempt": all(
            item.get("automatic_retry") is False
            and item.get("recovery_attempts") == 0
            and item.get("maximum_root_invocations") == 1
            for item in all_slots
        ),
    }
    return {"checks": checks, "pass": all(checks.values())}


__all__ = [
    "IMPLEMENTATION_VERSION",
    "PROGRAM_IDS",
    "build_f1_batch_pilot_plan_v1",
    "validate_f1_batch_pilot_plan_v1",
]
