"""Audit-only MP4 capture for nonformal development trajectories."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json
from .stage0_video_capture_v1 import Stage0TrajectoryMP4RecorderV1


SCHEMA_VERSION = "cmf_development_trajectory_mp4_v1"


def _sha(value: Any) -> str:
    return canonical_hash_json(value)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DevelopmentTrajectoryMP4RecorderV1(Stage0TrajectoryMP4RecorderV1):
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
            raise RuntimeError("development trajectory video produced no MP4 frames")
        os.replace(self.partial_path, self.output_path)
        value = {
            "schema_version": SCHEMA_VERSION,
            "formal_data": False,
            "stage0_data": False,
            "development_data": True,
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


def validate_development_trajectory_mp4_receipt_v1(
    value: Mapping[str, Any], *, expected_path: Path | None = None
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("development trajectory video receipt is missing")
    receipt = dict(value)
    payload = dict(receipt)
    claimed = payload.pop("receipt_sha256", None)
    path = Path(str(receipt.get("path", ""))).resolve()
    checks = {
        "schema": receipt.get("schema_version") == SCHEMA_VERSION,
        "labels": receipt.get("development_data") is True
        and receipt.get("formal_data") is False
        and receipt.get("stage0_data") is False,
        "self_hash": isinstance(claimed, str) and _sha(payload) == claimed,
        "path": expected_path is None or path == Path(expected_path).resolve(),
        "file": path.is_file(),
        "file_hash": path.is_file()
        and receipt.get("file_sha256") == _file_sha256(path),
        "bytes": path.is_file() and receipt.get("bytes") == path.stat().st_size,
        "frames": isinstance(receipt.get("frame_count"), int)
        and receipt["frame_count"] > 0,
        "endpoints": receipt.get("includes_initial_frame") is True
        and receipt.get("includes_final_frame") is True,
    }
    return {"checks": checks, "pass": all(checks.values())}


__all__ = [
    "DevelopmentTrajectoryMP4RecorderV1",
    "validate_development_trajectory_mp4_receipt_v1",
]
