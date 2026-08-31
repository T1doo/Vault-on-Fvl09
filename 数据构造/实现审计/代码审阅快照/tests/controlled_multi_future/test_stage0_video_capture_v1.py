from __future__ import annotations

import copy
import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from controlled_multi_future.stage0_smoke_family_runner_v1_1 import (
    _stage0_video_integrity,
    classify_stage0_attempt_outcome_v1_1,
)
from controlled_multi_future.stage0_video_capture_v1 import (
    Stage0TrajectoryMP4RecorderV1,
    validate_stage0_trajectory_mp4_receipt_v1,
)
from controlled_multi_future import (
    real_sapien_adapter_v1_2,
    root_orchestrator_v1_2,
    stage0_smoke_finalizer_v1_1,
)


class _Cameras:
    def __init__(self):
        self.value = 0

    def update_picture(self):
        self.value += 1

    def get_rgb(self):
        frame = np.full((16, 16, 3), self.value % 255, dtype=np.uint8)
        return {"head_camera": {"rgb": frame}}


class _Scene:
    def __init__(self):
        self.cameras = _Cameras()
        self._step_index = 1

    def _update_render(self):
        return None


class Stage0VideoCaptureV1Test(unittest.TestCase):
    def test_real_mp4_is_written_with_initial_stride_and_final_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "video" / "trajectory.mp4"
            scene = _Scene()
            recorder = Stage0TrajectoryMP4RecorderV1(path)
            recorder.capture(scene, step_index=0, force=True)
            for step in range(1, 12):
                scene._step_index = step + 1
                recorder.capture(scene, step_index=step)
            receipt = recorder.close(scene, terminal_status="accepted")
            audit = validate_stage0_trajectory_mp4_receipt_v1(
                receipt, expected_path=path
            )
            self.assertTrue(audit["pass"])
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)
            self.assertEqual(receipt["video_fps"], 25)
            self.assertEqual(receipt["sampled_step_indices"], [0, 10, 11])

    def test_video_receipt_tamper_or_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.mp4"
            scene = _Scene()
            recorder = Stage0TrajectoryMP4RecorderV1(path)
            recorder.capture(scene, step_index=0, force=True)
            receipt = recorder.close(scene, terminal_status="accepted")
            tampered = copy.deepcopy(receipt)
            tampered["frame_count"] += 1
            with self.assertRaisesRegex(ValueError, "receipt failed"):
                validate_stage0_trajectory_mp4_receipt_v1(
                    tampered, expected_path=path
                )
            path.unlink()
            with self.assertRaisesRegex(ValueError, "receipt failed"):
                validate_stage0_trajectory_mp4_receipt_v1(
                    receipt, expected_path=path
                )

    def test_generated_raw_without_mp4_is_infrastructure_failure(self):
        accepted = {"status": "accepted", "verifier": {"pass": True}}
        outcome = classify_stage0_attempt_outcome_v1_1(
            accepted,
            {"status": "accepted"},
            raw_integrity_pass=True,
            branch_receipt_present=True,
            video_integrity_pass=False,
        )
        self.assertEqual(outcome, "FAILED_INFRASTRUCTURE_WITH_EVIDENCE")
        with tempfile.TemporaryDirectory() as directory:
            audit = _stage0_video_integrity(
                Path(directory), accepted, trajectory_generated=True
            )
        self.assertFalse(audit["pass"])
        self.assertTrue(audit["required"])

    def test_no_trajectory_explicitly_marks_video_not_applicable(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = _stage0_video_integrity(
                Path(directory), None, trajectory_generated=False
            )
        self.assertTrue(audit["pass"])
        self.assertFalse(audit["required"])
        self.assertEqual(audit["status"], "video_not_applicable_no_trajectory")

    def test_stage0_orchestrator_cleanup_and_finalizer_wire_mp4_end_to_end(self):
        root_source = inspect.getsource(root_orchestrator_v1_2)
        context_source = inspect.getsource(real_sapien_adapter_v1_2)
        finalizer_source = inspect.getsource(stage0_smoke_finalizer_v1_1)
        self.assertIn("start_stage0_video_capture", root_source)
        self.assertIn('branch_dir / "video" / "trajectory.mp4"', root_source)
        self.assertIn("stage0_video_receipt", context_source)
        self.assertIn("finish_stage0_video_capture", context_source)
        self.assertIn("all_generated_trajectories_have_mp4", finalizer_source)
        self.assertIn("generated_video_count", finalizer_source)


if __name__ == "__main__":
    unittest.main()
