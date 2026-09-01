import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from controlled_multi_future.canonical_artifact import canonical_hash_json

from controlled_multi_future.f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
)
from controlled_multi_future.f3_asset_grasp_qualification_v2 import (
    build_f3_asset_grasp_qualification_v2,
)
from controlled_multi_future.f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
    select_f4_stage_a_source_v1,
)
from controlled_multi_future.high_level_planner_runner_v1 import (
    HighLevelPlannerRunnerV1,
    _build_f4_prior_slot_preservation_v1,
    rederive_f4_stage_b_candidate_checks_v1,
)
from controlled_multi_future.high_level_physical_runner_v1 import (
    HighLevelPhysicalRunnerV1,
    build_f3_level2_targets_v1,
    execute_f2_inside_physical_v1,
)
from controlled_multi_future.high_level_runtime_specs_v1 import (
    build_f2_runtime_spec_v1,
    build_f3_runtime_spec_v1,
    build_f4_runtime_spec_v1,
    job_budget_v1,
    validate_f2_runtime_spec_v1,
    validate_f3_runtime_spec_v1,
    validate_f4_runtime_spec_v1,
    validate_job_budget_v1,
)
from controlled_multi_future.real_sapien_adapter_high_level_v1 import (
    RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
    RoboTwinRealSapienF3AssetGraspV2Adapter,
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
    _build_render_device_binding_receipt_v1,
    _normalize_pci_bus_id,
    _selected_nvidia_device_v1,
)


class _FakeScene:
    def __init__(self):
        self.can = object()
        self.bottle = object()
        self.a = object()
        self.b = object()
        self.c = object()
        self.planner_query_count = 0
        self.role_actors = {"main_can": self.can}
        self._cmf_render_device_binding_v1 = {"pass": True}

    def initialize_trace(self, actor, arm, role_actors=None):
        self.trace_actor = actor
        self.trace_arm = arm
        self.trace_role_actors = dict(role_actors or {})
        self.planner_query_count = 0
        self.planner_queries = []

    def save_trace(self, path):
        Path(path).write_bytes(b"fake-trace")
        return {"path": str(path), "row_count": 1}


class _FakeContext:
    def __init__(self):
        self.scene = _FakeScene()
        self.cleanup_receipt = None

    def __enter__(self):
        return type("Handle", (), {"scene": self.scene})()

    def __exit__(self, exc_type, exc, tb):
        self.cleanup_receipt = {
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }
        return False


class _FakeAdapter:
    def __init__(self, spec):
        self.planned_spec = spec
        self.context = _FakeContext()

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        if planned_root_slot_spec != self.planned_spec:
            raise ValueError("spec mismatch")
        return self.context

    def capture_current(self, scene):
        return {"current_sha256": "1" * 64}

    def audit_current_rendered_visibility(self, scene, *, phase):
        return {"phase": phase, "pass": True}


class HighLevelRuntimeSpecsAndPlannerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2 = build_f2_hierarchical_template_search_v1()
        cls.f3 = build_f3_asset_grasp_qualification_v2()
        cls.f4 = build_f4_hierarchical_template_search_v1()

    def _f4_stage_a_terminal(self):
        gates = self.f4["stage_a_required_gates"]
        return select_f4_stage_a_source_v1(
            self.f4,
            [
                {
                    "candidate_id": item["candidate_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "checks": {
                        name: item["rank"] == 1 for name in gates
                    },
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
                for item in self.f4["stage_a_candidates"]
            ],
        )

    def test_every_stage_a_spec_is_rebuildable_and_hash_bound(self):
        for candidate_id in self.f2["fixed_inside_candidate_order"]:
            spec = build_f2_runtime_spec_v1(
                candidate_id, purpose="f2_stage_a_planner"
            )
            self.assertEqual(validate_f2_runtime_spec_v1(spec), spec)
        for tuple_id in self.f3["fixed_tuple_order"]:
            spec = build_f3_runtime_spec_v1(
                tuple_id, purpose="f3_level1_planner"
            )
            self.assertEqual(validate_f3_runtime_spec_v1(spec), spec)
        for candidate_id in self.f4["fixed_stage_a_order"]:
            spec = build_f4_runtime_spec_v1(
                candidate_id, purpose="f4_stage_a_planner"
            )
            self.assertEqual(validate_f4_runtime_spec_v1(spec), spec)
        terminal = self._f4_stage_a_terminal()
        stage_b = build_f4_stage_b_candidates_v1(self.f4, terminal)
        for candidate_id in stage_b["fixed_candidate_order"]:
            spec = build_f4_runtime_spec_v1(
                candidate_id,
                purpose="f4_stage_b_planner",
                stage_a_terminal=terminal,
            )
            self.assertEqual(validate_f4_runtime_spec_v1(spec), spec)

    def test_f2_right_candidate_mirrors_positions_but_not_stage_a_rank_inputs(self):
        right = next(
            item for item in self.f2["inside_candidates"] if item["arm"] == "right"
        )
        spec = build_f2_runtime_spec_v1(
            right["candidate_id"], purpose="f2_stage_a_planner"
        )
        binding = spec["f2_asset_layout_binding_v3"]
        self.assertGreater(binding["layout_payload"]["main_object_pose_xyz"][0], 0)
        self.assertTrue(binding["right_layout_transform_is_position_x_mirror_only"])
        self.assertTrue(binding["scale_and_stand_are_fixed_inert_stage_a_scene_assets"])
        self.assertFalse(binding["scale_or_stand_used_for_stage_a_rank"])

    def test_f4_arm_specific_grasp_evidence_is_not_overclaimed(self):
        left = self.f4["stage_a_candidates"][0]
        right = next(
            item for item in self.f4["stage_a_candidates"] if item["arm"] == "right"
        )
        self.assertEqual(left["grasp_policy"]["policy"], "f1_planner_assisted_top_down_v3_3")
        self.assertTrue(left["f1_15_of_15_execution_claim_applies_to_candidate"])
        self.assertEqual(right["grasp_policy"]["policy"], "project_cube_grasp_pose_v1")
        self.assertFalse(right["f1_15_of_15_execution_claim_applies_to_candidate"])
        spec = build_f4_runtime_spec_v1(
            right["candidate_id"], purpose="f4_stage_a_planner"
        )
        self.assertFalse(spec["stage_a_slot_search_active"])
        self.assertTrue(spec["scene_layout"]["stage_a_slot_placeholders_fixed_not_searched"])

    def test_budgets_keep_gpu_and_authorization_boundaries(self):
        for purpose in (
            "f2_stage_a_planner",
            "f2_inside_physical",
            "f3_level1_planner",
            "f3_level2_physical",
            "f4_stage_a_planner",
            "f4_stage_b_planner",
        ):
            budget = job_budget_v1(purpose)
            self.assertEqual(validate_job_budget_v1(budget), budget)
            self.assertEqual(budget["allowed_physical_gpu_indices"], list(range(8)))
            self.assertFalse(budget["stage1_authorized"])
            self.assertFalse(budget["automatic_retry"])
        self.assertEqual(job_budget_v1("f4_stage_a_planner")["planner_query_limit"], 48)
        self.assertEqual(job_budget_v1("f4_stage_b_planner")["planner_query_limit"], 42)
        self.assertEqual(
            job_budget_v1("f4_stage_b_planner")["planner_query_limit"],
            3 * 4 + 30,
        )

    def test_adapter_constructors_bind_exact_specs_without_scene_creation(self):
        f2_spec = build_f2_runtime_spec_v1(
            self.f2["fixed_inside_candidate_order"][0],
            purpose="f2_stage_a_planner",
        )
        f3_spec = build_f3_runtime_spec_v1(
            self.f3["fixed_tuple_order"][0], purpose="f3_level1_planner"
        )
        f4_spec = build_f4_runtime_spec_v1(
            self.f4["fixed_stage_a_order"][0], purpose="f4_stage_a_planner"
        )
        with patch(
            "controlled_multi_future.real_sapien_adapter_v1_5."
            "RoboTwinRealSapienStrictPrefixAdapterV1_5.__init__",
            return_value=None,
        ):
            f2_adapter = RoboTwinRealSapienF2HierarchicalStageAV1Adapter(
                output_root=Path("/nfs_share/lijunhui/Robotwin2/tmp/f2-adapter-test"),
                expected_implementation_source_sha256="a" * 64,
                planned_spec=f2_spec,
            )
            f3_adapter = RoboTwinRealSapienF3AssetGraspV2Adapter(
                output_root=Path("/nfs_share/lijunhui/Robotwin2/tmp/f3-adapter-test"),
                expected_implementation_source_sha256="a" * 64,
                planned_spec=f3_spec,
            )
        with patch(
            "controlled_multi_future.real_sapien_adapter_f4_selected_layout_v2."
            "RoboTwinRealSapienF4SelectedLayoutV2Adapter.__init__",
            return_value=None,
        ):
            f4_adapter = RoboTwinRealSapienF4HierarchicalStageAV1Adapter(
                output_root=Path("/nfs_share/lijunhui/Robotwin2/tmp/f4-adapter-test"),
                expected_implementation_source_sha256="a" * 64,
                planned_spec=f4_spec,
            )
        self.assertEqual(f2_adapter.planned_spec, f2_spec)
        self.assertEqual(f3_adapter.planned_spec, f3_spec)
        self.assertEqual(f4_adapter.planned_spec, f4_spec)

    def test_render_device_binding_maps_guard_uuid_to_exact_pci(self):
        self.assertEqual(
            _normalize_pci_bus_id("00000000:61:00.0"), "0000:61:00.0"
        )
        completed = type(
            "Completed",
            (),
            {
                "stdout": (
                    "0, GPU-zero, 00000000:01:00.0\n"
                    "3, GPU-three, 00000000:61:00.0\n"
                )
            },
        )()
        with patch.dict(
            os.environ,
            {
                "CUDA_VISIBLE_DEVICES": "GPU-three",
                "CMF_GPU_GUARD_PHYSICAL_INDEX": "3",
            },
            clear=False,
        ), patch(
            "controlled_multi_future.real_sapien_adapter_high_level_v1."
            "subprocess.run",
            return_value=completed,
        ):
            selected = _selected_nvidia_device_v1()
        self.assertEqual(
            selected,
            {
                "physical_index": 3,
                "uuid": "GPU-three",
                "pci_bus_id": "0000:61:00.0",
            },
        )

        class Device:
            name = "fake-render-device"
            cuda_id = 0
            pci_string = "0000:61:00.0"

            @staticmethod
            def can_render():
                return True

            @staticmethod
            def is_cuda():
                return True

        receipt = _build_render_device_binding_receipt_v1(
            selected=selected, device=Device()
        )
        self.assertTrue(receipt["pass"])
        self.assertEqual(receipt["render_device_cuda_id"], 0)
        self.assertEqual(
            receipt["render_device_pci_bus_id"], selected["pci_bus_id"]
        )

    def test_runner_writes_candidate_bound_terminal_and_never_executes(self):
        spec = build_f2_runtime_spec_v1(
            self.f2["fixed_inside_candidate_order"][0],
            purpose="f2_stage_a_planner",
        )
        adapter = _FakeAdapter(spec)

        def fake_plan(scene, targets, *, query_limit, arm):
            scene.planner_query_count = 1
            return {
                "pass": True,
                "segment_receipts": [
                    {
                        "segment_id": targets[0]["segment_id"],
                        "planner_status": "Success",
                    }
                ],
                "planner_query_count": 1,
                "terminal_qpos": [0.0],
                "terminal_qpos_sha256": "2" * 64,
                "controls": [{}],
            }

        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as temporary:
            output = Path(temporary) / "candidate"
            with patch(
                "controlled_multi_future.high_level_planner_runner_v1."
                "build_f2_stage_a_targets_v1",
                return_value=([{"segment_id": "one", "pose": [0, 0, 1, 1, 0, 0, 0]}], {}),
            ), patch(
                "controlled_multi_future.high_level_planner_runner_v1._planner_reset",
                return_value={"reset_performed": True},
            ), patch(
                "controlled_multi_future.high_level_planner_runner_v1._plan_chain",
                side_effect=fake_plan,
            ):
                receipt = HighLevelPlannerRunnerV1(adapter).run(
                    output_dir=output, planned_spec=spec
                )
            self.assertTrue(receipt["pass"])
            self.assertEqual(receipt["physical_execution_count"], 0)
            self.assertEqual(receipt["candidate_sha256"], spec["candidate_sha256"])
            self.assertTrue((output / "receipt.json").is_file())

    def test_runtime_spec_tamper_fails_closed(self):
        spec = build_f3_runtime_spec_v1(
            self.f3["fixed_tuple_order"][0], purpose="f3_level1_planner"
        )
        changed = copy.deepcopy(spec)
        changed["arm"] = "right" if spec["arm"] == "left" else "left"
        with self.assertRaises(ValueError):
            validate_f3_runtime_spec_v1(changed)

    def test_f4_stage_b_runner_requires_all_three_complete_role_chains(self):
        terminal = self._f4_stage_a_terminal()
        stage_b = build_f4_stage_b_candidates_v1(self.f4, terminal)
        spec = build_f4_runtime_spec_v1(
            stage_b["fixed_candidate_order"][0],
            purpose="f4_stage_b_planner",
            stage_a_terminal=terminal,
        )
        adapter = _FakeAdapter(spec)
        adapter.context.scene.role_actors = {
            "A": adapter.context.scene.a,
            "B": adapter.context.scene.b,
            "C": adapter.context.scene.c,
        }
        role_ids = {
            role: [f"{role}_segment_{index}" for index in range(10)]
            for role in ("A", "B", "C")
        }
        targets = [
            {
                "segment_id": segment_id,
                "pose": [0, 0, 1, 1, 0, 0, 0],
            }
            for role in ("A", "B", "C")
            for segment_id in role_ids[role]
        ]
        audit = {
            "role_target_segment_ids": role_ids,
            "nominal_noninterference": {"pass": True},
            "prior_slot_preservation": {"pass": True},
        }

        def fake_plan(scene, requested, *, query_limit, arm):
            self.assertEqual(requested, targets)
            scene.planner_query_count = len(requested)
            return {
                "pass": True,
                "segment_receipts": [
                    {
                        "segment_id": item["segment_id"],
                        "planner_status": "Success",
                    }
                    for item in requested
                ],
                "planner_query_count": len(requested),
                "terminal_qpos": [0.0],
                "terminal_qpos_sha256": "4" * 64,
                "controls": [{} for _ in requested],
            }

        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as temporary:
            output = Path(temporary) / "f4-stage-b"
            with patch(
                "controlled_multi_future.high_level_planner_runner_v1."
                "build_f4_stage_b_targets_v1",
                return_value=(targets, audit),
            ), patch(
                "controlled_multi_future.high_level_planner_runner_v1."
                "_planner_reset",
                return_value={"reset_performed": True},
            ), patch(
                "controlled_multi_future.high_level_planner_runner_v1."
                "_plan_chain",
                side_effect=fake_plan,
            ):
                receipt = HighLevelPlannerRunnerV1(adapter).run(
                    output_dir=output, planned_spec=spec
                )
        self.assertTrue(receipt["pass"])
        self.assertEqual(
            set(receipt["checks"]), set(self.f4["stage_b_required_gates"])
        )
        self.assertEqual(receipt["planner_query_count"], 30)
        self.assertEqual(receipt["physical_execution_count"], 0)

    def test_f4_prior_slot_overlay_uses_pose_tolerances_not_raw_quaternion_components(self):
        targets = {
            "A": [-0.1, 0.04, 0.764, 1.0, 1e-5, 0.0, 0.0],
            "B": [-0.2, 0.04, 0.764, 1.0, 1e-5, 0.0, 0.0],
            "C": [-0.3, 0.04, 0.764, 1.0, 1e-5, 0.0, 0.0],
        }
        observed = {
            role: [*pose[:3], *(np.asarray(pose[3:]) / np.linalg.norm(pose[3:]))]
            for role, pose in targets.items()
        }
        nominal = {
            "pass": True,
            "per_role": {
                "A": {
                    "state_of_other_blocks_before_role": {
                        "B": observed["B"],
                        "C": observed["C"],
                    },
                    "segment_non_target_collisions": {
                        "lift_to_carry_mid": [],
                        "carry_mid_to_preplace": [],
                    },
                },
                "B": {
                    "state_of_other_blocks_before_role": {
                        "A": observed["A"],
                        "C": observed["C"],
                    },
                    "segment_non_target_collisions": {
                        "lift_to_carry_mid": [],
                        "carry_mid_to_preplace": [],
                    },
                },
                "C": {
                    "state_of_other_blocks_before_role": {
                        "A": observed["A"],
                        "B": observed["B"],
                    },
                    "segment_non_target_collisions": {
                        "lift_to_carry_mid": [],
                        "carry_mid_to_preplace": [],
                    },
                },
            },
        }
        prior = _build_f4_prior_slot_preservation_v1(nominal, targets)
        self.assertTrue(prior["pass"])
        self.assertTrue(prior["raw_quaternion_component_comparison_forbidden"])
        role_ids = {role: [f"{role}_one"] for role in ("A", "B", "C")}
        bad_prior = copy.deepcopy(prior)
        bad_prior["pass"] = False
        source = {
            "schema_version": "cmf_high_level_planner_candidate_terminal_v1",
            "purpose": "f4_stage_b_planner",
            "candidate_id": "f4-slot-corridor-hv1-r01",
            "candidate_sha256": "a" * 64,
            "physical_execution_count": 0,
            "planner_result": {
                "pass": True,
                "segment_receipts": [
                    {"segment_id": ids[0], "planner_status": "Success"}
                    for ids in role_ids.values()
                ],
            },
            "rendered_visibility": {"pass": True},
            "target_construction": {
                "role_target_segment_ids": role_ids,
                "role_target_construction_audits": {
                    role: {"target_actor_pose": pose}
                    for role, pose in targets.items()
                },
                "nominal_noninterference": nominal,
                "prior_slot_preservation": bad_prior,
            },
            "checks": {
                "complete_A_neutral_grasp_slot_neutral": True,
                "complete_B_neutral_grasp_slot_neutral": True,
                "complete_C_neutral_grasp_slot_neutral": True,
                "rendered_visibility": True,
                "noninterference": True,
                "prior_slot_preservation": False,
            },
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }
        source["receipt_sha256"] = canonical_hash_json(source)
        overlay = rederive_f4_stage_b_candidate_checks_v1(source)
        self.assertTrue(overlay["pass"])
        self.assertFalse(overlay["reexecution_required"])
        self.assertTrue(overlay["checks"]["prior_slot_preservation"])

    def test_f3_level2_adds_v_minus_and_return_without_suffix(self):
        spec = build_f3_runtime_spec_v1(
            self.f3["fixed_tuple_order"][0], purpose="f3_level2_physical"
        )
        level1 = [
            {"segment_id": name, "pose": [0, 0, 1 + index * 0.01, 1, 0, 0, 0]}
            for index, name in enumerate(
                (
                    "pregrasp",
                    "grasp",
                    "lift",
                    "central",
                    "V_plus",
                    "return",
                )
            )
        ]
        with patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "build_f3_level1_targets_v1",
            return_value=(level1, {"source": "test"}),
        ):
            targets, audit = build_f3_level2_targets_v1(object(), spec)
        self.assertEqual(
            [item["segment_id"] for item in targets[-2:]],
            ["f3_level2_V_minus", "f3_level2_return"],
        )
        self.assertEqual(len(targets), 7)
        self.assertEqual(audit["level2_closed_loop_sequence"], ["V_plus", "V_minus", "return"])

    def test_f2_physical_fails_closed_before_execution_when_planner_fails(self):
        spec = build_f2_runtime_spec_v1(
            self.f2["fixed_inside_candidate_order"][0],
            purpose="f2_inside_physical",
        )
        fake_scene = object()
        with patch(
            "controlled_multi_future.high_level_physical_runner_v1."
            "build_f2_stage_a_targets_v1",
            return_value=([{"segment_id": "one", "pose": [0, 0, 1, 1, 0, 0, 0]}], {}),
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._planner_reset",
            return_value={},
        ), patch(
            "controlled_multi_future.high_level_physical_runner_v1._plan_chain",
            return_value={
                "pass": False,
                "segment_receipts": [],
                "planner_query_count": 1,
                "terminal_qpos": [0.0],
                "terminal_qpos_sha256": "3" * 64,
                "controls": [],
            },
        ):
            result = execute_f2_inside_physical_v1(fake_scene, spec)
        self.assertFalse(result["sequence_complete"])
        self.assertFalse(result["strict_inside_verifier_pass"])
        self.assertEqual(
            result["gates"],
            {
                "planner_success": False,
                "preload_entry_v11": False,
                "release_safety_v10": False,
                "final_inside_v10": False,
            },
        )

    def test_physical_runner_is_candidate_bound_and_one_execution_only(self):
        spec = build_f3_runtime_spec_v1(
            self.f3["fixed_tuple_order"][0], purpose="f3_level2_physical"
        )
        adapter = _FakeAdapter(spec)
        adapter.context.scene.role_actors = {"bottle": adapter.context.scene.bottle}

        def fake_execute(scene, value):
            scene.planner_query_count = 2
            scene.trace = [{}]
            return {"sequence_complete": True, "gates": {"all": True}}

        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as temporary:
            output = Path(temporary) / "physical"
            with patch(
                "controlled_multi_future.high_level_physical_runner_v1."
                "execute_f3_level2_physical_v1",
                side_effect=fake_execute,
            ):
                receipt = HighLevelPhysicalRunnerV1(adapter).run(
                    output_dir=output, planned_spec=spec
                )
            self.assertTrue(receipt["pass"])
            self.assertEqual(receipt["physical_execution_count"], 1)
            self.assertEqual(
                receipt["candidate_sha256"], spec["f3_asset_grasp_tuple_sha256"]
            )
            self.assertTrue((output / "physical_trace.npz").is_file())


if __name__ == "__main__":
    unittest.main()
