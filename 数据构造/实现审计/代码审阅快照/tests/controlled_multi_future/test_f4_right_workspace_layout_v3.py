import json
import tempfile
import unittest
from pathlib import Path

from controlled_multi_future.f4_right_workspace_layout_v3 import (
    LAYOUT,
    LAYOUT_VERSION,
    build_impact_review,
    write_review,
)


class F4RightWorkspaceLayoutV3Test(unittest.TestCase):
    def test_uniform_right_workspace_layout_passes_cpu_geometry(self):
        review = build_impact_review()
        self.assertTrue(review["pass"])
        self.assertEqual(review["layout"]["layout_version"], LAYOUT_VERSION)
        self.assertGreaterEqual(review["object_pairwise_minimum_m"], 0.10)
        self.assertGreaterEqual(review["slot_pairwise_minimum_m"], 0.10)
        self.assertTrue(all(review["checks"].values()))
        self.assertEqual(
            review["layout"]["common_x_pose"],
            [0.28, 0.10, 0.762, 1.0, 0.0, 0.0, 0.0],
        )
        self.assertEqual(review["layout"]["tray"]["model_id"], 0)

    def test_historical_repair_review_serializes(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "review.json"
        written = write_review(path)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), written)


if __name__ == "__main__":
    unittest.main()
