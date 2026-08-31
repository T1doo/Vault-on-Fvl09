from datetime import datetime, timedelta, timezone
import unittest

from controlled_multi_future.gpu_parallel_policy_v2 import (
    GpuPolicyError,
    current_gpu_policy_artifact,
    schedule_dynamic_gpu_wave,
    validate_current_gpu_authorization,
)


NOW = datetime(2026, 8, 31, 5, 0, tzinfo=timezone.utc)


def snapshots(*idle_indices: int):
    values = []
    idle = set(idle_indices)
    for index in range(8):
        is_idle = index in idle
        values.append(
            {
                "physical_index": index,
                "uuid": f"GPU-policy-v2-{index}",
                "memory_used_mib": 14 if is_idle else 16000,
                "utilization_percent": 0 if is_idle else 85,
                "pstate": "P8" if is_idle else "P2",
                "compute_processes": [] if is_idle else [{"pid": 9000 + index}],
                "captured_at": NOW.isoformat(),
            }
        )
    return values


def jobs(count: int):
    return [
        {
            "job_id": f"job-{index}",
            "root_id": f"root-{index}",
            "family": f"F{index % 4 + 1}",
            "output_namespace": f"namespace-{index}",
            "authorization_receipt_sha256": f"{index + 1:064x}",
            "allowed_physical_gpu_indices": list(range(8)),
            "root_sharded": False,
            "queue_rank": index,
        }
        for index in range(count)
    ]


class GpuParallelPolicyV2Test(unittest.TestCase):
    def test_current_policy_is_exactly_gpu0_7_and_rejects_gpu0_only(self):
        policy = current_gpu_policy_artifact()
        self.assertEqual(policy["allowed_physical_gpu_indices"], list(range(8)))
        self.assertTrue(policy["parallel_different_cards_authorized"])
        self.assertFalse(policy["automatic_gpu0_fallback"])
        restricted = dict(policy)
        restricted["allowed_physical_gpu_indices"] = [0]
        with self.assertRaisesRegex(GpuPolicyError, "policy mismatch"):
            validate_current_gpu_authorization(restricted)

    def test_busy_gpu0_does_not_block_idle_nonzero_cards(self):
        result = schedule_dynamic_gpu_wave(
            jobs(3), snapshots(2, 5, 7), now=NOW
        )
        self.assertEqual(result["assigned_count"], 3)
        self.assertEqual(
            [item["physical_gpu_index"] for item in result["assignments"]],
            [2, 5, 7],
        )
        self.assertNotIn(0, result["fresh_idle_gpu_indices"])
        self.assertEqual(result["status"], "scheduled_all")

    def test_one_idle_card_schedules_one_instead_of_waiting_for_four(self):
        result = schedule_dynamic_gpu_wave(jobs(4), snapshots(6), now=NOW)
        self.assertEqual(result["assigned_count"], 1)
        self.assertEqual(result["assignments"][0]["physical_gpu_index"], 6)
        self.assertEqual(result["deferred_count"], 3)
        self.assertEqual(result["status"], "scheduled_partial_wave")

    def test_four_idle_cards_schedule_four_parallel_unique_jobs(self):
        result = schedule_dynamic_gpu_wave(
            jobs(6), snapshots(1, 3, 4, 7), now=NOW
        )
        self.assertEqual(result["assigned_count"], 4)
        self.assertEqual(result["maximum_parallelism_this_wave"], 4)
        self.assertEqual(
            {item["physical_gpu_index"] for item in result["assignments"]},
            {1, 3, 4, 7},
        )
        self.assertEqual(len({item["root_id"] for item in result["assignments"]}), 4)

    def test_no_idle_card_waits_without_consuming_authorization(self):
        result = schedule_dynamic_gpu_wave(jobs(2), snapshots(), now=NOW)
        self.assertEqual(result["assigned_count"], 0)
        self.assertEqual(result["deferred_count"], 2)
        self.assertEqual(result["status"], "waiting_no_fresh_idle_gpu")

    def test_stale_snapshot_is_not_launchable(self):
        values = snapshots(4)
        values[4]["captured_at"] = (NOW - timedelta(seconds=16)).isoformat()
        result = schedule_dynamic_gpu_wave(jobs(1), values, now=NOW)
        self.assertEqual(result["assignments"], [])

    def test_duplicate_root_or_output_is_rejected(self):
        values = jobs(2)
        values[1]["root_id"] = values[0]["root_id"]
        with self.assertRaisesRegex(GpuPolicyError, "must be unique"):
            schedule_dynamic_gpu_wave(values, snapshots(1, 2), now=NOW)

    def test_scheduler_never_consumes_authorization_or_claims_reservation(self):
        result = schedule_dynamic_gpu_wave(jobs(1), snapshots(7), now=NOW)
        assignment = result["assignments"][0]
        self.assertFalse(assignment["authorization_consumed_by_scheduler"])
        self.assertFalse(assignment["scheduler_decision_is_reservation"])
        self.assertTrue(assignment["atomic_guard_recheck_required"])


if __name__ == "__main__":
    unittest.main()
