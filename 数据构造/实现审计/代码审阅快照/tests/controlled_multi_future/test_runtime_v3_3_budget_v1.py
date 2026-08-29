import json
import unittest
from pathlib import Path

from controlled_multi_future.runtime_v3_3_budget_v1 import (
    ROOT_SCOPES,
    SUPPORTED_SCOPES,
    budget_artifact,
    scope_budget,
    validate_runtime_receipt_against_budget,
    validate_static_scope_activity_envelope,
)


VAULT_BUDGET = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "PRE_STAGE0_RUNTIME_V3_3_SCOPE_BUDGET_V1_3.json"
)


class RuntimeV3_3BudgetV1Test(unittest.TestCase):
    def test_code_budget_is_byte_semantic_equal_to_frozen_vault_artifact(self):
        self.assertEqual(
            budget_artifact(), json.loads(VAULT_BUDGET.read_text(encoding="utf-8"))
        )
        self.assertEqual(len(SUPPORTED_SCOPES), 6)
        self.assertEqual(len(ROOT_SCOPES), 4)
        self.assertFalse(budget_artifact()["stage0_authorized"])
        self.assertEqual(
            budget_artifact()["allowed_physical_gpu_indices"], list(range(8))
        )

    def test_missing_invalid_and_overrun_counts_fail_closed(self):
        scope = "F1_planner_root_per_revision"
        with self.assertRaisesRegex(ValueError, "lacks budget_counts"):
            validate_runtime_receipt_against_budget(scope, {})
        for bad in (-1, 1.5, True):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                ValueError, "nonnegative integer"
            ):
                validate_runtime_receipt_against_budget(
                    scope,
                    {
                        "budget_counts": {
                            "planner_query_count": bad,
                            "execution_attempt_count": 0,
                            "recovery_attempt_count": 0,
                        }
                    },
                )
        limit = scope_budget(scope)
        with self.assertRaisesRegex(ValueError, "exceeded"):
            validate_runtime_receipt_against_budget(
                scope,
                {
                    "budget_counts": {
                        "planner_query_count": limit["planner_query_limit"] + 1,
                        "execution_attempt_count": 0,
                        "recovery_attempt_count": 0,
                    }
                },
            )

    def test_per_scene_caps_close_under_total_budget(self):
        expected_static_planner = {
            "F1_planner_root_per_revision": 46,
            "F2_diagnosis_root_per_revision": 32,
            "F3_prefix_root_per_revision": 96,
            "F4_block_root_per_revision": 116,
        }
        for scope, expected in expected_static_planner.items():
            self.assertEqual(
                validate_static_scope_activity_envelope(scope)[
                    "source_bound_static_envelope"
                ]["planner_query_count"],
                expected,
            )
        totals = {
            "F1_planner_root_per_revision": 16 + 3 * 16,
            "F2_diagnosis_root_per_revision": 24 + 3 * 24,
            "F3_prefix_root_per_revision": 32 + 3 * 42,
            "F4_block_root_per_revision": 24 + 3 * 64,
            "F4_cube_grasp_no_action_ik": 3 * 8,
        }
        for scope, total in totals.items():
            with self.subTest(scope=scope):
                self.assertLessEqual(total, scope_budget(scope)["planner_query_limit"])
        for scope in SUPPORTED_SCOPES:
            with self.subTest(static_scope=scope):
                self.assertTrue(validate_static_scope_activity_envelope(scope)["pass"])


if __name__ == "__main__":
    unittest.main()
