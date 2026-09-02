"""Disk-ledger-authorized V2.3.1a single-job issuer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable, canonical_write_json
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .planner_qualification_integration_v2_3_1a import build_manifest_bundle_v2_3_1a
from .planner_qualification_scene_bridges_v2_3_1 import RUNNER_SYMBOLS
from .planner_qualification_scene_bridges_v2_3_1a import (
    prepare_exact_job_bridge_envelope_v2_3_1a,
)
from .planner_wiring_smoke_v2_3_1a import (
    build_updated_planner_wiring_smoke_v1_proposal_v2,
    validate_wave_approval_v2,
)
from .planner_wiring_smoke_wave_driver_v1 import (
    build_f3_stage_b_registry_from_wave_v1,
    load_wave_ledger_state_v1,
    record_slot_issuance_v1,
    validate_slot_issuance_from_ledger_v1,
)
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.planner_qualification_authorization_v2_3_1a import (
    AUTH_SCHEMA,
    GUARD_PURPOSE,
    IMPLEMENTATION_VERSION,
    SCOPE,
    receipt_sha,
    validate as validate_authorization,
)
from .probes.runtime_v3_3_authorization_v1 import (
    CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
    CANONICAL_GPU_LEASE_DIRECTORY,
    CANONICAL_JOB_CACHE_DIRECTORY,
)
from .runtime_source_lock_v1 import load_runtime_source_lock


PYTHON = "/nfs_share/lijunhui/Robotwin2/env/bin/python"
CHILD_MODULE = (
    "controlled_multi_future.probes."
    "planner_qualification_scope_runner_v2_3_1a"
)
FAMILIES = {
    "F2_STAGE_A": "F2",
    "F3_STAGE_A": "F3",
    "F3_STAGE_B": "F3",
    "F4_PROGRAM": "F4",
}


def _workspace_new(path: Path, label: str):
    value = Path(path).resolve()
    if not str(value).startswith("/nfs_share/lijunhui/"):
        raise ValueError(f"{label} is outside workspace")
    if value.exists():
        raise FileExistsError(f"{label} must be new/O_EXCL")
    return value


def exact_child_command_v2_3_1a(authorization_path: Path):
    return [
        PYTHON,
        "-m",
        CHILD_MODULE,
        "--authorization-receipt",
        str(Path(authorization_path).resolve()),
    ]


def _manifest_entry(bundle, slot):
    kind, identity = slot["job_kind"], slot["entry_sha256"]
    if kind == "F2_STAGE_A":
        values = bundle["manifests"]["F2"]["ordered_recipes"]
        key = "entry_sha256"
        context = {
            "certificate": bundle["manifests"]["F2"]["certificate"],
            "bindings_by_arm": bundle["manifests"]["F2"]["bindings_by_arm"],
        }
        manifest_sha = bundle["f2_panel_sha256"]
    elif kind in {"F3_STAGE_A", "F3_STAGE_B"}:
        values = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
        key, context = "entry_sha256", {}
        manifest_sha = (
            bundle["f3_stage_a_panel_sha256"]
            if kind == "F3_STAGE_A"
            else bundle["f3_stage_b_policy_sha256"]
        )
    else:
        values = bundle["manifests"]["F4"]["ordered_jobs"]
        key = "job_sha256"
        job = next(item for item in values if item[key] == identity)
        candidate = next(
            item
            for item in bundle["manifests"]["F4"]["candidates"]
            if item["candidate_sha256"] == job["candidate_sha256"]
        )
        context = {
            "source_candidate": bundle["manifests"]["F4"]["source_candidate"],
            "candidate": candidate,
        }
        manifest_sha = bundle["f4_panel_sha256"]
    matches = [item for item in values if item.get(key) == identity]
    if len(matches) != 1:
        raise ValueError("wave job is absent from corrected manifest")
    return matches[0], context, manifest_sha


def issue_wave_job_authorization_v2_3_1a(
    *,
    activation_contract: Mapping[str, Any],
    wave_ledger_directory: Path,
    job_slot: str,
    authorization_id: str,
    authorization_receipt_path: Path,
    source_lock_receipt_path: Path,
    output_namespace: Path,
    guard_receipt_path: Path,
    issued_at: datetime | None = None,
):
    state = load_wave_ledger_state_v1(wave_ledger_directory)
    contract = canonical_jsonable(activation_contract)
    contract_payload = dict(contract)
    contract_sha = contract_payload.pop("contract_sha256", None)
    if (
        contract_sha != canonical_hash_json(contract_payload)
        or contract != state["meta"]["activation_contract"]
    ):
        raise ValueError("activation contract differs from wave ledger")
    approval = validate_wave_approval_v2(
        state["meta"]["wave_approval"], activation_contract=contract
    )
    decision = validate_slot_issuance_from_ledger_v1(
        wave_ledger_directory, slot=job_slot
    )
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    slot = next(item for item in proposal["ordered_job_slots"] if item["slot"] == job_slot)
    bundle = build_manifest_bundle_v2_3_1a()
    entry, context, manifest_sha = _manifest_entry(bundle, slot)
    dependency = (
        build_f3_stage_b_registry_from_wave_v1(
            wave_ledger_directory, stage_b_slot=job_slot
        )
        if slot["job_kind"] == "F3_STAGE_B"
        else None
    )
    slot_index = proposal["ordered_job_slots"].index(slot) + 1
    nonce = 2026091600 + slot_index
    bridge = prepare_exact_job_bridge_envelope_v2_3_1a(
        job_kind=slot["job_kind"],
        job_id=authorization_id,
        manifest_entry=entry,
        manifest_context=context,
        manifest_sha256=manifest_sha,
        planner_reset_nonce=nonce,
        dependency_registry=dependency,
    )
    actual_seed = bridge["actual_scene_seed"]
    auth_path = _workspace_new(authorization_receipt_path, "authorization path")
    output = _workspace_new(output_namespace, "output namespace")
    guard = _workspace_new(guard_receipt_path, "guard path")
    source_path = Path(source_lock_receipt_path).resolve()
    source = load_runtime_source_lock(
        source_path, expected_family=FAMILIES[slot["job_kind"]]
    )
    if (
        source["snapshot"]["implementation_source_sha256"]
        != contract["implementation_source_sha256"]
        or source["snapshot"]["official_repo_commit"]
        != contract["robotwin_tracked_head"]
    ):
        raise ValueError("source lock differs from hotfix contract")
    job_spec = {
        "schema_version": "cmf_planner_qualification_job_spec_v2_3_1a",
        "wave_id": approval["wave_id"],
        "job_id": authorization_id,
        "slot": slot["slot"],
        "job_kind": slot["job_kind"],
        "family": FAMILIES[slot["job_kind"]],
        "scene_seed": actual_seed,
        "planner_reset_nonce": nonce,
        "motiongen_reset_seed_argument": True,
        "numeric_rng_seed_application_proven": False,
        "bitwise_determinism_claimed": False,
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "manifest_sha256": manifest_sha,
        "manifest_entry": entry,
        "manifest_context": context,
        "dependency_registry": dependency,
        "bridge_envelope": bridge,
        "bridge_envelope_sha256": bridge["bridge_envelope_sha256"],
        "planner_query_limit": slot["max_queries"],
        "physical_execution_limit": 0,
    }
    job_spec["job_spec_sha256"] = canonical_hash_json(job_spec)
    timeout = 3600 if slot["job_kind"] == "F4_PROGRAM" else 1800
    budget = {
        "planner_query_limit": slot["max_queries"],
        "scene_limit": 1,
        "controlled_action_limit": 0,
        "physics_step_limit": 5000,
        "timeout_seconds": timeout,
        "physical_execution_limit": 0,
    }
    budget["budget_receipt_sha256"] = canonical_hash_json(budget)
    command = exact_child_command_v2_3_1a(auth_path)
    envelope = {
        "schema_version": "cmf_planner_qualification_job_envelope_v2_3_1a",
        "wave_id": approval["wave_id"],
        "slot": slot["slot"],
        "job_spec_sha256": job_spec["job_spec_sha256"],
        "bridge_envelope_sha256": bridge["bridge_envelope_sha256"],
        "output_namespace": str(output),
        "guard_receipt_path": str(guard),
        "authorized_command_sha256": command_sha256(command),
    }
    envelope["job_envelope_sha256"] = canonical_hash_json(envelope)
    policy = current_gpu_policy_artifact()
    now = (issued_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    value = {
        "schema_version": AUTH_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization_id,
        "authorized_run_id": authorization_id + "-run",
        "wave_id": approval["wave_id"],
        "slot": slot["slot"],
        "approved": True,
        "approved_scopes": [SCOPE],
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
        "activation_contract": contract,
        "activation_contract_sha256": contract_sha,
        "wave_approval": approval,
        "parent_user_authorization_sha256": approval["wave_approval_sha256"],
        "job_envelope": envelope,
        "job_envelope_sha256": envelope["job_envelope_sha256"],
        "approval_request_sha256": envelope["job_envelope_sha256"],
        "job_kind": slot["job_kind"],
        "family": job_spec["family"],
        "scene_seed": actual_seed,
        "planner_reset_nonce": nonce,
        "motiongen_reset_seed_argument": True,
        "reset_receipt_bound_to_authorization": True,
        "numeric_rng_seed_application_proven": False,
        "bitwise_determinism_claimed": False,
        "guard_purpose": GUARD_PURPOSE,
        "runner_symbol": RUNNER_SYMBOLS[slot["job_kind"]],
        "job_spec": job_spec,
        "job_spec_sha256": job_spec["job_spec_sha256"],
        "planned_root_slot_spec_sha256": job_spec["job_spec_sha256"],
        "budget": budget,
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": 0,
        "physics_step_limit": 5000,
        "timeout_seconds": timeout,
        "physical_execution_limit": 0,
        "max_invocations": 1,
        "automatic_retry": False,
        "fallback_allowed": False,
        "authorization_receipt_path": str(auth_path),
        "output_namespace": str(output),
        "guard_receipt_path": str(guard),
        "authorized_command": command,
        "authorized_command_sha256": command_sha256(command),
        "source_lock_receipt_path": str(source_path),
        "source_lock_receipt_sha256": source["source_lock_receipt_sha256"],
        "implementation_source_sha256": contract["implementation_source_sha256"],
        "robotwin_tracked_head": contract["robotwin_tracked_head"],
        "reviewed_content_commit": contract["vault_head"],
        "wave_ledger_directory": str(Path(wave_ledger_directory).resolve()),
        "prior_normalized_terminal_sha256s": decision[
            "prior_normalized_terminal_sha256s"
        ],
        "consumption_ledger_directory": CANONICAL_CONSUMPTION_LEDGER_DIRECTORY,
        "gpu_lease_directory": CANONICAL_GPU_LEASE_DIRECTORY,
        "job_cache_root_directory": CANONICAL_JOB_CACHE_DIRECTORY,
        "family_revision_index": None,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "physical_execution_count": 0,
        **{
            key: policy[key]
            for key in (
                "gpu_policy_version",
                "allowed_physical_gpu_indices",
                "dynamic_fresh_idle_selection",
                "parallel_different_cards_authorized",
                "one_project_job_per_gpu",
                "one_root_one_gpu",
                "root_sharding_authorized",
                "share_busy_gpu_authorized",
                "atomic_guard_recheck_before_launch",
                "automatic_gpu0_fallback",
            )
        },
    }
    value["receipt_sha256"] = receipt_sha(value)
    validate_authorization(
        value,
        requested_scope=SCOPE,
        expected_output_namespace=str(output),
        expected_family=value["family"],
        expected_seed=actual_seed,
        expected_reviewed_content_commit=contract["vault_head"],
        now=now + timedelta(seconds=1),
    )
    canonical_write_json(auth_path, value, exclusive=True, mode=0o600)
    record_slot_issuance_v1(
        wave_ledger_directory,
        slot=job_slot,
        authorization_receipt_path=auth_path,
        authorization=value,
    )
    return value


__all__ = [
    "exact_child_command_v2_3_1a",
    "issue_wave_job_authorization_v2_3_1a",
]
