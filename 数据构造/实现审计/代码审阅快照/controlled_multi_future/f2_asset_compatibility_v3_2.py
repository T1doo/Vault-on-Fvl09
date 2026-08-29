"""CPU-only official F2 object/container compatibility audit for runtime-v3_2."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Sequence

import numpy as np


ACTIVE_REPO_ROOT = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin")
REPO_ROOT = ACTIVE_REPO_ROOT if (ACTIVE_REPO_ROOT / "assets").is_dir() else Path(__file__).resolve().parents[1]
CAN_MODELNAME = "071_can"
BOX_MODELNAME = "062_plasticbox"
CURRENT_CAN_ID = 1
CURRENT_BOX_ID = 3
SAFETY_MARGIN_PER_SIDE_M = 0.005
GRID_STEP_M = 0.001


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _model_ids(modelname: str) -> list[int]:
    root = REPO_ROOT / "assets" / "objects" / modelname
    return sorted(int(path.stem.removeprefix("model_data")) for path in root.glob("model_data*.json"))


def _model_data(modelname: str, model_id: int) -> tuple[Path, dict]:
    path = REPO_ROOT / "assets" / "objects" / modelname / f"model_data{model_id}.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def _transformed_collision_meshes(modelname: str, model_id: int, scale: float):
    import trimesh

    path = REPO_ROOT / "assets" / "objects" / modelname / "collision" / f"base{model_id}.glb"
    scene = trimesh.load(path, force="scene")
    meshes = []
    for node_name in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node_name]
        mesh = scene.geometry[geometry_name].copy()
        mesh.apply_transform(transform)
        mesh.apply_scale(scale)
        meshes.append(mesh)
    return path, meshes


def _inside_convex_pieces(equations, points: np.ndarray) -> np.ndarray:
    return np.logical_or.reduce(
        [np.all(points @ equation[:, :3].T + equation[:, 3] <= 1e-7, axis=1) for equation in equations]
    )


def _free_interval_containing(values: np.ndarray, occupied: np.ndarray, center: float) -> tuple[float, float]:
    index = int(np.argmin(np.abs(values - float(center))))
    if bool(occupied[index]):
        raise ValueError("cavity center lies inside a collision piece")
    lower = index
    while lower > 0 and not occupied[lower - 1]:
        lower -= 1
    upper = index
    while upper + 1 < len(values) and not occupied[upper + 1]:
        upper += 1
    return float(values[lower]), float(values[upper])


def derive_axis_aligned_cavity(model_id: int, *, grid_step_m: float = GRID_STEP_M) -> dict:
    from scipy.spatial import ConvexHull

    model_path, data = _model_data(BOX_MODELNAME, model_id)
    scale = np.asarray(data["scale"], dtype=np.float64).reshape(3)
    if not np.allclose(scale, scale[0]):
        raise ValueError("plasticbox cavity audit requires uniform asset scale")
    collision_path, meshes = _transformed_collision_meshes(BOX_MODELNAME, model_id, float(scale[0]))
    equations = [ConvexHull(mesh.vertices).equations for mesh in meshes]
    bounds = np.asarray([mesh.bounds for mesh in meshes], dtype=np.float64)
    outer_lower = bounds[:, 0].min(axis=0)
    outer_upper = bounds[:, 1].max(axis=0)
    center = (outer_lower + outer_upper) / 2.0

    y_values = np.arange(outer_lower[1] + grid_step_m / 2.0, outer_upper[1], grid_step_m)
    y_points = np.tile(center, (len(y_values), 1))
    y_points[:, 1] = y_values
    y_lower, y_upper = _free_interval_containing(
        y_values, _inside_convex_pieces(equations, y_points), center[1]
    )
    interior_y = (y_lower + y_upper) / 2.0

    x_values = np.arange(outer_lower[0] + grid_step_m / 2.0, outer_upper[0], grid_step_m)
    x_points = np.tile([center[0], interior_y, center[2]], (len(x_values), 1))
    x_points[:, 0] = x_values
    x_lower, x_upper = _free_interval_containing(
        x_values, _inside_convex_pieces(equations, x_points), center[0]
    )

    z_values = np.arange(outer_lower[2] + grid_step_m / 2.0, outer_upper[2], grid_step_m)
    z_points = np.tile([center[0], interior_y, center[2]], (len(z_values), 1))
    z_points[:, 2] = z_values
    z_lower, z_upper = _free_interval_containing(
        z_values, _inside_convex_pieces(equations, z_points), center[2]
    )

    lower = np.asarray([x_lower, y_lower, z_lower], dtype=np.float64)
    upper = np.asarray([x_upper, y_upper, z_upper], dtype=np.float64)
    strict_lower = lower + SAFETY_MARGIN_PER_SIDE_M
    strict_upper = upper - SAFETY_MARGIN_PER_SIDE_M
    if np.any(strict_lower >= strict_upper):
        raise ValueError("plasticbox cavity disappears after safety margin")
    return {
        "model_id": model_id,
        "model_data_path": str(model_path.relative_to(REPO_ROOT)),
        "model_data_sha256": _sha256_file(model_path),
        "collision_path": str(collision_path.relative_to(REPO_ROOT)),
        "collision_sha256": _sha256_file(collision_path),
        "convex_piece_count": len(meshes),
        "grid_step_m": grid_step_m,
        "raw_lower_m": lower.tolist(),
        "raw_upper_m": upper.tolist(),
        "raw_dimensions_m": (upper - lower).tolist(),
        "strict_lower_m": strict_lower.tolist(),
        "strict_upper_m": strict_upper.tolist(),
        "strict_dimensions_m": (strict_upper - strict_lower).tolist(),
        "safety_margin_per_side_m": SAFETY_MARGIN_PER_SIDE_M,
    }


def can_record(model_id: int) -> dict:
    path, data = _model_data(CAN_MODELNAME, model_id)
    dimensions = np.asarray(data["extents"], dtype=np.float64) * np.asarray(data["scale"], dtype=np.float64)
    collision = REPO_ROOT / "assets" / "objects" / CAN_MODELNAME / "collision" / f"base{model_id}.glb"
    visual = REPO_ROOT / "assets" / "objects" / CAN_MODELNAME / "visual" / f"base{model_id}.glb"
    return {
        "model_id": model_id,
        "dimensions_m": dimensions.tolist(),
        "model_data_path": str(path.relative_to(REPO_ROOT)),
        "model_data_sha256": _sha256_file(path),
        "collision_sha256": _sha256_file(collision),
        "visual_sha256": _sha256_file(visual),
    }


def fit_record(can: dict, cavity: dict) -> dict:
    can_dimensions = np.asarray(can["dimensions_m"], dtype=np.float64)
    cavity_dimensions = np.asarray(cavity["strict_dimensions_m"], dtype=np.float64)
    candidates = []
    for permutation in itertools.permutations(range(3)):
        oriented = can_dimensions[list(permutation)]
        clearances = cavity_dimensions - oriented
        if np.all(clearances > 0):
            candidates.append(
                {
                    "axis_permutation": list(permutation),
                    "oriented_can_dimensions_m": oriented.tolist(),
                    "clearance_dimensions_m": clearances.tolist(),
                    "minimum_clearance_m": float(np.min(clearances)),
                }
            )
    selected = max(candidates, key=lambda item: item["minimum_clearance_m"]) if candidates else None
    return {
        "can_model_id": can["model_id"],
        "plasticbox_model_id": cavity["model_id"],
        "strict_full_obb_fit": selected is not None,
        "best_orientation": selected,
    }


def build_matrix() -> dict:
    can_ids = _model_ids(CAN_MODELNAME)
    box_ids = _model_ids(BOX_MODELNAME)
    cans = {model_id: can_record(model_id) for model_id in can_ids}
    cavities = {model_id: derive_axis_aligned_cavity(model_id) for model_id in box_ids}

    stage1 = [fit_record(cans[model_id], cavities[CURRENT_BOX_ID]) for model_id in can_ids]
    stage2 = [fit_record(cans[CURRENT_CAN_ID], cavities[model_id]) for model_id in box_ids]
    selected = next((item for item in stage1 if item["strict_full_obb_fit"]), None)
    selection_stage = "can_id_with_current_box"
    if selected is None:
        selected = next((item for item in stage2 if item["strict_full_obb_fit"]), None)
        selection_stage = "box_id_with_current_can"
    if selected is None:
        selection_stage = "requires_smaller_official_object_audit"

    return {
        "schema_version": "cmf_f2_official_asset_compatibility_matrix_v2",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_2",
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "audit_order": [
            "all 071_can model IDs with 062_plasticbox/base3",
            "071_can/base1 with all 062_plasticbox model IDs",
            "smaller official object audit only if stages 1-2 have no solution",
        ],
        "tie_break": "first model ID in ascending fixed audit order after provenance and >=5mm-per-side strict cavity gate",
        "can_records": list(cans.values()),
        "plasticbox_cavities": list(cavities.values()),
        "stage1_can_ids_current_box": stage1,
        "stage2_box_ids_current_can": stage2,
        "selection_stage": selection_stage,
        "selected": selected,
    }


def write_matrix(path: Path) -> dict:
    if path.exists():
        raise FileExistsError("F2 compatibility matrix output must be new")
    value = build_matrix()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value
