import copy
from datetime import datetime, timedelta, timezone
import inspect
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from controlled_multi_future.probes.gpu_guard_v2_1 import command_sha256
from controlled_multi_future.probes.gpu_guard_v2_4 import (
    GUARD_SCHEMA_VERSION,
    GuardAuthorizationMismatch,
    GuardBudgetMismatch,
    GuardGpuLeaseUnavailable,
    acquire_physical_gpu_lease,
    build_isolated_child_environment,
    build_guard_binding,
    claim_guard_receipt,
    cleanup_isolated_job_cache,
    main,
    prepare_isolated_job_cache,
    release_physical_gpu_lease,
    validate_guard_binding,
)
from controlled_multi_future.probes.gpu_guard_v2_1 import write_json
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
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
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "family_revision_index": None,
        "allowed_physical_gpu_indices": list(range(8)),
        "authorized_command_sha256": command_sha256(COMMAND),
    }


def consumption():
    value = {
        "schema_version": "cmf_runtime_v3_3_authorization_consumption_v1_1",
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
            "job_cache_environment",
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

    def test_any_authorized_card_is_accepted_and_out_of_range_is_rejected(self):
        binding = build_guard_binding(
            self.auth,
            self.consumption,
            physical_index=4,
            expected_uuid="GPU-four",
            timeout_seconds=1800,
            output_namespace=self.auth["output_namespace"],
            command=COMMAND,
            guard_pid=123,
        )
        self.assertEqual(binding["physical_gpu_index"], 4)
        with self.assertRaises(GuardAuthorizationMismatch):
            build_guard_binding(
                self.auth,
                self.consumption,
                physical_index=8,
                expected_uuid="GPU-out-of-range",
                timeout_seconds=1800,
                output_namespace=self.auth["output_namespace"],
                command=COMMAND,
                guard_pid=123,
            )

    def test_gpu_lease_excludes_same_card_but_allows_different_cards(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            directory = Path(directory)
            first = acquire_physical_gpu_lease(2, lease_directory=directory)
            with self.assertRaises(GuardGpuLeaseUnavailable):
                acquire_physical_gpu_lease(2, lease_directory=directory)
            other = acquire_physical_gpu_lease(3, lease_directory=directory)
            self.assertTrue(release_physical_gpu_lease(other)["released"])
            self.assertTrue(release_physical_gpu_lease(first)["released"])
            again = acquire_physical_gpu_lease(2, lease_directory=directory)
            self.assertTrue(release_physical_gpu_lease(again)["released"])

    def test_job_cache_is_unique_and_all_mutable_cache_env_is_isolated(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            directory = Path(directory)
            first_auth = authorization()
            first_auth["authorization_id"] = "cache-auth-one"
            first_auth["job_cache_root_directory"] = str(directory)
            second_auth = copy.deepcopy(first_auth)
            second_auth["authorization_id"] = "cache-auth-two"
            module = "controlled_multi_future.probes.gpu_guard_v2_4"
            with patch(f"{module}.CANONICAL_JOB_CACHE_DIRECTORY", str(directory)):
                first_path, first_receipt = prepare_isolated_job_cache(first_auth)
                with self.assertRaises(GuardAuthorizationMismatch):
                    prepare_isolated_job_cache(first_auth)
                second_path, second_receipt = prepare_isolated_job_cache(second_auth)
                first_env = build_isolated_child_environment(
                    {"PATH": ""}, "GPU-one", first_receipt
                )
                second_env = build_isolated_child_environment(
                    {"PATH": ""}, "GPU-two", second_receipt
                )
                for key in (
                    "CONDA_PKGS_DIRS",
                    "CUDA_CACHE_PATH",
                    "HF_HOME",
                    "HUGGINGFACE_HUB_CACHE",
                    "HOME",
                    "MPLCONFIGDIR",
                    "NUMBA_CACHE_DIR",
                    "PIP_CACHE_DIR",
                    "TMPDIR",
                    "TORCH_EXTENSIONS_DIR",
                    "TORCH_HOME",
                    "TRITON_CACHE_DIR",
                    "XDG_CACHE_HOME",
                ):
                    self.assertNotEqual(first_env[key], second_env[key])
                    self.assertTrue(first_env[key].startswith(str(first_path) + "/"))
                    self.assertTrue(second_env[key].startswith(str(second_path) + "/"))
                self.assertTrue(cleanup_isolated_job_cache(first_path)["succeeded"])
                self.assertTrue(cleanup_isolated_job_cache(second_path)["succeeded"])
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
        self.assertLess(source.index("signal.signal"), source.index("subprocess.Popen"))
        popen_index = source.index("subprocess.Popen")
        block_index = source.index("signal.SIG_BLOCK")
        running_write_index = source.index(
            "write_json(args.guard_receipt, guard)", popen_index
        )
        restore_mask_index = source.index("signal.SIG_SETMASK", running_write_index)
        self.assertLess(block_index, popen_index)
        self.assertLess(popen_index, running_write_index)
        self.assertLess(running_write_index, restore_mask_index)
        self.assertLess(
            source.index("terminal_cleanup_started = True"),
            source.index("pids_in_process_group"),
        )
        self.assertGreater(
            source.rindex("signal.signal"),
            source.rindex("write_json(args.guard_receipt, guard)"),
        )
        self.assertLess(launch_snapshot_index, consume_index)
        self.assertGreaterEqual(source.count("load_authorization_v3_3"), 2)
        self.assertIn("stdout/stderr paths must be new and immutable", source)
        self.assertIn("failed_guard_internal_prelaunch", source)

    def test_guard_claim_is_exclusive_and_json_updates_are_never_partial(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            path = Path(directory) / "guard.json"
            claim_guard_receipt(path, {"status": "starting"})
            with self.assertRaises(FileExistsError):
                claim_guard_receipt(path, {"status": "other"})
            failures = []
            done = threading.Event()

            def writer():
                for index in range(100):
                    write_json(path, {"index": index, "payload": "x" * 1000})
                done.set()

            thread = threading.Thread(target=writer)
            thread.start()
            while not done.is_set():
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except BaseException as exc:
                    failures.append(exc)
                    break
            thread.join()
            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
