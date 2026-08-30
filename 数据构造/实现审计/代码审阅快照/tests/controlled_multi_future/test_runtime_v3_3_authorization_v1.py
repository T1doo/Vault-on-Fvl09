import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controlled_multi_future.pre_stage0_authorization_v3 import (
    build_scope_request,
    issue_authorization_from_scope_request,
    load_parent_user_authorization,
    validate_scope_request,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
    authorization_receipt_sha256,
    canonical_sha256,
    consume_authorization_once,
    current_source_bindings_v3_3,
    validate_authorization_v3_3,
)
from controlled_multi_future.runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)


PARENT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "USER_AUTHORIZATION_RUNTIME_V3_3_REVISION9_REPAIRS_GPU0_20260830.json"
)
TMP_ROOT = Path("/nfs_share/lijunhui/Robotwin2/tmp")


def reviewed_publication(commit="a" * 40):
    return {
        "reviewed_content_commit": commit,
        "origin_main": commit,
        "vault_worktree_clean": True,
        "active_snapshot_source_sha256": current_source_bindings_v3_3()[
            "implementation_source_sha256"
        ],
    }


def root_authorization(*, auth_id, source_hash, seed=17, revision=1):
    return {
        "authorization_id": auth_id,
        "receipt_sha256": (auth_id.encode().hex() + "0" * 64)[:64],
        "authorized_run_id": f"run-{auth_id}",
        "approved_scopes": ["F1_planner_root_per_revision"],
        "family": "F1",
        "family_revision_index": revision,
        "revision_ledger_directory": "unused-patched-in-test",
        "scene_seed": seed,
        "planned_root_slot_spec": {
            "slot_id": "f1-root-a",
            "family": "F1",
            "arm": "left",
            "seed": seed,
            "implementation_revision_index": revision,
            "implementation_revision": f"f1-v3-3-r{revision}",
        },
        "planned_root_slot_spec_sha256": "b" * 64,
        "implementation_source_sha256": source_hash,
        "output_namespace": f"/nfs_share/lijunhui/Robotwin2/tmp/{auth_id}",
        "source_lock_receipt_sha256": "c" * 64,
    }


class RuntimeV3_3AuthorizationV1Test(unittest.TestCase):
    def test_parent_scope_revision_map_rejects_unapproved_work(self):
        parent = load_parent_user_authorization(PARENT)
        cases = (
            ("F1_planner_root_per_revision", "F1", 5),
            ("F4_block_root_per_revision", "F4", 7),
            ("F4_micro_lift_diagnosis_per_revision", "F4", 8),
            ("F4_cube_grasp_no_action_ik", "F4", None),
            ("canonical_prefix_real_smoke", "F1", None),
            ("F2_diagnosis_root_per_revision", "F2", 5),
            ("F3_prefix_root_per_revision", "F3", 7),
        )
        for scope, family, revision in cases:
            planned = {
                "slot_id": "negative-scope",
                "family": family,
                "arm": "right" if family == "F4" else "left",
                "seed": 17,
            }
            if revision is not None:
                planned.update(
                    {
                        "implementation_revision_index": revision,
                        "implementation_revision": f"{family.lower()}-r{revision}",
                    }
                )
            with self.subTest(scope=scope, revision=revision), self.assertRaisesRegex(
                ValueError, "authorization.*map"
            ):
                build_scope_request(
                    parent_user_authorization=parent,
                    scope=scope,
                    family=family,
                    scene_seed=17,
                    planned_root_slot_spec=planned,
                    reviewed_content_commit="a" * 40,
                    authorization_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/auth.json",
                    source_lock_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/lock.json",
                    consumption_ledger_directory=(
                        "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/authorizations"
                    ),
                    revision_ledger_directory=(
                        "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/family_revisions"
                        if revision is not None
                        else None
                    ),
                    family_revision_index=revision,
                    guard_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/guard.json",
                    output_namespace="/nfs_share/lijunhui/Robotwin2/tmp/output",
                    exact_child_command=["python", "child.py"],
                    allowed_physical_gpu_indices=[0],
                    reviewed_publication=reviewed_publication(),
                )

    def test_parent_and_scope_request_bind_gpu0_budget_source_and_revision(self):
        parent = load_parent_user_authorization(PARENT)
        planned = {
            "slot_id": "f2-root-a",
            "family": "F2",
            "arm": "left",
            "seed": 17,
            "origin": "runtime_v3_3_nonformal",
            "implementation_revision_index": 9,
            "implementation_revision": "f2-v3-3-r9",
        }
        request = build_scope_request(
            parent_user_authorization=parent,
            scope="F2_diagnosis_root_per_revision",
            family="F2",
            scene_seed=17,
            planned_root_slot_spec=planned,
            reviewed_content_commit="a" * 40,
            authorization_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/auth.json",
            source_lock_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/lock.json",
            consumption_ledger_directory=(
                "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/authorizations"
            ),
            revision_ledger_directory=(
                "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/family_revisions"
            ),
            family_revision_index=9,
            guard_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/guard.json",
            output_namespace="/nfs_share/lijunhui/Robotwin2/tmp/output",
            exact_child_command=["python", "-m", "controlled_multi_future.probes.runtime_v3_3_scope_runner"],
            allowed_physical_gpu_indices=[0],
            reviewed_publication=reviewed_publication(),
        )
        self.assertEqual(request["family_revision_index"], 9)
        self.assertEqual(request["allowed_physical_gpu_indices"], [0])
        self.assertEqual(request["scope_budget"]["planner_query_limit"], 96)
        self.assertIn("root_orchestrator_sha256", request["source_bindings"])
        tampered_publication = copy.deepcopy(request)
        tampered_publication["reviewed_publication"]["origin_main"] = "b" * 40
        unsigned = dict(tampered_publication)
        unsigned.pop("scope_request_sha256")
        tampered_publication["scope_request_sha256"] = canonical_sha256(unsigned)
        with self.assertRaisesRegex(ValueError, "reviewed publication"):
            validate_scope_request(tampered_publication, parent)
        for changed in ([1], [0, 1], list(range(8))):
            with self.subTest(changed=changed), self.assertRaisesRegex(
                ValueError, "GPU0"
            ):
                build_scope_request(
                    parent_user_authorization=parent,
                    scope="F2_diagnosis_root_per_revision",
                    family="F2",
                    scene_seed=17,
                    planned_root_slot_spec=planned,
                    reviewed_content_commit="a" * 40,
                    authorization_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/auth.json",
                    source_lock_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/lock.json",
                    consumption_ledger_directory=(
                        "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/authorizations"
                    ),
                    revision_ledger_directory=(
                        "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/family_revisions"
                    ),
                    family_revision_index=9,
                    guard_receipt_path="/nfs_share/lijunhui/Robotwin2/tmp/guard.json",
                    output_namespace="/nfs_share/lijunhui/Robotwin2/tmp/output",
                    exact_child_command=["python", "child.py"],
                    allowed_physical_gpu_indices=changed,
                    reviewed_publication=reviewed_publication(),
                )

    def test_canonical_one_shot_and_nine_revision_ledger_are_fail_closed(self):
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as directory:
            directory = Path(directory)
            auth_ledger = directory / "auth"
            revision_ledger = directory / "revision"
            module = "controlled_multi_future.probes.runtime_v3_3_authorization_v1"
            with patch(f"{module}.CANONICAL_CONSUMPTION_LEDGER_DIRECTORY", str(auth_ledger)), patch(
                f"{module}.CANONICAL_REVISION_LEDGER_DIRECTORY", str(revision_ledger)
            ):
                first = root_authorization(
                    auth_id="auth-r1", source_hash="1" * 64, revision=1
                )
                first["revision_ledger_directory"] = str(revision_ledger)
                consume_authorization_once(first, ledger_directory=auth_ledger)
                with self.assertRaisesRegex(Exception, "already.*consumed"):
                    consume_authorization_once(first, ledger_directory=auth_ledger)

                same_source = root_authorization(
                    auth_id="auth-r2-same", source_hash="1" * 64, revision=2
                )
                same_source["revision_ledger_directory"] = str(revision_ledger)
                with self.assertRaisesRegex(
                    AuthorizationBindingError, "different implementation source"
                ):
                    consume_authorization_once(same_source, ledger_directory=auth_ledger)
                self.assertFalse((auth_ledger / "auth-r2-same.json").exists())

                changed_seed = root_authorization(
                    auth_id="auth-r2-seed", source_hash="2" * 64, seed=18, revision=2
                )
                changed_seed["revision_ledger_directory"] = str(revision_ledger)
                with self.assertRaisesRegex(
                    AuthorizationBindingError, "frozen root identity"
                ):
                    consume_authorization_once(changed_seed, ledger_directory=auth_ledger)
                self.assertFalse((auth_ledger / "auth-r2-seed.json").exists())

                second = root_authorization(
                    auth_id="auth-r2", source_hash="2" * 64, revision=2
                )
                second["revision_ledger_directory"] = str(revision_ledger)
                receipt = consume_authorization_once(
                    second, ledger_directory=auth_ledger
                )
                self.assertTrue(Path(receipt["revision_consumption_path"]).is_file())

                third = root_authorization(
                    auth_id="auth-r3", source_hash="3" * 64, revision=3
                )
                third["revision_ledger_directory"] = str(revision_ledger)
                third_receipt = consume_authorization_once(
                    third, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(third_receipt["revision_consumption_path"]).is_file()
                )

                fourth = root_authorization(
                    auth_id="auth-r4", source_hash="4" * 64, revision=4
                )
                fourth["revision_ledger_directory"] = str(revision_ledger)
                fourth_receipt = consume_authorization_once(
                    fourth, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(fourth_receipt["revision_consumption_path"]).is_file()
                )
                fifth = root_authorization(
                    auth_id="auth-r5", source_hash="5" * 64, revision=5
                )
                fifth["revision_ledger_directory"] = str(revision_ledger)
                fifth_receipt = consume_authorization_once(
                    fifth, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(fifth_receipt["revision_consumption_path"]).is_file()
                )
                sixth = root_authorization(
                    auth_id="auth-r6", source_hash="6" * 64, revision=6
                )
                sixth["revision_ledger_directory"] = str(revision_ledger)
                sixth_receipt = consume_authorization_once(
                    sixth, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(sixth_receipt["revision_consumption_path"]).is_file()
                )
                seventh = root_authorization(
                    auth_id="auth-r7", source_hash="7" * 64, revision=7
                )
                seventh["revision_ledger_directory"] = str(revision_ledger)
                seventh_receipt = consume_authorization_once(
                    seventh, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(seventh_receipt["revision_consumption_path"]).is_file()
                )
                eighth = root_authorization(
                    auth_id="auth-r8", source_hash="8" * 64, revision=8
                )
                eighth["revision_ledger_directory"] = str(revision_ledger)
                eighth_receipt = consume_authorization_once(
                    eighth, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(eighth_receipt["revision_consumption_path"]).is_file()
                )
                ninth = root_authorization(
                    auth_id="auth-r9", source_hash="9" * 64, revision=9
                )
                ninth["revision_ledger_directory"] = str(revision_ledger)
                ninth_receipt = consume_authorization_once(
                    ninth, ledger_directory=auth_ledger
                )
                self.assertTrue(
                    Path(ninth_receipt["revision_consumption_path"]).is_file()
                )

    def test_noncanonical_ledger_is_rejected_before_write(self):
        value = root_authorization(
            auth_id="auth-bad-ledger", source_hash="1" * 64, revision=1
        )
        with self.assertRaisesRegex(AuthorizationBindingError, "not canonical"):
            consume_authorization_once(
                value, ledger_directory=TMP_ROOT / "alternate-ledger"
            )

    def test_full_request_source_lock_authorization_and_tamper_binding(self):
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as directory:
            directory = Path(directory)
            request_path = directory / "request.json"
            lock_path = directory / "lock.json"
            auth_path = directory / "authorization.json"
            parent = load_parent_user_authorization(PARENT)
            planned = {
                "slot_id": "pilot-F4-A-prestage0",
                "family": "F4",
                "arm": "right",
                "seed": 17,
                "origin": "test",
                "implementation_revision_index": 9,
                "implementation_revision": "f4-v3-3-r9-block-root",
            }
            request = build_scope_request(
                parent_user_authorization=parent,
                scope="F4_block_root_per_revision",
                family="F4",
                scene_seed=17,
                planned_root_slot_spec=planned,
                reviewed_content_commit="d" * 40,
                authorization_receipt_path=str(auth_path),
                source_lock_receipt_path=str(lock_path),
                consumption_ledger_directory=(
                    "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/authorizations"
                ),
                revision_ledger_directory=(
                    "/nfs_share/lijunhui/Robotwin2/runtime_v3_3_authorization_ledger/family_revisions"
                ),
                family_revision_index=9,
                guard_receipt_path=str(directory / "guard.json"),
                output_namespace=str(directory / "output"),
                exact_child_command=["python", "child.py"],
                allowed_physical_gpu_indices=[0],
                reviewed_publication=reviewed_publication("d" * 40),
            )
            request_path.write_text(
                json.dumps(request, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            source_lock = capture_runtime_source_lock(family="F4")
            write_runtime_source_lock(lock_path, source_lock)
            authorization = issue_authorization_from_scope_request(
                scope_request_path=request_path,
                parent_user_authorization_path=PARENT,
                source_lock_receipt=source_lock,
                authorization_id="test-f4-micro-auth",
                authorized_run_id="test-f4-micro-run",
                validity_seconds=3600,
            )
            auth_path.write_text(
                json.dumps(authorization, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            validated = validate_authorization_v3_3(
                authorization,
                requested_scope="F4_block_root_per_revision",
                expected_family="F4",
                expected_seed=17,
                expected_output_namespace=str(directory / "output"),
                expected_reviewed_content_commit="d" * 40,
            )
            self.assertEqual(validated["receipt_sha256"], authorization["receipt_sha256"])
            tampered = copy.deepcopy(authorization)
            tampered["scene_seed"] = 18
            tampered["receipt_sha256"] = authorization_receipt_sha256(tampered)
            with self.assertRaisesRegex(
                AuthorizationBindingError, "request/authorization mismatch"
            ):
                validate_authorization_v3_3(
                    tampered,
                    requested_scope="F4_block_root_per_revision",
                )
            tampered_guard = copy.deepcopy(authorization)
            tampered_guard["guard_receipt_path"] = str(
                directory / "other-guard.json"
            )
            tampered_guard["receipt_sha256"] = authorization_receipt_sha256(
                tampered_guard
            )
            with self.assertRaisesRegex(
                AuthorizationBindingError, "guard_receipt_path"
            ):
                validate_authorization_v3_3(
                    tampered_guard,
                    requested_scope="F4_block_root_per_revision",
                )


if __name__ == "__main__":
    unittest.main()
