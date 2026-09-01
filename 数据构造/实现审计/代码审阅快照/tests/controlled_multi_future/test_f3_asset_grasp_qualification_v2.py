import copy
import unittest

from controlled_multi_future.f3_asset_grasp_qualification_v2 import (
    MAXIMUM_GRASP_TUPLES,
    MAXIMUM_PHYSICAL_TUPLES,
    MAXIMUM_SELECTED_ASSETS,
    REQUIRED_LEVEL2_GATES,
    build_f3_asset_grasp_qualification_v2,
    build_official_bottle_inventory_v2,
    select_level2_tuples_v2,
    select_stable_grasp_v2,
    validate_f3_asset_grasp_qualification_v2,
)


class F3AssetGraspQualificationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_f3_asset_grasp_qualification_v2()

    def test_inventory_is_complete_and_honest_about_missing_physics_metadata(self):
        inventory = build_official_bottle_inventory_v2()
        self.assertEqual(inventory["model_ids"], list(range(23)))
        self.assertEqual(inventory["model_count"], 23)
        self.assertTrue(
            all(record["model_data_mass_available"] is False for record in inventory["records"])
        )
        self.assertTrue(
            all(record["lower_center_of_mass_claim_allowed"] is False for record in inventory["records"])
        )

    def test_four_assets_and_eight_genuinely_distinct_grasp_tuples_are_frozen(self):
        self.assertEqual(
            len(self.contract["selected_assets"]), MAXIMUM_SELECTED_ASSETS
        )
        self.assertEqual(len(self.contract["grasp_tuples"]), MAXIMUM_GRASP_TUPLES)
        self.assertEqual(
            len(set(self.contract["selected_asset_model_ids"])),
            MAXIMUM_SELECTED_ASSETS,
        )
        for model_id in self.contract["selected_asset_model_ids"]:
            tuples = [
                item
                for item in self.contract["grasp_tuples"]
                if item["asset"]["model_id"] == model_id
            ]
            self.assertEqual(len(tuples), 2)
            self.assertEqual({item["grasp_region"] for item in tuples}, {"lower_body", "upper_body"})
            self.assertEqual({item["arm"] for item in tuples}, {"left", "right"})

    def test_protocol_and_authorization_boundaries_are_unchanged(self):
        self.assertEqual(
            self.contract["program_ids"], ["F3-VVHH", "F3-VHVH", "F3-VHHV"]
        )
        self.assertFalse(self.contract["block_substitution_allowed"])
        self.assertFalse(self.contract["formal_data"])
        self.assertFalse(self.contract["stage0_data"])
        self.assertFalse(self.contract["stage1_authorized"])
        self.assertEqual(validate_f3_asset_grasp_qualification_v2(self.contract), self.contract)

    def test_level1_selects_at_most_four_by_frozen_rank(self):
        receipts = [
            {
                "tuple_id": item["tuple_id"],
                "tuple_sha256": item["tuple_sha256"],
                "planner_success": item["rank"] in {2, 3, 5, 6, 8},
            }
            for item in reversed(self.contract["grasp_tuples"])
        ]
        terminal = select_level2_tuples_v2(self.contract, receipts)
        self.assertEqual(
            terminal["level2_tuple_ids"],
            [
                "f3-asset-grasp-v2-r02",
                "f3-asset-grasp-v2-r03",
                "f3-asset-grasp-v2-r05",
                "f3-asset-grasp-v2-r06",
            ],
        )
        self.assertLessEqual(len(terminal["level2_tuple_ids"]), MAXIMUM_PHYSICAL_TUPLES)

    def test_level2_selects_lowest_rank_full_pass_and_tamper_fails_closed(self):
        planner = select_level2_tuples_v2(
            self.contract,
            [
                {
                    "tuple_id": item["tuple_id"],
                    "tuple_sha256": item["tuple_sha256"],
                    "planner_success": item["rank"] <= 4,
                }
                for item in self.contract["grasp_tuples"]
            ],
        )
        by_id = {item["tuple_id"]: item for item in self.contract["grasp_tuples"]}
        physical = []
        for tuple_id in reversed(planner["level2_tuple_ids"]):
            item = by_id[tuple_id]
            passed = item["rank"] in {2, 4}
            physical.append(
                {
                    "tuple_id": tuple_id,
                    "tuple_sha256": item["tuple_sha256"],
                    "gates": {name: passed for name in REQUIRED_LEVEL2_GATES},
                    "sequence_complete": True,
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        terminal = select_stable_grasp_v2(self.contract, planner, physical)
        self.assertEqual(terminal["selected_stable_grasp"]["rank"], 2)

        changed = copy.deepcopy(self.contract)
        changed["maximum_physical_tuples"] = 5
        with self.assertRaises(ValueError):
            validate_f3_asset_grasp_qualification_v2(changed)


if __name__ == "__main__":
    unittest.main()
