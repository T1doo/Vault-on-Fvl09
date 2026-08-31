import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f4_frozen_canonical_neutral_binding_v13 import (
    build_f4_frozen_canonical_neutral_binding_v13,
)
from controlled_multi_future.families import F1ObjectSelection
from controlled_multi_future.root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
)
from controlled_multi_future.stage0_smoke_family_runner_v1_1 import (
    TERMINAL_OUTCOMES,
    Stage0SmokeFamilyRunnerV1_1,
    classify_stage0_attempt_outcome_v1_1,
)
from controlled_multi_future.stage0_smoke_finalizer_v1_1 import (
    _finalize_stage0_smoke_payloads_v1_1,
)
from controlled_multi_future.stage0_smoke_manifest_v1_1 import (
    CANONICAL_OUTPUT,
    build_stage0_smoke_manifest_v1_1,
    planned_stage0_root_spec_v1_1,
    validate_stage0_smoke_manifest_structure,
)


def binding():
    return build_f4_frozen_canonical_neutral_binding_v13(
        canonical_terminal_neutral_pose=[
            0.24,
            -0.02,
            0.98,
            1.0,
            0.0,
            0.0,
            0.0,
        ],
        canonical_prefix_id="f4_common_x_tray_withdraw_high_neutral_v5",
        canonical_prefix_contract_sha256="1" * 64,
        canonical_prefix_action_sha256="2" * 64,
        semantic_prefix_end_anchor_sha256="3" * 64,
        acceptance_prefix_end_anchor_sha256="4" * 64,
        prefix_end_tolerance_version="physical_anchor_v2",
    )


def selected_candidate(value):
    pose = list(value["canonical_terminal_neutral_pose"])
    return {
        "candidate_id": "candidate-one",
        "candidate_contract_segments": [{"segment_id": "A_neutral", "pose": pose}],
        "applied_planner_targets": [{"segment_id": "A_neutral", "pose": pose}],
    }


def manifest():
    bound = binding()
    selected = selected_candidate(bound)
    roots = {
        family: planned_stage0_root_spec_v1_1(
            family,
            selected_f4_candidate_v13=selected if family == "F4" else None,
            f4_canonical_neutral_binding_v13=bound if family == "F4" else None,
        )
        for family in ("F1", "F2", "F3", "F4")
    }
    attempts = [
        {
            "attempt_id": attempt_id,
            "family": family,
            "root_slot_id": spec["slot_id"],
            "program_id": program_id,
            "realization": "r_pc",
            "formal_data": False,
            "stage0_data": True,
            "mp4_required_if_trajectory_generated": True,
        }
        for family, spec in roots.items()
        for attempt_id, program_id in zip(spec["stage0_attempt_ids"], spec["program_ids"])
    ]
    value = {
        "implementation_version": "controlled_multi_future_stage0_smoke_v1_1",
        "root_specs": roots,
        "attempts": attempts,
        "f4_canonical_neutral_binding_v13": bound,
        "f4_canonical_neutral_binding_sha256_v13": bound["binding_sha256"],
        "stage0_data": True,
        "stage0_authorized": True,
        "stage0_generated_trajectory_mp4_required": True,
        "stage0_video_contract": {
            "format": "mp4",
            "camera": "head_camera",
            "video_fps": 25,
            "control_frequency_hz": 250,
            "sample_stride_steps": 10,
            "initial_and_final_frames_required": True,
            "no_trajectory_status": "video_not_applicable_no_trajectory",
        },
        "formal_data": False,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    value["manifest_sha256"] = hash_json(value)
    return value


def fake_v13_infrastructure_tree(root: Path):
    bound = binding()
    selected = selected_candidate(bound)
    consumption = {
        "schema_version": "cmf_stage0_smoke_authorization_consumption_v1_1",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1_1",
        "authorization_id": "fake-v13",
        "authorization_receipt_sha256": "a" * 64,
        "approved_scope": "F4_candidate_hash_infra_v13",
        "family": "F4",
        "scene_seed": 20260829,
        "max_invocations": 1,
    }
    consumption["consumption_receipt_sha256"] = hash_json(consumption)
    consumption_path = root / "consumption.json"
    consumption_path.write_text(json.dumps(consumption), encoding="utf-8")
    shared_guard_binding = {
        "authorization_receipt_sha256": "a" * 64,
        "physical_gpu_index": 2,
        "expected_gpu_uuid": "GPU-test",
    }
    guard_path = root / "guard.json"
    outer = {
        "schema_version": "cmf_stage0_smoke_guarded_scope_receipt_v1_1",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1_1",
        "scope": "F4_candidate_hash_infra_v13",
        "family": "F4",
        "status": "completed_f4_hash_infrastructure_v13",
        "pipeline_integrity_pass": True,
        "hash_infrastructure_pass": True,
        "hash_infrastructure_audit_v13": {
            "checks": {"at_least_one_candidate_reached_real_planner": True},
            "pass": True,
        },
        "candidate_corridor_planner_query_count": 1,
        "budget_counts": {
            "planner_query_count": 11,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        },
        "scene_cleanup_succeeded": True,
        "orphan_process_count": 0,
        "stage0_data": False,
        "formal_data": False,
        "authorization": {
            "receipt_sha256": "a" * 64,
            "implementation_source_sha256": "b" * 64,
        },
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "guard_receipt": str(guard_path),
        "guard_binding": shared_guard_binding,
        "gpu_guard_binding": shared_guard_binding,
        "gpu_postcheck_release": {"verified": True},
        "canonical_neutral_binding_v13": bound,
        "selected_corridor_candidate_v13": selected,
    }
    outer["guard_sealed_receipt_sha256"] = hash_json(outer)
    outer_path = root / "receipt.json"
    outer_path.write_text(json.dumps(outer), encoding="utf-8")
    outer_file_sha = hashlib.sha256(outer_path.read_bytes()).hexdigest()
    guard = {
        "status": "completed",
        "post_source_lock_pass": True,
        "timed_out": False,
        "orphan_process_count": 0,
        "postcheck_release": {"verified": True},
        "child_receipt_file": {"sha256": outer_file_sha},
        "binding": shared_guard_binding,
        "consumption_receipt": str(consumption_path),
    }
    guard["guard_receipt_sha256"] = hash_json(guard)
    guard_path.write_text(json.dumps(guard), encoding="utf-8")
    return outer_path


class Stage0SmokeV11Test(unittest.TestCase):
    def test_manifest_builder_requires_v13_real_candidate_query_and_guard_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            outer_path = fake_v13_infrastructure_tree(Path(directory))
            value = build_stage0_smoke_manifest_v1_1(
                outer_path, require_canonical_path=False
            )
            self.assertEqual(value["planned_attempt_count"], 12)
            self.assertEqual(value["f4_candidate_corridor_planner_query_count"], 1)
            broken = json.loads(outer_path.read_text(encoding="utf-8"))
            broken["hash_infrastructure_audit_v13"]["checks"] = {
                "at_least_one_candidate_reached_planner": True
            }
            broken.pop("guard_sealed_receipt_sha256")
            broken["guard_sealed_receipt_sha256"] = hash_json(broken)
            outer_path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "infrastructure receipt failed"):
                build_stage0_smoke_manifest_v1_1(
                    outer_path, require_canonical_path=False
                )

    def test_manifest_exact_four_by_three_and_no_stage1(self):
        value = manifest()
        audit = validate_stage0_smoke_manifest_structure(value)
        self.assertTrue(audit["pass"], audit)
        self.assertEqual(len(value["attempts"]), 12)
        self.assertTrue(all(item["realization"] == "r_pc" for item in value["attempts"]))
        self.assertFalse(value["stage1_authorized"])
        self.assertEqual(CANONICAL_OUTPUT.name, "STAGE0_SMOKE_ATTEMPT_MANIFEST_V1.json")

    def test_selected_candidate_neutral_must_match_binding_without_payload_rewrite(self):
        bound = binding()
        candidate = selected_candidate(bound)
        original = copy.deepcopy(candidate)
        spec = planned_stage0_root_spec_v1_1(
            "F4",
            selected_f4_candidate_v13=candidate,
            f4_canonical_neutral_binding_v13=bound,
        )
        self.assertEqual(candidate, original)
        self.assertEqual(spec["selected_f4_corridor_candidate_v13"], original)
        changed = copy.deepcopy(candidate)
        changed["candidate_contract_segments"][-1]["pose"][0] += 0.01
        changed["applied_planner_targets"][-1]["pose"][0] += 0.01
        with self.assertRaisesRegex(ValueError, "neutral target hash"):
            planned_stage0_root_spec_v1_1(
                "F4",
                selected_f4_candidate_v13=changed,
                f4_canonical_neutral_binding_v13=bound,
            )

    def test_attempt_terminal_mapping_is_deterministic(self):
        accepted = {"status": "accepted", "verifier": {"pass": True}}
        self.assertEqual(
            classify_stage0_attempt_outcome_v1_1(
                accepted,
                {"status": "accepted"},
                raw_integrity_pass=True,
                branch_receipt_present=True,
            ),
            "PASSED",
        )
        self.assertEqual(
            classify_stage0_attempt_outcome_v1_1(
                {"status": "failed_verifier"},
                {"status": "failed_verifier"},
                raw_integrity_pass=True,
                branch_receipt_present=True,
            ),
            "FAILED_VERIFIER_WITH_EVIDENCE",
        )
        self.assertEqual(
            classify_stage0_attempt_outcome_v1_1(
                {"status": "failed_execution"},
                {"status": "failed_verifier"},
                raw_integrity_pass=False,
                branch_receipt_present=True,
            ),
            "FAILED_EXECUTION_WITH_EVIDENCE",
        )
        self.assertEqual(
            classify_stage0_attempt_outcome_v1_1(
                None,
                {"status": "failed_planner"},
                raw_integrity_pass=False,
                branch_receipt_present=False,
            ),
            "FAILED_PLANNER_WITH_EVIDENCE",
        )
        self.assertEqual(
            classify_stage0_attempt_outcome_v1_1(
                None,
                {"status": "failed_task_physical_feasibility"},
                raw_integrity_pass=False,
                branch_receipt_present=False,
            ),
            "FAILED_EXECUTION_WITH_EVIDENCE",
        )
        self.assertEqual(
            classify_stage0_attempt_outcome_v1_1(
                accepted,
                {"status": "failed_cleanup_uncertain"},
                raw_integrity_pass=True,
                branch_receipt_present=True,
            ),
            "FAILED_INFRASTRUCTURE_WITH_EVIDENCE",
        )
        self.assertEqual(set(TERMINAL_OUTCOMES), {
            "PASSED",
            "FAILED_PLANNER_WITH_EVIDENCE",
            "FAILED_EXECUTION_WITH_EVIDENCE",
            "FAILED_VERIFIER_WITH_EVIDENCE",
            "FAILED_INFRASTRUCTURE_WITH_EVIDENCE",
        })

    def test_shared_physical_gate_still_emits_three_execution_failure_receipts(self):
        class Adapter:
            family = "F1"

        spec = planned_stage0_root_spec_v1_1("F1")
        spec["stage0_manifest_sha256"] = "a" * 64
        spec["stage0_manifest_attempt_count"] = 12
        root = {
            "status": "failed_prefix_replay_gate",
            "branch_receipts": [],
            "suffix_planner_receipts": [
                {
                    "failure_stage": "prefix_replay_gate",
                    "evidence": {
                        "prefix_replay_failure": {
                            "prefix_end_equivalent": True,
                            "replayed_prefix_physical_acceptance": {"pass": False},
                        }
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
        with tempfile.TemporaryDirectory() as directory, patch.object(
            RealSapienStrictPrefixRootOrchestratorV1_2,
            "run_nonformal_root",
            return_value=root,
        ):
            receipt = Stage0SmokeFamilyRunnerV1_1(Adapter()).run(
                output_dir=Path(directory) / "family",
                planned_root_slot_spec=spec,
            )
        self.assertEqual(len(receipt["attempt_receipts"]), 3)
        self.assertTrue(
            all(
                item["terminal_status"] == "FAILED_EXECUTION_WITH_EVIDENCE"
                for item in receipt["attempt_receipts"]
            )
        )

    def test_finalizer_retains_failed_outcomes_and_never_authorizes_stage1(self):
        value = manifest()
        receipts = {}
        for family in ("F1", "F2", "F3", "F4"):
            attempts = []
            for planned in [x for x in value["attempts"] if x["family"] == family]:
                item = {
                    **planned,
                    "implementation_version": "controlled_multi_future_stage0_smoke_v1_1",
                    "terminal_status": "FAILED_PLANNER_WITH_EVIDENCE",
                    "trajectory_generated": False,
                    "raw_required_by_branch_status": False,
                    "video_required": False,
                    "video_status": "video_not_applicable_no_trajectory",
                    "video_integrity": {
                        "required": False,
                        "applicable": False,
                        "status": "video_not_applicable_no_trajectory",
                        "pass": True,
                    },
                    "formal_data": False,
                    "stage0_data": True,
                    "mp4_required_if_trajectory_generated": True,
                    "stage1_authorized": False,
                }
                item["receipt_sha256"] = hash_json(item)
                attempts.append(item)
            receipt = {
                "implementation_version": "controlled_multi_future_stage0_smoke_v1_1",
                "family": family,
                "root_slot_id": value["root_specs"][family]["slot_id"],
                "attempt_receipts": attempts,
                "outcome": "FAILED_WITH_EVIDENCE",
                "pipeline_integrity_pass": True,
                "generated_trajectory_count": 0,
                "generated_video_count": 0,
                "all_required_videos_complete": True,
                "cleanup_pass": True,
                "orphan_process_count": 0,
                "stage1_authorized": False,
                "formal_collection_authorized": False,
                "training_authorized": False,
            }
            if family == "F4":
                receipt["f4_canonical_neutral_binding_v13"] = value[
                    "f4_canonical_neutral_binding_v13"
                ]
            receipt["receipt_sha256"] = hash_json(receipt)
            receipts[family] = receipt
        result = _finalize_stage0_smoke_payloads_v1_1(
            value, receipts, {family: {"pass": True} for family in receipts}
        )
        self.assertTrue(result["stage0_completed"])
        self.assertEqual(result["stage0_outcome"], "FAILED_WITH_EVIDENCE")
        self.assertEqual(result["failed_attempt_count"], 12)
        self.assertFalse(result["stage1_authorized"])
        self.assertFalse(result["formal_collection_authorized"])
        self.assertFalse(result["training_authorized"])


if __name__ == "__main__":
    unittest.main()
