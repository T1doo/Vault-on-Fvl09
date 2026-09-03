import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.f2_controlled_insertion_physical_v2 import (
    build_f2_controlled_insertion_physical_spec_v2,
    run_f2_controlled_insertion_physical_v2,
    validate_f2_controlled_insertion_physical_spec_v2,
)
from controlled_multi_future.f2_planner_integration_v2 import (
    build_f2_final_grasp_stage_a_spec_v2,
    run_f2_final_grasp_stage_a_planner_v2,
)
from controlled_multi_future.high_level_physical_runner_v1 import (
    HighLevelPhysicalRunnerV1,
)
from controlled_multi_future.official_raw_pose_generation_v1 import (
    OFFICIAL_GENERATOR_VERSION,
)
from controlled_multi_future.planner_qualification_manifests_v2_3 import (
    build_f2_planner_panel_manifest_v1,
)


def raw_receipt(recipe, actor_pose):
    pregrasp = [actor_pose[0], actor_pose[1] - 0.10, 0.90, *actor_pose[3:]]
    grasp = [actor_pose[0], actor_pose[1] - 0.04, 0.90, *actor_pose[3:]]
    value = {
        "schema_version": "cmf_official_raw_pose_generation_v1",
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": "F2",
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "asset": {},
        "main_object_model_id": recipe["main_object_model_id"],
        "arm": recipe["arm"],
        "contact_point_id": recipe["official_contact_point_id"],
        "rotation_candidate_index": recipe[
            "official_rotation_candidate_index"
        ],
        "pregrasp_distance_m": recipe["pregrasp_distance_m"],
        "target_distance_m": recipe["target_distance_m"],
        "actor_pose": actor_pose,
        "actor_pose_sha256": canonical_hash_json(actor_pose),
        "ordered_rotation_candidate_count": 10,
        "ordered_rotation_candidates_sha256": canonical_hash_json(list(range(10))),
        "selected_raw_pregrasp_pose": pregrasp,
        "selected_raw_grasp_pose": grasp,
        "raw_pregrasp_sha256": canonical_hash_json(pregrasp),
        "raw_grasp_sha256": canonical_hash_json(grasp),
        "source_calls": ["production-path test fixture"],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


class F2ControlledInsertionPhysicalV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        panel = build_f2_planner_panel_manifest_v1()
        entry = panel["ordered_recipes"][0]
        cls.recipe = entry["recipe"]
        cls.stage_a_spec = build_f2_final_grasp_stage_a_spec_v2(
            cls.recipe,
            panel["certificate"],
            panel["bindings_by_arm"][cls.recipe["arm"]],
            slot_id="f2-stage-a",
            panel_sha256=panel["panel_sha256"],
            planner_reset_nonce=101,
        )

        class Scene:
            can = object()
            _cmf_scene_instance_id = "f2-scene"
            _cmf_f2_runtime_asset_metadata_receipt_v4 = {
                "receipt_sha256": "a" * 64
            }

        actor_pose = [-0.28, 0.04, 0.79, 0.5, 0.5, 0.5, 0.5]
        terminal_qpos = np.asarray([0.1, 0.2], dtype=np.float32)

        def plan(_scene, targets, *, query_limit, arm):
            return {
                "pass": True,
                "segment_receipts": [
                    {
                        "segment_id": item["segment_id"],
                        "planner_status": "Success",
                    }
                    for item in targets
                ],
                "planner_query_count": query_limit,
                "terminal_qpos": terminal_qpos.tolist(),
                "terminal_qpos_sha256": hash_array(terminal_qpos),
                "controls": [{} for _ in targets],
            }

        with patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "capture_f2_runtime_geometry_observation_v4",
            return_value={},
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "compare_f2_runtime_geometry_v4",
            return_value={"pass": True},
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "generate_official_raw_pose_receipt_v1",
            return_value=raw_receipt(cls.recipe, actor_pose),
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2._planner_reset",
            return_value={
                "reset_performed": True,
                "planner_seed": 101,
                "reset_seed_argument": True,
            },
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2._plan_chain",
            side_effect=plan,
        ):
            cls.stage_a_terminal = run_f2_final_grasp_stage_a_planner_v2(
                Scene(), cls.stage_a_spec
            )

    def test_spec_is_derived_from_passing_stage_a_and_requires_eight_queries(self):
        spec = build_f2_controlled_insertion_physical_spec_v2(
            self.stage_a_spec,
            self.stage_a_terminal,
            slot_id="f2-physical",
            planner_reset_nonce=202,
        )
        checked = validate_f2_controlled_insertion_physical_spec_v2(spec)
        self.assertEqual(checked["planner_query_limit"], 8)
        self.assertFalse(checked["old_gravity_drop_executor_allowed"])
        self.assertFalse(checked["external_target_pose_allowed"])
        self.assertEqual(checked["legacy_scene_spec"]["family"], "F2")
        self.assertEqual(
            checked["legacy_scene_spec"]["f2_asset_layout_binding_v3"][
                "selected_candidate_key"
            ]["main_object_model_id"],
            checked["recipe"]["main_object_model_id"],
        )

    def test_runner_calls_only_v2_executor_and_preserves_dependency(self):
        spec = build_f2_controlled_insertion_physical_spec_v2(
            self.stage_a_spec,
            self.stage_a_terminal,
            slot_id="f2-physical",
            planner_reset_nonce=202,
        )
        scene = type("Scene", (), {"planner_query_count": 8})()
        with patch(
            "controlled_multi_future.f2_controlled_insertion_physical_v2."
            "execute_f2_controlled_insertion_physical_v2",
            return_value={
                "sequence_complete": True,
                "strict_inside_verifier_pass": True,
            },
        ) as execute:
            terminal = run_f2_controlled_insertion_physical_v2(scene, spec)
        self.assertTrue(terminal["physically_qualified"])
        self.assertEqual(terminal["planner_query_count"], 8)
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(
            execute.call_args.kwargs["final_grasp_freeze"],
            spec["final_grasp_pose_freeze"],
        )

    def test_failed_stage_a_cannot_build_physical_spec(self):
        failed = dict(self.stage_a_terminal)
        failed.pop("receipt_sha256")
        failed["planner_qualified_for_physical_probe"] = False
        failed["receipt_sha256"] = canonical_hash_json(failed)
        with self.assertRaisesRegex(ValueError, "passing Stage-A"):
            build_f2_controlled_insertion_physical_spec_v2(
                self.stage_a_spec,
                failed,
                slot_id="f2-physical",
                planner_reset_nonce=202,
            )

    def test_legacy_high_level_f2_dispatcher_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "permanently disabled"):
            HighLevelPhysicalRunnerV1(object()).run(
                output_dir=Path("/nfs_share/lijunhui/Robotwin2/tmp/not-created"),
                planned_spec={"family": "F2"},
            )


if __name__ == "__main__":
    unittest.main()
