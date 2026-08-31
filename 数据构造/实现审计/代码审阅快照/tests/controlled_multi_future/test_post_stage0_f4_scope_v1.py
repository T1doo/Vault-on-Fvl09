import unittest
from controlled_multi_future.gpu_parallel_policy_v2 import validate_current_gpu_authorization
from controlled_multi_future.post_stage0_f4_scope_v1 import post_stage0_f4_budget_v1,post_stage0_f4_planned_spec_v1,post_stage0_f4_parent_authorization_v1
class TestPostStage0F4ScopeV1(unittest.TestCase):
    def test_scope(self):
        b=post_stage0_f4_budget_v1(); self.assertEqual(b["allowed_physical_gpu_indices"],list(range(8))); self.assertEqual(b["suffix_execution_limit"],0); self.assertEqual(b["planner_query_limit"],96)
        p=post_stage0_f4_planned_spec_v1(); self.assertEqual(p["post_stage0_selected_f4_corridor_id"],"lower_carry_height"); self.assertEqual(p["scene_layout"]["layout_version"],"f4_post_stage0_slot_row_v1")
        a=post_stage0_f4_parent_authorization_v1(); self.assertFalse(a["stage0_reopened"]); self.assertEqual(a["maximum_conditional_f4_development_roots_after_pass"],1)
    def test_gpu_policy(self):
        v={"gpu_policy_version":"cmf_gpu_parallel_policy_v2","allowed_physical_gpu_indices":list(range(8)),"dynamic_fresh_idle_selection":True,"parallel_different_cards_authorized":True,"one_project_job_per_gpu":True,"one_root_one_gpu":True,"root_sharding_authorized":False,"share_busy_gpu_authorized":False,"atomic_guard_recheck_before_launch":True,"automatic_gpu0_fallback":False}; validate_current_gpu_authorization(v)
if __name__=="__main__": unittest.main()
