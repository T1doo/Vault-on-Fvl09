"""V2.3.1 activation-bridge contract; no execution authorization."""

from __future__ import annotations

from typing import Any

from .canonical_artifact import canonical_hash_json
from .planner_qualification_integration_v2_3 import build_manifest_bundle_v2_3
from .planner_qualification_scene_bridges_v2_3_1 import RUNNER_SYMBOLS
from .planner_wiring_smoke_v2_3_1 import (
    build_updated_full_planner_panel_v1_proposal,
    build_updated_planner_wiring_smoke_v1_proposal,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_smoke_activation_bridge_v2_3_1"
SCOPE_RUNNER = "controlled_multi_future.probes.planner_qualification_scope_runner_v2_3"
SCENE_BRIDGE = "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1.run_with_production_scene_bridge_v2_3_1"


def build_v2_3_1_smoke_activation_bridge_contract(
    *, vault_head: str, implementation_source_sha256: str, robotwin_tracked_head: str
) -> dict[str, Any]:
    bundle = build_manifest_bundle_v2_3()
    smoke = build_updated_planner_wiring_smoke_v1_proposal()
    full = build_updated_full_planner_panel_v1_proposal()
    value = {
        "schema_version": "cmf_v2_3_1_smoke_activation_bridge_contract",
        "implementation_version": IMPLEMENTATION_VERSION,
        "vault_head": str(vault_head),
        "implementation_source_sha256": str(implementation_source_sha256),
        "robotwin_tracked_head": str(robotwin_tracked_head),
        "manifest_bundle_sha256": bundle["bundle_sha256"],
        "updated_smoke_proposal_sha256": smoke["proposal_sha256"],
        "updated_full_panel_proposal_sha256": full["proposal_sha256"],
        "scope_runner_module": SCOPE_RUNNER,
        "production_scene_bridge_symbol": SCENE_BRIDGE,
        "runner_symbols": RUNNER_SYMBOLS,
        "job_kinds": ["F2_STAGE_A", "F3_STAGE_A", "F3_STAGE_B", "F4_PROGRAM"],
        "required_guard_authorization_fields": [
            "timeout_seconds", "output_namespace", "authorized_command_sha256",
            "family", "scene_seed", "source_lock_receipt_path",
            "source_lock_receipt_sha256", "implementation_source_sha256",
            "budget", "budget_receipt_sha256", "controlled_action_limit",
            "physics_step_limit", "guard_receipt_path",
            "consumption_ledger_directory", "gpu_lease_directory",
            "job_cache_root_directory", "authorized_run_id",
            "reviewed_content_commit",
        ],
        "f3_stage_b_dependency_artifact_registry_required": True,
        "planner_rng_seed_authorization_to_reset_receipt_exact": True,
        "f4_query_accounting": {
            "target_construction_queries": 12,
            "chain_queries": 30,
            "total_queries_per_program": 42,
            "budget_exhaustion_classification": "INFRASTRUCTURE_ERROR",
        },
        "failure_classes": {
            "infrastructure": "stop_wave",
            "planner_candidate_fail": "retain_terminal_continue_frozen_order",
            "physical_design_fail": "not_applicable_no_physical_execution",
        },
        "authorization": {
            "wave_approval": False,
            "planner_execution": False,
            "gpu_execution": False,
            "physical_execution": False,
            "stage1": False,
            "formal_360": False,
            "training": False,
        },
        "physical_execution_count": 0,
        "trajectory_count": 0,
        "stage0_reopened": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["IMPLEMENTATION_VERSION", "build_v2_3_1_smoke_activation_bridge_contract"]
