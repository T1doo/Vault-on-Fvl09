import tempfile
import unittest
from pathlib import Path
import hashlib

import numpy as np

from controlled_multi_future.anchor import capture_physical_anchor_v2, compare_anchors
from controlled_multi_future.current_hasher import build_current_hashes_v2, require_same_current
from controlled_multi_future.families import F1ObjectSelection
from controlled_multi_future.probes.pipeline_dry_run import SyntheticAdapter
from controlled_multi_future.raw_writer import (
    RAW_SCHEMA_VERSION,
    validate_simulator_timing,
    verify_raw_artifact_integrity,
    write_raw_attempt,
)
from controlled_multi_future.runtime_v3_1_contracts import (
    GPU_PROBE_AUTHORIZED,
    IMPLEMENTATION_VERSION,
    RAW_LAYOUT_VERSION,
    RUNTIME_V3_1_BUDGET_PROPOSAL,
    STAGE0_AUTHORIZED,
    classify_f3_release_dynamics_v3_1,
    minimum_f4_safe_carry_height,
    select_first_f2_chained_candidate,
    validate_f1_executed_prefixes,
    validate_f4_route_results,
)


def camera_configuration():
    camera = {
        "resolution": [640, 480],
        "intrinsics_or_fov": {"fovy_rad": 1.0},
        "extrinsics": np.eye(4).tolist(),
        "mount_link": "world",
        "near_far": [0.1, 100.0],
    }
    return {
        "camera_names": ["head_camera", "left_camera", "right_camera"],
        "cameras": {name: dict(camera) for name in ("head_camera", "left_camera", "right_camera")},
        "renderer_version": "sapien-test",
        "render_settings": {"shader": "rt", "spp": 32},
    }


def physical_entities():
    return {
        "red": {
            "role": "red",
            "actor_name": "f1_red_block",
            "modelname": "project_create_box",
            "model_id": "rgb_red",
            "visual_asset_hash": "visual-red-v1",
            "collision_asset_hash": "collision-box-v1",
            "scale": [1, 1, 1],
            "static_or_dynamic": "dynamic",
            "mass": 0.1,
            "friction": {"static": 0.5, "dynamic": 0.5},
            "collision_mode": "box",
            "pose": [0, 0, 0, 1, 0, 0, 0],
            "linear_velocity": [0, 0, 0],
            "angular_velocity": [0, 0, 0],
            "sleep_state": True,
        }
    }


def current_v2():
    return build_current_hashes_v2(
        head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
        model_visible_robot_state=np.zeros(14),
        gripper_actual_state=np.zeros(4),
        visible_object_roles={"red": {"visible_name": "red block"}},
        camera_configuration=camera_configuration(),
        physical_entities=physical_entities(),
        scene_seed=1,
        generator_version="test-v3_1",
        simulation_configuration={"timestep": 0.004, "solver": "physx"},
        source_commit="c3ddfa8b97d5519efa828b075999bd0006778e5e",
    )


def physical_anchor(*, quaternion=(1, 0, 0, 0), velocity=(0, 0, 0)):
    return capture_physical_anchor_v2(
        robot_qpos=np.zeros(14),
        robot_qvel=np.zeros(14),
        robot_drive_target=np.zeros(14),
        gripper_joint_qpos=np.zeros(4),
        actor_states={
            "red": {
                "pose": [0, 0, 0, *quaternion],
                "linear_velocity": velocity,
                "angular_velocity": [0, 0, 0],
                "sleep_state": True,
            }
        },
        facility_poses={"box": [0, 0, 0, 1, 0, 0, 0]},
        physics_config={"timestep": 0.004, "solver": "physx"},
        source_commit="c3ddfa8b97d5519efa828b075999bd0006778e5e",
        metadata={"seed": 1},
    )


def prefix_evidence(role, action_hash="a" * 64, neutral_steps=1):
    anchor = physical_anchor()
    return {
        "target_role": role,
        "target_role_visible_during_prefix": False,
        "executed_prefix_action_sha256": action_hash,
        "executed_prefix_step_count": 2,
        "executed_prefix_start_state_sha256": "b" * 64,
        "executed_prefix_end_state_sha256": "c" * 64,
        "executed_prefix_start_anchor": anchor,
        "executed_prefix_end_anchor": anchor,
        "canonical_prefix_end_step": 2,
        "first_post_prefix_divergence_step": 2,
        "neutral_confirmation_step_count": neutral_steps,
        "neutral_confirmation_minimum_required_steps": 1,
    }


def f2_candidate(index, *, success=False):
    pre_end = f"pre-end-{index}"
    return {
        "candidate_id": f"f2_pose_{index}",
        "main_object": "071_can/base1",
        "arm": "left",
        "reference": "074_displaystand/base3",
        "planner_reset_receipt": {
            "reset_performed": True,
            "planner_seed": 20260828,
            "rng_state_after_reset_sha256": "same-reset-state",
            "planner_instance_id": f"fresh-planner-{index}",
        },
        "preplace_start_qpos_sha256": "common-start",
        "preplace_end_qpos_sha256": pre_end,
        "release_start_qpos_sha256": pre_end,
        "release_end_qpos_sha256": f"release-end-{index}",
        "chain_continuity_pass": True,
        "preplace_planner_status": "Success" if success else "Fail",
        "release_planner_status": "Success" if success else "Fail",
        "upright_axis_audited": success,
        "joint_limit_margin_pass": success,
        "carried_swept_geometry_pass": success,
        "facility_distance_pass": success,
    }


def f3_samples(*, before=0.0, intermediate=0.0, final=0.0, final_pass=True):
    names = (
        "before_release",
        "after_release_1",
        "after_release_5",
        "after_release_10",
        "after_release_25",
        "after_release_50",
        "after_release_125",
        "after_release_250",
        "after_rest",
    )
    result = {}
    for index, name in enumerate(names):
        value = before if index == 0 else final if index == len(names) - 1 else intermediate
        result[name] = {
            "sample_step": index,
            "bottle_position_error_m": value,
            "bottle_orientation_error_rad": 0.0,
            "eef_tracking_error_m": 0.0,
            "eef_tracking_applicable": index == 0,
            "bottle_linear_speed_mps": 0.0,
            "bottle_angular_speed_rps": 0.0,
            "bottle_footprint_inside_pad": final_pass,
            "bottle_pad_contact_count": 1 if final_pass else 0,
            "bottle_pad_contact_normals": [[0, 0, 1]] if final_pass else [],
            "bottle_pad_contact_impulse": 0.1 if final_pass else 0.0,
            "selected_gripper_contact": index == 0,
            "actual_gripper_joint_qpos": [0.0, 0.0],
            "stable_window_pass": final_pass,
            "support_pass": final_pass,
        }
    return result


def grasp_transform(*, stable=True):
    return {
        "initial_T_eef_actor": [0, 0, 0, 1, 0, 0, 0],
        "before_release_T_eef_actor": [0, 0, 0, 1, 0, 0, 0],
        "grasp_transform_translation_drift": 0.0 if stable else 0.02,
        "grasp_transform_orientation_drift": 0.0,
        "grasp_transform_stable": stable,
    }


def route(route_id, scene_id, *, success=False, cleanup=True, terminal="failed_planner"):
    return {
        "route_id": route_id,
        "scene_instance_id": scene_id,
        "scene_current_sha256": "current",
        "route_start_anchor_sha256": "anchor",
        "segment_receipts": [
            {"segment_id": "s0", "start_qpos_sha256": "q0", "end_qpos_sha256": "q1", "planner_status": "Success" if success else "Fail", "executed": success},
            {"segment_id": "s1", "start_qpos_sha256": "q1", "end_qpos_sha256": "q2", "planner_status": "Success" if success else "Fail", "executed": success},
        ],
        "carry_envelope_version": "common_x_plus_selected_left_gripper_v1",
        "semantic_probe_pass": success,
        "cleanup_pass": cleanup,
        "terminal_status": terminal,
        "tray_pose_changed": False,
    }


class RuntimeV3_1ContractsTest(unittest.TestCase):
    def test_version_and_authorization_are_closed(self):
        self.assertEqual(IMPLEMENTATION_VERSION, "controlled_multi_future_runtime_v3_1")
        self.assertEqual(RAW_SCHEMA_VERSION, "cmf_raw_attempt_v2_1_1")
        self.assertEqual(RAW_LAYOUT_VERSION, "controller_effective_setpoint_v1_layout_v2_1")
        self.assertFalse(GPU_PROBE_AUTHORIZED)
        self.assertFalse(STAGE0_AUTHORIZED)
        self.assertFalse(RUNTIME_V3_1_BUDGET_PROPOSAL["approved"])
        self.assertEqual(RUNTIME_V3_1_BUDGET_PROPOSAL["A0"]["planner_query_limit"], 0)

    def test_real_timestep_contract_is_not_step_index_self_proof(self):
        good = {
            "simulator_timing": {
                "simulator_timestep_seconds": 0.004,
                "control_steps_per_action": 1,
                "effective_action_interval_seconds": 0.004,
                "scene_timestep_source": "SAPIEN Scene.get_timestep()",
            }
        }
        self.assertEqual(validate_simulator_timing(good)["control_steps_per_action"], 1)
        good["simulator_timing"]["simulator_timestep_seconds"] = 0.002
        good["simulator_timing"]["control_steps_per_action"] = 2
        with self.assertRaisesRegex(ValueError, "requires a real 0.004"):
            validate_simulator_timing(good)

    def test_raw_artifact_hashes_are_bound(self):
        adapter = SyntheticAdapter()
        program = F1ObjectSelection().checked_provisional_programs()[0]
        rollout = adapter.rollout(None, program, {"realization": "r_pc"})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw"
            manifest = write_raw_attempt(output, rollout["streams"], rollout["audit_streams"], rollout["provenance"])
            self.assertEqual(manifest["schema_version"], "cmf_raw_attempt_v2_1_1")
            self.assertEqual(len(manifest["raw_streams_npz_sha256"]), 64)
            self.assertEqual(len(manifest["manifest_file_sha256"]), 64)
            self.assertEqual(len(manifest["manifest_integrity_sidecar_sha256"]), 64)
            self.assertEqual(len(manifest["trace_source_sha256"]), 64)
            self.assertTrue(verify_raw_artifact_integrity(output)["pass"])
            with (output / "raw_streams.npz").open("ab") as handle:
                handle.write(b"tamper")
            self.assertFalse(verify_raw_artifact_integrity(output)["pass"])

    def test_real_trace_source_path_is_rehashed(self):
        adapter = SyntheticAdapter()
        program = F1ObjectSelection().checked_provisional_programs()[0]
        rollout = adapter.rollout(None, program, {"realization": "r_pc"})
        with tempfile.TemporaryDirectory() as directory:
            attempt = Path(directory) / "attempt"
            attempt.mkdir()
            trace = attempt / "trace_source.npz"
            trace.write_bytes(b"independent dense trace source")
            rollout["provenance"]["trace_source_sha256"] = hashlib.sha256(trace.read_bytes()).hexdigest()
            rollout["provenance"]["trace_source_relative_path"] = "../trace_source.npz"
            raw_dir = attempt / "raw"
            write_raw_attempt(raw_dir, rollout["streams"], rollout["audit_streams"], rollout["provenance"])
            self.assertTrue(verify_raw_artifact_integrity(raw_dir)["pass"])
            trace.write_bytes(b"tampered trace source")
            self.assertFalse(verify_raw_artifact_integrity(raw_dir)["pass"])

    def test_planner_goal_is_bound_to_query_id_and_active_interval(self):
        adapter = SyntheticAdapter()
        program = F1ObjectSelection().checked_provisional_programs()[0]
        rollout = adapter.rollout(None, program, {"realization": "r_pc"})
        goal = np.asarray([0.1, 0.2, 0.3, 1, 0, 0, 0], dtype=float)
        rollout["streams"]["planner_goal_eef_pose"][:, :7] = goal
        rollout["streams"]["field_metadata"]["planner_goal_eef_pose"] = {
            "status": "commanded",
            "source": "test active left_move_to_pose planner goal",
        }
        audit = rollout["audit_streams"]
        audit["planner_goal_available"][:, 0] = True
        audit["planner_goal_active"][:, 0] = True
        audit["planner_query_id"][:, 0] = 1
        audit["planner_goal_source"][:, 0] = "left_move_to_pose"
        audit["planner_goal_start_step"][:, 0] = 0
        audit["planner_goal_end_step"][:, 0] = 4
        rollout["provenance"]["planner_queries"] = [
            {
                "query_id": 1,
                "arm": "left",
                "source": "left_move_to_pose",
                "goal_eef_pose": goal.tolist(),
                "status": "Success",
                "start_step": 0,
                "end_step": 4,
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            write_raw_attempt(Path(directory) / "pass", rollout["streams"], audit, rollout["provenance"])
            audit["planner_query_id"][2, 0] = 7
            with self.assertRaisesRegex(ValueError, "matching query-table"):
                write_raw_attempt(Path(directory) / "fail", rollout["streams"], audit, rollout["provenance"])

    def test_actual_camera_configuration_changes_current_hash(self):
        reference = current_v2()
        candidate_kwargs = camera_configuration()
        candidate_kwargs["cameras"]["head_camera"]["extrinsics"] = (np.eye(4) + 0.1).tolist()
        changed = build_current_hashes_v2(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            model_visible_robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            visible_object_roles={"red": {"visible_name": "red block"}},
            camera_configuration=candidate_kwargs,
            physical_entities=physical_entities(),
            scene_seed=1,
            generator_version="test-v3_1",
            simulation_configuration={"timestep": 0.004, "solver": "physx"},
            source_commit="c3ddfa8b97d5519efa828b075999bd0006778e5e",
        )
        with self.assertRaises(ValueError):
            require_same_current(reference, changed)
        self.assertFalse(reference["model_input_allows_hidden_physical_components"])

    def test_hidden_physics_changes_do_not_enter_model_visible_hash(self):
        reference = current_v2()
        entities = physical_entities()
        entities["red"]["mass"] = 0.2
        changed = build_current_hashes_v2(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            model_visible_robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            visible_object_roles={"red": {"visible_name": "red block"}},
            camera_configuration=camera_configuration(),
            physical_entities=entities,
            scene_seed=1,
            generator_version="test-v3_1",
            simulation_configuration={"timestep": 0.004, "solver": "physx"},
            source_commit="c3ddfa8b97d5519efa828b075999bd0006778e5e",
        )
        self.assertEqual(reference["model_visible_aggregate_sha256"], changed["model_visible_aggregate_sha256"])
        self.assertNotEqual(reference["hidden_physical_aggregate_sha256"], changed["hidden_physical_aggregate_sha256"])
        require_same_current(reference, changed)
        self.assertEqual(reference["aggregate_sha256"], changed["aggregate_sha256"])
        self.assertNotEqual(reference["audit_full_aggregate_sha256"], changed["audit_full_aggregate_sha256"])

    def test_anchor_quaternion_sign_and_actor_velocity(self):
        reference = physical_anchor(quaternion=(1, 0, 0, 0))
        same_rotation = physical_anchor(quaternion=(-1, 0, 0, 0))
        self.assertTrue(compare_anchors(reference, same_rotation)["equivalent"])
        moving = physical_anchor(velocity=(0.01, 0, 0))
        comparison = compare_anchors(reference, moving)
        self.assertFalse(comparison["equivalent"])
        self.assertIn("actor_linear_velocity:red", comparison["failures"])
        physics_changed = dict(reference)
        physics_changed["physics_config"] = {**reference["physics_config"], "solver": "different"}
        self.assertFalse(compare_anchors(reference, physics_changed)["equivalent"])

    def test_reconstruction_spec_change_fails_same_current(self):
        reference = current_v2()
        changed = build_current_hashes_v2(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            model_visible_robot_state=np.zeros(14),
            gripper_actual_state=np.zeros(4),
            visible_object_roles={"red": {"visible_name": "red block"}},
            camera_configuration=camera_configuration(),
            physical_entities=physical_entities(),
            scene_seed=1,
            generator_version="test-v3_1",
            simulation_configuration={"timestep": 0.004, "solver": "changed"},
            source_commit="c3ddfa8b97d5519efa828b075999bd0006778e5e",
        )
        with self.assertRaisesRegex(ValueError, "reconstruction_spec"):
            require_same_current(reference, changed)

    def test_f1_requires_actual_equal_prefix_and_minimum_hold(self):
        branches = [
            {"target_role": role, "executed_prefix": prefix_evidence(role), "semantic_probe_pass": True}
            for role in ("red", "green", "blue")
        ]
        self.assertTrue(validate_f1_executed_prefixes(branches)["pass"])
        branches[1]["executed_prefix"]["executed_prefix_action_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            validate_f1_executed_prefixes(branches)
        branches[1]["executed_prefix"] = prefix_evidence("green", neutral_steps=2)
        with self.assertRaisesRegex(ValueError, "neutral hold"):
            validate_f1_executed_prefixes(branches)

    def test_f2_requires_rng_reset_and_chained_qpos(self):
        results = [f2_candidate(index, success=index == 2) for index in range(6)]
        self.assertEqual(select_first_f2_chained_candidate(results)["selected"]["candidate_id"], "f2_pose_2")
        results[1]["release_start_qpos_sha256"] = "not-preplace-end"
        decision = select_first_f2_chained_candidate(results)
        self.assertFalse(decision["evaluated"][1]["checks"]["chain_continuity"])
        results[1]["planner_reset_receipt"]["reset_performed"] = False
        with self.assertRaisesRegex(ValueError, "reset"):
            select_first_f2_chained_candidate(results)

    def test_f3_slip_and_transient_final_success_are_distinct(self):
        common = dict(
            position_tolerance_m=0.03,
            orientation_tolerance_rad=0.1,
            eef_tracking_tolerance_m=0.01,
            grasp_translation_drift_tolerance_m=0.005,
            grasp_orientation_drift_tolerance_rad=0.05,
        )
        slip = classify_f3_release_dynamics_v3_1(f3_samples(before=0.04, final=0.04, final_pass=False), grasp_transform(stable=False), **common)
        self.assertEqual(slip["classification"], "grasp_slip_or_contact_change")
        self.assertFalse(slip["actor_to_eef_correction_allowed"])
        transient = classify_f3_release_dynamics_v3_1(f3_samples(intermediate=0.04, final=0.0, final_pass=True), grasp_transform(), **common)
        self.assertEqual(transient["classification"], "transient_release_dynamics_final_equivalent")
        self.assertTrue(transient["final_return_equivalence"])
        incomplete = f3_samples()
        del incomplete["after_release_5"]["bottle_pad_contact_normals"]
        with self.assertRaisesRegex(ValueError, "bottle_pad_contact_normals"):
            classify_f3_release_dynamics_v3_1(incomplete, grasp_transform(), **common)

    def test_f4_routes_are_fresh_chained_and_cleanup_gated(self):
        height = minimum_f4_safe_carry_height(
            [0.8, 0.82],
            actor_half_height_m=0.022,
            gripper_below_eef_envelope_m=0.06,
            frozen_clearance_m=0.03,
        )
        self.assertAlmostEqual(height["safe_eef_or_actor_center_z"], 0.91)
        first = route("route1_minimum_height_segmented", "scene-1", success=False)
        second = route("route2_carry_neutral_fallback", "scene-2", success=True)
        self.assertTrue(validate_f4_route_results([first, second])["pass"])
        second["scene_instance_id"] = "scene-1"
        with self.assertRaisesRegex(ValueError, "distinct fresh"):
            validate_f4_route_results([first, second])
        second["scene_instance_id"] = "scene-2"
        first["cleanup_pass"] = False
        with self.assertRaisesRegex(ValueError, "cleanup uncertainty"):
            validate_f4_route_results([first, second])


if __name__ == "__main__":
    unittest.main()
