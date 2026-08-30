"""Finalize a frozen manifest and four receipts into one Stage 0 outcome."""

from __future__ import annotations

from typing import Any, Mapping
from pathlib import Path
import json
import hashlib

from .current_hasher import hash_json
from .raw_writer import validate_raw_artifact_contract
from .probes.stage0_smoke_authorization_v1 import (
    implementation_source_sha256_stage0,
)
from .stage0_smoke_manifest_v1 import (
    CANONICAL_INFRA_RECEIPT,
    build_stage0_smoke_manifest,
    validate_stage0_smoke_manifest_structure,
)


FAMILIES = ("F1", "F2", "F3", "F4")
DATASET_ROOT = Path(
    "/nfs_share/lijunhui/Robotwin2/datasets/controlled_multi_future_stage0_smoke_v1"
)
CANONICAL_STAGE0_MANIFEST = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/"
    "STAGE0_SMOKE_MANIFEST_V1_20260830.json"
)


def _self_hash(value: Mapping[str, Any], field: str) -> bool:
    payload = dict(value)
    digest = payload.pop(field, None)
    return isinstance(digest, str) and hash_json(payload) == digest


def _audit_declared_file_evidence(
    value: Any, *, base_dir: Path, allowed_root: Path, label: str
) -> list[dict[str, Any]]:
    audits = []
    if isinstance(value, Mapping):
        path_value = value.get("path")
        if not isinstance(path_value, str):
            path_value = value.get("relative_path")
        digest = value.get("sha256")
        if isinstance(path_value, str) and isinstance(digest, str):
            path = Path(path_value)
            if not path.is_absolute():
                path = base_dir / path
            path = path.resolve()
            within_workspace = str(path).startswith("/nfs_share/lijunhui/")
            within_namespace = path == allowed_root or allowed_root in path.parents
            passed = bool(
                within_workspace
                and within_namespace
                and path.is_file()
                and hashlib.sha256(path.read_bytes()).hexdigest() == digest
            )
            audits.append(
                {
                    "label": label,
                    "path": str(path),
                    "within_workspace": within_workspace,
                    "within_namespace": within_namespace,
                    "pass": passed,
                }
            )
        for key, item in value.items():
            audits.extend(
                _audit_declared_file_evidence(
                    item,
                    base_dir=base_dir,
                    allowed_root=allowed_root,
                    label=f"{label}.{key}",
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            audits.extend(
                _audit_declared_file_evidence(
                    item,
                    base_dir=base_dir,
                    allowed_root=allowed_root,
                    label=f"{label}[{index}]",
                )
            )
    return audits


def canonical_outer_receipt_path(family: str) -> Path:
    if family not in FAMILIES:
        raise ValueError("unsupported Stage 0 family")
    return (
        DATASET_ROOT
        / f"stage0_smoke_v1_{family}_root_A_seed20260829_run1"
        / "receipt.json"
    )


def validate_stage0_family_outer_receipt(
    stage0_manifest: Mapping[str, Any], family: str, outer_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    outer_path = Path(outer_path).resolve()
    if outer_path != canonical_outer_receipt_path(family).resolve():
        raise ValueError(f"{family} outer receipt path is not canonical")
    if not outer_path.is_file():
        raise ValueError(f"{family} outer receipt is missing")
    outer_file_sha = hashlib.sha256(outer_path.read_bytes()).hexdigest()
    outer = json.loads(outer_path.read_text(encoding="utf-8"))
    outer_payload = dict(outer)
    outer_digest = outer_payload.pop("guard_sealed_receipt_sha256", None)
    guard_path = Path(str(outer.get("guard_receipt", ""))).resolve()
    guard = json.loads(guard_path.read_text()) if guard_path.is_file() else {}
    guard_payload = dict(guard)
    guard_digest = guard_payload.pop("guard_receipt_sha256", None)
    consumption_path = Path(str(guard.get("consumption_receipt", ""))).resolve()
    consumption = (
        json.loads(consumption_path.read_text())
        if consumption_path.is_file()
        else {}
    )
    consumption_payload = dict(consumption)
    consumption_digest = consumption_payload.pop(
        "consumption_receipt_sha256", None
    )
    expected_scope = f"Stage0_{family}_root_A"
    expected_manifest_sha = stage0_manifest.get("manifest_sha256")
    expected_source_sha = stage0_manifest.get("f4_infrastructure_source_sha256")
    result_relative = outer.get("result_relative_path")
    expected_relative = "stage0_family/stage0_family_receipt.json"
    inner_path = outer_path.parent / expected_relative
    inner_file_sha = (
        hashlib.sha256(inner_path.read_bytes()).hexdigest()
        if inner_path.is_file()
        else None
    )
    inner = json.loads(inner_path.read_text()) if inner_path.is_file() else {}
    root_ref = inner.get("root_receipt")
    root_receipt_path = (
        inner_path.parent / str(root_ref.get("relative_path"))
        if isinstance(root_ref, Mapping)
        else None
    )
    root_receipt_bound = bool(
        isinstance(root_ref, Mapping)
        and root_receipt_path is not None
        and root_receipt_path.is_file()
        and hashlib.sha256(root_receipt_path.read_bytes()).hexdigest()
        == root_ref.get("sha256")
    )
    root_receipt = (
        json.loads(root_receipt_path.read_text())
        if root_receipt_bound and root_receipt_path is not None
        else {}
    )
    declared_failure_file_audits = _audit_declared_file_evidence(
        root_receipt,
        base_dir=root_receipt_path.parent
        if root_receipt_path is not None
        else inner_path.parent,
        allowed_root=outer_path.parent,
        label="root_receipt",
    )
    checks = {
        "outer_guard_seal": isinstance(outer_digest, str)
        and hash_json(outer_payload) == outer_digest,
        "outer_schema": outer.get("schema_version")
        == "cmf_stage0_smoke_guarded_scope_receipt_v1",
        "outer_identity": outer.get("implementation_version")
        == "controlled_multi_future_stage0_smoke_v1"
        and outer.get("scope") == expected_scope
        and outer.get("family") == family,
        "outer_stage0_flags": outer.get("stage0_data") is True
        and outer.get("stage0_authorized") is True
        and outer.get("formal_data") is False,
        "outer_pipeline_complete": outer.get("status")
        == "completed_stage0_smoke"
        and outer.get("pipeline_integrity_pass") is True,
        "outer_manifest_binding": outer.get("stage0_manifest_sha256")
        == expected_manifest_sha,
        "outer_source_binding": outer.get("authorization", {}).get(
            "implementation_source_sha256"
        )
        == expected_source_sha,
        "result_path_exact": result_relative == expected_relative,
        "result_file_hash_bound": inner_file_sha is not None
        and outer.get("result_receipt_file_sha256") == inner_file_sha,
        "result_payload_hash_bound": inner.get("receipt_sha256")
        == outer.get("result_receipt_payload_sha256"),
        "guard_exists_and_self_hashed": guard_path.is_file()
        and isinstance(guard_digest, str)
        and hash_json(guard_payload) == guard_digest,
        "guard_terminal_clean": guard.get("status") == "completed"
        and guard.get("post_source_lock_pass") is True
        and guard.get("timed_out") is False
        and int(guard.get("orphan_process_count", -1)) == 0,
        "guard_child_hash": guard.get("child_receipt_file", {}).get("sha256")
        == outer_file_sha,
        "guard_binding": guard.get("binding")
        == outer.get("guard_binding")
        == outer.get("gpu_guard_binding"),
        "authorization_binding": outer.get("authorization", {}).get(
            "receipt_sha256"
        )
        == guard.get("binding", {}).get("authorization_receipt_sha256"),
        "consumption_exists_and_self_hashed": consumption_path.is_file()
        and isinstance(consumption_digest, str)
        and hash_json(consumption_payload) == consumption_digest,
        "consumption_binding": consumption_digest
        == outer.get("authorization_consumption_receipt_sha256")
        and consumption.get("authorization_receipt_sha256")
        == outer.get("authorization", {}).get("receipt_sha256"),
        "inner_self_hash": _self_hash(inner, "receipt_sha256"),
        "inner_identity": inner.get("family") == family
        and inner.get("root_slot_id")
        == stage0_manifest.get("root_specs", {}).get(family, {}).get("slot_id"),
        "root_receipt_file_bound": root_receipt_bound,
    }
    raw_audits = []
    failed_evidence_audits = []
    inner_dir = inner_path.parent
    for attempt in inner.get("attempt_receipts", []):
        branch_ref = attempt.get("branch_receipt")
        branch_path = (
            inner_dir / str(branch_ref.get("relative_path"))
            if isinstance(branch_ref, Mapping)
            else None
        )
        branch_bound = bool(
            isinstance(branch_ref, Mapping)
            and branch_path is not None
            and branch_path.is_file()
            and hashlib.sha256(branch_path.read_bytes()).hexdigest()
            == branch_ref.get("sha256")
        )
        if attempt.get("terminal_status") == "FAILED_WITH_EVIDENCE":
            branch_receipt = (
                json.loads(branch_path.read_text()) if branch_bound else {}
            )
            if branch_bound and branch_path is not None:
                declared_failure_file_audits.extend(
                    _audit_declared_file_evidence(
                        branch_receipt,
                        base_dir=branch_path.parent,
                        allowed_root=outer_path.parent,
                        label=f"branch:{attempt.get('attempt_id')}",
                    )
                )
            evidence_checks = {
                "root_receipt_bound": root_receipt_bound,
                "branch_receipt_bound_if_declared": not isinstance(
                    branch_ref, Mapping
                )
                or branch_bound,
                "failure_type_present": isinstance(
                    attempt.get("failure_type"), str
                ),
                "failure_message_present": isinstance(
                    attempt.get("failure_message"), str
                ),
            }
            failed_evidence_audits.append(
                {
                    "attempt_id": attempt.get("attempt_id"),
                    "checks": evidence_checks,
                    "pass": all(evidence_checks.values()),
                }
            )
        raw_required = attempt.get("branch_status") in (
            "accepted",
            "failed_verifier",
        ) or attempt.get("raw_required_by_branch_status") is True
        if not raw_required:
            continue
        if attempt.get("trajectory_generated") is not True:
            raw_audits.append(
                {
                    "attempt_id": attempt.get("attempt_id"),
                    "pass": False,
                    "reason": "branch_status_requires_raw_but_attempt_marks_none",
                }
            )
            continue
        if not isinstance(branch_ref, Mapping):
            raw_audits.append({"attempt_id": attempt.get("attempt_id"), "pass": False, "reason": "branch_ref_missing"})
            continue
        branch_ok = branch_bound
        raw_dir = branch_path.parent / "raw"
        try:
            raw = validate_raw_artifact_contract(raw_dir)
        except BaseException as exc:
            raw = {"pass": False, "error": str(exc)}
        raw_manifest = raw.get("manifest", {})
        live_checks = {
            "branch_receipt_file": branch_ok,
            "raw_integrity": raw.get("pass") is True,
            "raw_stage0_not_formal": raw_manifest.get("stage0_data") is True
            and raw_manifest.get("stage0_authorized") is True
            and raw_manifest.get("formal_data") is False,
            "raw_family_program": raw_manifest.get("provenance", {}).get("family")
            == family
            and raw_manifest.get("provenance", {}).get("program_id")
            == attempt.get("program_id"),
            "raw_realization_r_pc": raw_manifest.get("provenance", {}).get(
                "realization_spec", {}
            ).get("realization")
            == "r_pc",
            "raw_attempt_root_manifest_bound": raw_manifest.get(
                "provenance", {}
            ).get("realization_spec", {}).get("stage0_attempt_id")
            == attempt.get("attempt_id")
            and raw_manifest.get("provenance", {}).get(
                "realization_spec", {}
            ).get("stage0_root_slot_id")
            == attempt.get("root_slot_id")
            and raw_manifest.get("provenance", {}).get(
                "realization_spec", {}
            ).get("stage0_manifest_sha256")
            == stage0_manifest.get("manifest_sha256"),
            "raw_provenance_stage0_not_formal": raw_manifest.get(
                "provenance", {}
            ).get("stage0_data")
            is True
            and raw_manifest.get("provenance", {}).get("stage0_authorized")
            is True
            and raw_manifest.get("provenance", {}).get("formal_data")
            is False,
            "raw_hash_matches_attempt": raw_manifest.get(
                "raw_streams_npz_sha256"
            )
            == attempt.get("raw_integrity", {}).get("raw_streams_npz_sha256"),
            "raw_manifest_payload_matches_attempt": raw_manifest.get(
                "manifest_payload_sha256"
            )
            == attempt.get("raw_integrity", {}).get(
                "manifest_payload_sha256"
            ),
        }
        raw_audits.append(
            {"attempt_id": attempt.get("attempt_id"), "checks": live_checks, "pass": all(live_checks.values())}
        )
    expected_raw_count = sum(
        item.get("branch_status") in ("accepted", "failed_verifier")
        or item.get("raw_required_by_branch_status") is True
        for item in inner.get("attempt_receipts", [])
    )
    checks["all_required_raw_reverified"] = len(raw_audits) == expected_raw_count and all(
        item["pass"] for item in raw_audits
    )
    checks["all_failed_attempt_evidence_bound"] = len(
        failed_evidence_audits
    ) == int(inner.get("failed_attempt_count", 0)) and all(
        item["pass"] for item in failed_evidence_audits
    )
    checks["all_declared_failure_files_present_and_hashed"] = all(
        item["pass"] for item in declared_failure_file_audits
    )
    audit = {
        "family": family,
        "outer_path": str(outer_path),
        "outer_file_sha256": outer_file_sha,
        "inner_path": str(inner_path),
        "inner_file_sha256": inner_file_sha,
        "checks": checks,
        "raw_audits": raw_audits,
        "failed_evidence_audits": failed_evidence_audits,
        "declared_failure_file_audits": declared_failure_file_audits,
        "pass": all(checks.values()),
    }
    return inner, audit


def _finalize_stage0_smoke_payloads(
    stage0_manifest: Mapping[str, Any],
    family_receipts: Mapping[str, Mapping[str, Any]],
    outer_receipt_audits: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if set(family_receipts) != set(FAMILIES):
        raise ValueError("Stage 0 finalizer requires exactly F1-F4 receipts")
    if set(outer_receipt_audits) != set(FAMILIES):
        raise ValueError("Stage 0 finalizer requires four outer receipt audits")
    manifest = dict(stage0_manifest)
    normalized = {family: dict(family_receipts[family]) for family in FAMILIES}
    manifest_attempts = {
        item["attempt_id"]: dict(item) for item in manifest.get("attempts", [])
    }
    attempts = [
        dict(attempt)
        for family in FAMILIES
        for attempt in normalized[family].get("attempt_receipts", [])
    ]
    attempt_ids = [item.get("attempt_id") for item in attempts]
    attempt_audits = []
    for attempt in attempts:
        planned = manifest_attempts.get(attempt.get("attempt_id"), {})
        checks = {
            "receipt_self_hash": _self_hash(attempt, "receipt_sha256"),
            "attempt_in_manifest": bool(planned),
            "family_matches_manifest": attempt.get("family")
            == planned.get("family"),
            "root_matches_manifest": attempt.get("root_slot_id")
            == planned.get("root_slot_id"),
            "program_matches_manifest": attempt.get("program_id")
            == planned.get("program_id"),
            "realization_r_pc_matches_manifest": attempt.get("realization")
            == planned.get("realization")
            == "r_pc",
            "terminal_status_valid": attempt.get("terminal_status")
            in ("PASS", "FAILED_WITH_EVIDENCE"),
            "stage0_not_formal": attempt.get("stage0_data") is True
            and attempt.get("stage0_authorized") is True
            and attempt.get("formal_data") is False,
            "pass_has_real_verified_trajectory": (
                attempt.get("terminal_status") != "PASS"
                or (
                    attempt.get("trajectory_generated") is True
                    and attempt.get("verifier_pass") is True
                    and attempt.get("raw_integrity", {}).get("pass") is True
                )
            ),
        }
        attempt_audits.append(
            {
                "attempt_id": attempt.get("attempt_id"),
                "checks": checks,
                "pass": all(checks.values()),
            }
        )
    derived_family_outcomes = {}
    family_audits = {}
    for family in FAMILIES:
        receipt = normalized[family]
        family_attempts = [
            item for item in attempts if item.get("family") == family
        ]
        derived = (
            "PASS"
            if len(family_attempts) == 3
            and all(item.get("terminal_status") == "PASS" for item in family_attempts)
            else "FAILED_WITH_EVIDENCE"
        )
        derived_family_outcomes[family] = derived
        checks = {
            "receipt_self_hash": _self_hash(receipt, "receipt_sha256"),
            "family_exact": receipt.get("family") == family,
            "root_slot_matches_manifest": receipt.get("root_slot_id")
            == manifest.get("root_specs", {}).get(family, {}).get("slot_id"),
            "exact_three_attempts": len(family_attempts) == 3,
            "bucket_attempts_belong_to_family": all(
                item.get("family") == family
                for item in receipt.get("attempt_receipts", [])
            ),
            "declared_outcome_matches_attempts": receipt.get("outcome")
            == derived,
            "pipeline_integrity_pass": receipt.get("pipeline_integrity_pass")
            is True,
            "cleanup_pass": receipt.get("cleanup_pass") is True
            and int(receipt.get("orphan_process_count", -1)) == 0,
            "outer_guarded_receipt_audit_pass": outer_receipt_audits[
                family
            ].get("pass")
            is True,
        }
        family_audits[family] = {"checks": checks, "pass": all(checks.values())}
    manifest_payload = dict(manifest)
    manifest_digest = manifest_payload.pop("manifest_sha256", None)
    checks = {
        "manifest_self_hash": isinstance(manifest_digest, str)
        and hash_json(manifest_payload) == manifest_digest,
        "manifest_implementation": manifest.get("implementation_version")
        == "controlled_multi_future_stage0_smoke_v1",
        "manifest_exact_four_roots": set(manifest.get("root_specs", {}))
        == set(FAMILIES),
        "manifest_exact_twelve_attempts": len(manifest_attempts) == 12,
        "exact_four_family_receipts": len(normalized) == 4,
        "exact_twelve_attempt_receipts": len(attempts) == 12,
        "attempt_ids_exactly_match_manifest": set(attempt_ids)
        == set(manifest_attempts)
        and len(attempt_ids) == len(set(attempt_ids)) == 12,
        "all_attempt_audits_pass": len(attempt_audits) == 12
        and all(item["pass"] for item in attempt_audits),
        "all_family_audits_pass": all(
            item["pass"] for item in family_audits.values()
        ),
        "all_outer_receipt_audits_pass": all(
            outer_receipt_audits[family].get("pass") is True
            for family in FAMILIES
        ),
    }
    pipeline_complete = all(checks.values())
    overall_outcome = (
        "PASS"
        if pipeline_complete
        and all(value == "PASS" for value in derived_family_outcomes.values())
        else "FAILED_WITH_EVIDENCE"
    )
    result = {
        "schema_version": "cmf_stage0_smoke_finalizer_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        "stage0_manifest_sha256": manifest_digest,
        "stage0_completed": pipeline_complete,
        "stage0_outcome": overall_outcome,
        "family_outcomes": derived_family_outcomes,
        "family_audits": family_audits,
        "outer_receipt_audits": {
            family: dict(outer_receipt_audits[family]) for family in FAMILIES
        },
        "attempt_audits": attempt_audits,
        "planned_attempt_count": 12,
        "terminal_attempt_count": len(attempts),
        "successful_attempt_count": sum(
            item.get("terminal_status") == "PASS" for item in attempts
        ),
        "failed_attempt_count": sum(
            item.get("terminal_status") == "FAILED_WITH_EVIDENCE"
            for item in attempts
        ),
        "generated_trajectory_count": sum(
            item.get("trajectory_generated") is True for item in attempts
        ),
        "attempt_receipts": attempts,
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


def finalize_stage0_smoke_v1(
    stage0_manifest_path: Path = CANONICAL_STAGE0_MANIFEST,
) -> dict[str, Any]:
    manifest_path = Path(stage0_manifest_path).resolve()
    if manifest_path != CANONICAL_STAGE0_MANIFEST.resolve():
        raise ValueError("Stage 0 finalizer manifest path is not canonical")
    if not manifest_path.is_file():
        raise ValueError("canonical Stage 0 manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    structure = validate_stage0_smoke_manifest_structure(manifest)
    if structure["pass"] is not True:
        raise ValueError(
            f"canonical Stage 0 manifest structure failed: {structure['checks']}"
        )
    expected_manifest = build_stage0_smoke_manifest(CANONICAL_INFRA_RECEIPT)
    if manifest != expected_manifest:
        raise ValueError(
            "canonical Stage 0 manifest differs from deterministic reconstruction"
        )
    expected_source_sha = manifest.get("f4_infrastructure_source_sha256")
    source_sha_at_start = implementation_source_sha256_stage0()
    if source_sha_at_start != expected_source_sha:
        raise ValueError(
            "active source changed between F4 infrastructure and Stage 0 finalization"
        )
    family_receipts = {}
    outer_audits = {}
    for family in FAMILIES:
        inner, audit = validate_stage0_family_outer_receipt(
            manifest, family, canonical_outer_receipt_path(family)
        )
        family_receipts[family] = inner
        outer_audits[family] = audit
    result = _finalize_stage0_smoke_payloads(
        manifest, family_receipts, outer_audits
    )
    source_sha_at_end = implementation_source_sha256_stage0()
    if source_sha_at_end != source_sha_at_start:
        raise ValueError("active source changed during Stage 0 finalization")
    result.pop("receipt_sha256", None)
    result["authoritative"] = True
    result["canonical_manifest_path"] = str(manifest_path)
    result["implementation_source_sha256"] = source_sha_at_end
    result["receipt_sha256"] = hash_json(result)
    return result


__all__ = [
    "canonical_outer_receipt_path",
    "finalize_stage0_smoke_v1",
    "validate_stage0_family_outer_receipt",
]
