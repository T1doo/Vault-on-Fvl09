import copy
import unittest

from controlled_multi_future.high_level_template_redesign_v1 import (
    build_high_level_template_redesign_v1,
    validate_high_level_template_redesign_v1,
)


class HighLevelTemplateRedesignV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_high_level_template_redesign_v1()

    def test_parent_binds_all_three_hierarchical_contracts(self):
        self.assertEqual(set(self.contract["family_contracts"]), {"F2", "F3", "F4"})
        self.assertTrue(
            all(
                len(item["contract_sha256"]) == 64
                for item in self.contract["family_contracts"].values()
            )
        )
        self.assertEqual(validate_high_level_template_redesign_v1(self.contract), self.contract)

    def test_f1_and_prohibited_scopes_remain_closed(self):
        self.assertEqual(self.contract["f1_reference"]["accepted_root_count"], 5)
        self.assertEqual(self.contract["f1_reference"]["accepted_trajectory_count"], 15)
        self.assertFalse(self.contract["f1_reference"]["rerun_authorized"])
        for key in (
            "stage1_authorized",
            "formal_360_authorized",
            "training_authorized",
            "h_reveal_authorized",
            "compression_authorized",
            "pi05_authorized",
        ):
            self.assertFalse(self.contract[key])

    def test_gpu_policy_is_fvl05_multi_card_guarded_contract(self):
        policy = self.contract["gpu_policy"]
        self.assertEqual(policy["allowed_physical_gpu_indices"], list(range(8)))
        self.assertTrue(policy["fresh_idle_required"])
        self.assertTrue(policy["uuid_binding_required"])
        self.assertTrue(policy["guard_lease_pre_post_cleanup_required"])
        self.assertFalse(policy["root_sharding_allowed"])
        self.assertFalse(policy["hot_patch_while_jobs_live_allowed"])

    def test_parent_tamper_fails_closed(self):
        changed = copy.deepcopy(self.contract)
        changed["stage1_authorized"] = True
        with self.assertRaises(ValueError):
            validate_high_level_template_redesign_v1(changed)


if __name__ == "__main__":
    unittest.main()
