"""Pure, proposal-only F3 pre-close physical-consistency Gate.

This module does not create a scene, call a planner, initialize CUDA, or write
an artifact.  It evaluates already-realized pregrasp/grasp snapshots and
fails closed before any gripper-close command can be authorized.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from controlled_multi_future.f3_physical_contact_signal_v8 import (
    classify_contact_pair_physical_hit_v8,
)


SCHEMA_VERSION = "cmf_f3_preclose_physical_consistency_gate_v1"
IMPLEMENTATION_VERSION = "f3_preclose_physical_consistency_gate_v1"
ALLOWED_STAGES = ("pregrasp", "grasp")

# Existing implementation thresholds; no threshold is relaxed or invented.
EEF_POSITION_ERROR_LIMIT_M = 0.030
EEF_ORIENTATION_ERROR_LIMIT_RAD = 0.020
SELECTED_ARM_QPOS_ERROR_LIMIT_RAD = 0.10
BOTTLE_PRECLOSE_DISPLACEMENT_LIMIT_M = 0.010

FAILURE_PRIORITY = (
    "wrong_arm_or_action_routing",
    "contact_signal_incomplete",
    "executing_arm_self_collision",
    "executing_arm_support_collision",
    "premature_or_unexpected_arm_bottle_contact",
    "bottle_displaced_before_close",
    "selected_arm_qpos_tracking_failed",
    "eef_tracking_failed",
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _array(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    try:
        result = result.reshape(shape)
    except ValueError as exc:
        raise ValueError(f"{label} must have shape {shape}") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{label} contains non-finite values")
    return result


def _quaternion_angular_error(first: Sequence[float], second: Sequence[float]) -> float:
    a = _array(first, (4,), "realized EEF quaternion")
    b = _array(second, (4,), "planner-goal EEF quaternion")
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a <= 0.0 or norm_b <= 0.0:
        raise ValueError("EEF quaternion norm must be positive")
    dot = min(1.0, abs(float(np.dot(a / norm_a, b / norm_b))))
    return float(2.0 * math.acos(dot))


def _arm_prefix(arm: str) -> str:
    if arm == "left":
        return "fl_"
    if arm == "right":
        return "fr_"
    raise ValueError("arm must be exactly 'left' or 'right'")


def _is_executing_arm_body(name: Any, arm: str) -> bool:
    return isinstance(name, str) and name.startswith(_arm_prefix(arm))


def _contact_audit(
    contact_pairs: Sequence[Mapping[str, Any]],
    *,
    arm: str,
    stage: str,
    selected_gripper_links: Sequence[str],
    bottle_actor_name: str,
    support_actor_names: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(contact_pairs, (list, tuple)):
        raise TypeError("contact_pairs must be a sequence")
    selected = {str(value) for value in selected_gripper_links}
    supports = {str(value) for value in support_actor_names}
    if not selected or not supports:
        raise ValueError("selected gripper links and support actors must be non-empty")

    relevant = []
    incomplete = []
    self_hits = []
    support_hits = []
    unexpected_bottle_hits = []
    allowed_bottle_hits = []
    for pair_index, raw_pair in enumerate(contact_pairs):
        if not isinstance(raw_pair, Mapping):
            raise TypeError("each contact pair must be a mapping")
        body_a = raw_pair.get("body_a")
        body_b = raw_pair.get("body_b")
        bodies = {str(body_a), str(body_b)}
        arm_bodies = {
            body for body in bodies if _is_executing_arm_body(body, arm)
        }
        if not arm_bodies:
            continue
        is_self = len(arm_bodies) == 2
        is_support = bool(bodies & supports)
        is_bottle = bottle_actor_name in bodies
        if not (is_self or is_support or is_bottle):
            continue
        signal = classify_contact_pair_physical_hit_v8(raw_pair)
        row = {
            "pair_index": int(pair_index),
            "body_a": body_a,
            "body_b": body_b,
            "category": (
                "self" if is_self else "support" if is_support else "bottle"
            ),
            "evidence_complete": signal["evidence_complete"],
            "physical_hit_for_gate": signal["physical_hit_for_gate"],
            "observed_physical_contact": signal["observed_physical_contact"],
            "impulse_norm_sum": signal["impulse_norm_sum"],
            "minimum_signed_separation_m": signal["minimum_signed_separation_m"],
            "physical_contact_reasons": signal["physical_contact_reasons"],
            "pair_signal_receipt_sha256": signal["receipt_sha256"],
        }
        relevant.append(row)
        if signal["evidence_complete"] is not True:
            incomplete.append(row)
        if signal["physical_hit_for_gate"] is not True:
            continue
        if is_self:
            self_hits.append(row)
        elif is_support:
            support_hits.append(row)
        else:
            allowed = bool(stage == "grasp" and arm_bodies.issubset(selected))
            if allowed:
                allowed_bottle_hits.append(row)
            else:
                unexpected_bottle_hits.append(row)

    return {
        "relevant_pair_count": len(relevant),
        "relevant_pairs": relevant,
        "incomplete_signal_pairs": incomplete,
        "executing_arm_self_collision_hits": self_hits,
        "executing_arm_support_collision_hits": support_hits,
        "unexpected_arm_bottle_hits": unexpected_bottle_hits,
        "allowed_selected_gripper_bottle_hits": allowed_bottle_hits,
        "pair_presence_alone_is_not_physical_contact": True,
    }


def evaluate_preclose_stage(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one realized pregrasp or grasp boundary.

    The caller remains responsible for ensuring this function is called before
    close.  The returned ``close_allowed`` is the only authorization signal.
    """

    if not isinstance(snapshot, Mapping):
        raise TypeError("pre-close snapshot must be a mapping")
    stage = snapshot.get("stage")
    if stage not in ALLOWED_STAGES:
        raise ValueError(f"stage must be one of {ALLOWED_STAGES}")
    arm = str(snapshot.get("arm"))
    _arm_prefix(arm)

    planned_qpos = _array(
        snapshot.get("planned_selected_arm_qpos"),
        (6,),
        "planned selected-arm qpos",
    )
    realized_qpos = _array(
        snapshot.get("realized_selected_arm_qpos"),
        (6,),
        "realized selected-arm qpos",
    )
    goal_eef = _array(snapshot.get("planner_goal_eef_pose"), (7,), "planner goal EEF")
    realized_eef = _array(snapshot.get("realized_eef_pose"), (7,), "realized EEF")
    initial_bottle = _array(
        snapshot.get("initial_bottle_position_m"),
        (3,),
        "initial bottle position",
    )
    realized_bottle = _array(
        snapshot.get("realized_bottle_position_m"),
        (3,),
        "realized bottle position",
    )

    qpos_max_error = float(np.max(np.abs(realized_qpos - planned_qpos)))
    eef_position_error = float(
        np.linalg.norm(realized_eef[:3] - goal_eef[:3])
    )
    eef_orientation_error = _quaternion_angular_error(
        realized_eef[3:], goal_eef[3:]
    )
    bottle_displacement = float(
        np.linalg.norm(realized_bottle - initial_bottle)
    )
    contacts = _contact_audit(
        snapshot.get("contact_pairs", []),
        arm=arm,
        stage=stage,
        selected_gripper_links=snapshot.get("selected_gripper_links", []),
        bottle_actor_name=str(snapshot.get("bottle_actor_name", "")),
        support_actor_names=snapshot.get("support_actor_names", []),
    )

    checks = {
        "selected_arm_commanded": snapshot.get("selected_arm_commanded") is True,
        "opposite_arm_not_commanded": snapshot.get("opposite_arm_commanded") is False,
        "selected_arm_qpos_tracking": qpos_max_error
        <= SELECTED_ARM_QPOS_ERROR_LIMIT_RAD,
        "eef_position_tracking": eef_position_error <= EEF_POSITION_ERROR_LIMIT_M,
        "eef_orientation_tracking": eef_orientation_error
        <= EEF_ORIENTATION_ERROR_LIMIT_RAD,
        "contact_signal_complete": not contacts["incomplete_signal_pairs"],
        "no_executing_arm_self_collision": not contacts[
            "executing_arm_self_collision_hits"
        ],
        "no_executing_arm_support_collision": not contacts[
            "executing_arm_support_collision_hits"
        ],
        "no_premature_or_unexpected_arm_bottle_contact": not contacts[
            "unexpected_arm_bottle_hits"
        ],
        "bottle_not_displaced_before_close": bottle_displacement
        <= BOTTLE_PRECLOSE_DISPLACEMENT_LIMIT_M,
    }
    failures = []
    if not checks["selected_arm_commanded"] or not checks[
        "opposite_arm_not_commanded"
    ]:
        failures.append("wrong_arm_or_action_routing")
    if not checks["contact_signal_complete"]:
        failures.append("contact_signal_incomplete")
    if not checks["no_executing_arm_self_collision"]:
        failures.append("executing_arm_self_collision")
    if not checks["no_executing_arm_support_collision"]:
        failures.append("executing_arm_support_collision")
    if not checks["no_premature_or_unexpected_arm_bottle_contact"]:
        failures.append("premature_or_unexpected_arm_bottle_contact")
    if not checks["bottle_not_displaced_before_close"]:
        failures.append("bottle_displaced_before_close")
    if not checks["selected_arm_qpos_tracking"]:
        failures.append("selected_arm_qpos_tracking_failed")
    if not checks["eef_position_tracking"] or not checks[
        "eef_orientation_tracking"
    ]:
        failures.append("eef_tracking_failed")
    ordered_failures = [name for name in FAILURE_PRIORITY if name in failures]
    passed = not ordered_failures and all(checks.values())

    result = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage": stage,
        "arm": arm,
        "thresholds": {
            "selected_arm_qpos_max_error_rad": SELECTED_ARM_QPOS_ERROR_LIMIT_RAD,
            "eef_position_error_m": EEF_POSITION_ERROR_LIMIT_M,
            "eef_orientation_error_rad": EEF_ORIENTATION_ERROR_LIMIT_RAD,
            "bottle_preclose_displacement_m": BOTTLE_PRECLOSE_DISPLACEMENT_LIMIT_M,
        },
        "measurements": {
            "selected_arm_qpos_max_error_rad": qpos_max_error,
            "eef_position_error_m": eef_position_error,
            "eef_orientation_error_rad": eef_orientation_error,
            "bottle_preclose_displacement_m": bottle_displacement,
        },
        "checks": checks,
        "contact_audit": contacts,
        "failure_codes": ordered_failures,
        "earliest_failure_code": ordered_failures[0] if ordered_failures else None,
        "pass": passed,
        "close_allowed": passed,
        "stop_before_close": not passed,
        "formal_data": False,
        "stage1_authorized": False,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def evaluate_preclose_sequence(
    pregrasp_snapshot: Mapping[str, Any],
    grasp_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    pregrasp = evaluate_preclose_stage(pregrasp_snapshot)
    grasp = evaluate_preclose_stage(grasp_snapshot)
    if pregrasp["stage"] != "pregrasp" or grasp["stage"] != "grasp":
        raise ValueError("pre-close sequence must be pregrasp then grasp")
    if pregrasp["arm"] != grasp["arm"]:
        raise ValueError("pregrasp/grasp arm identity changed")
    first = pregrasp if pregrasp["pass"] is not True else grasp
    passed = pregrasp["pass"] is True and grasp["pass"] is True
    result = {
        "schema_version": "cmf_f3_preclose_physical_consistency_sequence_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "arm": pregrasp["arm"],
        "stage_receipts": [pregrasp, grasp],
        "earliest_failure_stage": None if passed else first["stage"],
        "earliest_failure_code": None if passed else first["earliest_failure_code"],
        "pass": passed,
        "close_allowed": passed,
        "stop_before_close": not passed,
        "lift_allowed": False,
        "shared_v_allowed": False,
        "root_allowed": False,
        "raw_allowed": False,
        "formal_data": False,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def gate_contract() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f3_preclose_physical_consistency_contract_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "ordered_stages": list(ALLOWED_STAGES),
        "failure_priority": list(FAILURE_PRIORITY),
        "thresholds": {
            "selected_arm_qpos_max_error_rad": SELECTED_ARM_QPOS_ERROR_LIMIT_RAD,
            "eef_position_error_m": EEF_POSITION_ERROR_LIMIT_M,
            "eef_orientation_error_rad": EEF_ORIENTATION_ERROR_LIMIT_RAD,
            "bottle_preclose_displacement_m": BOTTLE_PRECLOSE_DISPLACEMENT_LIMIT_M,
        },
        "contact_classifier": "controlled_multi_future.f3_physical_contact_signal_v8",
        "pair_presence_is_audit_only": True,
        "failure_semantics": "any failed check stops before gripper close",
        "gpu_execution_authorized": False,
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["contract_sha256"] = canonical_hash(value)
    return value


__all__ = [
    "ALLOWED_STAGES",
    "BOTTLE_PRECLOSE_DISPLACEMENT_LIMIT_M",
    "EEF_ORIENTATION_ERROR_LIMIT_RAD",
    "EEF_POSITION_ERROR_LIMIT_M",
    "IMPLEMENTATION_VERSION",
    "SELECTED_ARM_QPOS_ERROR_LIMIT_RAD",
    "canonical_hash",
    "evaluate_preclose_sequence",
    "evaluate_preclose_stage",
    "gate_contract",
]
