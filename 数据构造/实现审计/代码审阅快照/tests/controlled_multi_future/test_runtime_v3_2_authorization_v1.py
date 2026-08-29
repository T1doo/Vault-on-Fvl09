import copy
from datetime import datetime, timedelta, timezone
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from controlled_multi_future.pre_stage0_authorization_v2 import (
    PARENT_SCHEMA_VERSION,
    build_scope_request,
    issue_authorization_from_scope_request,
)
from controlled_multi_future.probes.runtime_v3_2_authorization_v1 import (
    AuthorizationBindingError,
    AuthorizationExpiredError,
    AuthorizationReplayError,
    authorization_receipt_sha256,
    canonical_sha256,
    consume_authorization_once,
    current_source_bindings_v3_2,
    sha256_file,
    validate_authorization_v3_2,
)
from controlled_multi_future.runtime_source_lock_v1 import SourceLockError


NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


class RuntimeAuthorizationV3_2V1Test(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir="/nfs_share/lijunhui/tmp")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.parent_md = self.root / "parent.md"
        self.parent_md.write_text("approved pre-stage0 work\n", encoding="utf-8")
        parent = {
            "schema_version": PARENT_SCHEMA_VERSION,
            "approved": True,
            "approved_scopes": ["F1_three_branch_nonformal_probe_v3_2"],
            "formal_stage0_authorized": False,
            "stage1_authorized": False,
            "formal_collection_authorized": False,
            "training_authorized": False,
            "authorization_markdown_path": str(self.parent_md),
            "authorization_markdown_sha256": sha256_file(self.parent_md),
        }
        parent["parent_user_authorization_sha256"] = canonical_sha256(parent)
        self.parent = parent
        self.parent_path = self.root / "parent.json"
        self.parent_path.write_text(json.dumps(parent, sort_keys=True), encoding="utf-8")
        self.output = self.root / "output"
        self.auth_path = self.root / "authorization.json"
        self.source_lock_path = self.root / "source-lock.json"
        self.request_path = self.root / "request.json"
        self.command = ["python", "-m", "controlled_multi_future.probes.runtime_v3_2_complete_family_scope", "--authorization-receipt", str(self.auth_path)]
        self.request = build_scope_request(
            parent_user_authorization=parent,
            scope="F1_three_branch_nonformal_probe_v3_2",
            family="F1",
            scene_seed=20260829,
            planned_root_slot_spec={"slot_id": "a0", "family": "F1", "seed": 20260829},
            reviewed_content_commit="0" * 40,
            authorization_receipt_path=str(self.auth_path),
            source_lock_receipt_path=str(self.source_lock_path),
            consumption_ledger_directory=str(self.root / "ledger"),
            guard_receipt_path=str(self.root / "guard.json"),
            output_namespace=str(self.output),
            exact_child_command=self.command,
        )
        self.request_path.write_text(json.dumps(self.request, sort_keys=True), encoding="utf-8")
        self.source_lock = {
            "source_lock_receipt_sha256": "a" * 64,
            "snapshot": {
                "family": "F1",
                "implementation_source_sha256": current_source_bindings_v3_2()["implementation_source_sha256"],
            },
        }

    def authorization(self):
        with mock.patch(
            "controlled_multi_future.pre_stage0_authorization_v2.validate_runtime_source_lock",
            return_value=self.source_lock,
        ):
            return issue_authorization_from_scope_request(
                scope_request_path=self.request_path,
                parent_user_authorization_path=self.parent_path,
                source_lock_receipt=self.source_lock,
                authorization_id="f1-v3-2-auth1",
                authorized_run_id="f1-v3-2-run1",
                issued_at=NOW - timedelta(minutes=1),
                validity_seconds=3600,
            )

    def validate(self, value):
        with mock.patch(
            "controlled_multi_future.probes.runtime_v3_2_authorization_v1.load_runtime_source_lock",
            return_value=self.source_lock,
        ):
            return validate_authorization_v3_2(
                value,
                requested_scope="F1_three_branch_nonformal_probe_v3_2",
                now=NOW,
                expected_family="F1",
                expected_seed=20260829,
                expected_output_namespace=str(self.output),
                expected_reviewed_content_commit="0" * 40,
            )

    def reseal(self, value):
        result = copy.deepcopy(value)
        result["receipt_sha256"] = authorization_receipt_sha256(result)
        return result

    def test_valid_request_bound_authorization_and_one_shot(self):
        authorization = self.validate(self.authorization())
        first = consume_authorization_once(authorization, ledger_directory=self.root / "ledger", now=NOW)
        self.assertEqual(first["source_lock_receipt_sha256"], "a" * 64)
        with self.assertRaises(AuthorizationReplayError):
            consume_authorization_once(authorization, ledger_directory=self.root / "ledger", now=NOW)

    def test_approval_request_sha_mismatch_fails(self):
        authorization = self.authorization()
        request = json.loads(self.request_path.read_text())
        request["status"] = "tampered"
        self.request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
        with self.assertRaises(AuthorizationBindingError):
            self.validate(authorization)

    def test_parent_user_authorization_sha_mismatch_fails(self):
        authorization = self.authorization()
        authorization["parent_user_authorization_sha256"] = "0" * 64
        with self.assertRaises(AuthorizationBindingError):
            self.validate(self.reseal(authorization))

    def test_authorization_validity_over_one_hour_fails(self):
        authorization = self.authorization()
        authorization["expires_at"] = (NOW + timedelta(hours=2)).isoformat()
        with self.assertRaises(AuthorizationExpiredError):
            self.validate(self.reseal(authorization))

    def test_physics_limit_mismatch_fails(self):
        authorization = self.authorization()
        authorization["physics_step_limit"] = 1
        with self.assertRaises(AuthorizationBindingError):
            self.validate(self.reseal(authorization))

    def test_source_lock_failure_prevents_validation_and_consumption(self):
        authorization = self.authorization()
        ledger = self.root / "not-consumed"
        with mock.patch(
            "controlled_multi_future.probes.runtime_v3_2_authorization_v1.load_runtime_source_lock",
            side_effect=SourceLockError("changed"),
        ):
            with self.assertRaises(SourceLockError):
                validate_authorization_v3_2(
                    authorization,
                    requested_scope="F1_three_branch_nonformal_probe_v3_2",
                    now=NOW,
                )
        self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
