import copy
import unittest
from unittest import mock

from controlled_multi_future.runtime_source_lock_v1 import (
    SOURCE_COMMIT,
    SOURCE_LOCK_SCHEMA_VERSION,
    SourceLockError,
    _canonical_sha256,
    capture_runtime_source_lock,
    validate_runtime_source_lock,
)


def snapshot():
    return {
        "family": "F1",
        "repo_root": "/nfs_share/lijunhui/Robotwin2/project/RoboTwin",
        "official_repo_commit": SOURCE_COMMIT,
        "expected_official_repo_commit": SOURCE_COMMIT,
        "official_worktree_clean": True,
        "official_tracked_status": "",
        "critical_source_hashes": {"envs/_base_task.py": "1" * 64},
        "asset_hashes": {"assets/objects/062_plasticbox/model_data3.json": "2" * 64},
        "config_hashes": {"task_config/_camera_config.yml": "3" * 64},
        "implementation_source_sha256": "4" * 64,
        "environment_lock": {
            "activation_script_sha256": "5" * 64,
            "sapien_version": "3.0.0b1",
            "torch_version": "2.4.1",
        },
        "dependency_locks": {"curobo_source_tree_sha256": "6" * 64},
        "source_lock_pass": True,
    }


def receipt(value=None):
    payload = {
        "schema_version": SOURCE_LOCK_SCHEMA_VERSION,
        "captured_at": "2026-08-29T12:00:00+00:00",
        "snapshot": copy.deepcopy(value or snapshot()),
    }
    payload["source_lock_receipt_sha256"] = _canonical_sha256(payload)
    return payload


class RuntimeSourceLockV1Test(unittest.TestCase):
    def test_valid_snapshot(self):
        with mock.patch(
            "controlled_multi_future.runtime_source_lock_v1.build_runtime_source_lock_snapshot",
            return_value=snapshot(),
        ):
            result = validate_runtime_source_lock(receipt(), expected_family="F1")
        self.assertTrue(result["snapshot"]["source_lock_pass"])

    def test_commit_dirty_and_each_hash_class_mismatch_fail(self):
        mutations = {
            "commit": lambda x: x.__setitem__("official_repo_commit", "0" * 40),
            "dirty": lambda x: x.__setitem__("official_worktree_clean", False),
            "critical": lambda x: x["critical_source_hashes"].__setitem__("envs/_base_task.py", "0" * 64),
            "asset": lambda x: x["asset_hashes"].__setitem__(
                "assets/objects/062_plasticbox/model_data3.json", "0" * 64
            ),
            "config": lambda x: x["config_hashes"].__setitem__("task_config/_camera_config.yml", "0" * 64),
            "implementation": lambda x: x.__setitem__("implementation_source_sha256", "0" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                changed = snapshot()
                mutate(changed)
                with mock.patch(
                    "controlled_multi_future.runtime_source_lock_v1.build_runtime_source_lock_snapshot",
                    return_value=snapshot(),
                ):
                    with self.assertRaises(SourceLockError):
                        validate_runtime_source_lock(receipt(changed), expected_family="F1")

    def test_capture_fails_when_snapshot_gate_fails(self):
        failed = snapshot()
        failed["source_lock_pass"] = False
        with mock.patch(
            "controlled_multi_future.runtime_source_lock_v1.build_runtime_source_lock_snapshot",
            return_value=failed,
        ):
            with self.assertRaises(SourceLockError):
                capture_runtime_source_lock(family="F1")

    def test_receipt_hash_and_family_are_bound(self):
        value = receipt()
        value["source_lock_receipt_sha256"] = "0" * 64
        with self.assertRaises(SourceLockError):
            validate_runtime_source_lock(value, expected_family="F1")
        with mock.patch(
            "controlled_multi_future.runtime_source_lock_v1.build_runtime_source_lock_snapshot",
            return_value=snapshot(),
        ):
            with self.assertRaises(SourceLockError):
                validate_runtime_source_lock(receipt(), expected_family="F2")


if __name__ == "__main__":
    unittest.main()
