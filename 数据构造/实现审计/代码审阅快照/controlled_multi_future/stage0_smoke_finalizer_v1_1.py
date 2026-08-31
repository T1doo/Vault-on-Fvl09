"""Authoritative canonical finalizer for the 12-attempt Stage-0 v1.1 smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .f4_frozen_canonical_neutral_binding_v13 import (
    validate_f4_frozen_canonical_neutral_binding_v13,
)
from .probes.stage0_smoke_authorization_v1_1 import (
    CANONICAL_STAGE0_MANIFEST,
    DATASET_ROOT,
    STAGE0_NAMESPACE_BY_SCOPE,
    implementation_source_sha256_stage0_v1_1,
)
from .raw_writer import verify_raw_artifact_integrity
from .stage0_smoke_budget_v1_1 import STAGE0_SCOPES
from .stage0_smoke_family_runner_v1_1 import TERMINAL_OUTCOMES
from .stage0_smoke_manifest_v1_1 import (
    IMPLEMENTATION_VERSION,
    build_stage0_smoke_manifest_v1_1,
    validate_stage0_smoke_manifest_structure,
)
from .stage0_video_capture_v1 import (
    validate_stage0_trajectory_mp4_receipt_v1,
)


FAMILIES = ("F1", "F2", "F3", "F4")
SCHEMA_VERSION = "cmf_stage0_smoke_finalizer_v1_1"
CANONICAL_OUTPUT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "STAGE0_SMOKE_RESULT_V1_1_20260830.json"
)


def _self_hash(value: Mapping[str, Any], field: str) -> bool:
    payload = dict(value)
    digest = payload.pop(field, None)
    return isinstance(digest, str) and hash_json(payload) == digest


def canonical_outer_receipt_path_v1_1(family: str) -> Path:
    if family not in FAMILIES:
        raise ValueError("unsupported Stage 0 v1.1 family")
    scope = f"Stage0_v1_1_{family}_root_A"
    return DATASET_ROOT / STAGE0_NAMESPACE_BY_SCOPE[scope] / "receipt.json"


def validate_stage0_family_outer_receipt_v1_1(
    manifest: Mapping[str, Any], family: str, outer_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(outer_path).resolve()
    if path != canonical_outer_receipt_path_v1_1(family).resolve():
        raise ValueError(f"{family} Stage 0 v1.1 outer path is not canonical")
    outer = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    outer_file_sha = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    expected_relative = "stage0_family/stage0_family_receipt.json"
    inner_path = path.parent / expected_relative
    inner = json.loads(inner_path.read_text(encoding="utf-8")) if inner_path.is_file() else {}
    inner_file_sha = hashlib.sha256(inner_path.read_bytes()).hexdigest() if inner_path.is_file() else None
    guard_path = Path(str(outer.get("guard_receipt", ""))).resolve()
    guard = json.loads(guard_path.read_text(encoding="utf-8")) if guard_path.is_file() else {}
    guard_payload = dict(guard)
    guard_digest = guard_payload.pop("guard_receipt_sha256", None)
    consumption_path = Path(str(guard.get("consumption_receipt", ""))).resolve()
    consumption = (
        json.loads(consumption_path.read_text(encoding="utf-8"))
        if consumption_path.is_file()
        else {}
    )
    consumption_payload = dict(consumption)
    consumption_digest = consumption_payload.pop("consumption_receipt_sha256", None)
    expected_scope = f"Stage0_v1_1_{family}_root_A"
    checks = {
        "outer_seal": _self_hash(outer, "guard_sealed_receipt_sha256"),
        "outer_identity": outer.get("schema_version")
        == "cmf_stage0_smoke_guarded_scope_receipt_v1_1"
        and outer.get("implementation_version") == IMPLEMENTATION_VERSION
        and outer.get("scope") == expected_scope
        and outer.get("family") == family,
        "outer_complete": outer.get("status") == "completed_stage0_smoke_v1_1"
        and outer.get("pipeline_integrity_pass") is True,
        "outer_manifest": outer.get("stage0_manifest_sha256")
        == manifest.get("manifest_sha256"),
        "outer_source": outer.get("authorization", {}).get(
            "implementation_source_sha256"
        )
        == manifest.get("f4_infrastructure_source_sha256"),
        "inner_path": outer.get("result_relative_path") == expected_relative,
        "inner_file": inner_file_sha is not None
        and outer.get("result_receipt_file_sha256") == inner_file_sha,
        "inner_payload": _self_hash(inner, "receipt_sha256")
        and inner.get("receipt_sha256")
        == outer.get("result_receipt_payload_sha256"),
        "inner_identity": inner.get("implementation_version") == IMPLEMENTATION_VERSION
        and inner.get("family") == family
        and inner.get("root_slot_id")
        == manifest.get("root_specs", {}).get(family, {}).get("slot_id"),
        "guard_hash": isinstance(guard_digest, str)
        and hash_json(guard_payload) == guard_digest,
        "guard_complete": guard.get("status") == "completed"
        and guard.get("post_source_lock_pass") is True
        and guard.get("timed_out") is False
        and int(guard.get("orphan_process_count", -1)) == 0
        and guard.get("postcheck_release", {}).get("verified") is True,
        "guard_child": guard.get("child_receipt_file", {}).get("sha256")
        == outer_file_sha,
        "guard_binding": guard.get("binding")
        == outer.get("guard_binding")
        == outer.get("gpu_guard_binding"),
        "consumption_hash": isinstance(consumption_digest, str)
        and hash_json(consumption_payload) == consumption_digest,
        "consumption_binding": consumption_digest
        == outer.get("authorization_consumption_receipt_sha256")
        and consumption.get("authorization_receipt_sha256")
        == outer.get("authorization", {}).get("receipt_sha256"),
        "no_stage1": inner.get("stage1_authorized") is False
        and inner.get("formal_collection_authorized") is False
        and inner.get("training_authorized") is False,
    }
    evidence_root = inner_path.parent.resolve()

    def validate_reference(reference: Any) -> bool:
        if not isinstance(reference, Mapping):
            return False
        relative = reference.get("relative_path")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            return False
        candidate = (evidence_root / relative).resolve()
        if not str(candidate).startswith(str(evidence_root) + "/"):
            return False
        if not candidate.is_file():
            return False
        data = candidate.read_bytes()
        return (
            len(data) == int(reference.get("bytes", -1))
            and hashlib.sha256(data).hexdigest() == reference.get("sha256")
        )

    checks["root_receipt_reference"] = validate_reference(
        inner.get("root_receipt")
    )
    attempt_file_audits = []
    branch_reference_audits = []
    for attempt in inner.get("attempt_receipts", []):
        attempt_id = attempt.get("attempt_id")
        attempt_path = evidence_root / "attempt_receipts" / f"{attempt_id}.json"
        stored_attempt = (
            json.loads(attempt_path.read_text(encoding="utf-8"))
            if isinstance(attempt_id, str) and attempt_path.is_file()
            else None
        )
        attempt_checks = {
            "canonical_path_exists": stored_attempt is not None,
            "payload_exact": stored_attempt == attempt,
            "self_hash": isinstance(stored_attempt, Mapping)
            and _self_hash(stored_attempt, "receipt_sha256"),
        }
        attempt_file_audits.append(
            {
                "attempt_id": attempt_id,
                "checks": attempt_checks,
                "pass": all(attempt_checks.values()),
            }
        )
        branch_ref = attempt.get("branch_receipt")
        branch_pass = branch_ref is None or validate_reference(branch_ref)
        branch_reference_audits.append(
            {"attempt_id": attempt_id, "pass": branch_pass}
        )
    checks["attempt_receipt_files"] = len(attempt_file_audits) == 3 and all(
        item["pass"] for item in attempt_file_audits
    )
    checks["branch_receipt_references"] = len(branch_reference_audits) == 3 and all(
        item["pass"] for item in branch_reference_audits
    )
    raw_audits = []
    video_audits = []
    for attempt in inner.get("attempt_receipts", []):
        required = attempt.get("raw_required_by_branch_status") is True or attempt.get(
            "terminal_status"
        ) in ("PASSED", "FAILED_VERIFIER_WITH_EVIDENCE")
        if not required:
            continue
        ref = attempt.get("branch_receipt")
        branch_path = (
            inner_path.parent / str(ref.get("relative_path"))
            if isinstance(ref, Mapping)
            else None
        )
        branch_ok = bool(
            isinstance(ref, Mapping)
            and branch_path is not None
            and branch_path.is_file()
            and hashlib.sha256(branch_path.read_bytes()).hexdigest() == ref.get("sha256")
        )
        try:
            raw = verify_raw_artifact_integrity(branch_path.parent / "raw") if branch_ok else {"pass": False}
        except BaseException as exc:
            raw = {"pass": False, "error": str(exc)}
        raw_manifest = raw.get("manifest", {})
        realization = raw_manifest.get("provenance", {}).get("realization_spec", {})
        item_checks = {
            "branch": branch_ok,
            "raw": raw.get("pass") is True,
            "family_program": raw_manifest.get("provenance", {}).get("family") == family
            and raw_manifest.get("provenance", {}).get("program_id")
            == attempt.get("program_id"),
            "implementation": raw_manifest.get("provenance", {}).get(
                "implementation_version"
            )
            == IMPLEMENTATION_VERSION,
            "attempt_root_manifest": realization.get("stage0_attempt_id")
            == attempt.get("attempt_id")
            and realization.get("stage0_root_slot_id") == attempt.get("root_slot_id")
            and realization.get("stage0_manifest_sha256") == manifest.get("manifest_sha256"),
            "r_pc": realization.get("realization") == "r_pc",
            "stage0_not_formal": raw_manifest.get("stage0_data") is True
            and raw_manifest.get("formal_data") is False,
        }
        raw_audits.append(
            {"attempt_id": attempt.get("attempt_id"), "checks": item_checks, "pass": all(item_checks.values())}
        )
    for attempt in inner.get("attempt_receipts", []):
        required = attempt.get("trajectory_generated") is True
        if not required:
            item_checks = {
                "not_required_without_trajectory": attempt.get("video_required")
                is False
                and attempt.get("video_status")
                == "video_not_applicable_no_trajectory"
            }
            video_audits.append(
                {
                    "attempt_id": attempt.get("attempt_id"),
                    "required": False,
                    "checks": item_checks,
                    "pass": all(item_checks.values()),
                }
            )
            continue
        ref = attempt.get("branch_receipt")
        branch_path = (
            inner_path.parent / str(ref.get("relative_path"))
            if isinstance(ref, Mapping)
            else None
        )
        branch = (
            json.loads(branch_path.read_text(encoding="utf-8"))
            if branch_path is not None and branch_path.is_file()
            else {}
        )
        expected_video = (
            branch_path.parent / "video" / "trajectory.mp4"
            if branch_path is not None
            else inner_path.parent / "missing_video.mp4"
        )
        try:
            video = validate_stage0_trajectory_mp4_receipt_v1(
                branch.get("stage0_video_receipt"),
                expected_path=expected_video,
            )
        except BaseException as exc:
            video = {"pass": False, "error": str(exc), "receipt": {}}
        item_checks = {
            "attempt_requires_video": attempt.get("video_required") is True,
            "attempt_video_integrity": attempt.get("video_integrity", {}).get(
                "pass"
            )
            is True,
            "attempt_video_status": attempt.get("video_status") == "generated",
            "live_mp4": video.get("pass") is True,
            "attempt_file_hash": attempt.get("video_integrity", {}).get(
                "file_sha256"
            )
            == video.get("receipt", {}).get("file_sha256"),
        }
        video_audits.append(
            {
                "attempt_id": attempt.get("attempt_id"),
                "required": True,
                "checks": item_checks,
                "pass": all(item_checks.values()),
            }
        )
    expected_raw = sum(
        item.get("raw_required_by_branch_status") is True
        or item.get("terminal_status") in ("PASSED", "FAILED_VERIFIER_WITH_EVIDENCE")
        for item in inner.get("attempt_receipts", [])
    )
    checks["all_required_raw"] = len(raw_audits) == expected_raw and all(
        item["pass"] for item in raw_audits
    )
    checks["all_generated_trajectories_have_mp4"] = len(video_audits) == 3 and all(
        item["pass"] for item in video_audits
    )
    audit = {
        "family": family,
        "outer_path": str(path),
        "inner_path": str(inner_path),
        "checks": checks,
        "raw_audits": raw_audits,
        "video_audits": video_audits,
        "attempt_file_audits": attempt_file_audits,
        "branch_reference_audits": branch_reference_audits,
        "pass": all(checks.values()),
    }
    return inner, audit


def _finalize_stage0_smoke_payloads_v1_1(
    manifest: Mapping[str, Any],
    family_receipts: Mapping[str, Mapping[str, Any]],
    outer_audits: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if set(family_receipts) != set(FAMILIES) or set(outer_audits) != set(FAMILIES):
        raise ValueError("Stage 0 v1.1 finalizer requires exact F1-F4 inputs")
    manifest_gate = validate_stage0_smoke_manifest_structure(manifest)
    attempts = [
        dict(item)
        for family in FAMILIES
        for item in family_receipts[family].get("attempt_receipts", [])
    ]
    planned = {item["attempt_id"]: item for item in manifest.get("attempts", [])}
    attempt_audits = []
    for item in attempts:
        expected = planned.get(item.get("attempt_id"), {})
        checks = {
            "self_hash": _self_hash(item, "receipt_sha256"),
            "manifest_mapping": bool(expected)
            and all(
                item.get(key) == expected.get(key)
                for key in (
                    "attempt_id",
                    "family",
                    "root_slot_id",
                    "program_id",
                    "realization",
                    "mp4_required_if_trajectory_generated",
                )
            ),
            "terminal": item.get("terminal_status") in TERMINAL_OUTCOMES,
            "stage0_not_formal": item.get("stage0_data") is True
            and item.get("formal_data") is False
            and item.get("stage1_authorized") is False,
        }
        attempt_audits.append(
            {"attempt_id": item.get("attempt_id"), "checks": checks, "pass": all(checks.values())}
        )
    family_outcomes = {}
    family_audits = {}
    for family in FAMILIES:
        receipt = family_receipts[family]
        bucket = list(receipt.get("attempt_receipts", []))
        derived = "PASS" if len(bucket) == 3 and all(
            item.get("terminal_status") == "PASSED" for item in bucket
        ) else "FAILED_WITH_EVIDENCE"
        family_outcomes[family] = derived
        checks = {
            "self_hash": _self_hash(receipt, "receipt_sha256"),
            "family": receipt.get("family") == family,
            "exact_bucket": len(bucket) == 3
            and all(item.get("family") == family for item in bucket),
            "outcome": receipt.get("outcome") == derived,
            "pipeline": receipt.get("pipeline_integrity_pass") is True,
            "videos": receipt.get("all_required_videos_complete") is True
            and int(receipt.get("generated_video_count", -1))
            == int(receipt.get("generated_trajectory_count", -2)),
            "cleanup": receipt.get("cleanup_pass") is True
            and int(receipt.get("orphan_process_count", -1)) == 0,
            "outer": outer_audits[family].get("pass") is True,
        }
        if family == "F4":
            binding = validate_f4_frozen_canonical_neutral_binding_v13(
                receipt.get("f4_canonical_neutral_binding_v13")
            )
            checks["v13_binding"] = binding["binding_sha256"] == manifest.get(
                "f4_canonical_neutral_binding_sha256_v13"
            )
        family_audits[family] = {"checks": checks, "pass": all(checks.values())}
    checks = {
        "manifest": manifest_gate["pass"],
        "twelve_attempts": len(attempts) == 12
        and len({item.get("attempt_id") for item in attempts}) == 12
        and {item.get("attempt_id") for item in attempts} == set(planned),
        "attempts": len(attempt_audits) == 12 and all(item["pass"] for item in attempt_audits),
        "families": all(item["pass"] for item in family_audits.values()),
        "outers": all(outer_audits[family].get("pass") is True for family in FAMILIES),
    }
    completed = all(checks.values())
    result = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "stage0_manifest_sha256": manifest.get("manifest_sha256"),
        "stage0_completed": completed,
        "stage0_outcome": "PASS"
        if completed and all(value == "PASS" for value in family_outcomes.values())
        else "FAILED_WITH_EVIDENCE",
        "family_outcomes": family_outcomes,
        "family_audits": family_audits,
        "outer_receipt_audits": {family: dict(outer_audits[family]) for family in FAMILIES},
        "attempt_audits": attempt_audits,
        "attempt_receipts": attempts,
        "planned_attempt_count": 12,
        "terminal_attempt_count": len(attempts),
        "successful_attempt_count": sum(item.get("terminal_status") == "PASSED" for item in attempts),
        "failed_attempt_count": sum(item.get("terminal_status") != "PASSED" for item in attempts),
        "generated_trajectory_count": sum(item.get("trajectory_generated") is True for item in attempts),
        "generated_video_count": sum(
            item.get("video_required") is True
            and item.get("video_integrity", {}).get("pass") is True
            for item in attempts
        ),
        "stage0_generated_trajectory_mp4_required": True,
        "stage0_video_contract": dict(manifest.get("stage0_video_contract", {})),
        "checks": checks,
        "accepted_formal_root_count": 0,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
        "authoritative": False,
    }
    result["receipt_sha256"] = hash_json(result)
    return result


def finalize_stage0_smoke_v1_1(
    stage0_manifest_path: Path = CANONICAL_STAGE0_MANIFEST,
) -> dict[str, Any]:
    path = Path(stage0_manifest_path).resolve()
    if path != CANONICAL_STAGE0_MANIFEST.resolve() or not path.is_file():
        raise ValueError("canonical Stage 0 v1.1 manifest is missing or noncanonical")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected_manifest = build_stage0_smoke_manifest_v1_1()
    if manifest != expected_manifest:
        raise ValueError(
            "canonical Stage 0 v1.1 manifest differs from deterministic v13 evidence reconstruction"
        )
    source_start = implementation_source_sha256_stage0_v1_1()
    if source_start != manifest.get("f4_infrastructure_source_sha256"):
        raise ValueError("active source differs from v13 infrastructure source")
    receipts = {}
    audits = {}
    for family in FAMILIES:
        receipts[family], audits[family] = validate_stage0_family_outer_receipt_v1_1(
            manifest, family, canonical_outer_receipt_path_v1_1(family)
        )
    result = _finalize_stage0_smoke_payloads_v1_1(manifest, receipts, audits)
    source_end = implementation_source_sha256_stage0_v1_1()
    if source_end != source_start:
        raise ValueError("active source changed during Stage 0 v1.1 finalization")
    result.pop("receipt_sha256", None)
    result["authoritative"] = True
    result["canonical_manifest_path"] = str(path)
    result["implementation_source_sha256"] = source_end
    result["receipt_sha256"] = hash_json(result)
    return result


__all__ = [
    "CANONICAL_OUTPUT",
    "FAMILIES",
    "_finalize_stage0_smoke_payloads_v1_1",
    "canonical_outer_receipt_path_v1_1",
    "finalize_stage0_smoke_v1_1",
    "validate_stage0_family_outer_receipt_v1_1",
]
