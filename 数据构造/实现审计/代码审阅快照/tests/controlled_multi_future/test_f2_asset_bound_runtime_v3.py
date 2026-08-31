import hashlib
import inspect
import json
from pathlib import Path
import unittest

from controlled_multi_future.f2_asset_bound_runtime_v3 import (
    F2AssetBoundControllerV3,
    _asset_bound_balanced_preload_spec_v3,
)
from controlled_multi_future.f2_dynamic_development_scope_v3 import (
    NAMESPACE,
    OUTPUT,
    SCOPE,
    f2_dynamic_development_budget_v3,
    validate_f2_dynamic_development_authorization_v3,
)
from controlled_multi_future.f2_dynamic_search_contract_v3 import (
    build_cpu_static_screening_v3,
    build_provisional_dynamic_candidate_binding_v3,
)
from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
    build_static_compatibility_matrix_v3,
)
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    _f2_active_cavity_contract,
    _f2_active_scale_support_half_xy,
)
from controlled_multi_future.probes.f2_dynamic_development_scope_runner_v3 import (
    F2DynamicThenDevelopmentRunnerV3,
)


def hash_json(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class F2AssetBoundRuntimeV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = build_static_compatibility_matrix_v3()
        cls.screening = build_cpu_static_screening_v3(cls.matrix)
        cls.provisional = build_provisional_dynamic_candidate_binding_v3(
            cls.screening, scope_index=0
        )

    def test_provisional_binding_is_planner_only_and_contains_actual_assets(self):
        binding = self.provisional
        self.assertTrue(binding["provisional_dynamic_candidate"])
        self.assertFalse(binding["selected"])
        self.assertFalse(binding["development_execution_authorized"])
        self.assertEqual(binding["dynamic_scope_index"], 0)
        self.assertIn("strict_cavity_contract", binding)
        F2AssetBoundControllerV3(binding, planner_only=True)
        with self.assertRaisesRegex(ValueError, "planner-only"):
            F2AssetBoundControllerV3(binding, planner_only=False)

    def test_historical_runtime_accessors_preserve_exact_fallback(self):
        class Scene:
            pass

        scene = Scene()
        cavity = _f2_active_cavity_contract(scene)
        self.assertEqual(cavity["coordinate_frame"], "062_plasticbox/base2 actor-local xyz")
        self.assertEqual(_f2_active_scale_support_half_xy(scene).tolist(), [0.07, 0.07])
        scene._cmf_f2_active_cavity_contract = self.provisional[
            "strict_cavity_contract"
        ]
        self.assertEqual(
            _f2_active_cavity_contract(scene)["full_envelope_evidence_sha256"],
            self.provisional["strict_cavity_contract"][
                "full_envelope_evidence_sha256"
            ],
        )

    def test_f2_scene_has_binding_path_and_unchanged_historical_fallback(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "controlled_multi_future/probes/scene_inspection.py"
        ).read_text(encoding="utf-8")
        self.assertIn('planned.get("f2_asset_layout_binding_v3")', source)
        self.assertIn('can_id = 1', source)
        self.assertIn('scale_model_id = 0', source)
        self.assertIn('stand_model_id = 3', source)
        self.assertIn('planned.get("plasticbox_model_id", 2)', source)

    def test_planner_only_gate_stops_before_execution_but_retains_pass_evidence(self):
        controller = F2AssetBoundControllerV3(
            self.provisional, planner_only=True
        )
        receipts = [
            {
                "program_id": program_id,
                "planner_solvable": True,
                "actual_prefix_end_qpos_sha256": str(index) * 64,
            }
            for index, program_id in enumerate(
                ("F2-inside", "F2-on", "F2-beside"), start=1
            )
        ]
        gate = controller.validate_family_suffix_gate(receipts)
        self.assertTrue(gate["all_three_complete_planner_chains_pass"])
        self.assertTrue(gate["intentional_stop_before_suffix_execution"])
        self.assertTrue(gate["evidence_complete"])
        self.assertFalse(gate["pass"])

    def test_asset_bound_release_keeps_v9_numeric_formula_without_base1_provenance(self):
        spec = _asset_bound_balanced_preload_spec_v3(
            self.provisional,
            actual_finger_qpos=[0.02, 0.024],
            current_drive_target=[-0.01, -0.01],
            applied_finger_qf=[1.0, -1.0],
            estimated_drive_effort=[-30.0, -31.0],
            drive_stiffness=[1000.0, 1000.0],
            drive_damping=[200.0, 200.0],
            drive_force_limit=[1e6, 1e6],
            drive_mode=["force", "force"],
        )
        self.assertEqual(spec["balanced_drive_target_m"], 0.022)
        self.assertEqual(spec["partial_open_normalized_target"], (0.022 + 0.01) / 0.055)
        self.assertEqual(spec["post_command_hold_steps"], 50)
        self.assertEqual(spec["disengagement_confirm_frames"], 10)
        self.assertFalse(spec["final_verifier_changed"])
        self.assertFalse(spec["historical_base1_failure_evidence_reused_as_asset_evidence"])
        self.assertEqual(spec["main_object"], "071_can/base0")

    def test_combined_authorization_binds_matrix_screening_budget_and_gpu_policy(self):
        budget = f2_dynamic_development_budget_v3()
        value = {
            "schema_version": "cmf_f2_dynamic_development_authorization_v3",
            "scope": SCOPE,
            "output_namespace": str(OUTPUT.resolve()),
            "matrix_sha256": self.matrix["matrix_sha256"],
            "screening_sha256": self.screening["screening_sha256"],
            "budget": budget,
            "budget_sha256": hash_json(budget),
            "approved": True,
            "source_lock_receipt_sha256": "a" * 64,
            "implementation_source_sha256": "b" * 64,
            "allowed_physical_gpu_indices": list(range(8)),
            "single_use": True,
            "automatic_retry": False,
            "one_root_one_gpu": True,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        value["receipt_sha256"] = hash_json(value)
        checked = validate_f2_dynamic_development_authorization_v3(
            value,
            matrix_sha256=self.matrix["matrix_sha256"],
            screening_sha256=self.screening["screening_sha256"],
        )
        self.assertEqual(checked["allowed_physical_gpu_indices"], list(range(8)))
        self.assertFalse(checked["automatic_retry"])

        legacy_double_hash = dict(value)
        legacy_double_hash["authorization_sha256"] = "c" * 64
        payload = dict(legacy_double_hash)
        payload.pop("receipt_sha256")
        legacy_double_hash["receipt_sha256"] = hash_json(payload)
        with self.assertRaisesRegex(ValueError, "one authoritative receipt hash"):
            validate_f2_dynamic_development_authorization_v3(
                legacy_double_hash,
                matrix_sha256=self.matrix["matrix_sha256"],
                screening_sha256=self.screening["screening_sha256"],
            )

    def test_child_source_orders_passive_planner_then_one_video_root(self):
        source = inspect.getsource(F2DynamicThenDevelopmentRunnerV3.run)
        self.assertLess(source.index("audit_passive_on_scene"), source.index("planner_only_root"))
        self.assertLess(source.index("planner_only_root"), source.index("selected_one_development_root"))
        self.assertIn("development_video_required=True", source)
        self.assertIn("build_provisional_dynamic_candidate_binding_v3", source)
        self.assertIn("build_dynamic_selected_asset_layout_binding_v3", source)


if __name__ == "__main__":
    unittest.main()
