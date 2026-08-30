import copy
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

from controlled_multi_future.f4_candidate_equivalence_v12 import (
    POSITION_ATOL_M,
    audit_f4_candidate_equivalence_v12,
)
from controlled_multi_future.f4_exact_corridor_application_v11 import (
    build_f4_exact_A_corridors_v11,
)
from controlled_multi_future.families import F1ObjectSelection
from controlled_multi_future.probes import gpu_guard_v2_4
from controlled_multi_future.probes.gpu_guard_v2_1 import (
    update_child_receipt_v2_1,
)
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter
from controlled_multi_future.probes.stage0_smoke_authorization_v1 import (
    current_stage0_source_bindings,
)
from controlled_multi_future.raw_writer import (
    validate_raw_artifact_contract,
    write_raw_attempt,
)
from controlled_multi_future.root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
)
from controlled_multi_future.stage0_smoke_budget_v1 import (
    ALLOWED_PHYSICAL_GPU_INDICES,
    STAGE0_SCOPES,
    budget_artifact,
)
from controlled_multi_future.stage0_smoke_finalizer_v1 import (
    _finalize_stage0_smoke_payloads,
)
from controlled_multi_future.stage0_smoke_manifest_v1 import (
    build_stage0_smoke_manifest,
    planned_stage0_root_spec,
)
from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.stage0_smoke_family_runner_v1 import (
    Stage0SmokeFamilyRunnerV1,
    _attempt_status,
    _audit_root_terminal_evidence,
)
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F2FrozenLayoutConfigurationError,
)
from controlled_multi_future.stage0_smoke_parallel_scheduler_v1 import (
    assign_stage0_scopes_to_idle_gpus,
)
from controlled_multi_future.stage0_smoke_scope_specs_v1 import planned_scope_spec


def base_a_targets():
    q = [1.0, 0.0, 0.0, 0.0]
    values = {
        "pregrasp": [0.16, 0.00, 0.98, *q],
        "grasp": [0.16, 0.01, 0.90, *q],
        "lift": [0.16, 0.01, 0.92, *q],
        "carry_mid": [0.155, 0.08, 1.00, *q],
        "preplace": [0.15, 0.15, 1.00, *q],
        "release": [0.15, 0.15, 0.90, *q],
        "neutral": [0.20, -0.12, 1.01, *q],
    }
    return [
        {"segment_id": f"A_{name}", "pose": pose}
        for name, pose in values.items()
    ]


def bind_candidate(candidate):
    result = copy.deepcopy(candidate)
    result["stage0_context_binding_v12"] = {
        "arm": "right",
        "scene_layout_sha256": hash_json(F4_LAYOUT),
        "layout_version": F4_LAYOUT["layout_version"],
        "release_target_semantics": "same_role_visible_slot_unchanged",
    }
    result["base_v11_candidate_application_sha256"] = result[
        "candidate_application_sha256"
    ]
    result["stage0_bound_candidate_sha256_v12"] = hash_json(result)
    return result


def refresh_candidate_hashes(candidate):
    value = copy.deepcopy(candidate)
    def target_hash(items):
        return hash_json(
            [
                {"segment_id": item["segment_id"], "pose": item["pose"]}
                for item in items
            ]
        )

    value["candidate_contract_target_pose_sha256"] = target_hash(
        value["candidate_contract_segments"]
    )
    value["applied_planner_target_pose_sha256"] = target_hash(
        value["applied_planner_targets"]
    )
    value["applied_candidate_subsequence_target_pose_sha256"] = target_hash(
        value["applied_planner_targets"][2:]
    )
    base_payload = {
        key: item
        for key, item in value.items()
        if key
        not in (
            "candidate_application_sha256",
            "base_v11_candidate_application_sha256",
            "stage0_context_binding_v12",
            "stage0_bound_candidate_sha256_v12",
        )
    }
    digest = hash_json(base_payload)
    value["candidate_application_sha256"] = digest
    value["base_v11_candidate_application_sha256"] = digest
    value.pop("stage0_bound_candidate_sha256_v12", None)
    value["stage0_bound_candidate_sha256_v12"] = hash_json(value)
    return value


def valid_infra_receipt(candidate, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    receipt_path = directory / "receipt.json"
    guard_path = directory / "guard.json"
    consumption_path = directory / "consumption.json"
    binding = {
        "authorization_receipt_sha256": "r" * 64,
        "physical_gpu_index": 0,
        "expected_gpu_uuid": "GPU-test",
    }
    consumption = {
        "authorization_receipt_sha256": "r" * 64,
        "approved_scope": "F4_candidate_hash_infra_v12",
        "family": "F4",
    }
    consumption["consumption_receipt_sha256"] = hash_json(consumption)
    consumption_path.write_text(json.dumps(consumption), encoding="utf-8")
    value = {
        "schema_version": "cmf_stage0_smoke_guarded_scope_receipt_v1",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        "scope": "F4_candidate_hash_infra_v12",
        "family": "F4",
        "hash_infrastructure_pass": True,
        "pipeline_integrity_pass": True,
        "status": "completed_f4_hash_infrastructure",
        "hash_infrastructure_audit_v12": {
            "pass": True,
            "checks": {"at_least_one_candidate_reached_planner": True},
        },
        "budget_counts": {
            "planner_query_count": 1,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        },
        "scene_cleanup_succeeded": True,
        "orphan_process_count": 0,
        "selected_corridor_candidate_v11": bind_candidate(candidate),
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
    value["gpu_guard_binding"] = binding
    value["gpu_postcheck"] = {"compute_processes": []}
    value["gpu_postcheck_release"] = {"verified": True}
    value["guard_receipt"] = str(guard_path)
    value["guard_sealed_receipt_sha256"] = hash_json(value)
    receipt_path.write_text(json.dumps(value), encoding="utf-8")
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
    guard_path.write_text(json.dumps(guard), encoding="utf-8")
    return receipt_path


def build_test_manifest(candidate):
    with tempfile.TemporaryDirectory(
        dir="/nfs_share/lijunhui/Robotwin2/tmp"
    ) as directory:
        return build_stage0_smoke_manifest(
            valid_infra_receipt(candidate, directory),
            require_canonical_path=False,
        )


def rewrite_infra_and_guard(receipt_path, mutate):
    receipt_path = Path(receipt_path)
    infra = json.loads(receipt_path.read_text())
    infra.pop("guard_sealed_receipt_sha256")
    mutate(infra)
    infra["guard_sealed_receipt_sha256"] = hash_json(infra)
    receipt_path.write_text(json.dumps(infra))
    guard_path = Path(infra["guard_receipt"])
    guard = json.loads(guard_path.read_text())
    guard.pop("guard_receipt_sha256")
    guard["child_receipt_file"]["sha256"] = __import__("hashlib").sha256(
        receipt_path.read_bytes()
    ).hexdigest()
    guard["guard_receipt_sha256"] = hash_json(guard)
    guard_path.write_text(json.dumps(guard))


def fake_family_receipt(manifest, family, outcomes):
    attempts = []
    planned = [item for item in manifest["attempts"] if item["family"] == family]
    for item, outcome in zip(planned, outcomes):
        attempt = {
                "attempt_id": item["attempt_id"],
                "family": family,
                "root_slot_id": item["root_slot_id"],
                "program_id": item["program_id"],
                "realization": "r_pc",
                "terminal_status": outcome,
                "trajectory_generated": outcome == "PASS",
                "verifier_pass": outcome == "PASS",
                "raw_integrity": {"pass": outcome == "PASS"},
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
            }
        attempt["receipt_sha256"] = hash_json(attempt)
        attempts.append(attempt)
    receipt = {
        "family": family,
        "root_slot_id": manifest["root_specs"][family]["slot_id"],
        "outcome": "PASS"
        if all(value == "PASS" for value in outcomes)
        else "FAILED_WITH_EVIDENCE",
        "attempt_receipts": attempts,
        "pipeline_integrity_pass": True,
        "cleanup_pass": True,
        "orphan_process_count": 0,
    }
    receipt["receipt_sha256"] = hash_json(receipt)
    return receipt


class Stage0SmokeV1Test(unittest.TestCase):
    def test_f4_raw_hash_noise_is_tolerated_but_structure_is_exact(self):
        contract = build_f4_exact_A_corridors_v11(base_a_targets())
        frozen = bind_candidate(contract["candidates"][0])
        reconstructed = copy.deepcopy(frozen)
        reconstructed["applied_planner_targets"][0]["pose"][0] += 5e-7
        reconstructed = refresh_candidate_hashes(reconstructed)
        result = audit_f4_candidate_equivalence_v12(frozen, reconstructed)
        self.assertTrue(result["pass"])
        self.assertFalse(result["raw_candidate_hash_equal_diagnostic"])
        self.assertLess(result["maximum_position_error_m"], POSITION_ATOL_M)
        changed = copy.deepcopy(reconstructed)
        changed["applied_planner_segment_ids"][0] = "A_wrong"
        self.assertFalse(
            audit_f4_candidate_equivalence_v12(frozen, changed)["pass"]
        )
        changed_target = copy.deepcopy(reconstructed)
        changed_target["applied_planner_targets"][0]["segment_id"] = "A_wrong"
        self.assertFalse(
            audit_f4_candidate_equivalence_v12(
                frozen, changed_target
            )["pass"]
        )
        changed_contract = copy.deepcopy(reconstructed)
        changed_contract["candidate_contract_segments"][0][
            "segment_id"
        ] = "A_wrong_contract"
        self.assertFalse(
            audit_f4_candidate_equivalence_v12(
                frozen, changed_contract
            )["pass"]
        )
        changed_layout = copy.deepcopy(reconstructed)
        changed_layout["stage0_context_binding_v12"][
            "scene_layout_sha256"
        ] = "different"
        self.assertFalse(
            audit_f4_candidate_equivalence_v12(
                frozen, changed_layout
            )["pass"]
        )
        far = copy.deepcopy(reconstructed)
        far["applied_planner_targets"][0]["pose"][0] += 2e-5
        self.assertFalse(
            audit_f4_candidate_equivalence_v12(frozen, far)["pass"]
        )

    def test_stage0_manifest_has_exactly_four_by_three_attempts(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        manifest = build_test_manifest(candidate)
        self.assertEqual(manifest["planned_family_root_count"], 4)
        self.assertEqual(manifest["planned_attempt_count"], 12)
        self.assertEqual(len(manifest["attempts"]), 12)
        self.assertTrue(manifest["stage0_authorized"])
        self.assertFalse(manifest["formal_data"])
        self.assertFalse(manifest["success_required_for_stage_completion"])
        for family in ("F1", "F2", "F3", "F4"):
            self.assertEqual(
                sum(item["family"] == family for item in manifest["attempts"]),
                3,
            )
        self.assertEqual(
            manifest["root_specs"]["F4"]["scene_layout"], F4_LAYOUT
        )

    def test_stage0_manifest_can_preserve_f4_physical_blocker(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            infra_path = valid_infra_receipt(candidate, directory)
            rewrite_infra_and_guard(
                infra_path,
                lambda value: value.update(
                    {"selected_corridor_candidate_v11": None}
                ),
            )
            manifest = build_stage0_smoke_manifest(
                infra_path, require_canonical_path=False
            )
        blocker = manifest["root_specs"]["F4"]["f4_shared_preflight_blocker"]
        self.assertEqual(blocker["failure_type"], "f4_no_planner_solvable_corridor")

    def test_manifest_rejects_fake_infra_without_real_query(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as directory:
            infra_path = valid_infra_receipt(candidate, directory)
            rewrite_infra_and_guard(
                infra_path,
                lambda value: value["budget_counts"].update(
                    {"planner_query_count": 0}
                ),
            )
            with self.assertRaisesRegex(ValueError, "infrastructure receipt"):
                build_stage0_smoke_manifest(
                    infra_path, require_canonical_path=False
                )

    def test_scope_spec_rejects_stale_manifest_hash_and_binds_f4_layout(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        manifest = build_test_manifest(candidate)
        self.assertEqual(
            planned_scope_spec("F4_candidate_hash_infra_v12")["scene_layout"],
            F4_LAYOUT,
        )
        tampered = copy.deepcopy(manifest)
        tampered["planned_attempt_count"] = 1
        with self.assertRaisesRegex(ValueError, "manifest structure"):
            planned_scope_spec("Stage0_F1_root_A", stage0_manifest=tampered)

    def test_stage0_finalizer_completes_with_failed_evidence(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        manifest = build_test_manifest(candidate)
        receipts = {
            "F1": fake_family_receipt(manifest, "F1", ["PASS", "PASS", "PASS"]),
            "F2": fake_family_receipt(
                manifest, "F2", ["FAILED_WITH_EVIDENCE", "PASS", "PASS"]
            ),
            "F3": fake_family_receipt(
                manifest, "F3", ["FAILED_WITH_EVIDENCE"] * 3
            ),
            "F4": fake_family_receipt(
                manifest, "F4", ["FAILED_WITH_EVIDENCE"] * 3
            ),
        }
        outer_audits = {
            family: {"pass": True} for family in ("F1", "F2", "F3", "F4")
        }
        result = _finalize_stage0_smoke_payloads(
            manifest, receipts, outer_audits
        )
        self.assertTrue(result["stage0_completed"])
        self.assertEqual(result["stage0_outcome"], "FAILED_WITH_EVIDENCE")
        self.assertEqual(result["terminal_attempt_count"], 12)
        self.assertEqual(result["successful_attempt_count"], 5)
        self.assertEqual(result["failed_attempt_count"], 7)
        self.assertEqual(result["accepted_formal_root_count"], 0)

    def test_finalizer_rejects_declared_pass_without_real_trajectories(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        manifest = build_test_manifest(candidate)
        receipts = {
            family: fake_family_receipt(
                manifest, family, ["FAILED_WITH_EVIDENCE"] * 3
            )
            for family in ("F1", "F2", "F3", "F4")
        }
        receipts["F1"]["outcome"] = "PASS"
        payload = dict(receipts["F1"])
        payload.pop("receipt_sha256")
        receipts["F1"]["receipt_sha256"] = hash_json(payload)
        result = _finalize_stage0_smoke_payloads(
            manifest,
            receipts,
            {family: {"pass": True} for family in receipts},
        )
        self.assertFalse(result["stage0_completed"])
        self.assertEqual(result["stage0_outcome"], "FAILED_WITH_EVIDENCE")

    def test_finalizer_requires_guarded_outer_receipts(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        manifest = build_test_manifest(candidate)
        receipts = {
            family: fake_family_receipt(
                manifest, family, ["FAILED_WITH_EVIDENCE"] * 3
            )
            for family in ("F1", "F2", "F3", "F4")
        }
        audits = {family: {"pass": True} for family in receipts}
        audits["F4"] = {"pass": False}
        result = _finalize_stage0_smoke_payloads(manifest, receipts, audits)
        self.assertFalse(result["stage0_completed"])

    def test_shared_prefix_failure_still_emits_three_terminal_attempts(self):
        class Adapter:
            family = "F1"

        root = {
            "status": "failed_prefix_replay_gate",
            "error_type": "PrefixGateFailure",
            "error": "shared prefix failed",
            "branch_receipts": [],
            "suffix_planner_receipts": [
                {
                    "failure_stage": "prefix_replay_gate",
                    "prefix_replay_failure": {
                        "status": "failed_prefix_replay_gate",
                        "prefix_end_equivalent": True,
                        "replayed_prefix_physical_acceptance": {"pass": False},
                    },
                }
            ],
            "cleanup_records": [
                {"cleanup_safety_pass": True, "orphan_process_count": 0}
            ],
            "budget_counts": {
                "planner_query_count": 1,
                "execution_attempt_count": 0,
                "recovery_attempt_count": 0,
            },
        }
        planned = planned_stage0_root_spec("F1")
        with tempfile.TemporaryDirectory() as directory, patch.object(
            RealSapienStrictPrefixRootOrchestratorV1_2,
            "run_nonformal_root",
            return_value=root,
        ) as call:
            receipt = Stage0SmokeFamilyRunnerV1(Adapter()).run(
                output_dir=Path(directory) / "F1",
                planned_root_slot_spec=planned,
            )
            self.assertEqual(receipt["stage0_attempt_count"], 3)
            self.assertEqual(receipt["failed_attempt_count"], 3)
            self.assertEqual(receipt["outcome"], "FAILED_WITH_EVIDENCE")
            self.assertTrue(receipt["pipeline_integrity_pass"])
            self.assertTrue(
                all(
                    item["terminal_status"] == "FAILED_WITH_EVIDENCE"
                    for item in receipt["attempt_receipts"]
                )
            )
            self.assertTrue(call.call_args.kwargs["stage0_data"])
            self.assertTrue(call.call_args.kwargs["stage0_authorized"])

    def test_branch_acceptance_cannot_override_failed_root(self):
        branch = {"status": "accepted", "verifier": {"pass": True}}
        self.assertEqual(
            _attempt_status(
                branch, "failed_verifier", raw_integrity_pass=True
            ),
            "FAILED_WITH_EVIDENCE",
        )

    def test_missing_raw_from_accepted_branches_breaks_pipeline_integrity(self):
        class Adapter:
            family = "F1"

        programs = F1ObjectSelection().checked_provisional_programs()
        root = {
            "status": "accepted",
            "root_finalization": {"accepted": True},
            "branch_receipts": [
                {
                    "program_id": program["program_id"],
                    "status": "accepted",
                    "verifier": {"pass": True},
                    "suffix_execution_planner_query_delta": 0,
                }
                for program in programs
            ],
            "cleanup_records": [
                {"cleanup_safety_pass": True, "orphan_process_count": 0}
            ],
            "budget_counts": {
                "planner_query_count": 1,
                "execution_attempt_count": 3,
                "recovery_attempt_count": 0,
            },
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(
            RealSapienStrictPrefixRootOrchestratorV1_2,
            "run_nonformal_root",
            return_value=root,
        ):
            receipt = Stage0SmokeFamilyRunnerV1(Adapter()).run(
                output_dir=Path(directory) / "F1",
                planned_root_slot_spec=planned_stage0_root_spec("F1"),
            )
        self.assertFalse(receipt["pipeline_integrity_pass"])
        self.assertFalse(receipt["all_required_branch_raw_complete"])

    def test_prefix_replay_state_mismatch_is_infrastructure_failure(self):
        audit = _audit_root_terminal_evidence(
            {
                "status": "failed_prefix_replay_gate",
                "suffix_planner_receipts": [
                    {
                        "failure_stage": "prefix_replay_gate",
                        "prefix_replay_failure": {
                            "prefix_end_equivalent": False,
                            "replayed_prefix_physical_acceptance": None,
                        },
                    }
                ],
            }
        )
        self.assertFalse(audit["pass"])

    def test_task_audit_exception_is_not_scientific_infeasibility(self):
        audit = _audit_root_terminal_evidence(
            {
                "status": "failed_task_physical_feasibility",
                "task_physical_feasibility_receipts": [
                    {
                        "status": "failed",
                        "evidence": {"error": "same current mismatch"},
                        "failure_stage": "task_same_current_infrastructure",
                        "task_infrastructure_failure": True,
                    },
                    {"status": "passed", "evidence": {}},
                    {"status": "passed", "evidence": {}},
                ],
            }
        )
        self.assertFalse(audit["pass"])
        with self.assertRaises(F2FrozenLayoutConfigurationError):
            F2ControllerV3_3().audit_task_physical_feasibility(
                SimpleNamespace(_cmf_planned_root_slot_spec={}),
                {"program_id": "F2-inside"},
            )

    def test_raw_writer_marks_authorized_stage0_without_formal_promotion(self):
        adapter = SyntheticAdapter()
        program = F1ObjectSelection().checked_provisional_programs()[0]
        rollout = adapter.rollout(None, program, {"realization": "r_pc"})
        rollout["provenance"].update(
            {
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_raw_attempt(
                Path(directory) / "raw",
                rollout["streams"],
                rollout["audit_streams"],
                rollout["provenance"],
            )
            self.assertTrue(manifest["stage0_data"])
            self.assertTrue(manifest["stage0_authorized"])
            self.assertFalse(manifest["formal_data"])
            self.assertTrue(validate_raw_artifact_contract(Path(directory) / "raw")["pass"])
        rollout["provenance"]["stage0_authorized"] = False
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "matching Stage 0"):
                write_raw_attempt(
                    Path(directory) / "raw",
                    rollout["streams"],
                    rollout["audit_streams"],
                    rollout["provenance"],
                )

    def test_budget_gpu_and_guard_contracts_are_parallel_but_bounded(self):
        artifact = budget_artifact()
        self.assertEqual(ALLOWED_PHYSICAL_GPU_INDICES, tuple(range(8)))
        self.assertTrue(artifact["family_level_parallelism_authorized"])
        self.assertEqual(artifact["stage0_planned_attempt_count"], 12)
        self.assertEqual(set(STAGE0_SCOPES), {
            "Stage0_F1_root_A", "Stage0_F2_root_A",
            "Stage0_F3_root_A", "Stage0_F4_root_A",
        })
        self.assertFalse(artifact["automatic_retry"])
        guard_source = inspect.getsource(gpu_guard_v2_4)
        self.assertIn("controlled_multi_future_stage0_smoke_v1", guard_source)

    def test_parallel_scheduler_assigns_four_unique_idle_gpus(self):
        bundles = {
            scope: {
                "family": scope.split("_")[1],
                "physical_gpu_indices": list(range(8)),
                "authorization_path": f"/{scope}.json",
                "guard_path": f"/{scope}.guard.json",
                "output_namespace": f"/{scope}",
                "timeout_seconds": 10,
                "child_command": ["python", scope],
            }
            for scope in STAGE0_SCOPES
        }
        snapshots = [
            {
                "physical_index": index,
                "uuid": f"GPU-{index}",
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
        self.assertEqual(
            len({item["physical_gpu_index"] for item in schedule["assignments"]}),
            4,
        )
        stale = copy.deepcopy(snapshots)
        stale[0]["captured_at"] = "2020-01-01T00:00:00+00:00"
        rejected = assign_stage0_scopes_to_idle_gpus(
            {"bundles": bundles}, stale[:3]
        )
        self.assertFalse(rejected["pass"])
        self.assertEqual(rejected["assignments"], [])

    def test_guard_rejects_unsealed_stage0_child_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "receipt.json").write_text(
                json.dumps(
                    {
                        "schema_version": "cmf_stage0_smoke_guarded_scope_receipt_v1",
                        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
                    }
                )
            )
            with self.assertRaises(Exception):
                update_child_receipt_v2_1(
                    output,
                    output / "guard.json",
                    {},
                    {},
                    [],
                    {"verified": True},
                )

    def test_source_bindings_and_root_api_cover_stage0(self):
        bindings = current_stage0_source_bindings()
        for key in (
            "real_adapter_sha256",
            "f4_candidate_equivalence_sha256",
            "f4_corridor_selection_sha256",
            "stage0_family_runner_sha256",
            "stage0_manifest_sha256",
            "stage0_finalizer_sha256",
            "stage0_finalizer_entrypoint_sha256",
            "scope_runner_sha256",
            "gpu_guard_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64)
        source = inspect.getsource(
            RealSapienStrictPrefixRootOrchestratorV1_2.run_nonformal_root
        )
        self.assertIn("stage0_data: bool = False", source)
        self.assertIn("stage0_authorized: bool = False", source)


if __name__ == "__main__":
    unittest.main()
