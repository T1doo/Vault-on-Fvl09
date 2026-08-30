import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from controlled_multi_future.anchor import capture_anchor, compare_anchors
from controlled_multi_future.attempt_state_machine import AttemptStateMachine
from controlled_multi_future.candidate_freezer import freeze_candidate_universe
from controlled_multi_future.current_hasher import build_current_hashes, require_same_current
from controlled_multi_future.families import F1ObjectSelection, F2TargetRelation
from controlled_multi_future.finalizer import finalize_nonformal_integration
from controlled_multi_future.geometry import (
    actor_target_to_eef_pose,
    footprint_inside_local_region,
    quaternion_angular_velocity,
    relative_pose,
    select_first_verified_pose,
    swept_path_collisions,
)
from controlled_multi_future.model_view import build_model_view
from controlled_multi_future.probe_contracts import FAMILY_VARIANTS as VARIANTS, HISTORICAL_FAMILY_VARIANTS, result_passed
from controlled_multi_future.probes.gpu_guard import (
    ALLOWED_PHYSICAL_GPU_INDICES,
    build_child_environment,
    classify_terminal_status,
    update_child_receipt,
    verify_post_release,
)
from controlled_multi_future.probes.lifecycle import initialize_cleanup_fields, managed_scene
from controlled_multi_future.probes.runtime_trace import DenseTraceMixin, PlannerQueryLimitExceeded, TRACE_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS, _gripper_joint_qf, _gripper_joint_qpos, _gripper_joint_qvel, is_selected_gripper_contact, trace_rows_to_raw_streams
from controlled_multi_future.a0_activity_monitor_v2 import TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS
from controlled_multi_future.raw_writer import ACTION_LAYOUT_DIMENSIONS, ACTION_LAYOUT_VERSION, TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS as RAW_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS, pack_effective_setpoint, validate_audit_streams, validate_raw_streams, validate_real_runtime_audit_fields, validate_simulator_timing
from controlled_multi_future.runtime_v2_contracts import PLASTICBOX_BASE3_CAVITY, PROVISIONAL_RUNTIME_THRESHOLDS, RUNTIME_V2_PROBE_VARIANTS, TRAY_BASE0_SUPPORT_REGION
from controlled_multi_future.verifiers import (
    verify_completed_slots_preserved,
    verify_beside_final_state,
    verify_common_prefix,
    verify_eef_bottle_axis_consistency,
    verify_non_target_displacement,
    verify_realized_motion_metrics,
    verify_return_equivalence,
    verify_staged_non_target_displacement,
    verify_true_cavity_obb,
)


class DummyScene:
    def __init__(self):
        self.closed = False

    def setup_demo(self, **kwargs):
        self.kwargs = kwargs

    def close_env(self, clear_cache):
        self.closed = clear_cache


class BrokenCleanupScene(DummyScene):
    def close_env(self, clear_cache):
        raise RuntimeError("cleanup failed")


class PreTraceBase:
    def take_dense_action(self, control_seq, save_freq=-1):
        return {"delegated": True, "control_seq": control_seq, "save_freq": save_freq}


class PreTraceProbe(DenseTraceMixin, PreTraceBase):
    pass


class DummyJoint:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name


class DummyEntity:
    def __init__(self, joints, qpos, qf=None, qvel=None):
        self.joints = joints
        self.qpos = np.asarray(qpos, dtype=float)
        self.qf = np.asarray(qf if qf is not None else qpos, dtype=float)
        self.qvel = np.asarray(qvel if qvel is not None else qpos, dtype=float)

    def get_active_joints(self):
        return self.joints

    def get_qpos(self):
        return self.qpos

    def get_qf(self):
        return self.qf

    def get_qvel(self):
        return self.qvel


def field_metadata(planner_status="unavailable"):
    values = {
        "controller_effective_setpoint": ("measured", "test effective drive targets"),
        "requested_command": ("commanded", "test requested control sequence"),
        "planner_goal_eef_pose": (planner_status, "test planner API" if planner_status != "unavailable" else "test has no planner"),
        "realized_qpos": ("measured", "test dual-arm qpos"),
        "realized_qvel": ("measured", "test dual-arm qvel"),
        "realized_eef": ("measured", "test dual-arm eef"),
        "gripper_command": ("commanded", "test gripper command"),
        "action_interval_start_timestamps": ("derived", "test action start index"),
        "action_interval_end_timestamps": ("derived", "test action end index"),
        "state_timestamps": ("derived", "test 250 Hz state index"),
        "component_masks": ("derived", "test component mask"),
    }
    return {key: {"status": status, "source": source} for key, (status, source) in values.items()}


class PipelineContractsTest(unittest.TestCase):
    def test_real_action_trace_uses_a0_float_representation_tolerance(self):
        self.assertEqual(
            TRACE_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
            TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
        )
        self.assertLess(
            abs(0.004000000189989805 - 0.004),
            TRACE_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
        )
        self.assertGreater(
            abs(0.004001 - 0.004),
            TRACE_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
        )

    def test_raw_writer_uses_same_float_timestep_representation_tolerance(self):
        self.assertEqual(
            RAW_TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
            TIMESTEP_ABSOLUTE_TOLERANCE_SECONDS,
        )
        value = {
            "simulator_timing": {
                "simulator_timestep_seconds": 0.004000000189989805,
                "control_steps_per_action": 1,
                "effective_action_interval_seconds": 0.004000000189989805,
                "scene_timestep_source": "SAPIEN scene.get_timestep()",
            }
        }
        self.assertEqual(validate_simulator_timing(value)["control_steps_per_action"], 1)
        value["simulator_timing"]["simulator_timestep_seconds"] = 0.004001
        value["simulator_timing"]["effective_action_interval_seconds"] = 0.004001
        with self.assertRaisesRegex(ValueError, "frozen 250 Hz"):
            validate_simulator_timing(value)

    def test_dense_trace_delegates_during_base_scene_setup(self):
        result = PreTraceProbe().take_dense_action({"setup": True}, save_freq=None)
        self.assertTrue(result["delegated"])
        self.assertEqual(result["control_seq"], {"setup": True})

    def test_planner_query_limit_is_fail_closed(self):
        probe = PreTraceProbe()
        probe.planner_query_count = 0
        probe.planner_query_limit = 1
        self.assertEqual(probe._reserve_planner_query(), 1)
        with self.assertRaises(PlannerQueryLimitExceeded):
            probe._reserve_planner_query()

    def test_action_probe_requires_semantic_verifier_not_only_plan_success(self):
        result = {
            "plan_success": True,
            "inside_verifier": {"pass_provisional_outer_obb": False},
            "left_gripper_open": True,
            "non_target_displacement_m": {"green": 0.0, "blue": 0.0},
        }
        self.assertFalse(result_passed("F1", result))
        result["inside_verifier"]["pass_provisional_outer_obb"] = True
        self.assertTrue(result_passed("F1", result))

    def test_f2_pot_fallback_is_versioned_without_changing_main_object_contract(self):
        self.assertEqual(HISTORICAL_FAMILY_VARIANTS["F2"], ("sector1", "sector2", "pot_left"))
        self.assertEqual(VARIANTS["F2"], ("actor_to_eef_stand",))
        self.assertEqual(F2TargetRelation.main_object, {"modelname": "071_can", "model_id": 1, "arm": "left"})

    def test_scene_cleanup_occurs_on_mid_probe_exception(self):
        receipt = {}
        initialize_cleanup_fields(receipt)
        with self.assertRaisesRegex(RuntimeError, "probe failed"):
            with managed_scene(DummyScene, {}, receipt, "dummy"):
                raise RuntimeError("probe failed")
        self.assertTrue(receipt["scene_cleanup_attempted"])
        self.assertTrue(receipt["scene_cleanup_succeeded"])

    def test_cleanup_uncertainty_is_visible(self):
        receipt = {}
        initialize_cleanup_fields(receipt)
        with managed_scene(BrokenCleanupScene, {}, receipt, "broken"):
            pass
        self.assertFalse(receipt["scene_cleanup_succeeded"])
        self.assertIsNotNone(receipt["cleanup_error"])

    def test_current_hash_is_deterministic_and_detects_change(self):
        kwargs = dict(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.ones((1, 1, 3), dtype=np.uint8), "right": np.ones((1, 1, 3), dtype=np.uint8)},
            robot_state=np.arange(4, dtype=np.float64),
            gripper_actual_state=np.arange(4, dtype=np.float64),
            object_role_layout={"red": [0, 1, 2]},
            camera_config_version="test_camera_v1",
            scene_seed=7,
            generator_version="test_v1",
        )
        first = build_current_hashes(**kwargs)
        second = build_current_hashes(**kwargs)
        require_same_current(first, second)
        kwargs["robot_state"] = np.arange(4, dtype=np.float64) + 1
        with self.assertRaises(ValueError):
            require_same_current(first, build_current_hashes(**kwargs))
        kwargs["robot_state"] = np.arange(4, dtype=np.float64)
        kwargs["gripper_actual_state"] = np.arange(4, dtype=np.float64) + 1
        with self.assertRaises(ValueError):
            require_same_current(first, build_current_hashes(**kwargs))
        kwargs["gripper_actual_state"] = np.arange(4, dtype=np.float64)
        kwargs["camera_config_version"] = "test_camera_v2"
        with self.assertRaises(ValueError):
            require_same_current(first, build_current_hashes(**kwargs))
        kwargs["camera_config_version"] = "test_camera_v1"
        kwargs["wrist_rgb"] = {"left": np.ones((1, 1, 3), dtype=np.uint8)}
        with self.assertRaises(ValueError):
            build_current_hashes(**kwargs)

    def test_anchor_equivalence(self):
        args = dict(robot_qpos=[0, 1], robot_qvel=[0, 0], actor_poses={"A": [0, 0, 0, 1, 0, 0, 0]}, gripper_state=[1, 1], metadata={"seed": 1})
        first = capture_anchor(**args)
        second = capture_anchor(**args)
        self.assertTrue(compare_anchors(first, second)["equivalent"])

    def test_candidate_freezer_and_f2_identity(self):
        programs = F1ObjectSelection().checked_provisional_programs()
        frozen = freeze_candidate_universe(planned_root_slot_spec={"slot": "pilot"}, programs=programs, observable_task_tree={"root": {}}, oracle_task_tree={"root": {}}, implementation_version="test")
        self.assertEqual(len(frozen["programs"]), 3)
        branches = [{"modelname": "071_can", "model_id": 1, "arm": "left"} for _ in range(3)]
        self.assertTrue(F2TargetRelation().validate_shared_execution_identity(branches))
        branches[2]["arm"] = "right"
        with self.assertRaises(ValueError):
            F2TargetRelation().validate_shared_execution_identity(branches)

    def test_primary_stream_26d_250hz_n_plus_one(self):
        action = pack_effective_setpoint(np.arange(6), np.arange(20, 26), 60, np.arange(10, 16), np.arange(30, 36), 70)
        np.testing.assert_array_equal(action, np.concatenate((np.arange(6), np.arange(10, 16), np.arange(20, 26), np.arange(30, 36), [60, 70])))
        self.assertEqual(ACTION_LAYOUT_VERSION, "controller_effective_setpoint_v1_layout_v2_1")
        self.assertEqual(len(ACTION_LAYOUT_DIMENSIONS), 26)
        self.assertEqual(ACTION_LAYOUT_DIMENSIONS[0], "left_joint_0_position_target")
        self.assertEqual(ACTION_LAYOUT_DIMENSIONS[6], "right_joint_0_position_target")
        self.assertEqual(ACTION_LAYOUT_DIMENSIONS[12], "left_joint_0_velocity_target")
        self.assertEqual(ACTION_LAYOUT_DIMENSIONS[24:], ("left_gripper_normalized_target", "right_gripper_normalized_target"))
        streams = {
            "controller_effective_setpoint": np.stack([action, action]),
            "requested_command": np.stack([action.copy(), action.copy()]),
            "planner_goal_eef_pose": np.full((2, 14), np.nan),
            "gripper_command": np.zeros((2, 2)),
            "action_interval_start_timestamps": np.asarray([0.0, 0.004]),
            "action_interval_end_timestamps": np.asarray([0.004, 0.008]),
            "state_timestamps": np.asarray([0.0, 0.004, 0.008]),
            "component_masks": np.ones((2, 26), dtype=bool),
            "realized_qpos": np.zeros((3, 14)),
            "realized_qvel": np.zeros((3, 14)),
            "realized_eef": np.zeros((3, 14)),
            "field_metadata": field_metadata(),
        }
        validate_raw_streams(streams)
        streams["realized_qpos"] = np.zeros((2, 14))
        with self.assertRaises(ValueError):
            validate_raw_streams(streams)
        streams["realized_qpos"] = np.zeros((3, 14))
        streams["action_interval_end_timestamps"] = np.asarray([0.004, 0.010])
        with self.assertRaisesRegex(ValueError, "action ends"):
            validate_raw_streams(streams)

    def test_raw_streams_reject_alias_and_placeholder_sources(self):
        actions = np.zeros((2, 26))
        streams = {
            "controller_effective_setpoint": actions,
            "requested_command": actions,
            "planner_goal_eef_pose": np.full((2, 14), np.nan),
            "gripper_command": np.zeros((2, 2)),
            "action_interval_start_timestamps": np.asarray([0.0, 0.004]),
            "action_interval_end_timestamps": np.asarray([0.004, 0.008]),
            "state_timestamps": np.asarray([0.0, 0.004, 0.008]),
            "component_masks": np.ones((2, 26), dtype=bool),
            "realized_qpos": np.zeros((3, 14)),
            "realized_qvel": np.zeros((3, 14)),
            "realized_eef": np.zeros((3, 14)),
            "field_metadata": field_metadata(),
        }
        with self.assertRaisesRegex(ValueError, "must not alias"):
            validate_raw_streams(streams)
        streams["requested_command"] = actions.copy()
        streams["field_metadata"]["requested_command"]["source"] = "placeholder copy"
        with self.assertRaisesRegex(ValueError, "non-placeholder"):
            validate_raw_streams(streams)

    def test_runtime_trace_converts_to_n_actions_n_plus_one_states(self):
        rows = []
        for index in range(3):
            action = np.arange(26, dtype=float) + index
            rows.append({
                "step_index": index,
                "initial_state": index == 0,
                "effective_setpoint": action,
                "requested_command": action.copy(),
                "planner_goal_eef_pose": np.arange(14, dtype=float),
                "planner_goal_available": np.asarray([True, True]),
                "planner_goal_active": np.asarray([index > 0, index > 0]),
                "planner_query_id": np.asarray([1, 2]) if index > 0 else np.asarray([-1, -1]),
                "planner_goal_source": ("left_move_to_pose", "right_move_to_pose") if index > 0 else ("", ""),
                "component_mask": np.ones(26, dtype=bool),
                "joint_qpos": np.zeros(14) + index,
                "joint_qvel": np.zeros(14),
                "joint_qf": np.zeros(14) + 0.5 * index,
                "dual_eef": np.zeros(14),
                "eef": np.zeros(7),
                "gripper_command": np.ones(2),
                "timestamp": index / 250,
                "actor_pose": np.zeros(7),
                "actor_linear_velocity": np.zeros(3),
                "actor_linear_velocity_measured": False,
                "actor_angular_velocity": np.zeros(3),
                "actor_angular_velocity_measured": False,
                "actor_component_linear_velocity": np.ones(3) * 9.0,
                "actor_component_linear_velocity_measured": True,
                "actor_component_angular_velocity": np.ones(3) * 7.0,
                "actor_component_angular_velocity_measured": True,
                "actor_component_velocity_provenance": {
                    "linear": {"component_type": "DummyRigid", "gate_signal": False},
                    "angular": {"component_type": "DummyRigid", "gate_signal": False},
                },
                "eef_linear_velocity": np.zeros(3),
                "eef_angular_velocity": np.zeros(3),
                "gripper_drive_target_readback": np.ones(2),
                "left_gripper_joint_drive_target": np.zeros(2) + index,
                "right_gripper_joint_drive_target": np.zeros(2) + index,
                "left_gripper_joint_drive_velocity_target": np.zeros(2),
                "right_gripper_joint_drive_velocity_target": np.zeros(2),
                "realized_left_gripper_joint_qpos": np.zeros(2) + index,
                "realized_right_gripper_joint_qpos": np.zeros(2) + index,
                "realized_left_gripper_joint_qvel": np.zeros(2),
                "realized_right_gripper_joint_qvel": np.zeros(2),
                "realized_left_gripper_joint_qf": np.zeros(2) + 0.1 * index,
                "realized_right_gripper_joint_qf": np.zeros(2) + 0.2 * index,
                "left_gripper_joint_drive_target_error": np.zeros(2),
                "right_gripper_joint_drive_target_error": np.zeros(2),
                "left_gripper_joint_drive_velocity_error": np.zeros(2),
                "right_gripper_joint_drive_velocity_error": np.zeros(2),
                "estimated_left_gripper_joint_drive_effort": np.zeros(2),
                "estimated_right_gripper_joint_drive_effort": np.zeros(2),
                "left_gripper_joint_drive_stiffness": np.ones(2) * 100,
                "right_gripper_joint_drive_stiffness": np.ones(2) * 100,
                "left_gripper_joint_drive_damping": np.ones(2) * 10,
                "right_gripper_joint_drive_damping": np.ones(2) * 10,
                "left_gripper_joint_drive_force_limit": np.ones(2) * 50,
                "right_gripper_joint_drive_force_limit": np.ones(2) * 50,
                "left_gripper_joint_drive_mode": ("force", "force"),
                "right_gripper_joint_drive_mode": ("force", "force"),
                "selected_gripper_contact": True,
                "selected_gripper_contact_count": 1,
                "selected_gripper_contact_impulse": 0.1,
                "selected_contact_actor_name": "object",
                "contact_pairs": [],
                "role_actor_poses": {"main": np.zeros(7)},
                "role_actor_linear_velocities": {"main": np.zeros(3)},
                "role_actor_angular_velocities": {"main": np.zeros(3)},
                "role_actor_linear_velocity_measured": {"main": False},
                "role_actor_angular_velocity_measured": {"main": False},
                "role_actor_component_linear_velocities": {"main": np.ones(3) * 9.0},
                "role_actor_component_angular_velocities": {"main": np.ones(3) * 7.0},
                "role_actor_component_linear_velocity_measured": {"main": True},
                "role_actor_component_angular_velocity_measured": {"main": True},
                "role_actor_component_velocity_provenance": {
                    "main": {
                        "linear": {"component_type": "DummyRigid", "gate_signal": False},
                        "angular": {"component_type": "DummyRigid", "gate_signal": False},
                    }
                },
            })
        streams, audit = trace_rows_to_raw_streams(rows)
        validate_raw_streams(streams)
        validate_audit_streams(audit, 2)
        self.assertEqual(streams["controller_effective_setpoint"].shape, (2, 26))
        self.assertEqual(streams["realized_qpos"].shape, (3, 14))
        np.testing.assert_allclose(streams["action_interval_start_timestamps"], [0.0, 0.004])
        np.testing.assert_allclose(streams["action_interval_end_timestamps"], [0.004, 0.008])
        np.testing.assert_allclose(streams["state_timestamps"], [0.0, 0.004, 0.008])
        self.assertEqual(audit["object_pose"].shape, (3, 7))
        self.assertEqual(audit["realized_left_gripper_joint_qpos"].shape, (3, 2))
        self.assertEqual(audit["left_gripper_joint_drive_target"].shape, (3, 2))
        self.assertEqual(audit["realized_joint_qf"].shape, (3, 14))
        self.assertEqual(audit["realized_left_gripper_joint_qf"].shape, (3, 2))
        self.assertEqual(audit["realized_left_gripper_joint_qvel"].shape, (3, 2))
        self.assertEqual(audit["left_gripper_joint_drive_target_error"].shape, (3, 2))
        self.assertEqual(audit["estimated_left_gripper_joint_drive_effort"].shape, (3, 2))
        self.assertEqual(audit["selected_contact_actor_name"].tolist(), ["object"] * 3)
        np.testing.assert_allclose(audit["object_linear_velocity"], 0.0)
        np.testing.assert_allclose(audit["object_component_linear_velocity"], 9.0)
        self.assertTrue(np.all(audit["object_component_linear_velocity_measured"]))
        self.assertIn("DummyRigid", audit["object_component_velocity_provenance_json"][0])
        self.assertEqual(audit["role_object_pose__main"].shape, (3, 7))
        np.testing.assert_allclose(audit["role_object_linear_velocity__main"], 0.0)
        np.testing.assert_allclose(audit["role_object_component_linear_velocity__main"], 9.0)
        real_provenance = {
            "synthetic": False,
            "trace_schema_version": "cmf_runtime_trace_pose_consistent_velocity_effort_v3",
            "trace_role_names": ["main"],
        }
        validate_real_runtime_audit_fields(audit, real_provenance)
        with self.assertRaisesRegex(ValueError, "exact trace schema"):
            validate_real_runtime_audit_fields(
                audit, {"synthetic": False, "trace_role_names": ["main"]}
            )
        missing = dict(audit)
        missing.pop("object_component_linear_velocity")
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            validate_real_runtime_audit_fields(
                missing,
                real_provenance,
            )
        missing_role = {
            key: value
            for key, value in audit.items()
            if not key.startswith("role_object_")
        }
        with self.assertRaisesRegex(ValueError, "role bundle"):
            validate_real_runtime_audit_fields(missing_role, real_provenance)
        missing_role_pose = dict(audit)
        missing_role_pose.pop("role_object_pose__main")
        with self.assertRaisesRegex(ValueError, "missing required field"):
            validate_real_runtime_audit_fields(
                missing_role_pose, real_provenance
            )
        wrong_role_shape = dict(audit)
        wrong_role_shape["role_object_linear_velocity__main"] = np.zeros((3, 1))
        with self.assertRaisesRegex(ValueError, "must have shape"):
            validate_real_runtime_audit_fields(
                wrong_role_shape, real_provenance
            )
        wrong_rows = dict(audit)
        wrong_rows["object_linear_velocity"] = wrong_rows["object_linear_velocity"][:-1]
        with self.assertRaisesRegex(ValueError, "must have 3 rows"):
            validate_audit_streams(wrong_rows, 2)
        probe = PreTraceProbe()
        probe.trace = rows
        probe.markers = {"test": 1}
        probe.planner_queries = []
        probe.selected_gripper_links = lambda: ["finger"]
        temp_root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            path = Path(directory) / "trace.npz"
            probe.save_trace(path)
            with np.load(path, allow_pickle=False) as saved:
                self.assertIn("role_object_pose__main", saved.files)
                self.assertIn("role_object_component_linear_velocity__main", saved.files)
                sources = json.loads(str(saved["field_sources_json"].item()))
                self.assertIn("role_object_component_velocity_provenance_json__main", sources)
        self.assertFalse(np.shares_memory(streams["controller_effective_setpoint"], streams["requested_command"]))

    def test_realized_gripper_qpos_comes_from_articulation_state(self):
        left_joints = [DummyJoint("left_arm"), DummyJoint("left_finger_a"), DummyJoint("left_finger_b")]
        right_joints = [DummyJoint("right_arm"), DummyJoint("right_finger_a"), DummyJoint("right_finger_b")]
        robot = type("Robot", (), {})()
        robot.left_entity = DummyEntity(left_joints, [0.1, 0.21, 0.22])
        robot.right_entity = DummyEntity(right_joints, [0.2, 0.31, 0.32])
        robot.left_gripper = [(left_joints[1], 1, 0), (left_joints[2], 1, 0)]
        robot.right_gripper = [(right_joints[1], 1, 0), (right_joints[2], 1, 0)]
        np.testing.assert_allclose(_gripper_joint_qpos(robot, "left"), [0.21, 0.22])
        np.testing.assert_allclose(_gripper_joint_qpos(robot, "right"), [0.31, 0.32])
        robot.left_entity.qf = np.asarray([1.0, 2.1, 2.2])
        robot.right_entity.qf = np.asarray([2.0, 3.1, 3.2])
        np.testing.assert_allclose(_gripper_joint_qf(robot, "left"), [2.1, 2.2])
        np.testing.assert_allclose(_gripper_joint_qf(robot, "right"), [3.1, 3.2])
        np.testing.assert_allclose(_gripper_joint_qvel(robot, "left"), [0.21, 0.22])
        np.testing.assert_allclose(_gripper_joint_qvel(robot, "right"), [0.31, 0.32])

    def test_actor_to_eef_mapping_preserves_frozen_grasp_transform(self):
        current_eef = [0.0, 0.0, 1.0, 1, 0, 0, 0]
        current_actor = [0.1, 0.0, 0.9, 1, 0, 0, 0]
        target_actor = [0.3, -0.2, 0.8, 1, 0, 0, 0]
        target_eef = actor_target_to_eef_pose(current_eef, current_actor, target_actor)
        np.testing.assert_allclose(relative_pose(current_eef, current_actor), relative_pose(target_eef, target_actor), atol=1e-9)
        np.testing.assert_allclose(target_eef[:3], [0.2, -0.2, 0.9], atol=1e-9)

    def test_true_cavity_and_staged_non_target_verifiers(self):
        container = [0, 0, 0, 1, 0, 0, 0]
        actor = [0, 0.047, 0, 1, 0, 0, 0]
        inside = verify_true_cavity_obb(actor, [0.022] * 3, container, PLASTICBOX_BASE3_CAVITY)
        self.assertTrue(inside["pass_true_cavity_obb"])
        actor[1] = 0.020
        self.assertFalse(verify_true_cavity_obb(actor, [0.022] * 3, container, PLASTICBOX_BASE3_CAVITY)["pass_true_cavity_obb"])
        staged = verify_staged_non_target_displacement(
            {"green": [0, 0, 0]},
            {"after_grasp": {"green": [0.001, 0, 0]}, "after_transport": {"green": [0.02, 0, 0]}},
            0.01,
        )
        self.assertFalse(staged["pass"])
        self.assertEqual(staged["first_violation"]["stage"], "after_transport")

    def test_swept_path_and_real_planner_selection_contract(self):
        obstacles = {"neighbor": {"lower": [-0.03, -0.03, 0.77], "upper": [0.03, 0.03, 0.83]}}
        direct = swept_path_collisions([[-0.2, 0, 0.8], [0.2, 0, 0.8]], [0.01] * 3, obstacles)
        high = swept_path_collisions([[-0.2, 0, 0.8], [-0.2, 0, 1.0], [0.2, 0, 1.0], [0.2, 0, 0.8]], [0.01] * 3, obstacles)
        self.assertFalse(direct["pass"])
        self.assertTrue(high["pass"])
        decision = select_first_verified_pose([
            {"candidate_id": "hardcoded_only", "workspace_pass": True, "swept_collision_free": True, "left_arm_reach_provisional": True, "planner_status": "not_run"},
            {"candidate_id": "planner_verified", "workspace_pass": True, "swept_collision_free": True, "planner_status": "Success"},
        ])
        self.assertEqual(decision["selected"]["candidate_id"], "planner_verified")

    def test_quaternion_angular_velocity_and_f3_return_gate(self):
        velocity = quaternion_angular_velocity([1, 0, 0, 0], [np.sqrt(0.5), 0, 0, np.sqrt(0.5)], 1.0)
        np.testing.assert_allclose(velocity, [0, 0, np.pi / 2], atol=1e-9)
        required = PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]
        gate = verify_return_equivalence(
            position_error=0.001,
            orientation_error=0.001,
            rest_position_error=0.001,
            rest_orientation_error=0.001,
            stable_speed_samples=[0.0] * required,
            support_contact_samples=[True] * required,
            gripper_open=True,
            thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
            eef_linear_speed=0.0,
            eef_angular_speed=0.0,
        )
        self.assertTrue(gate["pass"])
        failed = verify_return_equivalence(
            position_error=0.001,
            orientation_error=1.0,
            rest_position_error=0.001,
            rest_orientation_error=0.001,
            stable_speed_samples=[0.0] * required,
            support_contact_samples=[True] * required,
            gripper_open=True,
            thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
            eef_linear_speed=0.0,
            eef_angular_speed=0.0,
        )
        self.assertFalse(failed["pass"])
        event = {
            "eef_positive_amplitude": 0.05,
            "eef_negative_amplitude": 0.05,
            "bottle_positive_amplitude": 0.05,
            "bottle_negative_amplitude": 0.05,
            "eef_max_off_axis": 0.005,
            "bottle_max_off_axis": 0.005,
            "eef_return_error": 0.005,
            "bottle_return_error": 0.005,
            "bottle_orientation_drift": 0.01,
            "selected_gripper_contact_fraction": 1.0,
            "contact_break_count": 0,
        }
        self.assertTrue(verify_realized_motion_metrics({"V": event, "H": event}, PROVISIONAL_RUNTIME_THRESHOLDS)["pass"])
        event["contact_break_count"] = 1
        self.assertFalse(verify_realized_motion_metrics({"V": event}, PROVISIONAL_RUNTIME_THRESHOLDS)["pass"])

    def test_f4_tray_footprint_and_runtime_probe_scope(self):
        footprint = footprint_inside_local_region(
            [-0.0745, 0.030, 0.0, 1, 0, 0, 0],
            [0.022] * 3,
            [0, 0, 0, 1, 0, 0, 0],
            TRAY_BASE0_SUPPORT_REGION["lower_m"],
            TRAY_BASE0_SUPPORT_REGION["upper_m"],
            TRAY_BASE0_SUPPORT_REGION["horizontal_axes"],
        )
        self.assertTrue(footprint["pass_support_footprint"])
        self.assertEqual(RUNTIME_V2_PROBE_VARIANTS["F4"], ("common_prefix_mapping",))
        required = PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"]
        common = verify_common_prefix(
            footprint_result=footprint,
            support_contact_samples=[True] * required,
            stable_speed_samples=[0.0] * required,
            neutral_return_error=0.0,
            neutral_orientation_error=0.0,
            non_target_result={"pass": True},
            gripper_open=True,
            thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
            eef_linear_speed=0.0,
            eef_angular_speed=0.0,
        )
        self.assertTrue(common["pass"])

    def test_f2_beside_gate_requires_rest_pose_and_stationarity(self):
        gate = verify_beside_final_state(
            inside=False,
            on=False,
            beside=True,
            support_contact=True,
            stable_speed_window=True,
            gripper_open=True,
            rest_position_error=0.0,
            rest_orientation_error=0.0,
            eef_linear_speed=0.0,
            eef_angular_speed=0.0,
            thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
        )
        self.assertTrue(gate["pass"])
        gate = verify_beside_final_state(
            inside=False,
            on=False,
            beside=True,
            support_contact=True,
            stable_speed_window=True,
            gripper_open=True,
            rest_position_error=0.0,
            rest_orientation_error=1.0,
            eef_linear_speed=0.0,
            eef_angular_speed=0.0,
            thresholds=PROVISIONAL_RUNTIME_THRESHOLDS,
        )
        self.assertFalse(gate["pass"])

    def test_gpu_guard_scope_and_missing_child_receipt_fail_closed(self):
        self.assertEqual(ALLOWED_PHYSICAL_GPU_INDICES, tuple(range(8)))
        status, code = classify_terminal_status(
            child_started=True,
            receipt_updated=False,
            receipt_update_error=None,
            cleanup_uncertain=False,
            timed_out=False,
            child_exit=0,
        )
        self.assertEqual((status, code), ("failed_missing_child_receipt", 91))
        pre = {"memory_used_mib": 14, "compute_processes": []}
        released = verify_post_release(pre, {"memory_used_mib": 14, "utilization_percent": 0, "pstate": "P0", "compute_processes": []})
        self.assertTrue(released["verified"])
        claimed = verify_post_release(pre, {"memory_used_mib": 4000, "utilization_percent": 90, "pstate": "P2", "compute_processes": [{"pid": 99}]})
        self.assertFalse(claimed["verified"])
        self.assertEqual(claimed["new_compute_processes"][0]["pid"], 99)

    def test_gpu_guard_child_environment_rejects_host_cuda_12_2(self):
        environment = build_child_environment(
            {"PATH": "/share/apps/cuda/12.2/bin:/usr/bin", "LD_LIBRARY_PATH": "/share/apps/cuda/12.2/lib64"},
            "GPU-test",
            workspace="/nfs_share/lijunhui/Robotwin2",
        )
        self.assertNotIn("LD_LIBRARY_PATH", environment)
        self.assertNotIn("/share/apps/cuda", environment["PATH"])
        self.assertEqual(environment["CUDA_HOME"], "/nfs_share/lijunhui/Robotwin2/tools/cuda-12.1")
        self.assertEqual(environment["CUDA_VISIBLE_DEVICES"], "GPU-test")

    def test_gpu_guard_updates_top_level_v3_1_child_receipt(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "child"
            output.mkdir()
            receipt_path = output / "receipt.json"
            receipt_path.write_text(
                '{"status":"accepted","scene_created":true,"scene_cleanup_succeeded":true}\n',
                encoding="utf-8",
            )
            updated = update_child_receipt(
                output,
                Path(directory) / "guard.json",
                {"memory_used_mib": 14, "compute_processes": []},
                [],
                {"verified": True, "checks": {}},
            )
            self.assertTrue(updated)
            payload = __import__("json").loads(receipt_path.read_text())
            self.assertEqual(payload["orphan_process_count"], 0)
            self.assertTrue(payload["gpu_postcheck_release"]["verified"])
            receipt_path.write_text(
                '{"status":"accepted","scene_created":true,"scene_cleanup_succeeded":true,"orphan_process_count":2}\n',
                encoding="utf-8",
            )
            update_child_receipt(
                output,
                Path(directory) / "guard.json",
                {"memory_used_mib": 14, "compute_processes": []},
                [],
                {"verified": True, "checks": {}},
            )
            payload = __import__("json").loads(receipt_path.read_text())
            self.assertEqual(payload["scene_orphan_process_count"], 2)
            self.assertEqual(payload["orphan_process_count"], 2)
            self.assertEqual(payload["status"], "failed_cleanup_uncertain")

    def test_selected_arm_contact_and_f3_consistency(self):
        self.assertTrue(is_selected_gripper_contact("bottle", {"left_finger"}, ("bottle", "left_finger")))
        self.assertFalse(is_selected_gripper_contact("bottle", {"left_finger"}, ("bottle", "right_finger")))
        points = np.asarray([[0, 0, 0], [0, 0, 0.1], [0, 0, -0.1], [0, 0, 0]])
        self.assertTrue(verify_eef_bottle_axis_consistency(points, points * 0.9, 2)["pass"])

    def test_f4_non_target_and_slot_preservation(self):
        self.assertTrue(verify_non_target_displacement([0, 0, 0], [0.001, 0, 0], 0.01))
        self.assertTrue(verify_completed_slots_preserved({"A": True, "B": False}, {"A": True, "B": True})["pass"])
        self.assertFalse(verify_completed_slots_preserved({"A": True}, {"A": False})["pass"])

    def test_model_view_rejects_path_and_branch_leakage(self):
        sample = {
            "current_rgb": 1,
            "current_robot_state": 2,
            "future_effective_setpoints": 3,
            "candidate_program_semantics": 4,
            "visible_referring_expressions": 5,
        }
        self.assertNotIn("branch_id", build_model_view(sample))
        sample["branch_id"] = "F2-inside"
        with self.assertRaises(ValueError):
            build_model_view(sample)

    def test_state_machine_and_finalizer_fail_closed(self):
        machine = AttemptStateMachine()
        machine.transition("scene_built")
        machine.transition("candidates_frozen")
        machine.transition("anchor_reconstructed")
        machine.transition("rolling_out")
        machine.transition("raw_saved")
        machine.transition("verified")
        machine.transition("accepted")
        self.assertTrue(machine.terminal)
        result = finalize_nonformal_integration({"same_current_pass": True})
        self.assertFalse(result["accepted"])

    def test_implementation_error_is_terminal_from_each_attempt_phase(self):
        for phase_path in (
            (),
            ("scene_built",),
            ("scene_built", "candidates_frozen"),
            (
                "scene_built",
                "candidates_frozen",
                "anchor_reconstructed",
            ),
            (
                "scene_built",
                "candidates_frozen",
                "anchor_reconstructed",
                "rolling_out",
            ),
            (
                "scene_built",
                "candidates_frozen",
                "anchor_reconstructed",
                "rolling_out",
                "raw_saved",
            ),
            (
                "scene_built",
                "candidates_frozen",
                "anchor_reconstructed",
                "rolling_out",
                "raw_saved",
                "verified",
            ),
        ):
            machine = AttemptStateMachine()
            for state in phase_path:
                machine.transition(state)
            machine.transition("failed_implementation_error")
            self.assertTrue(machine.terminal)
            with self.assertRaises(RuntimeError):
                machine.transition("accepted")


if __name__ == "__main__":
    unittest.main()
