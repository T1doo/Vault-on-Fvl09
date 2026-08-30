import copy
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter
from controlled_multi_future.probes.stage0_smoke_authorization_v1 import (
    current_stage0_source_bindings,
)
from controlled_multi_future.raw_writer import write_raw_attempt
from controlled_multi_future.root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
)
from controlled_multi_future.stage0_smoke_budget_v1 import (
    ALLOWED_PHYSICAL_GPU_INDICES,
    STAGE0_SCOPES,
    budget_artifact,
)
from controlled_multi_future.stage0_smoke_finalizer_v1 import (
    finalize_stage0_smoke_v1,
)
from controlled_multi_future.stage0_smoke_manifest_v1 import (
    build_stage0_smoke_manifest,
    planned_stage0_root_spec,
)
from controlled_multi_future.stage0_smoke_family_runner_v1 import (
    Stage0SmokeFamilyRunnerV1,
)


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


def fake_family_receipt(family, outcomes):
    attempts = []
    for index, outcome in enumerate(outcomes):
        attempts.append(
            {
                "attempt_id": f"stage0-{family}-rootA-{index + 1:02d}",
                "family": family,
                "terminal_status": outcome,
                "trajectory_generated": outcome == "PASS",
                "formal_data": False,
                "stage0_data": True,
                "stage0_authorized": True,
            }
        )
    return {
        "family": family,
        "outcome": "PASS"
        if all(value == "PASS" for value in outcomes)
        else "FAILED_WITH_EVIDENCE",
        "attempt_receipts": attempts,
        "pipeline_integrity_pass": True,
        "cleanup_pass": True,
        "orphan_process_count": 0,
    }


class Stage0SmokeV1Test(unittest.TestCase):
    def test_f4_raw_hash_noise_is_tolerated_but_structure_is_exact(self):
        contract = build_f4_exact_A_corridors_v11(base_a_targets())
        frozen = contract["candidates"][0]
        reconstructed = copy.deepcopy(frozen)
        reconstructed["candidate_application_sha256"] = "different-raw-hash"
        reconstructed["applied_planner_targets"][0]["pose"][0] += 5e-7
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
        far = copy.deepcopy(reconstructed)
        far["applied_planner_targets"][0]["pose"][0] += 2e-5
        self.assertFalse(
            audit_f4_candidate_equivalence_v12(frozen, far)["pass"]
        )

    def test_stage0_manifest_has_exactly_four_by_three_attempts(self):
        candidate = build_f4_exact_A_corridors_v11(base_a_targets())[
            "candidates"
        ][0]
        infra = {
            "hash_infrastructure_pass": True,
            "selected_corridor_candidate_v11": candidate,
            "receipt_sha256": "a" * 64,
        }
        manifest = build_stage0_smoke_manifest(infra)
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

    def test_stage0_manifest_can_preserve_f4_physical_blocker(self):
        manifest = build_stage0_smoke_manifest(
            {
                "hash_infrastructure_pass": True,
                "selected_corridor_candidate_v11": None,
                "receipt_sha256": "b" * 64,
            }
        )
        blocker = manifest["root_specs"]["F4"]["f4_shared_preflight_blocker"]
        self.assertEqual(blocker["failure_type"], "f4_no_planner_solvable_corridor")

    def test_stage0_finalizer_completes_with_failed_evidence(self):
        receipts = {
            "F1": fake_family_receipt("F1", ["PASS", "PASS", "PASS"]),
            "F2": fake_family_receipt(
                "F2", ["FAILED_WITH_EVIDENCE", "PASS", "PASS"]
            ),
            "F3": fake_family_receipt(
                "F3", ["FAILED_WITH_EVIDENCE"] * 3
            ),
            "F4": fake_family_receipt(
                "F4", ["FAILED_WITH_EVIDENCE"] * 3
            ),
        }
        result = finalize_stage0_smoke_v1(receipts)
        self.assertTrue(result["stage0_completed"])
        self.assertEqual(result["stage0_outcome"], "FAILED_WITH_EVIDENCE")
        self.assertEqual(result["terminal_attempt_count"], 12)
        self.assertEqual(result["successful_attempt_count"], 5)
        self.assertEqual(result["failed_attempt_count"], 7)
        self.assertEqual(result["accepted_formal_root_count"], 0)

    def test_shared_prefix_failure_still_emits_three_terminal_attempts(self):
        class Adapter:
            family = "F1"

        root = {
            "status": "failed_execution",
            "error_type": "PrefixGateFailure",
            "error": "shared prefix failed",
            "branch_receipts": [],
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

    def test_source_bindings_and_root_api_cover_stage0(self):
        bindings = current_stage0_source_bindings()
        for key in (
            "real_adapter_sha256",
            "f4_candidate_equivalence_sha256",
            "f4_corridor_selection_sha256",
            "stage0_family_runner_sha256",
            "stage0_manifest_sha256",
            "stage0_finalizer_sha256",
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
