#!/usr/bin/env python3
"""Exact-binding read-only auditor for the F2 admission reissue successor.

V1.1 reuses the hash-frozen V1 scientific/Guard audit implementation and adds
an independently checked path-only successor lineage.  It writes only JSON to
stdout and never invokes a GPU, simulator, planner, or run process.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping


WORKSPACE = Path("/nfs_share/lijunhui")
AUDIT_ROOT = WORKSPACE / "Vault-on-Fvl09/数据构造/实现审计"
BASE_AUDITOR_PATH = (
    AUDIT_ROOT
    / "f2_controlled_insertion_route_gate_postrun_auditor_v1/auditor.py"
)
BASE_AUDITOR_SHA256 = (
    "a76aee0674ff641da41f5951d221d28547dc92db87e7a5c0f41558ced047251d"
)
EXPECTED_MANIFEST_PATH = (
    AUDIT_ROOT
    / "F2_CONTROLLED_INSERTION_ROUTE_GATE_ADMISSION_REISSUE_RUN2_MANIFEST_V1.json"
)
EXPECTED_MANIFEST_FILE_SHA256 = (
    "210dd17071c1f5b89aee6fb8f7451cb14949a2948c663cbc2e86c2824725ccd0"
)
EXPECTED_MANIFEST_SHA256 = (
    "42d4d48a41ab8fcab1515679450f20c2852dfc94a531022009a5b7fce56ff396"
)
EXPECTED_RUN_ID = (
    "f2-controlled-insertion-route-gate-admission-reissue-run2-20260904"
)
EXPECTED_JOB_ID = "f2-controlled-insertion-route-gate-run1"
EXPECTED_GUARD_DIRECTORY = AUDIT_ROOT / (
    "f2_controlled_insertion_route_gate_admission_reissue_run2/"
    "f2-controlled-insertion-route-gate-admission-reissue-run2-20260904/guards"
)
EXPECTED_CACHE_DIRECTORY = (
    WORKSPACE
    / "Robotwin2/cache/f2_controlled_insertion_route_gate_admission_reissue_run2"
)
EXPECTED_OUTPUT_NAMESPACE = WORKSPACE / (
    "Robotwin2/datasets/controlled_multi_future_f2_controlled_insertion_route_gate_v1/"
    "f2-controlled-insertion-route-gate-run1-admission-reissue-run2"
)
PARENT_MANIFEST_PATH = (
    AUDIT_ROOT / "F2_CONTROLLED_INSERTION_ROUTE_GATE_APPROVED_RUN1_MANIFEST_V1.json"
)
PARENT_MANIFEST_FILE_SHA256 = (
    "3cfe58ea26168d7c1ded0ddfa2d8d72c91223501a18a2463d2caad00eb5a5910"
)
PARENT_MANIFEST_SHA256 = (
    "b08933bf17707bfa8b8700f6b384eecf72b9d5e7b5aac7bc38bcb26f875210d8"
)
RECOVERY_PATH = (
    AUDIT_ROOT
    / "F2_CONTROLLED_INSERTION_ROUTE_GATE_RUN1_ATOMIC_IDLE_REJECTION_RECOVERY_V1.json"
)
RECOVERY_FILE_SHA256 = (
    "0e4baca15482429c285de9edaf34402967b8f876943a20d86faa6020c1858229"
)
RECOVERY_RECEIPT_SHA256 = (
    "5c44f850e6e2957db932d151e52bc2977b33da9e6503a395a9f54cd3ae16e41a"
)
PRIOR_GUARD_TERMINAL_PATH = AUDIT_ROOT / (
    "f2_controlled_insertion_route_gate_run1/"
    "f2-controlled-insertion-route-gate-run1-20260904/guards/"
    "f2-controlled-insertion-route-gate-run1.terminal.json"
)
PRIOR_GUARD_TERMINAL_FILE_SHA256 = (
    "8dc65036ff7c89e59e060a2ab9fe9c6daae228444c1d146374fd7474df19b30a"
)
PRIOR_GUARD_TERMINAL_RECEIPT_SHA256 = (
    "00e3db8cf39bd9532e00d7d6d8ea91ef1bd731994fcbc9a9dc2abcdc3d46e07e"
)
LATEST_REVIEW_PATH = (
    AUDIT_ROOT / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_20260904.md"
)
LATEST_REVIEW_FILE_SHA256 = (
    "790fc6e3e48694d212bb1c1a8833d270f2dc0dbe4748a605f319003787fd0dcd"
)
LATEST_REVIEW_RECEIPT_PATH = (
    AUDIT_ROOT
    / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_RECEIPT_20260904.json"
)
LATEST_REVIEW_RECEIPT_FILE_SHA256 = (
    "bcd64b8e013893707565b63a312ce396b1acdad3d502f0c9fdaf37fbd951401a"
)
LATEST_REVIEW_RECEIPT_SHA256 = (
    "c8ff692590d7cdb63995c9ce6932d851c1ef918fb5a8e8003881d2035eca7c35"
)
SUCCESSOR_ISSUE_VAULT_HEAD = "8883c69669d8f433e7bb23361d71fd058c5d8c95"


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_base():
    if file_sha(BASE_AUDITOR_PATH) != BASE_AUDITOR_SHA256:
        raise RuntimeError("hash-frozen F2 post-run auditor V1 changed")
    spec = importlib.util.spec_from_file_location(
        "cmf_f2_postrun_auditor_v1_frozen", BASE_AUDITOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load hash-frozen F2 post-run auditor V1")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.EXPECTED_MANIFEST_PATH = EXPECTED_MANIFEST_PATH
    module.EXPECTED_MANIFEST_FILE_SHA256 = EXPECTED_MANIFEST_FILE_SHA256
    module.EXPECTED_MANIFEST_SHA256 = EXPECTED_MANIFEST_SHA256
    module.EXPECTED_RUN_ID = EXPECTED_RUN_ID
    return module


base = load_base()

# Re-export the immutable scientific constants/functions used by the V1 tests.
canonical_hash = base.canonical_hash
AuditFailure = base.AuditFailure
GPU_UUIDS = base.GPU_UUIDS
INSIDE_SEGMENTS = base.INSIDE_SEGMENTS
BESIDE_SEGMENTS = base.BESIDE_SEGMENTS
EXPECTED_BINDING_SHA256 = base.EXPECTED_BINDING_SHA256
EXPECTED_PREFIX_QPOS_SHA256 = base.EXPECTED_PREFIX_QPOS_SHA256
EXPECTED_INSIDE_TARGETS_SHA256 = base.EXPECTED_INSIDE_TARGETS_SHA256
EXPECTED_BESIDE_TARGETS_SHA256 = base.EXPECTED_BESIDE_TARGETS_SHA256
EXPECTED_RUNNER_SHA256 = base.EXPECTED_RUNNER_SHA256
EXPECTED_GUARD_SHA256 = base.EXPECTED_GUARD_SHA256

ADDITIVE_LINEAGE_FIELDS = {
    "automatic_retry",
    "dispatch_ordinal",
    "latest_external_review_decision_file_sha256",
    "latest_external_review_decision_path",
    "latest_external_review_receipt_file_sha256",
    "latest_external_review_receipt_path",
    "latest_external_review_receipt_sha256",
    "manual_path_only_admission_reissue",
    "one_shot_scientific_authorization_consumed_before_successor",
    "parent_approved_manifest_file_sha256",
    "parent_approved_manifest_path",
    "parent_approved_manifest_sha256",
    "path_only_changed_fields",
    "prelaunch_unconsumed_recovery_receipt_file_sha256",
    "prelaunch_unconsumed_recovery_receipt_path",
    "prelaunch_unconsumed_recovery_receipt_sha256",
    "prior_dispatch_guard_terminal_file_sha256",
    "prior_dispatch_guard_terminal_path",
    "prior_dispatch_guard_terminal_receipt_sha256",
    "prior_dispatch_terminally_sealed",
    "scientific_attempt_ordinal",
    "second_admission_rejection_stop",
    "successor_issue_vault_head",
}


def load_json(path: Path, label: str) -> Mapping[str, Any]:
    if not Path(path).is_file():
        raise AuditFailure(f"{label}_missing", f"{label} is missing")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise AuditFailure(f"{label}_type", f"{label} must be an object")
    return value


def check_file(path: Path, expected: str, label: str) -> None:
    if not Path(path).is_file() or file_sha(path) != expected:
        raise AuditFailure(f"{label}_file_hash", f"{label} file identity changed")


def validate_successor_lineage_structure(
    manifest: Mapping[str, Any], parent: Mapping[str, Any]
) -> dict[str, Any]:
    base.validate_self_hash(manifest, "manifest_sha256", "manifest")
    base.validate_self_hash(parent, "manifest_sha256", "parent_manifest")
    expected_lineage = {
        "automatic_retry": False,
        "dispatch_ordinal": 2,
        "latest_external_review_decision_file_sha256": LATEST_REVIEW_FILE_SHA256,
        "latest_external_review_decision_path": str(LATEST_REVIEW_PATH),
        "latest_external_review_receipt_file_sha256": LATEST_REVIEW_RECEIPT_FILE_SHA256,
        "latest_external_review_receipt_path": str(LATEST_REVIEW_RECEIPT_PATH),
        "latest_external_review_receipt_sha256": LATEST_REVIEW_RECEIPT_SHA256,
        "manual_path_only_admission_reissue": True,
        "one_shot_scientific_authorization_consumed_before_successor": False,
        "parent_approved_manifest_file_sha256": PARENT_MANIFEST_FILE_SHA256,
        "parent_approved_manifest_path": str(PARENT_MANIFEST_PATH),
        "parent_approved_manifest_sha256": PARENT_MANIFEST_SHA256,
        "path_only_changed_fields": [
            "run_id",
            "guard_directory",
            "cache_directory",
            "jobs[0].output_namespace",
        ],
        "prelaunch_unconsumed_recovery_receipt_file_sha256": RECOVERY_FILE_SHA256,
        "prelaunch_unconsumed_recovery_receipt_path": str(RECOVERY_PATH),
        "prelaunch_unconsumed_recovery_receipt_sha256": RECOVERY_RECEIPT_SHA256,
        "prior_dispatch_guard_terminal_file_sha256": PRIOR_GUARD_TERMINAL_FILE_SHA256,
        "prior_dispatch_guard_terminal_path": str(PRIOR_GUARD_TERMINAL_PATH),
        "prior_dispatch_guard_terminal_receipt_sha256": PRIOR_GUARD_TERMINAL_RECEIPT_SHA256,
        "prior_dispatch_terminally_sealed": True,
        "scientific_attempt_ordinal": 1,
        "second_admission_rejection_stop": True,
        "successor_issue_vault_head": SUCCESSOR_ISSUE_VAULT_HEAD,
    }
    for key, expected in expected_lineage.items():
        if manifest.get(key) != expected:
            raise AuditFailure(
                "successor_lineage_contract", f"successor lineage changed: {key}"
            )
    if set(manifest) - set(parent) != ADDITIVE_LINEAGE_FIELDS:
        raise AuditFailure(
            "successor_additive_fields", "successor additive field set changed"
        )
    if set(parent) - set(manifest):
        raise AuditFailure(
            "successor_missing_parent_fields", "successor dropped parent fields"
        )
    jobs = manifest.get("jobs")
    parent_jobs = parent.get("jobs")
    if (
        not isinstance(jobs, list)
        or len(jobs) != 1
        or not isinstance(parent_jobs, list)
        or len(parent_jobs) != 1
    ):
        raise AuditFailure("successor_job_count", "successor/parent job count changed")
    exact_paths = {
        "run_id": EXPECTED_RUN_ID,
        "guard_directory": str(EXPECTED_GUARD_DIRECTORY),
        "cache_directory": str(EXPECTED_CACHE_DIRECTORY),
    }
    if any(manifest.get(key) != value for key, value in exact_paths.items()):
        raise AuditFailure("successor_exact_paths", "successor exact run paths changed")
    if jobs[0].get("output_namespace") != str(EXPECTED_OUTPUT_NAMESPACE):
        raise AuditFailure("successor_output_path", "successor output path changed")
    if jobs[0].get("job_id") != EXPECTED_JOB_ID:
        raise AuditFailure("successor_job_id", "fixed runner job_id changed")
    normalized = dict(manifest)
    for key in ADDITIVE_LINEAGE_FIELDS:
        normalized.pop(key, None)
    normalized["manifest_sha256"] = parent["manifest_sha256"]
    normalized["run_id"] = parent["run_id"]
    normalized["guard_directory"] = parent["guard_directory"]
    normalized["cache_directory"] = parent["cache_directory"]
    normalized["jobs"] = [dict(jobs[0])]
    normalized["jobs"][0]["output_namespace"] = parent_jobs[0]["output_namespace"]
    if normalized != parent:
        raise AuditFailure(
            "successor_not_path_only",
            "successor differs from parent outside four operational paths and lineage",
        )
    if len(
        {
            manifest["guard_directory"],
            parent["guard_directory"],
            manifest["cache_directory"],
            parent["cache_directory"],
            jobs[0]["output_namespace"],
            parent_jobs[0]["output_namespace"],
        }
    ) != 6:
        raise AuditFailure(
            "successor_path_collision", "successor paths collide with parent paths"
        )
    return {
        "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        "recovery_receipt_sha256": RECOVERY_RECEIPT_SHA256,
        "dispatch_ordinal": 2,
        "scientific_attempt_ordinal": 1,
        "path_only_changed_fields": list(expected_lineage["path_only_changed_fields"]),
        "parent_equivalent_after_four_path_normalizations": True,
        "second_admission_rejection_stop": True,
    }


def validate_successor_lineage_from_disk(
    manifest: Mapping[str, Any]
) -> dict[str, Any]:
    for path, digest, label in (
        (BASE_AUDITOR_PATH, BASE_AUDITOR_SHA256, "base_auditor"),
        (EXPECTED_MANIFEST_PATH, EXPECTED_MANIFEST_FILE_SHA256, "successor_manifest"),
        (PARENT_MANIFEST_PATH, PARENT_MANIFEST_FILE_SHA256, "parent_manifest"),
        (RECOVERY_PATH, RECOVERY_FILE_SHA256, "recovery_receipt"),
        (
            PRIOR_GUARD_TERMINAL_PATH,
            PRIOR_GUARD_TERMINAL_FILE_SHA256,
            "prior_guard_terminal",
        ),
        (LATEST_REVIEW_PATH, LATEST_REVIEW_FILE_SHA256, "latest_review"),
        (
            LATEST_REVIEW_RECEIPT_PATH,
            LATEST_REVIEW_RECEIPT_FILE_SHA256,
            "latest_review_receipt",
        ),
    ):
        check_file(path, digest, label)
    parent = load_json(PARENT_MANIFEST_PATH, "parent_manifest")
    lineage = validate_successor_lineage_structure(manifest, parent)
    recovery = load_json(RECOVERY_PATH, "recovery_receipt")
    base.validate_self_hash(recovery, "receipt_sha256", "recovery_receipt")
    if (
        recovery.get("receipt_sha256") != RECOVERY_RECEIPT_SHA256
        or recovery.get("status")
        != "GUARD_ATOMIC_IDLE_REJECTED_PRELAUNCH_UNCONSUMED"
        or recovery.get("dispatch_identity_reusable") is not False
        or recovery.get("consumption", {}).get(
            "one_shot_scientific_authorization_consumed"
        )
        is not False
        or recovery.get("consumption", {}).get("child_launches") != 0
        or recovery.get("consumption", {}).get("planner_queries") != 0
    ):
        raise AuditFailure(
            "recovery_contract", "prelaunch-unconsumed recovery contract changed"
        )
    prior = load_json(PRIOR_GUARD_TERMINAL_PATH, "prior_guard_terminal")
    base.validate_self_hash(prior, "receipt_sha256", "prior_guard_terminal")
    if (
        prior.get("receipt_sha256") != PRIOR_GUARD_TERMINAL_RECEIPT_SHA256
        or prior.get("child_pid") is not None
        or prior.get("launch_snapshot") is not None
        or prior.get("output_exists") is not False
        or prior.get("cache_removed") is not True
        or prior.get("lease_released") is not True
        or prior.get("gpu_returned_to_idle_baseline") is not True
    ):
        raise AuditFailure(
            "prior_guard_contract", "prior Guard is not the sealed prelaunch rejection"
        )
    review_receipt = load_json(
        LATEST_REVIEW_RECEIPT_PATH, "latest_review_receipt"
    )
    base.validate_self_hash(
        review_receipt, "receipt_sha256", "latest_review_receipt"
    )
    if review_receipt.get("receipt_sha256") != LATEST_REVIEW_RECEIPT_SHA256:
        raise AuditFailure("latest_review_contract", "latest review receipt changed")
    lineage.update(
        {
            "base_auditor_sha256": BASE_AUDITOR_SHA256,
            "prior_guard_terminal_receipt_sha256": PRIOR_GUARD_TERMINAL_RECEIPT_SHA256,
            "latest_external_review_receipt_sha256": LATEST_REVIEW_RECEIPT_SHA256,
        }
    )
    return lineage


def upgrade_report(report: Mapping[str, Any], lineage: Mapping[str, Any]) -> dict[str, Any]:
    upgraded = dict(report)
    base_receipt = upgraded.pop("receipt_sha256", None)
    upgraded["schema_version"] = (
        "cmf_f2_controlled_insertion_route_gate_postrun_audit_v1_1"
    )
    upgraded["auditor_version"] = "v1_1_path_only_admission_reissue"
    upgraded["base_audit_receipt_sha256"] = base_receipt
    upgraded["successor_lineage"] = dict(lineage)
    upgraded["base_auditor_source_sha256"] = BASE_AUDITOR_SHA256
    upgraded["auditor_source_sha256"] = file_sha(Path(__file__))
    return base.seal_report(upgraded)


def rejected_report(exc: BaseException) -> dict[str, Any]:
    code = exc.code if isinstance(exc, AuditFailure) else "unexpected_auditor_exception"
    return base.seal_report(
        {
            "schema_version": "cmf_f2_controlled_insertion_route_gate_postrun_audit_v1_1",
            "auditor_version": "v1_1_path_only_admission_reissue",
            "status": "REJECTED_F2_POSTRUN_EVIDENCE",
            "pass": False,
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "run_id": EXPECTED_RUN_ID,
            "job_id": EXPECTED_JOB_ID,
            "child_exit_code_alone_was_not_used_as_success": True,
            "automatic_root_continuation_authorized": False,
            "stage1_authorized": False,
            "formal_data": False,
            "base_auditor_source_sha256": BASE_AUDITOR_SHA256,
            "auditor_source_sha256": file_sha(Path(__file__)),
            "failure": {"code": code, "message": str(exc)},
        }
    )


def audit_documents(**kwargs: Any) -> dict[str, Any]:
    try:
        parent = load_json(PARENT_MANIFEST_PATH, "parent_manifest")
        lineage = validate_successor_lineage_structure(kwargs["manifest"], parent)
        report = base.audit_documents(**kwargs)
        return upgrade_report(report, lineage)
    except BaseException as exc:
        return rejected_report(exc)


def audit_from_disk(manifest_path: Path = EXPECTED_MANIFEST_PATH) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    if manifest_path != EXPECTED_MANIFEST_PATH.resolve():
        raise AuditFailure(
            "manifest_path_identity", "V1.1 accepts only the successor manifest path"
        )
    manifest = load_json(manifest_path, "successor_manifest")
    lineage = validate_successor_lineage_from_disk(manifest)
    report = base.audit_from_disk(manifest_path)
    return upgrade_report(report, lineage)


def run_audit(manifest_path: Path = EXPECTED_MANIFEST_PATH) -> dict[str, Any]:
    try:
        return audit_from_disk(manifest_path)
    except BaseException as exc:
        return rejected_report(exc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=EXPECTED_MANIFEST_PATH)
    args = parser.parse_args(argv)
    report = run_audit(args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

