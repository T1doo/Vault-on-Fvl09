"""Honest semantics for MotionGen reset receipts used by planner qualification."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable


def bind_planner_reset_nonce_v1(
    raw_reset_receipt: Mapping[str, Any], *, planner_reset_nonce: int
) -> dict[str, Any]:
    raw = canonical_jsonable(raw_reset_receipt)
    nonce = int(planner_reset_nonce)
    reset_seed_argument = raw.get("reset_evidence", {}).get(
        "reset_seed_argument", raw.get("reset_seed_argument")
    )
    if (
        raw.get("reset_performed") is not True
        or int(raw.get("planner_seed", -1)) != nonce
        or reset_seed_argument is not True
    ):
        raise ValueError("planner reset receipt is not bound to the audit nonce")
    value = {
        "schema_version": "cmf_planner_reset_nonce_receipt_v1",
        "planner_reset_nonce": nonce,
        "motiongen_reset_seed_argument": True,
        "reset_receipt_bound_to_authorization": True,
        "numeric_rng_seed_application_proven": False,
        "bitwise_determinism_claimed": False,
        "underlying_reset_receipt": raw,
        "underlying_reset_receipt_sha256": canonical_hash_json(raw),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["bind_planner_reset_nonce_v1"]
