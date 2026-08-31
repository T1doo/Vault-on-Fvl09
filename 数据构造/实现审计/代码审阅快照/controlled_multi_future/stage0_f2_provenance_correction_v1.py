"""Hash-bound metadata correction for already executed F2 on/beside raw."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .current_hasher import hash_json
from .stage0_f2_replacement_manifest_v1_2 import (
    IMPLEMENTATION_VERSION,
    ORIGINAL_ATTEMPT_IDS,
    OUTPUT_NAMESPACE,
    REPLACEMENT_ATTEMPT_IDS,
)
from .stage0_smoke_family_runner_v1 import _raw_integrity
from .stage0_smoke_family_runner_v1_1 import _stage0_video_integrity


RUN_SOURCE_SHA256 = "ad79e79df7607c7fc46740283a526a856071d904ef9630bea923a79202364807"
REPLACEMENT_ROOT_SLOT_ID = (
    "stage0-v1_2-F2-pilot-root-A-scene-layout-replacement"
)
REPLACEMENT_MANIFEST_SHA256 = (
    "27512294d0494c945a6b6dfe22ad39b9fc8ee61fbd71fe53fc8bd4978f822689"
)
FAMILY_ROOT = OUTPUT_NAMESPACE / "stage0_f2_replacement"
BRANCH_ROOT = FAMILY_ROOT / "root/branches"
BASE_FAMILY_RECEIPT = FAMILY_ROOT / "stage0_f2_replacement_family_receipt.json"
CORRECTION_OUTPUT = FAMILY_ROOT / "f2_raw_provenance_correction_v1.json"
CORRECTED_FAMILY_OUTPUT = (
    FAMILY_ROOT / "stage0_f2_replacement_family_receipt_corrected_v1.json"
)
CORRECTED_ATTEMPT_DIRECTORY = FAMILY_ROOT / "corrected_attempt_receipts_v1"


def _copy(value: Any) -> Any:
    return json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )


def _load(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    data = Path(path).read_bytes()
    return {
        "path": str(Path(path).resolve()),
        "relative_path": (
            Path(path).resolve().relative_to(relative_to.resolve()).as_posix()
            if relative_to is not None
            else None
        ),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _self_hash(value: Mapping[str, Any], field: str) -> bool:
    payload = dict(value)
    digest = payload.pop(field, None)
    return isinstance(digest, str) and hash_json(payload) == digest


def build_f2_raw_provenance_correction_v1() -> dict[str, Any]:
    base = _load(BASE_FAMILY_RECEIPT)
    if not _self_hash(base, "receipt_sha256"):
        raise ValueError("base F2 replacement family receipt hash is invalid")
    items = []
    for index, program_id in enumerate(("F2-on", "F2-beside"), start=1):
        branch_dir = BRANCH_ROOT / program_id
        branch_path = branch_dir / "receipt.json"
        branch = _load(branch_path)
        raw_manifest_path = branch_dir / "raw/manifest.json"
        raw_manifest = _load(raw_manifest_path)
        expected_attempt = REPLACEMENT_ATTEMPT_IDS[index]
        observed_integrity = _raw_integrity(
            branch_dir,
            branch,
            family="F2",
            program_id=program_id,
            attempt_id=expected_attempt,
            root_slot_id=REPLACEMENT_ROOT_SLOT_ID,
            stage0_manifest_sha256=REPLACEMENT_MANIFEST_SHA256,
            expected_implementation_version=(
                "controlled_multi_future_runtime_v3_3"
            ),
        )
        video = _stage0_video_integrity(
            branch_dir, branch, trajectory_generated=True
        )
        provenance = raw_manifest.get("provenance", {})
        realization = provenance.get("realization_spec", {})
        verifier = branch.get("verifier", {})
        checks = {
            "branch_accepted": branch.get("status") == "accepted",
            "verifier_pass": verifier.get("pass") is True,
            "verifier_implementation_v1_2": verifier.get(
                "implementation_version"
            )
            == IMPLEMENTATION_VERSION,
            "verifier_adapter_v1_8": verifier.get(
                "strict_prefix_adapter_version"
            )
            == "RoboTwinRealSapienStrictPrefixAdapterV1_8",
            "raw_integrity_except_label": observed_integrity.get("pass") is True,
            "observed_wrong_label": provenance.get("implementation_version")
            == "controlled_multi_future_runtime_v3_3",
            "realization_expected_label": realization.get(
                "implementation_version"
            )
            == IMPLEMENTATION_VERSION,
            "realization_attempt_binding": realization.get(
                "stage0_attempt_id"
            )
            == expected_attempt,
            "realization_replacement_binding": realization.get(
                "replacement_for_attempt_id"
            )
            == ORIGINAL_ATTEMPT_IDS[index],
            "source_lock_matches_executed_source": branch.get(
                "branch_current", {}
            ).get("reconstruction_spec_audit", {}).get(
                "simulation_configuration", {}
            ).get("implementation_source_sha256")
            == RUN_SOURCE_SHA256,
            "video_integrity": video.get("pass") is True,
        }
        if not all(checks.values()):
            raise ValueError(
                f"F2 provenance correction evidence failed for {program_id}: {checks}"
            )
        items.append(
            {
                "program_id": program_id,
                "attempt_id": expected_attempt,
                "replacement_for_attempt_id": ORIGINAL_ATTEMPT_IDS[index],
                "branch_receipt": _file(branch_path, relative_to=FAMILY_ROOT),
                "raw_manifest": _file(
                    raw_manifest_path, relative_to=FAMILY_ROOT
                ),
                "raw_streams": _file(
                    branch_dir / "raw/raw_streams.npz", relative_to=FAMILY_ROOT
                ),
                "trace_source": _file(
                    branch_dir / "trace_source.npz", relative_to=FAMILY_ROOT
                ),
                "video": _file(
                    branch_dir / "video/trajectory.mp4",
                    relative_to=FAMILY_ROOT,
                ),
                "observed_implementation_version": (
                    "controlled_multi_future_runtime_v3_3"
                ),
                "corrected_implementation_version": IMPLEMENTATION_VERSION,
                "correction_scope": "raw_manifest.provenance.implementation_version label only",
                "raw_bytes_modified": False,
                "raw_manifest_modified": False,
                "branch_receipt_modified": False,
                "observed_integrity": observed_integrity,
                "video_integrity": video,
                "checks": checks,
                "pass": True,
            }
        )
    value = {
        "schema_version": "cmf_f2_raw_provenance_label_correction_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "executed_source_sha256": RUN_SOURCE_SHA256,
        "bug_source": (
            "family_runners_v3_3._raw_result adapter-version dispatch omitted v1.8"
        ),
        "repair_type": "immutable_artifact_metadata_overlay",
        "physical_attempts_rerun": False,
        "raw_or_video_files_modified": False,
        "items": items,
        "pass": len(items) == 2 and all(item["pass"] for item in items),
    }
    value["receipt_sha256"] = hash_json(value)
    return value


def build_corrected_f2_family_receipt_v1() -> dict[str, Any]:
    base = _load(BASE_FAMILY_RECEIPT)
    correction = build_f2_raw_provenance_correction_v1()
    correction_by_program = {item["program_id"]: item for item in correction["items"]}
    corrected_attempts = []
    for base_attempt in base["attempt_receipts"]:
        program_id = base_attempt["program_id"]
        if program_id == "F2-inside":
            if base_attempt["terminal_status"] != "FAILED_EXECUTION_WITH_EVIDENCE":
                raise ValueError("F2-inside base terminal status changed")
            corrected_attempts.append(_copy(base_attempt))
            continue
        item = correction_by_program[program_id]
        attempt = {
            "schema_version": "cmf_stage0_f2_corrected_attempt_receipt_v1",
            "implementation_version": IMPLEMENTATION_VERSION,
            "attempt_id": base_attempt["attempt_id"],
            "replacement_for_attempt_id": base_attempt[
                "replacement_for_attempt_id"
            ],
            "replacement_reason": base_attempt["replacement_reason"],
            "family": "F2",
            "root_slot_id": base_attempt["root_slot_id"],
            "program_id": program_id,
            "realization": "r_pc",
            "terminal_status": "PASSED",
            "trajectory_generated": True,
            "raw_required_by_branch_status": True,
            "raw_integrity": {
                **item["observed_integrity"],
                "implementation_label_correction_applied": True,
                "corrected_implementation_version": IMPLEMENTATION_VERSION,
                "provenance_correction_receipt_sha256": correction[
                    "receipt_sha256"
                ],
                "pass": True,
            },
            "video_required": True,
            "mp4_required_if_trajectory_generated": True,
            "video_integrity": item["video_integrity"],
            "video_status": "generated",
            "verifier_pass": True,
            "branch_status": "accepted",
            "root_status": base_attempt["root_status"],
            "failure_type": None,
            "failure_message": None,
            "branch_receipt": base_attempt["branch_receipt"],
            "supersedes_derived_attempt_receipt_sha256": base_attempt[
                "receipt_sha256"
            ],
            "physical_attempt_rerun": False,
            "raw_or_video_modified": False,
            "formal_data": False,
            "stage0_data": True,
            "stage0_authorized": True,
            "stage1_authorized": False,
        }
        attempt["receipt_sha256"] = hash_json(attempt)
        corrected_attempts.append(attempt)
    success_count = sum(
        item["terminal_status"] == "PASSED" for item in corrected_attempts
    )
    value = {
        "schema_version": "cmf_stage0_f2_corrected_family_receipt_v1",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "family": "F2",
        "root_slot_id": REPLACEMENT_ROOT_SLOT_ID,
        "replacement_manifest_sha256": REPLACEMENT_MANIFEST_SHA256,
        "base_family_receipt": _file(BASE_FAMILY_RECEIPT),
        "base_family_receipt_sha256": base["receipt_sha256"],
        "provenance_correction_receipt_sha256": correction["receipt_sha256"],
        "attempt_receipts": corrected_attempts,
        "stage0_attempt_count": 3,
        "successful_attempt_count": success_count,
        "failed_attempt_count": 3 - success_count,
        "generated_trajectory_count": 2,
        "generated_video_count": 2,
        "outcome": "FAILED_WITH_EVIDENCE",
        "active_slot_terminal_evidence_valid": True,
        "pipeline_integrity_pass": correction["pass"]
        and base["cleanup_pass"] is True
        and int(base["orphan_process_count"]) == 0,
        "cleanup_pass": base["cleanup_pass"],
        "orphan_process_count": base["orphan_process_count"],
        "budget_counts": base["budget_counts"],
        "current_anchor_lineage_audit": base["current_anchor_lineage_audit"],
        "all_required_videos_complete": True,
        "formal_data": False,
        "stage0_data": True,
        "stage0_authorized": True,
        "stage1_authorized": False,
        "formal_collection_authorized": False,
        "training_authorized": False,
    }
    value["receipt_sha256"] = hash_json(value)
    return value


def write_f2_provenance_correction_v1() -> dict[str, Any]:
    if (
        CORRECTION_OUTPUT.exists()
        or CORRECTED_FAMILY_OUTPUT.exists()
        or CORRECTED_ATTEMPT_DIRECTORY.exists()
    ):
        raise FileExistsError("F2 provenance correction outputs already exist")
    correction = build_f2_raw_provenance_correction_v1()
    corrected = build_corrected_f2_family_receipt_v1()
    for path, value in (
        (CORRECTION_OUTPUT, correction),
        (CORRECTED_FAMILY_OUTPUT, corrected),
    ):
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    CORRECTED_ATTEMPT_DIRECTORY.mkdir()
    for attempt in corrected["attempt_receipts"]:
        path = CORRECTED_ATTEMPT_DIRECTORY / f"{attempt['attempt_id']}.json"
        path.write_text(
            json.dumps(attempt, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    return {
        "correction_receipt_sha256": correction["receipt_sha256"],
        "corrected_family_receipt_sha256": corrected["receipt_sha256"],
        "pass": correction["pass"] and corrected["pipeline_integrity_pass"],
    }


__all__ = [
    "CORRECTED_ATTEMPT_DIRECTORY",
    "CORRECTED_FAMILY_OUTPUT",
    "CORRECTION_OUTPUT",
    "build_corrected_f2_family_receipt_v1",
    "build_f2_raw_provenance_correction_v1",
    "write_f2_provenance_correction_v1",
]
