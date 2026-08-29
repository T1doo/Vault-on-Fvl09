import copy
from datetime import datetime, timedelta, timezone
import inspect
import unittest

from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes.gpu_guard_v2_4 import (
    GUARD_SCHEMA_VERSION,
    GuardAuthorizationMismatch,
    GuardBudgetMismatch,
    build_guard_binding,
    main,
    validate_guard_binding,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    canonical_sha256,
)


NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
COMMAND = ["python", "child.py"]


def authorization():
    return {
        "authorization_id": "auth",
        "receipt_sha256": "1" * 64,
        "authorized_run_id": "run",
        "approved_scopes": ["F4_cube_grasp_no_action_ik"],
        "family": "F4",
        "scene_seed": 20260829,
        "planned_root_slot_spec_sha256": "2" * 64,
        "parent_user_authorization_sha256": "3" * 64,
        "approval_request_sha256": "4" * 64,
        "source_lock_receipt_sha256": "5" * 64,
        "implementation_source_sha256": "6" * 64,
        "budget_receipt_sha256": "7" * 64,
        "planner_query_limit": 24,
        "controlled_action_limit": 0,
        "physics_step_limit": -1,
        "timeout_seconds": 1800,
        "output_namespace": "/nfs_share/lijunhui/output",
        "guard_receipt_path": "/nfs_share/lijunhui/guard.json",
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "family_revision_index": None,
        "allowed_physical_gpu_indices": [0],
        "authorized_command_sha256": command_sha256(COMMAND),
    }


def consumption():
    value = {
        "schema_version": "cmf_runtime_v3_3_authorization_consumption_v1",
        "authorization_id": "auth",
        "authorization_receipt_sha256": "1" * 64,
        "authorized_run_id": "run",
        "output_namespace": "/nfs_share/lijunhui/output",
        "source_lock_receipt_sha256": "5" * 64,
        "consumed_at": NOW.isoformat(),
        "max_invocations": 1,
        "approved_scope": "F4_cube_grasp_no_action_ik",
        "family_revision_index": None,
        "revision_consumption_receipt_sha256": None,
    }
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


class GpuGuardV2_4Test(unittest.TestCase):
    def setUp(self):
        self.auth = authorization()
        self.consumption = consumption()
        self.binding = build_guard_binding(
            self.auth,
            self.consumption,
            physical_index=0,
            expected_uuid="GPU-test",
            timeout_seconds=1800,
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

    def test_binding_and_fresh_precheck_are_exact(self):
        value = validate_guard_binding(
            self.guard(),
            self.auth,
            self.consumption,
            physical_index=0,
            expected_uuid="GPU-test",
            child_parent_pid=123,
            now=NOW,
        )
        self.assertEqual(value["binding"]["physical_gpu_index"], 0)
        for field in (
            "source_lock_receipt_sha256",
            "consumption_ledger_directory",
            "command_sha256",
            "guard_receipt_path",
        ):
            guard = self.guard()
            guard["binding"][field] = "tampered"
            with self.subTest(field=field), self.assertRaises(
                GuardAuthorizationMismatch
            ):
                validate_guard_binding(
                    guard,
                    self.auth,
                    self.consumption,
                    physical_index=0,
                    expected_uuid="GPU-test",
                    child_parent_pid=123,
                    now=NOW,
                )
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

    def test_gpu1_and_budget_mismatch_are_rejected(self):
        with self.assertRaises(GuardAuthorizationMismatch):
            build_guard_binding(
                self.auth,
                self.consumption,
                physical_index=1,
                expected_uuid="GPU-other",
                timeout_seconds=1800,
                output_namespace=self.auth["output_namespace"],
                command=COMMAND,
                guard_pid=123,
            )
        with self.assertRaises(GuardBudgetMismatch):
            build_guard_binding(
                self.auth,
                self.consumption,
                physical_index=0,
                expected_uuid="GPU-test",
                timeout_seconds=1799,
                output_namespace=self.auth["output_namespace"],
                command=COMMAND,
                guard_pid=123,
            )

    def test_main_rechecks_gpu_after_source_lock_and_before_consumption(self):
        source = inspect.getsource(main)
        source_lock_index = source.index("load_runtime_source_lock")
        launch_snapshot_index = source.index(
            "launch_pre = snapshot", source_lock_index
        )
        consume_index = source.index("consume_authorization_once")
        self.assertLess(source_lock_index, launch_snapshot_index)
        self.assertLess(launch_snapshot_index, consume_index)
        self.assertGreaterEqual(source.count("load_authorization_v3_3"), 2)
        self.assertIn("stdout/stderr paths must be new and immutable", source)
        self.assertIn("failed_guard_internal_prelaunch", source)


if __name__ == "__main__":
    unittest.main()
