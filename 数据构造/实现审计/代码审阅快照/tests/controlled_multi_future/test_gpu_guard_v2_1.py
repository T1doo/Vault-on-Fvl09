import copy
from datetime import datetime, timedelta, timezone
import json
import tempfile
import unittest
from pathlib import Path

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.probes.gpu_guard_v2_1 import (
    GUARD_SCHEMA_VERSION,
    GuardAuthorizationMismatch,
    GuardBudgetMismatch,
    build_guard_binding,
    command_sha256,
    update_child_receipt_v2_1,
    validate_guard_binding,
)
from controlled_multi_future.probes.runtime_v3_1_authorization_v1_1 import (
    ALLOWED_UUID_POLICY,
    AUTHORIZATION_SCHEMA_VERSION,
    authorization_receipt_sha256,
    consume_authorization_once,
    current_source_bindings,
    validate_authorization_v1_1,
)
from controlled_multi_future.runtime_v3_1_budget_v1_1 import scope_budget


NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
AUTH_PATH = "/nfs_share/lijunhui/Vault-on-Fvl09/a0-authorization.json"
OUTPUT = "/nfs_share/lijunhui/Vault-on-Fvl09/a0-output"
COMMAND = ["python", "-m", "controlled_multi_future.probes.a0_real_sapien_adapter_smoke", "--authorization-receipt", AUTH_PATH]


def authorization():
    planned = {"slot_id": "a0", "family": "F1", "seed": 20260829}
    budget = scope_budget("A0_current_anchor_smoke")
    value = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "authorization_id": "auth-a0-v5",
        "authorized_run_id": "run-a0-v5",
        "issued_at": (NOW - timedelta(minutes=1)).isoformat(),
        "expires_at": (NOW + timedelta(hours=1)).isoformat(),
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_1",
        "implementation_revision": "runtime_v3_1_cpu_hardening_v5",
        "content_commit": "0" * 40,
        **current_source_bindings(),
        "approved": True,
        "approved_scopes": ["A0_current_anchor_smoke"],
        "family": "F1",
        "scene_seed": 20260829,
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": hash_json(planned),
        "scene_pattern": ["A0_pristine", "A0_fresh_1", "A0_fresh_2", "A0_fresh_3"],
        "planner_query_limit": 0,
        "controlled_action_limit": 0,
        "timeout_seconds": 600,
        "max_invocations": 1,
        "scope_budget": budget,
        "scope_budget_sha256": budget["scope_budget_sha256"],
        "allowed_physical_gpu_indices": list(range(8)),
        "allowed_gpu_uuid_policy": ALLOWED_UUID_POLICY,
        "output_namespace": OUTPUT,
        "authorized_command_sha256": command_sha256(COMMAND),
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
    }
    value["receipt_sha256"] = authorization_receipt_sha256(value)
    return validate_authorization_v1_1(value, requested_scope="A0_current_anchor_smoke", now=NOW)


def precheck(**changes):
    value = {
        "physical_index": 4,
        "uuid": "GPU-test",
        "memory_used_mib": 5,
        "utilization_percent": 0,
        "pstate": "P8",
        "compute_processes": [],
        "captured_at": NOW.isoformat(),
    }
    value.update(changes)
    return value


class GpuGuardV2_1Test(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.auth = authorization()
        self.consumption = consume_authorization_once(
            self.auth,
            ledger_directory=Path(self.directory.name) / "ledger",
            now=NOW,
        )
        self.binding = build_guard_binding(
            self.auth,
            self.consumption,
            physical_index=4,
            expected_uuid="GPU-test",
            timeout_seconds=600,
            output_namespace=OUTPUT,
            command=COMMAND,
            guard_pid=1234,
        )

    def guard(self):
        return {
            "schema_version": GUARD_SCHEMA_VERSION,
            "status": "precheck_passed",
            "binding": copy.deepcopy(self.binding),
            "precheck": precheck(),
        }

    def test_valid_binding(self):
        result = validate_guard_binding(
            self.guard(),
            self.auth,
            self.consumption,
            physical_index=4,
            expected_uuid="GPU-test",
            child_parent_pid=1234,
            now=NOW,
        )
        self.assertEqual(result["precheck_age_seconds"], 0)

    def test_timeout_output_authorization_and_hash_mismatches_fail(self):
        for field, value, error in (
            ("timeout_seconds", 601, GuardBudgetMismatch),
            ("output_namespace", "/nfs_share/lijunhui/other", GuardAuthorizationMismatch),
            ("authorization_id", "other", GuardAuthorizationMismatch),
            ("implementation_source_sha256", "0" * 64, GuardAuthorizationMismatch),
            ("budget_receipt_sha256", "0" * 64, GuardBudgetMismatch),
        ):
            with self.subTest(field=field):
                guard = self.guard()
                guard["binding"][field] = value
                with self.assertRaises(error):
                    validate_guard_binding(
                        guard,
                        self.auth,
                        self.consumption,
                        physical_index=4,
                        expected_uuid="GPU-test",
                        child_parent_pid=1234,
                        now=NOW,
                    )

    def test_stale_wrong_uuid_busy_and_wrong_parent_fail(self):
        cases = (
            {"captured_at": (NOW - timedelta(seconds=61)).isoformat()},
            {"uuid": "GPU-other"},
            {"memory_used_mib": 101},
            {"utilization_percent": 2},
            {"pstate": "P2"},
            {"compute_processes": [{"pid": 9}]},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                guard = self.guard()
                guard["precheck"] = precheck(**changes)
                with self.assertRaises(GuardAuthorizationMismatch):
                    validate_guard_binding(
                        guard,
                        self.auth,
                        self.consumption,
                        physical_index=4,
                        expected_uuid="GPU-test",
                        child_parent_pid=1234,
                        now=NOW,
                    )
        with self.assertRaises(GuardAuthorizationMismatch):
            validate_guard_binding(
                self.guard(),
                self.auth,
                self.consumption,
                physical_index=4,
                expected_uuid="GPU-test",
                child_parent_pid=999,
                now=NOW,
            )

    def test_build_rejects_timeout_output_index_and_command(self):
        for kwargs, error in (
            ({"timeout_seconds": 601}, GuardBudgetMismatch),
            ({"output_namespace": "/nfs_share/lijunhui/other"}, GuardAuthorizationMismatch),
            ({"physical_index": 9}, GuardAuthorizationMismatch),
            ({"command": ["wrong"]}, GuardAuthorizationMismatch),
        ):
            values = {
                "physical_index": 4,
                "expected_uuid": "GPU-test",
                "timeout_seconds": 600,
                "output_namespace": OUTPUT,
                "command": COMMAND,
                "guard_pid": 1234,
            }
            values.update(kwargs)
            with self.assertRaises(error):
                build_guard_binding(self.auth, self.consumption, **values)

    def test_missing_child_receipt_post_release_and_orphan_fail_closed(self):
        output = Path(self.directory.name) / "output"
        output.mkdir()
        self.assertFalse(
            update_child_receipt_v2_1(
                output,
                Path(self.directory.name) / "guard.json",
                self.binding,
                precheck(),
                [],
                {"verified": True},
            )
        )
        receipt = {
            "status": "passed_nonformal_A0",
            "scene_created": True,
            "scene_cleanup_succeeded": True,
            "orphan_process_count": 0,
        }
        (output / "receipt.json").write_text(json.dumps(receipt))
        update_child_receipt_v2_1(
            output,
            Path(self.directory.name) / "guard.json",
            self.binding,
            precheck(),
            [123],
            {"verified": False},
        )
        updated = json.loads((output / "receipt.json").read_text())
        self.assertEqual(updated["status"], "failed_cleanup_uncertain")
        self.assertEqual(updated["guard_process_group_orphan_count"], 1)


if __name__ == "__main__":
    unittest.main()
