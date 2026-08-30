from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controlled_multi_future.f4_exact_corridor_application_v11 import (
    build_f4_exact_A_corridors_v11,
)
from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from controlled_multi_future.probes.stage0_smoke_authorization_v1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    authorization_receipt_sha256,
    canonical_sha256,
    current_stage0_source_bindings,
    sha256_file,
    validate_stage0_smoke_authorization,
)
from controlled_multi_future.runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from controlled_multi_future.stage0_smoke_budget_v1 import (
    budget_receipt_sha256,
    scope_budget,
)
from controlled_multi_future.stage0_smoke_manifest_v1 import (
    build_stage0_smoke_manifest,
)
from controlled_multi_future.stage0_smoke_scope_bundle_v1 import (
    PARENT_AUTHORIZATION,
    load_parent_user_authorization,
)
from controlled_multi_future.stage0_smoke_scope_specs_v1 import (
    planned_scope_spec,
)


def base_a_targets():
    q = [1, 0, 0, 0]
    return [
        {"segment_id": f"A_{name}", "pose": pose}
        for name, pose in (
            ("pregrasp", [0.16, 0.00, 0.98, *q]),
            ("grasp", [0.16, 0.01, 0.90, *q]),
            ("lift", [0.16, 0.01, 0.92, *q]),
            ("carry_mid", [0.155, 0.08, 1.00, *q]),
            ("preplace", [0.15, 0.15, 1.00, *q]),
            ("release", [0.15, 0.15, 0.90, *q]),
            ("neutral", [0.20, -0.12, 1.01, *q]),
        )
    ]


def bind_candidate(candidate):
    value = copy.deepcopy(candidate)
    value["stage0_context_binding_v12"] = {
        "arm": "right",
        "scene_layout_sha256": hash_json(F4_LAYOUT),
        "layout_version": F4_LAYOUT["layout_version"],
        "release_target_semantics": "same_role_visible_slot_unchanged",
    }
    value["base_v11_candidate_application_sha256"] = value[
        "candidate_application_sha256"
    ]
    value["stage0_bound_candidate_sha256_v12"] = hash_json(value)
    return value


class Stage0SmokeAuthorizationV1Test(unittest.TestCase):
    def manifest(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        candidate = bind_candidate(candidate)
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            directory = Path(directory)
            receipt_path = directory / "receipt.json"
            guard_path = directory / "guard.json"
            consumption_path = directory / "consumption.json"
            binding = {
                "authorization_receipt_sha256": "r" * 64,
                "physical_gpu_index": 0,
            }
            consumption = {
                "authorization_receipt_sha256": "r" * 64,
                "approved_scope": "F4_candidate_hash_infra_v12",
            }
            consumption["consumption_receipt_sha256"] = hash_json(consumption)
            consumption_path.write_text(json.dumps(consumption))
            value = {
                "schema_version": "cmf_stage0_smoke_guarded_scope_receipt_v1",
                "implementation_version": "controlled_multi_future_stage0_smoke_v1",
                "scope": "F4_candidate_hash_infra_v12",
                "family": "F4",
                "hash_infrastructure_pass": True,
                "pipeline_integrity_pass": True,
                "status": "completed_f4_hash_infrastructure",
                "hash_infrastructure_audit_v12": {"pass": True},
                "budget_counts": {"planner_query_count": 1},
                "scene_cleanup_succeeded": True,
                "orphan_process_count": 0,
                "selected_corridor_candidate_v11": candidate,
                "authorization": {
                    "receipt_sha256": "r" * 64,
                    "implementation_source_sha256": "s" * 64,
                },
                "authorization_consumption_receipt_sha256": consumption[
                    "consumption_receipt_sha256"
                ],
                "guard_binding": binding,
                "formal_data": False,
                "stage0_data": False,
                "stage0_authorized": True,
            }
            value["child_payload_sha256"] = hash_json(value)
            value.update(
                {
                    "gpu_guard_binding": binding,
                    "gpu_postcheck_release": {"verified": True},
                    "guard_receipt": str(guard_path),
                }
            )
            value["guard_sealed_receipt_sha256"] = hash_json(value)
            receipt_path.write_text(json.dumps(value))
            guard = {
                "status": "completed",
                "binding": binding,
                "post_source_lock_pass": True,
                "timed_out": False,
                "orphan_process_count": 0,
                "consumption_receipt": str(consumption_path),
                "child_receipt_file": {
                    "sha256": __import__("hashlib").sha256(
                        receipt_path.read_bytes()
                    ).hexdigest()
                },
            }
            guard["guard_receipt_sha256"] = hash_json(guard)
            guard_path.write_text(json.dumps(guard))
            return build_stage0_smoke_manifest(
                receipt_path, require_canonical_path=False
            )

    def attach_bundle_set(self, directory, receipt, manifest, manifest_path):
        directory = Path(directory)
        scopes = [
            "Stage0_F1_root_A",
            "Stage0_F2_root_A",
            "Stage0_F3_root_A",
            "Stage0_F4_root_A",
        ]
        ids = {scope: f"fixed-{scope}" for scope in scopes}
        ids["Stage0_F1_root_A"] = receipt["authorization_id"]
        paths = {scope: str(directory / f"{scope}.authorization.json") for scope in scopes}
        set_path = directory / "bundle_set.json"
        bundle_set = {
            "schema_version": "cmf_stage0_smoke_bundle_set_receipt_v1",
            "path": str(set_path),
            "reviewed_content_commit": receipt["reviewed_content_commit"],
            "implementation_source_sha256": receipt["implementation_source_sha256"],
            "stage0_manifest_sha256": manifest["manifest_sha256"],
            "stage0_manifest_path": str(manifest_path),
            "stage0_manifest_file_sha256": sha256_file(manifest_path),
            "budget_receipt_sha256": receipt["budget_receipt_sha256"],
            "parent_user_authorization_sha256": receipt["parent_user_authorization_sha256"],
            "scopes": scopes,
            "namespace_by_scope": {scope: scope for scope in scopes},
            "authorization_id_by_scope": ids,
            "authorization_paths": paths,
            "bundle_count": 4,
            "scope_max_invocations": 1,
            "formal_data": False,
            "stage0_data": True,
            "stage0_authorized": True,
        }
        bundle_set["bundle_set_receipt_sha256"] = canonical_sha256(bundle_set)
        set_path.write_text(json.dumps(bundle_set), encoding="utf-8")
        receipt.update(
            {
                "stage0_manifest_path": str(manifest_path),
                "stage0_manifest_file_sha256": sha256_file(manifest_path),
                "bundle_set_receipt_path": str(set_path),
                "bundle_set_receipt_file_sha256": sha256_file(set_path),
                "bundle_set_receipt_sha256": bundle_set[
                    "bundle_set_receipt_sha256"
                ],
            }
        )
        receipt["receipt_sha256"] = authorization_receipt_sha256(receipt)
        for scope in scopes:
            sibling = receipt if scope == "Stage0_F1_root_A" else {
                "approved_scopes": [scope],
                "bundle_set_receipt_sha256": bundle_set[
                    "bundle_set_receipt_sha256"
                ],
                "stage0_manifest_sha256": manifest["manifest_sha256"],
                "stage0_manifest_path": str(manifest_path),
                "stage0_manifest_file_sha256": sha256_file(manifest_path),
            }
            if scope != "Stage0_F1_root_A":
                sibling["receipt_sha256"] = authorization_receipt_sha256(sibling)
            Path(paths[scope]).write_text(json.dumps(sibling), encoding="utf-8")
        return receipt

    def build(self, directory, scope, manifest=None):
        directory = Path(directory)
        spec = planned_scope_spec(scope, stage0_manifest=manifest)
        parent = load_parent_user_authorization()
        request = {
            "schema_version": "cmf_stage0_smoke_scope_request_v1",
            "scope": scope,
            "family": spec["family"],
            "formal_data": False,
            "stage0_data": scope_budget(scope)["stage0_data"],
            "stage0_authorized": True,
        }
        request["scope_request_sha256"] = canonical_sha256(request)
        request_path = directory / "request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        lock = capture_runtime_source_lock(family=spec["family"])
        lock_path = directory / "source_lock.json"
        write_runtime_source_lock(lock_path, lock)
        output = directory / "output"
        guard = directory / "guard.json"
        command = [
            "/nfs_share/lijunhui/Robotwin2/env/bin/python",
            "-m",
            "controlled_multi_future.probes.stage0_smoke_scope_runner",
        ]
        now = datetime.now(timezone.utc)
        budget = scope_budget(scope)
        request.update(
            {
                "planned_root_slot_spec": spec,
                "planned_root_slot_spec_sha256": canonical_sha256(spec),
                "stage0_manifest_sha256": None
                if manifest is None
                else manifest["manifest_sha256"],
                "scope_budget": budget,
                "authorized_command_sha256": command_sha256(command),
                "output_namespace": str(output),
            }
        )
        request.pop("scope_request_sha256", None)
        request["scope_request_sha256"] = canonical_sha256(request)
        request_path.write_text(json.dumps(request), encoding="utf-8")
        bindings = current_stage0_source_bindings()
        receipt = {
            "schema_version": AUTHORIZATION_SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": "controlled_multi_future_stage0_smoke_v1",
            "implementation_revision": "f4_hash_fix_then_12_smoke_v1",
            "authorization_id": "stage0-test-auth-" + scope.replace("_", "-"),
            "authorized_run_id": "stage0-test-run-" + scope.replace("_", "-"),
            "issued_at": (now - timedelta(seconds=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "approved": True,
            "approved_scopes": [scope],
            "family": spec["family"],
            "scene_seed": spec["seed"],
            "planned_root_slot_spec": spec,
            "planned_root_slot_spec_sha256": canonical_sha256(spec),
            "stage0_manifest_sha256": None
            if manifest is None
            else manifest["manifest_sha256"],
            "parent_user_authorization_path": str(PARENT_AUTHORIZATION),
            "parent_user_authorization_file_sha256": sha256_file(PARENT_AUTHORIZATION),
            "parent_user_authorization_sha256": parent[
                "parent_user_authorization_sha256"
            ],
            "approval_request_path": str(request_path),
            "approval_request_file_sha256": sha256_file(request_path),
            "approval_request_sha256": request["scope_request_sha256"],
            "source_lock_receipt_path": str(lock_path),
            "source_lock_receipt_sha256": lock["source_lock_receipt_sha256"],
            "source_bindings": bindings,
            "implementation_source_sha256": bindings[
                "implementation_source_sha256"
            ],
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
            "reviewed_content_commit": "c" * 40,
            "max_invocations": 1,
            "automatic_retry": False,
            "recovery_attempts": 0,
            "formal_data": False,
            "stage0_data": budget["stage0_data"],
            "stage0_authorized": True,
        }
        receipt["receipt_sha256"] = authorization_receipt_sha256(receipt)
        return receipt, now

    def test_stage0_authorization_binds_manifest_and_gpu0_7(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            manifest = self.manifest()
            manifest_path = Path(directory) / "stage0_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            receipt, now = self.build(
                directory, "Stage0_F1_root_A", manifest
            )
            receipt = self.attach_bundle_set(
                directory, receipt, manifest, manifest_path
            )
            with patch(
                "controlled_multi_future.probes.stage0_smoke_authorization_v1.CANONICAL_STAGE0_MANIFEST",
                manifest_path,
            ):
                checked = validate_stage0_smoke_authorization(
                    receipt,
                    requested_scope="Stage0_F1_root_A",
                    now=now,
                    expected_family="F1",
                )
            self.assertTrue(checked["stage0_data"])
            self.assertTrue(checked["stage0_authorized"])
            self.assertEqual(checked["allowed_physical_gpu_indices"], list(range(8)))
            tampered = copy.deepcopy(receipt)
            tampered["allowed_physical_gpu_indices"] = [0]
            tampered["receipt_sha256"] = authorization_receipt_sha256(tampered)
            with patch(
                "controlled_multi_future.probes.stage0_smoke_authorization_v1.CANONICAL_STAGE0_MANIFEST",
                manifest_path,
            ), self.assertRaises(Exception):
                validate_stage0_smoke_authorization(
                    tampered,
                    requested_scope="Stage0_F1_root_A",
                    now=now,
                )

    def test_f4_infrastructure_scope_is_authorized_but_not_stage0_data(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            receipt, now = self.build(
                directory, "F4_candidate_hash_infra_v12", None
            )
            checked = validate_stage0_smoke_authorization(
                receipt,
                requested_scope="F4_candidate_hash_infra_v12",
                now=now,
            )
            self.assertFalse(checked["stage0_data"])
            self.assertTrue(checked["stage0_authorized"])


if __name__ == "__main__":
    unittest.main()
