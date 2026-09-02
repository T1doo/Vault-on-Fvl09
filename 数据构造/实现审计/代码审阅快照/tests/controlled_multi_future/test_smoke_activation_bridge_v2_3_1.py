import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.canonical_artifact import (
    canonical_hash_json,
    canonical_write_json,
)
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.official_raw_pose_generation_v1 import (
    OFFICIAL_GENERATOR_VERSION,
)
from controlled_multi_future.f3_planner_integration_v3_1 import (
    build_f3_stage_a_planner_spec_v3_1,
    run_f3_stage_a_planner_v3_1,
)
from controlled_multi_future.planner_qualification_integration_v2_3 import (
    build_manifest_bundle_v2_3,
)
from controlled_multi_future.planner_qualification_issuer_v2_3_1 import (
    exact_child_command_v2_3_1,
    issue_wave_job_authorization_v2_3_1,
)
from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1 import (
    RUNNER_SYMBOLS,
    build_f3_stage_b_dependency_registry_v1,
    build_production_scene_bridge_plan_v2_3_1,
)
from controlled_multi_future.planner_wiring_smoke_v2_3_1 import (
    build_updated_full_planner_panel_v1_proposal,
    build_updated_planner_wiring_smoke_v1_proposal,
)
from controlled_multi_future.probes.gpu_guard_v2_4 import build_guard_binding
from controlled_multi_future.probes.planner_qualification_authorization_v2_3_1 import (
    IMPLEMENTATION_VERSION,
    consumption_sha,
    load as load_authorization,
)
from controlled_multi_future.probes.planner_qualification_scope_runner_v2_3 import (
    dispatch_authorized_job_v2_3_1,
)
from controlled_multi_future.runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)
from controlled_multi_future.smoke_activation_bridge_v2_3_1 import (
    build_v2_3_1_smoke_activation_bridge_contract,
)


TMP_ROOT = Path("/nfs_share/lijunhui/Robotwin2/tmp")


def _wave_approval(contract):
    proposal = build_updated_planner_wiring_smoke_v1_proposal()
    value = {
        "schema_version": "cmf_planner_wiring_smoke_v1_wave_approval",
        "approved": True,
        "approved_scope": "PLANNER_WIRING_SMOKE_V1",
        "activation_contract_sha256": contract["contract_sha256"],
        "proposal_sha256": proposal["proposal_sha256"],
        "manifest_bundle_sha256": proposal["manifest_bundle_sha256"],
        "ordered_job_slots": proposal["ordered_job_slots"],
        "aggregate_budget": proposal["aggregate"],
        "conditional_issuance_rules": proposal["conditional_issuance_rules"],
        "vault_head": contract["vault_head"],
        "implementation_source_sha256": contract["implementation_source_sha256"],
        "robotwin_tracked_head": contract["robotwin_tracked_head"],
    }
    value["wave_approval_sha256"] = canonical_hash_json(value)
    return value


def _raw_pose_receipt(recipe):
    actor_pose = [0.0, 0.0, 0.8, 1.0, 0.0, 0.0, 0.0]
    pregrasp = [0.0, -0.10, 0.90, 1.0, 0.0, 0.0, 0.0]
    grasp = [0.0, -0.04, 0.90, 1.0, 0.0, 0.0, 0.0]
    value = {
        "schema_version": "cmf_official_raw_pose_generation_v1",
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": "F2",
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "asset": {},
        "main_object_model_id": recipe["main_object_model_id"],
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
        "source_calls": ["activation bridge CPU/mock"],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def _f3_raw_pose_receipt(recipe, actor_pose):
    pregrasp = [actor_pose[0], actor_pose[1] - 0.10, 0.90, *actor_pose[3:]]
    grasp = [actor_pose[0], actor_pose[1] - 0.04, 0.90, *actor_pose[3:]]
    value = {
        "schema_version": "cmf_official_raw_pose_generation_v1",
        "official_generator_version": OFFICIAL_GENERATOR_VERSION,
        "family": "F3",
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "asset": recipe["asset"],
        "main_object_model_id": None,
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
        "source_calls": ["activation bridge F3 dependency fixture"],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def _successful_plan(scene, targets, *, query_limit, arm):
    qpos = np.asarray([0.1, 0.2], dtype=np.float32)
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


class _FakeContext:
    def __init__(self, scene):
        self.handle = SimpleNamespace(scene=scene)
        self.cleanup_receipt = None

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc, traceback):
        self.cleanup_receipt = {
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }


class _FakeF2Adapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def scene(self, planned_spec, *, phase, program):
        scene = SimpleNamespace(
            can=object(),
            _cmf_scene_instance_id="activation-bridge-f2-fresh",
            _cmf_f2_runtime_asset_metadata_receipt_v4={
                "receipt_sha256": "a" * 64
            },
        )
        return _FakeContext(scene)


class SmokeActivationBridgeV231Tests(unittest.TestCase):
    def test_revised_budgets_are_exact(self):
        smoke = build_updated_planner_wiring_smoke_v1_proposal()
        full = build_updated_full_planner_panel_v1_proposal()
        self.assertEqual(smoke["F4"]["total_queries_per_program"], 42)
        self.assertEqual(smoke["aggregate"]["planner_query_limit"], 152)
        self.assertEqual(full["F4"]["maximum_queries"], 1008)
        self.assertEqual(full["maximum_aggregate_queries"], 1696)
        self.assertFalse(smoke["planner_execution_authorized"])

    def test_issuer_loader_guard_dispatch_bridge_exact_runner_terminal(self):
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="cmf_v231_activation_test_", dir=TMP_ROOT
        ) as directory:
            root = Path(directory)
            source_path = root / "source-lock.json"
            source = capture_runtime_source_lock(family="F2")
            write_runtime_source_lock(source_path, source)
            contract = build_v2_3_1_smoke_activation_bridge_contract(
                vault_head="f" * 40,
                implementation_source_sha256=source["snapshot"][
                    "implementation_source_sha256"
                ],
                robotwin_tracked_head=source["snapshot"]["official_repo_commit"],
            )
            approval = _wave_approval(contract)
            auth_path = root / "authorization.json"
            output = root / "output"
            guard_path = root / "guard.json"
            authorization = issue_wave_job_authorization_v2_3_1(
                activation_contract=contract,
                wave_approval=approval,
                job_slot="S1",
                authorization_id="v231-e2e-f2-s1",
                authorization_receipt_path=auth_path,
                source_lock_receipt_path=source_path,
                output_namespace=output,
                guard_receipt_path=guard_path,
                issued_at=datetime.now(timezone.utc),
            )
            canonical_write_json(auth_path, authorization, exclusive=True, mode=0o600)
            loaded = load_authorization(
                auth_path,
                requested_scope="PLANNER_WIRING_SMOKE_V1",
                expected_output_namespace=str(output),
                expected_family="F2",
                expected_seed=authorization["scene_seed"],
                expected_reviewed_content_commit=contract["vault_head"],
            )
            consumption = {
                "schema_version": "cmf_planner_qualification_consumption_v2_3_1",
                "implementation_version": IMPLEMENTATION_VERSION,
                "authorization_id": loaded["authorization_id"],
                "authorization_receipt_sha256": loaded["receipt_sha256"],
                "job_kind": loaded["job_kind"],
                "consumed_at": datetime.now(timezone.utc).isoformat(),
                "max_invocations": 1,
            }
            consumption["consumption_receipt_sha256"] = consumption_sha(consumption)
            binding = build_guard_binding(
                loaded,
                consumption,
                physical_index=7,
                expected_uuid="GPU-00000000-0000-0000-0000-000000000007",
                timeout_seconds=loaded["timeout_seconds"],
                output_namespace=loaded["output_namespace"],
                command=exact_child_command_v2_3_1(auth_path),
                guard_pid=12345,
            )
            observed_reset = {}

            def reset(scene, *, planner_seed, variant_id, arm):
                observed_reset.update(
                    seed=planner_seed, variant_id=variant_id, arm=arm
                )
                return {"reset_performed": True, "planner_seed": planner_seed}

            recipe = loaded["job_spec"]["manifest_entry"]["recipe"]
            with patch(
                "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1."
                "RoboTwinRealSapienF2HierarchicalStageAV1Adapter",
                _FakeF2Adapter,
            ), patch(
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
                return_value=_raw_pose_receipt(recipe),
            ), patch(
                "controlled_multi_future.f2_planner_integration_v2._planner_reset",
                side_effect=reset,
            ), patch(
                "controlled_multi_future.f2_planner_integration_v2._plan_chain",
                side_effect=_successful_plan,
            ):
                terminal = dispatch_authorized_job_v2_3_1(loaded, output=output)

            self.assertEqual(binding["scene_seed"], loaded["scene_seed"])
            self.assertEqual(binding["command_sha256"], loaded["authorized_command_sha256"])
            self.assertEqual(observed_reset["seed"], loaded["job_spec"]["planner_rng_seed"])
            self.assertEqual(terminal["runner_symbol"], RUNNER_SYMBOLS["F2_STAGE_A"])
            self.assertEqual(terminal["planner_query_count"], 3)
            self.assertTrue(terminal["planner_pass"])
            self.assertIsNone(terminal["failure_class"])
            self.assertTrue(terminal["cleanup"]["cleanup_safety_pass"])
            self.assertEqual(terminal["job_terminal"]["planner_rng_seed"], observed_reset["seed"])
            self.assertEqual(terminal["physical_execution_count"], 0)

    def test_all_four_job_kinds_build_exact_production_bridge_plans(self):
        bundle = build_manifest_bundle_v2_3()
        f2_entry = bundle["manifests"]["F2"]["ordered_recipes"][0]
        f2_recipe = f2_entry["recipe"]
        f2_auth = {
            "job_kind": "F2_STAGE_A",
            "runner_symbol": RUNNER_SYMBOLS["F2_STAGE_A"],
            "job_spec": {
                "job_id": "bridge-f2",
                "planner_rng_seed": 101,
                "manifest_entry": f2_entry,
                "manifest_sha256": bundle["f2_panel_sha256"],
                "manifest_context": {
                    "certificate": bundle["manifests"]["F2"]["certificate"],
                    "bindings_by_arm": bundle["manifests"]["F2"]["bindings_by_arm"],
                },
            },
        }

        f3_entry = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"][0]
        f3_spec = build_f3_stage_a_planner_spec_v3_1(
            f3_entry["recipe"],
            f3_entry["scene_binding"],
            slot_id="bridge-f3-a",
            panel_sha256=bundle["f3_stage_a_panel_sha256"],
            planner_rng_seed=102,
        )
        actor_pose = [
            -0.18 if f3_entry["recipe"]["arm"] == "left" else 0.18,
            -0.06,
            0.785,
            0.0,
            0.0,
            1.0,
            0.0,
        ]
        f3_scene = SimpleNamespace(
            bottle=object(),
            _cmf_scene_instance_id="bridge-f3-a-fresh",
            _cmf_f3_scene_binding_v3_1=f3_entry["scene_binding"],
        )
        with patch(
            "controlled_multi_future.f3_planner_integration_v3_1."
            "generate_official_raw_pose_receipt_v1",
            return_value=_f3_raw_pose_receipt(f3_entry["recipe"], actor_pose),
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._planner_reset",
            return_value={"reset_performed": True, "planner_seed": 102},
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._plan_chain",
            side_effect=_successful_plan,
        ):
            f3_terminal = run_f3_stage_a_planner_v3_1(f3_scene, f3_spec)
        self.assertTrue(f3_terminal["stage_a_pass"])

        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="cmf_v231_f3_registry_test_", dir=TMP_ROOT
        ) as directory:
            root = Path(directory)
            spec_path = root / "stage_a_spec.json"
            terminal_path = root / "stage_a_terminal.json"
            canonical_write_json(spec_path, f3_spec, exclusive=True, mode=0o600)
            canonical_write_json(
                terminal_path, f3_terminal, exclusive=True, mode=0o600
            )
            registry = build_f3_stage_b_dependency_registry_v1(
                stage_a_spec_path=spec_path,
                stage_a_terminal_path=terminal_path,
            )
            f3_a_auth = {
                "job_kind": "F3_STAGE_A",
                "runner_symbol": RUNNER_SYMBOLS["F3_STAGE_A"],
                "job_spec": {
                    "job_id": "bridge-f3-a",
                    "planner_rng_seed": 102,
                    "manifest_entry": f3_entry,
                    "manifest_sha256": bundle["f3_stage_a_panel_sha256"],
                },
            }
            f3_b_auth = {
                "job_kind": "F3_STAGE_B",
                "runner_symbol": RUNNER_SYMBOLS["F3_STAGE_B"],
                "job_spec": {
                    "job_id": "bridge-f3-b",
                    "planner_rng_seed": 103,
                    "manifest_entry": f3_entry,
                    "manifest_sha256": bundle["f3_stage_b_policy_sha256"],
                    "dependency_registry": registry,
                },
            }
            f4_entry = next(
                item
                for item in bundle["manifests"]["F4"]["ordered_jobs"]
                if item["candidate_rank"] == 1
            )
            f4_candidate = next(
                item
                for item in bundle["manifests"]["F4"]["candidates"]
                if item["candidate_sha256"] == f4_entry["candidate_sha256"]
            )
            f4_auth = {
                "job_kind": "F4_PROGRAM",
                "runner_symbol": RUNNER_SYMBOLS["F4_PROGRAM"],
                "job_spec": {
                    "job_id": "bridge-f4",
                    "planner_rng_seed": 104,
                    "manifest_entry": f4_entry,
                    "manifest_context": {
                        "source_candidate": bundle["manifests"]["F4"][
                            "source_candidate"
                        ],
                        "candidate": f4_candidate,
                    },
                },
            }
            plans = [
                build_production_scene_bridge_plan_v2_3_1(f2_auth),
                build_production_scene_bridge_plan_v2_3_1(f3_a_auth),
                build_production_scene_bridge_plan_v2_3_1(f3_b_auth),
                build_production_scene_bridge_plan_v2_3_1(f4_auth),
            ]
        self.assertEqual(
            [item["job_kind"] for item in plans],
            ["F2_STAGE_A", "F3_STAGE_A", "F3_STAGE_B", "F4_PROGRAM"],
        )
        self.assertEqual(
            [item["runner_symbol"] for item in plans],
            [RUNNER_SYMBOLS[item["job_kind"]] for item in plans],
        )
        self.assertEqual([item["planner_rng_seed"] for item in plans], [101, 102, 103, 104])
        self.assertEqual(plans[2]["runner_spec"]["stage_a_terminal_receipt_sha256"], f3_terminal["receipt_sha256"])

    def test_bridge_rejects_unknown_runner_instead_of_fallback(self):
        with self.assertRaisesRegex(ValueError, "runner symbol"):
            build_production_scene_bridge_plan_v2_3_1(
                {
                    "job_kind": "F2_STAGE_A",
                    "runner_symbol": "HighLevelPlannerRunnerV1",
                    "job_spec": {},
                }
            )


if __name__ == "__main__":
    unittest.main()
