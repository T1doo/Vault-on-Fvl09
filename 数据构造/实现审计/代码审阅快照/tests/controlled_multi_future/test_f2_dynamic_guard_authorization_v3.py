import inspect
import json
import os
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from controlled_multi_future.f2_dynamic_development_scope_v3 import (
    AUTH_ID,
    IMPLEMENTATION_VERSION,
    SCOPE,
    f2_dynamic_development_budget_v3,
    parent_authorization_v3,
)
import controlled_multi_future.f2_dynamic_development_scope_v3 as scope_module
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f2_dynamic_search_contract_v3 import (
    build_cpu_static_screening_v3,
)
from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
    build_static_compatibility_matrix_v3,
)
from controlled_multi_future.gpu_parallel_policy_v2 import (
    current_gpu_policy_artifact,
)
from controlled_multi_future.runtime_source_lock_v1 import (
    capture_runtime_source_lock,
)
from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes import (
    f2_dynamic_development_authorization_v3 as authorization_module,
)
from controlled_multi_future.probes import (
    f2_dynamic_development_scope_runner_v3 as runner_module,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    AuthorizationReplayError,
)


class F2DynamicGuardAuthorizationV3Test(unittest.TestCase):
    def fake_authorization(self, output):
        matrix = Path(output).parent / "matrix.json"
        screening = Path(output).parent / "screening.json"
        matrix.write_text("{}\n", encoding="utf-8")
        screening.write_text("{}\n", encoding="utf-8")
        return {
            "implementation_version": IMPLEMENTATION_VERSION,
            "authorization_id": AUTH_ID,
            "receipt_sha256": "a" * 64,
            "output_namespace": str(output),
            "matrix_publication_path": str(matrix),
            "screening_publication_path": str(screening),
            "implementation_source_sha256": "b" * 64,
            "source_lock_receipt_sha256": "c" * 64,
            "budget": f2_dynamic_development_budget_v3(),
            "matrix_sha256": "d" * 64,
            "screening_sha256": "e" * 64,
        }

    def test_authorization_source_binds_every_canonical_publication_and_dual_hash(self):
        source = inspect.getsource(authorization_module.validate)
        for token in (
            "budget_publication_path",
            "parent_user_authorization_path",
            "matrix_publication_path",
            "screening_publication_path",
            "scope_publication_path",
            "source_lock_receipt_path",
            "implementation_source_sha256",
            "approval_request_path",
            "authorized_command_sha256",
            "consumption_ledger_directory",
            "gpu_lease_directory",
            "job_cache_root_directory",
            "guard_receipt_path",
        ):
            self.assertIn(token, source)

    def test_full_canonical_validate_passes_single_hash_and_rejects_basename_output(self):
        matrix = build_static_compatibility_matrix_v3()
        screening = build_cpu_static_screening_v3(matrix)
        budget = f2_dynamic_development_budget_v3()
        parent = parent_authorization_v3()
        issued = datetime(2026, 8, 31, 13, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            root = Path(directory)
            paths = {
                "budget": root / "budget.json",
                "parent": root / "parent.json",
                "matrix": root / "matrix.json",
                "screening": root / "screening.json",
                "scope": root / "scope.json",
                "source": root / "source.json",
                "request": root / "request.json",
                "auth": root / "auth.json",
                "output": root / "output",
                "guard": root / "guard.json",
            }

            def write(path, value):
                path.write_text(
                    json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                )

            def fsha(path):
                return hashlib.sha256(path.read_bytes()).hexdigest()

            write(paths["budget"], budget)
            write(paths["parent"], parent)
            write(paths["matrix"], matrix)
            write(paths["screening"], screening)
            planned = {
                "schema_version": "cmf_f2_dynamic_development_planned_scope_spec_v3_test",
                "scope": SCOPE,
                "matrix_sha256": matrix["matrix_sha256"],
                "screening_sha256": screening["screening_sha256"],
                "dynamic_scope": screening["dynamic_scope"],
                "formal_data": False,
                "stage0_data": False,
                "stage1_authorized": False,
            }
            planned["planned_scope_spec_sha256"] = hash_json(planned)
            publication = {
                "schema_version": "cmf_f2_dynamic_development_scope_publication_v3_test",
                "scope": SCOPE,
                "matrix_sha256": matrix["matrix_sha256"],
                "screening_sha256": screening["screening_sha256"],
                "budget_receipt_sha256": budget["budget_receipt_sha256"],
                "planned_scope_spec": planned,
            }
            publication["scope_publication_sha256"] = hash_json(publication)
            write(paths["scope"], publication)
            source = capture_runtime_source_lock(family="F2")
            write(paths["source"], source)
            child = [
                "/nfs_share/lijunhui/Robotwin2/env/bin/python",
                "-m",
                "controlled_multi_future.probes.f2_dynamic_development_scope_runner_v3",
                "--authorization-receipt",
                str(paths["auth"]),
            ]
            request = {
                "schema_version": "cmf_f2_dynamic_development_scope_request_v3_test",
                "scope": SCOPE,
                "matrix_sha256": matrix["matrix_sha256"],
                "screening_sha256": screening["screening_sha256"],
                "authorized_command": child,
                "authorized_command_sha256": command_sha256(child),
                "output_namespace": str(paths["output"]),
            }
            request["scope_request_sha256"] = hash_json(request)
            write(paths["request"], request)
            policy = current_gpu_policy_artifact()
            authorization = {
                "schema_version": authorization_module.AUTH_SCHEMA,
                "implementation_version": IMPLEMENTATION_VERSION,
                "scope": SCOPE,
                "approved": True,
                "approved_scopes": [SCOPE],
                "authorization_id": AUTH_ID,
                "authorized_run_id": AUTH_ID + "-run",
                "issued_at": issued.isoformat(),
                "expires_at": (issued + timedelta(seconds=3600)).isoformat(),
                "family": "F2",
                "scene_seed": 20260829,
                "max_invocations": 1,
                "single_use": True,
                "automatic_retry": False,
                "recovery_attempts": 0,
                "formal_data": False,
                "stage0_data": False,
                "stage0_authorized": False,
                "stage1_authorized": False,
                "matrix_sha256": matrix["matrix_sha256"],
                "screening_sha256": screening["screening_sha256"],
                "budget": budget,
                "budget_sha256": hash_json(budget),
                "budget_publication_path": str(paths["budget"]),
                "budget_publication_file_sha256": fsha(paths["budget"]),
                "parent_user_authorization_path": str(paths["parent"]),
                "parent_user_authorization_file_sha256": fsha(paths["parent"]),
                "parent_user_authorization_sha256": parent[
                    "parent_user_authorization_sha256"
                ],
                "matrix_publication_path": str(paths["matrix"]),
                "matrix_publication_file_sha256": fsha(paths["matrix"]),
                "screening_publication_path": str(paths["screening"]),
                "screening_publication_file_sha256": fsha(paths["screening"]),
                "scope_publication_path": str(paths["scope"]),
                "scope_publication_file_sha256": fsha(paths["scope"]),
                "scope_publication_sha256": publication[
                    "scope_publication_sha256"
                ],
                "planned_scope_spec": planned,
                "planned_scope_spec_sha256": planned[
                    "planned_scope_spec_sha256"
                ],
                "source_lock_receipt_path": str(paths["source"]),
                "source_lock_receipt_sha256": source[
                    "source_lock_receipt_sha256"
                ],
                "implementation_source_sha256": source["snapshot"][
                    "implementation_source_sha256"
                ],
                "approval_request_path": str(paths["request"]),
                "approval_request_file_sha256": fsha(paths["request"]),
                "approval_request_sha256": request["scope_request_sha256"],
                "authorized_command": child,
                "authorized_command_sha256": command_sha256(child),
                "output_namespace": str(paths["output"]),
                "guard_receipt_path": str(paths["guard"]),
                "consumption_ledger_directory": authorization_module.CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
                "gpu_lease_directory": authorization_module.CANONICAL_GPU_LEASE_DIRECTORY,
                "job_cache_root_directory": authorization_module.CANONICAL_JOB_CACHE_DIRECTORY,
                "reviewed_content_commit": "a" * 40,
                "timeout_seconds": budget["maximum_wall_time_seconds"],
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
            authorization["receipt_sha256"] = authorization_module.receipt_sha(
                authorization
            )
            self.assertNotIn("authorization_sha256", authorization)
            patches = (
                patch.object(authorization_module, "BUDGET", paths["budget"]),
                patch.object(authorization_module, "PARENT", paths["parent"]),
                patch.object(authorization_module, "MATRIX", paths["matrix"]),
                patch.object(
                    authorization_module, "SCREENING", paths["screening"]
                ),
                patch.object(authorization_module, "PUBLICATION", paths["scope"]),
                patch.object(authorization_module, "SOURCE", paths["source"]),
                patch.object(authorization_module, "REQUEST", paths["request"]),
                patch.object(authorization_module, "OUTPUT", paths["output"]),
                patch.object(authorization_module, "GUARD", paths["guard"]),
                patch.object(scope_module, "OUTPUT", paths["output"]),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
                checked = authorization_module.validate(
                    authorization,
                    requested_scope=SCOPE,
                    now=issued + timedelta(seconds=1),
                    expected_family="F2",
                    expected_seed=20260829,
                    expected_output_namespace=str(paths["output"]),
                    expected_reviewed_content_commit="a" * 40,
                )
                self.assertEqual(
                    checked["receipt_sha256"], authorization["receipt_sha256"]
                )
                tampered = json.loads(json.dumps(authorization))
                tampered["output_namespace"] = scope_module.NAMESPACE
                tampered["receipt_sha256"] = authorization_module.receipt_sha(
                    tampered
                )
                with self.assertRaises(Exception):
                    authorization_module.validate(
                        tampered,
                        requested_scope=SCOPE,
                        now=issued + timedelta(seconds=1),
                        expected_family="F2",
                        expected_seed=20260829,
                    )

    def test_consumption_is_hash_bound_and_o_excl_single_use(self):
        authorization = {
            "receipt_sha256": "a" * 64,
            "matrix_sha256": "b" * 64,
            "screening_sha256": "c" * 64,
        }
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            with patch.object(
                authorization_module,
                "CANONICAL_CONSUMPTION_LEDGER_DIRECTORY",
                str(Path(directory).resolve()),
            ):
                receipt = authorization_module.consume(
                    authorization, ledger_directory=Path(directory)
                )
                checked = authorization_module.validate_consumption(
                    receipt, authorization
                )
                self.assertEqual(checked["max_invocations"], 1)
                with self.assertRaises(AuthorizationReplayError):
                    authorization_module.consume(
                        authorization, ledger_directory=Path(directory)
                    )
                tampered = dict(receipt)
                tampered["matrix_sha256"] = "f" * 64
                with self.assertRaises(Exception):
                    authorization_module.validate_consumption(
                        tampered, authorization
                    )

    def test_child_refuses_direct_cli_without_consumption_and_guard(self):
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            auth_path = Path(directory) / "auth.json"
            auth_path.write_text("{}\n", encoding="utf-8")
            authorization = self.fake_authorization(Path(directory) / "output")
            with patch.object(runner_module, "load", return_value=authorization), patch.dict(
                os.environ,
                {
                    "CMF_AUTHORIZATION_CONSUMPTION_RECEIPT": "",
                    "CMF_GPU_GUARD_RECEIPT": "",
                },
                clear=False,
            ):
                with self.assertRaisesRegex(PermissionError, "Guard binding missing"):
                    runner_module.main(
                        ["--authorization-receipt", str(auth_path)]
                    )

    def test_mock_guard_uuid_consumption_and_cleanup_budget_pass(self):
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            root = Path(directory)
            output = root / "output"
            authorization = self.fake_authorization(output)
            auth_path = root / "auth.json"
            auth_path.write_text("{}\n", encoding="utf-8")
            consumption_path = root / "consumption.json"
            consumption_path.write_text("{}\n", encoding="utf-8")
            guard_path = root / "guard.json"
            guard_path.write_text(
                json.dumps(
                    {
                        "binding": {
                            "physical_gpu_index": 4,
                            "expected_gpu_uuid": "GPU-f2-test",
                        }
                    }
                ),
                encoding="utf-8",
            )
            consumption = {
                "consumption_receipt_sha256": "f" * 64,
                "path": str(consumption_path),
            }
            result = {
                "status": "selected_development_root_completed",
                "planner_query_count_total": 10,
                "prefix_reference_execution_count": 2,
                "branch_execution_attempt_count": 3,
                "recovery_attempt_count": 0,
                "cleanup_records": [
                    {
                        "cleanup_safety_pass": True,
                        "orphan_process_count": 0,
                    }
                ],
            }
            instance = Mock()
            instance.run.return_value = result
            with patch.object(runner_module, "load", return_value=authorization), patch.object(
                runner_module, "load_consumption", return_value=consumption
            ), patch.object(
                runner_module,
                "require_atomic_gpu_guard_v2_4",
                return_value={
                    "binding": {"physical_gpu_index": 4},
                    "precheck": {"uuid": "GPU-f2-test"},
                },
            ) as guard, patch.object(
                runner_module,
                "F2DynamicThenDevelopmentRunnerV3",
                return_value=instance,
            ), patch.dict(
                os.environ,
                {
                    "CMF_AUTHORIZATION_CONSUMPTION_RECEIPT": str(
                        consumption_path
                    ),
                    "CMF_GPU_GUARD_RECEIPT": str(guard_path),
                    "CUDA_VISIBLE_DEVICES": "GPU-f2-test",
                },
                clear=False,
            ):
                code = runner_module.main(
                    ["--authorization-receipt", str(auth_path)]
                )
            self.assertEqual(code, 0)
            guard.assert_called_once_with(
                authorization,
                consumption,
                expected_uuid="GPU-f2-test",
                physical_index=4,
            )
            outer = json.loads((output / "receipt.json").read_text())
            self.assertEqual(outer["status"], "accepted")
            self.assertTrue(outer["budget_validation"]["pass"])
            self.assertTrue(outer["pass"])

    def test_uuid_mismatch_stops_before_guard_or_runner(self):
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            root = Path(directory)
            authorization = self.fake_authorization(root / "output")
            auth_path = root / "auth.json"
            auth_path.write_text("{}\n", encoding="utf-8")
            consumption_path = root / "consumption.json"
            consumption_path.write_text("{}\n", encoding="utf-8")
            guard_path = root / "guard.json"
            guard_path.write_text(
                json.dumps(
                    {
                        "binding": {
                            "physical_gpu_index": 2,
                            "expected_gpu_uuid": "GPU-expected",
                        }
                    }
                ),
                encoding="utf-8",
            )
            guard = Mock()
            with patch.object(runner_module, "load", return_value=authorization), patch.object(
                runner_module,
                "load_consumption",
                return_value={"consumption_receipt_sha256": "f" * 64},
            ), patch.object(
                runner_module, "require_atomic_gpu_guard_v2_4", guard
            ), patch.dict(
                os.environ,
                {
                    "CMF_AUTHORIZATION_CONSUMPTION_RECEIPT": str(
                        consumption_path
                    ),
                    "CMF_GPU_GUARD_RECEIPT": str(guard_path),
                    "CUDA_VISIBLE_DEVICES": "GPU-wrong",
                },
                clear=False,
            ):
                with self.assertRaisesRegex(RuntimeError, "UUID mismatch"):
                    runner_module.main(
                        ["--authorization-receipt", str(auth_path)]
                    )
            guard.assert_not_called()

    def test_child_budget_and_cleanup_fail_closed(self):
        valid = runner_module.validate_child_budget_cleanup_v3(
            {
                "planner_query_count_total": 10,
                "prefix_reference_execution_count": 2,
                "branch_execution_attempt_count": 3,
                "recovery_attempt_count": 0,
                "cleanup_records": [
                    {
                        "cleanup_safety_pass": True,
                        "orphan_process_count": 0,
                    }
                ],
            }
        )
        self.assertTrue(valid["pass"])
        over_budget = runner_module.validate_child_budget_cleanup_v3(
            {
                "planner_query_count_total": 769,
                "prefix_reference_execution_count": 14,
                "branch_execution_attempt_count": 4,
                "recovery_attempt_count": 1,
                "cleanup_records": [
                    {
                        "cleanup_safety_pass": False,
                        "orphan_process_count": 1,
                    }
                ],
            }
        )
        self.assertFalse(over_budget["pass"])
        self.assertTrue(all(not value for value in over_budget["checks"].values()))


if __name__ == "__main__":
    unittest.main()
