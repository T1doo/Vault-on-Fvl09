"""Deterministic planned specs for authorized runtime-v3_3 nonformal scopes."""

from __future__ import annotations

import json

from .f2_mutually_exclusive_region_layout_v2 import LAYOUT as F2_LAYOUT
from .runtime_v3_3_budget_v1 import ROOT_SCOPES, SCOPE_FAMILIES, scope_budget


SCHEMA_VERSION = "cmf_runtime_v3_3_planned_scope_spec_v1"
SCENE_SEED = 20260829
F4_LAYOUT = {
    "layout_version": "f4_right_arm_mirror_base0_v2_grasp_neutral",
    "branch_neutral_pose": [
        0.15,
        -0.02,
        0.95,
        0.5243570072481656,
        -0.47439082845243685,
        0.4743935067167858,
        0.5243604405510669,
    ],
    "common_x_pose": [0.28, 0.1, 0.762, 1.0, 0.0, 0.0, 0.0],
    "object_poses": {
        "A": [0.07, 0.08, 0.762, 1.0, 0.0, 0.0, 0.0],
        "B": [-0.08, 0.08, 0.762, 1.0, 0.0, 0.0, 0.0],
        "C": [-0.23, 0.08, 0.762, 1.0, 0.0, 0.0, 0.0],
    },
    "slot_poses": {
        "A": [0.07, -0.18, 0.742, 1.0, 0.0, 0.0, 0.0],
        "B": [-0.08, -0.18, 0.742, 1.0, 0.0, 0.0, 0.0],
        "C": [-0.23, -0.18, 0.742, 1.0, 0.0, 0.0, 0.0],
    },
    "tray": {
        "model_id": 0,
        "modelname": "008_tray",
        "pose": [
            0.28,
            -0.12,
            0.76,
            0.706527,
            0.706483,
            -0.0291356,
            -0.0291767,
        ],
    },
}


def planned_scope_spec(scope: str, *, revision_index: int | None = None) -> dict:
    family = SCOPE_FAMILIES[scope]
    if scope in ROOT_SCOPES:
        if revision_index not in (1, 2):
            raise ValueError("root scope revision_index must be 1 or 2")
    elif revision_index is not None:
        raise ValueError("non-root scope cannot declare a revision index")
    slot_ids = {
        "canonical_prefix_real_smoke": "runtime-v3-3-prefix-smoke-f1",
        "F4_cube_grasp_no_action_ik": "runtime-v3-3-f4-cube-ik",
        "F1_planner_root_per_revision": "pilot-F1-A-prestage0",
        "F2_diagnosis_root_per_revision": "pilot-F2-A-prestage0",
        "F3_prefix_root_per_revision": "pilot-F3-A-prestage0",
        "F4_block_root_per_revision": "pilot-F4-A-prestage0",
    }
    value = {
        "schema_version": SCHEMA_VERSION,
        "slot_id": slot_ids[scope],
        "family": family,
        "seed": SCENE_SEED,
        "generator": "controlled_multi_future_joint_scene_v3_3_adapter_v1_3",
        "origin": "runtime_v3_3_pre_stage0_nonformal",
        "scope": scope,
        "budget_sha256": scope_budget(scope)["scope_budget_sha256"],
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stop_condition": "terminal receipt or first cleanup/source/GPU safety uncertainty",
    }
    if scope in ROOT_SCOPES:
        value["implementation_revision_index"] = revision_index
        value["implementation_revision"] = (
            f"{family.lower()}-runtime-v3-3-revision-{revision_index}"
        )
        value["maximum_full_root_execution_per_revision"] = 1
        value["maximum_new_implementation_revisions_per_family"] = 2
    if family == "F2":
        value["plasticbox_model_id"] = 2
        value["scene_layout"] = json.loads(json.dumps(F2_LAYOUT, sort_keys=True))
    if family == "F4":
        value["scene_layout"] = json.loads(json.dumps(F4_LAYOUT, sort_keys=True))
    return value
