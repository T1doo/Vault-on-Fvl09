import inspect
import unittest

import numpy as np

from controlled_multi_future.canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
)
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.f2_mutually_exclusive_region_layout_v2 import LAYOUT
from controlled_multi_future.f4_staged_block_gate_v1 import (
    F4StagedBlockExecutionGateV1,
    GATE_SEQUENCE,
)
from controlled_multi_future.family_runners_v3_1 import _stable_and_support
from controlled_multi_future.family_runners_v3_3 import (
    F1ControllerV3_3,
    F2ControllerV3_3,
    F3ControllerV3_3,
    F4ControllerV3_3,
    _first_stable_slot_completion,
    _raw_result,
    install_frozen_suffix_controls,
)
from controlled_multi_future.probes import runtime_v3_3_scope_runner
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import (
    F4_LAYOUT,
    planned_scope_spec,
)
from controlled_multi_future.runtime_v3_3_scope_bundle_v1 import build_scope_bundle


class Pose:
    def __init__(self, value):
        value = np.asarray(value, dtype=np.float64)
        self.p = value[:3]
        self.q = value[3:]


class Actor:
    def __init__(self, name, pose):
        self.name = name
        self.pose = Pose(pose)

    def get_name(self):
        return self.name

    def get_pose(self):
        return self.pose


def anchor(value):
    return {
        "anchor_sha256": str(value) * 64,
        "actor_states": {},
        "facility_poses": {},
    }


class RuntimeV3_3HardeningTest(unittest.TestCase):
    def test_artifact_requires_passing_physical_gate_and_trace_hash(self):
        arrays = {
            "effective_setpoint_actions": np.zeros((1, 26)),
            "requested_commands": np.zeros((1, 26)),
            "component_masks": np.ones((1, 26), dtype=bool),
            "action_interval_start_timestamps": np.asarray([0.0]),
            "action_interval_end_timestamps": np.asarray([0.004]),
            "left_gripper_joint_drive_targets": np.zeros((1, 1)),
            "right_gripper_joint_drive_targets": np.zeros((1, 1)),
            "left_gripper_joint_drive_velocity_targets": np.zeros((1, 1)),
            "right_gripper_joint_drive_velocity_targets": np.zeros((1, 1)),
        }
        kwargs = dict(
            root_slot_id="root",
            family="F3",
            reference_current_sha256="a" * 64,
            reference_anchor=anchor(1),
            prefix_contract={"prefix_id": "f3", "arm": "left"},
            planner_seed=1,
            planner_query_receipts=[],
            planner_source_hash="b" * 64,
            arrays=arrays,
            semantic_prefix_end_anchor=anchor(2),
            acceptance_prefix_end_anchor=anchor(3),
            settling_step_count=50,
            settling_policy={
                "mode": "hold_last_effective_setpoint",
                "semantic": False,
                "component_mask_policy": "all_false_no_new_control_command",
                "transition_operator": "replay_effective_setpoint_step_v1_1",
            },
            prefix_physical_acceptance={"pass": False},
            reference_trace_source={"sha256": "c" * 64},
        )
        with self.assertRaisesRegex(ValueError, "physical-acceptance"):
            build_canonical_prefix_artifact(**kwargs)
        kwargs["prefix_physical_acceptance"] = {"pass": True}
        kwargs["reference_trace_source"] = {}
        with self.assertRaisesRegex(ValueError, "trace SHA"):
            build_canonical_prefix_artifact(**kwargs)

    def test_raw_result_wrapper_forces_v3_3_provenance(self):
        source = inspect.getsource(_raw_result)
        self.assertIn('"controlled_multi_future_runtime_v3_3"', source)

    def test_actor_specific_stability_never_uses_trace_primary_actor(self):
        red = Actor("red", [0, 0, 0, 1, 0, 0, 0])
        blue = Actor("blue", [0, 0, 0, 1, 0, 0, 0])
        scene = type("Scene", (), {})()
        scene.trace_actor = red
        scene.trace_role_actors = {"red": red, "blue": blue}
        scene.trace = [
            {
                "actor_linear_velocity": np.zeros(3),
                "role_actor_linear_velocities": {
                    "red": np.zeros(3),
                    "blue": np.asarray([0.1, 0, 0]),
                },
                "contact_pairs": [
                    {"body_a": "blue", "body_b": "table"}
                ],
            }
            for _ in range(50)
        ]
        _, blue_speeds, contacts = _stable_and_support(
            scene, blue, "table", frames=50
        )
        self.assertAlmostEqual(max(blue_speeds), 0.1)
        self.assertTrue(all(contacts))

    def test_f2_beside_uses_frozen_table_support_height_not_lifted_pose(self):
        scene = type("Scene", (), {})()
        scene.can = Actor("can", [-0.28, 0.04, 0.91, 0.5, 0.5, 0.5, 0.5])
        scene.stand = Actor(
            "stand", [*LAYOUT["stand_xyz"], *LAYOUT["stand_q_wxyz"]]
        )
        program = {"steps": [{"operation": "move"}, {"relation": "beside"}]}
        relation, target, _ = F2ControllerV3_3()._target_actor(scene, program)
        self.assertEqual(relation, "beside")
        self.assertAlmostEqual(target[2], LAYOUT["can_xyz"][2])
        self.assertNotAlmostEqual(target[2], scene.can.get_pose().p[2])
        execution_source = inspect.getsource(
            F2ControllerV3_3.execute_frozen_suffix_spec
        )
        self.assertIn("obb_corners", execution_source)
        self.assertIn("on_scale_full_obb_footprint", execution_source)
        self.assertNotIn("top_surface_region", execution_source)

    def test_f4_completion_is_first_consecutive_stable_supported_window(self):
        actor = Actor("cube-a", [0, 0, 0, 1, 0, 0, 0])
        slot = Actor("slot-a", [0, 0, 0, 1, 0, 0, 0])
        scene = type("Scene", (), {})()
        scene.trace = []
        for index in range(8):
            good = index >= 3
            scene.trace.append(
                {
                    "role_actor_poses": {
                        "A": np.asarray([0 if good else 0.2, 0, 0, 1, 0, 0, 0])
                    },
                    "role_actor_linear_velocities": {
                        "A": np.zeros(3) if good else np.asarray([0.1, 0, 0])
                    },
                    "role_actor_angular_velocities": {
                        "A": np.zeros(3) if good else np.asarray([0.1, 0, 0])
                    },
                    "contact_pairs": [
                        {"body_a": "cube-a", "body_b": "table"}
                    ]
                    if good
                    else [],
                }
            )
        receipt = _first_stable_slot_completion(
            scene,
            role="A",
            actor=actor,
            slot=slot,
            start_row=0,
            required_frames=3,
        )
        self.assertTrue(receipt["pass"])
        self.assertEqual(receipt["completion_trace_row"], 3)

    def test_scope_runner_and_f4_gate_order_are_current(self):
        source = inspect.getsource(runtime_v3_3_scope_runner)
        self.assertIn("RoboTwinRealSapienStrictPrefixAdapterV1_3", source)
        self.assertIn("RealSapienStrictPrefixRootOrchestratorV1_2", source)
        self.assertIn("require_atomic_gpu_guard_v2_4", source)
        self.assertNotIn("runtime_v3_2", source)
        self.assertIn("execution_dispatched", source)
        self.assertIn("result_returned", source)
        self.assertEqual(
            GATE_SEQUENCE, (("A",), ("B",), ("C",), ("A", "B"))
        )
        staged_source = inspect.getsource(F4StagedBlockExecutionGateV1.run)
        self.assertIn("preflight_partial_trace_source.npz", staged_source)
        self.assertIn("partial_trace_source.npz", staged_source)
        self.assertLess(
            staged_source.index("raw = write_raw_attempt"),
            staged_source.index("verifier = self.adapter.verify"),
        )
        f4_source = inspect.getsource(F4ControllerV3_3.execute_frozen_suffix_spec)
        self.assertIn("set_trace_contact_actor(actor)", f4_source)
        self.assertIn("_first_stable_slot_completion", f4_source)
        self.assertIn("common_x_preserved_after_all_blocks", f4_source)

    def test_f3_prefix_has_realized_motion_stability_contact_and_grasp_gate(self):
        source = inspect.getsource(F3ControllerV3_3.plan_and_execute_canonical_prefix)
        for token in (
            "verify_realized_motion_metrics",
            "shared_first_v_realized_motion",
            "grasp_transform_translation_stable",
            "grasp_transform_orientation_stable",
            "require_selected_contact=True",
            "prefix_physical_acceptance",
        ):
            self.assertIn(token, source)

    def test_f1_comparative_gate_requires_all_qpos_and_joint_margins(self):
        receipts = []
        for role in ("red", "green", "blue"):
            receipts.append(
                {
                    "program_id": f"F1-{role}",
                    "planner_solvable": True,
                    "actual_prefix_end_qpos_sha256": "a" * 64,
                    "execution_spec": {
                        "terminal_qpos": [0.0] * 7,
                        "terminal_qpos_sha256": "b" * 64,
                        "terminal_joint_limit_margin_rad": [1.0] * 7,
                        "minimum_terminal_joint_limit_margin_rad": 1.0,
                        "terminal_qpos_within_joint_limits": True,
                        "comparative_reachability": {
                            "minimum_non_target_waypoint_clearance_m": 0.05
                        },
                    },
                    "evidence": {
                        "planner_collision_check_source": "CuRobo",
                        "quantitative_collision_clearance_available": False,
                    },
                }
            )
        gate = F1ControllerV3_3().validate_family_suffix_gate(receipts)
        self.assertTrue(gate["pass"])
        bad = [dict(item) for item in receipts]
        bad[2] = {**bad[2], "execution_spec": {}}
        self.assertFalse(F1ControllerV3_3().validate_family_suffix_gate(bad)["pass"])

    def test_float64_actual_and_float32_planner_hashes_are_distinct_fields(self):
        actual = np.asarray([0.1, 0.2], dtype=np.float64)
        planner = actual.astype(np.float32)
        self.assertNotEqual(hash_array(actual), hash_array(planner))
        source = inspect.getsource(
            __import__(
                "controlled_multi_future.family_runners_v3_3",
                fromlist=["_cache_suffix_controls"],
            )._cache_suffix_controls
        )
        self.assertIn("raw_actual_qpos", source)
        self.assertIn("planner_input_prefix_end_qpos_sha256", source)

    def test_frozen_suffix_install_restores_query_table_without_live_query(self):
        scene = type("Scene", (), {})()
        scene.planner_queries = []
        scene.planner_query_count = 0
        control = {
            "status": "Success",
            "position": np.zeros((1, 7), dtype=np.float32),
            "velocity": np.zeros((1, 7), dtype=np.float32),
            "_cmf_planner_query": {
                "query_id": 1,
                "arm": "left",
                "source": "segment",
                "goal_eef_pose": [0, 0, 1, 1, 0, 0, 0],
                "status": "Success",
                "start_step": 5,
                "end_step": 6,
            },
        }
        install_frozen_suffix_controls(
            scene,
            {"control_cache_key": "cache-key"},
            [control],
        )
        self.assertEqual(scene.planner_query_count, 0)
        self.assertEqual(len(scene.planner_queries), 1)
        self.assertIsNone(scene.planner_queries[0]["start_step"])
        self.assertTrue(
            scene.planner_queries[0]["replayed_from_frozen_suffix_artifact"]
        )

    def test_only_initial_suffix_segment_requires_exact_preflight_qpos(self):
        module = __import__(
            "controlled_multi_future.family_runners_v3_3",
            fromlist=["_execute_cached_segment"],
        )
        source = inspect.getsource(module._execute_cached_segment)
        self.assertIn("if index == 0", source)
        self.assertIn("intervening_control_trace_is_authoritative", source)
        self.assertIn("terminal_qpos_within_provisional_audit_tolerance", source)
        self.assertNotIn("terminal qpos tracking failed", source)

    def test_planned_specs_freeze_f2_layout_f4_layout_and_revision_identity(self):
        f2_r1 = planned_scope_spec(
            "F2_diagnosis_root_per_revision", revision_index=1
        )
        f2_r2 = planned_scope_spec(
            "F2_diagnosis_root_per_revision", revision_index=2
        )
        self.assertEqual(f2_r1["slot_id"], f2_r2["slot_id"])
        self.assertEqual(f2_r1["seed"], f2_r2["seed"])
        self.assertEqual(f2_r1["scene_layout"], LAYOUT)
        f4 = planned_scope_spec(
            "F4_block_root_per_revision", revision_index=1
        )
        self.assertEqual(f4["scene_layout"], F4_LAYOUT)
        self.assertEqual(f4["scene_layout"]["tray"]["model_id"], 0)
        builder_source = inspect.getsource(build_scope_bundle)
        self.assertIn("capture_runtime_source_lock", builder_source)
        self.assertIn("issue_authorization_from_scope_request", builder_source)
        self.assertIn("allowed_physical_gpu_indices=list(range(8))", builder_source)


if __name__ == "__main__":
    unittest.main()
