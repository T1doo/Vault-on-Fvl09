import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from controlled_multi_future.f2_dynamic_development_scope_v3 import (
    AUTH_ID,
    IMPLEMENTATION_VERSION,
    SCOPE,
    f2_dynamic_development_budget_v3,
)
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
