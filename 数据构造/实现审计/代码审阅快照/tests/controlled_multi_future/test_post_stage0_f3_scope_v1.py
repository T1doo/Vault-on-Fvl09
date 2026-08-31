import unittest

from controlled_multi_future.gpu_parallel_policy_v2 import (
    validate_current_gpu_authorization,
)
from controlled_multi_future.post_stage0_f3_scope_v1 import (
    SCOPE,
    post_stage0_f3_budget_v1,
    post_stage0_f3_parent_authorization_v1,
    post_stage0_f3_planned_spec_v1,
    post_stage0_f3_scope_publication_v1,
)


class PostStage0F3ScopeV1Tests(unittest.TestCase):
    def test_budget_is_one_shot_gpu0_to_7_and_no_suffix(self):
        budget = post_stage0_f3_budget_v1()
        self.assertEqual(budget["allowed_physical_gpu_indices"], list(range(8)))
        self.assertEqual(budget["execution_limit"], 3)
        self.assertEqual(budget["fresh_scene_limit"], 3)
        self.assertEqual(budget["suffix_planner_query_limit"], 0)
        self.assertEqual(budget["suffix_execution_limit"], 0)
        self.assertEqual(budget["recovery_attempts"], 0)
        self.assertFalse(budget["stage0_authorized"])
        self.assertFalse(budget["stage1_authorized"])

    def test_planned_spec_binds_repair_and_three_contexts(self):
        planned = post_stage0_f3_planned_spec_v1()
        self.assertEqual(planned["scope"], SCOPE)
        self.assertEqual(
            planned["repair_contract"]["close_normalized_target"], 0.35
        )
        self.assertEqual(
            planned["diagnostic_contract"]["fresh_scene_count"], 3
        )
        self.assertEqual(
            planned["diagnostic_contract"]["suffix_planner_query_count"], 0
        )
        self.assertEqual(planned["diagnostic_contract"]["accepted_root_increment"], 0)

    def test_parent_and_publication_keep_stage0_sealed(self):
        parent = post_stage0_f3_parent_authorization_v1()
        self.assertTrue(parent["approved"])
        self.assertFalse(parent["stage0_reopened"])
        self.assertFalse(parent["formal_collection_authorized"])
        publication = post_stage0_f3_scope_publication_v1()
        self.assertTrue(publication["stage0_seal_unchanged"])

    def test_current_gpu_policy_rejects_gpu0_only(self):
        parent = post_stage0_f3_parent_authorization_v1()
        policy_fields = {
            "gpu_policy_version": "cmf_gpu_parallel_policy_v2",
            "allowed_physical_gpu_indices": parent[
                "allowed_physical_gpu_indices"
            ],
            "dynamic_fresh_idle_selection": True,
            "parallel_different_cards_authorized": True,
            "one_project_job_per_gpu": True,
            "one_root_one_gpu": True,
            "root_sharding_authorized": False,
            "share_busy_gpu_authorized": False,
            "atomic_guard_recheck_before_launch": True,
            "automatic_gpu0_fallback": False,
        }
        validate_current_gpu_authorization(policy_fields)
        policy_fields["allowed_physical_gpu_indices"] = [0]
        with self.assertRaises(ValueError):
            validate_current_gpu_authorization(policy_fields)


if __name__ == "__main__":
    unittest.main()
