import inspect
import unittest

import numpy as np

from controlled_multi_future.family_runners_v3_1 import F4RunnerV3_1
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F3ControllerV3_3,
    F3_CLOSED_LOOP_PRIMITIVE_VERSION,
    F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2,
    F4ControllerV3_3,
    _f2_dynamic_post_settle_checks,
    _time_dilated_closed_loop_event_targets,
)
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import planned_scope_spec


class Revision2RepairsF2F3F4Test(unittest.TestCase):
    def test_f2_dynamic_can_uses_post_settle_contract_not_spawn_z_equality(self):
        source = inspect.getsource(F2ControllerV3_3._require_layout_v2)
        helper_source = inspect.getsource(_f2_dynamic_post_settle_checks)
        self.assertIn("f2_post_settle_dynamic_pose_contract_v3", source)
        self.assertIn("post_settle_xy_within_5mm_of_spawn", helper_source)
        self.assertIn("post_settle_z_drop_nonnegative_bounded_10cm", helper_source)
        self.assertNotIn('"can_xyz": _pose(scene.can)', source)
        self.assertIn('"box_xyz": _pose(scene.box)', source)

    def test_f2_held_can_skips_only_dynamic_spawn_gate(self):
        held_pose = [0.1, -0.1, 0.95, 0.5, 0.5, 0.5, 0.5]
        self.assertEqual(
            _f2_dynamic_post_settle_checks(
                planned_can_xyz=[-0.28, 0.04, 0.79],
                can_pose=held_pose,
                table_support_height_m=0.74,
                pose_linear_speeds=[],
                pose_angular_speeds=[],
                table_contact_window=[],
                sleep_state=False,
                required=False,
            ),
            {},
        )
        failed = _f2_dynamic_post_settle_checks(
            planned_can_xyz=[-0.28, 0.04, 0.79],
            can_pose=held_pose,
            table_support_height_m=0.74,
            pose_linear_speeds=[0.0] * 50,
            pose_angular_speeds=[0.0] * 50,
            table_contact_window=[False] * 50,
            sleep_state=False,
            required=True,
        )
        self.assertFalse(all(failed.values()))
        passed = _f2_dynamic_post_settle_checks(
            planned_can_xyz=[-0.28, 0.04, 0.79],
            can_pose=[-0.28, 0.04, 0.741, 0.5, 0.5, 0.5, 0.5],
            table_support_height_m=0.74,
            pose_linear_speeds=[0.0] * 50,
            pose_angular_speeds=[0.0] * 50,
            table_contact_window=[True] * 50,
            sleep_state=True,
            required=True,
        )
        self.assertTrue(all(passed.values()))

    def test_f3_time_dilated_event_keeps_axes_amplitude_and_seven_targets(self):
        center = np.asarray([0.1, -0.2, 0.9, 1.0, 0.0, 0.0, 0.0])
        for axis, amplitude, dimension in (("V", 0.055, 2), ("H", 0.05, 0)):
            targets = _time_dilated_closed_loop_event_targets(
                center,
                axis=axis,
                amplitude_m=amplitude,
                segment_prefix="event",
            )
            self.assertEqual(len(targets), 7)
            values = [item["pose"][dimension] - center[dimension] for item in targets]
            np.testing.assert_allclose(
                values,
                [0.5 * amplitude, amplitude, 0.0, -0.5 * amplitude, -amplitude, -0.5 * amplitude, 0.0],
            )
        self.assertEqual(F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2, 50)
        self.assertEqual(
            F3_CLOSED_LOOP_PRIMITIVE_VERSION,
            "f3_pose_consistent_time_dilated_closed_loop_v2",
        )
        prefix_source = inspect.getsource(F3ControllerV3_3.plan_and_execute_canonical_prefix)
        suffix_source = inspect.getsource(F3ControllerV3_3.execute_frozen_suffix_spec)
        self.assertIn("_time_dilated_closed_loop_event_targets", prefix_source)
        self.assertIn("_wait_and_record", prefix_source)
        self.assertIn("target_count != 7", suffix_source)
        self.assertIn("_wait_and_record(scene, hold_steps)", suffix_source)
        self.assertIn("event_order_matches_program", suffix_source)

    def test_f4_common_x_uses_frozen_explicit_cube_grasp_contract(self):
        legacy_source = inspect.getsource(F4RunnerV3_1.build_targets)
        current_source = inspect.getsource(F4ControllerV3_3._common_targets)
        self.assertIn('common_grasp_mode == "project_cube_grasp_v1"', legacy_source)
        self.assertIn("build_project_cube_grasp_poses", legacy_source)
        self.assertIn('"common_grasp_mode": "project_cube_grasp_v1"', current_source)
        self.assertNotIn("_audited_planner_assisted_target_construction", current_source)
        self.assertEqual(
            planned_scope_spec("F4_block_root_per_revision", revision_index=2)["arm"],
            "right",
        )
        self.assertEqual(
            planned_scope_spec("F2_diagnosis_root_per_revision", revision_index=2)["arm"],
            "left",
        )
        execute_source = inspect.getsource(F4ControllerV3_3.execute_frozen_suffix_spec)
        self.assertLess(
            execute_source.index("common_angular_speeds ="),
            execute_source.index('"stable_window"'),
        )

    def test_f4_target_structure_requires_exact_common_and_three_groups(self):
        common = [
            {"segment_id": segment_id}
            for segment_id in F4ControllerV3_3.COMMON_SEGMENT_IDS
        ]
        groups = []
        flattened = []
        for role in ("A", "B", "C"):
            targets = [
                {"segment_id": f"{role}_{suffix}"}
                for suffix in (
                    "pregrasp",
                    "grasp",
                    "lift",
                    "carry_mid",
                    "preplace",
                    "release",
                    "neutral",
                )
            ]
            groups.append({"role": role, "targets": targets})
            flattened.extend(targets)
        extra = {
            "execution_arm": "right",
            "common_grasp_contract": {"arm": "right"},
            "object_order": ["A", "B", "C"],
            "object_target_groups": groups,
        }
        F4ControllerV3_3._validate_f4_target_structure(
            common + flattened, extra, require_three_groups=True
        )
        bad = [dict(item) for item in common + flattened]
        bad[9]["segment_id"] = "A_wrong"
        with self.assertRaises(ValueError):
            F4ControllerV3_3._validate_f4_target_structure(
                bad, extra, require_three_groups=True
            )


if __name__ == "__main__":
    unittest.main()
