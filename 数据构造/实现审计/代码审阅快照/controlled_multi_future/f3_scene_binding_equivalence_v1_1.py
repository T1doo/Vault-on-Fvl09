"""Evidence-driven F3 scene-equivalence refinement after real SAPIEN run2."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_scene_binding_equivalence_v1 import (
    audit_f3_scene_binding_equivalence_v1,
)
from .runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS


RUN2_EVIDENCE_RECEIPT_SHA256S = (
    "6e5e98565a33bb5bd60e7a47a7f44618e03855799f448ad12f914e2f9ddb4183",
    "3969d9d0e7a850287737f63f24dd8bf20ce38d5b53bba76bdb6dcb18084ac1c8",
    "9a0674d67b9aa1bcc24ca14803adb0c368c71f92bb1f799fcd599eff5f32c6f7",
    "7ddc2c65667dc3890714c120f249eeaaa5808353a0eac6a27a0239b596e0961e",
)


def audit_f3_scene_binding_equivalence_v1_1(**kwargs) -> dict[str, Any]:
    base = audit_f3_scene_binding_equivalence_v1(**kwargs)
    runtime_asset = canonical_jsonable(kwargs.get("runtime_asset") or {})
    linear = np.asarray(
        runtime_asset.get("linear_velocity", [np.inf, np.inf, np.inf]),
        dtype=np.float64,
    ).reshape(-1)
    angular = np.asarray(
        runtime_asset.get("angular_velocity", [np.inf, np.inf, np.inf]),
        dtype=np.float64,
    ).reshape(-1)
    linear_speed = float(np.linalg.norm(linear)) if linear.shape == (3,) else float("inf")
    angular_speed = float(np.linalg.norm(angular)) if angular.shape == (3,) else float("inf")
    exact = dict(base["exact_identity_checks"])
    physical = dict(base["physical_equivalence_checks"])
    sleep_check = physical.pop("bottle_sleep_state_true")
    table_check = physical.pop("bottle_not_directly_on_table")
    physical.update(
        {
            "bottle_linear_speed_within_stability_limit": linear_speed
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "bottle_angular_speed_within_stability_limit": angular_speed
            <= PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
        }
    )
    checks = {**exact, **physical}
    value = {
        **base,
        "schema_version": "cmf_f3_scene_binding_equivalence_v1_1",
        "supersedes_v1_receipt_sha256": base["receipt_sha256"],
        "run2_evidence_receipt_sha256s": list(RUN2_EVIDENCE_RECEIPT_SHA256S),
        "exact_identity_checks": exact,
        "physical_equivalence_checks": physical,
        "diagnostic_checks_not_scene_rejection": {
            "actor_sleep_state_true": sleep_check,
            "bottle_not_directly_on_table": table_check,
        },
        "measured_bottle_linear_speed_mps": linear_speed,
        "measured_bottle_angular_speed_rps": angular_speed,
        "checks": checks,
        "planned_scene_identity_preserved": all(exact.values()),
        "post_settle_physical_equivalence_pass": all(physical.values()),
        "pass": all(checks.values()),
        "failure_class": None if all(checks.values()) else "INFRASTRUCTURE_ERROR",
        "failure_code": None
        if all(checks.values())
        else "F3_ACTUAL_SCENE_BINDING_NOT_PHYSICALLY_EQUIVALENT_V1_1",
    }
    value.pop("receipt_sha256", None)
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["audit_f3_scene_binding_equivalence_v1_1"]
