from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest

from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from controlled_multi_future.probes.runtime_v3_4_authorization_v1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    authorization_receipt_sha256,
    canonical_sha256,
    consumption_receipt_sha256,
    current_source_bindings_v3_4,
    sha256_file,
    validate_authorization_v3_4,
    validate_consumption_receipt,
)
from controlled_multi_future.runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from controlled_multi_future.runtime_v3_4_budget_v1 import (
    budget_receipt_sha256,
    scope_budget,
)
from controlled_multi_future.runtime_v3_4_scope_bundle_v1 import (
    PARENT_AUTHORIZATION,
    load_parent_user_authorization,
)
from controlled_multi_future.runtime_v3_4_scope_specs_v1 import planned_scope_spec


class RuntimeV34AuthorizationV1Test(unittest.TestCase):
    def build(self, directory):
        directory = Path(directory)
        scope = "F2_inside_targeted_v10"
        spec = planned_scope_spec(scope)
        parent = load_parent_user_authorization()
        request = {
            "schema_version": "cmf_runtime_v3_4_scope_request_v1",
            "scope": scope,
            "family": "F2",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
        }
        request["scope_request_sha256"] = canonical_sha256(request)
        request_path = directory / "request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        source_lock = capture_runtime_source_lock(family="F2")
        source_lock_path = directory / "source_lock.json"
        write_runtime_source_lock(source_lock_path, source_lock)
        output = directory / "output"
        guard = directory / "guard.json"
        command = ["python", "-m", "controlled_multi_future.probes.runtime_v3_4_scope_runner"]
        now = datetime.now(timezone.utc)
        budget = scope_budget(scope)
        receipt = {
            "schema_version": AUTHORIZATION_SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_runtime_v3_4",
            "implementation_revision": "diagnosis_first_multi_gpu_convergence_v1",
            "authorization_id": "test-runtime-v3-4-auth",
            "authorized_run_id": "test-runtime-v3-4-run",
            "issued_at": (now - timedelta(seconds=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "approved": True,
            "approved_scopes": [scope],
            "family": "F2",
            "scene_seed": spec["seed"],
            "planned_root_slot_spec": spec,
            "planned_root_slot_spec_sha256": canonical_sha256(spec),
            "parent_user_authorization_path": str(PARENT_AUTHORIZATION),
            "parent_user_authorization_file_sha256": sha256_file(PARENT_AUTHORIZATION),
            "parent_user_authorization_sha256": parent["parent_user_authorization_sha256"],
            "approval_request_path": str(request_path),
            "approval_request_file_sha256": sha256_file(request_path),
            "approval_request_sha256": request["scope_request_sha256"],
            "source_lock_receipt_path": str(source_lock_path),
            "source_lock_receipt_sha256": source_lock["source_lock_receipt_sha256"],
            "source_bindings": current_source_bindings_v3_4(),
            "implementation_source_sha256": current_source_bindings_v3_4()["implementation_source_sha256"],
            "budget_receipt_sha256": budget_receipt_sha256(),
            "scope_budget": budget,
            "planner_query_limit": budget["planner_query_limit"],
            "controlled_action_limit": budget["execution_limit"],
            "physics_step_limit": -1,
            "timeout_seconds": budget["timeout_seconds"],
            "allowed_physical_gpu_indices": list(range(8)),
            "output_namespace": str(output),
            "guard_receipt_path": str(guard),
            "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
            "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
            "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
            "authorized_command_sha256": command_sha256(command),
            "reviewed_content_commit": "84c86fedd27e343e1e2afb565142c5beeedf3c11",
            "max_invocations": 1,
            "automatic_retry": False,
            "recovery_attempts": 0,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
        }
        receipt["receipt_sha256"] = authorization_receipt_sha256(receipt)
        return receipt, now

    def test_valid_authorization_binds_source_budget_gpu0_7_and_parent(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            receipt, now = self.build(directory)
            value = validate_authorization_v3_4(
                receipt,
                requested_scope="F2_inside_targeted_v10",
                now=now,
                expected_family="F2",
                expected_seed=20260829,
                expected_output_namespace=receipt["output_namespace"],
                expected_reviewed_content_commit=receipt["reviewed_content_commit"],
            )
            self.assertEqual(value["allowed_physical_gpu_indices"], list(range(8)))
            self.assertFalse(value["stage0_authorized"])
            tampered = copy.deepcopy(receipt)
            tampered["allowed_physical_gpu_indices"] = [0]
            tampered["receipt_sha256"] = authorization_receipt_sha256(tampered)
            with self.assertRaises(Exception):
                validate_authorization_v3_4(
                    tampered,
                    requested_scope="F2_inside_targeted_v10",
                    now=now,
                )

    def test_consumption_is_bound_to_v3_4_authorization(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            receipt, _ = self.build(directory)
            consumption = {
                "schema_version": "cmf_runtime_v3_4_authorization_consumption_v1",
                "authorization_id": receipt["authorization_id"],
                "authorization_receipt_sha256": receipt["receipt_sha256"],
                "approved_scope": receipt["approved_scopes"][0],
                "family": receipt["family"],
                "scene_seed": receipt["scene_seed"],
                "consumed_at": datetime.now(timezone.utc).isoformat(),
                "max_invocations": 1,
            }
            consumption["consumption_receipt_sha256"] = consumption_receipt_sha256(
                consumption
            )
            self.assertEqual(
                validate_consumption_receipt(consumption, receipt), consumption
            )


if __name__ == "__main__":
    unittest.main()
