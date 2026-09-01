"""Fail-closed CPU geometry/layout screening for the F2 asset redesign.

The inside evaluator uses center-line intervals only to propose a cavity.  It
then independently certifies the complete, margin-inflated object AABB against
every convex collision piece with linear-program feasibility checks.  A
center-line result by itself is never emitted as passing evidence.

The layout evaluator is a necessary static screen.  Its result must not be
used as passive-on, fresh-scene realization, or planner evidence.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable

from .f2_official_asset_compatibility_matrix_v3 import (
    ASSET_ROOT,
    MINIMUM_STRICT_INSIDE_MARGIN_M,
    REPO_ROOT,
    validate_static_candidate_row_v3,
)


GEOMETRY_SCHEMA_VERSION = "cmf_f2_full_envelope_geometry_receipt_v3"
LAYOUT_SCHEMA_VERSION = "cmf_f2_asset_derived_layout_cpu_receipt_v3"
TABLE_PLANE_Z_M = 0.74
TABLE_BOUNDS_XY_M = np.asarray([[-0.45, -0.35], [0.45, 0.20]], dtype=np.float64)
FACILITY_XY_M = {
    "plastic_box": np.asarray([-0.29, -0.20], dtype=np.float64),
    "electronic_scale": np.asarray([-0.10, -0.20], dtype=np.float64),
    "beside_reference": np.asarray([0.20, -0.03], dtype=np.float64),
}
MAIN_OBJECT_XY_M = np.asarray([-0.28, 0.04], dtype=np.float64)
ROLE_ORIENTATION_WXYZ = {
    "main_object": np.asarray([0.5, 0.5, 0.5, 0.5], dtype=np.float64),
    "plastic_box": np.asarray([0.5, 0.5, 0.5, 0.5], dtype=np.float64),
    "electronic_scale": np.asarray([0.5, 0.5, 0.5, 0.5], dtype=np.float64),
    "beside_reference": np.asarray(
        [0.7071067811865476, 0.7071067811865476, 0.0, 0.0], dtype=np.float64
    ),
}
BESIDE_OFFSETS_XY_M = (
    np.asarray([0.00, 0.15], dtype=np.float64),
    np.asarray([-0.08, 0.13], dtype=np.float64),
    np.asarray([-0.12, 0.10], dtype=np.float64),
)
BESIDE_INNER_M = 0.12
BESIDE_OUTER_M = 0.23
FACILITY_CLEARANCE_M = 0.01
SUPPORT_MARGIN_M = 0.005
CAVITY_PROPOSAL_GRID_STEP_M = 0.001


def _copy(value: Any) -> Any:
    return canonical_jsonable(value)


def _hash_json(value: Any) -> str:
    return canonical_hash_json(value)


def _asset_path(modelname: str, model_id: int, kind: str) -> Path:
    family = ASSET_ROOT / modelname
    candidates = (
        family / kind / f"base{model_id}.glb",
        family / kind / f"textured{model_id}.obj",
        family / f"base{model_id}.glb",
        family / f"textured{model_id}.obj",
    )
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FileNotFoundError(f"missing {kind} for {modelname}/base{model_id}")
    return path


@lru_cache(maxsize=None)
def _collision_geometry(modelname: str, model_id: int) -> dict[str, Any]:
    import trimesh
    from scipy.spatial import ConvexHull

    model_data_path = ASSET_ROOT / modelname / f"model_data{model_id}.json"
    model_data = json.loads(model_data_path.read_text(encoding="utf-8"))
    scale = np.asarray(model_data.get("scale", [1.0, 1.0, 1.0]), dtype=np.float64).reshape(-1)
    if scale.size == 1:
        scale = np.repeat(scale, 3)
    if scale.shape != (3,) or not np.all(np.isfinite(scale)) or np.any(scale <= 0):
        raise ValueError("F2 asset scale is invalid")
    collision_path = _asset_path(modelname, model_id, "collision")
    scene = trimesh.load(collision_path, force="scene")
    pieces = []
    all_vertices = []
    for node_name in sorted(scene.graph.nodes_geometry):
        transform, geometry_name = scene.graph[node_name]
        mesh = scene.geometry[geometry_name].copy()
        mesh.apply_transform(transform)
        mesh.apply_scale(scale)
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 4:
            raise ValueError("F2 collision piece lacks a 3-D envelope")
        hull = ConvexHull(vertices)
        pieces.append(
            {
                "node_name": str(node_name),
                "equations": np.asarray(hull.equations, dtype=np.float64),
                "lower": vertices.min(axis=0),
                "upper": vertices.max(axis=0),
            }
        )
        all_vertices.append(vertices)
    if not pieces:
        raise ValueError("F2 collision asset has no geometry")
    vertices = np.concatenate(all_vertices, axis=0)
    return {
        "pieces": pieces,
        "lower": vertices.min(axis=0),
        "upper": vertices.max(axis=0),
        "center": (vertices.min(axis=0) + vertices.max(axis=0)) / 2.0,
        "dimensions": vertices.max(axis=0) - vertices.min(axis=0),
        "collision_path": str(collision_path.relative_to(REPO_ROOT)),
    }


def _points_inside_any_piece(pieces, points: np.ndarray) -> np.ndarray:
    occupied = np.zeros(len(points), dtype=bool)
    for piece in pieces:
        equations = piece["equations"]
        occupied |= np.all(
            points @ equations[:, :3].T + equations[:, 3] <= 1e-8,
            axis=1,
        )
    return occupied


def _free_interval(values: np.ndarray, occupied: np.ndarray, center: float) -> tuple[float, float]:
    index = int(np.argmin(np.abs(values - center)))
    if bool(occupied[index]):
        raise ValueError("candidate cavity center is occupied")
    lower = index
    upper = index
    while lower > 0 and not occupied[lower - 1]:
        lower -= 1
    while upper + 1 < len(values) and not occupied[upper + 1]:
        upper += 1
    return float(values[lower]), float(values[upper])


@lru_cache(maxsize=None)
def _cavity_proposal(box_id: int) -> dict[str, Any]:
    box = _collision_geometry("062_plasticbox", int(box_id))
    lower = box["lower"]
    upper = box["upper"]
    center = box["center"]
    intervals = []
    probe_center = center.copy()
    # Y is resolved first to move the X/Z probes into the empty interior.
    axis_order = (1, 0, 2)
    resolved = {}
    for axis in axis_order:
        values = np.arange(
            lower[axis] + CAVITY_PROPOSAL_GRID_STEP_M / 2.0,
            upper[axis],
            CAVITY_PROPOSAL_GRID_STEP_M,
        )
        points = np.tile(probe_center, (len(values), 1))
        points[:, axis] = values
        interval = _free_interval(
            values,
            _points_inside_any_piece(box["pieces"], points),
            center[axis],
        )
        resolved[axis] = interval
        probe_center[axis] = sum(interval) / 2.0
    for axis in range(3):
        intervals.append(resolved[axis])
    raw_lower = np.asarray([item[0] for item in intervals], dtype=np.float64)
    raw_upper = np.asarray([item[1] for item in intervals], dtype=np.float64)
    return {
        "raw_lower": raw_lower,
        "raw_upper": raw_upper,
        "center": (raw_lower + raw_upper) / 2.0,
        "proposal_source": "three_axis_center_lines_proposal_only",
        "proposal_is_acceptance_evidence": False,
    }


def _aabb_intersects_convex_piece(lower: np.ndarray, upper: np.ndarray, equations: np.ndarray) -> bool:
    from scipy.optimize import linprog

    result = linprog(
        np.zeros(3, dtype=np.float64),
        A_ub=equations[:, :3],
        b_ub=-equations[:, 3],
        bounds=list(zip(lower.tolist(), upper.tolist())),
        method="highs",
    )
    if result.status == 0:
        return True
    if result.status == 2:
        return False
    raise RuntimeError(f"F2 convex-envelope feasibility was indeterminate: {result.status}")


def _proper_axis_orientations():
    from itertools import permutations
    from scipy.spatial.transform import Rotation

    values = []
    for permutation in permutations(range(3)):
        matrix = np.zeros((3, 3), dtype=np.float64)
        for world_axis, local_axis in enumerate(permutation):
            matrix[world_axis, local_axis] = 1.0
        if np.linalg.det(matrix) < 0:
            matrix[0] *= -1.0
        quat_xyzw = Rotation.from_matrix(matrix).as_quat()
        quat_wxyz = [
            float(quat_xyzw[3]),
            float(quat_xyzw[0]),
            float(quat_xyzw[1]),
            float(quat_xyzw[2]),
        ]
        values.append((permutation, matrix, quat_wxyz))
    return values


def evaluate_strict_full_envelope_inside_v3(static_row: Mapping[str, Any]) -> dict[str, Any]:
    row = validate_static_candidate_row_v3(static_row)
    key = row["candidate_key"]
    can_id = int(key["main_object_model_id"])
    box_id = int(key["plastic_box_model_id"])
    try:
        can = _collision_geometry("071_can", can_id)
        box = _collision_geometry("062_plasticbox", box_id)
        proposal = _cavity_proposal(box_id)
        selected = None
        orientation_receipts = []
        for orientation_rank, (permutation, matrix, quaternion) in enumerate(_proper_axis_orientations()):
            world_dimensions = np.abs(matrix) @ can["dimensions"]
            half = world_dimensions / 2.0
            inflated_half = half + MINIMUM_STRICT_INSIDE_MARGIN_M
            envelope_lower = proposal["center"] - inflated_half
            envelope_upper = proposal["center"] + inflated_half
            within_proposal = bool(
                np.all(envelope_lower >= proposal["raw_lower"] - 1e-10)
                and np.all(envelope_upper <= proposal["raw_upper"] + 1e-10)
            )
            intersecting_piece_indices = []
            if within_proposal:
                for piece_index, piece in enumerate(box["pieces"]):
                    if _aabb_intersects_convex_piece(
                        envelope_lower, envelope_upper, piece["equations"]
                    ):
                        intersecting_piece_indices.append(piece_index)
            passed = within_proposal and not intersecting_piece_indices
            item = {
                "orientation_rank": orientation_rank,
                "axis_permutation": list(permutation),
                "selected_orientation_wxyz": quaternion,
                "full_collision_envelope_dimensions_m": world_dimensions.tolist(),
                "margin_inflated_envelope_lower_m": envelope_lower.tolist(),
                "margin_inflated_envelope_upper_m": envelope_upper.tolist(),
                "within_center_line_proposed_bounds": within_proposal,
                "convex_piece_count_checked": len(box["pieces"]),
                "intersecting_convex_piece_indices": intersecting_piece_indices,
                "complete_inflated_envelope_collision_free": passed,
                "pass": passed,
            }
            orientation_receipts.append(item)
            if passed and selected is None:
                selected = item
        passed = selected is not None
        receipt = {
            "schema_version": GEOMETRY_SCHEMA_VERSION,
            "candidate_key_sha256": row["candidate_key_sha256"],
            "candidate_key": key,
            "asset_record_sha256s": {
                role: row["asset_record_sha256s"][role]
                for role in ("main_object", "plastic_box")
            },
            "proposal_source": proposal["proposal_source"],
            "center_line_or_axis_interval_only": False,
            "center_line_proposal_is_acceptance_evidence": False,
            "full_object_envelope_checked": True,
            "complete_cavity_collision_surface_checked": True,
            "certification_method": "margin_inflated_full_AABB_vs_every_convex_piece_LP_feasibility",
            "minimum_signed_margin_m": MINIMUM_STRICT_INSIDE_MARGIN_M if passed else 0.0,
            "raw_cavity_proposal_lower_m": proposal["raw_lower"].tolist(),
            "raw_cavity_proposal_upper_m": proposal["raw_upper"].tolist(),
            "can_collision_path": can["collision_path"],
            "box_collision_path": box["collision_path"],
            "orientation_receipts": orientation_receipts,
            "selected_orientation_rank": None if selected is None else selected["orientation_rank"],
            "selected_orientation_wxyz": None if selected is None else selected["selected_orientation_wxyz"],
            "status": "passed" if passed else "rejected",
            "pass": passed,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
    except Exception as exc:
        receipt = {
            "schema_version": GEOMETRY_SCHEMA_VERSION,
            "candidate_key_sha256": row["candidate_key_sha256"],
            "candidate_key": key,
            "asset_record_sha256s": {
                role: row["asset_record_sha256s"][role]
                for role in ("main_object", "plastic_box")
            },
            "center_line_or_axis_interval_only": False,
            "full_object_envelope_checked": False,
            "complete_cavity_collision_surface_checked": False,
            "minimum_signed_margin_m": 0.0,
            "selected_orientation_wxyz": None,
            "status": "rejected",
            "pass": False,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
    receipt["evidence_sha256"] = _hash_json(receipt)
    return receipt


def _box_corners(lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    from itertools import product

    return np.asarray(
        [[lower[axis] if bit == 0 else upper[axis] for axis, bit in enumerate(bits)] for bits in product((0, 1), repeat=3)],
        dtype=np.float64,
    )


def _rotation_matrix_wxyz(quaternion: np.ndarray) -> np.ndarray:
    from scipy.spatial.transform import Rotation

    q = np.asarray(quaternion, dtype=np.float64).reshape(4)
    return Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()


def _world_aabb(
    modelname: str,
    model_id: int,
    xy: np.ndarray,
    quaternion_wxyz: np.ndarray,
) -> dict[str, np.ndarray]:
    geometry = _collision_geometry(modelname, model_id)
    rotation = _rotation_matrix_wxyz(quaternion_wxyz)
    rotated = _box_corners(geometry["lower"], geometry["upper"]) @ rotation.T
    rotated_lower = rotated.min(axis=0)
    rotated_upper = rotated.max(axis=0)
    origin = np.asarray([xy[0], xy[1], TABLE_PLANE_Z_M - rotated_lower[2]])
    return {
        "origin": origin,
        "lower": rotated_lower + origin,
        "upper": rotated_upper + origin,
        "local_center": geometry["center"],
        "local_dimensions": geometry["dimensions"],
        "rotation": rotation,
        "quaternion_wxyz": np.asarray(quaternion_wxyz, dtype=np.float64),
    }


def _rect_contains(point: np.ndarray, center: np.ndarray, half: np.ndarray) -> bool:
    return bool(np.all(np.abs(point - center) <= half))


def evaluate_asset_derived_layout_cpu_v3(
    static_row: Mapping[str, Any], inside_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Build one deterministic necessary-condition layout for a candidate."""

    row = validate_static_candidate_row_v3(static_row)
    inside = _copy(inside_receipt)
    inside_digest = inside.pop("evidence_sha256", None)
    if not isinstance(inside_digest, str) or _hash_json(inside) != inside_digest:
        raise ValueError("F2 CPU inside receipt hash mismatch")
    key = row["candidate_key"]
    models = {
        "plastic_box": ("062_plasticbox", int(key["plastic_box_model_id"])),
        "electronic_scale": ("072_electronicscale", int(key["electronic_scale_model_id"])),
        "beside_reference": ("074_displaystand", int(key["beside_reference_model_id"])),
    }
    aabbs = {
        role: _world_aabb(
            modelname,
            model_id,
            FACILITY_XY_M[role],
            ROLE_ORIENTATION_WXYZ[role],
        )
        for role, (modelname, model_id) in models.items()
    }
    can = _world_aabb(
        "071_can",
        int(key["main_object_model_id"]),
        MAIN_OBJECT_XY_M,
        ROLE_ORIENTATION_WXYZ["main_object"],
    )
    cavity = _cavity_proposal(int(key["plastic_box_model_id"]))
    box_origin = aabbs["plastic_box"]["origin"]
    cavity_world = _box_corners(cavity["raw_lower"], cavity["raw_upper"]) @ aabbs[
        "plastic_box"
    ]["rotation"].T + box_origin
    inside_lower = cavity_world.min(axis=0)
    inside_upper = cavity_world.max(axis=0)
    inside_center = (inside_lower[:2] + inside_upper[:2]) / 2.0
    inside_half = (inside_upper[:2] - inside_lower[:2]) / 2.0
    scale = aabbs["electronic_scale"]
    on_center = (scale["lower"][:2] + scale["upper"][:2]) / 2.0
    on_half = (scale["upper"][:2] - scale["lower"][:2]) / 2.0 - SUPPORT_MARGIN_M
    on_static_support_nonempty = bool(np.all(on_half > 0))

    facility_pairs = []
    roles = tuple(models)
    for first_index, first in enumerate(roles):
        for second in roles[first_index + 1 :]:
            a = aabbs[first]
            b = aabbs[second]
            separated = bool(
                np.any(
                    np.maximum(a["lower"][:2], b["lower"][:2])
                    - np.minimum(a["upper"][:2], b["upper"][:2])
                    >= FACILITY_CLEARANCE_M
                )
            )
            facility_pairs.append({"roles": [first, second], "xy_clearance_pass": separated})

    beside_center = FACILITY_XY_M["beside_reference"]
    beside_points = [beside_center + offset for offset in BESIDE_OFFSETS_XY_M]
    beside_checks = []
    for point in beside_points:
        radial = float(np.linalg.norm(point - beside_center))
        within_table = bool(
            np.all(point >= TABLE_BOUNDS_XY_M[0]) and np.all(point <= TABLE_BOUNDS_XY_M[1])
        )
        inside_overlap = _rect_contains(point, inside_center, inside_half)
        on_overlap = on_static_support_nonempty and _rect_contains(point, on_center, on_half)
        beside_checks.append(
            {
                "point_xy_m": point.tolist(),
                "radial_distance_m": radial,
                "within_table": within_table,
                "inside_overlap": inside_overlap,
                "on_overlap": on_overlap,
                "mutually_exclusive_static": (
                    BESIDE_INNER_M <= radial <= BESIDE_OUTER_M
                    and within_table
                    and not inside_overlap
                    and not on_overlap
                ),
            }
        )
    checks = {
        "inside_full_envelope_cpu_pass": inside.get("pass") is True,
        "on_support_footprint_nonempty_static_only": on_static_support_nonempty,
        "facility_xy_clearance": all(item["xy_clearance_pass"] for item in facility_pairs),
        "beside_points_mutually_exclusive_static_only": all(
            item["mutually_exclusive_static"] for item in beside_checks
        ),
        "all_facility_aabbs_inside_table": all(
            np.all(value["lower"][:2] >= TABLE_BOUNDS_XY_M[0])
            and np.all(value["upper"][:2] <= TABLE_BOUNDS_XY_M[1])
            for value in aabbs.values()
        ),
        "main_object_spawn_aabb_inside_table": bool(
            np.all(can["lower"][:2] >= TABLE_BOUNDS_XY_M[0])
            and np.all(can["upper"][:2] <= TABLE_BOUNDS_XY_M[1])
        ),
    }
    passed = all(checks.values())
    layout = {
        "layout_version": "f2_asset_derived_layout_cpu_v3",
        "candidate_key": key,
        "table_plane_z_m": TABLE_PLANE_Z_M,
        "main_object_pose_xyz": can["origin"].tolist(),
        "facility_pose_xyz": {
            role: value["origin"].tolist() for role, value in aabbs.items()
        },
        "main_object_orientation_wxyz": ROLE_ORIENTATION_WXYZ["main_object"].tolist(),
        "facility_orientation_wxyz": {
            role: ROLE_ORIENTATION_WXYZ[role].tolist() for role in aabbs
        },
        "inside_region_center_xy_m": inside_center.tolist(),
        "inside_region_half_xy_m": inside_half.tolist(),
        "on_region_center_xy_m": on_center.tolist(),
        "on_region_half_xy_m": on_half.tolist(),
        "beside_candidate_xy_m": [point.tolist() for point in beside_points],
    }
    receipt = {
        "schema_version": LAYOUT_SCHEMA_VERSION,
        "candidate_key_sha256": row["candidate_key_sha256"],
        "candidate_key": key,
        "inside_evidence_sha256": inside_digest,
        "layout": layout,
        "layout_payload_sha256": _hash_json(layout),
        "facility_pair_checks": facility_pairs,
        "beside_static_checks": beside_checks,
        "checks": checks,
        "status": "passed" if passed else "rejected",
        "pass": passed,
        "static_screen_only": True,
        "passive_on_stability_verified": False,
        "fresh_scene_layout_realization_verified": False,
        "runtime_beside_predicates_verified": False,
        "planner_reachability_verified": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    receipt["receipt_sha256"] = _hash_json(receipt)
    return receipt


__all__ = [
    "evaluate_asset_derived_layout_cpu_v3",
    "evaluate_strict_full_envelope_inside_v3",
]
