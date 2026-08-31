import tempfile
import unittest
import json
from pathlib import Path

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f1_batch_generation_pilot_v1 import (
    build_f1_batch_pilot_plan_v1,
)
from controlled_multi_future.f1_batch_pilot_scope_runner_v1 import (
    F1BatchPilotScopeRunnerV1,
    validate_f1_batch_scope_budget_v1,
)
from controlled_multi_future.f1_batch_pilot_scope_v1 import (
    AUTH_ID,
    SCOPE,
    budget,
    parent,
    spec,
)
from controlled_multi_future.probes.f1_batch_pilot_authorization_v1 import (
    CONSUMPTION_SCHEMA,
    consumption_sha,
    validate_consumption,
)


def _receipt(slot_id, accepted, *, cleanup=True, planner=10, execution=3):
    value = {
        "schema_version": "synthetic_f1_batch_root_receipt_v1",
        "root_slot_id": slot_id,
        "root_status": "accepted" if accepted else "failed_planner_with_evidence",
        "accepted_development_root": accepted,
        "trajectory_count": 3 if accepted else 0,
        "pass": accepted,
        "terminal_attempt_evidence": cleanup,
        "cleanup_records": [
            {
                "cleanup_safety_pass": cleanup,
                "orphan_process_count": 0 if cleanup else 1,
            }
        ],
        "budget_counts": {
            "planner_query_count": planner,
            "execution_attempt_count": execution,
            "recovery_attempt_count": 0,
        },
        "elapsed_seconds": 1.0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "accepted_root_increment": 0,
    }
    value["receipt_sha256"] = hash_json(value)
    return value


class _Runner:
    def __init__(self, slot, outcomes):
        self.slot = slot
        self.outcomes = outcomes

    def run(self, *, output_dir, planned_root_slot_spec):
        self.assert_slot = planned_root_slot_spec["slot_id"]
        return self.outcomes[self.assert_slot]


def _scope(outcomes):
    def adapter_factory(slot, attempt_dir):
        return slot

    def root_runner_factory(slot):
        return _Runner(slot, outcomes)

    return F1BatchPilotScopeRunnerV1(
        adapter_factory=adapter_factory,
        root_runner_factory=root_runner_factory,
    )


class F1BatchPilotScopeV1Test(unittest.TestCase):
    def setUp(self):
        self.plan = build_f1_batch_pilot_plan_v1()
        self.primary_ids = [item["slot_id"] for item in self.plan["primary_slots"]]
        self.reserve_ids = [
            item["slot_id"] for item in self.plan["ordered_reserve_slots"]
        ]

    def run_scope(self, outcomes):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return _scope(outcomes).run(
            output_dir=Path(temporary.name) / "batch", plan=self.plan
        )

    def test_scope_is_finite_gpu_ready_and_development_only(self):
        frozen = budget()
        self.assertEqual(frozen["allowed_physical_gpu_indices"], list(range(8)))
        self.assertEqual(frozen["primary_root_limit"], 5)
        self.assertEqual(frozen["ordered_reserve_activation_limit"], 5)
        self.assertEqual(frozen["total_root_attempt_limit"], 10)
        self.assertEqual(frozen["trajectory_execution_limit"], 30)
        self.assertEqual(frozen["planner_query_limit"], 320)
        self.assertEqual(frozen["fresh_scene_limit"], 160)
        self.assertEqual(frozen["timeout_seconds"], 28800)
        self.assertFalse(frozen["automatic_retry"])
        self.assertFalse(frozen["root_sharding_authorized"])
        self.assertTrue(frozen["development_raw_required"])
        self.assertTrue(frozen["development_mp4_required"])
        self.assertFalse(frozen["formal_data"])
        self.assertFalse(frozen["stage0_data"])
        self.assertFalse(frozen["stage1_authorized"])
        self.assertEqual(spec()["plan_sha256"], self.plan["plan_sha256"])
        self.assertEqual(parent()["authorized_scopes"], [SCOPE])

    def test_five_primary_successes_stop_without_reserves(self):
        outcomes = {slot: _receipt(slot, True) for slot in self.primary_ids}
        result = self.run_scope(outcomes)
        self.assertTrue(result["pass"])
        self.assertTrue(result["five_accepted_roots"])
        self.assertEqual(result["attempt_order"], self.primary_ids)
        self.assertEqual(result["reserve_activations"], [])
        self.assertEqual(result["stop_reason"], "five_accepted_development_roots")

    def test_one_failure_activates_exactly_next_reserve_and_preserves_failure(self):
        outcomes = {
            slot: _receipt(slot, index != 0)
            for index, slot in enumerate(self.primary_ids)
        }
        outcomes[self.reserve_ids[0]] = _receipt(self.reserve_ids[0], True)
        result = self.run_scope(outcomes)
        self.assertTrue(result["pass"])
        self.assertEqual(result["attempt_order"], self.primary_ids + [self.reserve_ids[0]])
        self.assertIn(self.primary_ids[0], result["root_receipts"])
        self.assertFalse(
            result["root_receipts"][self.primary_ids[0]]["accepted_development_root"]
        )
        self.assertEqual(len(result["reserve_activations"]), 1)
        activation = result["reserve_activations"][0]
        self.assertEqual(activation["failed_slot_id"], self.primary_ids[0])
        self.assertEqual(activation["reserve_slot_id"], self.reserve_ids[0])

    def test_all_failures_exhaust_ordered_reserves_once(self):
        all_ids = self.primary_ids + self.reserve_ids
        outcomes = {slot: _receipt(slot, False) for slot in all_ids}
        result = self.run_scope(outcomes)
        self.assertTrue(result["scope_terminal"])
        self.assertTrue(result["pass"])
        self.assertFalse(result["five_accepted_roots"])
        self.assertEqual(result["attempt_order"], all_ids)
        self.assertEqual(len(set(result["attempt_order"])), 10)
        self.assertEqual(len(result["reserve_activations"]), 5)
        self.assertEqual(result["finalizer"]["status"], "COMPLETED_RESERVE_EXHAUSTED")

    def test_cleanup_uncertainty_stops_without_activation(self):
        outcomes = {self.primary_ids[0]: _receipt(self.primary_ids[0], False, cleanup=False)}
        result = self.run_scope(outcomes)
        self.assertFalse(result["pass"])
        self.assertFalse(result["scope_terminal"])
        self.assertEqual(result["attempt_order"], [self.primary_ids[0]])
        self.assertEqual(result["reserve_activations"], [])
        self.assertEqual(
            result["stop_reason"], "nonterminal_or_cleanup_uncertain_root_failure"
        )

    def test_exception_with_terminal_root_cleanup_is_preserved_then_activates(self):
        failed = self.primary_ids[0]
        outcomes = {
            slot: _receipt(slot, True) for slot in self.primary_ids[1:]
        }
        outcomes[self.reserve_ids[0]] = _receipt(self.reserve_ids[0], True)

        def adapter_factory(slot, attempt_dir):
            return slot

        class ThrowingRunner:
            def __init__(self, slot):
                self.slot = slot

            def run(self, *, output_dir, planned_root_slot_spec):
                root_dir = Path(output_dir) / "root"
                root_dir.mkdir(parents=True, exist_ok=True)
                root = {
                    "status": "failed_planner_with_evidence",
                    "cleanup_records": [
                        {"cleanup_safety_pass": True, "orphan_process_count": 0}
                    ],
                    "budget_counts": {
                        "planner_query_count": 2,
                        "execution_attempt_count": 0,
                        "recovery_attempt_count": 0,
                    },
                    "elapsed_seconds": 0.5,
                }
                (root_dir / "root_receipt.json").write_text(
                    json.dumps(root), encoding="utf-8"
                )
                raise RuntimeError("synthetic terminal planner failure")

        def root_runner_factory(slot):
            if slot["slot_id"] == failed:
                return ThrowingRunner(slot)
            return _Runner(slot, outcomes)

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        result = F1BatchPilotScopeRunnerV1(
            adapter_factory=adapter_factory,
            root_runner_factory=root_runner_factory,
        ).run(output_dir=Path(temporary.name) / "batch", plan=self.plan)
        self.assertTrue(result["pass"])
        failure = result["root_receipts"][failed]
        self.assertTrue(failure["terminal_attempt_evidence"])
        self.assertEqual(
            failure["error"]["message"], "synthetic terminal planner failure"
        )
        self.assertIsNotNone(failure["root_receipt_reference"])
        self.assertEqual(result["reserve_activations"][0]["failed_slot_id"], failed)

    def test_aggregate_budget_rejects_excess_and_consumption_is_unique(self):
        receipts = {
            slot: _receipt(slot, True, planner=40, execution=3)
            for slot in self.primary_ids
        }
        self.assertTrue(
            validate_f1_batch_scope_budget_v1(
                root_receipts=receipts, activation_count=0
            )["pass"]
        )
        receipts[self.reserve_ids[0]] = _receipt(
            self.reserve_ids[0], False, planner=200, execution=3
        )
        self.assertFalse(
            validate_f1_batch_scope_budget_v1(
                root_receipts=receipts, activation_count=1
            )["pass"]
        )
        authorization = {"receipt_sha256": "a" * 64}
        consumption = {
            "schema_version": CONSUMPTION_SCHEMA,
            "implementation_version": self.plan["implementation_version"],
            "authorization_id": AUTH_ID,
            "authorization_receipt_sha256": "a" * 64,
            "approved_scope": SCOPE,
            "family": "F1",
            "scene_seed": 2026083101,
            "consumed_at": "2026-08-31T00:00:00+00:00",
            "max_invocations": 1,
        }
        consumption["consumption_receipt_sha256"] = consumption_sha(consumption)
        self.assertEqual(validate_consumption(consumption, authorization), consumption)


if __name__ == "__main__":
    unittest.main()
