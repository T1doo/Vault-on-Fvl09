"""Machine contract for the CPU/source-only V2.3.1a pre-smoke hotfix."""

from __future__ import annotations

from typing import Any

from .canonical_artifact import canonical_hash_json
from .planner_qualification_integration_v2_3_1a import (
    IMPLEMENTATION_VERSION,
    build_manifest_bundle_v2_3_1a,
)
from .planner_wiring_smoke_v2_3_1a import (
    build_updated_full_planner_panel_v1_proposal_v2,
    build_updated_planner_wiring_smoke_v1_proposal_v2,
)
from .planner_wiring_smoke_wave_driver_v1 import (
    build_planner_wiring_smoke_wave_driver_v1_contract,
)


def build_v2_3_1a_pre_smoke_operational_hotfix_contract(
    *, vault_head: str, implementation_source_sha256: str, robotwin_tracked_head: str
) -> dict[str, Any]:
    bundle = build_manifest_bundle_v2_3_1a()
    smoke = build_updated_planner_wiring_smoke_v1_proposal_v2()
    full = build_updated_full_planner_panel_v1_proposal_v2()
    driver = build_planner_wiring_smoke_wave_driver_v1_contract()
    value = {
        "schema_version": "cmf_v2_3_1a_pre_smoke_operational_hotfix_contract",
        "implementation_version": IMPLEMENTATION_VERSION,
        "vault_head": str(vault_head),
        "implementation_source_sha256": str(implementation_source_sha256),
        "robotwin_tracked_head": str(robotwin_tracked_head),
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "f4_manifest_v1_1_sha256": bundle["f4_panel_sha256"],
        "updated_smoke_proposal_v2_sha256": smoke["proposal_sha256"],
        "updated_full_panel_proposal_v2_sha256": full["proposal_sha256"],
        "wave_driver_contract_sha256": driver["contract_sha256"],
        "f4_query_accounting": {
            "target_construction_per_job": 12,
            "chain_per_job": 30,
            "total_per_job": 42,
            "maximum_panel_queries": 1008,
        },
        "exact_bridge_envelope_precedes_authorization": True,
        "authorization_scene_seed_equals_legacy_setup_seed": True,
        "f3_stage_b_inherits_stage_a_scene_seed": True,
        "f4_programs_share_candidate_scene_seed_and_use_distinct_scenes": True,
        "planner_reset_semantics": {
            "field": "planner_reset_nonce",
            "motiongen_reset_seed_argument": True,
            "reset_receipt_bound_to_authorization": True,
            "numeric_rng_seed_application_proven": False,
            "bitwise_determinism_claimed": False,
        },
        "guard_purpose": "planner_wiring_smoke_v1",
        "failure_classes": {
            "NO_VALID_GRASP_TARGET": "PLANNER_CANDIDATE_FAIL",
            "query_or_schema_or_binding_error": "INFRASTRUCTURE_ERROR",
        },
        "authorization": {
            "operational_wave_approval": False,
            "planner_execution": False,
            "gpu_execution": False,
            "physical_execution": False,
            "stage1": False,
            "formal_360": False,
            "training": False,
        },
        "real_counts": {
            "planner_jobs": 0,
            "gpu_scene_jobs": 0,
            "physical_gate_attempts": 0,
            "new_trajectories": 0,
            "formal_trajectories": 0,
        },
        "stage0_reopened": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["build_v2_3_1a_pre_smoke_operational_hotfix_contract"]
