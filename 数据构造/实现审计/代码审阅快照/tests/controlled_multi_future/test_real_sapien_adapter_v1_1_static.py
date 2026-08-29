import hashlib
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

import numpy as np

from controlled_multi_future.family_runners_v3_1 import (
    F1RunnerV3_1,
    F2RunnerV3_1,
    _left_gripper_below_eef_envelope,
    _merge_left_arm_terminal_qpos,
    get_family_runner,
)
from controlled_multi_future.families import F2TargetRelation, F4SubtaskOrder
from controlled_multi_future.probes.runtime_v3_1_authorization import (
    load_runtime_v3_1_authorization,
    require_atomic_gpu_guard,
)
from controlled_multi_future.real_sapien_adapter_v1_1 import (
    RoboTwinRealSapienPilotRootAdapterV1_1,
    implementation_source_sha256,
)
from controlled_multi_future.root_orchestrator_v1_1 import RealSapienPilotRootAdapterV1_1


class RealSapienAdapterV1_1StaticTest(unittest.TestCase):
    def test_adapter_is_concrete_and_import_does_not_create_scene(self):
        self.assertTrue(issubclass(RoboTwinRealSapienPilotRootAdapterV1_1, RealSapienPilotRootAdapterV1_1))
        self.assertFalse(inspect.isabstract(RoboTwinRealSapienPilotRootAdapterV1_1))
        for family in ("F1", "F2", "F3", "F4"):
            adapter = RoboTwinRealSapienPilotRootAdapterV1_1(family=family, output_root=Path("/nfs_share/lijunhui/Robotwin2/tmp/static-only"))
            self.assertEqual(adapter.family, family)
            self.assertIs(adapter.runner, get_family_runner(family))
        first = implementation_source_sha256()
        self.assertEqual(first, implementation_source_sha256())
        self.assertEqual(len(first), 64)

    def test_f2_and_f4_planner_variants_are_preregistered(self):
        f2 = get_family_runner("F2")
        beside = next(item for item in F2TargetRelation().checked_provisional_programs() if item["program_id"] == "F2-beside")
        self.assertEqual(len(f2.planner_audit_variants(beside)), 6)
        self.assertEqual([item["variant_id"] for item in f2.planner_audit_variants(beside)], [f"f2_pose_{index}" for index in range(6)])
        f4 = get_family_runner("F4")
        program = F4SubtaskOrder().checked_provisional_programs()[0]
        self.assertEqual(
            [item["variant_id"] for item in f4.planner_audit_variants(program)],
            ["route1_minimum_height_segmented", "route2_carry_neutral_fallback"],
        )

    def test_f1_rollout_reads_target_only_after_actual_prefix_boundary(self):
        source = inspect.getsource(F1RunnerV3_1.rollout)
        boundary = source.index("prefix_end = anchor_capture(scene)")
        target_read = source.index('role = program["target_role"]')
        self.assertGreater(target_read, boundary)
        self.assertIn("scene.initialize_trace(scene.red", source[:boundary])
        self.assertNotIn('program["target_role"]', source[:boundary])
        self.assertNotIn("realization_spec[", source[:boundary])

    def test_f2_candidate_audit_uses_exactly_two_chained_queries(self):
        class MotionGen:
            def reset(self, reset_seed):
                self.reset_seed = reset_seed

        class Planner:
            def __init__(self):
                self.motion_gen = MotionGen()

        class Entity:
            def get_qpos(self):
                return np.zeros(2)

        class Robot:
            communication_flag = False

            def __init__(self):
                self.left_planner = Planner()
                self.left_entity = Entity()
                self.last_qpos_dtypes = []

            def left_plan_path(self, pose, last_qpos=None):
                self.last_qpos_dtypes.append(np.asarray(last_qpos).dtype)
                start = np.asarray(last_qpos, dtype=np.float32)
                return {"status": "Success", "position": np.stack((start, start + 1.0))}

        class Scene:
            def __init__(self):
                self.robot = Robot()
                self.planner_query_count = 0
                self.planner_queries = []

            def _reserve_planner_query(self):
                self.planner_query_count += 1
                if self.planner_query_count > self.planner_query_limit:
                    raise RuntimeError("query limit")
                return self.planner_query_count

        runner = F2RunnerV3_1()
        targets = [{"segment_id": f"s{index}", "pose": [0, 0, 0, 1, 0, 0, 0]} for index in range(7)]
        runner.build_targets = lambda scene, program, variant: (targets, {"relation": "beside"})
        result = runner.audit_planner_solvability(Scene(), {"program_id": "F2-beside"}, {"variant_id": "f2_pose_0"})
        self.assertTrue(result["planner_solvable"])
        self.assertEqual(result["planner_query_count"], 2)
        self.assertTrue(result["execution_spec"]["chain_continuity_pass"])
        self.assertEqual(Scene().robot.left_entity.get_qpos().dtype, np.float64)
        scene = Scene()
        runner.audit_planner_solvability(scene, {"program_id": "F2-beside"}, {"variant_id": "f2_pose_0"})
        self.assertEqual(scene.robot.last_qpos_dtypes, [np.dtype(np.float32), np.dtype(np.float32)])

    def test_arm_terminal_qpos_is_merged_into_full_articulation_state(self):
        class Joint:
            def __init__(self, name):
                self.name = name

            def get_name(self):
                return self.name

        arm = [Joint("a0"), Joint("a1")]
        gripper = Joint("finger")
        entity = type("Entity", (), {"get_active_joints": lambda self: [arm[0], gripper, arm[1]]})()
        robot = type("Robot", (), {"left_entity": entity, "left_arm_joints": arm})()
        scene = type("Scene", (), {"robot": robot})()
        merged = _merge_left_arm_terminal_qpos(scene, [0.0, 0.7, 0.0], [1.0, 2.0])
        np.testing.assert_allclose(merged, [1.0, 0.7, 2.0])

    def test_f4_gripper_envelope_comes_from_selected_runtime_links(self):
        class Pose:
            def __init__(self, z):
                self.p = np.asarray([0.0, 0.0, z])

        class Link:
            def __init__(self, name, z):
                self.name, self.pose = name, Pose(z)

            def get_name(self):
                return self.name

            def get_pose(self):
                return self.pose

        fixed = Link("left_fixed_finger", 0.92)
        moving = Link("left_moving_finger", 0.90)
        joint = type("Joint", (), {"child_link": moving})()
        entity = type("Entity", (), {"get_links": lambda self: [fixed, moving]})()
        robot = type(
            "Robot",
            (),
            {
                "left_fix_gripper_name": ["left_fixed_finger"],
                "left_gripper": [(joint, 1, 0)],
                "left_entity": entity,
                "get_left_ee_pose": lambda self: [0, 0, 1.0, 1, 0, 0, 0],
            },
        )()
        scene = type("Scene", (), {"robot": robot})()
        evidence = _left_gripper_below_eef_envelope(scene, conservative_link_margin_m=0.03)
        self.assertAlmostEqual(evidence["gripper_below_eef_envelope_m"], 0.13)
        self.assertEqual(evidence["selected_gripper_links"], ["left_fixed_finger", "left_moving_finger"])

    def test_gpu_authorization_receipt_is_required_and_content_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authorization.json"
            with self.assertRaises(PermissionError):
                load_runtime_v3_1_authorization(path, requested_scope="A0_current_anchor_smoke")
            payload = {
                "schema_version": "cmf_runtime_v3_1_gpu_authorization_v1",
                "implementation_version": "controlled_multi_future_runtime_v3_1",
                "approved": True,
                "stage0_authorized": False,
                "formal_data": False,
                "stage0_data": False,
                "approved_scopes": ["A0_current_anchor_smoke"],
            }
            payload["receipt_sha256"] = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(load_runtime_v3_1_authorization(path, requested_scope="A0_current_anchor_smoke")["approved"])
            payload["approved_scopes"].append("F1_bounded_nonformal_probe")
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "SHA-256"):
                load_runtime_v3_1_authorization(path, requested_scope="A0_current_anchor_smoke")

    def test_atomic_guard_receipt_is_required_and_must_be_fresh_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "guard.json"
            receipt = {
                "schema_version": "cmf_gpu_guard_v2",
                "status": "precheck_passed",
                "physical_gpu_index": 4,
                "expected_gpu_uuid": "GPU-test",
                "guard_pid": os.getppid(),
                "precheck": {
                    "physical_index": 4,
                    "uuid": "GPU-test",
                    "memory_used_mib": 14,
                    "utilization_percent": 0,
                    "pstate": "P8",
                    "compute_processes": [],
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            path.write_text(json.dumps(receipt), encoding="utf-8")
            environment = {
                "CMF_GPU_GUARD_RECEIPT": str(path),
                "CMF_GPU_GUARD_PHYSICAL_INDEX": "4",
            }
            with patch.dict(os.environ, environment, clear=False):
                self.assertEqual(
                    require_atomic_gpu_guard(expected_uuid="GPU-test", physical_index=4)["precheck"]["memory_used_mib"],
                    14,
                )
                receipt["precheck"]["compute_processes"] = [{"pid": 7}]
                path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaisesRegex(PermissionError, "fresh-idle"):
                    require_atomic_gpu_guard(expected_uuid="GPU-test", physical_index=4)
                receipt["precheck"]["compute_processes"] = []
                receipt["precheck"]["captured_at"] = "2000-01-01T00:00:00+00:00"
                path.write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaisesRegex(PermissionError, "fresh-idle"):
                    require_atomic_gpu_guard(expected_uuid="GPU-test", physical_index=4)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(PermissionError, "atomic GPU guard"):
                    require_atomic_gpu_guard(expected_uuid="GPU-test", physical_index=4)

    def test_f3_and_f4_repair_and_full_root_modes_are_distinct(self):
        f3_source = inspect.getsource(type(get_family_runner("F3")).rollout)
        f4_source = inspect.getsource(type(get_family_runner("F4")).rollout)
        self.assertIn('f3_full_program_nonformal_root', f3_source)
        self.assertIn('f4_full_program_nonformal_root', f4_source)
        self.assertIn('"full_f3_program_complete": full_program and repair_probe_pass', f3_source)
        self.assertIn('"full_f4_program_complete": full_program_pass', f4_source)
        self.assertIn('else "runtime-v3_1 repair scope is V->H diagnosis only"', f3_source)
        self.assertIn('else "runtime-v3_1 repair scope covers common-X only"', f4_source)


if __name__ == "__main__":
    unittest.main()
