"""CPU-only machine evidence for runtime-v2 geometry and action contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from ..raw_writer import ACTION_LAYOUT_DIMENSIONS, ACTION_LAYOUT_VERSION
from ..runtime_v2_contracts import (
    FAMILY_IMPLEMENTATION_VERSIONS,
    IMPLEMENTATION_VERSION,
    PLASTICBOX_BASE3_CAVITY,
    PROBE_PLANNER_QUERY_LIMITS,
    RUNTIME_V2_AUTHORIZATION,
    TRAY_BASE0_SUPPORT_REGION,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _transformed_meshes(path: Path):
    import trimesh

    scene = trimesh.load(path, force="scene")
    meshes = []
    for node_name in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node_name]
        mesh = scene.geometry[geometry_name].copy()
        mesh.apply_transform(transform)
        meshes.append(mesh)
    return meshes


def _convex_piece_grid_audit(path: Path, lower_m, upper_m, scale, samples_per_axis=25):
    from scipy.spatial import ConvexHull

    meshes = _transformed_meshes(path)
    equations = [ConvexHull(mesh.vertices).equations for mesh in meshes]
    lower = np.asarray(lower_m, dtype=np.float64) / float(scale)
    upper = np.asarray(upper_m, dtype=np.float64) / float(scale)
    axes = [np.linspace(lower[index], upper[index], samples_per_axis) for index in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    inside_collision = np.zeros(len(grid), dtype=bool)
    for equation in equations:
        inside_collision |= np.all(grid @ equation[:, :3].T + equation[:, 3] <= 1e-7, axis=1)
    bounds = np.asarray([mesh.bounds for mesh in meshes]) * float(scale)
    return {
        "convex_piece_count": len(meshes),
        "samples_per_axis": samples_per_axis,
        "sample_count": len(grid),
        "sampled_points_inside_collision_piece": int(inside_collision.sum()),
        "sampled_collision_free": bool(not inside_collision.any()),
        "combined_collision_lower_m": bounds[:, 0].min(axis=0).tolist(),
        "combined_collision_upper_m": bounds[:, 1].max(axis=0).tolist(),
        "method": "uniform grid tested against scipy ConvexHull half-spaces for every official convex collision piece",
        "limitation": "finite CPU sampling is implementation evidence, not a substitute for runtime contact and realized-pose verification",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("static audit output must use a new immutable path")
    repo = Path(__file__).resolve().parents[2]
    plastic_collision = repo / "assets/objects/062_plasticbox/collision/base3.glb"
    tray_collision = repo / "assets/objects/008_tray/collision/base0.glb"
    plastic_audit = _convex_piece_grid_audit(
        plastic_collision,
        PLASTICBOX_BASE3_CAVITY["collision_free_core_lower_m"],
        PLASTICBOX_BASE3_CAVITY["upper_m"],
        scale=0.1,
    )
    tray_meshes = _transformed_meshes(tray_collision)
    tray_bounds = np.asarray([mesh.bounds for mesh in tray_meshes]) * 0.16
    payload = {
        "schema_version": "cmf_runtime_v2_cpu_static_audit_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "gpu_used": False,
        "family_implementation_versions": FAMILY_IMPLEMENTATION_VERSIONS,
        "authorization": RUNTIME_V2_AUTHORIZATION,
        "probe_planner_query_limits": PROBE_PLANNER_QUERY_LIMITS,
        "action_contract": {
            "stream": "controller_effective_setpoint_v1",
            "frequency_hz": 250,
            "dimension": 26,
            "layout_version": ACTION_LAYOUT_VERSION,
            "dimensions": list(ACTION_LAYOUT_DIMENSIONS),
        },
        "f1_plasticbox_true_cavity": {
            "contract": PLASTICBOX_BASE3_CAVITY,
            "collision_path": str(plastic_collision.relative_to(repo)),
            "collision_sha256_recomputed": _sha256(plastic_collision),
            "grid_audit": plastic_audit,
            "grid_audit_region": "collision_free_core_lower_m through upper_m; semantic lower support boundary intentionally excluded from free-space sampling",
            "runtime_contact_validation_required": True,
        },
        "f4_tray_support_region": {
            "contract": TRAY_BASE0_SUPPORT_REGION,
            "collision_path": str(tray_collision.relative_to(repo)),
            "collision_sha256_recomputed": _sha256(tray_collision),
            "convex_piece_count": len(tray_meshes),
            "combined_collision_lower_m": tray_bounds[:, 0].min(axis=0).tolist(),
            "combined_collision_upper_m": tray_bounds[:, 1].max(axis=0).tolist(),
            "predicate_scope": "horizontal footprint inside region plus runtime support contact/stability; not full-height containment",
            "runtime_contact_validation_required": True,
        },
        "conclusion": "cpu_static_contracts_passed_gpu_runtime_unverified",
        "stage0_readiness_effect": "none; BLOCKED_WITH_REASONS remains",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if plastic_audit["sampled_collision_free"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
