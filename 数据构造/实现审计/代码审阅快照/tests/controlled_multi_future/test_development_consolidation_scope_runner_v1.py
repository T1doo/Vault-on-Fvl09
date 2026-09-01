import unittest

from controlled_multi_future.probes.development_consolidation_scope_runner_v1 import (
    _apply_dispatch_terminal,
)


class DevelopmentConsolidationScopeRunnerV1Tests(unittest.TestCase):
    def test_family_terminal_is_not_dropped(self):
        outer = {"status": "running", "result": None, "job_terminal": None}
        terminal = {"status": "ALL_12_DYNAMIC_CANDIDATES_EXHAUSTED"}
        result = _apply_dispatch_terminal(
            outer,
            {
                "result": {"status": "higher_level_redesign_required"},
                "terminal": terminal,
                "scope_completed": True,
                "pass": False,
            },
        )
        self.assertEqual(result["job_terminal"], terminal)
        self.assertEqual(result["status"], "completed_with_failure_evidence")
        self.assertTrue(result["scope_completed"])
        self.assertFalse(result["pass"])


if __name__ == "__main__":
    unittest.main()
