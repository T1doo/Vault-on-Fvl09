import copy
import unittest
from unittest.mock import patch

import numpy as np

from controlled_multi_future.f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
    select_f4_stage_a_source_v1,
)
from controlled_multi_future.f4_program_planner_integration_v2 import (
    PLANNER_COLLISION_SCOPE,
    PROGRAMS,
    PURPOSE,
    build_f4_program_planner_spec_v2,
    finalize_f4_candidate_program_qualification_v2,
    run_f4_program_planner_v2,
)
from controlled_multi_future.f4_stage_b_geometry_contract_v2 import (
    audit_f4_actual_source_layout_v2,
)
from controlled_multi_future.high_level_planner_runner_v1 import (
    build_f4_stage_b_targets_v1,
)


def candidates():
    contract = build_f4_hierarchical_template_search_v1()
    gates = contract["stage_a_required_gates"]
    receipts = [
        {
            "candidate_id": item["candidate_id"],
            "candidate_sha256": item["candidate_sha256"],
            "checks": {gate: item["rank"] == 1 for gate in gates},
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }
        for item in contract["stage_a_candidates"]
    ]
    terminal = select_f4_stage_a_source_v1(contract, receipts)
    source = terminal["selected_source_grasp"]
    slot = build_f4_stage_b_candidates_v1(contract, terminal)["candidates"][0]
    return source, slot


def successful_plan(scene, targets, *, query_limit, arm):
    scene.planner_query_count += len(targets)
    return {
        "pass": True,
        "segment_receipts": [
            {
                "segment_id": item["segment_id"],
                "planner_status": "Success",
            }
            for item in targets
        ],
        "planner_query_count": scene.planner_query_count,
        "terminal_qpos": [0.0],
        "terminal_qpos_sha256": "a" * 64,
        "controls": [{} for _ in targets],
    }


class Scene:
    def __init__(self, scene_id):
        self._cmf_scene_instance_id = scene_id
        self._cmf_scene_lifecycle = "fresh"
        self.planner_query_count = 0


def fake_target_builder(scene, spec):
    scene.planner_query_count += 12
    order = spec["program_order"]
    targets = [
        {
            "segment_id": f"{role}_segment_{index}",
            "pose": [0, 0, 0.9, 1, 0, 0, 0],
        }
        for role in order
        for index in range(10)
    ]
    return targets, {
        "program_id": spec["program_id"],
        "program_order": order,
        "actual_source_layout_gate_v2": {"pass": True},
        "actual_source_construction_geometry_v2": {
            "construction_valid": True
        },
    }


class F4ProgramPlannerIntegrationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.slot = candidates()

    def test_specs_bind_each_program_id_to_its_exact_order(self):
        for program_id, order in PROGRAMS.items():
            with self.subTest(program_id=program_id):
                spec = build_f4_program_planner_spec_v2(
                    self.source,
                    self.slot,
                    program_id=program_id,
                    slot_id=f"slot-{program_id}",
                    planner_reset_nonce=2026091601,
                )
                self.assertEqual(spec["purpose"], PURPOSE)
                self.assertEqual(spec["program_order"], list(order))
                self.assertFalse(spec["planner_execution_authorized"])
        with self.assertRaises(ValueError):
            build_f4_program_planner_spec_v2(
                self.source,
                self.slot,
                program_id="F4-CAB",
                slot_id="bad",
                planner_reset_nonce=2026091601,
            )

    def test_all_three_independent_scenes_required_not_abc_only(self):
        terminals = []
        for index, program_id in enumerate(PROGRAMS):
            spec = build_f4_program_planner_spec_v2(
                self.source,
                self.slot,
                program_id=program_id,
                slot_id=f"slot-{program_id}",
                planner_reset_nonce=2026091601 + index,
            )
            terminals.append(
                self._run(Scene(f"fresh-{index}"), spec)
            )
        self.assertTrue(
            finalize_f4_candidate_program_qualification_v2(
                self.slot, terminals
            )["planner_qualified_for_physical_probe"]
        )
        abc_only = finalize_f4_candidate_program_qualification_v2(
            self.slot, terminals[:1]
        )
        self.assertFalse(abc_only["planner_qualified_for_physical_probe"])
        self.assertFalse(abc_only["candidate_ready"])
        reused_scene = copy.deepcopy(terminals)
        reused_scene[1]["scene_instance_id"] = reused_scene[0]["scene_instance_id"]
        reused_scene[1]["receipt_sha256"] = __import__(
            "controlled_multi_future.canonical_artifact", fromlist=["canonical_hash_json"]
        ).canonical_hash_json(
            {
                key: value
                for key, value in reused_scene[1].items()
                if key != "receipt_sha256"
            }
        )
        self.assertFalse(
            finalize_f4_candidate_program_qualification_v2(
                self.slot, reused_scene
            )["planner_qualified_for_physical_probe"]
        )

    def _run(self, scene, spec):
        with patch(
            "controlled_multi_future.f4_program_planner_integration_v2."
            "_planner_reset",
            create=True,
            return_value={
                "reset_performed": True,
                "planner_seed": spec["planner_reset_nonce"],
                "reset_seed_argument": True,
            },
        ), patch(
            "controlled_multi_future.f4_program_planner_integration_v2._plan_chain",
            side_effect=successful_plan,
        ), patch(
            "controlled_multi_future.f4_program_planner_integration_v2."
            "build_f4_stage_b_targets_v1",
            side_effect=fake_target_builder,
        ):
            return run_f4_program_planner_v2(scene, spec)

    def test_planner_collision_scope_is_explicit_and_missing_scope_fails(self):
        spec = build_f4_program_planner_spec_v2(
            self.source,
            self.slot,
            program_id="F4-ABC",
            slot_id="scope",
            planner_reset_nonce=2026091601,
        )
        terminal = self._run(Scene("scope-scene"), spec)
        self.assertEqual(terminal["planner_collision_scope"], PLANNER_COLLISION_SCOPE)
        self.assertTrue(terminal["robot_kinematic_table_world_planner_pass"])
        self.assertNotIn("physical_feasible", terminal)
        changed = copy.deepcopy(terminal)
        changed.pop("planner_collision_scope")
        changed["receipt_sha256"] = __import__(
            "controlled_multi_future.canonical_artifact", fromlist=["canonical_hash_json"]
        ).canonical_hash_json(
            {key: value for key, value in changed.items() if key != "receipt_sha256"}
        )
        self.assertFalse(
            finalize_f4_candidate_program_qualification_v2(
                self.slot, [changed, terminal, terminal]
            )["planner_qualified_for_physical_probe"]
        )

    def test_actual_source_layout_gate_precedes_actual_geometry(self):
        frozen = self.source["source_layout"]
        self.assertTrue(audit_f4_actual_source_layout_v2(frozen, frozen)["pass"])
        changed = copy.deepcopy(frozen)
        changed["B"][0] += 0.0011
        self.assertFalse(
            audit_f4_actual_source_layout_v2(frozen, changed)["pass"]
        )

    def test_existing_target_builder_uses_acb_not_hardcoded_abc(self):
        spec = build_f4_program_planner_spec_v2(
            self.source,
            self.slot,
            program_id="F4-ACB",
            slot_id="builder-acb",
            planner_reset_nonce=2026091601,
        )

        class Actor:
            def __init__(self, pose):
                self.pose = pose

        scene = Scene("builder-fresh")
        scene.a = Actor(self.source["source_layout"]["A"])
        scene.b = Actor(self.source["source_layout"]["B"])
        scene.c = Actor(self.source["source_layout"]["C"])

        def pose(actor):
            return np.asarray(actor.pose, dtype=np.float64)

        def grasp(scene_arg, source, role, *, program_id=None):
            actor_pose = pose(getattr(scene_arg, role.lower()))
            return actor_pose.copy(), actor_pose.copy(), {"pass": True}

        with patch(
            "controlled_multi_future.high_level_planner_runner_v1._pose",
            side_effect=pose,
        ), patch(
            "controlled_multi_future.high_level_planner_runner_v1._f4_role_grasp",
            side_effect=grasp,
        ), patch(
            "controlled_multi_future.high_level_planner_runner_v1._arm_original_pose",
            return_value=np.asarray([0, 0, 0.95, 1, 0, 0, 0], dtype=np.float64),
        ):
            targets, audit = build_f4_stage_b_targets_v1(scene, spec)
        observed = []
        for item in targets:
            role = item["segment_id"].split("_", 1)[0]
            if not observed or observed[-1] != role:
                observed.append(role)
        self.assertEqual(observed, ["A", "C", "B"])
        self.assertEqual(audit["program_order"], ["A", "C", "B"])
        self.assertTrue(audit["actual_source_layout_gate_v2"]["pass"])
        self.assertTrue(
            audit["actual_source_construction_geometry_v2"][
                "construction_valid"
            ]
        )


if __name__ == "__main__":
    unittest.main()
