"""Deterministic diagnosis-first planned specs for runtime-v3_4."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .f2_mutually_exclusive_region_layout_v2 import LAYOUT as F2_LAYOUT
from .f3_grasp_robustness_v10 import build_f3_common_grasp_contract_v10
from .f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from .runtime_v3_4_budget_v1 import SCOPE_FAMILIES, scope_budget


SCHEMA_VERSION = "cmf_runtime_v3_4_planned_scope_spec_v1"
SCENE_SEED = 20260829


def planned_scope_spec(
    scope: str,
    *,
    prerequisite_receipts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    family = SCOPE_FAMILIES[scope]
    prerequisites = json.loads(
        json.dumps(prerequisite_receipts or {}, sort_keys=True, allow_nan=False)
    )
    required = {
        "F1_shared_regression_v3_4": (),
        "F2_inside_targeted_v10": (),
        "F2_full_root_v10": ("F2_inside_targeted_v10",),
        "F3_grasp_three_context_v10": (),
        "F3_full_root_v10": ("F3_grasp_three_context_v10",),
        "F4_corridor_A_v10": (),
        "F4_BC_AB_v10": ("F4_corridor_A_v10",),
        "F4_full_root_v10": ("F4_corridor_A_v10", "F4_BC_AB_v10"),
    }[scope]
    if set(prerequisites) != set(required):
        raise ValueError(
            f"runtime-v3_4 scope {scope} requires prerequisite receipts {required}"
        )
    for name, receipt in prerequisites.items():
        if not isinstance(receipt, Mapping) or receipt.get("pass") is not True:
            raise ValueError(f"runtime-v3_4 prerequisite {name} is not passing")
        if not isinstance(receipt.get("receipt_sha256"), str):
            raise ValueError(f"runtime-v3_4 prerequisite {name} lacks SHA")
    slot_ids = {
        "F1_shared_regression_v3_4": "pilot-F1-A-prestage0-regression",
        "F2_inside_targeted_v10": "pilot-F2-A-prestage0-targeted",
        "F2_full_root_v10": "pilot-F2-A-prestage0",
        "F3_grasp_three_context_v10": "pilot-F3-A-prestage0-targeted",
        "F3_full_root_v10": "pilot-F3-A-prestage0",
        "F4_corridor_A_v10": "pilot-F4-A-prestage0-corridor",
        "F4_BC_AB_v10": "pilot-F4-A-prestage0-block-gates",
        "F4_full_root_v10": "pilot-F4-A-prestage0",
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "slot_id": slot_ids[scope],
        "family": family,
        "arm": "right" if family == "F4" else "left",
        "seed": SCENE_SEED,
        "generator": "controlled_multi_future_joint_scene_v3_4_adapter_v1_4",
        "origin": "runtime_v3_4_diagnosis_first_nonformal",
        "scope": scope,
        "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_scope_invocations": 1,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "prerequisite_receipts": prerequisites,
        "stop_condition": "terminal receipt or first cleanup/source/GPU safety uncertainty",
    }
    if family == "F2":
        result["main_object"] = "071_can/base1"
        result["plasticbox_model_id"] = 2
        result["scene_layout"] = json.loads(json.dumps(F2_LAYOUT, sort_keys=True))
        result["release_strategy"] = "f2_release_safety_then_final_inside_v10"
        result["final_settle_frames"] = 250
    if family == "F3":
        result["bottle"] = "001_bottle/base13"
        result["grasp_contract"] = build_f3_common_grasp_contract_v10()
        result["diagnostic_program_order"] = ["VVHH", "VHVH", "VHHV"]
        result["release_modified"] = False
    if family == "F4":
        result["scene_layout"] = json.loads(json.dumps(F4_LAYOUT, sort_keys=True))
        result["corridor_contract_version"] = (
            "f4_revision4_evidence_fixed_order_corridors_v10"
        )
        result["tray_pose_changed"] = False
        result["arm_changed"] = False
    return result


__all__ = ["SCENE_SEED", "planned_scope_spec"]
