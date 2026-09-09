"""Render one accepted F2/F3 root from immutable measured states.

This is a display-only process.  Scene construction is used to recreate the
camera/asset registry, after which physics stepping and task actions are
prohibited and every rendered frame is restored from the accepted trace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import traceback
import types
from pathlib import Path
from typing import Any

import numpy as np

from ..probes.lifecycle import initialize_cleanup_fields, managed_scene
from ..probes.scene_inspection import _args
from .canonical import atomic_write_json, canonical_sha256, sha256_file
from .f2_scene import RedesignF2Scene
from .hd_recorder import FONT, Recorder as NativeRecorder
from .scene import RedesignF3Scene


WORKSPACE = Path("/nfs_share/lijunhui")
VAULT = WORKSPACE / "Vault-on-Fvl09"
VIDEO_ROOT = VAULT / "数据构造" / "演示视频"
FFMPEG = WORKSPACE / "Robotwin2" / "env" / "bin" / "ffmpeg"
FFPROBE = WORKSPACE / "Robotwin2" / "env" / "bin" / "ffprobe"
ROOTS = {
    "F2-A": ("F2", "根组A"),
    "F2-B": ("F2", "根组B"),
    "F3-A": ("F3", "根组A"),
    "F3-B": ("F3", "根组B"),
}


def _sample_indices(count: int) -> list[int]:
    if count < 2:
        raise ValueError("at least two measured states required")
    return sorted(set([*range(0, count, 10), count - 1]))


def _load_trace(path: Path) -> dict[str, Any]:
    if not path.resolve().is_relative_to(WORKSPACE):
        raise ValueError("trace leaves workspace")
    with np.load(path, allow_pickle=False) as saved:
        qpos = saved["joint_qpos"].copy()
        qvel = saved["joint_qvel"].copy()
        timestamp = saved["timestamp"].copy()
        roles = {
            key.removeprefix("role_object_pose__"): saved[key].copy()
            for key in saved.files
            if key.startswith("role_object_pose__")
        }
    count = len(qpos)
    if qpos.shape != (count, 38) or qvel.shape != (count, 38):
        raise ValueError("saved articulation must be lossless shared 38qpos+38qvel")
    if timestamp.shape != (count,) or not np.allclose(np.diff(timestamp), 0.004, atol=1e-9, rtol=0):
        raise ValueError("saved trace must use the measured 250Hz timebase")
    if not roles or any(value.shape != (count, 7) for value in roles.values()):
        raise ValueError("saved trace has an invalid role-pose layout")
    if not all(np.isfinite(value).all() for value in [qpos, qvel, timestamp, *roles.values()]):
        raise ValueError("saved trace contains non-finite state")
    return {"qpos": qpos, "qvel": qvel, "timestamp": timestamp, "roles": roles}


def _restore(scene, trace: dict[str, Any], index: int, sapien) -> None:
    if scene.robot.left_entity is not scene.robot.right_entity:
        raise ValueError("render scene does not expose the shared 38-DOF articulation")
    entity = scene.robot.left_entity
    if len(entity.get_qpos()) != 38 or set(scene.role_actors) != set(trace["roles"]):
        raise ValueError("render scene differs from saved articulation/actor roles")
    entity.set_qpos(trace["qpos"][index])
    entity.set_qvel(trace["qvel"][index])
    for role, values in trace["roles"].items():
        actor = scene.role_actors[role]
        native = actor.actor if hasattr(actor, "actor") else actor
        native.set_pose(sapien.Pose(values[index, :3], values[index, 3:]))
    if not np.allclose(entity.get_qpos(), trace["qpos"][index], atol=1e-6, rtol=0):
        raise ValueError("joint restoration failed")
    for role, values in trace["roles"].items():
        actor = scene.role_actors[role]
        native = actor.actor if hasattr(actor, "actor") else actor
        pose = native.get_pose()
        actual = np.r_[pose.p, pose.q]
        target = values[index]
        if not np.allclose(actual[:3], target[:3], atol=1e-6, rtol=0):
            raise ValueError(f"role position restoration failed: {role}")
        if abs(float(np.dot(actual[3:], target[3:]))) < 1 - 1e-6:
            raise ValueError(f"role orientation restoration failed: {role}")


def _writer_factory(label: str):
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(FONT), 24)

    def factory(path, **kwargs):
        writer = imageio.get_writer(path, **kwargs)

        def append(data):
            image = Image.fromarray(data)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, image.height - 34, image.width, image.height), fill=(0, 0, 0))
            draw.text(
                (12, image.height - 31),
                f"SAVED-STATE RE-RENDER | {label} | NOT A NEW ROLLOUT",
                font=font,
                fill=(255, 255, 255),
            )
            writer.append_data(np.asarray(image))

        return types.SimpleNamespace(append_data=append, close=writer.close)

    return factory


def _probe(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(FFPROBE), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,avg_frame_rate,nb_frames", "-of", "json", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    value = json.loads(completed.stdout)["streams"][0]
    decode = subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(path), "-f", "null", "-"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
    )
    if decode.returncode:
        raise RuntimeError(f"published video decode failed: {decode.stderr[-500:]}")
    return {"width": int(value["width"]), "height": int(value["height"]), "avg_frame_rate": value["avg_frame_rate"], "nb_frames": int(value["nb_frames"]), "full_decode_pass": True}


def _publish(page1: Path, page2: Path, family: str, group: str, variant_dir: str, program: str) -> list[dict[str, Any]]:
    target = VIDEO_ROOT / family / "高清多视角_状态回放" / group / variant_dir
    target.mkdir(parents=True, exist_ok=True)
    six = target / f"{family}-{program}_六视角.mp4"
    front = target / f"{family}-{program}_前视角.mp4"
    if six.exists() or front.exists():
        raise FileExistsError(f"immutable published video target exists for {family}-{program}")
    shutil.copy2(page1, six)
    partial = front.with_suffix(".partial.mp4")
    subprocess.run(
        [str(FFMPEG), "-v", "error", "-i", str(page2), "-vf", "crop=960:720:0:0", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-threads", "2", "-movflags", "+faststart", "-an", str(partial)],
        check=True,
        timeout=900,
    )
    os.replace(partial, front)
    result = []
    for path, expected in ((six, (2880, 1440)), (front, (960, 720))):
        metadata = _probe(path)
        if (metadata["width"], metadata["height"]) != expected:
            raise ValueError("published video dimensions differ from contract")
        result.append({"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size, **metadata})
    return result


def _render_cell(*, root: dict[str, Any], cell: dict[str, Any], output: Path) -> dict[str, Any]:
    family = root["family"]
    root_id = root["root_id"]
    trace_path = Path(cell["trace"]["path"])
    trace_sha = sha256_file(trace_path)
    trace = _load_trace(trace_path)
    indices = _sample_indices(len(trace["qpos"]))
    if len(indices) > 602:
        raise ValueError("saved-state frame cap exceeded")
    import imageio_ffmpeg
    import sapien

    if not Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve().is_relative_to(WORKSPACE):
        raise ValueError("imageio encoder leaves workspace")
    sapien.render.set_camera_shader_dir("default")
    cell_output = output / f"{cell['program_id']}_{cell['realization_id']}"
    cell_output.mkdir(parents=True, exist_ok=False)
    lifecycle: dict[str, Any] = {}
    initialize_cleanup_fields(lifecycle)
    scene_cls = RedesignF2Scene if family == "F2" else RedesignF3Scene
    args = _args(family, cell_output / "scene")
    args.update({
        "seed": int(root["contract"]["scene_seed"]),
        "task_name": f"cmf_{family.lower()}_{root_id.lower()}_hd_saved_state",
        "render_freq": 0,
        "save_data": False,
        "collect_data": False,
        "need_plan": False,
    })
    if family == "F2":
        args["f2_layout_id"] = root["layout_id"]
    recorder = None
    physics_step_calls = 0
    started = time.monotonic()
    with managed_scene(scene_cls, args, lifecycle, f"hd-saved-state-{root_id}-{cell['program_id']}-{cell['realization_id']}") as scene:
        original_step = scene.scene.step

        def prohibited_step(*_args, **_kwargs):
            nonlocal physics_step_calls
            physics_step_calls += 1
            raise RuntimeError("physics stepping prohibited during saved-state replay")

        scene.scene.step = prohibited_step
        try:
            _restore(scene, trace, 0, sapien)
            recorder = NativeRecorder(scene, cell_output / "native_hd", writer_factory=_writer_factory(f"{root_id} {cell['program_id']} {cell['realization_id']}"))
            for index in indices:
                _restore(scene, trace, index, sapien)
                scene._step_index = index + 1
                recorder.capture(scene, step_index=index, force=True)
            video = recorder.close(scene, terminal_status="SAVED_STATE_RENDER_COMPLETE_NOT_NEW_ROLLOUT")
        finally:
            try:
                if recorder is not None and not recorder.closed:
                    recorder.abort(scene)
            finally:
                scene.scene.step = original_step
    if physics_step_calls:
        raise RuntimeError("saved-state replay attempted a prohibited physics step")
    if lifecycle.get("scene_cleanup_succeeded") is not True:
        raise RuntimeError("render scene cleanup failed")
    if sha256_file(trace_path) != trace_sha:
        raise RuntimeError("source trace changed during render")
    pages = video["pages"]
    if len(pages) < 2 or pages[0]["labels"] != ["head", "left_wrist", "right_wrist", "observer", "world1", "world2"]:
        raise ValueError("six-view page inventory differs from F1/F4 delivery contract")
    if not pages[1]["labels"] or "front_camera" not in pages[1]["labels"][0]:
        raise ValueError("front-camera page is absent")
    _, group = ROOTS[root_id]
    realization = cell["realization_id"]
    variant_dir = {"r_pc": "01_标准轨迹", "r_inv_path": "02_路径变化", "r_inv_motion": "03_节奏变化"}.get(realization)
    if variant_dir is None:
        raise ValueError("unknown realization-to-display-directory mapping")
    published = _publish(Path(pages[0]["path"]), Path(pages[1]["path"]), family, group, variant_dir, cell["program_id"])
    result = {
        "schema_version": "cmf_f2_f3_hd_saved_state_cell_v1",
        "pass": True,
        "root_id": root_id,
        "family": family,
        "program_id": cell["program_id"],
        "realization_id": cell["realization_id"],
        "source_trace": str(trace_path),
        "source_trace_sha256_before": trace_sha,
        "source_trace_sha256_after": sha256_file(trace_path),
        "source_trace_sample_count": len(trace["qpos"]),
        "sampled_state_indices": indices,
        "rendered_frame_count": video["frame_count"],
        "native_camera_resolution": video["native_camera_resolution"],
        "mosaic_resolution": video["mosaic_resolution"],
        "video_fps": video["video_fps"],
        "views": video["views"],
        "published": published,
        "saved_state_reconstruction": True,
        "display_shader": "default_native_raster",
        "new_physical_rollout": False,
        "task_action_count": 0,
        "collection_attempts": 0,
        "solver_problem_count": 0,
        "production_fresh_scene_count": 0,
        "display_scene_count": 1,
        "physics_step_calls_after_setup": physics_step_calls,
        "primary_data_modified": False,
        "lifecycle": lifecycle,
        "elapsed_seconds": time.monotonic() - started,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    atomic_write_json(cell_output / "cell_render_receipt.json", result)
    return result


def run(root_receipt: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    source_sha = sha256_file(root_receipt)
    root = json.loads(root_receipt.read_text(encoding="utf-8"))
    root_id = root.get("root_id")
    if root_id not in ROOTS or root.get("accepted") is not True or root.get("status") != "ACCEPTED":
        raise ValueError("HD source must be one of the four final accepted roots")
    family, _ = ROOTS[root_id]
    if root.get("family") != family or len(root.get("cells", [])) != 6:
        raise ValueError("accepted root family/cell count differs")
    expected_programs = {"inside", "on", "beside"} if family == "F2" else {"VVHH", "VHVH", "VHHV"}
    realizations = {cell.get("realization_id") for cell in root["cells"]}
    expected_realizations = {"r_pc", "r_inv_path"} if root_id.endswith("A") else {"r_pc", "r_inv_motion"}
    if realizations != expected_realizations:
        raise ValueError("HD root realization set differs from the accepted contract")
    if any(sum(cell.get("program_id") == program for cell in root["cells"]) != 2 for program in expected_programs):
        raise ValueError("HD root does not contain two realizations for every program")
    cells = []
    error = None
    started = time.monotonic()
    try:
        for cell in root["cells"]:
            cells.append(_render_cell(root=root, cell=cell, output=output))
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    result = {
        "schema_version": "cmf_f2_f3_hd_saved_state_root_v1",
        "pass": error is None and len(cells) == 6 and all(cell["pass"] for cell in cells),
        "root_id": root_id,
        "family": family,
        "source_root_receipt": str(root_receipt),
        "source_root_receipt_sha256_before": source_sha,
        "source_root_receipt_sha256_after": sha256_file(root_receipt),
        "selected_realizations": sorted(realizations),
        "cells": cells,
        "published_video_count": sum(len(cell["published"]) for cell in cells),
        "display_scene_count": len(cells),
        "new_physical_rollout_count": 0,
        "production_budget_delta": {"solver_problems": 0, "fresh_scenes": 0, "action_scenes": 0, "collection_attempts": 0},
        "error": error,
        "elapsed_seconds": time.monotonic() - started,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    atomic_write_json(output / "root_render_receipt.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(Path(args.root_receipt), Path(args.output))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
