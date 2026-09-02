"""Versioned single-job issuer for a future approved V2.3 wiring smoke.

The issuer is inert without a separate self-hashed approval that binds the
current seal and exact job envelope.  This module performs no file write and
does not launch a planner or GPU.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .gpu_parallel_policy_v2 import current_gpu_policy_artifact
from .planner_qualification_integration_v2_3 import (
    IMPLEMENTATION_VERSION,
    RUNNER_SYMBOLS,
    build_manifest_bundle_v2_3,
    validate_f4_next_job_v1,
)
from .probes.planner_qualification_authorization_v2_3 import AUTH_SCHEMA, receipt_sha


QUERY_LIMITS = {"F2_STAGE_A": 3, "F3_STAGE_A": 3, "F3_STAGE_B": 7, "F4_PROGRAM": 30}


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"V2.3 issuer {label} hash mismatch")
    return result


def build_planner_job_envelope_v2_3(
    seal: Mapping[str, Any],
    *,
    job_kind: str,
    manifest_entry: Mapping[str, Any],
    job_id: str,
    scene_id: str,
    output_path: str,
    prior_terminals: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    contract = _self_hashed(seal, "contract_sha256", "seal")
    if contract.get("implementation_version") != IMPLEMENTATION_VERSION:
        raise ValueError("V2.3 issuer seal implementation changed")
    if job_kind not in RUNNER_SYMBOLS:
        raise ValueError("V2.3 issuer job kind is unsupported")
    bundle = build_manifest_bundle_v2_3()
    if contract.get("manifest_bundle_sha256") != bundle["bundle_sha256"]:
        raise ValueError("V2.3 issuer manifest bundle changed")
    entry = canonical_jsonable(manifest_entry)
    if job_kind == "F2_STAGE_A":
        source = bundle["manifests"]["F2"]["ordered_recipes"]
        identity_key, manifest_sha = "entry_sha256", bundle["f2_panel_sha256"]
    elif job_kind == "F3_STAGE_A":
        source = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
        identity_key, manifest_sha = "entry_sha256", bundle["f3_stage_a_panel_sha256"]
    elif job_kind == "F3_STAGE_B":
        source = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"]
        identity_key, manifest_sha = "entry_sha256", bundle["f3_stage_b_policy_sha256"]
        matching_terminals = [
            item
            for item in prior_terminals
            if item.get("recipe_sha256") == entry.get("recipe_sha256")
            and item.get("stage_a_pass") is True
        ]
        if len(matching_terminals) != 1:
            raise ValueError("V2.3 F3 Stage-B requires one bound Stage-A pass")
    else:
        entry = validate_f4_next_job_v1(
            bundle["manifests"]["F4"], entry, prior_terminals
        )
        source = bundle["manifests"]["F4"]["ordered_jobs"]
        identity_key, manifest_sha = "job_sha256", bundle["f4_panel_sha256"]
    matches = [item for item in source if item.get(identity_key) == entry.get(identity_key)]
    if len(matches) != 1 or matches[0] != entry:
        raise ValueError("V2.3 issuer entry is outside exact manifest")
    output = Path(output_path)
    if not output.is_absolute() or not str(output).startswith("/nfs_share/lijunhui/"):
        raise ValueError("V2.3 issuer output path is outside workspace")
    if output.exists():
        raise FileExistsError("V2.3 issuer requires a nonexistent O_EXCL output")
    seed = 2026090300 + int(entry.get("panel_rank", entry.get("candidate_rank", 0)))
    job_spec = {
        "job_id": str(job_id),
        "scene_id": str(scene_id),
        "job_kind": job_kind,
        "manifest_entry_sha256": entry[identity_key],
        "manifest_sha256": manifest_sha,
        "runner_symbol": RUNNER_SYMBOLS[job_kind],
        "planner_rng_seed": seed,
        "planner_rng_reset_required": True,
        "planner_query_limit": QUERY_LIMITS[job_kind],
        "scene_limit": 1,
        "physical_execution_limit": 0,
        "prior_terminal_receipt_sha256s": [
            item.get("receipt_sha256") for item in prior_terminals
        ],
    }
    job_spec["job_spec_sha256"] = canonical_hash_json(job_spec)
    value = {
        "schema_version": "cmf_planner_job_envelope_v2_3",
        "integration_contract_sha256": contract["contract_sha256"],
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "manifest_sha256": manifest_sha,
        "job_kind": job_kind,
        "runner_symbol": RUNNER_SYMBOLS[job_kind],
        "job_spec": job_spec,
        "job_spec_sha256": job_spec["job_spec_sha256"],
        "output_path": str(output),
        "output_preexisting": False,
        "o_excl_output_required": True,
        "source_change_invalidates_authorization": True,
        "automatic_retry": False,
        "fallback_allowed": False,
        "physical_execution_limit": 0,
    }
    value["envelope_sha256"] = canonical_hash_json(value)
    return value


def issue_planner_authorization_v2_3(
    seal: Mapping[str, Any],
    envelope: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    *,
    authorization_id: str,
    requested_scope: str,
    issued_at: datetime | None = None,
    validity_seconds: int = 1800,
) -> dict[str, Any]:
    contract = _self_hashed(seal, "contract_sha256", "seal")
    job = _self_hashed(envelope, "envelope_sha256", "job envelope")
    if approval is None:
        raise PermissionError("V2.3 issuer requires separate user/senior approval")
    approved = _self_hashed(approval, "approval_sha256", "approval")
    if (
        approved.get("schema_version") != "cmf_planner_wiring_smoke_user_approval_v1"
        or approved.get("approved") is not True
        or approved.get("approved_scope") != requested_scope
        or approved.get("integration_contract_sha256") != contract["contract_sha256"]
        or approved.get("job_envelope_sha256") != job["envelope_sha256"]
    ):
        raise PermissionError("V2.3 approval does not bind this exact job")
    if not 0 < int(validity_seconds) <= 3600:
        raise ValueError("V2.3 authorization validity must be at most one hour")
    now = (issued_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    policy = current_gpu_policy_artifact()
    value = {
        "schema_version": AUTH_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": str(authorization_id),
        "approved": True,
        "approved_scopes": [requested_scope],
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=int(validity_seconds))).isoformat(),
        "integration_contract_sha256": contract["contract_sha256"],
        "approval_sha256": approved["approval_sha256"],
        "job_envelope_sha256": job["envelope_sha256"],
        "job_kind": job["job_kind"],
        "manifest_bundle_sha256": job["manifest_bundle_sha256"],
        "manifest_sha256": job["manifest_sha256"],
        "runner_symbol": job["runner_symbol"],
        "job_spec": job["job_spec"],
        "job_spec_sha256": job["job_spec_sha256"],
        "planner_query_limit": job["job_spec"]["planner_query_limit"],
        "scene_limit": 1,
        "physical_execution_limit": 0,
        "max_invocations": 1,
        "automatic_retry": False,
        "fallback_allowed": False,
        "o_excl_output_required": True,
        "output_preexisting": False,
        "output_path": job["output_path"],
        "source_change_invalidates_authorization": True,
        "vault_head": contract["vault_head"],
        "active_source_tree_sha256": contract["active_source_tree_sha256"],
        "robotwin_tracked_head": contract["robotwin_tracked_head"],
        "formal_data": False,
        "stage1_authorized": False,
        "physical_execution_count": 0,
        **{
            key: policy[key]
            for key in (
                "gpu_policy_version", "allowed_physical_gpu_indices",
                "dynamic_fresh_idle_selection", "parallel_different_cards_authorized",
                "one_project_job_per_gpu", "one_root_one_gpu",
                "root_sharding_authorized", "share_busy_gpu_authorized",
                "atomic_guard_recheck_before_launch", "automatic_gpu0_fallback",
            )
        },
    }
    value["receipt_sha256"] = receipt_sha(value)
    return value


__all__ = [
    "build_planner_job_envelope_v2_3",
    "issue_planner_authorization_v2_3",
]
