import unittest

import numpy as np

from controlled_multi_future.anchor import capture_anchor, compare_anchors
from controlled_multi_future.attempt_state_machine import AttemptStateMachine
from controlled_multi_future.candidate_freezer import freeze_candidate_universe
from controlled_multi_future.current_hasher import build_current_hashes, require_same_current
from controlled_multi_future.families import F1ObjectSelection, F2TargetRelation
from controlled_multi_future.finalizer import finalize_nonformal_integration
from controlled_multi_future.model_view import build_model_view
from controlled_multi_future.probe_contracts import FAMILY_VARIANTS as VARIANTS, result_passed
from controlled_multi_future.probes.lifecycle import initialize_cleanup_fields, managed_scene
from controlled_multi_future.probes.runtime_trace import DenseTraceMixin, is_selected_gripper_contact
from controlled_multi_future.raw_writer import pack_effective_setpoint, validate_raw_streams
from controlled_multi_future.verifiers import verify_completed_slots_preserved, verify_eef_bottle_axis_consistency, verify_non_target_displacement


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


class PipelineContractsTest(unittest.TestCase):
    def test_dense_trace_delegates_during_base_scene_setup(self):
        result = PreTraceProbe().take_dense_action({"setup": True}, save_freq=None)
        self.assertTrue(result["delegated"])
        self.assertEqual(result["control_seq"], {"setup": True})

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
        self.assertEqual(VARIANTS["F2"], ("sector1", "sector2", "pot_left"))
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
            wrist_rgb={"left": np.ones((1, 1, 3), dtype=np.uint8)},
            robot_state=np.arange(4, dtype=np.float64),
            object_role_layout={"red": [0, 1, 2]},
            scene_seed=7,
            generator_version="test_v1",
        )
        first = build_current_hashes(**kwargs)
        second = build_current_hashes(**kwargs)
        require_same_current(first, second)
        kwargs["robot_state"] = np.arange(4, dtype=np.float64) + 1
        with self.assertRaises(ValueError):
            require_same_current(first, build_current_hashes(**kwargs))

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
        action = pack_effective_setpoint(np.zeros(6), np.zeros(6), 1, np.zeros(6), np.zeros(6), 1)
        streams = {
            "controller_effective_setpoint": np.stack([action, action]),
            "requested_command": np.zeros((2, 26)),
            "planner_target": np.zeros((2, 26)),
            "gripper_command": np.zeros((2, 2)),
            "timestamps": np.arange(2) / 250,
            "component_masks": np.ones((2, 26)),
            "realized_qpos": np.zeros((3, 14)),
            "realized_qvel": np.zeros((3, 14)),
            "realized_eef": np.zeros((3, 14)),
        }
        validate_raw_streams(streams)
        streams["realized_qpos"] = np.zeros((2, 14))
        with self.assertRaises(ValueError):
            validate_raw_streams(streams)

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


if __name__ == "__main__":
    unittest.main()
