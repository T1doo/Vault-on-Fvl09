import copy
from datetime import datetime, timedelta, timezone
import unittest

from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes.gpu_guard_v2_3 import (
    GUARD_SCHEMA_VERSION,
    GuardAuthorizationMismatch,
    GuardBudgetMismatch,
    build_guard_binding,
    validate_guard_binding,
)


NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
COMMAND = ["python", "child.py"]


def authorization():
    return {
        "authorization_id": "auth",
        "receipt_sha256": "1" * 64,
        "authorized_run_id": "run",
        "approved_scopes": ["F1_three_branch_nonformal_probe_v3_2"],
        "family": "F1",
        "scene_seed": 20260829,
        "planned_root_slot_spec_sha256": "2" * 64,
        "parent_user_authorization_sha256": "3" * 64,
        "approval_request_sha256": "4" * 64,
        "source_lock_receipt_sha256": "5" * 64,
        "implementation_source_sha256": "6" * 64,
        "budget_receipt_sha256": "7" * 64,
        "planner_query_limit": 36,
        "controlled_action_limit": 3,
        "physics_step_limit": -1,
        "timeout_seconds": 3600,
        "output_namespace": "/nfs_share/lijunhui/output",
        "allowed_physical_gpu_indices": list(range(8)),
        "authorized_command_sha256": command_sha256(COMMAND),
    }


def consumption():
    value = {
        "schema_version": "cmf_runtime_v3_2_authorization_consumption_v1",
        "authorization_id": "auth",
        "authorization_receipt_sha256": "1" * 64,
        "authorized_run_id": "run",
        "output_namespace": "/nfs_share/lijunhui/output",
        "source_lock_receipt_sha256": "5" * 64,
        "consumed_at": NOW.isoformat(),
        "max_invocations": 1,
    }
    from controlled_multi_future.probes.runtime_v3_2_authorization_v1 import canonical_sha256

    value["consumption_receipt_sha256"] = canonical_sha256(value)
    return value


def precheck():
    return {
        "physical_index": 0,
        "uuid": "GPU-test",
        "memory_used_mib": 5,
        "utilization_percent": 0,
        "pstate": "P8",
        "compute_processes": [],
        "captured_at": NOW.isoformat(),
    }


class GpuGuardV2_3Test(unittest.TestCase):
    def setUp(self):
        self.auth = authorization()
        self.consumption = consumption()
        self.binding = build_guard_binding(
            self.auth,
            self.consumption,
            physical_index=0,
            expected_uuid="GPU-test",
            timeout_seconds=3600,
            output_namespace=self.auth["output_namespace"],
            command=COMMAND,
            guard_pid=123,
        )

    def guard(self):
        return {
            "schema_version": GUARD_SCHEMA_VERSION,
            "status": "precheck_passed",
            "binding": copy.deepcopy(self.binding),
            "precheck": precheck(),
        }

    def test_request_source_lock_and_physics_are_bound(self):
        result = validate_guard_binding(
            self.guard(),
            self.auth,
            self.consumption,
            physical_index=0,
            expected_uuid="GPU-test",
            child_parent_pid=123,
            now=NOW,
        )
        self.assertEqual(result["binding"]["source_lock_receipt_sha256"], "5" * 64)
        for field in (
            "parent_user_authorization_sha256",
            "approval_request_sha256",
            "source_lock_receipt_sha256",
            "physics_step_limit",
        ):
            with self.subTest(field=field):
                guard = self.guard()
                guard["binding"][field] = 1 if field == "physics_step_limit" else "0" * 64
                error = GuardBudgetMismatch if field == "physics_step_limit" else GuardAuthorizationMismatch
                with self.assertRaises(error):
                    validate_guard_binding(
                        guard,
                        self.auth,
                        self.consumption,
                        physical_index=0,
                        expected_uuid="GPU-test",
                        child_parent_pid=123,
                        now=NOW,
                    )

    def test_stale_precheck_fails(self):
        guard = self.guard()
        guard["precheck"]["captured_at"] = (NOW - timedelta(seconds=61)).isoformat()
        with self.assertRaises(GuardAuthorizationMismatch):
            validate_guard_binding(
                guard,
                self.auth,
                self.consumption,
                physical_index=0,
                expected_uuid="GPU-test",
                child_parent_pid=123,
                now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
