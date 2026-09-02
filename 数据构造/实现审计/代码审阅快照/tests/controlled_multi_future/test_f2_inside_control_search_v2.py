import copy
import unittest

from controlled_multi_future.f2_inside_control_search_v2 import (
    audit_f2_horizontal_margin_budget_v2,
    audit_f2_post_close_grasp_transform_v2,
    build_f2_controlled_insertion_suffix_v2,
    build_f2_geometry_certificate_v4,
    build_f2_geometry_certificate_inventory_v4,
    build_f2_grasp_recipe_universe_v2,
    compare_f2_runtime_geometry_v4,
    expand_legacy_f2_preload_failure_v2,
    validate_f2_controlled_insertion_event_order_v2,
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


if __name__ == "__main__":
    unittest.main()
