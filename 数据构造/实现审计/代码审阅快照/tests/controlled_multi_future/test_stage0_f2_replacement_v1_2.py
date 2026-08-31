import copy
import inspect
import unittest

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f2_frozen_scene_layout_binding_v1 import (
    build_f2_frozen_scene_layout_binding_v1,
    legacy_f2_layout_core,
    validate_f2_frozen_scene_layout_binding_v1,
)
from controlled_multi_future.f2_mutually_exclusive_region_layout_v2 import (
    LAYOUT as F2_LAYOUT_V2,
)
from controlled_multi_future.gpu_parallel_policy_v2 import (
    validate_current_gpu_authorization,
)
from controlled_multi_future.stage0_f2_replacement_manifest_v1_2 import (
    ORIGINAL_ATTEMPT_IDS,
    PROGRAM_IDS,
    REPLACEMENT_ATTEMPT_IDS,
    SCOPE,
    build_stage0_f2_replacement_manifest_v1_2,
    f2_replacement_budget_v1_2,
    planned_f2_replacement_root_spec_v1_2,
    validate_stage0_f2_replacement_manifest_v1_2,
)
from controlled_multi_future.stage0_f2_replacement_scope_bundle_v1_2 import (
    build_parent_user_authorization_v1_2,
)
from controlled_multi_future.stage0_smoke_finalizer_v1_2 import (
    build_stage0_terminal_seal_v1_2,
)
from controlled_multi_future.probes import gpu_guard_v2_1, gpu_guard_v2_4


class Stage0F2ReplacementV1_2Test(unittest.TestCase):
    def test_binding_carries_role_explicit_and_legacy_layout(self):
        binding = build_f2_frozen_scene_layout_binding_v1()
        checked = validate_f2_frozen_scene_layout_binding_v1(binding)
        layout = checked["scene_layout"]
        for key in (
            "main_object_pose",
            "plastic_box_pose",
            "electronic_scale_pose",
            "beside_reference_pose",
            "distractor_poses",
            "obstacle_pose",
        ):
            self.assertIn(key, layout)
        self.assertEqual(legacy_f2_layout_core(layout), F2_LAYOUT_V2)
        self.assertEqual(checked["layout_payload_sha256"], hash_json(layout))
        self.assertEqual(checked["execution_arm"], "left")

    def test_binding_tamper_is_rejected(self):
        value = build_f2_frozen_scene_layout_binding_v1()
        value["scene_layout"]["box_xyz"][0] += 0.01
        with self.assertRaisesRegex(ValueError, "binding changed"):
            validate_f2_frozen_scene_layout_binding_v1(value)

    def test_replacement_spec_preserves_program_object_arm_seed(self):
        spec = planned_f2_replacement_root_spec_v1_2()
        self.assertEqual(spec["scope"], SCOPE)
        self.assertEqual(spec["seed"], 20260829)
        self.assertEqual(spec["program_ids"], list(PROGRAM_IDS))
        self.assertEqual(spec["main_object"], "071_can/base1")
        self.assertEqual(spec["execution_arm"], "left")
        self.assertEqual(spec["stage0_attempt_ids"], list(REPLACEMENT_ATTEMPT_IDS))
        self.assertEqual(spec["replacement_for_attempt_ids"], list(ORIGINAL_ATTEMPT_IDS))
        payload = dict(spec)
        digest = payload.pop("planned_root_slot_spec_sha256")
        self.assertEqual(hash_json(payload), digest)

    def test_manifest_has_twelve_active_slots_and_fifteen_history(self):
        value = build_stage0_f2_replacement_manifest_v1_2()
        checked = validate_stage0_f2_replacement_manifest_v1_2(value)
        self.assertEqual(checked["active_stage0_slot_count_after_replacement"], 12)
        self.assertEqual(checked["historical_terminal_attempt_count_retained"], 15)
        self.assertFalse(checked["original_f2_attempts_deleted"])
        self.assertFalse(checked["original_f2_attempts_overwritten"])
        self.assertEqual(len(checked["replacement_attempts"]), 3)
        self.assertEqual(
            [item["replacement_for_attempt_id"] for item in checked["replacement_attempts"]],
            list(ORIGINAL_ATTEMPT_IDS),
        )

    def test_manifest_explicitly_refuses_false_current_equivalence_claim(self):
        value = build_stage0_f2_replacement_manifest_v1_2()
        self.assertEqual(
            value["original_attempt_current_comparability"],
            "not_comparable_due_to_missing_layout_binding_and_default_layout_drift",
        )
        self.assertIn("runtime_v3_4_1", value["intended_layout_lineage_source"])

    def test_budget_is_exactly_three_no_retry_and_gpu0_7(self):
        budget = f2_replacement_budget_v1_2()
        self.assertEqual(budget["attempts"], 3)
        self.assertEqual(budget["attempts_per_program"], 1)
        self.assertFalse(budget["automatic_retry"])
        self.assertEqual(budget["recovery_attempts"], 0)
        self.assertEqual(budget["allowed_physical_gpu_indices"], list(range(8)))

    def test_parent_authorization_does_not_authorize_stage1(self):
        parent = build_parent_user_authorization_v1_2()
        self.assertTrue(parent["approved"])
        self.assertEqual(parent["attempts"], 3)
        self.assertFalse(parent["stage1_authorized"])
        self.assertFalse(parent["formal_collection_authorized"])
        self.assertFalse(parent["training_authorized"])
        payload = dict(parent)
        digest = payload.pop("parent_user_authorization_sha256")
        self.assertEqual(hash_json(payload), digest)

    def test_gpu_policy_validator_rejects_gpu0_only_parent(self):
        policy = {
            "gpu_policy_version": "cmf_gpu_parallel_policy_v2",
            "allowed_physical_gpu_indices": list(range(8)),
            "dynamic_fresh_idle_selection": True,
            "parallel_different_cards_authorized": True,
            "one_project_job_per_gpu": True,
            "one_root_one_gpu": True,
            "root_sharding_authorized": False,
            "share_busy_gpu_authorized": False,
            "atomic_guard_recheck_before_launch": True,
            "automatic_gpu0_fallback": False,
        }
        validate_current_gpu_authorization(policy)
        restricted = copy.deepcopy(policy)
        restricted["allowed_physical_gpu_indices"] = [0]
        with self.assertRaises(ValueError):
            validate_current_gpu_authorization(restricted)

    def test_guard_dispatch_and_child_seal_cover_v1_2(self):
        guard_source = inspect.getsource(gpu_guard_v2_4)
        updater_source = inspect.getsource(gpu_guard_v2_1)
        self.assertIn("controlled_multi_future_stage0_smoke_v1_2", guard_source)
        self.assertIn("load_stage0_f2_replacement_authorization_v1_2", guard_source)
        self.assertIn(
            "cmf_stage0_f2_replacement_guarded_scope_receipt_v1_2",
            updater_source,
        )

    def test_terminal_seal_distinguishes_completed_with_failure(self):
        result = {
            "stage0_completed": True,
            "stage0_outcome": "STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE",
            "active_stage0_slot_count": 12,
            "historical_terminal_attempt_count": 15,
            "stage1_authorized": False,
        }
        result["receipt_sha256"] = hash_json(result)
        seal = build_stage0_terminal_seal_v1_2(result)
        self.assertTrue(seal["stage0_completed"])
        self.assertEqual(
            seal["stage0_outcome"], "STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE"
        )
        self.assertTrue(seal["sealed_no_reopen_or_overwrite"])
        self.assertFalse(seal["stage1_authorized"])


if __name__ == "__main__":
    unittest.main()
