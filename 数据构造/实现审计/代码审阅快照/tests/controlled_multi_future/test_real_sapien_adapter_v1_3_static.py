import inspect
import unittest

from controlled_multi_future.family_runners_v3_3 import CONTROLLERS
from controlled_multi_future.real_sapien_adapter_v1_3 import (
    ADAPTER_VERSION_V1_3,
    RoboTwinRealSapienStrictPrefixAdapterV1_3,
)


class RealSapienAdapterV1_3StaticTest(unittest.TestCase):
    def test_all_families_have_strict_prefix_controllers(self):
        self.assertEqual(set(CONTROLLERS), {"F1", "F2", "F3", "F4"})
        for family, controller in CONTROLLERS.items():
            contract = controller.canonical_prefix_contract([])
            self.assertEqual(contract["family"], family)
            self.assertIn(contract["arm"], ("left", "right"))
            self.assertFalse(contract["target_role_read"])
            self.assertTrue(contract["settling_excluded_from_semantic_P"])

    def test_adapter_exposes_v3_3_split_interfaces(self):
        source = inspect.getsource(RoboTwinRealSapienStrictPrefixAdapterV1_3)
        for name in (
            "canonical_prefix_contract",
            "plan_and_execute_canonical_prefix",
            "initialize_prefix_replay_trace",
            "plan_suffix_from_actual_prefix_end_state",
            "execute_frozen_suffix_spec",
        ):
            self.assertIn(f"def {name}", source)
        self.assertEqual(
            ADAPTER_VERSION_V1_3,
            "RoboTwinRealSapienStrictPrefixAdapterV1_3",
        )

    def test_import_and_adapter_do_not_create_scene(self):
        module = inspect.getmodule(RoboTwinRealSapienStrictPrefixAdapterV1_3)
        source = inspect.getsource(module)
        self.assertNotIn("setup_demo(", source)
        self.assertNotIn("import sapien", source)
        self.assertNotIn("torch", source)


if __name__ == "__main__":
    unittest.main()
