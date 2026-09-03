import copy
import hashlib
import json
from pathlib import Path
import unittest

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f2_top_contact_development_root_proposal_v1 import (
    SELECTED,
    build_f2_top_contact_development_root_proposal_v1,
    validate_f2_top_contact_development_root_proposal_v1,
)
from controlled_multi_future.f3_post_rotation1_replacement_proposal_v1 import (
    REPLACEMENTS,
    RETAINED_SURVIVOR,
    build_f3_post_rotation1_replacement_proposal_v1,
    validate_f3_post_rotation1_replacement_proposal_v1,
)
from controlled_multi_future.f4_guard_manifest_static_preflight_v1 import (
    audit_f4_guard_manifest_static_v1,
    reject_f4_proposal_execution_v1,
)


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
AUDIT = WORKSPACE / "Vault-on-Fvl09/数据构造/实现审计"


class PostGateNextProposalContractsV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2 = build_f2_top_contact_development_root_proposal_v1()
        cls.f3 = build_f3_post_rotation1_replacement_proposal_v1()

    def test_f2_exact_candidate_root_budget_and_fail_closed(self):
        self.assertEqual(self.f2["selected_candidate"]["recipe_sha256"], SELECTED["recipe_sha256"])
        self.assertEqual(
            [
                self.f2["selected_candidate"][key]
                for key in (
                    "main_object_model_id",
                    "plastic_box_model_id",
                    "arm",
                    "official_contact_point_id",
                    "official_rotation_candidate_index",
                )
            ],
            [0, 2, "left", 8, 0],
        )
        self.assertEqual(self.f2["program_ids"], ["F2-inside", "F2-on", "F2-beside"])
        self.assertEqual(
            self.f2["budget"],
            {
                "root_invocation_cap": 1,
                "canonical_prefix_planner_query_cap": 3,
                "suffix_planner_query_cap_per_program": 24,
                "aggregate_planner_query_cap": 75,
                "fresh_scene_cap": 8,
                "robot_action_scene_cap": 4,
                "branch_execution_cap": 3,
                "raw_trajectory_cap": 3,
                "debug_video_cap": 3,
                "accepted_development_root_cap": 1,
                "accepted_development_trajectory_cap": 3,
                "formal_trajectory_cap": 0,
                "timeout_seconds": 28800,
            },
        )
        validation = validate_f2_top_contact_development_root_proposal_v1(self.f2)
        self.assertTrue(validation["pass"], validation)
        self.assertFalse(validation["executable"])
        self.assertFalse(self.f2["gpu_execution_authorized"])
        self.assertFalse(self.f2["stage1_authorized"])

    def test_f3_exact_replacements_retained_survivor_and_budget(self):
        expected = [
            (5, "right", "lower_body", 2, 1, "f3-final-pose-v3-r1505"),
            (4, "left", "upper_body", 0, 6, "f3-final-pose-v3-r2180"),
            (13, "right", "upper_body", 2, 5, "f3-final-pose-v3-r3677"),
        ]
        observed = [
            (
                item["asset_model_id"],
                item["arm"],
                item["grasp_region"],
                item["contact_point_id"],
                item["rotation_index"],
                item["recipe_id"],
            )
            for item in self.f3["replacement_candidates"]
        ]
        self.assertEqual(observed, expected)
        self.assertEqual(tuple(REPLACEMENTS[i]["recipe_sha256"] for i in range(3)), tuple(item["recipe_sha256"] for item in self.f3["replacement_candidates"]))
        self.assertEqual(self.f3["retained_prior_survivor"], RETAINED_SURVIVOR)
        self.assertFalse(self.f3["retained_prior_survivor"]["planner_rerun_authorized"])
        self.assertEqual(self.f3["bounded_gate"]["total_planner_query_cap"], 30)
        self.assertEqual(self.f3["bounded_gate"]["planner_scene_cap"], 6)
        self.assertEqual(self.f3["bounded_gate"]["physical_candidate_cap"], 4)
        validation = validate_f3_post_rotation1_replacement_proposal_v1(self.f3)
        self.assertTrue(validation["pass"], validation)
        self.assertFalse(validation["executable"])

    def test_f4_run13_regression_and_guard_complete_proposal(self):
        run13 = json.loads(
            (
                AUDIT
                / "production_micro_gate_v1/UNIFIED_RUN_MANIFEST_V1_RUN13.json"
            ).read_text(encoding="utf-8")
        )
        failed = audit_f4_guard_manifest_static_v1(
            run13, workspace_root=WORKSPACE, project_root=PROJECT
        )
        self.assertFalse(failed["pass"])
        self.assertEqual(
            {key for key, value in failed["checks"].items() if not value},
            {
                "all_guard_top_level_inputs_present",
                "proposal_not_authorized",
                "f4_asset_map_nonempty",
                "all_f4_assets_exist_and_match",
            },
        )
        proposed = json.loads(
            (
                AUDIT / "PROPOSED_F4_GUARD_COMPLETE_REOPEN2_MANIFEST_V1.json"
            ).read_text(encoding="utf-8")
        )
        checked = audit_f4_guard_manifest_static_v1(
            proposed, workspace_root=WORKSPACE, project_root=PROJECT
        )
        self.assertTrue(checked["pass"], checked)
        self.assertFalse(checked["executable"])
        self.assertFalse(proposed["approved"])
        self.assertFalse(proposed["gpu_execution_authorized"])
        self.assertTrue(all(checked["asset_checks"].values()))
        with self.assertRaises(PermissionError):
            reject_f4_proposal_execution_v1(proposed)

    def test_unified_packet_self_hash_and_global_denials(self):
        packet = json.loads(
            (AUDIT / "PROPOSED_NEXT_RECOVERY_REVIEW_PACKET_V2.json").read_text(
                encoding="utf-8"
            )
        )
        payload = copy.deepcopy(packet)
        digest = payload.pop("packet_sha256")
        self.assertEqual(digest, canonical_hash_json(payload))
        self.assertFalse(packet["approved"])
        self.assertFalse(packet["gpu_execution_authorized"])
        self.assertFalse(packet["physical_execution_authorized"])
        self.assertFalse(packet["executable"])
        self.assertEqual(packet["global"]["allowed_physical_gpu_indices"], list(range(8)))
        self.assertTrue(
            all(
                packet["global"][key] is False
                for key in (
                    "stage0_rerun",
                    "stage1_authorized",
                    "formal_360_authorized",
                    "training_authorized",
                    "h_reveal_authorized",
                    "compression_authorized",
                    "pi05_authorized",
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
