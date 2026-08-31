import unittest
from controlled_multi_future.closure_f3_scope_v2 import budget,spec,parent
from controlled_multi_future.gpu_parallel_policy_v2 import validate_current_gpu_authorization
class TestClosureF3ScopeV2(unittest.TestCase):
 def test_scope(self):
  b=budget();self.assertEqual(b["allowed_physical_gpu_indices"],list(range(8)));self.assertEqual(b["execution_limit"],3);self.assertEqual(b["suffix_execution_limit"],0);s=spec();self.assertEqual(s["f3_common_grasp_prefix_v2"]["close_normalized_target"],0.5);self.assertEqual(s["diagnostic_scene_count"],3);self.assertFalse(parent()["stage1_authorized"])
 def test_gpu(self):
  v={"gpu_policy_version":"cmf_gpu_parallel_policy_v2","allowed_physical_gpu_indices":list(range(8)),"dynamic_fresh_idle_selection":True,"parallel_different_cards_authorized":True,"one_project_job_per_gpu":True,"one_root_one_gpu":True,"root_sharding_authorized":False,"share_busy_gpu_authorized":False,"atomic_guard_recheck_before_launch":True,"automatic_gpu0_fallback":False};validate_current_gpu_authorization(v)
if __name__=="__main__":unittest.main()
