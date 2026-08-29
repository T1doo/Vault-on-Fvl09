import copy
from datetime import datetime, timedelta, timezone
import json
import tempfile
import unittest
from pathlib import Path

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes.runtime_v3_1_authorization_v1_1 import (
    ALLOWED_UUID_POLICY,
    AUTHORIZATION_SCHEMA_VERSION,
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    AuthorizationScopeError,
    authorization_receipt_sha256,
    consume_authorization_once,
    current_source_bindings,
    load_authorization_v1_1,
    load_consumption_receipt,
    validate_authorization_v1_1,
)
from controlled_multi_future.runtime_v3_1_budget_v1_1 import scope_budget


NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
AUTH_PATH = "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/authorizations/runtime_v3_1_v5/a0.json"
OUTPUT = "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/nonformal_a0_runtime_v3_1_v5_f1_seed20260829_run1"
COMMAND = [
    "/nfs_share/lijunhui/Robotwin2/env/bin/python",
    "-m",
    "controlled_multi_future.probes.a0_real_sapien_adapter_smoke",
    "--authorization-receipt",
    AUTH_PATH,
]


def valid_authorization():
    planned = {
        "slot_id": "runtime_v3_1_A0_v5_F1_seed20260829",
        "family": "F1",
        "seed": 20260829,
        "origin": "nonformal_A0_user_approved_once",
    }
    budget = scope_budget("A0_current_anchor_smoke")
    payload = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "authorization_id": "a0-f1-seed20260829-v5-auth1",
        "authorized_run_id": "a0-f1-seed20260829-v5-run1",
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
    payload["receipt_sha256"] = authorization_receipt_sha256(payload)
    return payload


def reseal(value):
    value = copy.deepcopy(value)
    value["receipt_sha256"] = authorization_receipt_sha256(value)
    return value


class RuntimeAuthorizationV1_1Test(unittest.TestCase):
    def test_valid_receipt_and_missing_file(self):
        receipt = validate_authorization_v1_1(
            valid_authorization(),
            requested_scope="A0_current_anchor_smoke",
            now=NOW,
            expected_family="F1",
            expected_seed=20260829,
            expected_output_namespace=OUTPUT,
            expected_content_commit="0" * 40,
        )
        self.assertTrue(receipt["approved"])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AuthorizationBindingError):
                load_authorization_v1_1(
                    Path(directory) / "missing.json",
                    requested_scope="A0_current_anchor_smoke",
                )

    def test_approval_scope_family_seed_and_spec_are_bound(self):
        cases = {
            "approved": ("approved", False, AuthorizationBindingError),
            "scope": ("approved_scopes", ["F1_three_branch_nonformal_probe"], AuthorizationScopeError),
            "family": ("family", "F2", AuthorizationBindingError),
            "seed": ("scene_seed", 1, AuthorizationBindingError),
            "planned_hash": ("planned_root_slot_spec_sha256", "0" * 64, AuthorizationBindingError),
        }
        for name, (field, replacement, error) in cases.items():
            with self.subTest(name=name):
                value = valid_authorization()
                value[field] = replacement
                value = reseal(value)
                with self.assertRaises(error):
                    validate_authorization_v1_1(
                        value,
                        requested_scope="A0_current_anchor_smoke",
                        now=NOW,
                    )

    def test_all_source_budget_timeout_and_output_bindings_fail_independently(self):
        fields = [
            "implementation_source_sha256",
            "a0_orchestrator_sha256",
            "a0_activity_monitor_sha256",
            "real_adapter_sha256",
            "gpu_guard_sha256",
            "budget_receipt_sha256",
        ]
        for field in fields:
            with self.subTest(field=field):
                value = valid_authorization()
                value[field] = "0" * 64
                value = reseal(value)
                with self.assertRaises(AuthorizationBindingError):
                    validate_authorization_v1_1(value, requested_scope="A0_current_anchor_smoke", now=NOW)
        for field, replacement in (
            ("timeout_seconds", 601),
            ("output_namespace", "/nfs_share/lijunhui/other"),
            ("scope_budget_sha256", "0" * 64),
            ("authorized_command_sha256", "x" * 64),
        ):
            with self.subTest(field=field):
                value = valid_authorization()
                value[field] = replacement
                value = reseal(value)
                with self.assertRaises(AuthorizationBindingError):
                    validate_authorization_v1_1(
                        value,
                        requested_scope="A0_current_anchor_smoke",
                        now=NOW,
                        expected_output_namespace=OUTPUT,
                    )

    def test_expired_old_schema_hash_and_gpu_policy_fail(self):
        value = valid_authorization()
        value["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
        value = reseal(value)
        with self.assertRaises(AuthorizationExpiredError):
            validate_authorization_v1_1(value, requested_scope="A0_current_anchor_smoke", now=NOW)
        for field, replacement in (
            ("schema_version", "cmf_runtime_v3_1_gpu_authorization_v1"),
            ("receipt_sha256", "0" * 64),
            ("allowed_physical_gpu_indices", [9]),
            ("allowed_gpu_uuid_policy", "any"),
        ):
            value = valid_authorization()
            value[field] = replacement
            if field != "receipt_sha256":
                value = reseal(value)
            with self.assertRaises(AuthorizationBindingError):
                validate_authorization_v1_1(value, requested_scope="A0_current_anchor_smoke", now=NOW)

    def test_one_shot_consumption_first_succeeds_second_fails(self):
        authorization = validate_authorization_v1_1(
            valid_authorization(),
            requested_scope="A0_current_anchor_smoke",
            now=NOW,
        )
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger"
            first = consume_authorization_once(authorization, ledger_directory=ledger, now=NOW)
            loaded = load_consumption_receipt(Path(first["path"]), authorization)
            self.assertEqual(loaded["authorization_id"], authorization["authorization_id"])
            with self.assertRaises(AuthorizationReplayError):
                consume_authorization_once(authorization, ledger_directory=ledger, now=NOW)

    def test_consumption_ledger_creation_failure_is_terminal(self):
        authorization = validate_authorization_v1_1(
            valid_authorization(),
            requested_scope="A0_current_anchor_smoke",
            now=NOW,
        )
        with tempfile.TemporaryDirectory() as directory:
            blocker = Path(directory) / "not-a-directory"
            blocker.write_text("block")
            with self.assertRaises(AuthorizationBindingError):
                consume_authorization_once(
                    authorization,
                    ledger_directory=blocker / "child",
                    now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
