import copy
import unittest
from unittest.mock import patch

from controlled_multi_future.f2_inside_control_search_v2 import (
    audit_f2_horizontal_margin_budget_v2,
    audit_f2_post_close_grasp_transform_v2,
    build_f2_controlled_insertion_suffix_v2,
    build_f2_controlled_insertion_contract_v2,
    build_f2_geometry_certificate_v4,
    build_f2_geometry_certificate_inventory_v4,
    build_f2_grasp_recipe_universe_v2,
    compare_f2_runtime_geometry_v4,
    expand_legacy_f2_preload_failure_v2,
    freeze_f2_final_grasp_pose_v2,
    validate_f2_final_grasp_qualification_v2,
    validate_f2_controlled_insertion_event_order_v2,
)
from controlled_multi_future.high_level_physical_runner_v1 import (
    execute_f2_controlled_insertion_physical_v2,
)


class F2InsideControlSearchV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.certificate = build_f2_geometry_certificate_v4(
            main_object_model_id=5, plastic_box_model_id=8
        )

    def _runtime_geometry(self):
        keys = (
            "main_object_model_id",
            "plastic_box_model_id",
            "main_object_collision_path",
            "plastic_box_collision_path",
            "main_object_model_data_sha256",
            "plastic_box_model_data_sha256",
            "main_object_collision_sha256",
            "plastic_box_collision_sha256",
            "main_object_scale",
            "plastic_box_scale",
            "main_object_spawn_orientation_wxyz",
            "plastic_box_spawn_orientation_wxyz",
            "main_object_local_lower_m",
            "main_object_local_upper_m",
            "main_object_local_center_m",
            "main_object_local_dimensions_m",
            "plastic_box_local_lower_m",
            "plastic_box_local_upper_m",
            "plastic_box_local_center_m",
            "plastic_box_local_dimensions_m",
            "cavity_raw_lower_m",
            "cavity_raw_upper_m",
            "cavity_center_m",
        )
        return {key: copy.deepcopy(self.certificate[key]) for key in keys}

    def test_controlled_insertion_contract_is_cpu_only_and_dispatch_inactive(self):
        contract = build_f2_controlled_insertion_contract_v2()
        self.assertFalse(contract["controlled_insertion"]["primary_10cm_gravity_drop"])
        self.assertEqual(
            contract["controlled_insertion"]["slow_release_normalized_targets"],
            [0.2, 0.4, 0.6, 0.8, 1.0],
        )
        self.assertFalse(contract["legacy_v1_executor_selected_for_dispatch"])
        self.assertFalse(contract["v2_executor_selected_for_dispatch"])
        self.assertFalse(contract["physical_execution_authorized"])

    def test_cpu_runtime_geometry_certificate_fails_closed_on_one_micron_mismatch(self):
        runtime = self._runtime_geometry()
        self.assertTrue(
            compare_f2_runtime_geometry_v4(self.certificate, runtime)["pass"]
        )
        runtime["main_object_local_center_m"][0] += 2e-6
        failed = compare_f2_runtime_geometry_v4(self.certificate, runtime)
        self.assertFalse(failed["pass"])
        self.assertEqual(
            failed["status"], "CPU_RUNTIME_GEOMETRY_CERTIFICATE_MISMATCH"
        )

    def test_cpu_certificate_inventory_covers_all_66_pairs_without_claiming_runtime_pass(self):
        inventory = build_f2_geometry_certificate_inventory_v4()
        self.assertEqual(inventory["distinct_pair_count"], 66)
        self.assertEqual(
            inventory["certificate_count"]
            + len(inventory["certificate_failures"]),
            66,
        )
        self.assertEqual(inventory["runtime_qualified_pair_count"], 0)
        self.assertFalse(inventory["grasp_recipe_pool_generated"])

    def test_grasp_universe_uses_all_contacts_rotations_offsets_and_distances(self):
        pair = {
            "main_object_model_id": 5,
            "plastic_box_model_id": 8,
            "official_can_contact_point_count": 2,
            "geometry_certificate_sha256": self.certificate[
                "certificate_sha256"
            ],
        }
        universe = build_f2_grasp_recipe_universe_v2([pair])
        self.assertEqual(universe["recipe_count"], 2 * 2 * 10 * 3 * 3)
        self.assertEqual(
            {item["official_contact_point_id"] for item in universe["recipes"]},
            {0, 1},
        )
        self.assertTrue(
            all(
                item["first_planner_success_selection_forbidden"]
                for item in universe["recipes"]
            )
        )
        recipe = next(
            item
            for item in universe["recipes"]
            if item["axial_grasp_offset_m"] == 0.02
        )
        frozen = freeze_f2_final_grasp_pose_v2(
            recipe,
            actor_pose=[0, 0, 0.8, 1, 0, 0, 0],
            raw_official_pregrasp_pose=[0, -0.1, 0.9, 1, 0, 0, 0],
            raw_official_grasp_pose=[0, -0.04, 0.9, 1, 0, 0, 0],
            raw_rotation_candidate_index=recipe[
                "official_rotation_candidate_index"
            ],
        )
        receipt = {
            "recipe_sha256": recipe["recipe_sha256"],
            "final_grasp_pose_freeze_sha256": frozen[
                "final_grasp_pose_freeze_sha256"
            ],
            "ordered_planner_input_sha256": frozen[
                "ordered_final_planner_input_sha256"
            ],
            "goal_pose_hashes": frozen["final_goal_pose_hashes"],
            "planner_statuses": {
                "pregrasp": "Success",
                "grasp": "Success",
            },
            "ik_collision_planner_checked": True,
            "post_qualification_pose_mutation": False,
        }
        from controlled_multi_future.canonical_artifact import canonical_hash_json

        receipt["receipt_sha256"] = canonical_hash_json(receipt)
        self.assertTrue(
            validate_f2_final_grasp_qualification_v2(
                recipe, frozen, receipt
            )["pass"]
        )

    def test_five_millimeter_candidate_fails_margin_budget(self):
        gate = audit_f2_horizontal_margin_budget_v2(
            signed_horizontal_margin_m=0.005,
            object_half_extents_m=[0.037, 0.047, 0.036],
        )
        self.assertFalse(gate["pass"])
        self.assertGreater(gate["required_horizontal_margin_m"], 0.020)

    def test_actual_grasp_transform_drives_controlled_suffix(self):
        planned_eef = [0.0, 0.0, 1.0, 1, 0, 0, 0]
        planned_actor = [0.0, 0.0, 0.9, 1, 0, 0, 0]
        actual_eef = [0.002, 0.0, 1.0, 1, 0, 0, 0]
        actual_actor = [0.002, 0.0, 0.9, 1, 0, 0, 0]
        grasp = audit_f2_post_close_grasp_transform_v2(
            planned_eef_pose=planned_eef,
            planned_actor_pose=planned_actor,
            actual_eef_pose=actual_eef,
            actual_actor_pose=actual_actor,
            selected_contact_continuous=True,
            selected_actor_identity_continuous=True,
            actor_table_contact=False,
            evidence_complete=True,
        )
        self.assertTrue(grasp["pass"])
        margin = audit_f2_horizontal_margin_budget_v2(
            signed_horizontal_margin_m=0.040,
            object_half_extents_m=[0.03, 0.04, 0.03],
        )
        suffix = build_f2_controlled_insertion_suffix_v2(
            actual_eef_pose=actual_eef,
            actual_actor_pose=actual_actor,
            target_actor_pose=[0.2, -0.2, 0.8, 1, 0, 0, 0],
            opening_normal_world=[0, 0, 1],
            neutral_eef_pose=[0, 0, 1.1, 1, 0, 0, 0],
            grasp_gate=grasp,
            margin_gate=margin,
        )
        self.assertTrue(suffix["suffix_built_from_actual_grasp_transform"])
        self.assertFalse(suffix["primary_10cm_gravity_drop"])
        self.assertTrue(suffix["support_stability_gate_before_open"]["required"])
        self.assertEqual(
            [item["normalized_open_target"] for item in suffix["slow_release_schedule"]],
            [0.2, 0.4, 0.6, 0.8, 1.0],
        )
        events = [
            "post_close_settle_250",
            "post_close_grasp_transform_gate",
            "suffix_planned_from_actual_transform",
            "lift",
            "preinsert_30mm",
            "controlled_descend_to_support",
            "support_stability_gate_50",
            *[f"slow_release_{index}" for index in range(1, 6)],
            "post_release_settle_250",
            "retreat_neutral",
        ]
        self.assertTrue(
            validate_f2_controlled_insertion_event_order_v2(
                events, support_gate_pass=True
            )["pass"]
        )
        premature = list(events)
        premature[6], premature[7] = premature[7], premature[6]
        self.assertFalse(
            validate_f2_controlled_insertion_event_order_v2(
                premature, support_gate_pass=True
            )["pass"]
        )
        changed = audit_f2_post_close_grasp_transform_v2(
            planned_eef_pose=planned_eef,
            planned_actor_pose=planned_actor,
            actual_eef_pose=actual_eef,
            actual_actor_pose=[0.012, 0.0, 0.9, 1, 0, 0, 0],
            selected_contact_continuous=True,
            selected_actor_identity_continuous=True,
            actor_table_contact=False,
            evidence_complete=True,
        )
        self.assertFalse(changed["pass"])

    def test_legacy_preload_overlay_expands_every_hard_check(self):
        checks = {
            "contact_signal_complete_all_60": True,
            "selected_finger_contact_continuous_all_60": False,
            "selected_actor_identity_all_60": True,
            "no_unintended_contact_all_60": False,
            "opening_projection_inside": False,
            "rim_clearance_reported_pass": False,
            "rim_clearance_at_least_20mm": False,
            "geometry_evidence_complete": True,
            "controller_safety_linear": True,
            "controller_safety_angular": True,
            "exact_10_plus_50_evidence_window": True,
        }
        outer = {
            "receipt_sha256": "a" * 64,
            "result": {
                "physical_result": {
                    "preload_entry_gate_v11": {
                        "pass": False,
                        "receipt_sha256": "b" * 64,
                        "checks": checks,
                        "final_geometry_gate": {
                            "opening_projection_inside": False,
                            "rim_clearance_m": -0.18,
                        },
                        "unintended_contacts": [{"body_b": "table"}],
                    }
                }
            },
        }
        receipt = expand_legacy_f2_preload_failure_v2(
            candidate_id="f2-inside-hv1-r09", outer_receipt=outer
        )
        self.assertEqual(receipt["hard_checks"], checks)
        self.assertEqual(
            receipt["corrected_status"],
            "GRASP_NOT_ACQUIRED_OR_RETAINED_BEFORE_PRELOAD_ENTRY",
        )
        self.assertFalse(receipt["broader_asset_family_exhaustion_supported"])

    def test_two_phase_executor_replans_after_actual_grasp_and_opens_only_after_support(self):
        pair = {
            "main_object_model_id": 5,
            "plastic_box_model_id": 8,
            "official_can_contact_point_count": 1,
            "geometry_certificate_sha256": self.certificate[
                "certificate_sha256"
            ],
        }
        recipe = build_f2_grasp_recipe_universe_v2([pair])["recipes"][0]
        planned_actor = [0, 0, 0.9, 1, 0, 0, 0]
        frozen = freeze_f2_final_grasp_pose_v2(
            recipe,
            actor_pose=planned_actor,
            raw_official_pregrasp_pose=[0, -0.1, 1.0, 1, 0, 0, 0],
            raw_official_grasp_pose=[0, -0.04, 1.0, 1, 0, 0, 0],
            raw_rotation_candidate_index=0,
        )
        qualification = {
            "recipe_sha256": recipe["recipe_sha256"],
            "final_grasp_pose_freeze_sha256": frozen[
                "final_grasp_pose_freeze_sha256"
            ],
            "ordered_planner_input_sha256": frozen[
                "ordered_final_planner_input_sha256"
            ],
            "goal_pose_hashes": frozen["final_goal_pose_hashes"],
            "planner_statuses": {
                "pregrasp": "Success",
                "grasp": "Success",
            },
            "ik_collision_planner_checked": True,
            "post_qualification_pose_mutation": False,
        }
        from controlled_multi_future.canonical_artifact import canonical_hash_json

        qualification["receipt_sha256"] = canonical_hash_json(qualification)

        class Actor:
            def __init__(self, name):
                self.name = name

            def get_name(self):
                return self.name

        class Scene:
            def __init__(self):
                self.can = Actor("can")
                self.box = Actor("box")
                self.trace = [{}]
                self.planner_query_count = 0

            def close_gripper(self, arm, pos):
                return {"kind": "close", "pos": pos}

            def open_gripper(self, arm, pos):
                return {"kind": "open", "pos": pos}

        scene = Scene()
        event_log = []
        wait_count = {"value": 0}

        def fake_plan(scene_arg, targets, *, query_limit, arm):
            event_log.append(f"plan_{len(targets)}")
            scene_arg.planner_query_count += len(targets)
            return {
                "pass": True,
                "segment_receipts": [],
                "planner_query_count": scene_arg.planner_query_count,
                "terminal_qpos": [0.0],
                "terminal_qpos_sha256": "a" * 64,
                "controls": [{} for _ in targets],
            }

        def fake_execute(scene_arg, controls, targets, index, arm):
            event_log.append(targets[index]["segment_id"])
            return {"segment_id": targets[index]["segment_id"]}

        def fake_action(scene_arg, action, label):
            event_log.append(label)
            return {"label": label}

        def fake_wait(scene_arg, steps):
            wait_count["value"] += 1
            event_log.append(f"wait_{steps}")
            kind = "finger" if wait_count["value"] == 1 else "box"
            for _ in range(steps):
                scene_arg.trace.append(
                    {
                        "selected_gripper_contact": True,
                        "selected_contact_actor_name": "can",
                        "contact_pairs": [{"kind": kind}],
                        "actor_linear_velocity": [0.0, 0.0, 0.0],
                        "actor_angular_velocity": [0.0, 0.0, 0.0],
                    }
                )

        def fake_pair(pair, first, second):
            return pair.get("kind") == "box" and "box" in second

        actual_eef = [0.002, -0.06, 1.0, 1, 0, 0, 0]
        actual_actor = [0.002, 0, 0.9, 1, 0, 0, 0]
        neutral = [0, 0, 1.1, 1, 0, 0, 0]
        with patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "capture_f2_runtime_geometry_observation_v4",
            return_value=self._runtime_geometry(),
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._planner_reset",
            side_effect=lambda *args, **kwargs: event_log.append("reset"),
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._plan_chain",
            side_effect=fake_plan,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_execute_planned_segment",
            side_effect=fake_execute,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._must_action",
            side_effect=fake_action,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._arm_tag",
            return_value="left",
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._wait_and_record",
            side_effect=fake_wait,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_pair_is_physical_hit_between",
            side_effect=fake_pair,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_complete_contact_signal",
            return_value=True,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._arm_eef_pose",
            side_effect=[actual_eef, neutral],
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._pose",
            return_value=actual_actor,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_arm_original_pose",
            return_value=neutral,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_inside_opening_geometry",
            return_value={"opening_projection_inside": True},
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_f2_relation_predicates",
            return_value={"inside": True, "on": False, "beside": False},
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "_arm_gripper_open",
            return_value=True,
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "audit_f2_final_inside_success_gate_v10",
            return_value={"pass": True},
        ):
            result = execute_f2_controlled_insertion_physical_v2(
                scene,
                arm="left",
                binding={},
                recipe=recipe,
                final_grasp_freeze=frozen,
                final_grasp_qualification=qualification,
                geometry_certificate=self.certificate,
                planned_actor_pose=planned_actor,
                target_actor_pose=[0.2, -0.2, 0.8, 1, 0, 0, 0],
                runtime_signed_horizontal_margin_m=0.04,
                opening_normal_world=[0, 0, 1],
                planner_query_limit=12,
            )
        self.assertTrue(result["sequence_complete"], result)
        self.assertFalse(result["primary_10cm_gravity_drop"])
        self.assertLess(event_log.index("wait_250"), event_log.index("plan_5"))
        self.assertLess(
            event_log.index("wait_50"),
            event_log.index("f2_v2_slow_release_1"),
        )
        self.assertEqual(
            [
                event
                for event in event_log
                if event.startswith("f2_v2_slow_release_")
            ],
            [f"f2_v2_slow_release_{index}" for index in range(1, 6)],
        )


if __name__ == "__main__":
    unittest.main()
