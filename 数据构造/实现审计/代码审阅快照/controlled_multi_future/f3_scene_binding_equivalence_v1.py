"""F3 nominal-scene identity and post-settle physical-equivalence audit.

The manifest binds the deterministic scene construction.  A dynamic bottle is
allowed to settle by a small, explicitly reported amount before planning; the
settled floating-point pose is evidence, not a byte-identical scene identity.
This module does not authorize GPU, planner, physical, or data execution.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_f3_scene_binding_equivalence_v1"
BOTTLE_POSITION_ATOL_M = 0.010
BOTTLE_ORIENTATION_ATOL_RAD = 0.200
FIXTURE_POSITION_ATOL_M = 1.0e-6
FIXTURE_ORIENTATION_ATOL_RAD = 1.0e-6


def _pose7(value: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite pose7")
    norm = float(np.linalg.norm(result[3:]))
    if norm <= 1.0e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    result = result.copy()
    result[3:] /= norm
    return result


def _pose_errors(actual: Sequence[float], expected: Sequence[float]) -> dict[str, float]:
    left = _pose7(actual, "actual pose")
    right = _pose7(expected, "expected pose")
    return {
        "position_error_m": float(np.linalg.norm(left[:3] - right[:3])),
        "orientation_error_rad": float(
            quaternion_angular_error(left[3:], right[3:])
        ),
    }


def audit_f3_scene_binding_equivalence_v1(
    *,
    recipe: Mapping[str, Any],
    expected_scene_binding: Mapping[str, Any],
    actual_scene_binding: Mapping[str, Any],
    actual_bottle_pose: Sequence[float],
    actual_pad_pose: Sequence[float],
    actual_marker_pose: Sequence[float],
    scene_seed: int,
    scene_instance_id: str | None,
    canonical_settle_steps: int,
    actor_sleep_state: bool | None,
    contact_state: Mapping[str, Any],
    runtime_asset: Mapping[str, Any] | None,
    runtime_tuple: Mapping[str, Any] | None,
) -> dict[str, Any]:
    value_recipe = canonical_jsonable(recipe)
    expected = canonical_jsonable(expected_scene_binding)
    actual = canonical_jsonable(actual_scene_binding)
    source_x = -0.18 if value_recipe.get("arm") == "left" else 0.18
    expected_bottle = [source_x, -0.06, 0.785, 0.0, 0.0, 1.0, 0.0]
    expected_pad = [source_x, -0.06, 0.745, 1.0, 0.0, 0.0, 0.0]
    expected_marker = [0.0, -0.05, 0.95, 1.0, 0.0, 0.0, 0.0]
    bottle_error = _pose_errors(actual_bottle_pose, expected_bottle)
    pad_error = _pose_errors(actual_pad_pose, expected_pad)
    marker_error = _pose_errors(actual_marker_pose, expected_marker)
    runtime_asset_value = (
        canonical_jsonable(runtime_asset) if isinstance(runtime_asset, Mapping) else {}
    )
    runtime_tuple_value = (
        canonical_jsonable(runtime_tuple) if isinstance(runtime_tuple, Mapping) else {}
    )
    asset = value_recipe.get("asset", {})
    contact = canonical_jsonable(contact_state)
    exact_identity_checks = {
        "expected_asset_record_bound": expected.get("bottle_asset_sha256")
        == value_recipe.get("asset_record_sha256"),
        "runtime_asset_model_bound": runtime_asset_value.get("modelname")
        == asset.get("modelname")
        and runtime_asset_value.get("model_id") == asset.get("model_id"),
        "runtime_actor_name_bound": runtime_asset_value.get("actor_name")
        == "f3_main_bottle",
        "runtime_tuple_asset_bound": runtime_tuple_value.get("asset") == asset,
        "runtime_tuple_arm_bound": runtime_tuple_value.get("arm")
        == value_recipe.get("arm"),
        "scene_seed_is_integer": isinstance(scene_seed, int),
        "canonical_settle_is_60_steps": int(canonical_settle_steps) == 60,
    }
    physical_equivalence_checks = {
        "bottle_position_within_10mm": bottle_error["position_error_m"]
        <= BOTTLE_POSITION_ATOL_M,
        "bottle_orientation_within_200mrad": bottle_error[
            "orientation_error_rad"
        ]
        <= BOTTLE_ORIENTATION_ATOL_RAD,
        "pad_position_within_1um": pad_error["position_error_m"]
        <= FIXTURE_POSITION_ATOL_M,
        "pad_orientation_within_1urad": pad_error["orientation_error_rad"]
        <= FIXTURE_ORIENTATION_ATOL_RAD,
        "marker_position_within_1um": marker_error["position_error_m"]
        <= FIXTURE_POSITION_ATOL_M,
        "marker_orientation_within_1urad": marker_error[
            "orientation_error_rad"
        ]
        <= FIXTURE_ORIENTATION_ATOL_RAD,
        "bottle_sleep_state_true": actor_sleep_state is True,
        "contact_api_available": contact.get("contact_api_available") is True,
        "bottle_supported_by_pad": contact.get("bottle_pad_contact") is True,
        "bottle_not_directly_on_table": contact.get("bottle_table_contact") is False,
    }
    checks = {**exact_identity_checks, **physical_equivalence_checks}
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "scene_seed": int(scene_seed),
        "scene_instance_id": scene_instance_id,
        "canonical_settle_steps": int(canonical_settle_steps),
        "asset_model_id": asset.get("model_id"),
        "expected_scene_binding": expected,
        "actual_scene_binding_observation": actual,
        "expected_bottle_pose": expected_bottle,
        "actual_bottle_pose": canonical_jsonable(actual_bottle_pose),
        "expected_pad_pose": expected_pad,
        "actual_pad_pose": canonical_jsonable(actual_pad_pose),
        "expected_marker_pose": expected_marker,
        "actual_marker_pose": canonical_jsonable(actual_marker_pose),
        "bottle_pose_error": bottle_error,
        "pad_pose_error": pad_error,
        "marker_pose_error": marker_error,
        "position_delta_xyz": (
            _pose7(actual_bottle_pose, "actual bottle")[:3]
            - np.asarray(expected_bottle[:3], dtype=np.float64)
        ).tolist(),
        "position_error_m": bottle_error["position_error_m"],
        "orientation_error_rad": bottle_error["orientation_error_rad"],
        "tolerances": {
            "bottle_position_atol_m": BOTTLE_POSITION_ATOL_M,
            "bottle_orientation_atol_rad": BOTTLE_ORIENTATION_ATOL_RAD,
            "fixture_position_atol_m": FIXTURE_POSITION_ATOL_M,
            "fixture_orientation_atol_rad": FIXTURE_ORIENTATION_ATOL_RAD,
        },
        "actor_sleep_state": actor_sleep_state,
        "table_pad_contact_state": contact,
        "runtime_asset": runtime_asset_value,
        "runtime_tuple": runtime_tuple_value,
        "exact_identity_checks": exact_identity_checks,
        "physical_equivalence_checks": physical_equivalence_checks,
        "checks": checks,
        "exact_post_settle_pose_equality_required": False,
        "planned_scene_identity_preserved": all(exact_identity_checks.values()),
        "post_settle_physical_equivalence_pass": all(
            physical_equivalence_checks.values()
        ),
        "pass": all(checks.values()),
        "failure_class": None if all(checks.values()) else "INFRASTRUCTURE_ERROR",
        "failure_code": None
        if all(checks.values())
        else "F3_ACTUAL_SCENE_BINDING_NOT_PHYSICALLY_EQUIVALENT",
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    receipt["receipt_sha256"] = canonical_hash_json(receipt)
    return receipt


__all__ = [
    "BOTTLE_ORIENTATION_ATOL_RAD",
    "BOTTLE_POSITION_ATOL_M",
    "FIXTURE_ORIENTATION_ATOL_RAD",
    "FIXTURE_POSITION_ATOL_M",
    "SCHEMA_VERSION",
    "audit_f3_scene_binding_equivalence_v1",
]
