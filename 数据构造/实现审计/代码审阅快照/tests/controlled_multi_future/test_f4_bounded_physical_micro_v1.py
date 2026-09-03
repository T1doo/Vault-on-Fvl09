import unittest
from unittest.mock import patch

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f4_bounded_physical_micro_v1 import (
    STAGES,
    build_f4_bounded_physical_micro_spec_v1,
    run_f4_bounded_physical_micro_v1,
)
from controlled_multi_future.planner_qualification_manifests_v2_3 import (
    build_f4_program_panel_manifest_v1_1,
)


class F4BoundedPhysicalMicroV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        panel = build_f4_program_panel_manifest_v1_1()
        cls.source = panel["source_candidate"]
        cls.candidate = panel["candidates"][0]

    def terminal(self, stage):
        from controlled_multi_future.f4_program_planner_integration_v2 import (
            build_f4_program_planner_spec_v2,
        )

        program_id = STAGES[stage]["program_id"]
        spec = build_f4_program_planner_spec_v2(
            self.source,
            self.candidate,
            program_id=program_id,
            slot_id=f"{stage.lower()}-planner-source",
            planner_reset_nonce=404,
        )
        terminal = {
            "spec_sha256": spec["spec_sha256"],
            "candidate_sha256": spec["candidate_sha256"],
            "program_id": program_id,
            "robot_kinematic_table_world_planner_pass": True,
            "physical_execution_count": 0,
        }
        terminal["receipt_sha256"] = canonical_hash_json(terminal)
        return terminal

    def test_stage_order_and_exact_query_budgets(self):
        expected = {
            "A_ONLY": ("F4-ABC", ["A"], 22),
            "B_ONLY": ("F4-BAC", ["B"], 22),
            "C_ONLY": ("F4-ACB", ["C"], 22),
            "AB_NONINTERFERENCE": ("F4-ABC", ["A", "B"], 32),
            "AC_NONINTERFERENCE": ("F4-ACB", ["A", "C"], 32),
        }
        for stage, (program, roles, queries) in expected.items():
            with self.subTest(stage=stage):
                spec = build_f4_bounded_physical_micro_spec_v1(
                    self.source,
                    self.candidate,
                    self.terminal(stage),
                    stage=stage,
                    slot_id=stage.lower(),
                    planner_reset_nonce=404,
                )
                self.assertEqual(spec["program_id"], program)
                self.assertEqual(spec["role_sequence"], roles)
                self.assertEqual(spec["planner_query_limit"], queries)
                self.assertFalse(spec["automatic_next_stage"])
                self.assertEqual(spec["legacy_scene_spec"]["family"], "F4")

    def test_runner_requires_physical_result_and_never_auto_advances(self):
        spec = build_f4_bounded_physical_micro_spec_v1(
            self.source,
            self.candidate,
            self.terminal("A_ONLY"),
            stage="A_ONLY",
            slot_id="a_only",
            planner_reset_nonce=404,
        )
        scene = type("Scene", (), {"planner_query_count": 22})()
        with patch(
            "controlled_multi_future.f4_bounded_physical_micro_v1."
            "execute_f4_bounded_physical_micro_v1",
            return_value={"sequence_complete": True, "verifier": {"pass": True}},
        ) as execute:
            terminal = run_f4_bounded_physical_micro_v1(
                scene, spec, capture_anchor_callback=lambda _: {}
            )
        self.assertEqual(execute.call_count, 1)
        self.assertTrue(terminal["stage_physically_qualified"])
        self.assertFalse(terminal["automatic_next_stage"])
        self.assertFalse(terminal["candidate_ready"])

    def test_planner_failure_or_wrong_program_cannot_seed_physical_stage(self):
        terminal = self.terminal("A_ONLY")
        terminal.pop("receipt_sha256")
        terminal["robot_kinematic_table_world_planner_pass"] = False
        terminal["receipt_sha256"] = canonical_hash_json(terminal)
        with self.assertRaisesRegex(ValueError, "passing planner"):
            build_f4_bounded_physical_micro_spec_v1(
                self.source,
                self.candidate,
                terminal,
                stage="A_ONLY",
                slot_id="a-only",
                planner_reset_nonce=404,
            )


if __name__ == "__main__":
    unittest.main()
