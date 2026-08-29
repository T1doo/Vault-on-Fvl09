"""Deterministic builder for the pending (never self-approved) A0 request."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Sequence

from .current_hasher import hash_json
from .probes.gpu_guard_v2_1 import command_sha256
from .probes.runtime_v3_1_authorization_v1_1 import (
    ALLOWED_UUID_POLICY,
    AUTHORIZATION_SCHEMA_VERSION,
    current_source_bindings,
)
from .runtime_v3_1_budget_v1_1 import scope_budget


REQUEST_SCHEMA_VERSION = "cmf_runtime_v3_1_a0_user_approval_request_v5"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def build_a0_user_approval_request_v5(
    *,
    content_commit: str,
    authorization_receipt_path: str,
    output_namespace: str,
    consumption_ledger_directory: str,
    guard_receipt_path: str,
    allowed_physical_gpu_indices: Sequence[int] = tuple(range(8)),
) -> dict:
    if HEX40.fullmatch(content_commit) is None:
        raise ValueError("approval request requires the reviewed full content commit")
    for label, value in (
        ("authorization_receipt_path", authorization_receipt_path),
        ("output_namespace", output_namespace),
        ("consumption_ledger_directory", consumption_ledger_directory),
        ("guard_receipt_path", guard_receipt_path),
    ):
        if not value.startswith("/nfs_share/lijunhui/") or "/../" in value:
            raise ValueError(f"{label} must be an absolute workspace path")
    indices = list(allowed_physical_gpu_indices)
    if not indices or len(set(indices)) != len(indices) or any(index not in range(8) for index in indices):
        raise ValueError("approval request GPU indices must be a unique subset of physical 0-7")

    scope = "A0_current_anchor_smoke"
    budget = scope_budget(scope)
    planned = {
        "slot_id": "runtime_v3_1_A0_v5_F1_seed20260829",
        "family": "F1",
        "seed": 20260829,
        "origin": "nonformal_A0_user_approved_once",
    }
    child_command = [
        "/nfs_share/lijunhui/Robotwin2/env/bin/python",
        "-m",
        "controlled_multi_future.probes.a0_real_sapien_adapter_smoke",
        "--authorization-receipt",
        authorization_receipt_path,
    ]
    bindings = current_source_bindings()
    authorization_template = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "authorization_id": "a0-f1-seed20260829-v5-auth1",
        "authorized_run_id": "a0-f1-seed20260829-v5-run1",
        "issued_at": None,
        "expires_at": None,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_runtime_v3_1",
        "implementation_revision": "runtime_v3_1_cpu_hardening_v5",
        "content_commit": content_commit,
        **bindings,
        "approved": False,
        "approved_scopes": [scope],
        "family": "F1",
        "scene_seed": 20260829,
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": hash_json(planned),
        "scene_pattern": budget["scene_pattern"],
        "planner_query_limit": budget["planner_query_limit"],
        "controlled_action_limit": budget["controlled_action_limit"],
        "timeout_seconds": budget["timeout_seconds"],
        "max_invocations": budget["max_invocations"],
        "scope_budget": budget,
        "scope_budget_sha256": budget["scope_budget_sha256"],
        "allowed_physical_gpu_indices": indices,
        "allowed_gpu_uuid_policy": ALLOWED_UUID_POLICY,
        "output_namespace": output_namespace,
        "authorized_command_sha256": command_sha256(child_command),
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "receipt_sha256": None,
    }
    request = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "status": "pending_user_approval",
        "approved": False,
        "gpu_probe_authorized": False,
        "stage0_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "requested_scope": scope,
        "family": "F1",
        "scene_seed": 20260829,
        "scene_pattern": budget["scene_pattern"],
        "post_setup_planner_query_limit": 0,
        "post_setup_controlled_action_limit": 0,
        "timeout_seconds": 600,
        "max_invocations": 1,
        "content_commit": content_commit,
        "source_bindings": bindings,
        "planned_root_slot_spec": planned,
        "planned_root_slot_spec_sha256": hash_json(planned),
        "scope_budget": budget,
        "authorization_receipt_path_if_approved": authorization_receipt_path,
        "consumption_ledger_directory": consumption_ledger_directory,
        "guard_receipt_path": guard_receipt_path,
        "output_namespace": output_namespace,
        "allowed_physical_gpu_indices": indices,
        "allowed_gpu_uuid_policy": ALLOWED_UUID_POLICY,
        "exact_child_command": child_command,
        "exact_child_command_sha256": command_sha256(child_command),
        "guard_command_template": [
            "/nfs_share/lijunhui/Robotwin2/env/bin/python",
            "-m",
            "controlled_multi_future.probes.gpu_guard_v2_1",
            "--authorization-receipt",
            authorization_receipt_path,
            "--consumption-ledger-dir",
            consumption_ledger_directory,
            "--physical-index",
            "<fresh-idle-authorized-index>",
            "--expected-uuid",
            "<freshly-verified-matching-uuid>",
            "--timeout-seconds",
            "600",
            "--guard-receipt",
            guard_receipt_path,
            "--output-dir",
            output_namespace,
            "--",
            *child_command,
        ],
        "expected_artifacts": [
            "receipt.json",
            "planned_root_slot_spec.json",
            "scenes/00_A0_pristine/{current,anchor,activity,cleanup,artifact_hashes}.json",
            "scenes/01_A0_fresh_1/{current,anchor,activity,cleanup,artifact_hashes}.json",
            "scenes/02_A0_fresh_2/{current,anchor,activity,cleanup,artifact_hashes}.json",
            "scenes/03_A0_fresh_3/{current,anchor,activity,cleanup,artifact_hashes}.json",
            "guard receipt with pre/post GPU and one-shot consumption binding",
        ],
        "success_conditions": [
            "four unique scenes created and cleaned",
            "all fresh currents exactly match the pristine current",
            "all physical anchors are equivalent under frozen tolerances",
            "each v2 activity receipt has zero planner/control/physics deltas",
            "all artifact hashes recompute",
            "no task-owned orphan and GPU returns to baseline",
        ],
        "failure_conditions": [
            "authorization replay/expiry/scope/binding failure",
            "guard authorization/budget/GPU mismatch",
            "activity monitor installation/restoration/binding/reuse failure",
            "nonzero post-setup planner/control/physics activity",
            "current or anchor mismatch",
            "cleanup/orphan/post-release uncertainty",
            "timeout or missing child receipt",
        ],
        "authorization_template_pending_user_action": authorization_template,
        "explicit_non_actions": [
            "does not create an approved authorization receipt",
            "does not consume authorization",
            "does not run GPU/SAPIEN/A0",
            "does not authorize family probes or Stage 0",
        ],
    }
    request["approval_request_sha256"] = _sha256(request)
    return request
