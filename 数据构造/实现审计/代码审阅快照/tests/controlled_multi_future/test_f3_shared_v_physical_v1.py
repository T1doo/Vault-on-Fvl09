import unittest
from unittest.mock import patch

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f3_shared_v_physical_v1 import (
    build_f3_shared_v_physical_spec_v1,
    run_f3_shared_v_physical_v1,
    validate_f3_shared_v_physical_spec_v1,
)


class F3SharedVPhysicalV1Test(unittest.TestCase):
    def fixtures(self):
        recipe = {
            "recipe_sha256": "1" * 64,
            "asset": {"modelname": "001_bottle", "model_id": 15},
            "arm": "left",
        }
        stage_a_spec = {
            "spec_sha256": "2" * 64,
            "recipe": recipe,
            "scene_binding": {"scene": "nominal"},
        }
        stage_a_terminal = {
            "receipt_sha256": "3" * 64,
            "final_pose_freeze": {
                "final_goal_poses": {
                    "pregrasp": [0, 0, 1, 1, 0, 0, 0],
                    "grasp": [0, 0, 0.9, 1, 0, 0, 0],
                    "lift": [0, 0, 0.95, 1, 0, 0, 0],
                }
            },
        }
        stage_b_spec = {"spec_sha256": "4" * 64}
        stage_b_terminal = {"stage_b_pass": True}
        stage_b_terminal["receipt_sha256"] = canonical_hash_json(stage_b_terminal)
        runtime_tuple = {
            "asset": recipe["asset"],
            "arm": "left",
            "tuple_id": "f3-asset-grasp-v2-r01",
            "tuple_sha256": "5" * 64,
            "close_normalized_target": 0.0,
            "post_close_settle_frames": 250,
        }
        return recipe, stage_a_spec, stage_a_terminal, stage_b_spec, stage_b_terminal, runtime_tuple

    def build(self):
        recipe, a_spec, a_terminal, b_spec, b_terminal, runtime_tuple = self.fixtures()
        with patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "validate_f3_stage_a_planner_spec_v3_1",
            return_value=a_spec,
        ), patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "validate_f3_stage_a_terminal_v3_1",
            return_value=a_terminal,
        ), patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "validate_f3_stage_b_planner_spec_v3_1",
            return_value=b_spec,
        ), patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "finalize_f3_candidate_qualification_v3_1",
            return_value={
                "planner_qualified_for_physical_probe": True,
                "receipt_sha256": "6" * 64,
            },
        ), patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "build_f3_asset_grasp_qualification_v2",
            return_value={"grasp_tuples": [runtime_tuple]},
        ), patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "build_f3_stage_b_targets_v3_1",
            return_value=[
                {"segment_id": "central_1", "pose": [0, 0, 0.95, 1, 0, 0, 0]},
                {"segment_id": "V_plus", "pose": [0, 0, 1.005, 1, 0, 0, 0]},
                {"segment_id": "V_minus", "pose": [0, 0, 0.895, 1, 0, 0, 0]},
                {"segment_id": "central_2", "pose": [0, 0, 0.95, 1, 0, 0, 0]},
            ],
        ):
            return build_f3_shared_v_physical_spec_v1(
                a_spec,
                a_terminal,
                b_spec,
                b_terminal,
                slot_id="f3-physical",
                planner_reset_nonce=707,
            )

    def test_spec_has_exact_seven_target_no_suffix_chain(self):
        spec = validate_f3_shared_v_physical_spec_v1(self.build())
        self.assertEqual(len(spec["ordered_targets"]), 7)
        self.assertEqual(spec["planner_query_limit"], 7)
        self.assertFalse(spec["suffix_allowed"])
        self.assertEqual(spec["legacy_scene_spec"]["family"], "F3")
        self.assertEqual(
            [item["segment_id"] for item in spec["ordered_targets"][-3:]],
            [
                "f3_shared_v_v_plus",
                "f3_shared_v_v_minus",
                "f3_shared_v_return_central",
            ],
        )

    def test_runner_uses_real_physical_gate_result(self):
        spec = self.build()
        scene = type("Scene", (), {"planner_query_count": 7})()
        with patch(
            "controlled_multi_future.f3_shared_v_physical_v1."
            "execute_f3_level2_physical_v1",
            return_value={"sequence_complete": True, "gates": {"all": True}},
        ) as execute:
            terminal = run_f3_shared_v_physical_v1(scene, spec)
        self.assertEqual(execute.call_count, 1)
        self.assertTrue(terminal["shared_v_physically_qualified"])
        self.assertTrue(terminal["three_scene_confirmation_ready"])
        self.assertFalse(terminal["candidate_ready"])


if __name__ == "__main__":
    unittest.main()
