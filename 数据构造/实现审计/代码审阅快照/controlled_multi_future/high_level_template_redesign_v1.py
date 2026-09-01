"""Unified parent contract for the post-consolidation high-level redesign."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
)
from .f3_asset_grasp_qualification_v2 import (
    build_f3_asset_grasp_qualification_v2,
)
from .f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
)


SCHEMA_VERSION = "cmf_high_level_template_redesign_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_template_redesign_v1"
SCOPE = "HIGH_LEVEL_TEMPLATE_REDESIGN_V1"


def build_high_level_template_redesign_v1() -> dict[str, Any]:
    f2 = build_f2_hierarchical_template_search_v1()
    f3 = build_f3_asset_grasp_qualification_v2()
    f4 = build_f4_hierarchical_template_search_v1()
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "scientific_protocol_changed": False,
        "f1_reference": {
            "status": "FROZEN_REFERENCE_PASS",
            "accepted_root_count": 5,
            "accepted_trajectory_count": 15,
            "rerun_authorized": False,
        },
        "stopped_old_searches": [
            "F2_rank62_plus",
            "F3_base13_rotation_extension",
            "F4_c07_plus",
        ],
        "family_contracts": {
            "F2": {
                "scope": f2["scope"],
                "contract_sha256": f2["search_contract_sha256"],
                "maximum_stage_a_candidates": f2["maximum_inside_candidates"],
                "maximum_stage_b_candidates": f2[
                    "maximum_stage_b_layout_candidates"
                ],
                "success_status": f2["success_status"],
                "exhaustion_status": f2["stage_a_exhaustion_status"],
            },
            "F3": {
                "scope": f3["scope"],
                "contract_sha256": f3["qualification_sha256"],
                "maximum_assets": f3["maximum_selected_assets"],
                "maximum_grasp_tuples": f3["maximum_grasp_tuples"],
                "success_status": f3["success_status"],
                "exhaustion_status": f3["exhaustion_status"],
            },
            "F4": {
                "scope": f4["scope"],
                "contract_sha256": f4["search_contract_sha256"],
                "maximum_stage_a_candidates": f4["maximum_stage_a_candidates"],
                "maximum_stage_b_candidates": f4["maximum_stage_b_candidates"],
                "success_status": f4["success_status"],
                "exhaustion_status": f4["stage_a_exhaustion_status"],
            },
        },
        "execution_order": [
            "publish_CPU_contract_and_source_snapshot",
            "sign_source_hash_bound_single_use_GPU_bundles",
            "run_F2_stage_A_F3_level1_F4_stage_A_as_independent_GPU_jobs",
            "run_only_result_authorized_downstream_stages",
            "seal_family_terminals_and_unified_readiness",
        ],
        "gpu_policy": {
            "allowed_physical_gpu_indices": list(range(8)),
            "fresh_idle_required": True,
            "one_project_job_per_card": True,
            "root_sharding_allowed": False,
            "uuid_binding_required": True,
            "guard_lease_pre_post_cleanup_required": True,
            "hot_patch_while_jobs_live_allowed": False,
        },
        "valid_family_terminal_types": [
            "passing_development_root",
            "root_cause_covering_high_level_bounded_exhaustion",
        ],
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "formal_360_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
    }
    value["parent_contract_sha256"] = canonical_hash_json(value)
    return value


def validate_high_level_template_redesign_v1(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    expected = build_high_level_template_redesign_v1()
    if canonical_jsonable(value) != expected:
        raise ValueError("high-level template redesign V1 parent contract changed")
    return expected


__all__ = [
    "build_high_level_template_redesign_v1",
    "validate_high_level_template_redesign_v1",
]
