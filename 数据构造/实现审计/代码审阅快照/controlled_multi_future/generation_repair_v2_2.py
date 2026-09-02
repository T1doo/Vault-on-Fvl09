"""Machine-readable CPU completion contract for Generation Repair V2.2."""

from __future__ import annotations

import inspect
from typing import Any

from .canonical_artifact import canonical_hash_json
from .f2_inside_control_search_v2 import (
    audit_f2_post_close_grasp_transform_v2,
    audit_f2_post_lift_grasp_transform_v2,
)
from .f3_planner_integration_v3 import STAGE_A_PURPOSE, STAGE_B_PURPOSE
from .f4_program_planner_integration_v2 import PROGRAMS, PURPOSE
from .high_level_physical_runner_v1 import (
    execute_f2_controlled_insertion_physical_v2,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_generation_repair_v2_2"
BASE_VAULT_COMMIT = "0dd38a2fca83ba41304bc526f663c8a1522cf594"


def build_generation_repair_v2_2_contract() -> dict[str, Any]:
    f2_parameters = list(
        inspect.signature(execute_f2_controlled_insertion_physical_v2).parameters
    )
    forbidden_external_geometry = (
        "planned_actor_pose",
        "target_actor_pose",
        "runtime_signed_horizontal_margin_m",
        "opening_normal_world",
    )
    value = {
        "schema_version": "cmf_generation_repair_v2_2_contract",
        "implementation_version": IMPLEMENTATION_VERSION,
        "base_vault_commit": BASE_VAULT_COMMIT,
        "scope": "CPU-only Generation Repair V2.2",
        "f2": {
            "executor_symbol": (
                "controlled_multi_future.high_level_physical_runner_v1."
                "execute_f2_controlled_insertion_physical_v2"
            ),
            "pre_lift_gate_symbol": (
                f"{audit_f2_post_close_grasp_transform_v2.__module__}."
                f"{audit_f2_post_close_grasp_transform_v2.__name__}"
            ),
            "post_lift_gate_symbol": (
                f"{audit_f2_post_lift_grasp_transform_v2.__module__}."
                f"{audit_f2_post_lift_grasp_transform_v2.__name__}"
            ),
            "ordered_phases": [
                "pregrasp",
                "grasp",
                "close",
                "settle_250",
                "pre_lift_gate_table_support_allowed",
                "qualification_micro_lift_25mm",
                "post_lift_hold_50",
                "post_lift_off_table_retention_gate",
                "suffix_from_post_lift_actual_transform",
                "preinsert_descend_support_release_retreat",
            ],
            "planner_query_minimum": 8,
            "post_lift_drift_limits": {
                "translation_m": 0.005,
                "orientation_rad": 0.050,
            },
            "executor_parameters": f2_parameters,
            "forbidden_external_geometry_parameters_absent": all(
                name not in f2_parameters for name in forbidden_external_geometry
            ),
            "runtime_asset_metadata_independent_of_certificate": True,
        },
        "f3": {
            "official_raw_pose_generation_receipt_required": True,
            "raw_pose_fields_bound": [
                "asset",
                "arm",
                "contact_point_id",
                "rotation_candidate_index",
                "pregrasp_distance_m",
                "actor_pose_sha256",
                "official_generator_version",
                "raw_pregrasp_sha256",
                "raw_grasp_sha256",
            ],
            "stage_a_purpose": STAGE_A_PURPOSE,
            "stage_b_purpose": STAGE_B_PURPOSE,
            "stage_a_order": ["pregrasp", "grasp", "lift"],
            "stage_b_order": [
                "lift",
                "central",
                "V_plus",
                "V_minus",
                "central",
                "H_plus",
                "H_minus",
                "central",
            ],
            "stage_a_alone_candidate_ready": False,
            "both_stages_required": True,
        },
        "f4": {
            "purpose": PURPOSE,
            "program_orders": {
                key: list(order) for key, order in PROGRAMS.items()
            },
            "program_id_order_exact_binding_required": True,
            "actual_source_layout_gate_before_planner": True,
            "geometry_v2_rerun_from_actual_source_poses": True,
            "independent_fresh_or_reconstructed_scene_per_program": True,
            "all_three_programs_required_per_hv2_candidate": True,
            "abc_only_candidate_qualification_forbidden": True,
        },
        "dispatch": {
            "legacy_high_level_dispatch_activated": False,
            "v2_2_planner_issuer_implemented": False,
            "planner_only_design_budget_proposal_allowed": True,
        },
        "authorization": {
            "planner_execution": False,
            "gpu_execution": False,
            "physical_execution": False,
            "stage1": False,
            "formal_360": False,
            "training": False,
            "h_reveal": False,
            "compression": False,
            "pi_0_5": False,
        },
        "stage0_reopened_or_rerun": False,
        "new_trajectory_count": 0,
        "formal_trajectory_increment": 0,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["build_generation_repair_v2_2_contract"]
