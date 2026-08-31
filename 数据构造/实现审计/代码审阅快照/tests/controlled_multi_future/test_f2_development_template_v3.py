import hashlib
import json
import unittest

from controlled_multi_future.f2_asset_geometry_layout_v3 import (
    evaluate_strict_full_envelope_inside_v3,
)
from controlled_multi_future.f2_development_template_v3 import (
    F2AssetBoundDevelopmentAdapterV3,
    F2OneDevelopmentRootRunnerV3,
    SCOPE,
    build_f2_development_scope_v3,
    f2_development_budget_v3,
    guard_dispatch_descriptor_v3,
)
from controlled_multi_future.f2_dynamic_search_contract_v3 import (
    build_cpu_static_screening_v3,
    build_dynamic_selected_asset_layout_binding_v3,
)
from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    REQUIRED_GATE_IDS,
    apply_gate_receipts_v3,
    build_gate_receipt_v3,
    build_static_compatibility_matrix_v3,
)


def hash_json(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class F2DevelopmentTemplateV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = build_static_compatibility_matrix_v3()
        cls.screening = build_cpu_static_screening_v3(cls.matrix)
        rank = cls.screening["dynamic_scope"]["candidates"][0]["rank"]
        cls.row = cls.matrix["rows"][rank]
        cls.layout = {"layout_version": "f2_test_selected_layout_v3", "poses": {}}
        inside = evaluate_strict_full_envelope_inside_v3(cls.row)
        receipts = []
        predecessor = None
        for gate_id in REQUIRED_GATE_IDS:
            if gate_id == "strict_full_object_inside_margin":
                evidence = inside
            else:
                evidence = {"runtime_or_complete_geometry_evidence": True}
                if gate_id == "on_passive_stability":
                    evidence.update(
                        passive_250hz_settle_verified=True,
                        continuous_scale_support=True,
                        stable_window_pass=True,
                    )
                elif gate_id == "beside_mutual_exclusion":
                    evidence.update(
                        asset_derived_predicates=True,
                        zero_overlap=True,
                        table_clearance_pass=True,
                    )
                elif gate_id == "asset_derived_scene_layout":
                    evidence.update(
                        fresh_scene_layout_realized=True,
                        facility_clearance_pass=True,
                        layout_payload_sha256=hash_json(cls.layout),
                    )
                else:
                    evidence.update(
                        selected_execution_arm="left",
                        program_ids=list(PROGRAM_IDS),
                        same_start_qpos_and_seed=True,
                        complete_planner_chains=True,
                        same_main_object_for_all_programs=True,
                        same_execution_arm_for_all_programs=True,
                    )
            receipts.append(
                build_gate_receipt_v3(
                    cls.row,
                    gate_id=gate_id,
                    status="passed",
                    evidence=evidence,
                    predecessor_gate_receipt_sha256=predecessor,
                )
            )
            predecessor = receipts[-1]["gate_receipt_sha256"]
        cls.evaluated = apply_gate_receipts_v3(cls.row, receipts)
        cls.binding = build_dynamic_selected_asset_layout_binding_v3(
            screening=cls.screening,
            evaluated_rows=[cls.evaluated],
            selected_execution_arm="left",
            layout_payload=cls.layout,
        )

    def authorization(self):
        budget = f2_development_budget_v3()
        value = {
            "schema_version": "cmf_f2_one_development_root_authorization_v3",
            "scope": SCOPE,
            "output_namespace": "post_stage0_f2_asset_redesign_v3_one_root_run1",
            "selected_binding_sha256": self.binding["binding_sha256"],
            "single_use": True,
            "automatic_retry": False,
            "maximum_recovery_attempts": 0,
            "maximum_development_root_count": 1,
            "maximum_branch_execution_attempts": 3,
            "gpu_policy_version": "cmf_gpu_parallel_policy_v2",
            "allowed_physical_gpu_indices": list(range(8)),
            "one_project_job_per_gpu": True,
            "one_root_one_gpu": True,
            "root_sharding_authorized": False,
            "source_lock_sha256": "a" * 64,
            "approved": True,
            "budget": budget,
            "budget_sha256": hash_json(budget),
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        value["authorization_sha256"] = hash_json(value)
        return value

    def guard_context(self, authorization):
        return {
            "schema_version": "cmf_f2_guard_launch_context_v3",
            "scope": SCOPE,
            "authorization_sha256": authorization["authorization_sha256"],
            "selected_binding_sha256": self.binding["binding_sha256"],
            "atomic_fresh_idle_recheck_pass": True,
            "physical_gpu_uuid": "GPU-test-f2-v3",
            "physical_gpu_index": 4,
            "per_gpu_lease_acquired": True,
            "source_lock_sha256": authorization["source_lock_sha256"],
        }

    def test_scope_budget_and_dispatch_descriptor_are_bounded(self):
        scope = build_f2_development_scope_v3(self.binding)
        budget = scope["budget"]
        self.assertEqual(budget["maximum_dynamic_candidate_count"], 12)
        self.assertEqual(budget["maximum_development_root_count"], 1)
        self.assertEqual(budget["maximum_branch_execution_attempts"], 3)
        self.assertFalse(budget["automatic_retry"])
        self.assertEqual(budget["allowed_physical_gpu_indices"], list(range(8)))
        self.assertFalse(scope["guard_dispatch_integrated"])
        descriptor = guard_dispatch_descriptor_v3()
        self.assertFalse(descriptor["shared_guard_dispatch_integrated"])
        self.assertTrue(descriptor["must_preserve_f3_v2_1_dispatch"])

    def test_adapter_requires_scene_to_expose_exact_binding_identity(self):
        class Scene:
            pass

        def factory(program_id, binding):
            scene = Scene()
            scene.f2_asset_binding_identity = {
                "binding_sha256": binding["binding_sha256"],
                "main_object_model_id": binding["selected_candidate_key"][
                    "main_object_model_id"
                ],
                "execution_arm": binding["selected_execution_arm"],
            }
            return scene

        adapter = F2AssetBoundDevelopmentAdapterV3(
            binding=self.binding, scene_factory=factory
        )
        self.assertIsInstance(adapter.scene("F2-inside"), Scene)
        with self.assertRaisesRegex(ValueError, "unknown program"):
            adapter.scene("F2-not-a-program")

    def test_exactly_one_three_branch_root_keeps_object_arm_and_lineage(self):
        authorization = self.authorization()
        runner = F2OneDevelopmentRootRunnerV3(
            binding=self.binding,
            authorization=authorization,
            guard_context=self.guard_context(authorization),
        )
        common = {
            "current_sha256": "1" * 64,
            "anchor_sha256": "2" * 64,
            "canonical_prefix_sha256": "3" * 64,
        }

        def execute(program_id, binding):
            return {
                "program_id": program_id,
                "main_object_modelname": "071_can",
                "main_object_model_id": binding["selected_candidate_key"][
                    "main_object_model_id"
                ],
                "execution_arm": binding["selected_execution_arm"],
                "selected_binding_sha256": binding["binding_sha256"],
                "status": "accepted",
                "verifier_pass": True,
                "release_chain_unchanged": True,
                "verifier_unchanged": True,
                "formal_data": False,
                "stage0_data": False,
                "stage1_authorized": False,
                "execution_attempt_count": 1,
                "recovery_attempt_count": 0,
                "planner_query_count": 5,
                "fresh_scene": True,
                **common,
            }

        receipt = runner.run(execute)
        self.assertEqual(receipt["program_ids"], list(PROGRAM_IDS))
        self.assertEqual(receipt["branch_count"], 3)
        self.assertTrue(receipt["all_branches_accepted"])
        with self.assertRaisesRegex(RuntimeError, "single-use"):
            runner.run(execute)

    def test_branch_specific_object_change_fails_closed(self):
        authorization = self.authorization()
        runner = F2OneDevelopmentRootRunnerV3(
            binding=self.binding,
            authorization=authorization,
            guard_context=self.guard_context(authorization),
        )

        def execute(program_id, binding):
            return {
                "program_id": program_id,
                "main_object_modelname": "071_can",
                "main_object_model_id": 999,
                "execution_arm": binding["selected_execution_arm"],
                "selected_binding_sha256": binding["binding_sha256"],
                "status": "accepted",
                "verifier_pass": True,
                "release_chain_unchanged": True,
                "verifier_unchanged": True,
                "formal_data": False,
                "stage0_data": False,
                "stage1_authorized": False,
                "execution_attempt_count": 1,
                "recovery_attempt_count": 0,
                "planner_query_count": 5,
                "fresh_scene": True,
                "current_sha256": "1" * 64,
                "anchor_sha256": "2" * 64,
                "canonical_prefix_sha256": "3" * 64,
            }

        with self.assertRaisesRegex(ValueError, "frozen identity"):
            runner.run(execute)


if __name__ == "__main__":
    unittest.main()
