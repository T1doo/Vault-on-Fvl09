from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.probes import gpu_guard_v2_4
from controlled_multi_future.probes.gpu_guard_v2_1 import (
    update_child_receipt_v2_1,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    AuthorizationReplayError,
)
from controlled_multi_future.probes.stage0_smoke_authorization_v1_1 import (
    AUTHORIZATION_SCHEMA_VERSION,
    CANONICAL_STAGE0_BUDGET,
    CANONICAL_STAGE0_MANIFEST,
    CONSUMPTION_SCHEMA_VERSION,
    IMPLEMENTATION_VERSION,
    INFRA_AUTHORIZATION_ID,
    INFRA_NAMESPACE,
    STAGE0_AUTHORIZATION_ID_BY_SCOPE,
    STAGE0_NAMESPACE_BY_SCOPE,
    authorization_receipt_sha256,
    consume_authorization_once_v1_1,
    current_stage0_source_bindings_v1_1,
    validate_consumption_receipt_v1_1,
)
from controlled_multi_future.stage0_smoke_budget_v1_1 import (
    F4_INFRA_SCOPE,
    STAGE0_SCOPES,
    budget_artifact,
    scope_budget,
)
from controlled_multi_future.stage0_smoke_parallel_scheduler_v1_1 import (
    assign_stage0_scopes_to_idle_gpus,
)
from controlled_multi_future.stage0_smoke_scope_bundle_v1_1 import (
    CANONICAL_STAGE0_BUDGET_MD,
    CANONICAL_STAGE0_MANIFEST_MD,
    build_f4_infrastructure_bundle_v1_1,
    build_stage0_bundle_set_v1_1,
)
from controlled_multi_future.stage0_smoke_scope_specs_v1_1 import (
    planned_scope_spec,
)


class Stage0SmokeAuthorizationV1_1Test(unittest.TestCase):
    def test_v13_scopes_and_budgets_are_new_and_exact(self):
        self.assertEqual(F4_INFRA_SCOPE, "F4_candidate_hash_infra_v13")
        self.assertEqual(
            STAGE0_SCOPES,
            (
                "Stage0_v1_1_F1_root_A",
                "Stage0_v1_1_F2_root_A",
                "Stage0_v1_1_F3_root_A",
                "Stage0_v1_1_F4_root_A",
            ),
        )
        expected = {
            F4_INFRA_SCOPE: (48, 0, 7200, False),
            STAGE0_SCOPES[0]: (64, 3, 7200, True),
            STAGE0_SCOPES[1]: (64, 3, 7200, True),
            STAGE0_SCOPES[2]: (96, 3, 10800, True),
            STAGE0_SCOPES[3]: (96, 3, 20400, True),
        }
        for scope, wanted in expected.items():
            value = scope_budget(scope)
            self.assertEqual(
                (
                    value["planner_query_limit"],
                    value["execution_limit"],
                    value["timeout_seconds"],
                    value["stage0_data"],
                ),
                wanted,
            )
            self.assertFalse(value["automatic_retry"])
            self.assertEqual(value["recovery_attempts"], 0)
            self.assertEqual(value["allowed_physical_gpu_indices"], list(range(8)))
        artifact = budget_artifact()
        self.assertTrue(artifact["approved"])
        self.assertTrue(artifact["stage0_authorized"])
        self.assertFalse(artifact["stage1_authorized"])
        self.assertFalse(artifact["formal_collection_authorized"])
        self.assertFalse(artifact["training_authorized"])
        self.assertIsNone(artifact["h_reveal"])
        self.assertFalse(artifact["compression_authorized"])
        self.assertFalse(artifact["pi05_authorized"])
        self.assertNotEqual(
            artifact["budget_receipt_sha256"],
            "4ca7471888af9282351a1455bf96965fd565001b43f0806ec1d40e2b67913783",
        )

    def test_infrastructure_spec_binds_v13_and_new_provenance(self):
        spec = planned_scope_spec(F4_INFRA_SCOPE)
        self.assertEqual(spec["scope"], F4_INFRA_SCOPE)
        self.assertIn("v13", spec["slot_id"])
        self.assertEqual(spec["arm"], "right")
        self.assertEqual(
            spec["generator"],
            "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7",
        )
        self.assertEqual(spec["predecessor_scope"], "F4_candidate_hash_infra_v12")
        self.assertFalse(spec["stage0_data"])
        self.assertFalse(spec["formal_data"])

    def test_paths_ids_and_public_builders_do_not_reuse_v12(self):
        self.assertIn("v13", INFRA_NAMESPACE)
        self.assertIn("v1_1", INFRA_NAMESPACE)
        self.assertIn("v13", INFRA_AUTHORIZATION_ID)
        self.assertNotIn("infra-v12", INFRA_AUTHORIZATION_ID)
        self.assertEqual(len(set(STAGE0_NAMESPACE_BY_SCOPE.values())), 4)
        self.assertEqual(len(set(STAGE0_AUTHORIZATION_ID_BY_SCOPE.values())), 4)
        self.assertEqual(
            CANONICAL_STAGE0_MANIFEST.name,
            "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.json",
        )
        self.assertEqual(
            CANONICAL_STAGE0_BUDGET.name,
            "STAGE0_SMOKE_ATTEMPT_BUDGET_V1.json",
        )
        self.assertEqual(
            CANONICAL_STAGE0_MANIFEST_MD.name,
            "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.md",
        )
        self.assertEqual(
            CANONICAL_STAGE0_BUDGET_MD.name,
            "STAGE0_SMOKE_ATTEMPT_BUDGET_V1.md",
        )
        self.assertTrue(callable(build_f4_infrastructure_bundle_v1_1))
        self.assertTrue(callable(build_stage0_bundle_set_v1_1))

    def test_consumption_is_v1_1_single_use_and_self_hashed(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        authorization = {
            "authorization_id": INFRA_AUTHORIZATION_ID,
            "receipt_sha256": "a" * 64,
            "approved_scopes": [F4_INFRA_SCOPE],
            "family": "F4",
            "scene_seed": 20260829,
        }
        module = (
            "controlled_multi_future.probes."
            "stage0_smoke_authorization_v1_1"
        )
        with tempfile.TemporaryDirectory(dir=root) as directory, patch(
            f"{module}.CANONICAL_CONSUMPTION_LEDGER_DIRECTORY", directory
        ):
            receipt = consume_authorization_once_v1_1(
                authorization, ledger_directory=Path(directory)
            )
            checked = validate_consumption_receipt_v1_1(receipt, authorization)
            self.assertEqual(checked["schema_version"], CONSUMPTION_SCHEMA_VERSION)
            self.assertEqual(checked["implementation_version"], IMPLEMENTATION_VERSION)
            with self.assertRaises(AuthorizationReplayError):
                consume_authorization_once_v1_1(
                    authorization, ledger_directory=Path(directory)
                )

    def test_scheduler_requires_four_fresh_unique_cards(self):
        bundles = {
            scope: {
                "scope": scope,
                "family": f"F{index + 1}",
                "physical_gpu_indices": list(range(8)),
                "authorization_path": f"/{scope}.json",
                "guard_path": f"/{scope}.guard.json",
                "output_namespace": f"/{scope}",
                "timeout_seconds": 10,
                "child_command": ["python", scope],
            }
            for index, scope in enumerate(STAGE0_SCOPES)
        }
        snapshots = [
            {
                "physical_index": index,
                "uuid": f"GPU-v1-1-{index}",
                "memory_used_mib": 14,
                "utilization_percent": 0,
                "pstate": "P8",
                "compute_processes": [],
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            for index in range(4)
        ]
        schedule = assign_stage0_scopes_to_idle_gpus(
            {"bundles": bundles}, snapshots
        )
        self.assertTrue(schedule["pass"])
        self.assertEqual(schedule["assigned_scope_count"], 4)
        blocked = assign_stage0_scopes_to_idle_gpus(
            {"bundles": bundles}, snapshots[:3]
        )
        self.assertFalse(blocked["pass"])
        self.assertEqual(blocked["assigned_scope_count"], 0)

    def test_guard_dispatch_and_mandatory_child_seal_cover_v1_1(self):
        source = inspect.getsource(gpu_guard_v2_4)
        self.assertIn("controlled_multi_future_stage0_smoke_v1_1", source)
        self.assertIn("load_stage0_smoke_authorization_v1_1", source)
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            output = Path(directory)
            payload = {
                "schema_version": "cmf_stage0_smoke_guarded_scope_receipt_v1_1",
                "implementation_version": IMPLEMENTATION_VERSION,
                "status": "completed_stage0_smoke_v1_1",
                "orphan_process_count": 0,
                "scene_created": False,
            }
            payload["child_payload_sha256"] = hash_json(payload)
            (output / "receipt.json").write_text(json.dumps(payload))
            self.assertTrue(
                update_child_receipt_v2_1(
                    output,
                    output / "guard.json",
                    {},
                    {},
                    [],
                    {"verified": True},
                )
            )
            invalid = dict(payload)
            invalid.pop("child_payload_sha256")
            (output / "receipt.json").write_text(json.dumps(invalid))
            with self.assertRaises(Exception):
                update_child_receipt_v2_1(
                    output,
                    output / "guard.json",
                    {},
                    {},
                    [],
                    {"verified": True},
                )

    def test_authorization_schema_and_hash_are_versioned(self):
        value = {
            "schema_version": AUTHORIZATION_SCHEMA_VERSION,
            "implementation_version": IMPLEMENTATION_VERSION,
            "authorization_id": INFRA_AUTHORIZATION_ID,
        }
        digest = authorization_receipt_sha256(value)
        self.assertEqual(len(digest), 64)
        self.assertEqual(AUTHORIZATION_SCHEMA_VERSION, "cmf_stage0_smoke_gpu_authorization_v1_1")

    def test_source_bindings_cover_v13_and_all_v1_1_entrypoints(self):
        bindings = current_stage0_source_bindings_v1_1()
        for key in (
            "real_adapter_sha256",
            "f4_candidate_equivalence_sha256",
            "f4_frozen_neutral_binding_sha256",
            "f4_corridor_selection_sha256",
            "stage0_family_runner_sha256",
            "stage0_video_capture_sha256",
            "stage0_manifest_sha256",
            "stage0_manifest_builder_sha256",
            "stage0_finalizer_sha256",
            "stage0_finalizer_entrypoint_sha256",
            "scope_runner_sha256",
            "scope_bundle_builder_sha256",
            "scheduler_sha256",
            "gpu_guard_sha256",
            "gpu_guard_updater_sha256",
            "implementation_source_sha256",
            "budget_receipt_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64, key)


if __name__ == "__main__":
    unittest.main()
