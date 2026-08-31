import copy
import tempfile
import unittest
from pathlib import Path

from controlled_multi_future.f3_common_grasp_prefix_v2 import (
    PROGRAM_IDS,
    build_f3_common_grasp_prefix_v2,
)
from controlled_multi_future.f3_common_grasp_prefix_v2_1 import (
    BINDING_FIELD,
    build_f3_common_grasp_prefix_binding_v2_1,
    build_f3_common_grasp_prefix_context_binding_v2_1,
    validate_bound_f3_common_grasp_prefix_v2_1,
)
from controlled_multi_future.f3_contact_preserving_prefix_v11 import (
    build_f3_contact_preserving_prefix_contract_v11,
)
from controlled_multi_future.f3_shared_prefix_no_suffix_diagnostic_v1_1 import (
    F3SharedPrefixNoSuffixDiagnosticV1_1,
    finalize_f3_common_grasp_prefix_no_suffix_diagnostic_v2_1,
)
from controlled_multi_future.family_runners_v3_3 import F3ControllerV3_3
from controlled_multi_future.families.f3_motion_order import F3MotionOrder
from test_root_orchestrator_v1_2 import StrictPrefixSyntheticAdapter


class _Adapter:
    family = "F3"

    def __init__(self):
        self.controller_v3_3 = F3ControllerV3_3()
        self.controller_v3_3.f3_common_grasp_prefix_v2 = (
            build_f3_common_grasp_prefix_v2()
        )


class _FullSyntheticAdapter(StrictPrefixSyntheticAdapter):
    family = "F3"

    def __init__(self):
        super().__init__()
        self.controller_v3_3 = F3ControllerV3_3()
        self.controller_v3_3.f3_common_grasp_prefix_v2 = (
            build_f3_common_grasp_prefix_v2()
        )

    def build_programs(self, scene):
        return F3MotionOrder().checked_provisional_programs()

    def canonical_prefix_contract(self, programs):
        return self.controller_v3_3.canonical_prefix_contract(programs)


def _contexts(binding):
    values = []
    for index, program_id in enumerate(PROGRAM_IDS):
        values.append(
            {
                "program_id": program_id,
                "execution_mode": "reference_generation" if index == 0 else "exact_replay",
                "pass": True,
                "scene_instance_id": f"scene-{index}",
                "executed_prefix_action_sha256": "a" * 64,
                "repair_binding": copy.deepcopy(binding),
                "suffix_planner_query_count": 0,
                "suffix_executed": False,
                "release_executed": False,
                "diagnostic_nonroot": True,
            }
        )
    return values


def _cleanups():
    return [
        {
            "scene_instance_id": f"scene-{index}",
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }
        for index in range(3)
    ]


class F3CommonGraspPrefixV2_1Tests(unittest.TestCase):
    def setUp(self):
        self.contract = build_f3_common_grasp_prefix_v2()
        controller = F3ControllerV3_3()
        controller.f3_common_grasp_prefix_v2 = self.contract
        self.prefix_contract = controller.canonical_prefix_contract([])

    def test_constructor_to_prefix_binding_is_exact_and_physical_contract_unchanged(self):
        diagnostic = F3SharedPrefixNoSuffixDiagnosticV1_1(_Adapter())
        validation = diagnostic._validate_prefix_contract(self.prefix_contract)
        self.assertEqual(validation["binding"]["binding_field"], BINDING_FIELD)
        self.assertEqual(
            validation["binding"]["contract_sha256"], self.contract["contract_sha256"]
        )
        self.assertTrue(validation["binding"]["physical_contract_unchanged"])
        self.assertEqual(self.contract["close_normalized_target"], 0.50)
        self.assertEqual(self.contract["post_close_settle_frames"], 250)
        self.assertEqual(self.contract["program_ids"], list(PROGRAM_IDS))
        self.assertEqual(self.contract["invariants"]["official_contact_point_id"], 0)
        self.assertEqual(self.contract["invariants"]["rotation_candidate_index"], 0)

    def test_missing_mutated_or_mixed_binding_fails_closed(self):
        missing = dict(self.prefix_contract)
        missing.pop(BINDING_FIELD)
        with self.assertRaisesRegex(ValueError, "binding is missing"):
            validate_bound_f3_common_grasp_prefix_v2_1(
                missing, expected_contract=self.contract
            )
        mutated = copy.deepcopy(self.prefix_contract)
        mutated[BINDING_FIELD]["close_normalized_target"] = 0.49
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_bound_f3_common_grasp_prefix_v2_1(
                mutated, expected_contract=self.contract
            )
        mixed = copy.deepcopy(self.prefix_contract)
        mixed["shared_prefix_repair_v11"] = (
            build_f3_contact_preserving_prefix_contract_v11()
        )
        with self.assertRaisesRegex(ValueError, "cannot coexist"):
            validate_bound_f3_common_grasp_prefix_v2_1(
                mixed, expected_contract=self.contract
            )
        missing_constructor = _Adapter()
        del missing_constructor.controller_v3_3.f3_common_grasp_prefix_v2
        with self.assertRaisesRegex(ValueError, "constructor contract"):
            F3SharedPrefixNoSuffixDiagnosticV1_1(missing_constructor)

    def test_reference_callback_advances_past_historical_binding_check(self):
        class Sentinel(RuntimeError):
            pass

        class Adapter(_Adapter):
            def capture_current(self, scene):
                return {"aggregate_sha256": "1" * 64}

            def capture_anchor(self, scene):
                return {"anchor_sha256": "2" * 64}

            def build_programs(self, scene):
                return F3MotionOrder().checked_provisional_programs()

            def canonical_prefix_contract(self, programs):
                return self.controller_v3_3.canonical_prefix_contract(programs)

            def plan_and_execute_canonical_prefix(self, scene, prefix_contract):
                raise Sentinel("planner sentinel after V2_1 binding")

        class Scene:
            planner_query_count = 0

            @staticmethod
            def save_trace(path):
                Path(path).write_bytes(b"partial")
                return {"bytes": 7}

        diagnostic = F3SharedPrefixNoSuffixDiagnosticV1_1(Adapter())
        scene = Scene()

        def scene_call(**kwargs):
            return kwargs["callback"](scene, kwargs.get("program"))

        diagnostic.helper._scene_call = scene_call
        with tempfile.TemporaryDirectory() as temporary:
            result = diagnostic.run(
                output_dir=Path(temporary) / "diagnostic",
                planned_root_slot_spec={
                    "slot_id": "v2-1-cpu",
                    "family": "F3",
                    "seed": 20260829,
                },
            )
        self.assertEqual(result["execution_attempt_count"], 1)
        self.assertEqual(result["error_type"], "Sentinel")
        self.assertEqual(result["error"], "planner sentinel after V2_1 binding")
        self.assertNotIn("not bound", result["error"])

    def test_three_scene_receipt_binding_reaches_v2_1_finalizer(self):
        validation = validate_bound_f3_common_grasp_prefix_v2_1(
            self.prefix_contract, expected_contract=self.contract
        )
        context_binding = build_f3_common_grasp_prefix_context_binding_v2_1(
            validation, artifact_sha256="b" * 64
        )
        expected = build_f3_common_grasp_prefix_binding_v2_1(self.contract)
        result = finalize_f3_common_grasp_prefix_no_suffix_diagnostic_v2_1(
            _contexts(context_binding),
            cleanup_records=_cleanups(),
            expected_binding=expected,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["repair_binding"]["contract_version"], "F3CommonGraspPrefixV2")
        self.assertNotIn("f3_contact_preserving_partial_close_v11", str(result))

    def test_full_synthetic_reference_and_two_fresh_replays(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = F3SharedPrefixNoSuffixDiagnosticV1_1(
                _FullSyntheticAdapter()
            ).run(
                output_dir=Path(temporary) / "diagnostic",
                planned_root_slot_spec={
                    "slot_id": "v2-1-full-cpu",
                    "family": "F3",
                    "seed": 20260829,
                },
            )
        self.assertTrue(result["pass"], result.get("error"))
        self.assertEqual(result["execution_attempt_count"], 3)
        self.assertEqual(len(result["contexts"]), 3)
        self.assertEqual(len(result["cleanup_records"]), 3)
        self.assertEqual(result["suffix_planner_query_count"], 0)
        bindings = [item["repair_binding"] for item in result["contexts"]]
        self.assertEqual(bindings[0], bindings[1])
        self.assertEqual(bindings[1], bindings[2])
        self.assertTrue(result["finalizer"]["checks"]["all_contexts_match_constructor_binding"])

    def test_finalizer_rejects_missing_or_different_scene_binding(self):
        validation = validate_bound_f3_common_grasp_prefix_v2_1(
            self.prefix_contract, expected_contract=self.contract
        )
        context_binding = build_f3_common_grasp_prefix_context_binding_v2_1(
            validation, artifact_sha256="b" * 64
        )
        expected = build_f3_common_grasp_prefix_binding_v2_1(self.contract)
        contexts = _contexts(context_binding)
        contexts[1].pop("repair_binding")
        self.assertFalse(
            finalize_f3_common_grasp_prefix_no_suffix_diagnostic_v2_1(
                contexts, cleanup_records=_cleanups(), expected_binding=expected
            )["pass"]
        )
        contexts = _contexts(context_binding)
        contexts[2]["repair_binding"]["artifact_sha256"] = "c" * 64
        self.assertFalse(
            finalize_f3_common_grasp_prefix_no_suffix_diagnostic_v2_1(
                contexts, cleanup_records=_cleanups(), expected_binding=expected
            )["pass"]
        )
        contexts = _contexts(context_binding)
        binding = contexts[0]["repair_binding"]
        binding.pop("artifact_sha256")
        payload = dict(binding)
        payload.pop("context_binding_sha256")
        from controlled_multi_future.current_hasher import hash_json

        binding["context_binding_sha256"] = hash_json(payload)
        self.assertFalse(
            finalize_f3_common_grasp_prefix_no_suffix_diagnostic_v2_1(
                contexts, cleanup_records=_cleanups(), expected_binding=expected
            )["pass"]
        )


if __name__ == "__main__":
    unittest.main()
