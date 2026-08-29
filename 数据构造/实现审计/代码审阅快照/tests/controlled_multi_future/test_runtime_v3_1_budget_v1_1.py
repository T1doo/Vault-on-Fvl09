import unittest

from controlled_multi_future.runtime_v3_1_budget_v1_1 import (
    SUPPORTED_SCOPES,
    budget_artifact,
    budget_receipt_sha256,
    scope_budget,
    validate_runtime_receipt_against_budget,
    validate_scope_budget,
)


class RuntimeBudgetV1_1Test(unittest.TestCase):
    def test_all_future_scopes_are_machine_registered_but_only_a0_requestable(self):
        self.assertEqual(len(SUPPORTED_SCOPES), 6)
        requestable = [scope for scope in SUPPORTED_SCOPES if scope_budget(scope)["currently_requestable"]]
        self.assertEqual(requestable, ["A0_current_anchor_smoke"])
        artifact = budget_artifact()
        self.assertFalse(artifact["approved"])
        self.assertFalse(artifact["frozen"])
        self.assertFalse(artifact["gpu_probe_authorized"])
        self.assertEqual(artifact["budget_receipt_sha256"], budget_receipt_sha256())

    def test_scope_budget_tampering_fails(self):
        value = scope_budget("F2_beside_nonformal_probe")
        validate_scope_budget("F2_beside_nonformal_probe", value)
        value["planner_query_limit_total"] = 17
        with self.assertRaises(ValueError):
            validate_scope_budget("F2_beside_nonformal_probe", value)

    def test_a0_budget_enforced_in_code(self):
        valid = {
            "scenes": [{}, {}, {}, {}],
            "post_setup_planner_query_count": 0,
            "post_setup_controlled_action_count": 0,
        }
        self.assertTrue(validate_runtime_receipt_against_budget("A0_current_anchor_smoke", valid)["pass"])
        valid["post_setup_planner_query_count"] = 1
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget("A0_current_anchor_smoke", valid)

    def test_family_budget_envelopes_are_fail_closed(self):
        f1 = {
            "branch_receipts": [
                {"rollout_planner_query_count": 12},
                {"rollout_planner_query_count": 12},
                {"rollout_planner_query_count": 12},
            ],
            "recovery_attempt_count": 0,
        }
        self.assertTrue(validate_runtime_receipt_against_budget("F1_three_branch_nonformal_probe", f1)["pass"])
        f1["branch_receipts"][2]["rollout_planner_query_count"] = 13
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget("F1_three_branch_nonformal_probe", f1)

        f2 = {
            "planner_variant_receipts": [{}] * 6,
            "planner_solvability_query_count_total": 15,
            "rollout_planner_query_count": 1,
            "execution_attempt_count": 1,
        }
        self.assertTrue(validate_runtime_receipt_against_budget("F2_beside_nonformal_probe", f2)["pass"])
        f2["planner_solvability_query_count_total"] = 16
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget("F2_beside_nonformal_probe", f2)

        f3 = {
            "attempts": [{"attempt_kind": "diagnosis"}, {"attempt_kind": "correction"}],
            "planner_query_count_by_run": [
                {"attempt_kind": "diagnosis", "planner_solvability_query_count": 8, "rollout_planner_query_count": 8},
                {"attempt_kind": "correction", "planner_solvability_query_count": 8, "rollout_planner_query_count": 8},
            ],
        }
        self.assertTrue(validate_runtime_receipt_against_budget("F3_release_diagnosis_nonformal_probe", f3)["pass"])
        f3["attempts"].append({"attempt_kind": "correction", "rollout_planner_query_count": 0})
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget("F3_release_diagnosis_nonformal_probe", f3)

        f4 = {
            "planner_variant_receipts": [{"planner_query_count": 16}, {"planner_query_count": 16}],
            "execution_attempt_count": 2,
        }
        self.assertTrue(validate_runtime_receipt_against_budget("F4_common_carry_nonformal_probe", f4)["pass"])
        f4["planner_variant_receipts"].append({"planner_query_count": 0})
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget("F4_common_carry_nonformal_probe", f4)


if __name__ == "__main__":
    unittest.main()
