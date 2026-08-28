import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import json

from controlled_multi_future.f3_conditional_repair_orchestrator_v1_1 import F3ConditionalRepairOrchestratorV1_1


class Adapter:
    family = "F3"


def diagnosis_receipt(*, correction_allowed):
    diagnosis = {
        "classification": "pre_release_systematic_offset" if correction_allowed else "grasp_slip_or_contact_change",
        "actor_to_eef_correction_allowed": correction_allowed,
        "grasp_transform_stable": correction_allowed,
        "eef_tracking_ok": True,
        "next_gate": "one_deterministic_actor_to_eef_correction" if correction_allowed else "grasp_slip_or_contact_impact_review",
    }
    return {
        "status": "failed_verifier",
        "repair_probe_pass": False,
        "reference_current_sha256": "same-current",
        "cleanup_records": [{"scene_created": True, "cleanup_safety_pass": True, "orphan_process_count": 0}],
        "semantic_verifier": {
            "diagnosis": diagnosis,
            "samples": {
                "before_release": {
                    "sample_step": 10,
                    "eef_pose": [0, 0, 0, 1, 0, 0, 0],
                    "bottle_pose": [0.04, 0, 0, 1, 0, 0, 0],
                    "target_bottle_pose": [0, 0, 0, 1, 0, 0, 0],
                    "commanded_release_eef_pose": [0, 0, 0, 1, 0, 0, 0],
                }
            },
        },
    }


class F3ConditionalRepairOrchestratorV1_1Test(unittest.TestCase):
    def test_eligible_diagnosis_unlocks_exactly_one_correction(self):
        correction = {
            "status": "passed_nonformal_repair_probe_full_program_incomplete",
            "repair_probe_pass": True,
            "reference_current_sha256": "same-current",
            "cleanup_records": [{"scene_created": True, "cleanup_safety_pass": True, "orphan_process_count": 0}],
        }
        responses = [diagnosis_receipt(correction_allowed=True), correction]

        def fake_run(*args, **kwargs):
            output = kwargs["output_dir"]
            output.mkdir(parents=True, exist_ok=False)
            anchor = {
                "schema_version": "physical_anchor_v1_legacy",
                "robot_qpos": [0, 0],
                "robot_qvel": [0, 0],
                "actor_poses": {"bottle": [0, 0, 0, 1, 0, 0, 0]},
                "gripper_state": [1, 1],
                "metadata": {"seed": 1},
                "anchor_sha256": "same-anchor",
            }
            (output / "reference_anchor.json").write_text(json.dumps(anchor), encoding="utf-8")
            return responses.pop(0)

        with tempfile.TemporaryDirectory() as directory, patch(
            "controlled_multi_future.f3_conditional_repair_orchestrator_v1_1.FamilyRepairOrchestratorV1_1.run",
            side_effect=fake_run,
        ) as run:
            receipt = F3ConditionalRepairOrchestratorV1_1(Adapter()).run(
                output_dir=Path(directory) / "f3",
                planned_root_slot_spec={"slot_id": "f3", "family": "F3"},
                program={"program_id": "F3-VHVH"},
            )
            self.assertEqual(run.call_count, 2)
            self.assertEqual(receipt["diagnostic_execution_count"], 1)
            self.assertEqual(receipt["correction_execution_count"], 1)
            self.assertTrue(receipt["repair_probe_pass"])
            self.assertTrue(receipt["diagnosis_correction_same_current"])
            self.assertTrue(receipt["diagnosis_correction_anchor_equivalence"]["equivalent"])
            self.assertTrue((Path(directory) / "f3" / "correction_spec.json").is_file())
            second = run.call_args_list[1].kwargs
            self.assertEqual(second["repair_mode"], "deterministic_correction")
            self.assertEqual(second["correction_spec"]["maximum_correction_attempt_count"], 1)

    def test_grasp_slip_does_not_unlock_correction(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "controlled_multi_future.f3_conditional_repair_orchestrator_v1_1.FamilyRepairOrchestratorV1_1.run",
            return_value=diagnosis_receipt(correction_allowed=False),
        ) as run:
            receipt = F3ConditionalRepairOrchestratorV1_1(Adapter()).run(
                output_dir=Path(directory) / "f3",
                planned_root_slot_spec={"slot_id": "f3", "family": "F3"},
                program={"program_id": "F3-VHVH"},
            )
            self.assertEqual(run.call_count, 1)
            self.assertEqual(receipt["correction_execution_count"], 0)
            self.assertEqual(receipt["next_gate"], "grasp_slip_or_contact_impact_review")

    def test_correction_current_mismatch_fails(self):
        responses = [
            diagnosis_receipt(correction_allowed=True),
            {
                "status": "passed_nonformal_repair_probe_full_program_incomplete",
                "repair_probe_pass": True,
                "reference_current_sha256": "different-current",
                "cleanup_records": [{"scene_created": True, "cleanup_safety_pass": True, "orphan_process_count": 0}],
            },
        ]

        def fake_run(*args, **kwargs):
            output = kwargs["output_dir"]
            output.mkdir(parents=True, exist_ok=False)
            anchor = {
                "schema_version": "physical_anchor_v1_legacy",
                "robot_qpos": [0, 0], "robot_qvel": [0, 0],
                "actor_poses": {"bottle": [0, 0, 0, 1, 0, 0, 0]},
                "gripper_state": [1, 1], "metadata": {"seed": 1}, "anchor_sha256": "same-anchor",
            }
            (output / "reference_anchor.json").write_text(json.dumps(anchor), encoding="utf-8")
            return responses.pop(0)

        with tempfile.TemporaryDirectory() as directory, patch(
            "controlled_multi_future.f3_conditional_repair_orchestrator_v1_1.FamilyRepairOrchestratorV1_1.run",
            side_effect=fake_run,
        ):
            receipt = F3ConditionalRepairOrchestratorV1_1(Adapter()).run(
                output_dir=Path(directory) / "f3",
                planned_root_slot_spec={"slot_id": "f3", "family": "F3"},
                program={"program_id": "F3-VHVH"},
            )
            self.assertFalse(receipt["repair_probe_pass"])
            self.assertEqual(receipt["status"], "failed_current_or_anchor_equivalence")


if __name__ == "__main__":
    unittest.main()
