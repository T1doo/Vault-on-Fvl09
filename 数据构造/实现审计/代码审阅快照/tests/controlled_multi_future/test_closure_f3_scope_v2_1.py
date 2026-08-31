import unittest
from unittest.mock import patch

from controlled_multi_future.closure_f3_scope_v2 import (
    AUTH_ID as OLD_AUTH_ID,
    NAMESPACE as OLD_NAMESPACE,
    SCOPE as OLD_SCOPE,
)
from controlled_multi_future.closure_f3_scope_v2_1 import (
    AUTH_ID,
    NAMESPACE,
    SCOPE,
    budget,
    parent,
    spec,
)
from controlled_multi_future.f3_common_grasp_prefix_v2_1 import (
    IMPLEMENTATION_VERSION,
)
from controlled_multi_future.probes import gpu_guard_v2_4
from controlled_multi_future.probes.closure_f3_authorization_v2_1 import (
    consumption_sha,
    validate_consumption,
)
from controlled_multi_future.probes.closure_f3_scope_runner_v2_1 import (
    _budget as validate_child_budget,
)


class ClosureF3ScopeV2_1Tests(unittest.TestCase):
    def test_new_one_shot_identity_and_frozen_limits(self):
        self.assertNotEqual(SCOPE, OLD_SCOPE)
        self.assertNotEqual(NAMESPACE, OLD_NAMESPACE)
        self.assertNotEqual(AUTH_ID, OLD_AUTH_ID)
        frozen = budget()
        self.assertEqual(frozen["allowed_physical_gpu_indices"], list(range(8)))
        self.assertEqual(frozen["maximum_scope_invocations"], 1)
        self.assertEqual(frozen["execution_limit"], 3)
        self.assertEqual(frozen["fresh_scene_limit"], 3)
        self.assertEqual(frozen["suffix_planner_limit"], 0)
        self.assertEqual(frozen["suffix_execution_limit"], 0)
        self.assertEqual(frozen["release_execution_limit"], 0)
        self.assertFalse(frozen["automatic_retry"])
        self.assertEqual(frozen["recovery_attempts"], 0)
        planned = spec()
        self.assertTrue(planned["interface_fix_only"])
        self.assertEqual(planned["f3_common_grasp_prefix_v2"]["close_normalized_target"], 0.5)
        self.assertFalse(parent()["stage1_authorized"])

    def test_child_budget_rejects_any_suffix_release_or_recovery(self):
        base = {
            "budget_counts": {
                "planner_query_count": 16,
                "execution_attempt_count": 3,
                "recovery_attempt_count": 0,
            },
            "cleanup_records": [{}, {}, {}],
            "suffix_planner_query_count": 0,
            "suffix_execution_count": 0,
            "release_execution_count": 0,
        }
        self.assertTrue(validate_child_budget(base)["pass"])
        for key in (
            "suffix_planner_query_count",
            "suffix_execution_count",
            "release_execution_count",
        ):
            changed = dict(base)
            changed[key] = 1
            with self.assertRaises(RuntimeError):
                validate_child_budget(changed)
        changed = {**base, "budget_counts": {**base["budget_counts"], "recovery_attempt_count": 1}}
        with self.assertRaises(RuntimeError):
            validate_child_budget(changed)

    def test_guard_load_consume_validate_dispatches_v2_1(self):
        fake_authorization = {"implementation_version": IMPLEMENTATION_VERSION}
        with patch.object(
            gpu_guard_v2_4,
            "_authorization_implementation",
            return_value=IMPLEMENTATION_VERSION,
        ), patch.object(
            gpu_guard_v2_4, "load_closure_f3_v2_1", return_value="loaded"
        ) as loader:
            self.assertEqual(
                gpu_guard_v2_4._load_runtime_authorization(
                    "unused", requested_scope=SCOPE
                ),
                "loaded",
            )
            loader.assert_called_once()
        with patch.object(
            gpu_guard_v2_4, "consume_closure_f3_v2_1", return_value="consumed"
        ) as consumer:
            self.assertEqual(
                gpu_guard_v2_4._consume_runtime_authorization(
                    fake_authorization, ledger_directory="unused"
                ),
                "consumed",
            )
            consumer.assert_called_once()
        with patch.object(
            gpu_guard_v2_4,
            "validate_closure_f3_consumption_v2_1",
            return_value="validated",
        ) as validator:
            self.assertEqual(
                gpu_guard_v2_4._validate_runtime_consumption(
                    "consumption", fake_authorization
                ),
                "validated",
            )
            validator.assert_called_once()

    def test_consumption_contract_is_unique_and_hash_bound(self):
        authorization = {"receipt_sha256": "a" * 64}
        value = {
            "schema_version": "cmf_post_stage0_f3_v2_1_consumption",
            "implementation_version": IMPLEMENTATION_VERSION,
            "authorization_id": AUTH_ID,
            "authorization_receipt_sha256": "a" * 64,
            "approved_scope": SCOPE,
            "family": "F3",
            "scene_seed": 20260829,
            "consumed_at": "2026-08-31T00:00:00+00:00",
            "max_invocations": 1,
        }
        value["consumption_receipt_sha256"] = consumption_sha(value)
        self.assertEqual(validate_consumption(value, authorization), value)
        changed = dict(value)
        changed["approved_scope"] = OLD_SCOPE
        with self.assertRaises(Exception):
            validate_consumption(changed, authorization)


if __name__ == "__main__":
    unittest.main()
