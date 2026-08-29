import inspect
import unittest

from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F3ControllerV3_3,
    F4ControllerV3_3,
)
from controlled_multi_future.f3_clearance_route_v3 import (
    F3_H_NOMINAL_AMPLITUDE_M,
    F3_PROGRAMS,
    F3_V_NOMINAL_AMPLITUDE_M,
)
from controlled_multi_future.f4_uniform_block_carry_midpoint_v3 import (
    F4_SEGMENTED_BLOCK_SUFFIXES,
)
from controlled_multi_future.pre_stage0_authorization_v3 import (
    load_parent_user_authorization,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    current_source_bindings_v3_3,
)
from controlled_multi_future.runtime_v3_3_budget_v1 import (
    budget_artifact,
    validate_static_scope_activity_envelope,
)
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import (
    planned_scope_spec,
)


PARENT = (
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "USER_AUTHORIZATION_RUNTIME_V3_3_CONTINUED_REPAIRS_GPU0_7_20260830.json"
)


class Revision3RepairsIntegrationTest(unittest.TestCase):
    def test_f2_uses_drop_route_and_fixed_six_candidate_beside(self):
        source = inspect.getsource(
            F2ControllerV3_3.plan_suffix_from_actual_prefix_end_state
        )
        candidate_source = inspect.getsource(
            F2ControllerV3_3._plan_fixed_beside_candidates
        )
        execution_source = inspect.getsource(
            F2ControllerV3_3.execute_frozen_suffix_spec
        )
        self.assertIn("build_inside_gravity_drop_route", source)
        self.assertIn("inside_gravity_drop_10cm_v3", source)
        self.assertIn("_plan_fixed_beside_candidates", source)
        self.assertIn("F2_BESIDE_CANDIDATES_V3", candidate_source)
        self.assertIn("audit_beside_candidate_receipts", candidate_source)
        self.assertNotIn("BESIDE_SECTORS_RELATIVE_XY_M[-1]", candidate_source)
        self.assertIn("inside_drop_opening_projection_inside", execution_source)
        self.assertIn("inside_drop_rim_clearance_pass", execution_source)
        self.assertIn("verify_true_cavity_obb", execution_source)
        self.assertIn('"target_relation"', execution_source)

    def test_f3_clearance_route_preserves_science_and_hard_gates(self):
        source = inspect.getsource(F3ControllerV3_3.plan_and_execute_canonical_prefix)
        replay_source = inspect.getsource(
            F3ControllerV3_3.validate_replayed_prefix_physical
        )
        self.assertEqual(F3_V_NOMINAL_AMPLITUDE_M, 0.055)
        self.assertEqual(F3_H_NOMINAL_AMPLITUDE_M, 0.050)
        self.assertEqual(F3_PROGRAMS, ("VVHH", "VHVH", "VHHV"))
        self.assertIn("build_f3_clearance_height_audit", source)
        self.assertIn("build_f3_clearance_route_targets", source)
        self.assertIn("time_dilate_f3_carry_control_2x", source)
        self.assertIn("F3_CENTRAL_HOLD_STEPS", source)
        self.assertIn("frozen contact3/candidate0", source)
        self.assertIn("audit_f3_free_space_event_contacts", source)
        self.assertIn("audit_f3_grasp_boundary_stability", source)
        self.assertIn("audit_f3_free_space_event_contacts", replay_source)
        self.assertIn("audit_f3_grasp_boundary_stability", replay_source)

    def test_f4_uniform_seven_segment_route_is_used_for_staged_and_full(self):
        suffix = inspect.getsource(
            F4ControllerV3_3.plan_suffix_from_actual_prefix_end_state
        )
        diagnostic = inspect.getsource(
            F4ControllerV3_3.plan_diagnostic_blocks_from_actual_prefix_end_state
        )
        execution = inspect.getsource(F4ControllerV3_3.execute_frozen_suffix_spec)
        self.assertEqual(
            F4_SEGMENTED_BLOCK_SUFFIXES,
            (
                "pregrasp",
                "grasp",
                "lift",
                "carry_mid",
                "preplace",
                "release",
                "neutral",
            ),
        )
        self.assertIn("expand_uniform_f4_block_carry_targets", suffix)
        self.assertIn("validate_uniform_f4_block_carry_targets", suffix)
        self.assertIn("expand_uniform_f4_block_carry_targets", diagnostic)
        self.assertIn("target_start_index", diagnostic)
        self.assertIn("cursor + 6", execution)
        self.assertIn("cursor += len(F4_SEGMENTED_BLOCK_SUFFIXES)", execution)
        self.assertEqual(
            F4ControllerV3_3.COMMON_SEGMENT_IDS,
            (
                "common_pregrasp",
                "common_grasp",
                "common_lift",
                "common_safe_vertical",
                "common_center_high",
                "common_above_tray",
                "common_preplace",
                "common_release",
                "common_neutral",
            ),
        )

    def test_revision3_budget_parent_and_source_bindings_are_closed(self):
        budget = budget_artifact()
        self.assertEqual(budget["maximum_new_implementation_revisions_per_family"], 3)
        self.assertFalse(budget["automatic_retry"])
        self.assertFalse(budget["stage0_authorized"])
        self.assertEqual(
            validate_static_scope_activity_envelope(
                "F2_diagnosis_root_per_revision"
            )["source_bound_static_envelope"]["planner_query_count"],
            68,
        )
        self.assertEqual(
            validate_static_scope_activity_envelope(
                "F3_prefix_root_per_revision"
            )["source_bound_static_envelope"]["planner_query_count"],
            96,
        )
        self.assertEqual(
            validate_static_scope_activity_envelope(
                "F4_block_root_per_revision"
            )["source_bound_static_envelope"]["planner_query_count"],
            116,
        )
        for family, scope in (
            ("F2", "F2_diagnosis_root_per_revision"),
            ("F3", "F3_prefix_root_per_revision"),
            ("F4", "F4_block_root_per_revision"),
        ):
            spec = planned_scope_spec(scope, revision_index=3)
            self.assertEqual(spec["family"], family)
            self.assertEqual(spec["implementation_revision_index"], 3)
            self.assertEqual(spec["maximum_full_root_execution_per_revision"], 1)
        parent = load_parent_user_authorization(PARENT)
        self.assertEqual(parent["maximum_new_implementation_revisions_per_family"], 3)
        self.assertEqual(parent["allowed_physical_gpu_indices"], list(range(8)))
        self.assertFalse(parent["formal_stage0_authorized"])
        bindings = current_source_bindings_v3_3()
        for key in (
            "f2_suffix_routes_sha256",
            "f3_clearance_route_sha256",
            "f4_uniform_block_carry_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64)


if __name__ == "__main__":
    unittest.main()
