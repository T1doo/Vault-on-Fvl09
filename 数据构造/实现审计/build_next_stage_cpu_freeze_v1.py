"""Publish immutable CPU-freeze artifacts for the post-Stage-0 template work."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f1_batch_generation_pilot_v1 import (
    build_f1_batch_pilot_plan_v1,
    validate_f1_batch_pilot_plan_v1,
)
from controlled_multi_future import f1_batch_pilot_scope_v1 as f1_scope
from controlled_multi_future import closure_f3_scope_v2_1 as f3_scope
from controlled_multi_future import f4_selected_layout_scope_v2 as f4_scope
from controlled_multi_future.f2_dynamic_development_scope_v3 import (
    IMPLEMENTATION_VERSION as F2_IMPLEMENTATION_VERSION,
    SCOPE as F2_SCOPE,
    f2_dynamic_development_budget_v3,
    parent_authorization_v3,
)
from controlled_multi_future.f2_dynamic_search_contract_v3 import (
    build_cpu_static_screening_v3,
    validate_cpu_static_screening_v3,
)
from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
    build_static_compatibility_matrix_v3,
    validate_static_compatibility_matrix_v3,
)
from controlled_multi_future.f4_layout_candidate_search_v2 import (
    build_f4_layout_candidate_search_v2,
    build_single_selected_layout_dispatch_v2,
)


AUDIT = Path(__file__).resolve().parent
SOURCE_SHA256 = "9a0b7a9e8640192e82e927aa98c56a0001522bcfec28fdfde3269e12d83e0c65"
TESTS_SHA256 = "dac7861c9e3f817f20a639d38627c9381abc1fea213f15ee8308b2c2e5ffc105"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, value) -> None:
    _write_new(
        path,
        (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8"),
    )


def _f2_scope_publication(matrix, screening, budget):
    planned = {
        "schema_version": "cmf_f2_dynamic_development_planned_scope_spec_v3",
        "implementation_version": F2_IMPLEMENTATION_VERSION,
        "scope": F2_SCOPE,
        "family": "F2",
        "seed": 20260829,
        "matrix_sha256": matrix["matrix_sha256"],
        "screening_sha256": screening["screening_sha256"],
        "dynamic_scope": screening["dynamic_scope"],
        "maximum_dynamic_candidates": 12,
        "first_all_gates_selection": True,
        "provisional_binding_execution_forbidden": True,
        "maximum_development_execution_roots": 1,
        "program_ids": ["F2-inside", "F2-on", "F2-beside"],
        "same_main_object_all_branches": True,
        "same_execution_arm_all_branches": True,
        "old_release_and_verifier_semantics_unchanged": True,
        "automatic_retry": False,
        "fallback_beyond_candidate_12": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "stop_condition": "first full dynamic candidate then one development root, or twelve terminal rejects, or first safety/source/cleanup uncertainty",
    }
    planned["planned_scope_spec_sha256"] = hash_json(planned)
    value = {
        "schema_version": "cmf_f2_dynamic_development_scope_publication_v3",
        "implementation_version": F2_IMPLEMENTATION_VERSION,
        "scope": F2_SCOPE,
        "matrix_sha256": matrix["matrix_sha256"],
        "screening_sha256": screening["screening_sha256"],
        "budget_receipt_sha256": budget["budget_receipt_sha256"],
        "planned_scope_spec": planned,
        "stage0_seal_unchanged": True,
    }
    value["scope_publication_sha256"] = hash_json(value)
    return value


def main() -> int:
    f1_plan = build_f1_batch_pilot_plan_v1()
    if validate_f1_batch_pilot_plan_v1(f1_plan)["pass"] is not True:
        raise RuntimeError("F1 batch plan failed validation")
    matrix = build_static_compatibility_matrix_v3()
    matrix = validate_static_compatibility_matrix_v3(matrix)
    screening = build_cpu_static_screening_v3(matrix)
    screening = validate_cpu_static_screening_v3(screening)
    f4_search = build_f4_layout_candidate_search_v2()
    f4_dispatch = build_single_selected_layout_dispatch_v2(f4_search)
    f2_budget = f2_dynamic_development_budget_v3()
    f2_publication = _f2_scope_publication(matrix, screening, f2_budget)

    publications = {
        f1_scope.PARENT: f1_scope.parent(),
        f1_scope.BUDGET: f1_scope.budget(),
        f1_scope.PUBLICATION: f1_scope.publication(),
        AUDIT / "F1_BATCH_GENERATION_PILOT_V1_PLAN.json": f1_plan,
        Path(
            "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/USER_AUTHORIZATION_F2_ASSET_REDESIGN_V3_20260831.json"
        ): parent_authorization_v3(),
        AUDIT / "POST_STAGE0_F2_ASSET_REDESIGN_V3_BUDGET.json": f2_budget,
        AUDIT / "POST_STAGE0_F2_ASSET_REDESIGN_V3_SCOPE.json": f2_publication,
        AUDIT / "F2_OFFICIAL_ASSET_COMPATIBILITY_MATRIX_V3.json": matrix,
        AUDIT / "F2_CPU_STATIC_SCREENING_V3.json": screening,
        f3_scope.PARENT: f3_scope.parent(),
        f3_scope.BUDGET: f3_scope.budget(),
        f3_scope.PUBLICATION: f3_scope.publication(),
        f4_scope.PARENT: f4_scope.parent(),
        f4_scope.BUDGET: f4_scope.budget(),
        f4_scope.PUBLICATION: f4_scope.publication(),
        AUDIT / "F4_LAYOUT_CANDIDATE_SEARCH_V2.json": f4_search,
    }
    for path, value in publications.items():
        _write_json(Path(path), value)

    artifact_files = {
        path.name: {
            "path": str(path),
            "file_sha256": _file_sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(publications)
    }
    report = {
        "schema_version": "cmf_next_stage_template_cpu_freeze_v1_report",
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "status": "CPU_SOURCE_FREEZE_READY_FOR_PUBLISHED_BASELINE",
        "active_full_suite": {"passed": 635, "failed": 0},
        "snapshot_full_suite": {"passed": 635, "failed": 0},
        "active_snapshot_byte_equal": True,
        "implementation_source_sha256": SOURCE_SHA256,
        "tests_tree_sha256": TESTS_SHA256,
        "f1": {
            "primary_roots": 5,
            "ordered_reserves": 5,
            "target_development_trajectories": 15,
            "gpu_run_generated": False,
        },
        "f2": {
            "matrix_rows": matrix["row_count"],
            "cpu_static_admissible_rows": screening[
                "cpu_static_admissible_count"
            ],
            "dynamic_candidate_ranks": [
                item["rank"] for item in screening["dynamic_scope"]["candidates"]
            ],
            "selected_binding": None,
            "gpu_run_generated": False,
        },
        "f3": {
            "scope": f3_scope.SCOPE,
            "physical_attempts": 0,
            "gpu_run_generated": False,
        },
        "f4": {
            "candidate_count": len(f4_search["candidates"]),
            "cpu_selected_candidate": f4_dispatch["dispatch_candidate_id"],
            "cpu_is_ik_evidence": False,
            "gpu_run_generated": False,
        },
        "artifacts": artifact_files,
        "authorization_receipts_signed": False,
        "gpu_jobs_started": False,
        "formal_trajectory_increment": 0,
        "stage0_reopened": False,
        "canonical_stage1_authorized": False,
        "formal_data_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
        "next_safe_step": "commit and push CPU freeze, then sign source-bound single-use family bundles from the clean published baseline",
    }
    report["report_sha256"] = hash_json(report)
    report_path = AUDIT / "NEXT_STAGE_TEMPLATE_CPU_FREEZE_V1_REPORT.json"
    _write_json(report_path, report)
    markdown = f"""# Next-stage template CPU freeze V1

- Status: `{report['status']}`
- Active tests: `635/635`
- Review-snapshot tests: `635/635`
- Source SHA: `{SOURCE_SHA256}`
- Tests SHA: `{TESTS_SHA256}`
- F1: 5 primary + 5 ordered reserves; GPU not run.
- F2: 1,650 rows, {screening['cpu_static_admissible_count']} CPU-admissible, dynamic ranks 50–61; no selected binding yet.
- F3: V2_1 interface-fixed one-shot prepared; 0 physical attempts in this namespace.
- F4: six CPU candidates, fixed dispatch `{f4_dispatch['dispatch_candidate_id']}`; CPU is not IK evidence.
- Stage 0 was not reopened. Stage 1, formal data, training, H-reveal, compression and π0.5 remain unauthorized.
"""
    _write_new(
        AUDIT / "NEXT_STAGE_TEMPLATE_CPU_FREEZE_V1_REPORT.md",
        markdown.encode("utf-8"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
