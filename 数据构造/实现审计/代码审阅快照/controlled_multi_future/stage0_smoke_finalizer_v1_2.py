"""Replacement-aware authoritative seal for the 12 active Stage-0 slots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .stage0_f2_replacement_manifest_v1_2 import (
    CANONICAL_OUTPUT as REPLACEMENT_MANIFEST_PATH,
    IMPLEMENTATION_VERSION,
    ORIGINAL_ATTEMPT_IDS,
    ORIGINAL_RESULT,
    OUTPUT_NAMESPACE,
    REPLACEMENT_ATTEMPT_IDS,
    validate_stage0_f2_replacement_manifest_v1_2,
)
from .stage0_smoke_family_runner_v1_1 import TERMINAL_OUTCOMES


AUDIT_ROOT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计"
)
CANONICAL_OUTPUT = AUDIT_ROOT / "STAGE0_SMOKE_RESULT_V1_2.json"
CANONICAL_SEAL_OUTPUT = AUDIT_ROOT / "STAGE0_SMOKE_TERMINAL_SEAL_V1_2.json"
SCHEMA_VERSION = "cmf_stage0_smoke_replacement_aware_finalizer_v1_2"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file(path: Path) -> dict[str, Any]:
    data = Path(path).read_bytes()
    return {
        "path": str(Path(path).resolve()),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _self_hash(value: Mapping[str, Any], field: str) -> bool:
    payload = dict(value)
    digest = payload.pop(field, None)
    return isinstance(digest, str) and hash_json(payload) == digest


def validate_f2_replacement_outer_v1_2(
    manifest: Mapping[str, Any], outer_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(outer_path).resolve()
    expected_path = (OUTPUT_NAMESPACE / "receipt.json").resolve()
    if path != expected_path or not path.is_file():
        raise ValueError("F2 replacement outer receipt path is noncanonical")
    outer = _load(path)
    inner_path = (
        path.parent
        / "stage0_f2_replacement/stage0_f2_replacement_family_receipt.json"
    )
    inner = _load(inner_path) if inner_path.is_file() else {}
    outer_file = _file(path)
    inner_file = _file(inner_path) if inner_path.is_file() else {}
    guard_path = Path(str(outer.get("guard_receipt", ""))).resolve()
    guard = _load(guard_path) if guard_path.is_file() else {}
    guard_payload = dict(guard)
    guard_digest = guard_payload.pop("guard_receipt_sha256", None)
    consumption_path = Path(str(guard.get("consumption_receipt", ""))).resolve()
    consumption = _load(consumption_path) if consumption_path.is_file() else {}
    consumption_payload = dict(consumption)
    consumption_digest = consumption_payload.pop(
        "consumption_receipt_sha256", None
    )
    checks = {
        "outer_seal": _self_hash(outer, "guard_sealed_receipt_sha256"),
        "outer_identity": outer.get("schema_version")
        == "cmf_stage0_f2_replacement_guarded_scope_receipt_v1_2"
        and outer.get("implementation_version") == IMPLEMENTATION_VERSION
        and outer.get("family") == "F2",
        "outer_complete": outer.get("status")
        == "completed_stage0_f2_replacement_v1_2"
        and outer.get("pipeline_integrity_pass") is True,
        "manifest": outer.get("replacement_manifest_sha256")
        == manifest.get("manifest_sha256"),
        "inner_file": bool(inner_file)
        and outer.get("result_receipt_file_sha256") == inner_file.get("sha256"),
        "inner_payload": _self_hash(inner, "receipt_sha256")
        and inner.get("receipt_sha256")
        == outer.get("result_receipt_payload_sha256"),
        "inner_pipeline": inner.get("pipeline_integrity_pass") is True
        and inner.get("active_slot_terminal_evidence_valid") is True,
        "attempt_count": len(inner.get("attempt_receipts", [])) == 3,
        "attempt_ids": [
            item.get("attempt_id") for item in inner.get("attempt_receipts", [])
        ]
        == list(REPLACEMENT_ATTEMPT_IDS),
        "replacement_ids": [
            item.get("replacement_for_attempt_id")
            for item in inner.get("attempt_receipts", [])
        ]
        == list(ORIGINAL_ATTEMPT_IDS),
        "no_active_infrastructure_failure": all(
            item.get("terminal_status")
            != "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
            for item in inner.get("attempt_receipts", [])
        ),
        "guard_hash": isinstance(guard_digest, str)
        and hash_json(guard_payload) == guard_digest,
        "guard_complete": guard.get("status") == "completed"
        and guard.get("post_source_lock_pass") is True
        and guard.get("timed_out") is False
        and int(guard.get("orphan_process_count", -1)) == 0
        and guard.get("postcheck_release", {}).get("verified") is True,
        "guard_child": guard.get("child_receipt_file", {}).get("sha256")
        == outer_file["sha256"],
        "consumption_hash": isinstance(consumption_digest, str)
        and hash_json(consumption_payload) == consumption_digest,
        "consumption_binding": consumption_digest
        == outer.get("authorization_consumption_receipt_sha256"),
        "cleanup": inner.get("cleanup_pass") is True
        and int(inner.get("orphan_process_count", -1)) == 0,
        "video_contract": inner.get("all_required_videos_complete") is True
        and int(inner.get("generated_video_count", -1))
        == int(inner.get("generated_trajectory_count", -2)),
        "no_stage1": inner.get("stage1_authorized") is False
        and inner.get("formal_collection_authorized") is False
        and inner.get("training_authorized") is False,
    }
    attempt_file_audits = []
    for attempt in inner.get("attempt_receipts", []):
        attempt_path = (
            inner_path.parent / "attempt_receipts" / f"{attempt.get('attempt_id')}.json"
        )
        stored = _load(attempt_path) if attempt_path.is_file() else None
        item_checks = {
            "exists": stored is not None,
            "exact": stored == attempt,
            "self_hash": isinstance(stored, Mapping)
            and _self_hash(stored, "receipt_sha256"),
            "terminal": isinstance(stored, Mapping)
            and stored.get("terminal_status") in TERMINAL_OUTCOMES,
        }
        attempt_file_audits.append(
            {
                "attempt_id": attempt.get("attempt_id"),
                "checks": item_checks,
                "pass": all(item_checks.values()),
            }
        )
    checks["attempt_files"] = len(attempt_file_audits) == 3 and all(
        item["pass"] for item in attempt_file_audits
    )
    audit = {
        "outer_path": str(path),
        "inner_path": str(inner_path),
        "guard_path": str(guard_path),
        "consumption_path": str(consumption_path),
        "attempt_file_audits": attempt_file_audits,
        "checks": checks,
        "pass": all(checks.values()),
    }
    return inner, audit


def finalize_stage0_smoke_v1_2() -> dict[str, Any]:
    manifest = validate_stage0_f2_replacement_manifest_v1_2(
        _load(REPLACEMENT_MANIFEST_PATH)
    )
    original = _load(ORIGINAL_RESULT)
    original_file = _file(ORIGINAL_RESULT)
    expected_original = manifest["original_result"]
    if original_file["sha256"] != expected_original["sha256"]:
        raise ValueError("original Stage 0 result file changed")
    original_attempts = {
        item.get("attempt_id"): item for item in original.get("attempt_receipts", [])
    }
    retained_ids = [
        attempt_id
        for attempt_id in original_attempts
        if attempt_id not in ORIGINAL_ATTEMPT_IDS
    ]
    retained = [original_attempts[item] for item in retained_ids]
    replacement, replacement_audit = validate_f2_replacement_outer_v1_2(
        manifest, OUTPUT_NAMESPACE / "receipt.json"
    )
    replacement_attempts = list(replacement.get("attempt_receipts", []))
    active = retained + replacement_attempts
    active_ids = [item.get("attempt_id") for item in active]
    active_family_counts = {
        family: sum(item.get("family") == family for item in active)
        for family in ("F1", "F2", "F3", "F4")
    }
    attempt_audits = []
    for item in active:
        checks = {
            "self_hash": _self_hash(item, "receipt_sha256"),
            "terminal": item.get("terminal_status") in TERMINAL_OUTCOMES,
            "no_active_infrastructure": item.get("terminal_status")
            != "FAILED_INFRASTRUCTURE_WITH_EVIDENCE",
            "stage0_not_formal": item.get("stage0_data") is True
            and item.get("formal_data") is False
            and item.get("stage1_authorized") is False,
            "video_if_trajectory": (
                item.get("trajectory_generated") is not True
                or (
                    item.get("video_required") is True
                    and item.get("video_integrity", {}).get("pass") is True
                )
            ),
        }
        # Historical F3/F4 smoke failures are valid active evidence, while F1 is pass.
        if item.get("family") in ("F1", "F3", "F4"):
            checks["original_outer_audit"] = original.get(
                "outer_receipt_audits", {}
            ).get(item.get("family"), {}).get("pass") is True
        if item.get("family") == "F2":
            checks["replacement_lineage"] = item.get(
                "replacement_for_attempt_id"
            ) in ORIGINAL_ATTEMPT_IDS
        attempt_audits.append(
            {
                "attempt_id": item.get("attempt_id"),
                "checks": checks,
                "pass": all(checks.values()),
            }
        )
    checks = {
        "original_authoritative": original.get("authoritative") is True,
        "original_attempt_phase_complete": original.get("terminal_attempt_count")
        == 12,
        "original_seal_failed_only_before_replacement": original.get(
            "stage0_completed"
        )
        is False,
        "old_f2_history_retained": all(
            item in original_attempts for item in ORIGINAL_ATTEMPT_IDS
        ),
        "replacement_outer": replacement_audit["pass"],
        "active_slot_count": len(active) == 12 and len(set(active_ids)) == 12,
        "active_family_counts": active_family_counts
        == {"F1": 3, "F2": 3, "F3": 3, "F4": 3},
        "active_attempts": len(attempt_audits) == 12
        and all(item["pass"] for item in attempt_audits),
        "replacement_mapping": [
            item.get("replacement_for_attempt_id")
            for item in replacement_attempts
        ]
        == list(ORIGINAL_ATTEMPT_IDS),
        "no_active_infrastructure_failure": all(
            item.get("terminal_status")
            != "FAILED_INFRASTRUCTURE_WITH_EVIDENCE"
            for item in active
        ),
    }
    completed = all(checks.values())
    successful = sum(item.get("terminal_status") == "PASSED" for item in active)
    result = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "authoritative": True,
        "replacement_manifest_sha256": manifest["manifest_sha256"],
        "original_stage0_result": original_file,
        "stage0_attempt_phase_completed": True,
        "stage0_completed": completed,
        "stage0_outcome": (
            "STAGE0_COMPLETED_ALL_ACTIVE_ATTEMPTS_PASSED"
            if completed and successful == 12
            else "STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE"
            if completed
            else "STAGE0_SEAL_FAILED"
        ),
        "active_stage0_slot_count": len(active),
        "historical_terminal_attempt_count": 15,
        "successful_attempt_count": successful,
        "failed_attempt_count": len(active) - successful,
        "generated_trajectory_count": sum(
            item.get("trajectory_generated") is True for item in active
        ),
        "generated_video_count": sum(
            item.get("trajectory_generated") is True
            and item.get("video_integrity", {}).get("pass") is True
            for item in active
        ),
        "family_outcomes": {
            family: (
                "PASS"
                if all(
                    item.get("terminal_status") == "PASSED"
                    for item in active
                    if item.get("family") == family
                )
                else "FAILED_WITH_EVIDENCE"
            )
            for family in ("F1", "F2", "F3", "F4")
        },
        "active_attempt_receipts": active,
        "superseded_f2_attempt_receipts": [
            original_attempts[item] for item in ORIGINAL_ATTEMPT_IDS
        ],
        "replacement_outer_audit": replacement_audit,
        "active_attempt_audits": attempt_audits,
        "checks": checks,
        "accepted_formal_root_count": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "h_reveal": None,
        "compression_authorized": False,
        "pi05_authorized": False,
    }
    result["receipt_sha256"] = hash_json(result)
    return result


def build_stage0_terminal_seal_v1_2(result: Mapping[str, Any]) -> dict[str, Any]:
    if not _self_hash(result, "receipt_sha256"):
        raise ValueError("Stage 0 v1.2 result self-hash is invalid")
    value = {
        "schema_version": "cmf_stage0_terminal_seal_v1_2",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage0_result_sha256": result["receipt_sha256"],
        "stage0_completed": result["stage0_completed"],
        "stage0_outcome": result["stage0_outcome"],
        "active_stage0_slot_count": result["active_stage0_slot_count"],
        "historical_terminal_attempt_count": result[
            "historical_terminal_attempt_count"
        ],
        "sealed_no_reopen_or_overwrite": result["stage0_completed"],
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    value["seal_sha256"] = hash_json(value)
    return value


__all__ = [
    "CANONICAL_OUTPUT",
    "CANONICAL_SEAL_OUTPUT",
    "build_stage0_terminal_seal_v1_2",
    "finalize_stage0_smoke_v1_2",
    "validate_f2_replacement_outer_v1_2",
]
