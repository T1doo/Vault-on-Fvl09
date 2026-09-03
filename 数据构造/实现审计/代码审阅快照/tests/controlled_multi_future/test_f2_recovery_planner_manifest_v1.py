import unittest

from controlled_multi_future.f2_recovery_planner_manifest_v1 import (
    build_f2_recovery_planner_manifest_v1,
    build_f2_recovery_stage_a_spec_v1,
)
from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1 import (
    RUNNER_SYMBOLS,
    build_production_scene_bridge_plan_v2_3_1,
)


class F2RecoveryPlannerManifestV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = build_f2_recovery_planner_manifest_v1()

    def test_two_pairs_four_strata_and_exact_budget(self):
        self.assertEqual(self.manifest["recipe_count"], 128)
        self.assertEqual(self.manifest["maximum_stage_a_queries"], 384)
        self.assertEqual(
            [item["pair_id"] for item in self.manifest["pair_order"]],
            ["can0-box2", "can5-box8"],
        )
        self.assertEqual(len(self.manifest["stratum_order"]), 4)
        self.assertEqual(self.manifest["maximum_physical_survivors"], 4)

    def test_each_pair_and_arm_builds_exact_stage_a_and_scene_bridge(self):
        for pair_id in ("can0-box2", "can5-box8"):
            for arm in ("left", "right"):
                entry = next(
                    item
                    for item in self.manifest["ordered_recipes"]
                    if item["pair_id"] == pair_id
                    and item["recipe"]["arm"] == arm
                )
                spec = build_f2_recovery_stage_a_spec_v1(
                    self.manifest,
                    entry,
                    slot_id=f"{pair_id}-{arm}",
                    planner_reset_nonce=101,
                )
                self.assertEqual(spec["binding"]["selected_execution_arm"], arm)
                auth = {
                    "job_kind": "F2_STAGE_A",
                    "runner_symbol": RUNNER_SYMBOLS["F2_STAGE_A"],
                    "job_spec": {
                        "job_id": f"{pair_id}-{arm}",
                        "planner_reset_nonce": 101,
                        "manifest_entry": entry,
                        "manifest_sha256": self.manifest["manifest_sha256"],
                        "manifest_context": {
                            "certificates_by_pair": self.manifest[
                                "certificates_by_pair"
                            ],
                            "bindings_by_pair_and_arm": self.manifest[
                                "bindings_by_pair_and_arm"
                            ],
                        },
                    },
                }
                bridge = build_production_scene_bridge_plan_v2_3_1(auth)
                self.assertEqual(
                    bridge["runner_spec"]["recipe_sha256"],
                    entry["recipe_sha256"],
                )
                self.assertEqual(
                    bridge["legacy_scene_spec"]["f2_asset_layout_binding_v3"][
                        "selected_candidate_key"
                    ]["main_object_model_id"],
                    entry["recipe"]["main_object_model_id"],
                )


if __name__ == "__main__":
    unittest.main()
