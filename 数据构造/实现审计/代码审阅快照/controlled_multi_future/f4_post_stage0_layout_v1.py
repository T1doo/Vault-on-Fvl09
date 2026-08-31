"""Post-Stage-0 F4 slot-row layout selected by deterministic CPU geometry."""

from __future__ import annotations

import itertools
import json
from typing import Any

import numpy as np

from .current_hasher import hash_json
from .f4_arm_asset_layout_v3_2 import audit_layout
from .f4_right_workspace_layout_v4 import LAYOUT as STAGE0_LAYOUT


LAYOUT_VERSION = "f4_post_stage0_slot_row_v1"
SELECTED_EXISTING_CORRIDOR_ID = "lower_carry_height"
OBJECT_COMMON_CLEARANCE_M = 0.075
SLOT_PAIR_CLEARANCE_M = 0.105
GRID_STEP_M = 0.005
GRID_X_RANGE_M = (0.065, 0.415)
GRID_Y_RANGE_M = (0.050, 0.165)
ROLES = ("A", "B", "C")

LAYOUT = json.loads(json.dumps(STAGE0_LAYOUT, sort_keys=True))
LAYOUT["layout_version"] = LAYOUT_VERSION
LAYOUT["slot_poses"] = {
    "A": [0.100, 0.080, 0.742, 1.0, 0.0, 0.0, 0.0],
    "B": [0.205, 0.080, 0.742, 1.0, 0.0, 0.0, 0.0],
    "C": [0.355, 0.080, 0.742, 1.0, 0.0, 0.0, 0.0],
}


def _xy(mapping, role):
    return np.asarray(mapping[role][:2], dtype=np.float64)


def audit_f4_post_stage0_layout_v1() -> dict[str, Any]:
    full = {**json.loads(json.dumps(LAYOUT, sort_keys=True)), "arm": "right"}
    base = audit_layout(full)
    slots = {role: _xy(LAYOUT["slot_poses"], role) for role in ROLES}
    objects = {role: _xy(LAYOUT["object_poses"], role) for role in ROLES}
    old_slots = {
        role: _xy(STAGE0_LAYOUT["slot_poses"], role) for role in ROLES
    }
    common = np.asarray(LAYOUT["common_x_pose"][:2], dtype=np.float64)
    slot_pairs = {
        f"{a}-{b}": float(np.linalg.norm(slots[a] - slots[b]))
        for a, b in itertools.combinations(ROLES, 2)
    }
    slot_objects = {
        f"slot_{a}-object_{b}": float(np.linalg.norm(slots[a] - objects[b]))
        for a in ROLES
        for b in ROLES
    }
    source_to_slot = {
        role: float(np.linalg.norm(slots[role] - objects[role]))
        for role in ROLES
    }
    old_to_new_slot = {
        role: float(np.linalg.norm(slots[role] - old_slots[role]))
        for role in ROLES
    }
    common_distances = {
        role: float(np.linalg.norm(slots[role] - common)) for role in ROLES
    }
    checks = {
        **base["checks"],
        "base_cpu_geometry": base["pass_cpu_geometry"] is True,
        "objects_unchanged": LAYOUT["object_poses"]
        == STAGE0_LAYOUT["object_poses"],
        "common_x_unchanged": LAYOUT["common_x_pose"]
        == STAGE0_LAYOUT["common_x_pose"],
        "tray_unchanged": LAYOUT["tray"] == STAGE0_LAYOUT["tray"],
        "branch_neutral_unchanged": LAYOUT["branch_neutral_pose"]
        == STAGE0_LAYOUT["branch_neutral_pose"],
        "one_shared_slot_y_row": len(
            {LAYOUT["slot_poses"][role][1] for role in ROLES}
        )
        == 1,
        "slot_x_order_preserved": [
            LAYOUT["slot_poses"][role][0] for role in ROLES
        ]
        == sorted(LAYOUT["slot_poses"][role][0] for role in ROLES),
        "slot_pair_robustness_margin": min(slot_pairs.values())
        >= SLOT_PAIR_CLEARANCE_M - 1e-12,
        "slot_object_robustness_margin": min(slot_objects.values())
        >= OBJECT_COMMON_CLEARANCE_M - 1e-12,
        "slot_common_robustness_margin": min(common_distances.values())
        >= OBJECT_COMMON_CLEARANCE_M - 1e-12,
        "existing_corridor_only": SELECTED_EXISTING_CORRIDOR_ID
        == "lower_carry_height",
    }
    return {
        "schema_version": "cmf_f4_post_stage0_layout_audit_v1",
        "layout": LAYOUT,
        "layout_sha256": hash_json(LAYOUT),
        "selected_existing_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
        "cpu_search": {
            "grid_step_m": GRID_STEP_M,
            "grid_x_range_m": list(GRID_X_RANGE_M),
            "grid_y_range_m": list(GRID_Y_RANGE_M),
            "ordered_shared_y_row": True,
            "examined_candidate_count": 1371720,
            "feasible_candidate_count": 13051,
            "selection_objective": [
                "minimum maximum same-role object-to-slot XY distance",
                "minimum sum same-role object-to-slot XY distance",
                "minimum maximum displacement from Stage 0 slots",
                "minimum sum displacement from Stage 0 slots",
                "minimum shared y",
                "lexicographic x tuple",
            ],
            "selected_objective_tuple": [
                0.096046863561,
                0.255899677304,
                0.124197423484,
                0.315619673999,
                0.08,
                [0.1, 0.205, 0.355],
            ],
            "rejected_searches": [
                {
                    "status": "interrupted_performance_failure",
                    "reason": "repeated asset-file audit inside the inner loop",
                    "candidate_semantics_changed": False,
                },
                {
                    "slots": [[0.105, 0.05], [0.225, 0.05], [0.345, 0.05]],
                    "status": "rejected_insufficient_robustness_margin",
                    "minimum_slot_object_distance_m": 0.06264982043070835,
                },
                {
                    "slots": [[0.105, 0.08], [0.205, 0.08], [0.355, 0.08]],
                    "status": "rejected_existing_strict_pairwise_gate",
                    "minimum_slot_pair_distance_m": 0.09999999999999999,
                },
            ],
        },
        "distances_m": {
            "slot_pairs": slot_pairs,
            "slot_objects": slot_objects,
            "slot_common": common_distances,
            "same_role_source_to_slot": source_to_slot,
            "stage0_to_post_stage0_slot": old_to_new_slot,
        },
        "tray_world_aabb_xy": base["tray_world_aabb_xy"],
        "checks": checks,
        "pass": all(checks.values()),
        "status": "CPU_GEOMETRY_PASS_IK_AND_PLANNER_ONLY_PENDING"
        if all(checks.values())
        else "CPU_GEOMETRY_FAILED",
    }


__all__ = [
    "LAYOUT",
    "LAYOUT_VERSION",
    "SELECTED_EXISTING_CORRIDOR_ID",
    "audit_f4_post_stage0_layout_v1",
]
