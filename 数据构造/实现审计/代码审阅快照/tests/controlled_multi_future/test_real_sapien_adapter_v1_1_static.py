import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.family_runners_v3_1 import F2RunnerV3_1, get_family_runner
from controlled_multi_future.families import F2TargetRelation, F4SubtaskOrder
from controlled_multi_future.probes.runtime_v3_1_authorization import load_runtime_v3_1_authorization
from controlled_multi_future.real_sapien_adapter_v1_1 import RoboTwinRealSapienPilotRootAdapterV1_1
from controlled_multi_future.root_orchestrator_v1_1 import RealSapienPilotRootAdapterV1_1


class RealSapienAdapterV1_1StaticTest(unittest.TestCase):
    def test_adapter_is_concrete_and_import_does_not_create_scene(self):
        self.assertTrue(issubclass(RoboTwinRealSapienPilotRootAdapterV1_1, RealSapienPilotRootAdapterV1_1))
        self.assertFalse(inspect.isabstract(RoboTwinRealSapienPilotRootAdapterV1_1))
        for family in ("F1", "F2", "F3", "F4"):
            adapter = RoboTwinRealSapienPilotRootAdapterV1_1(family=family, output_root=Path("/nfs_share/lijunhui/Robotwin2/tmp/static-only"))
            self.assertEqual(adapter.family, family)
            self.assertIs(adapter.runner, get_family_runner(family))

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

            def left_plan_path(self, pose, last_qpos=None):
                start = np.asarray(last_qpos, dtype=float)
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

    def test_f3_and_f4_full_root_claims_fail_closed(self):
        f3_source = inspect.getsource(type(get_family_runner("F3")).rollout)
        f4_source = inspect.getsource(type(get_family_runner("F4")).rollout)
        self.assertIn('"full_f3_program_complete": False', f3_source)
        self.assertIn('"full_f4_program_complete": False', f4_source)
        self.assertIn('"pass": False', f3_source)
        self.assertIn('"pass": False', f4_source)


if __name__ == "__main__":
    unittest.main()
