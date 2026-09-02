import copy
import unittest

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f3_final_pose_search_v3 import (
    build_f3_final_pose_recipe_universe_v3,
)
from controlled_multi_future.f3_planner_integration_v3 import (
    STAGE_A_PURPOSE,
    STAGE_B_PURPOSE,
    build_f3_stage_a_planner_spec_v3,
    build_f3_stage_b_planner_spec_v3,
    build_f3_stage_b_targets_v3,
    finalize_f3_candidate_qualification_v3,
    run_f3_stage_a_planner_v3,
    run_f3_stage_b_planner_v3,
)
from controlled_multi_future.official_raw_pose_generation_v1 import (
    OFFICIAL_GENERATOR_VERSION,
)


def raw_receipt(recipe):
    actor = [0, 0, 0.8, 1, 0, 0, 0]
    pregrasp = [0, -0.10, 0.9, 1, 0, 0, 0]
    grasp = [0, -0.04, 0.9, 1, 0, 0, 0]
    value = {
        "schema_version": "cmf_official_raw_pose_generation_v1",
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": "F3",
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "asset": recipe["asset"],
        "main_object_model_id": None,
        "arm": recipe["arm"],
        "contact_point_id": recipe["official_contact_point_id"],
        "rotation_candidate_index": recipe[
            "official_rotation_candidate_index"
        ],
        "pregrasp_distance_m": recipe["pregrasp_distance_m"],
        "target_distance_m": recipe["target_distance_m"],
        "actor_pose": actor,
        "actor_pose_sha256": canonical_hash_json(actor),
        "ordered_rotation_candidate_count": 10,
        "ordered_rotation_candidates_sha256": canonical_hash_json(
            list(range(10))
        ),
        "selected_raw_pregrasp_pose": pregrasp,
        "selected_raw_grasp_pose": grasp,
        "raw_pregrasp_sha256": canonical_hash_json(pregrasp),
        "raw_grasp_sha256": canonical_hash_json(grasp),
        "source_calls": ["official fake"],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def successful_plan(scene, targets, *, query_limit, arm):
    receipts = [
        {
            "segment_id": item["segment_id"],
            "planner_status": "Success",
            "goal_eef_pose": item["pose"],
        }
        for item in targets
    ]
    return {
        "pass": True,
        "segment_receipts": receipts,
        "planner_query_count": len(receipts),
        "terminal_qpos": [0.0],
        "terminal_qpos_sha256": "a" * 64,
        "controls": [{} for _ in targets],
    }


class Scene:
    bottle = object()

    def __init__(self, scene_id):
        self._cmf_scene_instance_id = scene_id


class F3PlannerIntegrationV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = build_f3_final_pose_recipe_universe_v3()["recipes"][0]

    def stage_a(self):
        spec = build_f3_stage_a_planner_spec_v3(
            self.recipe, slot_id="f3-stage-a-test"
        )
        terminal = run_f3_stage_a_planner_v3(
            Scene("fresh-a"),
            spec,
            plan_chain_fn=successful_plan,
            raw_pose_generator=lambda scene, actor, recipe, **kwargs: raw_receipt(
                recipe
            ),
        )
        return spec, terminal

    def test_independent_purposes_and_stage_a_alone_never_ready(self):
        spec, terminal = self.stage_a()
        self.assertEqual(spec["purpose"], STAGE_A_PURPOSE)
        self.assertFalse(spec["planner_execution_authorized"])
        self.assertTrue(terminal["stage_a_pass"])
        self.assertFalse(terminal["candidate_ready"])
        self.assertEqual(
            terminal["raw_pose_generation_receipt"][
                "official_generator_version"
            ],
            OFFICIAL_GENERATOR_VERSION,
        )

    def test_stage_b_exact_closed_loop_order_and_axes(self):
        _, stage_a = self.stage_a()
        spec = build_f3_stage_b_planner_spec_v3(
            stage_a, slot_id="f3-stage-b-test"
        )
        self.assertEqual(spec["purpose"], STAGE_B_PURPOSE)
        targets = build_f3_stage_b_targets_v3(stage_a)
        self.assertEqual(
            [item["segment_id"].replace("f3_v3_stage_b_", "") for item in targets],
            [
                "lift",
                "central_1",
                "V_plus",
                "V_minus",
                "central_2",
                "H_plus",
                "H_minus",
                "central_3",
            ],
        )
        central = targets[1]["pose"]
        self.assertAlmostEqual(targets[2]["pose"][2] - central[2], 0.055)
        self.assertAlmostEqual(targets[3]["pose"][2] - central[2], -0.055)
        self.assertAlmostEqual(targets[5]["pose"][0] - central[0], 0.050)
        self.assertAlmostEqual(targets[6]["pose"][0] - central[0], -0.050)
        stage_b = run_f3_stage_b_planner_v3(
            Scene("fresh-b"), spec, stage_a, plan_chain_fn=successful_plan
        )
        final = finalize_f3_candidate_qualification_v3(stage_a, stage_b)
        self.assertTrue(stage_b["stage_b_pass"])
        self.assertTrue(final["candidate_ready"])

    def test_stage_b_failure_and_wrong_binding_fail_closed(self):
        _, stage_a = self.stage_a()
        spec = build_f3_stage_b_planner_spec_v3(
            stage_a, slot_id="f3-stage-b-fail"
        )

        def failed(scene, targets, *, query_limit, arm):
            result = successful_plan(
                scene, targets, query_limit=query_limit, arm=arm
            )
            result["pass"] = False
            result["segment_receipts"][-1]["planner_status"] = "Fail"
            return result

        stage_b = run_f3_stage_b_planner_v3(
            Scene("fresh-b-fail"), spec, stage_a, plan_chain_fn=failed
        )
        self.assertFalse(stage_b["candidate_ready"])
        self.assertFalse(
            finalize_f3_candidate_qualification_v3(stage_a, stage_b)[
                "candidate_ready"
            ]
        )
        tampered = copy.deepcopy(stage_a)
        tampered["recipe_sha256"] = "0" * 64
        tampered["receipt_sha256"] = canonical_hash_json(
            {key: value for key, value in tampered.items() if key != "receipt_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "binding"):
            run_f3_stage_b_planner_v3(
                Scene("fresh-b-wrong"),
                spec,
                tampered,
                plan_chain_fn=successful_plan,
            )


if __name__ == "__main__":
    unittest.main()
