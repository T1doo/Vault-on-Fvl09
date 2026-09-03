import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.canonical_artifact import canonical_hash_json, canonical_write_json
from controlled_multi_future.current_hasher import hash_array
from controlled_multi_future.f3_planner_integration_v3_1 import run_f3_stage_a_planner_v3_1
from controlled_multi_future.f4_program_planner_integration_v2 import (
    PlannerQueryAccountingError,
    build_f4_program_planner_spec_v2,
    run_f4_program_planner_v2,
)
from controlled_multi_future.high_level_planner_runner_v1 import PlannerCandidateNoValidGrasp
from controlled_multi_future.official_raw_pose_generation_v1 import OFFICIAL_GENERATOR_VERSION
from controlled_multi_future.planner_qualification_integration_v2_3_1a import build_manifest_bundle_v2_3_1a
from controlled_multi_future.planner_qualification_issuer_v2_3_1a import issue_wave_job_authorization_v2_3_1a
from controlled_multi_future.planner_qualification_manifests_v2_3 import (
    build_f4_program_panel_manifest_v1,
    build_f4_program_panel_manifest_v1_1,
)
from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1 import (
    build_f3_stage_b_dependency_registry_v1_1,
)
from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a import (
    F3ActualSceneBindingMismatch,
    prepare_exact_job_bridge_envelope_v2_3_1a,
    run_with_production_scene_bridge_v2_3_1a,
)
from controlled_multi_future.planner_wiring_smoke_v2_3_1a import (
    build_updated_full_planner_panel_v1_proposal_v2,
    build_updated_planner_wiring_smoke_v1_proposal_v2,
    validate_wave_approval_v2,
)
from controlled_multi_future.planner_wiring_smoke_wave_driver_v1 import (
    build_f3_stage_b_registry_from_wave_v1,
    finalize_wave_terminal_v1,
    initialize_wave_ledger_v1,
    load_wave_ledger_state_v1,
    normalize_outer_terminal_from_disk_v1,
    record_guard_prevalidation_terminal_v1,
    record_outer_terminal_v1,
    record_slot_issuance_v1,
    validate_slot_issuance_from_ledger_v1,
)
from controlled_multi_future.pre_smoke_operational_hotfix_v2_3_1a import (
    build_v2_3_1a_pre_smoke_operational_hotfix_contract,
)
from controlled_multi_future.probes.gpu_guard_v2_4 import planner_wiring_smoke_guard_purpose_v1
from controlled_multi_future.probes.planner_qualification_authorization_v2_3_1a import (
    IMPLEMENTATION_VERSION,
    SCOPE,
    validate as validate_authorization,
)
from controlled_multi_future.runtime_source_lock_v1 import (
    capture_runtime_source_lock,
    write_runtime_source_lock,
)


TMP_ROOT = Path("/nfs_share/lijunhui/Robotwin2/tmp")
ROBOTWIN_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
SOURCE_SHA = "a" * 64
FREEZE_HEAD = "b" * 40


def contract(source_sha=SOURCE_SHA, vault_head=FREEZE_HEAD):
    return build_v2_3_1a_pre_smoke_operational_hotfix_contract(
        vault_head=vault_head,
        implementation_source_sha256=source_sha,
        robotwin_tracked_head=ROBOTWIN_HEAD,
    )


def approval(value, wave_id="wave-v231a-test"):
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    result = {
        "schema_version": "cmf_planner_wiring_smoke_v1_wave_approval_v2",
        "wave_id": wave_id,
        "approved": True,
        "approved_scope": SCOPE,
        "activation_contract_sha256": value["contract_sha256"],
        "proposal_sha256": proposal["proposal_sha256"],
        "manifest_bundle_sha256": proposal["manifest_bundle_sha256"],
        "ordered_job_slots": proposal["ordered_job_slots"],
        "aggregate_budget": proposal["aggregate"],
        "conditional_issuance_rules": proposal["conditional_issuance_rules"],
        "vault_head": value["vault_head"],
        "implementation_source_sha256": value["implementation_source_sha256"],
        "robotwin_tracked_head": value["robotwin_tracked_head"],
    }
    result["wave_approval_sha256"] = canonical_hash_json(result)
    return result


def raw_f3(recipe, actor_pose):
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
        "source_calls": ["V2.3.1a CPU/mock"],
        "external_raw_pose_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def successful_plan(scene, targets, *, query_limit, arm):
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


def write_hashed(path, value, key):
    result = dict(value)
    result[key] = canonical_hash_json(result)
    canonical_write_json(path, result, exclusive=True, mode=0o600)
    return result


class FakeContext:
    counter = 0

    def __init__(self, seed, *, family="F2"):
        type(self).counter += 1
        scene_id = f"{family.lower()}-mock-{type(self).counter}"
        self.handle = SimpleNamespace(
            scene=SimpleNamespace(
                _cmf_setup_kwargs={"seed": seed},
                _cmf_scene_instance_id=scene_id,
            )
        )
        self.cleanup_receipt = None

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        self.cleanup_receipt = {
            "cleanup_safety_pass": True,
            "orphan_process_count": 0,
        }


class FakeAdapter:
    force_seed = None

    def __init__(self, **kwargs):
        self.planned_spec = kwargs["planned_spec"]

    def scene(self, planned_spec, *, phase, program):
        seed = planned_spec["seed"] if self.force_seed is None else self.force_seed
        return FakeContext(seed, family=planned_spec["family"])


class PreSmokeHotfixV231aTests(unittest.TestCase):
    def setUp(self):
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="v231a_", dir=TMP_ROOT)
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def init_ledger(self, name="ledger"):
        c = contract()
        a = approval(c, wave_id=f"wave-{name}")
        path = self.root / name
        initialize_wave_ledger_v1(path, activation_contract=c, wave_approval=a)
        return path, c, a

    def manual_issued(self, ledger, slot, auth):
        auth_path = Path(auth["authorization_receipt_path"])
        canonical_write_json(auth_path, auth, exclusive=True, mode=0o600)
        value = {
            "schema_version": "cmf_planner_wiring_smoke_slot_issuance_v1",
            "wave_id": auth["wave_id"],
            "slot": slot,
            "prior_normalized_terminal_sha256s": [],
            "aggregate_before_issuance": {
                "planner_query_count": 0,
                "scene_count": 0,
                "elapsed_seconds": 0,
                "physical_execution_count": 0,
                "trajectory_count": 0,
            },
            "authorization_id": auth["authorization_id"],
            "authorization_receipt_path": str(auth_path),
            "authorization_receipt_file_sha256": hashlib.sha256(
                auth_path.read_bytes()
            ).hexdigest(),
            "authorization_receipt_sha256": auth["receipt_sha256"],
        }
        return write_hashed(
            ledger / "issued" / f"{slot}.json",
            value,
            "issuance_sha256",
        )

    def manual_terminal(self, ledger, slot, *, planner_pass=True, queries=1, scenes=1, elapsed=1.0, failure_class=None):
        value = {
            "schema_version": "cmf_planner_wiring_smoke_normalized_terminal_v1",
            "wave_id": json.loads((ledger / "meta.json").read_text())["wave_id"],
            "slot": slot,
            "planner_query_count": queries,
            "scene_count": scenes,
            "elapsed_seconds": elapsed,
            "physical_execution_count": 0,
            "trajectory_count": 0,
            "planner_pass": planner_pass,
            "failure_class": failure_class,
        }
        return write_hashed(ledger / "terminals" / f"{slot}.json", value, "normalized_terminal_sha256")

    def disk_job(
        self,
        ledger,
        slot,
        *,
        planner_pass=True,
        failure_class=None,
        failure_code=None,
        queries=1,
        scenes=1,
        elapsed=1.0,
        job_kind="F2_STAGE_A",
        family="F2",
        stage_a_spec=None,
        job_terminal=None,
        scene_seed=1234,
    ):
        wave_id = json.loads((ledger / "meta.json").read_text())["wave_id"]
        auth_path = self.root / f"{ledger.name}-{slot}.auth.json"
        output = self.root / f"{ledger.name}-{slot}.output"
        guard_path = self.root / f"{ledger.name}-{slot}.guard.json"
        auth = {
            "wave_id": wave_id,
            "slot": slot,
            "job_kind": job_kind,
            "family": family,
            "authorization_id": f"{wave_id}-{slot}",
            "authorization_receipt_path": str(auth_path),
            "output_namespace": str(output),
            "guard_receipt_path": str(guard_path),
            "planner_query_limit": max(queries, 42),
            "scene_seed": scene_seed,
        }
        auth["receipt_sha256"] = canonical_hash_json(auth)
        canonical_write_json(auth_path, auth, exclusive=True, mode=0o600)
        record_slot_issuance_v1(
            ledger,
            slot=slot,
            authorization_receipt_path=auth_path,
            authorization=auth,
        )
        output.mkdir()
        if stage_a_spec is not None:
            canonical_write_json(
                output / "stage_a_spec.json",
                stage_a_spec,
                exclusive=True,
                mode=0o600,
            )
        if job_terminal is None:
            job_terminal = {
                "scene_instance_id": f"{wave_id}-{slot}-scene",
            }
            job_terminal["receipt_sha256"] = canonical_hash_json(job_terminal)
        if stage_a_spec is not None:
            canonical_write_json(
                output / "stage_a_terminal.json",
                job_terminal,
                exclusive=True,
                mode=0o600,
            )
        cleanup = {"cleanup_safety_pass": True, "orphan_process_count": 0}
        dispatch = {
            "job_terminal": job_terminal,
            "job_terminal_receipt_sha256": job_terminal["receipt_sha256"],
            "cleanup": cleanup,
            "planner_query_count": queries,
            "planner_pass": planner_pass,
            "failure_class": failure_class,
            "failure_code": failure_code,
        }
        dispatch["receipt_sha256"] = canonical_hash_json(dispatch)
        outer = {
            "schema_version": "cmf_planner_qualification_outer_terminal_v2_3_1a",
            "wave_id": wave_id,
            "slot": slot,
            "job_kind": job_kind,
            "family": family,
            "authorization_id": auth["authorization_id"],
            "authorization_receipt_sha256": auth["receipt_sha256"],
            "planner_pass": planner_pass,
            "failure_class": failure_class,
            "failure_code": failure_code,
            "planner_query_count": queries,
            "scene_count": scenes,
            "scene_instance_id": job_terminal["scene_instance_id"],
            "elapsed_seconds": elapsed,
            "dispatch": dispatch,
            "physical_execution_count": 0,
            "trajectory_count": 0,
        }
        outer["receipt_sha256"] = canonical_hash_json(outer)
        canonical_write_json(
            output / "receipt.json", outer, exclusive=True, mode=0o600
        )
        guard = {
            "schema_version": "cmf_gpu_guard_v2_4_1",
            "purpose": "planner_wiring_smoke_v1",
            "status": "completed" if failure_class is None else "completed_child_failed",
            "binding": {
                "authorization_id": auth["authorization_id"],
                "authorization_receipt_sha256": auth["receipt_sha256"],
            },
            "job_cache_cleanup": {"succeeded": True},
            "gpu_lease_release": {"released": True},
            "orphan_process_count": 0,
            "postcheck_release": {"verified": True},
        }
        guard["guard_receipt_sha256"] = canonical_hash_json(guard)
        canonical_write_json(guard_path, guard, exclusive=True, mode=0o600)
        with patch(
            "controlled_multi_future.probes."
            "planner_qualification_authorization_v2_3_1a.validate",
            return_value=auth,
        ):
            normalized = record_outer_terminal_v1(
                ledger,
                authorization_receipt_path=auth_path,
                outer_terminal_path=output / "receipt.json",
                guard_receipt_path=guard_path,
            )
        return normalized, auth, output

    def test_01_f4_manifest_v1_1_is_12_plus_30_equals_42(self):
        old = build_f4_program_panel_manifest_v1()
        new = build_f4_program_panel_manifest_v1_1()
        self.assertEqual(old["queries_per_job"], 30)
        self.assertEqual(new["target_construction_query_limit_per_job"], 12)
        self.assertEqual(new["chain_query_limit_per_job"], 30)
        self.assertEqual(new["total_query_limit_per_job"], 42)
        self.assertEqual(new["candidate_count"], 8)
        self.assertEqual(new["programs_per_candidate"], 3)
        self.assertEqual(new["ordered_jobs"], old["ordered_jobs"])

    def test_02_full_f4_maximum_is_1008(self):
        bundle = build_manifest_bundle_v2_3_1a()
        smoke = build_updated_planner_wiring_smoke_v1_proposal_v2()
        full = build_updated_full_planner_panel_v1_proposal_v2()
        self.assertEqual(bundle["manifests"]["F4"]["maximum_panel_queries"], 1008)
        self.assertEqual(smoke["aggregate"]["planner_query_limit"], 152)
        self.assertEqual(full["F4"]["maximum_queries"], 1008)
        self.assertEqual(full["maximum_aggregate_queries"], 1696)

    def test_03_s1_normalized_terminal_drives_s2_issuance(self):
        ledger, _, _ = self.init_ledger("s1-s2")
        self.disk_job(ledger, "S1")
        decision = validate_slot_issuance_from_ledger_v1(ledger, slot="S2")
        self.assertEqual(decision["slot"], "S2")
        self.assertEqual(len(decision["prior_normalized_terminal_sha256s"]), 1)

    def test_04_unhashed_or_forged_prior_terminal_is_rejected(self):
        ledger, _, _ = self.init_ledger("forged")
        canonical_write_json(
            ledger / "terminals" / "S1.json",
            {"schema_version": "forged", "slot": "S1"},
            exclusive=True,
            mode=0o600,
        )
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_wave_ledger_state_v1(ledger)
        hashed_ledger, _, _ = self.init_ledger("forged-hashed")
        write_hashed(
            hashed_ledger / "terminals" / "S1.json",
            {
                "schema_version": "forged_but_self_hashed",
                "wave_id": "wave-forged-hashed",
                "slot": "S1",
            },
            "normalized_terminal_sha256",
        )
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            load_wave_ledger_state_v1(hashed_ledger)

    def test_05_duplicate_slot_is_rejected(self):
        ledger, _, _ = self.init_ledger("duplicate")
        auth_path = self.root / "duplicate-auth.json"
        auth = {
            "wave_id": "wave-duplicate",
            "slot": "S1",
            "authorization_id": "duplicate-auth",
            "authorization_receipt_path": str(auth_path),
        }
        auth["receipt_sha256"] = canonical_hash_json(auth)
        self.manual_issued(ledger, "S1", auth)
        with self.assertRaises(FileExistsError):
            validate_slot_issuance_from_ledger_v1(ledger, slot="S1")

    def test_06_aggregate_query_scene_time_limits_are_hard(self):
        for label, values in (
            ("query", {"queries": 153}),
            ("scene", {"scenes": 10}),
            ("time", {"elapsed": 16201.0}),
        ):
            with self.subTest(label=label):
                ledger, _, _ = self.init_ledger(f"limit-{label}")
                with self.assertRaises((RuntimeError, ValueError)):
                    self.disk_job(ledger, "S1", **values)

    def test_07_infrastructure_terminal_permanently_closes_wave(self):
        ledger, _, _ = self.init_ledger("infra")
        self.disk_job(
            ledger,
            "S1",
            planner_pass=False,
            failure_class="INFRASTRUCTURE_ERROR",
            failure_code="TEST_INFRA",
        )
        with self.assertRaisesRegex(PermissionError, "closed"):
            validate_slot_issuance_from_ledger_v1(ledger, slot="S2")

    def make_f3_artifacts(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        bundle = build_manifest_bundle_v2_3_1a()
        entry = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"][0]
        envelope = prepare_exact_job_bridge_envelope_v2_3_1a(
            job_kind="F3_STAGE_A",
            job_id="f3-stage-a",
            manifest_entry=entry,
            manifest_context={},
            manifest_sha256=bundle["f3_stage_a_panel_sha256"],
            planner_reset_nonce=123,
        )
        recipe = entry["recipe"]
        actor_pose = [-0.18 if recipe["arm"] == "left" else 0.18, -0.06, 0.785, 0.0, 0.0, 1.0, 0.0]
        scene = SimpleNamespace(
            bottle=object(),
            _cmf_scene_instance_id="f3-stage-a-scene",
            _cmf_f3_scene_binding_v3_1=entry["scene_binding"],
        )
        with patch(
            "controlled_multi_future.f3_planner_integration_v3_1.generate_official_raw_pose_receipt_v1",
            return_value=raw_f3(recipe, actor_pose),
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._planner_reset",
            return_value={"reset_performed": True, "planner_seed": 123, "reset_seed_argument": True},
        ), patch(
            "controlled_multi_future.f3_planner_integration_v3_1._plan_chain",
            side_effect=successful_plan,
        ):
            terminal = run_f3_stage_a_planner_v3_1(scene, envelope["runner_spec"])
        spec_path = directory / "stage_a_spec.json"
        terminal_path = directory / "stage_a_terminal.json"
        canonical_write_json(spec_path, envelope["runner_spec"], exclusive=True, mode=0o600)
        canonical_write_json(terminal_path, terminal, exclusive=True, mode=0o600)
        registry = build_f3_stage_b_dependency_registry_v1_1(
            stage_a_spec_path=spec_path,
            stage_a_terminal_path=terminal_path,
            actual_scene_seed=envelope["actual_scene_seed"],
            stage_a_scene_instance_id=terminal["scene_instance_id"],
        )
        return bundle, entry, envelope, terminal, registry

    def test_08_f3_stage_a_pass_builds_stage_b_registry(self):
        ledger, _, _ = self.init_ledger("f3-auto")
        self.disk_job(ledger, "S1")
        bundle, entry, envelope, terminal, _ = self.make_f3_artifacts(
            self.root / "f3-source"
        )
        normalized, auth, output = self.disk_job(
            ledger,
            "S2",
            job_kind="F3_STAGE_A",
            family="F3",
            queries=3,
            scene_seed=envelope["actual_scene_seed"],
            stage_a_spec=envelope["runner_spec"],
            job_terminal=terminal,
        )
        registry = build_f3_stage_b_registry_from_wave_v1(
            ledger, stage_b_slot="S6A"
        )
        self.assertEqual(registry["actual_scene_seed"], normalized["scene_seed"])
        self.assertEqual(
            registry["stage_a_scene_instance_id"], terminal["scene_instance_id"]
        )

    def test_09_f3_stage_b_inherits_stage_a_scene_seed(self):
        bundle, entry, stage_a, _, registry = self.make_f3_artifacts(self.root)
        stage_b = prepare_exact_job_bridge_envelope_v2_3_1a(
            job_kind="F3_STAGE_B",
            job_id="f3-stage-b",
            manifest_entry=entry,
            manifest_context={},
            manifest_sha256=bundle["f3_stage_b_policy_sha256"],
            planner_reset_nonce=124,
            dependency_registry=registry,
        )
        self.assertEqual(stage_b["actual_scene_seed"], stage_a["actual_scene_seed"])

    def test_10_f4_three_programs_share_seed_and_use_distinct_scene_ids(self):
        bundle = build_manifest_bundle_v2_3_1a()
        jobs = [item for item in bundle["manifests"]["F4"]["ordered_jobs"] if item["candidate_rank"] == 1]
        candidate = bundle["manifests"]["F4"]["candidates"][0]
        envelopes = [
            prepare_exact_job_bridge_envelope_v2_3_1a(
                job_kind="F4_PROGRAM",
                job_id=f"f4-{job['program_id']}",
                manifest_entry=job,
                manifest_context={"source_candidate": bundle["manifests"]["F4"]["source_candidate"], "candidate": candidate},
                manifest_sha256=bundle["f4_panel_sha256"],
                planner_reset_nonce=200 + index,
            )
            for index, job in enumerate(jobs)
        ]
        self.assertEqual(len({item["actual_scene_seed"] for item in envelopes}), 1)
        scene_ids = []
        with patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a.RoboTwinRealSapienF4HierarchicalStageAV1Adapter",
            FakeAdapter,
        ), patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a.run_f4_program_planner_v2",
            side_effect=lambda scene, spec: {"receipt_sha256": "d" * 64, "scene_instance_id": scene._cmf_scene_instance_id},
        ):
            for job, envelope in zip(jobs, envelopes):
                auth = {"job_kind": "F4_PROGRAM", "family": "F4", "runner_symbol": envelope["runner_symbol"], "scene_seed": envelope["actual_scene_seed"], "implementation_source_sha256": SOURCE_SHA, "job_spec": {"job_id": envelope["job_id"], "scene_seed": envelope["actual_scene_seed"], "planner_reset_nonce": envelope["planner_reset_nonce"], "manifest_entry": job, "bridge_envelope": envelope}}
                scene_ids.append(run_with_production_scene_bridge_v2_3_1a(auth, output_root=self.root / job["program_id"])["terminal"]["scene_instance_id"])
        self.assertEqual(len(set(scene_ids)), 3)

    def test_11_actual_setup_seed_equals_authorization(self):
        bundle = build_manifest_bundle_v2_3_1a()
        entry = bundle["manifests"]["F2"]["ordered_recipes"][0]
        envelope = prepare_exact_job_bridge_envelope_v2_3_1a(
            job_kind="F2_STAGE_A", job_id="seed-test", manifest_entry=entry,
            manifest_context={"certificate": bundle["manifests"]["F2"]["certificate"], "bindings_by_arm": bundle["manifests"]["F2"]["bindings_by_arm"]},
            manifest_sha256=bundle["f2_panel_sha256"], planner_reset_nonce=300,
        )
        auth = {"job_kind": "F2_STAGE_A", "family": "F2", "runner_symbol": envelope["runner_symbol"], "scene_seed": envelope["actual_scene_seed"], "implementation_source_sha256": SOURCE_SHA, "job_spec": {"job_id": "seed-test", "scene_seed": envelope["actual_scene_seed"], "planner_reset_nonce": 300, "manifest_entry": entry, "bridge_envelope": envelope}}
        with patch("controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a.RoboTwinRealSapienF2HierarchicalStageAV1Adapter", FakeAdapter), patch("controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a.run_f2_final_grasp_stage_a_planner_v2", return_value={"receipt_sha256": "e" * 64}):
            FakeAdapter.force_seed = envelope["actual_scene_seed"] + 1
            with self.assertRaisesRegex(RuntimeError, "setup seed"):
                run_with_production_scene_bridge_v2_3_1a(auth, output_root=self.root / "wrong-seed")
            FakeAdapter.force_seed = None
            run_with_production_scene_bridge_v2_3_1a(auth, output_root=self.root / "right-seed")

    def f4_spec(self):
        manifest = build_f4_program_panel_manifest_v1_1()
        job = manifest["ordered_jobs"][0]
        candidate = manifest["candidates"][0]
        return build_f4_program_planner_spec_v2(
            manifest["source_candidate"], candidate, program_id=job["program_id"], slot_id="f4-test", planner_reset_nonce=400,
        )

    def test_12_f4_no_valid_grasp_is_candidate_fail(self):
        spec = self.f4_spec()
        scene = SimpleNamespace(_cmf_scene_instance_id="f4-fail", _cmf_scene_lifecycle="fresh", planner_query_count=0)
        audit = {"contact_point_ids": [0, 1, 2, 3], "batch_call_count": 4, "batch_receipts": [{"candidate_statuses": ["Fail"] * 10}] * 4}
        def fail(scene_arg, checked):
            scene_arg.planner_query_count += 4
            raise PlannerCandidateNoValidGrasp(context={"family": "F4", "candidate_id": checked["candidate_id"], "program_id": checked["program_id"], "failed_role": "A"}, audit=audit)
        with patch("controlled_multi_future.f4_program_planner_integration_v2._planner_reset", return_value={"reset_performed": True, "planner_seed": 400, "reset_seed_argument": True}), patch("controlled_multi_future.f4_program_planner_integration_v2.build_f4_stage_b_targets_v1", side_effect=fail):
            terminal = run_f4_program_planner_v2(scene, spec)
        self.assertEqual(terminal["failure_class"], "PLANNER_CANDIDATE_FAIL")
        self.assertEqual(terminal["failure_code"], "NO_VALID_GRASP_TARGET")
        self.assertEqual(terminal["planner_query_accounting"]["total_queries"], 4)

    def test_13_query_miscount_remains_infrastructure_error(self):
        spec = self.f4_spec()
        scene = SimpleNamespace(_cmf_scene_instance_id="f4-miscount", _cmf_scene_lifecycle="fresh", planner_query_count=0)
        def bad_count(scene_arg, checked):
            scene_arg.planner_query_count += 11
            return [], {}
        with patch("controlled_multi_future.f4_program_planner_integration_v2._planner_reset", return_value={"reset_performed": True, "planner_seed": 400, "reset_seed_argument": True}), patch("controlled_multi_future.f4_program_planner_integration_v2.build_f4_stage_b_targets_v1", side_effect=bad_count):
            with self.assertRaises(PlannerQueryAccountingError) as caught:
                run_f4_program_planner_v2(scene, spec)
        self.assertEqual(caught.exception.failure_class, "INFRASTRUCTURE_ERROR")

    def test_14_guard_purpose_is_planner_wiring_smoke(self):
        value = {"implementation_version": "controlled_multi_future_pre_smoke_hotfix_v2_3_1a"}
        self.assertEqual(planner_wiring_smoke_guard_purpose_v1(value), "planner_wiring_smoke_v1")
        self.assertEqual(
            planner_wiring_smoke_guard_purpose_v1(
                {"implementation_version": IMPLEMENTATION_VERSION}
            ),
            "planner_wiring_smoke_v1",
        )

    def issue_s1(self, suffix="source"):
        ledger, c, _ = self.init_ledger(f"issuer-{suffix}")
        source_path = self.root / f"source-{suffix}.json"
        source_path.write_text("{}", encoding="utf-8")
        source = {"source_lock_receipt_sha256": "c" * 64, "snapshot": {"implementation_source_sha256": c["implementation_source_sha256"], "official_repo_commit": ROBOTWIN_HEAD}}
        with patch("controlled_multi_future.planner_qualification_issuer_v2_3_1a.load_runtime_source_lock", return_value=source), patch("controlled_multi_future.probes.planner_qualification_authorization_v2_3_1a.load_runtime_source_lock", return_value=source):
            auth = issue_wave_job_authorization_v2_3_1a(
                activation_contract=c, wave_ledger_directory=ledger, job_slot="S1", authorization_id=f"auth-{suffix}", authorization_receipt_path=self.root / f"auth-{suffix}.json", source_lock_receipt_path=source_path, output_namespace=self.root / f"output-{suffix}", guard_receipt_path=self.root / f"guard-{suffix}.json", issued_at=datetime.now(timezone.utc),
            )
        return auth, source, c

    def test_15_source_change_invalidates_approval_and_authorization(self):
        auth, source, c = self.issue_s1("changed")
        changed_contract = contract(source_sha="9" * 64)
        with self.assertRaises(PermissionError):
            validate_wave_approval_v2(auth["wave_approval"], activation_contract=changed_contract)
        changed_source = copy.deepcopy(source)
        changed_source["snapshot"]["implementation_source_sha256"] = "9" * 64
        with patch("controlled_multi_future.probes.planner_qualification_authorization_v2_3_1a.load_runtime_source_lock", return_value=changed_source):
            with self.assertRaisesRegex(Exception, "source lock"):
                validate_authorization(auth, requested_scope=SCOPE, now=datetime.now(timezone.utc))

    def test_16_publication_head_later_than_source_freeze_is_not_mismatch(self):
        auth, source, c = self.issue_s1("publication")
        self.assertNotEqual(c["vault_head"], "6bab4344c03caaf0bc2f9445ff5810eadec3e19c")
        with patch("controlled_multi_future.probes.planner_qualification_authorization_v2_3_1a.load_runtime_source_lock", return_value=source):
            checked = validate_authorization(auth, requested_scope=SCOPE, expected_reviewed_content_commit=c["vault_head"], now=datetime.now(timezone.utc))
        self.assertEqual(checked["reviewed_content_commit"], c["vault_head"])

    def test_17_f3_binding_mismatch_retains_required_evidence(self):
        bundle = build_manifest_bundle_v2_3_1a()
        entry = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"][0]
        envelope = prepare_exact_job_bridge_envelope_v2_3_1a(
            job_kind="F3_STAGE_A",
            job_id="f3-mismatch",
            manifest_entry=entry,
            manifest_context={},
            manifest_sha256=bundle["f3_stage_a_panel_sha256"],
            planner_reset_nonce=500,
        )

        class Actor:
            def __init__(self, pose):
                self.pose = pose

            def get_pose(self):
                return SimpleNamespace(
                    p=np.asarray(self.pose[:3]), q=np.asarray(self.pose[3:])
                )

            def get_components(self):
                return []

        class Context:
            def __init__(self):
                source_x = -0.18 if entry["recipe"]["arm"] == "left" else 0.18
                self.handle = SimpleNamespace(
                    scene=SimpleNamespace(
                        bottle=Actor([source_x + 0.002, -0.06, 0.785, 0, 0, 1, 0]),
                        pad=Actor([source_x, -0.06, 0.745, 1, 0, 0, 0]),
                        central_marker=Actor([0, -0.05, 0.95, 1, 0, 0, 0]),
                        scene=SimpleNamespace(get_contacts=lambda: []),
                        _cmf_setup_kwargs={"seed": envelope["actual_scene_seed"]},
                        _cmf_canonical_settle_steps=60,
                        _cmf_scene_instance_id="f3-mismatch-scene",
                    )
                )
                self.cleanup_receipt = None

            def __enter__(self):
                return self.handle

            def __exit__(self, exc_type, exc, tb):
                self.cleanup_receipt = {
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }

        class Adapter:
            def __init__(self, **kwargs):
                pass

            def scene(self, *args, **kwargs):
                return Context()

        auth = {
            "job_kind": "F3_STAGE_A",
            "family": "F3",
            "runner_symbol": envelope["runner_symbol"],
            "scene_seed": envelope["actual_scene_seed"],
            "implementation_source_sha256": SOURCE_SHA,
            "job_spec": {
                "job_id": "f3-mismatch",
                "scene_seed": envelope["actual_scene_seed"],
                "planner_reset_nonce": 500,
                "manifest_entry": entry,
                "bridge_envelope": envelope,
            },
        }
        with patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a."
            "RoboTwinRealSapienF3AssetGraspV2Adapter",
            Adapter,
        ):
            with self.assertRaises(F3ActualSceneBindingMismatch) as caught:
                run_with_production_scene_bridge_v2_3_1a(
                    auth, output_root=self.root / "f3-mismatch-output"
                )
        evidence = caught.exception.evidence
        for key in (
            "asset_model_id",
            "scene_seed",
            "canonical_settle_steps",
            "expected_bottle_pose",
            "actual_bottle_pose",
            "position_delta_xyz",
            "position_error_m",
            "orientation_error_rad",
            "expected_pad_pose",
            "actual_pad_pose",
            "expected_marker_pose",
            "actual_marker_pose",
            "actor_sleep_state",
            "table_pad_contact_state",
        ):
            self.assertIn(key, evidence)
        self.assertTrue(caught.exception.cleanup_receipt["cleanup_safety_pass"])

    def test_18_wave_terminal_is_self_hashed_and_records_skips(self):
        ledger, _, _ = self.init_ledger("terminal")
        self.disk_job(
            ledger,
            "S1",
            planner_pass=False,
            failure_class="INFRASTRUCTURE_ERROR",
            failure_code="TEST_STOP",
        )
        terminal = finalize_wave_terminal_v1(ledger)
        payload = dict(terminal)
        digest = payload.pop("wave_terminal_sha256")
        self.assertEqual(digest, canonical_hash_json(payload))
        self.assertEqual(terminal["status"], "INFRASTRUCTURE_ERROR_STOPPED")
        self.assertEqual(set(terminal["skipped_slots"]), set(("S2", "S3", "S4", "S5", "S6A", "S6B", "S7A", "S7B")))

    def test_19_preclaimed_guard_is_narrowly_accepted(self):
        auth, source, _ = self.issue_s1("preclaimed")
        self.assertEqual(auth["implementation_version"], IMPLEMENTATION_VERSION)
        guard_path = Path(auth["guard_receipt_path"])
        starting = {
            "schema_version": "cmf_gpu_guard_v2_4_1",
            "purpose": "planner_wiring_smoke_v1",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "starting",
        }
        canonical_write_json(guard_path, starting, exclusive=True, mode=0o600)
        source_patch = patch(
            "controlled_multi_future.probes."
            "planner_qualification_authorization_v2_3_1a."
            "load_runtime_source_lock",
            return_value=source,
        )
        with source_patch:
            checked = validate_authorization(
                auth,
                requested_scope=SCOPE,
                allow_preclaimed_guard_receipt=True,
                now=datetime.now(timezone.utc),
            )
        self.assertEqual(checked["receipt_sha256"], auth["receipt_sha256"])
        with source_patch:
            with self.assertRaisesRegex(Exception, "O_EXCL"):
                validate_authorization(
                    auth,
                    requested_scope=SCOPE,
                    now=datetime.now(timezone.utc),
                )
        starting["status"] = "precheck_passed"
        canonical_write_json(guard_path, starting, mode=0o600)
        with source_patch:
            with self.assertRaisesRegex(Exception, "exact starting"):
                validate_authorization(
                    auth,
                    requested_scope=SCOPE,
                    allow_preclaimed_guard_receipt=True,
                    now=datetime.now(timezone.utc),
                )

    def test_20_active_guard_requires_self_hash_and_authorization_binding(self):
        auth, source, _ = self.issue_s1("active")
        guard_path = Path(auth["guard_receipt_path"])
        active = {
            "schema_version": "cmf_gpu_guard_v2_4_1",
            "purpose": "planner_wiring_smoke_v1",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "precheck_passed",
            "binding": {
                "authorization_id": auth["authorization_id"],
                "authorization_receipt_sha256": auth["receipt_sha256"],
                "output_namespace": auth["output_namespace"],
                "command_sha256": auth["authorized_command_sha256"],
            },
        }
        active["guard_receipt_sha256"] = canonical_hash_json(active)
        canonical_write_json(guard_path, active, exclusive=True, mode=0o600)
        source_patch = patch(
            "controlled_multi_future.probes."
            "planner_qualification_authorization_v2_3_1a."
            "load_runtime_source_lock",
            return_value=source,
        )
        with source_patch:
            checked = validate_authorization(
                auth,
                requested_scope=SCOPE,
                allow_active_guard_receipt=True,
                now=datetime.now(timezone.utc),
            )
        self.assertEqual(checked["authorization_id"], auth["authorization_id"])
        active["binding"]["output_namespace"] = str(self.root / "tampered")
        active.pop("guard_receipt_sha256")
        active["guard_receipt_sha256"] = canonical_hash_json(active)
        canonical_write_json(guard_path, active, mode=0o600)
        with source_patch:
            with self.assertRaisesRegex(Exception, "active Guard"):
                validate_authorization(
                    auth,
                    requested_scope=SCOPE,
                    allow_active_guard_receipt=True,
                    now=datetime.now(timezone.utc),
                )

    def test_21_prevalidation_terminal_api_closes_without_manual_artifacts(self):
        auth, _, _ = self.issue_s1("prechild")
        ledger = Path(auth["wave_ledger_directory"])
        guard_path = Path(auth["guard_receipt_path"])
        guard = {
            "schema_version": "cmf_gpu_guard_v2_4_1",
            "purpose": "planner_wiring_smoke_v1",
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "failed_authorization_binding",
            "error": {
                "type": "AuthorizationBindingError",
                "message": "synthetic prevalidation failure",
            },
            "elapsed_seconds": 0.25,
        }
        guard["guard_receipt_sha256"] = canonical_hash_json(guard)
        canonical_write_json(guard_path, guard, exclusive=True, mode=0o600)
        normalized = record_guard_prevalidation_terminal_v1(
            ledger,
            authorization_receipt_path=Path(
                auth["authorization_receipt_path"]
            ),
            guard_receipt_path=guard_path,
            failure_code="TEST_PREVALIDATION_FAILURE",
        )
        self.assertEqual(normalized["planner_query_count"], 0)
        self.assertEqual(normalized["scene_count"], 0)
        terminal = finalize_wave_terminal_v1(ledger)
        self.assertEqual(terminal["status"], "INFRASTRUCTURE_ERROR_STOPPED")
        self.assertEqual(terminal["aggregate"]["planner_query_count"], 0)
        self.assertEqual(
            set(terminal["skipped_slots"]),
            {"S2", "S3", "S4", "S5", "S6A", "S6B", "S7A", "S7B"},
        )
        with self.assertRaises(Exception):
            record_guard_prevalidation_terminal_v1(
                ledger,
                authorization_receipt_path=Path(
                    auth["authorization_receipt_path"]
                ),
                guard_receipt_path=guard_path,
                failure_code="TEST_DUPLICATE",
            )

    def test_22_real_guard_main_crosses_prevalidation_before_fake_busy_gate(self):
        source = capture_runtime_source_lock(family="F2")
        source_path = self.root / "real-source-lock.json"
        write_runtime_source_lock(source_path, source)
        c = contract(
            source_sha=source["snapshot"]["implementation_source_sha256"]
        )
        ledger = self.root / "real-guard-ledger"
        initialize_wave_ledger_v1(
            ledger,
            activation_contract=c,
            wave_approval=approval(c, wave_id="wave-real-guard-main"),
        )
        auth = issue_wave_job_authorization_v2_3_1a(
            activation_contract=c,
            wave_ledger_directory=ledger,
            job_slot="S1",
            authorization_id=f"real-guard-{self.root.name}",
            authorization_receipt_path=self.root / "real-guard-auth.json",
            source_lock_receipt_path=source_path,
            output_namespace=self.root / "real-guard-output",
            guard_receipt_path=self.root / "real-guard.json",
            issued_at=datetime.now(timezone.utc),
        )
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_smi = fake_bin / "nvidia-smi"
        fake_smi.write_text(
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  --query-gpu=*) printf '0, GPU-test, 500, 99, P2\\n' ;;\n"
            "  --query-compute-apps=*) printf 'GPU-test, 424242, 500\\n' ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_smi.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = str(fake_bin) + ":" + environment.get("PATH", "")
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONPATH"] = "/nfs_share/lijunhui/Robotwin2/project/RoboTwin"
        environment.pop("LD_LIBRARY_PATH", None)
        command = [
            sys.executable,
            "-m",
            "controlled_multi_future.probes.gpu_guard_v2_4",
            "--authorization-receipt",
            auth["authorization_receipt_path"],
            "--consumption-ledger-dir",
            auth["consumption_ledger_directory"],
            "--physical-index",
            "0",
            "--expected-uuid",
            "GPU-test",
            "--timeout-seconds",
            str(auth["timeout_seconds"]),
            "--guard-receipt",
            auth["guard_receipt_path"],
            "--output-dir",
            auth["output_namespace"],
            "--",
            *auth["authorized_command"],
        ]
        completed = subprocess.run(
            command,
            cwd="/nfs_share/lijunhui/Robotwin2/project/RoboTwin",
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            42,
            msg=f"stdout={completed.stdout}\nstderr={completed.stderr}",
        )
        guard = json.loads(Path(auth["guard_receipt_path"]).read_text())
        self.assertEqual(guard["status"], "blocked_precheck_not_idle")
        self.assertNotEqual(guard["status"], "failed_authorization_binding")
        self.assertTrue(guard["job_cache_cleanup"]["succeeded"])
        self.assertTrue(guard["gpu_lease_release"]["released"])
        self.assertFalse(Path(auth["output_namespace"]).exists())
        self.assertFalse(
            (
                Path(auth["consumption_ledger_directory"])
                / f"{auth['authorization_id']}.json"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
