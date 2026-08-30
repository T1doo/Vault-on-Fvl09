import copy
import unittest

from controlled_multi_future.runtime_v3_4_budget_v1 import (
    ALLOWED_PHYSICAL_GPU_INDICES,
    SCOPE_FAMILIES,
    SUPPORTED_SCOPES,
    budget_artifact,
    scope_budget,
    validate_runtime_receipt_against_budget,
    validate_static_scope_activity_envelope,
)
from controlled_multi_future.runtime_v3_4_multi_gpu_scheduler_v1 import (
    parse_live_gpu_snapshot,
    schedule_ready_scopes,
)
from controlled_multi_future.runtime_v3_4_scope_specs_v1 import planned_scope_spec


def gpu_csv():
    rows = []
    for index in range(8):
        memory = 14 if index in (1, 4, 6) else 1000
        util = 0 if index in (1, 4, 6) else 50
        rows.append(f"{index}, GPU-{index:032d}, {memory}, {util}, P8")
    return "\n".join(rows)


class RuntimeV34BudgetSchedulerTest(unittest.TestCase):
    def test_budget_is_finite_gpu0_7_and_never_stage0(self):
        artifact = budget_artifact()
        self.assertEqual(tuple(artifact["allowed_physical_gpu_indices"]), tuple(range(8)))
        self.assertEqual(ALLOWED_PHYSICAL_GPU_INDICES, tuple(range(8)))
        self.assertFalse(artifact["stage0_authorized"])
        self.assertFalse(artifact["automatic_retry"])
        self.assertEqual(artifact["recovery_attempts"], 0)
        for scope in SUPPORTED_SCOPES:
            static = validate_static_scope_activity_envelope(scope)
            self.assertTrue(static["pass"])
            budget = scope_budget(scope)
            receipt = {
                "budget_counts": {
                    "planner_query_count": static["source_bound_static_envelope"]["planner_query_count"],
                    "execution_attempt_count": static["source_bound_static_envelope"]["execution_attempt_count"],
                    "recovery_attempt_count": 0,
                }
            }
            self.assertTrue(validate_runtime_receipt_against_budget(scope, receipt)["pass"])
            over = copy.deepcopy(receipt)
            over["budget_counts"]["execution_attempt_count"] += 1
            with self.assertRaises(ValueError):
                validate_runtime_receipt_against_budget(scope, over)

    def test_full_scopes_require_passing_targeted_receipts(self):
        self.assertEqual(planned_scope_spec("F2_inside_targeted_v10")["family"], "F2")
        with self.assertRaises(ValueError):
            planned_scope_spec("F2_full_root_v10")
        prerequisite = {
            "pass": True,
            "receipt_sha256": "a" * 64,
        }
        spec = planned_scope_spec(
            "F2_full_root_v10",
            prerequisite_receipts={"F2_inside_targeted_v10": prerequisite},
        )
        self.assertFalse(spec["stage0_authorized"])
        self.assertEqual(spec["main_object"], "071_can/base1")

    def test_parser_and_scheduler_use_any_idle_gpu_without_sharing(self):
        snapshot = {
            "gpus": parse_live_gpu_snapshot(gpu_csv(), "")
        }
        ready = [
            {"scope": scope, "family": SCOPE_FAMILIES[scope], "authorization_receipt_sha256": scope}
            for scope in (
                "F2_inside_targeted_v10",
                "F3_grasp_three_context_v10",
                "F4_corridor_A_v10",
            )
        ]
        result = schedule_ready_scopes(ready, snapshot)
        self.assertTrue(result["pass"])
        self.assertEqual(
            [item["physical_gpu_index"] for item in result["assignments"]],
            [1, 4, 6],
        )
        self.assertEqual(len({item["gpu_uuid"] for item in result["assignments"]}), 3)
        self.assertTrue(all(not item["root_sharded"] for item in result["assignments"]))

    def test_busy_process_prevents_idle_classification(self):
        process = "GPU-00000000000000000000000000000001, 1234, 512"
        snapshot = parse_live_gpu_snapshot(gpu_csv(), process)
        self.assertFalse(snapshot[1]["independently_fresh_idle"])


if __name__ == "__main__":
    unittest.main()
