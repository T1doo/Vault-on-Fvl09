"""Per-trajectory MP4 audit video for Stage-0 smoke data.

The primary control stream remains 250 Hz.  Video is an audit-only 25 fps
head-camera stream sampled every ten control steps, plus exact initial/final
frames.  A video never substitutes for raw actions, states or verifier truth.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

import imageio.v2 as imageio
import numpy as np

from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_stage0_trajectory_mp4_v1"
VIDEO_FPS = 25
CONTROL_FREQUENCY_HZ = 250
SAMPLE_STRIDE_STEPS = CONTROL_FREQUENCY_HZ // VIDEO_FPS
CAMERA_NAME = "head_camera"


def _sha(value: Any) -> str:
    return canonical_hash_json(value)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame(scene, camera_name: str) -> np.ndarray:
    if hasattr(scene, "_update_render"):
        scene._update_render()
    cameras = getattr(scene, "cameras", None)
    if cameras is None or not hasattr(cameras, "update_picture"):
        raise RuntimeError("Stage 0 video requires the RoboTwin camera manager")
    cameras.update_picture()
    values = cameras.get_rgb()
    if camera_name not in values or "rgb" not in values[camera_name]:
        raise RuntimeError(f"Stage 0 video camera is missing: {camera_name}")
    rgb = np.asarray(values[camera_name]["rgb"])
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.shape[0] < 2 or rgb.shape[1] < 2:
        raise ValueError("Stage 0 video frame must have shape [H,W,3]")
    if rgb.dtype != np.uint8:
        if np.issubdtype(rgb.dtype, np.floating) and np.nanmax(rgb) <= 1.0:
            rgb = np.rint(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
        else:
            rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(rgb)


class Stage0TrajectoryMP4RecorderV1:
    def __init__(
        self,
        output_path: Path,
        *,
        camera_name: str = CAMERA_NAME,
        video_fps: int = VIDEO_FPS,
        control_frequency_hz: int = CONTROL_FREQUENCY_HZ,
    ):
        self.output_path = Path(output_path).resolve()
        if self.output_path.suffix.lower() != ".mp4":
            raise ValueError("Stage 0 trajectory video must use .mp4")
        if self.output_path.exists():
            raise FileExistsError(self.output_path)
        if video_fps <= 0 or control_frequency_hz <= 0:
            raise ValueError("Stage 0 video frequencies must be positive")
        if control_frequency_hz % video_fps != 0:
            raise ValueError("Stage 0 video fps must divide control frequency")
        self.camera_name = str(camera_name)
        self.video_fps = int(video_fps)
        self.control_frequency_hz = int(control_frequency_hz)
        self.sample_stride_steps = self.control_frequency_hz // self.video_fps
        self.partial_path = self.output_path.with_suffix(".partial.mp4")
        if self.partial_path.exists():
            raise FileExistsError(self.partial_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.writer = imageio.get_writer(
            str(self.partial_path),
            format="FFMPEG",
            mode="I",
            fps=self.video_fps,
            codec="libx264",
            macro_block_size=2,
            ffmpeg_log_level="error",
        )
        self.frame_count = 0
        self.frame_shape = None
        self.sampled_step_indices: list[int] = []
        self.last_sampled_step = None
        self.closed = False
        self.receipt = None

    def capture(self, scene, *, step_index: int, force: bool = False) -> bool:
        if self.closed:
            raise RuntimeError("Stage 0 video recorder is already closed")
        step_index = int(step_index)
        if not force and step_index % self.sample_stride_steps != 0:
            return False
        if self.last_sampled_step == step_index:
            return False
        rgb = _frame(scene, self.camera_name)
        if self.frame_shape is None:
            self.frame_shape = list(rgb.shape)
        elif list(rgb.shape) != self.frame_shape:
            raise RuntimeError("Stage 0 video frame shape changed within trajectory")
        self.writer.append_data(rgb)
        self.frame_count += 1
        self.sampled_step_indices.append(step_index)
        self.last_sampled_step = step_index
        return True

    def close(self, scene, *, terminal_status: str) -> dict[str, Any]:
        if self.closed:
            return dict(self.receipt)
        try:
            final_step = max(0, int(getattr(scene, "_step_index", 0)) - 1)
            self.capture(scene, step_index=final_step, force=True)
        finally:
            try:
                self.writer.close()
            finally:
                self.closed = True
        if self.frame_count < 1 or not self.partial_path.is_file():
            raise RuntimeError("Stage 0 trajectory video produced no MP4 frames")
        os.replace(self.partial_path, self.output_path)
        value = {
            "schema_version": SCHEMA_VERSION,
            "formal_data": False,
            "stage0_data": True,
            "stage0_is_pilot_smoke": True,
            "camera_name": self.camera_name,
            "video_fps": self.video_fps,
            "control_frequency_hz": self.control_frequency_hz,
            "sample_stride_steps": self.sample_stride_steps,
            "frame_count": self.frame_count,
            "frame_shape": self.frame_shape,
            "sampled_step_indices": list(self.sampled_step_indices),
            "includes_initial_frame": 0 in self.sampled_step_indices,
            "includes_final_frame": final_step in self.sampled_step_indices,
            "terminal_status_at_close": str(terminal_status),
            "path": str(self.output_path),
            "bytes": self.output_path.stat().st_size,
            "file_sha256": _file_sha256(self.output_path),
        }
        value["receipt_sha256"] = _sha(value)
        self.receipt = value
        return dict(value)

    def abort(self) -> None:
        if not self.closed:
            try:
                self.writer.close()
            finally:
                self.closed = True
        if self.partial_path.exists():
            self.partial_path.unlink()


def validate_stage0_trajectory_mp4_receipt_v1(
    value: Mapping[str, Any], *, expected_path: Path | None = None
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("Stage 0 trajectory video receipt is missing")
    receipt = canonical_jsonable(value)
    payload = dict(receipt)
    digest = payload.pop("receipt_sha256", None)
    path = Path(str(receipt.get("path", ""))).resolve()
    checks = {
        "schema": receipt.get("schema_version") == SCHEMA_VERSION,
        "data_role": receipt.get("formal_data") is False
        and receipt.get("stage0_data") is True
        and receipt.get("stage0_is_pilot_smoke") is True,
        "frequency": receipt.get("video_fps") == VIDEO_FPS
        and receipt.get("control_frequency_hz") == CONTROL_FREQUENCY_HZ
        and receipt.get("sample_stride_steps") == SAMPLE_STRIDE_STEPS,
        "frames": int(receipt.get("frame_count", 0)) >= 1
        and receipt.get("includes_initial_frame") is True
        and receipt.get("includes_final_frame") is True,
        "path": path.suffix.lower() == ".mp4"
        and (expected_path is None or path == Path(expected_path).resolve()),
        "file": path.is_file()
        and path.stat().st_size == int(receipt.get("bytes", -1))
        and _file_sha256(path) == receipt.get("file_sha256"),
        "self_hash": isinstance(digest, str) and _sha(payload) == digest,
    }
    result = {"checks": checks, "pass": all(checks.values()), "receipt": receipt}
    if not result["pass"]:
        raise ValueError(f"Stage 0 trajectory MP4 receipt failed: {checks}")
    return result


__all__ = [
    "CAMERA_NAME",
    "CONTROL_FREQUENCY_HZ",
    "SAMPLE_STRIDE_STEPS",
    "SCHEMA_VERSION",
    "Stage0TrajectoryMP4RecorderV1",
    "VIDEO_FPS",
    "validate_stage0_trajectory_mp4_receipt_v1",
]
