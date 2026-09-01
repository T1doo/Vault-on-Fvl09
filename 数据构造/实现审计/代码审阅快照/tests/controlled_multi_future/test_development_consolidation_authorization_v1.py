from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controlled_multi_future.canonical_artifact import (
    canonical_hash_json,
    canonical_write_json,
)
from controlled_multi_future.f3_grasp_qualification_v1 import (
    build_f3_grasp_candidate_spec_v1,
)
from controlled_multi_future.gpu_parallel_policy_v2 import current_gpu_policy_artifact
from controlled_multi_future.probes.development_consolidation_authorization_v1 import (
    AUTH_SCHEMA,
    IMPLEMENTATION_VERSION,
    job_budget_v1,
    receipt_sha,
    validate,
    validate_consumption,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)


class DevelopmentConsolidationAuthorizationV1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        )
        self.root = Path(self.temp.name)
        (self.root / "development_pipeline_consolidation_v1").mkdir()
        self.spec = build_f3_grasp_candidate_spec_v1(
            "f3-grasp-qv1-r01", purpose="physical"
        )
        self.budget = job_budget_v1("F3_PHYSICAL_CANDIDATE")
        self.authorization_id = "test-development-consolidation-f3-r01"
        self.output = self.root / "output"
        self.guard = (
            self.root
            / "development_pipeline_consolidation_v1"
            / "test.guard.json"
        )
        self.source = self.root / "source.json"
        canonical_write_json(self.source, {"source": True})
        self.source_job = self.root / "planner_screen_receipt.json"
        source_job = {
            "status": "completed_pass",
            "selected_candidate_id": "f3-grasp-qv1-r01",
        }
        source_job["receipt_sha256"] = canonical_hash_json(source_job)
        canonical_write_json(self.source_job, source_job)
        self.parent = self.root / "parent.json"
        parent = {
            "schema_version": "cmf_development_consolidation_parent_v1",
            "authorized_scopes": [self.spec["scope"]],
            "stage1_authorized": False,
        }
        parent["parent_user_authorization_sha256"] = canonical_hash_json(parent)
        canonical_write_json(self.parent, parent)
        self.request = self.root / "request.json"
        request = {
            "schema_version": "cmf_development_consolidation_request_v1",
            "authorization_id": self.authorization_id,
            "authorized_command_sha256": "a" * 64,
            "output_namespace": str(self.output.resolve()),
            "planned_root_slot_spec_sha256": self.spec[
                "planned_scope_spec_sha256"
            ],
        }
        request["scope_request_sha256"] = canonical_hash_json(request)
        canonical_write_json(self.request, request)
        now = datetime.now(timezone.utc)
        policy = current_gpu_policy_artifact()
        self.value = {
            "schema_version": AUTH_SCHEMA,
            "implementation_version": IMPLEMENTATION_VERSION,
            "approved": True,
            "approved_scopes": [self.spec["scope"]],
            "authorization_id": self.authorization_id,
            "authorized_run_id": self.authorization_id + "-run",
            "job_kind": "F3_PHYSICAL_CANDIDATE",
            "family": "F3",
            "scene_seed": self.spec["seed"],
            "planned_root_slot_spec": self.spec,
            "planned_root_slot_spec_sha256": self.spec[
                "planned_scope_spec_sha256"
            ],
            "job_inputs": {
                "source_receipt_path": str(self.source_job.resolve()),
                "source_receipt_file_sha256": hashlib.sha256(
                    self.source_job.read_bytes()
                ).hexdigest(),
                "source_receipt_sha256": source_job["receipt_sha256"],
                "selected_candidate_id": "f3-grasp-qv1-r01",
            },
            "budget": self.budget,
            "budget_receipt_sha256": self.budget["budget_receipt_sha256"],
            "planner_query_limit": self.budget["planner_query_limit"],
            "controlled_action_limit": self.budget["controlled_action_limit"],
            "physics_step_limit": -1,
            "timeout_seconds": self.budget["timeout_seconds"],
            "max_invocations": 1,
            "automatic_retry": False,
            "recovery_attempts": 0,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "stage1_authorized": False,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=30)).isoformat(),
            "source_lock_receipt_path": str(self.source.resolve()),
            "source_lock_receipt_sha256": "b" * 64,
            "implementation_source_sha256": "c" * 64,
            "approval_request_path": str(self.request.resolve()),
            "approval_request_file_sha256": hashlib.sha256(
                self.request.read_bytes()
            ).hexdigest(),
            "approval_request_sha256": request["scope_request_sha256"],
            "parent_user_authorization_path": str(self.parent.resolve()),
            "parent_user_authorization_file_sha256": hashlib.sha256(
                self.parent.read_bytes()
            ).hexdigest(),
            "parent_user_authorization_sha256": parent[
                "parent_user_authorization_sha256"
            ],
            "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
            "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
            "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
            "output_namespace": str(self.output.resolve()),
            "guard_receipt_path": str(self.guard.resolve()),
            "authorized_command_sha256": "a" * 64,
            "reviewed_content_commit": "d" * 40,
            **{
                key: policy[key]
                for key in (
                    "gpu_policy_version",
                    "allowed_physical_gpu_indices",
                    "dynamic_fresh_idle_selection",
                    "parallel_different_cards_authorized",
                    "one_project_job_per_gpu",
                    "one_root_one_gpu",
                    "root_sharding_authorized",
                    "share_busy_gpu_authorized",
                    "atomic_guard_recheck_before_launch",
                    "automatic_gpu0_fallback",
                )
            },
        }
        self.value["receipt_sha256"] = receipt_sha(self.value)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_authorization_and_consumption_contract(self):
        source = {
            "source_lock_receipt_sha256": "b" * 64,
            "snapshot": {"implementation_source_sha256": "c" * 64},
        }
        with patch(
            "controlled_multi_future.probes.development_consolidation_authorization_v1.load_runtime_source_lock",
            return_value=source,
        ):
            validated = validate(
                self.value,
                requested_scope=self.spec["scope"],
                expected_output_namespace=str(self.output),
                expected_family="F3",
                expected_seed=self.spec["seed"],
            )
        self.assertEqual(validated, self.value)
        consumption = {
            "schema_version": "cmf_development_consolidation_consumption_v1",
            "implementation_version": IMPLEMENTATION_VERSION,
            "authorization_id": self.authorization_id,
            "authorization_receipt_sha256": self.value["receipt_sha256"],
            "approved_scope": self.spec["scope"],
            "job_kind": "F3_PHYSICAL_CANDIDATE",
            "family": "F3",
            "scene_seed": self.spec["seed"],
            "consumed_at": datetime.now(timezone.utc).isoformat(),
            "max_invocations": 1,
        }
        consumption["consumption_receipt_sha256"] = canonical_hash_json(consumption)
        self.assertEqual(validate_consumption(consumption, self.value), consumption)

    def test_job_kind_purpose_tamper_fails_closed(self):
        changed = dict(self.value)
        changed["job_kind"] = "F3_FULL_ROOT"
        changed["budget"] = job_budget_v1("F3_FULL_ROOT")
        changed["budget_receipt_sha256"] = changed["budget"][
            "budget_receipt_sha256"
        ]
        changed["planner_query_limit"] = changed["budget"]["planner_query_limit"]
        changed["controlled_action_limit"] = changed["budget"][
            "controlled_action_limit"
        ]
        changed["timeout_seconds"] = changed["budget"]["timeout_seconds"]
        changed["receipt_sha256"] = receipt_sha(changed)
        with self.assertRaises(Exception):
            validate(changed, requested_scope=self.spec["scope"])


if __name__ == "__main__":
    unittest.main()
