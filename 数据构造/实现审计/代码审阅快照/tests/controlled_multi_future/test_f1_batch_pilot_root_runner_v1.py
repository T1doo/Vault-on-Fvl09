import inspect
import unittest

from controlled_multi_future import f1_batch_pilot_root_runner_v1


class F1BatchPilotRootRunnerV1Test(unittest.TestCase):
    def test_runner_requires_development_raw_video_and_never_promotes(self):
        source = inspect.getsource(f1_batch_pilot_root_runner_v1)
        self.assertIn("development_video_required=True", source)
        self.assertIn('"formal_data": False', source)
        self.assertIn('"stage0_data": False', source)
        self.assertIn('"stage1_authorized": False', source)
        self.assertIn('"accepted_root_increment": 0', source)
        self.assertIn("verify_raw_artifact_integrity", source)
        self.assertIn("validate_development_trajectory_mp4_receipt_v1", source)


if __name__ == "__main__":
    unittest.main()
