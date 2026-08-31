import unittest
from controlled_multi_future.closure_f4_scope_v2 import budget,spec
class TestClosureF4ScopeV2(unittest.TestCase):
 def test_scope(self):
  b=budget();self.assertEqual(b["allowed_physical_gpu_indices"],list(range(8)));self.assertEqual(b["suffix_execution_limit"],0);s=spec();self.assertEqual(s["derivation_interface_version"],"cmf_f4_derivation_interface_v2");self.assertEqual(s["scene_layout"]["layout_version"],"f4_post_stage0_slot_row_v1");self.assertEqual(s["post_stage0_selected_f4_corridor_id"],"lower_carry_height")
if __name__=="__main__":unittest.main()
