"""Frozen, explicit scene contracts consumed by the v2 F2/F3 runners.

This module is CPU safe.  It contains no simulator imports and is therefore
also the source used by the independent finalizer and the preflight tests.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .canonical import canonical_sha256
from .factory import load_model_spec


ASSET_ROOT = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets")


_BASE_F2 = {
    "layout_id": "v4_beside_y_workspace",
    "box_center_xyz": [-0.18, -0.18, 0.755],
    "scale_center_xyz": [-0.02, -0.18, 0.755],
    "stand_center_xyz": [0.08, -0.18, 0.79],
    "table_support_z": 0.740,
    "box_support_z": 0.760,
    "box_inner_lower_xyz": [-0.29, -0.29, 0.760],
    "box_inner_upper_xyz": [-0.07, -0.07, 0.855],
    "scale_half_xy": [0.04, 0.06],
    "scale_top_z": 0.760,
    "stand_half_xy": [0.05, 0.05],
    "stand_top_z": 0.825,
    "beside_annulus_radius": [0.105, 0.205],
    "beside_table_z": 0.740,
    "beside_min_axis_clearance_m": 0.005,
    "beside_z_tolerance": 0.012,
    "inside_support_z_tolerance": 0.012,
    "inside_horizontal_margin": [0.040, 0.050],
    "can_support_half_xy": [0.038, 0.049],
    "forbid_reference_top_contact": True,
}

_BASE_F3 = {
    "pad_center_xyz": [-0.18, -0.06, 0.745],
    "rest_source": "setup_origin_eef_captured_before_first_action",
    "rest_position_tolerance_m": 0.030,
    "rest_orientation_tolerance_rad": 0.020,
    "rest_linear_speed_mps": 0.010,
    "rest_angular_speed_rps": 0.050,
}


def _shift(values: list[float], dx: float) -> list[float]:
    return [float(values[0] + dx), float(values[1]), float(values[2])]


def scene_spec(root_id: str) -> dict[str, Any]:
    if root_id not in {"F2-A-v2", "F2-B-v2", "F3-A-v2", "F3-B-v2"}:
        raise ValueError(f"unknown v2 root: {root_id}")
    family = root_id[:2]
    variant = root_id[3]
    shift = 0.0 if variant == "A" else 0.040
    value: dict[str, Any] = {
        "schema_version": "cmf_f2_f3_scene_spec_v2",
        "root_id": root_id,
        "family": family,
        "layout_variant": variant,
        "physical_layout_delta_x_m": shift,
        "scene_seed": {"F2-A-v2": 202609101, "F2-B-v2": 202609102, "F3-A-v2": 202609103, "F3-B-v2": 202609104}[root_id],
    }
    if family == "F2":
        f2 = deepcopy(_BASE_F2)
        # v4 keeps the reference object clear of the box and moves the legal
        # beside target into the reachable side of the table.  The target is
        # a table-supported point near (x=.06, y=-.04); the stand remains the
        # semantic reference at (x=.06, y=.08).  A/B still differ through the
        # registered x shift of the static layout, while the finite target is
        # kept in the planner-qualified workspace.
        f2["layout_id"] = "v4_beside_y_workspace"
        f2["stand_center_xyz"] = [0.06, 0.08, 0.79]
        asset = load_model_spec(ASSET_ROOT, "071_can", model_id=0, asset_id="f2_can_v2")
        f2["asset_binding"] = asset.to_receipt()
        support_point = asset.semantic_points.get("contact_0")
        if support_point is None:
            raise ValueError("F2 can asset lacks the frozen contact_0 support point")
        f2["support_point_local_xyz"] = list(support_point)
        f2["support_point_source"] = "asset model_data contact_points_pose[0] after effective_scale; transformed by actual actor quaternion"
        for key in ("box_center_xyz", "scale_center_xyz", "stand_center_xyz"):
            f2[key] = _shift(f2[key], shift)
        f2["box_inner_lower_xyz"] = _shift(f2["box_inner_lower_xyz"], shift)
        f2["box_inner_upper_xyz"] = _shift(f2["box_inner_upper_xyz"], shift)
        f2["beside_target_xy"] = [0.06, -0.04]
        f2["support_identity_by_relation"] = {
            "inside": "f2_redesign_box_bottom",
            "on": "f2_redesign_scale",
            "beside": "table",
        }
        value["f2"] = f2
    else:
        f3 = deepcopy(_BASE_F3)
        asset = load_model_spec(ASSET_ROOT, "114_bottle", model_id=1, asset_id="f3_bottle_v2")
        f3["asset_binding"] = asset.to_receipt()
        f3["pad_center_xyz"] = _shift(f3["pad_center_xyz"], shift)
        f3["central_marker_xyz"] = _shift([0.0, -0.05, 0.95], shift)
        value["f3"] = f3
    value["candidate_set_schema"] = {
        "F2": {"fields": ["family", "object_ref", "target_ref", "relation", "program_id"], "relations": ["inside", "on", "beside"]},
        "F3": {"fields": ["family", "object_ref", "program_id", "event_sequence"], "programs": ["VVHH", "VHVH", "VHHV"]},
    }[family]
    value["spec_sha256"] = canonical_sha256(value)
    return value


def candidate_set_for(spec: dict[str, Any]) -> list[dict[str, str]]:
    if spec["family"] == "F2":
        return [
            {"family": "F2", "object_ref": "main_can", "target_ref": "box", "relation": "inside", "program_id": "inside"},
            {"family": "F2", "object_ref": "main_can", "target_ref": "scale", "relation": "on", "program_id": "on"},
            {"family": "F2", "object_ref": "main_can", "target_ref": "stand", "relation": "beside", "program_id": "beside"},
        ]
    return [
        {"family": "F3", "object_ref": "bottle", "program_id": program, "event_sequence": program}
        for program in ("VVHH", "VHVH", "VHHV")
    ]
