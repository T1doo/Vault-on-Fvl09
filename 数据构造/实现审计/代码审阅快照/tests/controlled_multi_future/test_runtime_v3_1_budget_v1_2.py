import copy
import unittest

from controlled_multi_future.runtime_v3_1_budget_v1_2 import (
    SUPPORTED_SCOPES,
    authorization_common_limits,
    budget_artifact,
    scope_budget,
    validate_runtime_receipt_against_budget,
    validate_scope_budget,
)


class RuntimeBudgetV1_2Test(unittest.TestCase):
    def test_all_pre_stage0_scopes_are_user_authorized_but_stage0_is_false(self):
        artifact = budget_artifact()
        self.assertTrue(artifact["approved"])
        self.assertTrue(artifact["frozen"])
        self.assertTrue(artifact["gpu_probe_authorized"])
        self.assertFalse(artifact["stage0_authorized"])
        self.assertEqual(set(artifact["scopes"]), set(SUPPORTED_SCOPES))
        self.assertTrue(all(item["user_authorized"] for item in artifact["scopes"].values()))

    def test_a0_physics_is_an_explicit_zero_limit(self):
        budget = scope_budget("A0_current_anchor_smoke")
        self.assertEqual(budget["post_setup_physics_step_limit"], 0)
        self.assertEqual(authorization_common_limits("A0_current_anchor_smoke"), (0, 0, 0, 600))
        receipt = {
            "scenes": [{}, {}, {}, {}],
            "post_setup_planner_query_count": 0,
            "post_setup_controlled_action_count": 0,
            "post_setup_physics_step_count": 0,
            "orphan_process_count": 0,
        }
        self.assertTrue(validate_runtime_receipt_against_budget("A0_current_anchor_smoke", receipt)["pass"])
        receipt["post_setup_physics_step_count"] = 1
        with self.assertRaises(ValueError):
            validate_runtime_receipt_against_budget("A0_current_anchor_smoke", receipt)

    def test_scope_budget_tampering_fails(self):
        for scope in SUPPORTED_SCOPES:
            with self.subTest(scope=scope):
                value = scope_budget(scope)
                validate_scope_budget(scope, value)
                changed = copy.deepcopy(value)
                changed["automatic_retry"] = True
                with self.assertRaises(ValueError):
                    validate_scope_budget(scope, changed)


if __name__ == "__main__":
    unittest.main()
