import inspect
import unittest

from controlled_multi_future.probes import runtime_v3_2_complete_family_scope
from controlled_multi_future.probes import gpu_guard_v2_3
from controlled_multi_future.probes import runtime_v3_2_authorization_v1


class RuntimeV3_2EntrypointsStaticTest(unittest.TestCase):
    def test_family_scopes_and_versions_are_v3_2_only(self):
        self.assertEqual(
            runtime_v3_2_complete_family_scope.SCOPE_FAMILIES,
            {
                "F1_three_branch_nonformal_probe_v3_2": "F1",
                "F2_asset_mapping_and_three_branch_nonformal_probe_v3_2": "F2",
                "F3_grasp_lift_and_full_program_nonformal_probe_v3_2": "F3",
                "F4_arm_asset_layout_and_full_program_nonformal_probe_v3_2": "F4",
            },
        )
        self.assertEqual(
            runtime_v3_2_authorization_v1.IMPLEMENTATION_VERSION,
            "controlled_multi_future_runtime_v3_2",
        )
        self.assertEqual(gpu_guard_v2_3.GUARD_SCHEMA_VERSION, "cmf_gpu_guard_v2_3")
        source = inspect.getsource(runtime_v3_2_complete_family_scope.main)
        self.assertIn('implementation_version="controlled_multi_future_runtime_v3_2"', source)
        self.assertNotIn("load_authorization_v1_2", source)


if __name__ == "__main__":
    unittest.main()
