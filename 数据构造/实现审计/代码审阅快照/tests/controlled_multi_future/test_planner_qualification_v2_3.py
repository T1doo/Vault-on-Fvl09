import copy
import inspect
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.f2_planner_integration_v2 import (
    build_f2_final_grasp_stage_a_spec_v2,
    finalize_f2_planner_panel_v2,
    run_f2_final_grasp_stage_a_planner_v2,
)
from controlled_multi_future.f3_planner_integration_v3_1 import (
    build_f3_stage_a_planner_spec_v3_1,
    build_f3_stage_b_planner_spec_v3_1,
    build_f3_stage_b_targets_v3_1,
    finalize_f3_candidate_qualification_v3_1,
    run_f3_stage_a_planner_v3_1,
    run_f3_stage_b_planner_v3_1,
)
from controlled_multi_future.high_level_planner_runner_v1 import (
    build_f2_stage_a_targets_v1,
)
from controlled_multi_future.official_raw_pose_generation_v1 import (
    OFFICIAL_GENERATOR_VERSION,
)
from controlled_multi_future.planner_qualification_integration_v2_3 import (
    IMPLEMENTATION_VERSION,
    RUNNER_FUNCTIONS,
    RUNNER_SYMBOLS,
    build_full_planner_panel_v1_proposal,
    build_manifest_bundle_v2_3,
    build_planner_qualification_integration_v2_3_contract,
    build_planner_wiring_smoke_v1_proposal,
    select_f3_stage_b_survivors_v1,
    validate_f4_next_job_v1,
)
from controlled_multi_future.planner_qualification_issuer_v2_3 import (
    build_planner_job_envelope_v2_3,
    issue_planner_authorization_v2_3,
)
from controlled_multi_future.planner_qualification_manifests_v2_3 import (
    build_f2_planner_panel_manifest_v1,
    build_f3_stage_a_panel_manifest_v1,
    build_f3_stage_b_selection_policy_v1,
    build_f4_program_panel_manifest_v1,
)
from controlled_multi_future.probes.planner_qualification_authorization_v2_3 import (
    receipt_sha,
    validate as validate_authorization,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
)


def raw_receipt(recipe, *, family, actor_pose):
    pregrasp = [actor_pose[0], actor_pose[1] - 0.10, 0.90, *actor_pose[3:]]
    grasp = [actor_pose[0], actor_pose[1] - 0.04, 0.90, *actor_pose[3:]]
    value = {
        "schema_version": "cmf_official_raw_pose_generation_v1",
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": family,
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "asset": recipe.get("asset", {}),
        "main_object_model_id": recipe.get("main_object_model_id"),
        "arm": recipe["arm"],
        "contact_point_id": recipe["official_contact_point_id"],
        "rotation_candidate_index": recipe["official_rotation_candidate_index"],
        "pregrasp_distance_m": recipe["pregrasp_distance_m"],
        "target_distance_m": recipe["target_distance_m"],
        "actor_pose": actor_pose,
        "actor_pose_sha256": canonical_hash_json(actor_pose),
        "ordered_rotation_candidate_count": 10,
        "ordered_rotation_candidates_sha256": canonical_hash_json(list(range(10))),
        "selected_raw_pregrasp_pose": pregrasp,
        "selected_raw_grasp_pose": grasp,
        "raw_pregrasp_sha256": canonical_hash_json(pregrasp),
        "raw_grasp_sha256": canonical_hash_json(grasp),
        "source_calls": ["official test fixture"],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def plan_result(targets, terminal_qpos=(0.1, 0.2)):
    qpos = np.asarray(terminal_qpos, dtype=np.float32)
    return {
        "pass": True,
        "segment_receipts": [
            {"segment_id": item["segment_id"], "planner_status": "Success"}
            for item in targets
        ],
        "planner_query_count": len(targets),
        "terminal_qpos": qpos.tolist(),
        "terminal_qpos_sha256": hash_array(qpos),
        "controls": [{} for _ in targets],
    }


class PlannerQualificationV23Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2 = build_f2_planner_panel_manifest_v1()
        cls.f3 = build_f3_stage_a_panel_manifest_v1()
        cls.f3_policy = build_f3_stage_b_selection_policy_v1(cls.f3)
        cls.f4 = build_f4_program_panel_manifest_v1()

    def test_exact_manifests_and_proposals(self):
        self.assertEqual(
            (self.f2["selected_can_id"], self.f2["selected_box_id"]), (0, 2)
        )
        self.assertEqual(self.f2["recipe_count"], 64)
        self.assertEqual(self.f2["contact_ids"], list(range(16)))
        self.assertEqual(self.f2["rotation_indices"], [0, 5])
        self.assertEqual(self.f3["recipe_count"], 128)
        self.assertEqual(self.f3["geometry_diverse_contact_ids"], [0, 2, 4, 6])
        self.assertEqual(self.f3["frozen_rotation_indices"], [0, 5])
        self.assertEqual(self.f3_policy["stratum_count"], 16)
        self.assertEqual(self.f3_policy["stage_b_planner_query_limit"], 112)
        self.assertEqual(self.f4["candidate_count"], 8)
        self.assertEqual(self.f4["job_count"], 24)
        smoke = build_planner_wiring_smoke_v1_proposal()
        self.assertEqual(smoke["aggregate"]["planner_query_limit"], 116)
        self.assertEqual(smoke["aggregate"]["scene_limit"], 9)
        self.assertFalse(smoke["planner_execution_authorized"])
        full = build_full_planner_panel_v1_proposal()
        self.assertEqual(full["F3"]["maximum_queries"], 496)
        self.assertEqual(full["maximum_aggregate_queries"], 1408)

    def test_production_runners_expose_no_callback_injection(self):
        for kind, function in RUNNER_FUNCTIONS.items():
            with self.subTest(kind=kind):
                names = inspect.signature(function).parameters
                self.assertFalse(
                    any("callback" in name or name.endswith("_fn") for name in names)
                )
        contract = build_planner_qualification_integration_v2_3_contract(
            vault_head="d8b90ec003aa83c025796ffd3ff31028c1db7be8",
            active_source_tree_sha256="1" * 64,
            robotwin_tracked_head="c3ddfa8b97d5519efa828b075999bd0006778e5e",
        )
        self.assertFalse(contract["production_arbitrary_callable_injection_allowed"])
        self.assertFalse(contract["authorization"]["planner_execution"])

    def test_f2_new_runner_is_exact_three_segments_and_old_builder_is_closed(self):
        entry = self.f2["ordered_recipes"][0]
        recipe = entry["recipe"]
        spec = build_f2_final_grasp_stage_a_spec_v2(
            recipe,
            self.f2["certificate"],
            self.f2["bindings_by_arm"][recipe["arm"]],
            slot_id="f2-test",
            panel_sha256=self.f2["panel_sha256"],
        )

        class Scene:
            can = object()
            _cmf_scene_instance_id = "f2-fresh"
            _cmf_f2_runtime_asset_metadata_receipt_v4 = {
                "receipt_sha256": "a" * 64
            }

            def __getattr__(self, name):
                if name in {"move", "close_gripper", "open_gripper"}:
                    raise AssertionError("physical action method accessed")
                raise AttributeError(name)

        actor_pose = [0, 0, 0.8, 1, 0, 0, 0]
        seen = {}

        def plan(scene, targets, *, query_limit, arm):
            seen["ids"] = [item["segment_id"] for item in targets]
            seen["limit"] = query_limit
            return plan_result(targets)

        with patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "capture_f2_runtime_geometry_observation_v4",
            return_value={},
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "compare_f2_runtime_geometry_v4",
            return_value={"pass": True},
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "generate_official_raw_pose_receipt_v1",
            return_value=raw_receipt(recipe, family="F2", actor_pose=actor_pose),
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2._planner_reset",
            return_value={"seed": 20260903, "reset": True},
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2._plan_chain",
            side_effect=plan,
        ):
            terminal = run_f2_final_grasp_stage_a_planner_v2(Scene(), spec)
        self.assertEqual(seen["limit"], 3)
        self.assertEqual(len(seen["ids"]), 3)
        self.assertTrue(terminal["planner_qualified_for_physical_probe"])
        self.assertFalse(terminal["runtime_qualified"])
        self.assertFalse(terminal["candidate_ready"])
        self.assertEqual(terminal["physical_execution_count"], 0)
        with self.assertRaisesRegex(RuntimeError, "permanently disabled"):
            build_f2_stage_a_targets_v1(object(), {})
        with self.assertRaises(ValueError):
            finalize_f2_planner_panel_v2(self.f2, [spec], [terminal])

    def _run_f3_stage_a(self):
        entry = self.f3["ordered_recipes"][0]
        recipe = entry["recipe"]
        spec = build_f3_stage_a_planner_spec_v3_1(
            recipe,
            entry["scene_binding"],
            slot_id="f3-a",
            panel_sha256=self.f3["panel_sha256"],
        )
        actor_pose = [
            -0.18 if recipe["arm"] == "left" else 0.18,
            -0.06,
            0.785,
            0.0,
            0.0,
            1.0,
            0.0,
        ]

        class Scene:
            bottle = object()
            _cmf_scene_instance_id = "f3-a-fresh"
            _cmf_f3_scene_binding_v3_1 = entry["scene_binding"]

        def plan(scene, targets, *, query_limit, arm):
            return plan_result(targets)

        with patch(
            "controlled_multi_future.f3_planner_integration_v3_1."
            "generate_official_raw_pose_receipt_v1",
            return_value=raw_receipt(recipe, family="F3", actor_pose=actor_pose),
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._planner_reset",
            return_value={"reset": True},
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._plan_chain",
            side_effect=plan,
        ):
            terminal = run_f3_stage_a_planner_v3_1(Scene(), spec)
        return entry, spec, terminal, actor_pose

    def test_f2_recipe_certificate_binding_and_raw_receipt_mismatch_fail_closed(self):
        entry = self.f2["ordered_recipes"][0]
        recipe = entry["recipe"]
        certificate = self.f2["certificate"]
        binding = self.f2["bindings_by_arm"][recipe["arm"]]
        changed_recipe = copy.deepcopy(recipe)
        changed_recipe["geometry_certificate_sha256"] = "0" * 64
        changed_recipe["recipe_sha256"] = canonical_hash_json(
            {key: value for key, value in changed_recipe.items() if key != "recipe_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "mismatch"):
            build_f2_final_grasp_stage_a_spec_v2(
                changed_recipe, certificate, binding,
                slot_id="bad-recipe", panel_sha256=self.f2["panel_sha256"]
            )
        changed_certificate = copy.deepcopy(certificate)
        changed_certificate["main_object_model_id"] = 1
        changed_certificate["certificate_sha256"] = canonical_hash_json(
            {key: value for key, value in changed_certificate.items() if key != "certificate_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "mismatch"):
            build_f2_final_grasp_stage_a_spec_v2(
                recipe, changed_certificate, binding,
                slot_id="bad-certificate", panel_sha256=self.f2["panel_sha256"]
            )
        changed_binding = copy.deepcopy(binding)
        changed_binding["selected_candidate_key"]["main_object_model_id"] = 1
        changed_binding["binding_sha256"] = canonical_hash_json(
            {key: value for key, value in changed_binding.items() if key != "binding_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "mismatch"):
            build_f2_final_grasp_stage_a_spec_v2(
                recipe, certificate, changed_binding,
                slot_id="bad-binding", panel_sha256=self.f2["panel_sha256"]
            )
        spec = build_f2_final_grasp_stage_a_spec_v2(
            recipe, certificate, binding,
            slot_id="bad-raw", panel_sha256=self.f2["panel_sha256"]
        )
        bad_raw = raw_receipt(recipe, family="F2", actor_pose=[0, 0, 0.8, 1, 0, 0, 0])
        bad_raw["contact_point_id"] += 1
        bad_raw["receipt_sha256"] = canonical_hash_json(
            {key: value for key, value in bad_raw.items() if key != "receipt_sha256"}
        )

        class Scene:
            can = object()
            _cmf_f2_runtime_asset_metadata_receipt_v4 = {"receipt_sha256": "a" * 64}

        with patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "capture_f2_runtime_geometry_observation_v4", return_value={}
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "compare_f2_runtime_geometry_v4", return_value={"pass": True}
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2."
            "generate_official_raw_pose_receipt_v1", return_value=bad_raw
        ), patch(
            "controlled_multi_future.f2_planner_integration_v2._plan_chain"
        ) as planner:
            with self.assertRaisesRegex(ValueError, "raw-pose"):
                run_f2_final_grasp_stage_a_planner_v2(Scene(), spec)
            planner.assert_not_called()

    def test_f3_stage_b_binds_qpos_scene_actor_and_exact_seven_targets(self):
        entry, stage_a_spec, stage_a, actor_pose = self._run_f3_stage_a()
        spec = build_f3_stage_b_planner_spec_v3_1(
            stage_a,
            stage_a_spec,
            slot_id="f3-b",
            selection_policy_sha256=self.f3_policy["policy_sha256"],
        )
        targets = build_f3_stage_b_targets_v3_1(spec)
        self.assertEqual(len(targets), 7)
        self.assertEqual(
            [item["segment_id"].replace("f3_v3_stage_b_", "") for item in targets],
            ["central_1", "V_plus", "V_minus", "central_2", "H_plus", "H_minus", "central_3"],
        )

        class Entity:
            def set_qpos(self, value):
                self.value = np.asarray(value, dtype=np.float32)

            def get_qpos(self):
                return self.value

        class Bottle:
            pose = actor_pose

        class Scene:
            bottle = Bottle()
            _cmf_scene_instance_id = "f3-b-reconstructed"
            _cmf_f3_scene_binding_v3_1 = entry["scene_binding"]

        entity = Entity()
        with patch(
            "controlled_multi_future.f3_planner_integration_v3_1._planner_reset",
            return_value={"reset": True},
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._arm_entity",
            return_value=entity,
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._arm_eef_pose",
            return_value=stage_a["final_pose_freeze"]["final_goal_poses"]["lift"],
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._pose",
            return_value=np.asarray(actor_pose, dtype=np.float64),
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._plan_chain",
            side_effect=lambda scene, requested, **kwargs: plan_result(requested),
        ):
            stage_b = run_f3_stage_b_planner_v3_1(Scene(), spec)
        final = finalize_f3_candidate_qualification_v3_1(
            stage_a, stage_a_spec, stage_b, spec
        )
        self.assertTrue(final["planner_qualified_for_physical_probe"])
        self.assertFalse(final["candidate_ready"])
        self.assertFalse(final["stage1_ready"])
        self.assertEqual(stage_b["physical_execution_count"], 0)

        wrong_qpos = copy.deepcopy(spec)
        wrong_qpos["stage_a_terminal_qpos"][0] += 0.01
        wrong_qpos["spec_sha256"] = canonical_hash_json(
            {key: value for key, value in wrong_qpos.items() if key != "spec_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "continuity"):
            build_f3_stage_b_targets_v3_1(wrong_qpos)
        bad_scene = Scene()
        bad_scene._cmf_f3_scene_binding_v3_1 = {
            **entry["scene_binding"], "robot_config_sha256": "0" * 64
        }
        with self.assertRaisesRegex(ValueError, "scene binding"):
            run_f3_stage_b_planner_v3_1(bad_scene, spec)
        wrong_actor = list(actor_pose)
        wrong_actor[0] += 0.01
        with patch(
            "controlled_multi_future.f3_planner_integration_v3_1._pose",
            return_value=np.asarray(wrong_actor, dtype=np.float64),
        ):
            with self.assertRaisesRegex(ValueError, "actor pose"):
                run_f3_stage_b_planner_v3_1(Scene(), spec)
        with patch(
            "controlled_multi_future.f3_planner_integration_v3_1._planner_reset",
            return_value={"reset": True},
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._arm_entity",
            return_value=entity,
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._arm_eef_pose",
            return_value=[9, 9, 9, 1, 0, 0, 0],
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._pose",
            return_value=np.asarray(actor_pose, dtype=np.float64),
        ):
            with self.assertRaisesRegex(ValueError, "initial EEF"):
                run_f3_stage_b_planner_v3_1(Scene(), spec)

    def test_f3_stratum_selection_and_f4_conditional_rank_issuance(self):
        first_by_stratum = {}
        terminals = []
        for entry in self.f3["ordered_recipes"]:
            key = tuple(entry["stratum"].values())
            if key not in first_by_stratum:
                first_by_stratum[key] = entry
                terminals.append(
                    {"recipe_sha256": entry["recipe_sha256"], "stage_a_pass": True}
                )
        survivors = select_f3_stage_b_survivors_v1(
            self.f3, self.f3_policy, terminals
        )
        self.assertEqual(len(survivors), 16)
        jobs = self.f4["ordered_jobs"]
        r1 = [item for item in jobs if item["candidate_rank"] == 1]
        self.assertEqual(validate_f4_next_job_v1(self.f4, r1[0], []), r1[0])
        with self.assertRaises(ValueError):
            validate_f4_next_job_v1(self.f4, r1[1], [])
        abc = {
            "candidate_id": r1[0]["candidate_id"],
            "program_id": "F4-ABC",
            "robot_kinematic_table_world_planner_pass": True,
        }
        self.assertEqual(validate_f4_next_job_v1(self.f4, r1[1], [abc]), r1[1])
        acb = {**abc, "program_id": "F4-ACB"}
        bac = {**abc, "program_id": "F4-BAC"}
        r2abc = next(item for item in jobs if item["candidate_rank"] == 2)
        with self.assertRaisesRegex(ValueError, "full pass"):
            validate_f4_next_job_v1(self.f4, r2abc, [abc, acb, bac])
        failed_bac = {**bac, "robot_kinematic_table_world_planner_pass": False}
        self.assertEqual(
            validate_f4_next_job_v1(self.f4, r2abc, [abc, acb, failed_bac]),
            r2abc,
        )

    def test_v2_3_authorization_binds_source_manifest_runner_and_gpu_policy(self):
        bundle = build_manifest_bundle_v2_3()
        now = datetime.now(timezone.utc)
        job_spec = {"job_id": "smoke-f2-left"}
        job_spec["job_spec_sha256"] = canonical_hash_json(job_spec)
        value = {
            "schema_version": "cmf_planner_qualification_authorization_v2_3",
            "implementation_version": IMPLEMENTATION_VERSION,
            "authorization_id": "v23-test-auth",
            "approved": True,
            "approved_scopes": ["planner_wiring_smoke_v1"],
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=30)).isoformat(),
            "job_kind": "F2_STAGE_A",
            "manifest_bundle_sha256": bundle["bundle_sha256"],
            "manifest_sha256": bundle["f2_panel_sha256"],
            "runner_symbol": RUNNER_SYMBOLS["F2_STAGE_A"],
            "planner_query_limit": 3,
            "scene_limit": 1,
            "physical_execution_limit": 0,
            "max_invocations": 1,
            "automatic_retry": False,
            "fallback_allowed": False,
            "o_excl_output_required": True,
            "output_preexisting": False,
            "source_change_invalidates_authorization": True,
            "stage1_authorized": False,
            "formal_data": False,
            "vault_head": "d8b90ec003aa83c025796ffd3ff31028c1db7be8",
            "active_source_tree_sha256": "1" * 64,
            "robotwin_tracked_head": "c3ddfa8b97d5519efa828b075999bd0006778e5e",
            "output_path": "/nfs_share/lijunhui/Robotwin2/tmp/v23-test-nonexistent",
            "job_spec": job_spec,
            "job_spec_sha256": job_spec["job_spec_sha256"],
            "gpu_policy_version": "cmf_gpu_parallel_policy_v2",
            "allowed_physical_gpu_indices": list(range(8)),
            "dynamic_fresh_idle_selection": True,
            "parallel_different_cards_authorized": True,
            "one_project_job_per_gpu": True,
            "one_root_one_gpu": True,
            "root_sharding_authorized": False,
            "share_busy_gpu_authorized": False,
            "atomic_guard_recheck_before_launch": True,
            "automatic_gpu0_fallback": False,
        }
        value["receipt_sha256"] = receipt_sha(value)
        self.assertEqual(
            validate_authorization(
                value,
                requested_scope="planner_wiring_smoke_v1",
                expected_vault_head=value["vault_head"],
                expected_source_tree_sha256=value["active_source_tree_sha256"],
                expected_robotwin_tracked_head=value["robotwin_tracked_head"],
                now=now,
            ),
            value,
        )
        with self.assertRaisesRegex(AuthorizationBindingError, "source tree"):
            validate_authorization(
                value,
                requested_scope="planner_wiring_smoke_v1",
                expected_source_tree_sha256="2" * 64,
                now=now,
            )
        changed = copy.deepcopy(value)
        changed["plan_chain_fn"] = "forbidden"
        changed["receipt_sha256"] = receipt_sha(changed)
        with self.assertRaisesRegex(AuthorizationBindingError, "boundary"):
            validate_authorization(
                changed, requested_scope="planner_wiring_smoke_v1", now=now
            )

    def test_issuer_requires_separate_exact_approval_and_emits_one_job_only(self):
        seal = build_planner_qualification_integration_v2_3_contract(
            vault_head="d8b90ec003aa83c025796ffd3ff31028c1db7be8",
            active_source_tree_sha256="1" * 64,
            robotwin_tracked_head="c3ddfa8b97d5519efa828b075999bd0006778e5e",
        )
        entry = self.f2["ordered_recipes"][0]
        envelope = build_planner_job_envelope_v2_3(
            seal,
            job_kind="F2_STAGE_A",
            manifest_entry=entry,
            job_id="smoke-f2-left",
            scene_id="smoke-f2-left-scene",
            output_path="/nfs_share/lijunhui/Robotwin2/tmp/v23-issuer-test-nonexistent",
        )
        with self.assertRaisesRegex(PermissionError, "separate"):
            issue_planner_authorization_v2_3(
                seal,
                envelope,
                None,
                authorization_id="not-issued",
                requested_scope="planner_wiring_smoke_v1",
            )
        approval = {
            "schema_version": "cmf_planner_wiring_smoke_user_approval_v1",
            "approved": True,
            "approved_scope": "planner_wiring_smoke_v1",
            "integration_contract_sha256": seal["contract_sha256"],
            "job_envelope_sha256": envelope["envelope_sha256"],
        }
        approval["approval_sha256"] = canonical_hash_json(approval)
        now = datetime.now(timezone.utc)
        authorization = issue_planner_authorization_v2_3(
            seal,
            envelope,
            approval,
            authorization_id="v23-issued-test",
            requested_scope="planner_wiring_smoke_v1",
            issued_at=now,
        )
        self.assertEqual(authorization["max_invocations"], 1)
        self.assertEqual(authorization["physical_execution_limit"], 0)
        self.assertFalse(authorization["automatic_retry"])
        self.assertEqual(
            validate_authorization(
                authorization,
                requested_scope="planner_wiring_smoke_v1",
                expected_vault_head=seal["vault_head"],
                expected_source_tree_sha256=seal["active_source_tree_sha256"],
                expected_robotwin_tracked_head=seal["robotwin_tracked_head"],
                now=now,
            ),
            authorization,
        )


if __name__ == "__main__":
    unittest.main()
