import inspect
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.current_hasher import SameCurrentMismatch, hash_json
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F3ControllerV3_3,
    F4ControllerV3_3,
    _f2_left_gripper_assembly_topology,
)
from controlled_multi_future.f3_return_release_v5 import (
    POST_RELEASE_SAMPLE_STEPS,
)
from controlled_multi_future.runtime_v3_1_contracts import (
    F3_RELEASE_SAMPLE_POINTS,
)
from controlled_multi_future.f4_micro_lift_gate_v5 import (
    F4CommonBoundaryAndMicroLiftGateV5,
)
from controlled_multi_future.probes.runtime_v3_3_scope_runner import SCOPE_FAMILIES
from controlled_multi_future.real_sapien_adapter_v1_2 import (
    ImplementationSourceIntegrityError,
    RoboTwinRealSapienPilotRootAdapterV1_2,
)
from controlled_multi_future.real_sapien_adapter_v1_3 import (
    RoboTwinRealSapienStrictPrefixAdapterV1_3,
)
from controlled_multi_future.root_orchestrator_v1_2 import (
    _require_same_current_and_persist,
)
from controlled_multi_future.runtime_v3_3_budget_v1 import (
    ROOT_SCOPES,
    validate_static_scope_activity_envelope,
)
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import planned_scope_spec


TMP_ROOT = Path("/nfs_share/lijunhui/Robotwin2/tmp")


class Revision5IntegrationTest(unittest.TestCase):
    def test_f2_palm_classification_keeps_finger_signal(self):
        source = inspect.getsource(F2ControllerV3_3.execute_frozen_suffix_spec)
        self.assertIn("_f2_left_gripper_assembly_topology", source)
        self.assertIn("allowed_gripper_assembly_body_names", source)
        self.assertIn("selected_gripper_body_names", source)

    def test_f2_live_topology_adapter_binds_palm_and_two_fingers(self):
        class Link:
            def __init__(self, name, z):
                self.name = name
                self.z = z

            def get_name(self):
                return self.name

            def get_pose(self):
                return SimpleNamespace(p=[0.0, 0.0, self.z])

        links = {
            name: Link(name, z)
            for name, z in (
                ("fl_link6", 1.0),
                ("fl_link7", 0.98),
                ("fl_link8", 0.98),
            )
        }

        class Joint:
            def __init__(self, name, child):
                self.name = name
                self.parent_link = links["fl_link6"]
                self.child_link = links[child]

            def get_name(self):
                return self.name

        robot = SimpleNamespace(
            left_entity=SimpleNamespace(get_links=lambda: list(links.values())),
            left_gripper=[
                (Joint("fl_joint7", "fl_link7"), 1.0),
                (Joint("fl_joint8", "fl_link8"), 1.0),
            ],
            left_fix_gripper_name=[],
            left_move_group="fl_link6",
            get_left_ee_pose=lambda: [0, 0, 1.02, 1, 0, 0, 0],
        )
        receipt = _f2_left_gripper_assembly_topology(
            SimpleNamespace(robot=robot)
        )
        self.assertEqual(
            receipt["selected_contact_signal_link_names"],
            ["fl_link7", "fl_link8"],
        )
        self.assertEqual(
            receipt["additional_allowed_gripper_assembly_body_names"],
            ["fl_link6"],
        )

    def test_f3_changes_only_return_release_path(self):
        planning = inspect.getsource(
            F3ControllerV3_3.plan_suffix_from_actual_prefix_end_state
        )
        execution = inspect.getsource(
            F3ControllerV3_3.execute_frozen_suffix_spec
        )
        self.assertIn("contact_free_release_actor_pose", planning)
        self.assertIn("control_transformer=transform_f3_return_controls_v5", planning)
        self.assertIn("F3 contact-free pre-open Gate failed", execution)
        self.assertIn("F3 failed_release_disengagement", execution)
        self.assertIn("physical_release_trace_index", execution)
        classifier_keys = (
            "before_release",
            *tuple(
                f"after_release_{step}"
                for step in POST_RELEASE_SAMPLE_STEPS
                if step != 0
            ),
            "after_rest",
        )
        self.assertEqual(classifier_keys, F3_RELEASE_SAMPLE_POINTS)

    def test_f4_r5_scope_is_revision_bound_and_finite(self):
        scope = "F4_micro_lift_diagnosis_per_revision"
        self.assertEqual(SCOPE_FAMILIES[scope], "F4")
        self.assertIn(scope, ROOT_SCOPES)
        static = validate_static_scope_activity_envelope(scope)
        self.assertEqual(
            static["source_bound_static_envelope"],
            {"planner_query_count": 13, "execution_attempt_count": 1},
        )
        spec = planned_scope_spec(scope, revision_index=5)
        self.assertEqual(spec["slot_id"], "pilot-F4-A-prestage0")
        self.assertFalse(spec["stage0_authorized"])
        self.assertIn("common_vertical_withdraw", spec["branch_neutral_runtime_policy"])
        source = inspect.getsource(F4CommonBoundaryAndMicroLiftGateV5.run)
        self.assertIn("plan_a_micro_lift_from_actual_prefix_end_state", source)
        self.assertIn("execute_a_micro_lift_diagnostic", source)
        self.assertNotIn("F4StagedBlockExecutionGateV1", source)

    def test_f4_failed_pregrasp_boundary_never_closes_or_lifts(self):
        controller = F4ControllerV3_3()
        calls = {"close": 0, "segments": []}

        class Scene:
            a = object()
            b = object()
            c = object()
            common_x = object()
            tray = object()
            trace = [
                {
                    "eef_linear_velocity": [0, 0, 0],
                    "eef_angular_velocity": [0, 0, 0],
                    "realized_right_gripper_joint_qpos": [0.044, 0.044],
                }
            ]

            def set_trace_contact_actor(self, _actor):
                return None

            def close_gripper(self, *_args, **_kwargs):
                calls["close"] += 1
                return object()

        scene = Scene()
        targets = [
            {"segment_id": "A_pregrasp", "pose": [0, 0, 1, 1, 0, 0, 0]},
            {"segment_id": "A_grasp", "pose": [0, 0, 0.9, 1, 0, 0, 0]},
            {"segment_id": "A_micro_lift", "pose": [0, 0, 0.92, 1, 0, 0, 0]},
        ]

        def execute(_scene, _spec, _controls, index):
            calls["segments"].append(index)
            return {"segment_id": targets[index]["segment_id"]}

        with patch(
            "controlled_multi_future.family_runners_v3_3._cached_controls",
            return_value=[{}, {}, {}],
        ), patch(
            "controlled_multi_future.family_runners_v3_3._execute_cached_segment",
            side_effect=execute,
        ), patch(
            "controlled_multi_future.family_runners_v3_3._wait_and_record"
        ), patch(
            "controlled_multi_future.family_runners_v3_3._arm_eef_pose",
            return_value=[0, 0, 1, 1, 0, 0, 0],
        ), patch(
            "controlled_multi_future.family_runners_v3_3._pose",
            return_value=np.asarray([0, 0, 0.8, 1, 0, 0, 0], dtype=np.float64),
        ), patch(
            "controlled_multi_future.family_runners_v3_3._stable_and_support",
            return_value=(
                [
                    {
                        "role_actor_angular_velocities": {
                            "common_x": [0, 0, 0],
                            "B": [0, 0, 0],
                            "C": [0, 0, 0],
                        }
                    }
                ]
                * 50,
                [0.0] * 50,
                [True] * 50,
            ),
        ), patch(
            "controlled_multi_future.family_runners_v3_3.footprint_inside_local_region",
            return_value={"pass_support_footprint": True},
        ), patch.object(
            controller,
            "_actual_open_boundary_receipt",
            return_value={"pass": False},
        ), self.assertRaisesRegex(RuntimeError, "pregrasp"):
            controller.execute_a_micro_lift_diagnostic(
                scene,
                {"program_id": "F4-DIAG-A-MICRO-LIFT"},
                {"targets": targets},
                {},
                {"formal_data": False, "stage0_data": False},
            )
        self.assertEqual(calls["segments"], [0])
        self.assertEqual(calls["close"], 0)

    def test_source_hash_is_sealed_and_live_change_fails_closed(self):
        fake_scene = SimpleNamespace(
            _cmf_setup_kwargs={
                "static_friction": 0.5,
                "dynamic_friction": 0.5,
                "restitution": 0.0,
            },
            _cmf_canonical_settle_steps=60,
            _cmf_sealed_implementation_source_sha256="a" * 64,
            _cmf_adapter_version="adapter-test",
            scene=SimpleNamespace(get_timestep=lambda: 0.004),
        )
        with patch(
            "controlled_multi_future.real_sapien_adapter_v1_2.implementation_source_sha256",
            return_value="a" * 64,
        ):
            config = RoboTwinRealSapienPilotRootAdapterV1_2._simulation_configuration(
                fake_scene
            )
        self.assertEqual(config["implementation_source_sha256"], "a" * 64)
        self.assertTrue(config["implementation_source_live_check_equal"])
        with patch(
            "controlled_multi_future.real_sapien_adapter_v1_2.implementation_source_sha256",
            return_value="b" * 64,
        ), self.assertRaisesRegex(ImplementationSourceIntegrityError, "changed"):
            RoboTwinRealSapienPilotRootAdapterV1_2._simulation_configuration(
                fake_scene
            )

    def test_authorization_source_hash_binds_adapter_before_scene(self):
        with patch(
            "controlled_multi_future.real_sapien_adapter_v1_2.implementation_source_sha256",
            return_value="b" * 64,
        ), self.assertRaisesRegex(
            ImplementationSourceIntegrityError, "authorization-bound"
        ):
            RoboTwinRealSapienStrictPrefixAdapterV1_3(
                family="F2",
                output_root=TMP_ROOT / "adapter-toctou",
                expected_implementation_source_sha256="a" * 64,
            )
        runner_source = inspect.getsource(
            __import__(
                "controlled_multi_future.probes.runtime_v3_3_scope_runner",
                fromlist=["main"],
            ).main
        )
        self.assertIn(
            "expected_implementation_source_sha256=authorization",
            runner_source,
        )

    def test_same_current_mismatch_receipt_is_saved_before_cleanup(self):
        reference = {
            "schema_version": "current_context_hash_v2",
            "aggregate_sha256": "1" * 64,
            "model_visible_aggregate_sha256": "2" * 64,
            "hidden_physical_aggregate_sha256": "3" * 64,
            "reconstruction_spec_aggregate_sha256": "4" * 64,
            "model_visible_components": {"rgb": "5" * 64},
            "reconstruction_spec_components": {"simulation": "6" * 64},
            "reconstruction_spec_audit": {"source": "a" * 64},
        }
        candidate = json.loads(json.dumps(reference))
        candidate["aggregate_sha256"] = "7" * 64
        candidate["reconstruction_spec_aggregate_sha256"] = "8" * 64
        candidate["reconstruction_spec_components"]["simulation"] = "9" * 64
        candidate["reconstruction_spec_audit"] = {"source": "b" * 64}
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TMP_ROOT) as directory:
            path = Path(directory) / "mismatch.json"
            with self.assertRaises(SameCurrentMismatch):
                _require_same_current_and_persist(
                    reference,
                    candidate,
                    receipt_path=path,
                    phase="test",
                    program_id="F3-VHVH",
                    scene_instance_id="scene-1",
                )
            value = json.loads(path.read_text(encoding="utf-8"))
            digest = value.pop("receipt_sha256")
            self.assertEqual(digest, hash_json(value))
            self.assertTrue(value["saved_before_scene_cleanup"])
            self.assertEqual(
                value["candidate_reconstruction_spec_audit"]["source"],
                "b" * 64,
            )


if __name__ == "__main__":
    unittest.main()
