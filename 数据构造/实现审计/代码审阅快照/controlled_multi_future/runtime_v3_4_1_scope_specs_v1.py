"""Deterministic one-shot scope specs for runtime-v3_4_1."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .f2_mutually_exclusive_region_layout_v2 import LAYOUT as F2_LAYOUT
from .f3_grasp_robustness_v10 import build_f3_common_grasp_contract_v10
from .f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from .runtime_v3_4_1_budget_v1 import SCOPE_FAMILIES, scope_budget


SCHEMA_VERSION = "cmf_runtime_v3_4_1_planned_scope_spec_v1"
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
        "F1_shared_regression_v3_4_1": (),
        "F2_inside_targeted_v11": (),
        "F2_full_root_v3_4_1": ("F2_inside_targeted_v11",),
        "F3_three_context_targeted_v11": (),
        "F3_full_root_v3_4_1": ("F3_three_context_targeted_v11",),
        "F4_exact_corridor_A_v11": (),
        "F4_BC_preflight_v11": ("F4_exact_corridor_A_v11",),
        "F4_full_root_v3_4_1": (
            "F4_exact_corridor_A_v11",
            "F4_BC_preflight_v11",
        ),
    }[scope]
    if set(prerequisites) != set(required):
        raise ValueError(f"{scope} requires prerequisite receipts {required}")
    for name, receipt in prerequisites.items():
        if not isinstance(receipt, Mapping) or receipt.get("pass") is not True:
            raise ValueError(f"prerequisite {name} is not passing")
        if not isinstance(receipt.get("receipt_sha256"), str):
            raise ValueError(f"prerequisite {name} lacks receipt SHA")
    slot_ids = {
        "F1_shared_regression_v3_4_1": "pilot-F1-A-prestage0-regression-v341",
        "F2_inside_targeted_v11": "pilot-F2-A-prestage0-targeted-v341",
        "F2_full_root_v3_4_1": "pilot-F2-A-prestage0-v341",
        "F3_three_context_targeted_v11": "pilot-F3-A-prestage0-targeted-v341",
        "F3_full_root_v3_4_1": "pilot-F3-A-prestage0-v341",
        "F4_exact_corridor_A_v11": "pilot-F4-A-prestage0-corridor-v341",
        "F4_BC_preflight_v11": "pilot-F4-A-prestage0-bc-v341",
        "F4_full_root_v3_4_1": "pilot-F4-A-prestage0-v341",
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "slot_id": slot_ids[scope],
        "family": family,
        "arm": "right" if family == "F4" else "left",
        "seed": SCENE_SEED,
        "generator": "controlled_multi_future_joint_scene_v3_4_1_adapter_v1_5",
        "origin": "runtime_v3_4_1_one_shot_postmortem_nonformal",
        "scope": scope,
        "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "maximum_scope_invocations": 1,
        "single_source_freeze": True,
        "second_freeze_forbidden": True,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "prerequisite_receipts": prerequisites,
        "stop_condition": "terminal receipt or first cleanup/source/GPU safety uncertainty",
    }
    if family == "F2":
        result.update(
            {
                "main_object": "071_can/base1",
                "plasticbox_model_id": 2,
                "scene_layout": json.loads(json.dumps(F2_LAYOUT, sort_keys=True)),
                "preload_entry_gate": "F2PreloadEntryEvidenceGateV11",
                "release_safety_gate": "F2ReleaseSafetyGateV10",
                "final_inside_gate": "F2FinalInsideSuccessGateV10",
                "final_settle_frames": 250,
                "v10_gate_semantics_changed": False,
            }
        )
    if family == "F3":
        result.update(
            {
                "bottle": "001_bottle/base13",
                "grasp_contract": build_f3_common_grasp_contract_v10(),
                "canonical_program_ids": ["F3-VVHH", "F3-VHVH", "F3-VHHV"],
                "diagnostic_program_id_mutation_forbidden": True,
                "release_modified": False,
            }
        )
    if family == "F4":
        result.update(
            {
                "scene_layout": json.loads(json.dumps(F4_LAYOUT, sort_keys=True)),
                "exact_corridor_application_version": (
                    "f4_exact_variable_length_corridor_application_v11"
                ),
                "layout_changed": False,
                "tray_pose_changed": False,
                "arm_changed": False,
                "final_release_target_changed": False,
            }
        )
        if prerequisites:
            selected = prerequisites["F4_exact_corridor_A_v11"].get(
                "selected_corridor_candidate_v11"
            )
            if not isinstance(selected, Mapping):
                raise ValueError("F4 passing prerequisite lacks selected corridor")
            result["selected_f4_corridor_candidate_v11"] = dict(selected)
    return result


__all__ = ["SCENE_SEED", "planned_scope_spec"]
