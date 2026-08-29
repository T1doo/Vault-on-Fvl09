import unittest

from controlled_multi_future.runtime_v3_2_budget_v1 import (
    SUPPORTED_SCOPES,
    authorization_common_limits,
    budget_artifact,
    scope_budget,
    validate_runtime_receipt_against_budget,
)


class RuntimeV3_2BudgetV1Test(unittest.TestCase):
    def test_all_scopes_are_finite_and_never_authorize_stage0(self):
        artifact = budget_artifact()
        self.assertTrue(artifact["approved"])
        self.assertFalse(artifact["stage0_authorized"])
        for scope in SUPPORTED_SCOPES:
            budget = scope_budget(scope)
            planner, execution, _, timeout = authorization_common_limits(scope)
            self.assertGreater(planner, 0)
            self.assertGreater(execution, 0)
            self.assertGreater(timeout, 0)
            self.assertFalse(budget["automatic_retry"])

    def test_budget_validator_rejects_retry_or_overrun(self):
        scope = "F1_three_branch_nonformal_probe_v3_2"
        valid = {"budget_counts": {"planner_query_count": 36, "execution_attempt_count": 3, "recovery_attempt_count": 0}}
        self.assertTrue(validate_runtime_receipt_against_budget(scope, valid)["pass"])
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget(
                scope,
                {"budget_counts": {"planner_query_count": 37, "execution_attempt_count": 3, "recovery_attempt_count": 0}},
            )


if __name__ == "__main__":
    unittest.main()
