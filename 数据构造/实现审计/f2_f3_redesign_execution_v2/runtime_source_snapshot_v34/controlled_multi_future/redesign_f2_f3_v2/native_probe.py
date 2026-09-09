"""Bounded native SAPIEN asset probe used by the V2.1 stage-A gate.

This probe creates one scene, builds the two candidate source assets with the
same explicit scale for visual and collision geometry, and records whatever
native mass/COM/inertia/material readback the installed SAPIEN exposes.  It
never wraps the actor in the legacy ``Actor`` class and never claims physical
qualification.
"""

from __future__ import annotations

import argparse
import os
import platform
import time
from pathlib import Path
from typing import Any

from .assets import AssetReadbackError, validate_inertia
from .canonical import atomic_write_json
from .factory import capture_native_readback, load_model_spec, build_actor


def _json_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def run(output: str | Path) -> dict[str, Any]:
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    receipt: dict[str, Any] = {
        "schema_version": "cmf_f2_f3_native_asset_probe_v1",
        "job_id": output_path.name,
        "pid": os.getpid(),
        "host": platform.node(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "guard_physical_index": os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX"),
        "status": "STARTING",
        "assets": [],
        "physical_qualification": "UNVERIFIED",
    }
    try:
        import sapien.core as sapien

        engine = sapien.Engine()
        from sapien.render import RenderSystem

        config = sapien.SceneConfig()
        sapien.physx.set_scene_config(config)
        device = sapien.Device("cuda:0")
        render_system = RenderSystem(device)
        scene = sapien.Scene([sapien.physx.PhysxCpuSystem(), render_system])
        scene.set_timestep(1 / 250)
        scene.default_physical_material = scene.create_physical_material(0.5, 0.5, 0.0)
        receipt["render_binding"] = {
            "logical_device": "cuda:0",
            "device_name": getattr(device, "name", None),
            "cuda_id": getattr(device, "cuda_id", None),
            "pci_bus_id": getattr(device, "pci_string", None),
            "can_render": bool(device.can_render()) if hasattr(device, "can_render") else None,
            "is_cuda": bool(device.is_cuda()) if hasattr(device, "is_cuda") else None,
        }
        asset_root = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets")
        bindings = (("f2_can_v1", "071_can", 0, [0.0, 0.0, 0.15]), ("f3_bottle_v1", "114_bottle", 1, [0.45, 0.0, 0.20]))
        for asset_id, model_name, model_id, position in bindings:
            spec = load_model_spec(asset_root, model_name, model_id=model_id, asset_id=asset_id)
            actor = build_actor(scene, spec, sapien.Pose(position, [1, 0, 0, 0]), convex=True, dynamic=True)
            stages: dict[str, Any] = {}
            for stage in ("native_before_wrapper", "after_wrapper", "after_revision"):
                try:
                    stages[stage] = capture_native_readback(actor, stage=stage, spec=spec)
                except Exception as exc:
                    stages[stage] = {"stage": stage, "available": False, "error": f"{type(exc).__name__}: {exc}"}
            scene.step()
            try:
                stages["after_settle"] = capture_native_readback(actor, stage="after_settle", spec=spec)
            except Exception as exc:
                stages["after_settle"] = {"stage": "after_settle", "available": False, "error": f"{type(exc).__name__}: {exc}"}
            for stage in stages.values():
                try:
                    validate_inertia(stage["mass"], stage["inertia_tensor"], max(spec.scaled_extents) / 2)
                    stage["inertia_bound_check"] = "PASS"
                except Exception as exc:
                    stage["inertia_bound_check"] = f"FAIL: {type(exc).__name__}: {exc}"
            receipt["assets"].append({"spec": spec.to_receipt(), "stages": _json_value(stages)})
        receipt["status"] = "COMPLETED"
        receipt["readback_complete"] = all(
            all(stage.get("mass_available") and stage.get("inertia_available") and stage.get("com_available") and stage.get("inertia_bound_check") == "PASS" for stage in item["stages"].values() if isinstance(stage, dict))
            for item in receipt["assets"]
        )
        if not receipt["readback_complete"]:
            receipt["status"] = "COMPLETED_WITH_MISSING_NATIVE_READBACK"
    except BaseException as exc:
        receipt["status"] = "FAILED"
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        receipt["elapsed_seconds"] = time.monotonic() - started
        atomic_write_json(output_path / "native_probe_receipt.json", _json_value(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = run(args.output)
    if receipt.get("status") == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
