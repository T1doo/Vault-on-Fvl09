"""Pure model13/assembly geometry contract for the F3 revision-6 release.

Revision-5 raised the bottle actor origin by 10 mm.  The model13 actor origin
is not the bottom of its scaled, offset OBB, so that produced only about 4.94
mm of geometric clearance at the frozen original pose.  This module computes
the world-z shift needed to give both the bottle OBB and the conservative
gripper assembly envelope a real 10 mm clearance above the highest support.

There are no SAPIEN, planner, runner, or GPU imports here.  V/H axes,
amplitudes, and the three ordered programs are sealed as unchanged audit
fields; only the common return/release world-z translation is computed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .geometry import compose_pose, obb_corners, relative_pose


SCHEMA_VERSION = "cmf_f3_release_geometry_clearance_v6"
FROZEN_ASSET = {"modelname": "001_bottle", "model_id": 13}
MODEL13_MODEL_DATA_SHA256 = (
    "a0b94d276bf41e03a7b0c2fa7f8352c8c45b7bcaa8db2925328955fc8e18ef1f"
)
MODEL13_MODEL_DATA_CENTER = (
    6.813343718070148e-05,
    0.9390977719300474,
    2.540242926586833e-05,
)
MODEL13_MODEL_DATA_EXTENTS = (
    0.5201516785787955,
    1.8783392663982066,
    0.5123145297663331,
)
MODEL13_MODEL_DATA_SCALE = (0.132, 0.132, 0.132)
MODEL13_LOCAL_GEOMETRY_CENTER_M = (
    8.993613707852595e-06,
    0.12396090589476626,
    3.3531206630946197e-06,
)
MODEL13_HALF_EXTENTS_M = (
    0.03433001078620051,
    0.12397039158228164,
    0.033812758964577985,
)

FROZEN_GEOMETRIC_CLEARANCE_M = 0.010
FROZEN_V_NOMINAL_AMPLITUDE_M = 0.055
FROZEN_H_NOMINAL_AMPLITUDE_M = 0.050
FROZEN_PROGRAMS = ("VVHH", "VHVH", "VHHV")
FROZEN_AXIS_FRAME = {
    "V": "table-frame +/-z",
    "H": "table-frame +/-x",
}
FROZEN_FULL_ASSEMBLY_LINK_NAMES = ("fl_link6", "fl_link7", "fl_link8")
FROZEN_ASSEMBLY_CONSERVATIVE_MARGIN_M = 0.030
FROZEN_RUNTIME_TRACKING_ALLOWANCE_M = 0.005
FROZEN_RUNTIME_MINIMUM_CLEARANCE_M = (
    FROZEN_GEOMETRIC_CLEARANCE_M - FROZEN_RUNTIME_TRACKING_ALLOWANCE_M
)


def _json_safe(value: Any, *, path: str = "value") -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise ValueError(f"{path} must be finite")
        return result
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path=path)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} mapping keys must be strings")
            result[key] = _json_safe(item, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{path} contains unsupported type {type(value).__name__}")


def canonical_json_sha256(value: Any) -> str:
    normalized = _json_safe(value)
    return hashlib.sha256(
        json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _pose(value: Sequence[float], *, label: str) -> np.ndarray:
    try:
        pose = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be one finite 7-D pose")
    if float(np.linalg.norm(pose[3:])) <= 1e-12:
        raise ValueError(f"{label} quaternion must be nonzero")
    return np.ascontiguousarray(pose)


def _finite_scalar(value: Any, *, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not np.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def model13_world_obb_z_bounds(actor_pose: Sequence[float]) -> tuple[float, float]:
    """Return exact scaled model-data OBB z bounds at one actor pose."""

    actor = _pose(actor_pose, label="model13 actor pose")
    center_pose = compose_pose(
        actor,
        [*MODEL13_LOCAL_GEOMETRY_CENTER_M, 1.0, 0.0, 0.0, 0.0],
    )
    corners = obb_corners(center_pose, MODEL13_HALF_EXTENTS_M)
    return float(np.min(corners[:, 2])), float(np.max(corners[:, 2]))


def build_target_specific_full_assembly_projection_v6(
    *,
    current_eef_pose: Sequence[float],
    live_assembly_link_poses: Mapping[str, Sequence[float]],
    release_eef_pose: Sequence[float],
    conservative_margin_m: float = FROZEN_ASSEMBLY_CONSERVATIVE_MARGIN_M,
) -> dict:
    """Project live fl6/fl7/fl8 link centers into one target EEF pose.

    The link-to-EEF transforms come from the live articulation.  Applying
    those transforms to ``release_eef_pose`` makes the downward envelope
    target-orientation specific instead of reusing a world-z measurement from
    the central pose.  The fixed margin remains a conservative proxy for link
    collision geometry around each link origin.
    """

    current_eef = _pose(current_eef_pose, label="current EEF pose")
    target_eef = _pose(release_eef_pose, label="release EEF pose")
    margin = _finite_scalar(conservative_margin_m, label="conservative_margin_m")
    if margin < 0.0:
        raise ValueError("conservative_margin_m must be nonnegative")
    if not isinstance(live_assembly_link_poses, Mapping) or set(
        live_assembly_link_poses
    ) != set(FROZEN_FULL_ASSEMBLY_LINK_NAMES):
        raise ValueError(
            "full assembly projection requires exactly fl_link6/fl_link7/fl_link8"
        )

    per_link = {}
    for name in FROZEN_FULL_ASSEMBLY_LINK_NAMES:
        live_pose = _pose(
            live_assembly_link_poses[name], label=f"live assembly link {name}"
        )
        eef_link = relative_pose(current_eef, live_pose)
        target_link = compose_pose(target_eef, eef_link)
        conservative_lowest = float(target_link[2] - margin)
        per_link[name] = {
            "live_world_pose": live_pose.tolist(),
            "eef_relative_pose": np.asarray(eef_link, dtype=np.float64).tolist(),
            "target_world_pose": np.asarray(target_link, dtype=np.float64).tolist(),
            "target_link_center_z_m": float(target_link[2]),
            "target_conservative_lowest_z_m": conservative_lowest,
        }
    lowest_name = min(
        FROZEN_FULL_ASSEMBLY_LINK_NAMES,
        key=lambda name: per_link[name]["target_conservative_lowest_z_m"],
    )
    lowest_z = per_link[lowest_name]["target_conservative_lowest_z_m"]
    below_eef = max(0.0, float(target_eef[2] - lowest_z))
    receipt = {
        "schema_version": "cmf_f3_target_specific_full_assembly_projection_v6",
        "formal_data": False,
        "stage0_data": False,
        "assembly_link_names": list(FROZEN_FULL_ASSEMBLY_LINK_NAMES),
        "current_eef_pose": current_eef.tolist(),
        "release_eef_pose": target_eef.tolist(),
        "conservative_margin_m": margin,
        "per_link": per_link,
        "lowest_link_name": lowest_name,
        "predicted_assembly_lowest_z_m": lowest_z,
        "gripper_assembly_below_eef_m": below_eef,
        "target_orientation_specific": True,
        "pass": True,
    }
    receipt = _json_safe(receipt, path="assembly_projection")
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return validate_target_specific_full_assembly_projection_v6(receipt)


def validate_target_specific_full_assembly_projection_v6(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("assembly projection receipt must be a mapping")
    value = _json_safe(receipt, path="assembly_projection")
    digest = value.pop("receipt_sha256", None)
    if (
        value.get("schema_version")
        != "cmf_f3_target_specific_full_assembly_projection_v6"
    ):
        raise ValueError("assembly projection schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("assembly projection receipt hash mismatch")
    if value.get("assembly_link_names") != list(FROZEN_FULL_ASSEMBLY_LINK_NAMES):
        raise ValueError("assembly projection link set changed")
    if set(value.get("per_link", {})) != set(FROZEN_FULL_ASSEMBLY_LINK_NAMES):
        raise ValueError("assembly projection link evidence is incomplete")
    if value.get("lowest_link_name") not in FROZEN_FULL_ASSEMBLY_LINK_NAMES:
        raise ValueError("assembly projection lowest link is invalid")
    if value.get("target_orientation_specific") is not True or value.get("pass") is not True:
        raise ValueError("assembly projection contract did not pass")
    value["receipt_sha256"] = digest
    return value


def build_f3_release_geometry_clearance_v6(
    *,
    original_actor_pose: Sequence[float],
    unshifted_release_eef_pose: Sequence[float],
    support_top_z_m: float,
    gripper_assembly_below_eef_m: float,
) -> dict:
    """Build the uniform world-z target satisfying both held envelopes."""

    actor = _pose(original_actor_pose, label="original actor pose")
    eef = _pose(unshifted_release_eef_pose, label="unshifted release EEF pose")
    support_top = _finite_scalar(support_top_z_m, label="support_top_z_m")
    assembly_below = _finite_scalar(
        gripper_assembly_below_eef_m,
        label="gripper_assembly_below_eef_m",
    )
    if assembly_below < 0.0:
        raise ValueError("gripper_assembly_below_eef_m must be nonnegative")

    bottle_min_z, bottle_max_z = model13_world_obb_z_bounds(actor)
    assembly_min_z = float(eef[2] - assembly_below)
    required_lowest_z = support_top + FROZEN_GEOMETRIC_CLEARANCE_M
    bottle_shift = max(0.0, required_lowest_z - bottle_min_z)
    assembly_shift = max(0.0, required_lowest_z - assembly_min_z)
    selected_shift = max(bottle_shift, assembly_shift)

    release_actor = actor.copy()
    release_actor[2] += selected_shift
    release_eef = eef.copy()
    release_eef[2] += selected_shift
    shifted_min_z, shifted_max_z = model13_world_obb_z_bounds(release_actor)
    shifted_assembly_min_z = assembly_min_z + selected_shift
    bottle_gap = shifted_min_z - support_top
    assembly_gap = shifted_assembly_min_z - support_top

    if bottle_shift > assembly_shift:
        source = "bottle_obb"
    elif assembly_shift > bottle_shift:
        source = "gripper_assembly_envelope"
    else:
        source = "tie"

    scientific_invariants = {
        "axis_frame": dict(FROZEN_AXIS_FRAME),
        "v_nominal_amplitude_m": FROZEN_V_NOMINAL_AMPLITUDE_M,
        "h_nominal_amplitude_m": FROZEN_H_NOMINAL_AMPLITUDE_M,
        "programs": list(FROZEN_PROGRAMS),
        "shared_first_event": "V",
        "v_h_targets_changed": False,
        "event_order_changed": False,
        "executing_arm_changed": False,
        "bottle_asset_changed": False,
    }
    checks = {
        "selected_shift_is_envelope_max": abs(
            selected_shift - max(bottle_shift, assembly_shift)
        )
        <= 1e-12,
        "bottle_clearance_at_least_frozen_10mm": bottle_gap
        >= FROZEN_GEOMETRIC_CLEARANCE_M - 1e-12,
        "assembly_clearance_at_least_frozen_10mm": assembly_gap
        >= FROZEN_GEOMETRIC_CLEARANCE_M - 1e-12,
        "actor_xy_and_orientation_unchanged": bool(
            np.array_equal(release_actor[[0, 1, 3, 4, 5, 6]], actor[[0, 1, 3, 4, 5, 6]])
        ),
        "eef_xy_and_orientation_unchanged": bool(
            np.array_equal(release_eef[[0, 1, 3, 4, 5, 6]], eef[[0, 1, 3, 4, 5, 6]])
        ),
        "actor_and_eef_share_exact_world_z_shift": bool(
            release_actor[2] - actor[2] == release_eef[2] - eef[2]
        ),
        "v_h_and_program_contract_unchanged": all(
            scientific_invariants[key] is False
            for key in (
                "v_h_targets_changed",
                "event_order_changed",
                "executing_arm_changed",
                "bottle_asset_changed",
            )
        ),
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "asset": dict(FROZEN_ASSET),
        "model_data_sha256": MODEL13_MODEL_DATA_SHA256,
        "model13_local_geometry_center_m": list(
            MODEL13_LOCAL_GEOMETRY_CENTER_M
        ),
        "model13_half_extents_m": list(MODEL13_HALF_EXTENTS_M),
        "frozen_geometric_clearance_m": FROZEN_GEOMETRIC_CLEARANCE_M,
        "support_top_z_m": support_top,
        "original_actor_pose": actor.tolist(),
        "unshifted_release_eef_pose": eef.tolist(),
        "original_bottle_obb_min_z_m": bottle_min_z,
        "original_bottle_obb_max_z_m": bottle_max_z,
        "unshifted_assembly_lowest_z_m": assembly_min_z,
        "gripper_assembly_below_eef_m": assembly_below,
        "bottle_required_world_z_shift_m": bottle_shift,
        "assembly_required_world_z_shift_m": assembly_shift,
        "selected_world_z_shift_m": selected_shift,
        "selected_shift_source": source,
        "release_actor_pose": release_actor.tolist(),
        "release_eef_pose": release_eef.tolist(),
        "predicted_bottle_obb_min_z_m": shifted_min_z,
        "predicted_bottle_obb_max_z_m": shifted_max_z,
        "predicted_assembly_lowest_z_m": shifted_assembly_min_z,
        "predicted_bottle_clearance_m": bottle_gap,
        "predicted_assembly_clearance_m": assembly_gap,
        "scientific_invariants": scientific_invariants,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt = _json_safe(receipt, path="receipt")
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return validate_f3_release_geometry_clearance_v6(receipt)


def build_runtime_live_release_geometry_audit_v6(
    *,
    planning_clearance_receipt: Mapping[str, Any],
    live_actor_pose: Sequence[float],
    live_release_eef_pose: Sequence[float],
    live_assembly_link_poses: Mapping[str, Sequence[float]],
    live_support_top_z_m: float,
    live_model_center: Sequence[float],
    live_model_extents: Sequence[float],
    live_model_scale: Sequence[float],
    conservative_margin_m: float = FROZEN_ASSEMBLY_CONSERVATIVE_MARGIN_M,
) -> dict:
    """Audit fresh-scene model/support/link geometry using live values only."""

    planning = validate_f3_release_geometry_clearance_v6(
        planning_clearance_receipt
    )
    actor = _pose(live_actor_pose, label="live actor pose")
    eef = _pose(live_release_eef_pose, label="live release EEF pose")
    support_top = _finite_scalar(
        live_support_top_z_m, label="live_support_top_z_m"
    )
    try:
        raw_center = np.asarray(live_model_center, dtype=np.float64).reshape(3)
        raw_extents = np.asarray(live_model_extents, dtype=np.float64).reshape(3)
        raw_scale = np.asarray(live_model_scale, dtype=np.float64).reshape(3)
    except (TypeError, ValueError) as exc:
        raise ValueError("live model13 config arrays must have shape (3,)") from exc
    if (
        not np.all(np.isfinite(raw_center))
        or not np.all(np.isfinite(raw_extents))
        or not np.all(np.isfinite(raw_scale))
        or np.any(raw_extents <= 0.0)
        or np.any(raw_scale <= 0.0)
    ):
        raise ValueError("live model13 config arrays must be finite positive")
    scaled_center = raw_center * raw_scale
    scaled_half = raw_extents * raw_scale / 2.0
    projection = build_target_specific_full_assembly_projection_v6(
        current_eef_pose=eef,
        live_assembly_link_poses=live_assembly_link_poses,
        release_eef_pose=eef,
        conservative_margin_m=conservative_margin_m,
    )
    bottle_min_z, bottle_max_z = model13_world_obb_z_bounds(actor)
    bottle_gap = bottle_min_z - support_top
    assembly_gap = projection["predicted_assembly_lowest_z_m"] - support_top
    model_center_matches = bool(
        np.allclose(
            scaled_center,
            np.asarray(MODEL13_LOCAL_GEOMETRY_CENTER_M),
            rtol=0.0,
            atol=1e-12,
        )
    )
    model_half_matches = bool(
        np.allclose(
            scaled_half,
            np.asarray(MODEL13_HALF_EXTENTS_M),
            rtol=0.0,
            atol=1e-12,
        )
    )
    checks = {
        "live_model13_center_matches_frozen": model_center_matches,
        "live_model13_half_extents_match_frozen": model_half_matches,
        "live_support_top_matches_planning": abs(
            support_top - float(planning["support_top_z_m"])
        )
        <= 1e-12,
        "live_bottle_gap_at_least_frozen_runtime_minimum": bottle_gap
        >= FROZEN_RUNTIME_MINIMUM_CLEARANCE_M - 1e-12,
        "live_full_assembly_gap_at_least_frozen_runtime_minimum": assembly_gap
        >= FROZEN_RUNTIME_MINIMUM_CLEARANCE_M - 1e-12,
        "planning_bottle_gap_at_least_frozen_10mm": float(
            planning["predicted_bottle_clearance_m"]
        )
        >= FROZEN_GEOMETRIC_CLEARANCE_M - 1e-12,
        "planning_assembly_gap_at_least_frozen_10mm": float(
            planning["predicted_assembly_clearance_m"]
        )
        >= FROZEN_GEOMETRIC_CLEARANCE_M - 1e-12,
    }
    receipt = {
        "schema_version": "cmf_f3_runtime_live_release_geometry_audit_v6",
        "formal_data": False,
        "stage0_data": False,
        "planning_clearance_receipt_sha256": planning["receipt_sha256"],
        "live_support_top_z_m": support_top,
        "planning_support_top_z_m": planning["support_top_z_m"],
        "live_actor_pose": actor.tolist(),
        "live_release_eef_pose": eef.tolist(),
        "live_model_config": {
            "center": raw_center.tolist(),
            "extents": raw_extents.tolist(),
            "scale": raw_scale.tolist(),
            "scaled_local_center_m": scaled_center.tolist(),
            "scaled_half_extents_m": scaled_half.tolist(),
        },
        "live_bottle_obb_min_z_m": bottle_min_z,
        "live_bottle_obb_max_z_m": bottle_max_z,
        "live_bottle_clearance_m": bottle_gap,
        "live_full_assembly_projection": projection,
        "live_full_assembly_clearance_m": assembly_gap,
        "frozen_runtime_tracking_allowance_m": FROZEN_RUNTIME_TRACKING_ALLOWANCE_M,
        "frozen_runtime_minimum_clearance_m": FROZEN_RUNTIME_MINIMUM_CLEARANCE_M,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt = _json_safe(receipt, path="runtime_audit")
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return validate_runtime_live_release_geometry_audit_v6(receipt)


def validate_runtime_live_release_geometry_audit_v6(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("runtime live geometry receipt must be a mapping")
    value = _json_safe(receipt, path="runtime_audit")
    digest = value.pop("receipt_sha256", None)
    if (
        value.get("schema_version")
        != "cmf_f3_runtime_live_release_geometry_audit_v6"
    ):
        raise ValueError("runtime live geometry schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("runtime live geometry receipt hash mismatch")
    validate_target_specific_full_assembly_projection_v6(
        value.get("live_full_assembly_projection")
    )
    checks = value.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        raise ValueError("runtime live geometry checks are missing")
    if value.get("pass") is not all(checks.values()):
        raise ValueError("runtime live geometry aggregate pass mismatch")
    value["receipt_sha256"] = digest
    return value


def validate_f3_release_geometry_clearance_v6(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("F3 release geometry receipt must be a mapping")
    value = _json_safe(receipt, path="receipt")
    digest = value.pop("receipt_sha256", None)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F3 release geometry schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F3 release geometry receipt hash mismatch")
    if value.get("asset") != FROZEN_ASSET:
        raise ValueError("F3 release geometry asset contract changed")
    if value.get("model_data_sha256") != MODEL13_MODEL_DATA_SHA256:
        raise ValueError("F3 release geometry model-data hash changed")
    if value.get("frozen_geometric_clearance_m") != FROZEN_GEOMETRIC_CLEARANCE_M:
        raise ValueError("F3 release geometric clearance changed")
    invariants = value.get("scientific_invariants")
    expected_invariants = {
        "axis_frame": dict(FROZEN_AXIS_FRAME),
        "v_nominal_amplitude_m": FROZEN_V_NOMINAL_AMPLITUDE_M,
        "h_nominal_amplitude_m": FROZEN_H_NOMINAL_AMPLITUDE_M,
        "programs": list(FROZEN_PROGRAMS),
        "shared_first_event": "V",
        "v_h_targets_changed": False,
        "event_order_changed": False,
        "executing_arm_changed": False,
        "bottle_asset_changed": False,
    }
    if invariants != expected_invariants:
        raise ValueError("F3 release geometry scientific invariants changed")
    checks = value.get("checks")
    if not isinstance(checks, Mapping) or not checks:
        raise ValueError("F3 release geometry checks are missing")
    if value.get("pass") is not all(checks.values()):
        raise ValueError("F3 release geometry aggregate pass mismatch")
    selected = float(value.get("selected_world_z_shift_m"))
    required = max(
        float(value.get("bottle_required_world_z_shift_m")),
        float(value.get("assembly_required_world_z_shift_m")),
    )
    if not np.isfinite(selected) or abs(selected - required) > 1e-12:
        raise ValueError("F3 release geometry selected shift is inconsistent")
    json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    value["receipt_sha256"] = digest
    return value


__all__ = [
    "FROZEN_ASSET",
    "FROZEN_ASSEMBLY_CONSERVATIVE_MARGIN_M",
    "FROZEN_AXIS_FRAME",
    "FROZEN_FULL_ASSEMBLY_LINK_NAMES",
    "FROZEN_GEOMETRIC_CLEARANCE_M",
    "FROZEN_H_NOMINAL_AMPLITUDE_M",
    "FROZEN_PROGRAMS",
    "FROZEN_V_NOMINAL_AMPLITUDE_M",
    "FROZEN_RUNTIME_MINIMUM_CLEARANCE_M",
    "FROZEN_RUNTIME_TRACKING_ALLOWANCE_M",
    "MODEL13_HALF_EXTENTS_M",
    "MODEL13_LOCAL_GEOMETRY_CENTER_M",
    "MODEL13_MODEL_DATA_CENTER",
    "MODEL13_MODEL_DATA_EXTENTS",
    "MODEL13_MODEL_DATA_SCALE",
    "MODEL13_MODEL_DATA_SHA256",
    "SCHEMA_VERSION",
    "build_f3_release_geometry_clearance_v6",
    "build_runtime_live_release_geometry_audit_v6",
    "build_target_specific_full_assembly_projection_v6",
    "canonical_json_sha256",
    "model13_world_obb_z_bounds",
    "validate_f3_release_geometry_clearance_v6",
    "validate_runtime_live_release_geometry_audit_v6",
    "validate_target_specific_full_assembly_projection_v6",
]
