import unittest

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f1_batch_generation_pilot_v1 import (
    PROGRAM_IDS,
    build_f1_batch_pilot_plan_v1,
    validate_f1_batch_pilot_plan_v1,
)
from controlled_multi_future.real_sapien_adapter_f1_batch_v1 import (
    RoboTwinRealSapienF1BatchPilotAdapterV1,
)


class F1BatchGenerationPilotV1Test(unittest.TestCase):
    def test_frozen_plan_has_five_primary_and_ordered_reserves(self):
        plan = build_f1_batch_pilot_plan_v1()
        self.assertTrue(validate_f1_batch_pilot_plan_v1(plan)["pass"])
        self.assertEqual(len(plan["primary_slots"]), 5)
        self.assertEqual(len(plan["ordered_reserve_slots"]), 5)
        self.assertEqual(plan["target_trajectory_count"], 15)

    def test_primary_roots_rotate_layout_and_display_order(self):
        roots = build_f1_batch_pilot_plan_v1()["primary_slots"]
        self.assertEqual(len({item["scene_layout_sha256"] for item in roots}), 5)
        self.assertEqual(
            len({item["candidate_display_order_sha256"] for item in roots}), 5
        )
        for item in roots:
            self.assertEqual(set(item["candidate_display_order"]), set(PROGRAM_IDS))
            self.assertEqual(
                item["scene_layout_sha256"], item["scene_layout"]["layout_sha256"]
            )

    def test_tamper_fails_closed(self):
        plan = build_f1_batch_pilot_plan_v1()
        plan["primary_slots"][0]["candidate_display_order"].reverse()
        self.assertFalse(validate_f1_batch_pilot_plan_v1(plan)["pass"])

    def test_adapter_reorders_semantics_without_mutating_programs(self):
        adapter = object.__new__(RoboTwinRealSapienF1BatchPilotAdapterV1)
        scene = type("Scene", (), {})()
        scene._cmf_planned_root_slot_spec = {
            "candidate_display_order": ["F1-blue", "F1-red", "F1-green"]
        }
        programs = adapter.build_programs(scene)
        self.assertEqual(
            [item["program_id"] for item in programs],
            ["F1-blue", "F1-red", "F1-green"],
        )
        self.assertEqual(hash_json(programs[0]), hash_json(next(
            item for item in programs if item["program_id"] == "F1-blue"
        )))


if __name__ == "__main__":
    unittest.main()
