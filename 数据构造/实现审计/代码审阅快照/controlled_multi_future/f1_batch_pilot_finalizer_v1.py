"""Deterministic reserve activation and final report for F1 batch pilot."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json as hash_json
from .f1_batch_generation_pilot_v1 import validate_f1_batch_pilot_plan_v1


def build_reserve_activation_receipt_v1(
    *,
    plan: Mapping[str, Any],
    failed_slot_id: str,
    prior_activations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    audit = validate_f1_batch_pilot_plan_v1(plan)
    if not audit["pass"]:
        raise ValueError("F1 batch plan is invalid")
    primaries = {item["slot_id"]: item for item in plan["primary_slots"]}
    reserves = list(plan["ordered_reserve_slots"])
    if failed_slot_id not in primaries and failed_slot_id not in {
        item.get("reserve_slot_id") for item in prior_activations
    }:
        raise ValueError("failed slot is not active in the frozen plan")
    expected_rank = len(prior_activations) + 1
    if expected_rank > len(reserves):
        raise ValueError("F1 ordered reserve slots are exhausted")
    reserve = reserves[expected_rank - 1]
    if any(item.get("reserve_slot_id") == reserve["slot_id"] for item in prior_activations):
        raise ValueError("F1 reserve slot was already activated")
    value = {
        "schema_version": "cmf_f1_batch_pilot_reserve_activation_v1",
        "plan_sha256": plan["plan_sha256"],
        "failed_slot_id": failed_slot_id,
        "reserve_rank": expected_rank,
        "reserve_slot_id": reserve["slot_id"],
        "reserve_planned_root_slot_spec_sha256": reserve[
            "planned_root_slot_spec_sha256"
        ],
        "activation_reason": "terminal_failed_development_root",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["activation_receipt_sha256"] = hash_json(value)
    return value


def _validate_activation_sequence(
    plan: Mapping[str, Any], activations: Sequence[Mapping[str, Any]]
) -> bool:
    prior: list[Mapping[str, Any]] = []
    try:
        for item in activations:
            expected = build_reserve_activation_receipt_v1(
                plan=plan,
                failed_slot_id=str(item.get("failed_slot_id")),
                prior_activations=prior,
            )
            if dict(item) != expected:
                return False
            prior.append(item)
    except (TypeError, ValueError):
        return False
    return True


def finalize_f1_batch_pilot_v1(
    *,
    plan: Mapping[str, Any],
    root_receipts: Mapping[str, Mapping[str, Any]],
    reserve_activations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    plan_audit = validate_f1_batch_pilot_plan_v1(plan)
    primaries = [item["slot_id"] for item in plan.get("primary_slots", [])]
    activated = [item.get("reserve_slot_id") for item in reserve_activations]
    allowed_attempts = set(primaries + activated)
    receipts = deepcopy(dict(root_receipts))
    receipt_hash_pass = {}
    for slot_id, receipt in receipts.items():
        payload = dict(receipt)
        claimed = payload.pop("receipt_sha256", None)
        receipt_hash_pass[slot_id] = isinstance(claimed, str) and hash_json(payload) == claimed
    accepted = sorted(
        slot_id
        for slot_id, receipt in receipts.items()
        if receipt.get("accepted_development_root") is True
        and receipt.get("pass") is True
    )
    failed = sorted(set(receipts) - set(accepted))
    planner_failures: dict[str, int] = {}
    for slot_id in failed:
        status = str(receipts[slot_id].get("root_status", "missing_status"))
        planner_failures[status] = planner_failures.get(status, 0) + 1
    elapsed = [
        float(item["elapsed_seconds"])
        for item in receipts.values()
        if isinstance(item.get("elapsed_seconds"), (int, float))
    ]
    terminal = len(accepted) >= 5 or (
        len(reserve_activations) == len(plan.get("ordered_reserve_slots", []))
        and set(allowed_attempts).issubset(receipts)
    )
    checks = {
        "plan": plan_audit["pass"],
        "activation_sequence": _validate_activation_sequence(
            plan, reserve_activations
        ),
        "all_primaries_attempted": set(primaries).issubset(receipts),
        "only_active_slots_attempted": set(receipts).issubset(allowed_attempts),
        "receipt_hashes": bool(receipt_hash_pass)
        and all(receipt_hash_pass.values()),
        "accepted_count_bounded": len(accepted) <= 5,
        "terminal_stop": terminal,
        "development_only": all(
            item.get("formal_data") is False
            and item.get("stage0_data") is False
            and item.get("stage1_authorized") is False
            and item.get("accepted_root_increment") == 0
            for item in receipts.values()
        ),
    }
    result = {
        "schema_version": "cmf_f1_batch_generation_pilot_v1_report",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_f1_batch_pilot_v1",
        "status": "COMPLETED_FIVE_ACCEPTED_ROOTS"
        if len(accepted) == 5
        else "COMPLETED_RESERVE_EXHAUSTED"
        if terminal
        else "INCOMPLETE",
        "plan_sha256": plan.get("plan_sha256"),
        "attempted_root_count": len(receipts),
        "accepted_root_count": len(accepted),
        "failed_root_count": len(failed),
        "accepted_trajectory_count": sum(
            int(receipts[slot_id].get("trajectory_count", 0))
            for slot_id in accepted
        ),
        "root_success_rate": len(accepted) / len(receipts) if receipts else 0.0,
        "accepted_root_ids": accepted,
        "failed_root_ids": failed,
        "reserve_activations": deepcopy(list(reserve_activations)),
        "planner_failure_distribution": planner_failures,
        "per_root_elapsed_seconds": {
            slot_id: receipt.get("elapsed_seconds")
            for slot_id, receipt in receipts.items()
        },
        "mean_attempted_root_elapsed_seconds": sum(elapsed) / len(elapsed)
        if elapsed
        else None,
        "checks": checks,
        "pass": all(checks.values()) and len(accepted) == 5,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "formal_trajectory_increment": 0,
    }
    result["report_sha256"] = hash_json(result)
    return result


__all__ = [
    "build_reserve_activation_receipt_v1",
    "finalize_f1_batch_pilot_v1",
]
