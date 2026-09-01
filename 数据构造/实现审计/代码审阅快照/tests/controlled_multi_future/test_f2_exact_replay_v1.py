import json
from pathlib import Path
import unittest

from controlled_multi_future.f2_exact_replay_v1 import (
    FROZEN_RANKS,
    build_f2_exact_replay_v1,
    f2_exact_replay_budget_v1,
    finalize_f2_exact_replay_v1,
)


AUDIT = Path("/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计")


class F2ExactReplayV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(
            (AUDIT / "F2_OFFICIAL_ASSET_COMPATIBILITY_MATRIX_V3.json").read_text(
                encoding="utf-8"
            )
        )
        cls.screening = json.loads(
            (AUDIT / "F2_CPU_STATIC_SCREENING_V3.json").read_text(encoding="utf-8")
        )

    def test_exact_frozen_rank50_61_and_no_redesign(self):
        contract = build_f2_exact_replay_v1(self.matrix, self.screening)
        self.assertEqual(contract["candidate_ranks"], list(FROZEN_RANKS))
        for key in (
            "inside_on_beside_verifier_changed",
            "asset_changed",
            "layout_changed",
            "planner_changed",
            "threshold_changed",
            "release_changed",
            "candidate_rank_changed",
        ):
            self.assertFalse(contract[key])

    def test_budget_is_exactly_bounded_and_gpu0_7(self):
        budget = f2_exact_replay_budget_v1()
        self.assertEqual(budget["maximum_dynamic_candidates"], 12)
        self.assertEqual(budget["allowed_physical_gpu_indices"], list(range(8)))
        self.assertFalse(budget["fallback_beyond_rank61"])

    def test_terminal_exhaustion_requires_all_twelve_in_order(self):
        result = {
            "dynamic_candidate_receipts": [
                {"rank": rank} for rank in FROZEN_RANKS
            ],
            "selected_binding": None,
            "development_root": None,
        }
        terminal = finalize_f2_exact_replay_v1(result)
        self.assertEqual(terminal["status"], "ALL_12_DYNAMIC_CANDIDATES_EXHAUSTED")
        with self.assertRaises(ValueError):
            finalize_f2_exact_replay_v1(
                {**result, "dynamic_candidate_receipts": [{"rank": 50}]}
            )

    def test_terminal_pass_requires_accepted_three_branch_root(self):
        terminal = finalize_f2_exact_replay_v1(
            {
                "dynamic_candidate_receipts": [{"rank": 50}],
                "selected_binding": {"binding_sha256": "a" * 64},
                "development_root": {
                    "status": "accepted",
                    "branch_execution_attempt_count": 3,
                },
                "branch_execution_attempt_count": 3,
            }
        )
        self.assertEqual(terminal["status"], "PASS_TEMPLATE")


if __name__ == "__main__":
    unittest.main()
