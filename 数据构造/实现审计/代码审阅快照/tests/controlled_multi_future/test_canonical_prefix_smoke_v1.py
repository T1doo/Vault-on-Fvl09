import tempfile
import unittest
from pathlib import Path

from controlled_multi_future.canonical_prefix_smoke_v1 import (
    CanonicalPrefixRealSmokeV1,
)

from test_root_orchestrator_v1_2 import StrictPrefixSyntheticAdapter


class PrefixFailureAdapter(StrictPrefixSyntheticAdapter):
    def plan_and_execute_canonical_prefix(self, scene, prefix_contract):
        scene.reset_trace()
        scene.planner_query_count = 2
        raise RuntimeError("synthetic prefix planner failure")


class CanonicalPrefixSmokeV1Test(unittest.TestCase):
    def run_smoke(self, adapter):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "smoke"
        receipt = CanonicalPrefixRealSmokeV1(adapter).run(
            output_dir=output,
            planned_root_slot_spec={
                "slot_id": "prefix-smoke",
                "family": "F1",
                "seed": 17,
            },
        )
        return receipt, output

    def test_success_generates_once_and_replays_three_fresh_scenes(self):
        receipt, output = self.run_smoke(StrictPrefixSyntheticAdapter())
        self.assertEqual(receipt["status"], "passed_canonical_prefix_real_smoke")
        self.assertEqual(receipt["planner_query_count"], 1)
        self.assertEqual(receipt["prefix_replay_count"], 3)
        self.assertEqual(len(receipt["replays"]), 3)
        self.assertEqual(len(receipt["cleanup_records"]), 5)
        self.assertTrue((output / "artifact/canonical_prefix_artifact.json").is_file())

    def test_prefix_exception_preserves_true_query_delta_partial_trace_and_cleanup(self):
        receipt, output = self.run_smoke(PrefixFailureAdapter())
        self.assertEqual(receipt["status"], "failed_canonical_prefix_real_smoke")
        self.assertEqual(receipt["planner_query_count"], 2)
        self.assertEqual(receipt["reference_partial_trace"]["status"], "saved")
        self.assertTrue((output / "reference_partial_trace.npz").is_file())
        self.assertTrue(receipt["scene_cleanup_succeeded"])


if __name__ == "__main__":
    unittest.main()
