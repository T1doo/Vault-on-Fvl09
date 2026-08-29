import inspect
import unittest

from controlled_multi_future.family_runners_v3_3 import CONTROLLERS


class FamilyControllersV3_3StaticTest(unittest.TestCase):
    def test_all_suffix_planners_cache_controls_from_actual_prefix_end(self):
        for family, controller in CONTROLLERS.items():
            source = inspect.getsource(
                controller.plan_suffix_from_actual_prefix_end_state
            )
            self.assertIn("_cache_suffix_controls", source, family)
            self.assertNotIn("home", source.lower(), family)

    def test_all_suffix_execution_is_planner_free(self):
        forbidden = (
            "_plan_chain(",
            "_move_arm(",
            "_move_left(",
            "grasp_actor(",
            "move_by_displacement(",
            "choose_grasp_pose(",
        )
        for family, controller in CONTROLLERS.items():
            source = inspect.getsource(controller.execute_frozen_suffix_spec)
            self.assertIn("_cached_controls", source, family)
            self.assertIn("_execute_cached_segment", source, family)
            for token in forbidden:
                self.assertNotIn(token, source, f"{family}: {token}")

    def test_family_specific_contracts_are_present(self):
        f1 = inspect.getsource(CONTROLLERS["F1"].plan_suffix_from_actual_prefix_end_state)
        f2 = inspect.getsource(CONTROLLERS["F2"].plan_suffix_from_actual_prefix_end_state)
        f3 = inspect.getsource(CONTROLLERS["F3"].plan_and_execute_canonical_prefix)
        f4 = inspect.getsource(CONTROLLERS["F4"].plan_suffix_from_actual_prefix_end_state)
        self.assertIn("v3_3_uniform_8cm_lift", f1)
        self.assertIn("inside_descend", f2)
        self.assertIn("shared_V", f3)
        self.assertIn("object_target_groups", f4)


if __name__ == "__main__":
    unittest.main()
