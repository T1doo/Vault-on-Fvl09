"""Source-bound asset factory for the new F2/F3 scene lineages.

Metadata is read before any builder call and the same effective scale is sent
to visual and collision geometry.  SAPIEN is imported only when an actual
scene build is requested; metadata qualification therefore remains safe on a
host where the renderer is unavailable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .assets import AssetReadbackError, principal_to_actor_tensor, validate_scale
from .canonical import canonical_sha256, sha256_file


class FactoryError(ValueError):
    """Raised when an asset cannot be bound to one immutable scene spec."""


@dataclass(frozen=True)
class ModelSpec:
    asset_id: str
    model_name: str
    model_id: int | None
    model_data_path: str
    points_info_path: str
    collision_path: str
    visual_path: str
    effective_scale: tuple[float, float, float]
    unscaled_extents: tuple[float, float, float]
    scaled_extents: tuple[float, float, float]
    center: tuple[float, float, float]
    semantic_points: Mapping[str, tuple[float, float, float]]
    source_hashes: Mapping[str, str]

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema_version": "cmf_f2_f3_model_spec_v1",
            "asset_id": self.asset_id,
            "model_name": self.model_name,
            "model_id": self.model_id,
            "model_data_path": self.model_data_path,
            "points_info_path": self.points_info_path,
            "collision_path": self.collision_path,
            "visual_path": self.visual_path,
            "effective_scale": list(self.effective_scale),
            "unscaled_extents": list(self.unscaled_extents),
            "scaled_extents": list(self.scaled_extents),
            "center": list(self.center),
            "semantic_points": {key: list(value) for key, value in self.semantic_points.items()},
            "source_hashes": dict(self.source_hashes),
            "spec_sha256": canonical_sha256({
                "asset_id": self.asset_id,
                "model_name": self.model_name,
                "model_id": self.model_id,
                "effective_scale": list(self.effective_scale),
                "scaled_extents": list(self.scaled_extents),
                "semantic_points": {key: list(value) for key, value in self.semantic_points.items()},
                "source_hashes": dict(self.source_hashes),
            }),
        }


def _asset_file(model_dir: Path, stem: str, model_id: int | None) -> Path:
    suffix = "" if model_id is None else str(model_id)
    candidates = [model_dir / f"{stem}{suffix}.glb", model_dir / f"{stem}{suffix}.obj"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FactoryError(f"missing {stem} mesh for {model_dir.name} model_id={model_id}")


def _json_path(model_dir: Path, model_id: int | None) -> Path:
    path = model_dir / ("model_data.json" if model_id is None else f"model_data{model_id}.json")
    if not path.exists():
        raise FactoryError(f"missing model metadata: {path}")
    return path


def _point_from_matrix(value: Any, scale: Sequence[float]) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) < 3 or any(not isinstance(row, list) or len(row) < 4 for row in value[:3]):
        raise FactoryError("semantic point matrix is malformed")
    return tuple(float(value[i][3]) * scale[i] for i in range(3))


def load_model_spec(asset_root: str | Path, model_name: str, *, model_id: int | None = 0, asset_id: str | None = None) -> ModelSpec:
    root = Path(asset_root)
    model_dir = root / "objects" / model_name
    if not model_dir.is_dir():
        raise FactoryError(f"asset directory does not exist: {model_dir}")
    metadata_path = _json_path(model_dir, model_id)
    points_path = model_dir / "points_info.json"
    if not points_path.exists():
        raise FactoryError(f"missing points metadata: {points_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    points = json.loads(points_path.read_text(encoding="utf-8"))
    scale = validate_scale(metadata.get("scale", ()))
    extents_raw = metadata.get("extents")
    center_raw = metadata.get("center")
    if not isinstance(extents_raw, list) or len(extents_raw) != 3 or not isinstance(center_raw, list) or len(center_raw) != 3:
        raise FactoryError("model metadata must provide three-axis center/extents")
    extents = tuple(float(value) for value in extents_raw)
    center = tuple(float(value) for value in center_raw)
    semantic: dict[str, tuple[float, float, float]] = {}
    matrices = metadata.get("contact_points_pose", [])
    if matrices:
        semantic["contact_0"] = _point_from_matrix(matrices[0], scale)
    functional = metadata.get("functional_matrix", [])
    if functional:
        semantic["functional_0"] = _point_from_matrix(functional[0], scale)
    collision_dir = model_dir / "collision"
    visual_dir = model_dir / "visual"
    collision_base = collision_dir.exists() and any(collision_dir.glob("base*.glb"))
    visual_base = visual_dir.exists() and any(visual_dir.glob("base*.glb"))
    collision = _asset_file(collision_dir if collision_dir.exists() else model_dir, "base" if collision_base else "textured", model_id)
    visual = _asset_file(visual_dir if visual_dir.exists() else model_dir, "base" if visual_base else "textured", model_id)
    source_paths = (metadata_path, points_path, collision, visual)
    return ModelSpec(
        asset_id=asset_id or f"{model_name}__{model_id}",
        model_name=model_name,
        model_id=model_id,
        model_data_path=str(metadata_path),
        points_info_path=str(points_path),
        collision_path=str(collision),
        visual_path=str(visual),
        effective_scale=scale,
        unscaled_extents=extents,
        scaled_extents=tuple(extents[i] * scale[i] for i in range(3)),
        center=center,
        semantic_points=semantic,
        source_hashes={str(path): sha256_file(path) for path in source_paths},
    )


def build_actor(scene: Any, spec: ModelSpec, pose: Any, *, convex: bool = True, dynamic: bool = True, name: str | None = None) -> Any:
    """Build visual/collision geometry with one explicit effective scale.

    No mass setter or legacy Actor wrapper is called here.  The returned
    native entity must be read back at all four stages before qualification.
    """

    try:
        builder = scene.create_actor_builder()
        builder.set_physx_body_type("dynamic" if dynamic else "static")
        if convex:
            builder.add_multiple_convex_collisions_from_file(filename=spec.collision_path, scale=spec.effective_scale)
        else:
            builder.add_nonconvex_collision_from_file(filename=spec.collision_path, scale=spec.effective_scale)
        builder.add_visual_from_file(filename=spec.visual_path, scale=spec.effective_scale)
        actor = builder.build(name=name or spec.asset_id)
        actor.set_pose(pose)
        return actor
    except Exception as exc:
        raise FactoryError(f"native actor build failed for {spec.asset_id}: {exc}") from exc


def capture_native_readback(actor: Any, *, stage: str, spec: ModelSpec) -> dict[str, Any]:
    """Capture available native properties without inventing missing values."""

    components = actor.get_components() if hasattr(actor, "get_components") else []
    dynamic = next((component for component in components if "RigidDynamic" in type(component).__name__), None)
    if dynamic is None:
        raise AssetReadbackError(f"no dynamic rigid component at stage {stage}")
    result: dict[str, Any] = {
        "stage": stage,
        "asset_id": spec.asset_id,
        "frame": "actor",
        "units": {"mass": "kg", "inertia": "kg*m^2"},
        "dynamic": True,
        "wrapper_applied": False,
        "mass": None,
        "mass_available": False,
        "inertia_principal": None,
        "inertia_tensor": None,
        "inertia_available": False,
        "com": None,
        "com_available": False,
        "mass_frame_quaternion": None,
    }
    mass_method = getattr(dynamic, "get_mass", None)
    if callable(mass_method):
        result["mass"] = float(mass_method())
        result["mass_available"] = True
    elif hasattr(dynamic, "mass"):
        result["mass"] = float(dynamic.mass)
        result["mass_available"] = True
    cmass_method = getattr(dynamic, "get_cmass_local_pose", None)
    if callable(cmass_method):
        cmass_pose = cmass_method()
        position = getattr(cmass_pose, "p", None)
        quaternion = getattr(cmass_pose, "q", None)
        if position is not None:
            result["com"] = position.tolist() if hasattr(position, "tolist") else list(position)
            result["com_available"] = True
        if quaternion is not None:
            result["mass_frame_quaternion"] = quaternion.tolist() if hasattr(quaternion, "tolist") else list(quaternion)
    for method_name in ("get_inertia", "get_inertia_tensor"):
        method = getattr(dynamic, method_name, None)
        if callable(method):
            value = method()
            principal = value.tolist() if hasattr(value, "tolist") else list(value)
            if isinstance(principal, list) and len(principal) == 3 and all(not isinstance(item, list) for item in principal):
                result["inertia_principal"] = principal
                quaternion = result.get("mass_frame_quaternion") or [1.0, 0.0, 0.0, 0.0]
                if len(quaternion) == 4:
                    w, x, y, z = (float(item) for item in quaternion)
                    rotation = [
                        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
                    ]
                    result["inertia_tensor"] = principal_to_actor_tensor(principal, rotation)
                    result["inertia_available"] = True
            elif isinstance(principal, list) and len(principal) == 3 and all(isinstance(item, list) for item in principal):
                result["inertia_tensor"] = principal
                result["inertia_available"] = True
            break
    return result
