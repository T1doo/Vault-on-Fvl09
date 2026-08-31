from pathlib import Path
import tempfile
import unittest

import numpy as np

from controlled_multi_future.development_video_capture_v1 import (
    DevelopmentTrajectoryMP4RecorderV1,
    validate_development_trajectory_mp4_receipt_v1,
)


class _Cameras:
    def __init__(self):
        self.value = 0

    def update_picture(self):
        self.value += 1

    def get_rgb(self):
        return {
            "head_camera": {
                "rgb": np.full((16, 16, 3), self.value, dtype=np.uint8)
            }
        }


class _Scene:
    def __init__(self):
        self.cameras = _Cameras()
        self._step_index = 1

    def _update_render(self):
        return None


class DevelopmentVideoCaptureV1Test(unittest.TestCase):
    def test_receipt_is_development_not_stage0(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trajectory.mp4"
            scene = _Scene()
            recorder = DevelopmentTrajectoryMP4RecorderV1(path)
            recorder.capture(scene, step_index=0, force=True)
            receipt = recorder.close(scene, terminal_status="accepted")
            audit = validate_development_trajectory_mp4_receipt_v1(
                receipt, expected_path=path
            )
            self.assertTrue(audit["pass"])
            self.assertTrue(receipt["development_data"])
            self.assertFalse(receipt["stage0_data"])
            self.assertFalse(receipt["formal_data"])


if __name__ == "__main__":
    unittest.main()
