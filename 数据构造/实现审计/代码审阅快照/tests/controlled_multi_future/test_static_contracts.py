import unittest
from pathlib import Path

from controlled_multi_future.base import ImplementationAuditError
from controlled_multi_future.families import F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder
from controlled_multi_future.schemas import validate_probe_receipt
from controlled_multi_future.signals import beside_annulus, inside_volume, top_surface_region
from controlled_multi_future.verifiers import classify_exclusive_relation, completion_frame, verify_motion_event


class StaticContractsTest(unittest.TestCase):
    def test_each_family_has_exactly_three_frozen_programs(self):
        for cls in (F1ObjectSelection, F2TargetRelation, F3MotionOrder, F4SubtaskOrder):
            self.assertEqual(len(cls().checked_provisional_programs()), 3)

    def test_f3_programs_and_shared_first_v(self):
        programs = F3MotionOrder().checked_provisional_programs()
        seqs = ["".join(step["axis"] for step in program["steps"]) for program in programs]
        self.assertEqual(seqs, ["VVHH", "VHVH", "VHHV"])
        self.assertTrue(all(sequence.startswith("V") for sequence in seqs))

    def test_f4_programs(self):
        programs = F4SubtaskOrder().checked_provisional_programs()
        orders = ["".join(step["object"] for step in program["steps"][1:]) for program in programs]
        self.assertEqual(orders, ["ABC", "ACB", "BAC"])
        self.assertTrue(all(program["steps"][0]["object"] == "common_X" for program in programs))

    def test_runtime_fails_closed(self):
        with self.assertRaises(ImplementationAuditError):
            F1ObjectSelection().rollout({}, {})

    def test_probe_receipt_requires_nonformal_finite_budget(self):
        root = Path("/tmp/probe_outputs")
        receipt = {"formal_data": False, "stage0_data": False, "purpose": "implementation_audit", "timeout_seconds": 10, "attempt_limit": 1, "output_root": str(root)}
        validate_probe_receipt(receipt, root)
        receipt["formal_data"] = True
        with self.assertRaises(ValueError):
            validate_probe_receipt(receipt, root)

    def test_relation_predicates_are_separable(self):
        self.assertTrue(inside_volume([0, 0, 0], [-1, -1, -1], [1, 1, 1]))
        self.assertTrue(top_surface_region([0, 0, 1], [0, 0, 1], [0.2, 0.2], 0.01))
        self.assertTrue(beside_annulus([0.3, 0, 0], [0, 0, 0], 0.2, 0.4, 0.01))
        self.assertEqual(classify_exclusive_relation(inside=True, on=False, beside=False), "inside")
        self.assertIsNone(classify_exclusive_relation(inside=True, on=True, beside=False))

    def test_f3_metrics_and_f4_completion(self):
        samples = [[0, 0, 0], [0, 0, 0.1], [0, 0, -0.1], [0, 0, 0]]
        result = verify_motion_event(samples, [0, 0, 0], 2, 0.09, 0.001, 0.001)
        self.assertTrue(result["pass"])
        self.assertEqual(completion_frame([False, True, True, True], 3), 1)


if __name__ == "__main__":
    unittest.main()
