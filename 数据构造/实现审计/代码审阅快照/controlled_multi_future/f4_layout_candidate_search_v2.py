"""Pure-CPU, pre-registered F4 layout candidate contract.

This module intentionally does not import SAPIEN, a planner, or CUDA.  A CPU
pass is only a necessary-condition audit.  It never means that endpoint IK,
whole-robot collision, rendered instance visibility, or a complete planner
chain has passed.
"""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .canonical_artifact import canonical_hash_json as hash_json
from .f4_arm_asset_layout_v3_2 import (
    RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
    audit_layout,
)
from .f4_derivation_interface_v2 import validate_f4_derivation_interface_v2
from .f4_post_stage0_layout_v1 import LAYOUT as CLOSURE_LAYOUT
from .f4_top_down_block_carry_v8 import (
    _audit_nominal_noninterference,
    _build_role_group,
)
from .f4_top_down_clearance_v6 import (
    build_uniform_f4_top_down_clearance_contract_v6,
)


SCHEMA_VERSION = "cmf_f4_layout_candidate_search_v2"
DISPATCH_SCHEMA_VERSION = "cmf_f4_single_selected_layout_dispatch_v2"
IMPLEMENTATION_VERSION = "controlled_multi_future_post_stage0_f4_selected_layout_v2"
SELECTED_LAYOUT_SCOPE = "F4_selected_layout_v2_complete_three_program_planner_only"
SELECTED_EXISTING_CORRIDOR_ID = "lower_carry_height"
PROGRAM_ORDERS = (("A", "B", "C"), ("A", "C", "B"), ("B", "A", "C"))
ROLES = ("A", "B", "C")
MAXIMUM_CANDIDATE_COUNT = 12

# This static-camera specification is copied from the active aloha-agilex
# embodiment and D435 camera config.  Center-in-frustum is necessary only; it
# does not establish non-occlusion or rendered-pixel visibility.
HEAD_CAMERA = {
    "name": "head_camera",
    "position": [-0.032, -0.45, 1.35],
    "forward": [0.0, 0.6, -0.8],
    "left": [-1.0, 0.0, 0.0],
    "vertical_fov_degrees": 37.0,
    "width": 320,
    "height": 240,
    "near_m": 0.1,
    "far_m": 100.0,
}

# The source row is moved into the frozen head-camera frustum.  Its physical
# reachability remains explicitly pending.  The common-X and tray never move.
VISIBLE_OBJECT_POSES = {
    "A": [0.06, 0.12, 0.762, 1.0, 0.0, 0.0, 0.0],
    "B": [0.18, 0.14, 0.762, 1.0, 0.0, 0.0, 0.0],
    "C": [0.33, 0.17, 0.762, 1.0, 0.0, 0.0, 0.0],
}
SLOT_ROWS = (
    (0.100, 0.205, 0.355),
    (0.080, 0.200, 0.360),
    (0.070, 0.195, 0.360),
)
SLOT_Y_M = 0.04
R4_CARRY_ORIENTATION_WXYZ = [
    0.683011,
    -0.183023,
    0.183016,
    0.683011,
]

ALLOWED_LAYOUT_DIFF_PATHS = frozenset(
    {
        "layout_version",
        "object_poses.A",
        "object_poses.B",
        "object_poses.C",
        "slot_poses.A",
        "slot_poses.B",
        "slot_poses.C",
        "branch_neutral_pose",
    }
)
def _pose7(value: Sequence[float], label: str) -> list[float]:
    pose = np.asarray(value, dtype=np.float64).reshape(-1)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be finite pose7")
    norm = float(np.linalg.norm(pose[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion is invalid")
    pose = pose.copy()
    pose[3:] /= norm
    return pose.tolist()


def _slerp(left: Sequence[float], right: Sequence[float], fraction: float) -> list[float]:
    q0 = np.asarray(left, dtype=np.float64)
    q1 = np.asarray(right, dtype=np.float64)
    q0 /= np.linalg.norm(q0)
    q1 /= np.linalg.norm(q1)
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    dot = float(np.clip(dot, -1.0, 1.0))
    if dot > 0.9995:
        result = q0 + float(fraction) * (q1 - q0)
    else:
        theta = math.acos(dot)
        result = (
            math.sin((1.0 - fraction) * theta) / math.sin(theta) * q0
            + math.sin(fraction * theta) / math.sin(theta) * q1
        )
    result /= np.linalg.norm(result)
    return result.tolist()


PREPLACE_ORIENTATIONS = (
    (
        "halfway_to_r4_carry",
        _slerp(
            RIGHT_ARM_COMMON_GRASP_ORIENTATION_WXYZ,
            R4_CARRY_ORIENTATION_WXYZ,
            0.5,
        ),
    ),
    (
        "r4_carry",
        _pose7(
            [0.0, 0.0, 0.0, *R4_CARRY_ORIENTATION_WXYZ],
            "R4 carry orientation",
        )[3:],
    ),
)


def _layout_candidate(index: int, slot_xs: Sequence[float], orientation_name: str, orientation: Sequence[float]) -> dict[str, Any]:
    layout = deepcopy(CLOSURE_LAYOUT)
    layout["layout_version"] = f"f4_post_closure_layout_candidate_v2_{index:02d}"
    layout["object_poses"] = deepcopy(VISIBLE_OBJECT_POSES)
    layout["slot_poses"] = {
        role: [float(x), SLOT_Y_M, 0.742, 1.0, 0.0, 0.0, 0.0]
        for role, x in zip(ROLES, slot_xs)
    }
    # The CPU contract keeps the proven shared neutral target.  A future real
    # prefix must still re-seal its realized canonical neutral independently.
    layout["branch_neutral_pose"] = deepcopy(CLOSURE_LAYOUT["branch_neutral_pose"])
    candidate = {
        "candidate_index": int(index),
        "candidate_id": f"f4-layout-v2-c{index:02d}",
        "arm": "right",
        "program_ids": ["F4-ABC", "F4-ACB", "F4-BAC"],
        "object_slot_mapping": {role: f"slot_{role}" for role in ROLES},
        "verifier_policy": "unchanged_controlled_multi_future_f1_f4_v1_2_f4",
        "layout": layout,
        "layout_sha256": hash_json(layout),
        "preplace_approach_orientation_name": orientation_name,
        "preplace_approach_orientation_wxyz": _pose7(
            [0.0, 0.0, 0.0, *orientation], "preplace orientation"
        )[3:],
        "target_change_scope": "uniform_A_B_C_preplace_quaternion_only",
        "allowed_layout_diff_paths": sorted(ALLOWED_LAYOUT_DIFF_PATHS),
        "added_waypoints": [],
        "temporary_waypoint_allowed": False,
    }
    candidate["candidate_sha256"] = hash_json(candidate)
    return candidate


def preregistered_f4_layout_candidates_v2() -> list[dict[str, Any]]:
    candidates = []
    index = 1
    for slot_xs in SLOT_ROWS:
        for orientation_name, orientation in PREPLACE_ORIENTATIONS:
            candidates.append(
                _layout_candidate(index, slot_xs, orientation_name, orientation)
            )
            index += 1
    if not 0 < len(candidates) <= MAXIMUM_CANDIDATE_COUNT:
        raise AssertionError("F4 V2 preregistered candidate bound changed")
    return candidates


def _changed_paths(left: Mapping[str, Any], right: Mapping[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    keys = set(left) | set(right)
    for key in keys:
        path = f"{prefix}.{key}" if prefix else str(key)
        lv, rv = left.get(key), right.get(key)
        if isinstance(lv, Mapping) and isinstance(rv, Mapping):
            paths.update(_changed_paths(lv, rv, path))
        elif lv != rv:
            paths.add(path)
    return paths


def audit_head_camera_frustum_v2(layout: Mapping[str, Any]) -> dict[str, Any]:
    camera = HEAD_CAMERA
    position = np.asarray(camera["position"], dtype=np.float64)
    forward = np.asarray(camera["forward"], dtype=np.float64)
    left = np.asarray(camera["left"], dtype=np.float64)
    forward /= np.linalg.norm(forward)
    left /= np.linalg.norm(left)
    up = np.cross(forward, left)
    basis = np.stack([forward, left, up], axis=1)
    tan_vertical = math.tan(math.radians(camera["vertical_fov_degrees"]) / 2.0)
    tan_horizontal = tan_vertical * float(camera["width"]) / float(camera["height"])
    points = {
        **{role: layout["object_poses"][role][:3] for role in ROLES},
        "common_x": layout["common_x_pose"][:3],
    }
    projections = {}
    for role, point in points.items():
        local = basis.T @ (np.asarray(point, dtype=np.float64) - position)
        depth = float(local[0])
        horizontal_ratio = abs(float(local[1])) / depth if depth > 0.0 else math.inf
        vertical_ratio = abs(float(local[2])) / depth if depth > 0.0 else math.inf
        passed = bool(
            camera["near_m"] < depth < camera["far_m"]
            and horizontal_ratio < tan_horizontal
            and vertical_ratio < tan_vertical
        )
        projections[role] = {
            "camera_xyz_forward_left_up_m": local.tolist(),
            "horizontal_ratio": horizontal_ratio,
            "vertical_ratio": vertical_ratio,
            "center_inside_frustum": passed,
        }
    return {
        "schema_version": "cmf_f4_camera_frustum_necessary_condition_v2",
        "camera": deepcopy(camera),
        "required_dynamic_roles": list(points),
        "projections": projections,
        "pass": all(value["center_inside_frustum"] for value in projections.values()),
        "necessary_condition_only": True,
        "occlusion_checked": False,
        "rendered_instance_pixels_checked": False,
        "segmentation_visibility_pending": True,
    }


def _generic_geometry_audit(layout: Mapping[str, Any]) -> dict[str, Any]:
    full = deepcopy(dict(layout))
    full["arm"] = "right"
    full["branch_neutral_orientation_policy"] = (
        "single_preregistered_pose_shared_by_ABC_ACB_BAC"
    )
    base = audit_layout(full)
    objects = {
        role: np.asarray(layout["object_poses"][role][:2], dtype=np.float64)
        for role in ROLES
    }
    slots = {
        role: np.asarray(layout["slot_poses"][role][:2], dtype=np.float64)
        for role in ROLES
    }
    common = np.asarray(layout["common_x_pose"][:2], dtype=np.float64)
    slot_object = [
        float(np.linalg.norm(slots[left] - objects[right]))
        for left in ROLES
        for right in ROLES
    ]
    slot_common = [float(np.linalg.norm(slots[role] - common)) for role in ROLES]
    object_common = [float(np.linalg.norm(objects[role] - common)) for role in ROLES]
    checks = {
        "legacy_cpu_geometry": base["pass_cpu_geometry"] is True,
        "slot_object_center_margin_75mm": min(slot_object) >= 0.075 - 1e-12,
        "slot_common_center_margin_75mm": min(slot_common) >= 0.075 - 1e-12,
        "object_common_center_margin_75mm": min(object_common) >= 0.075 - 1e-12,
    }
    return {
        "legacy_audit": base,
        "minimum_slot_object_center_distance_m": min(slot_object),
        "minimum_slot_common_center_distance_m": min(slot_common),
        "minimum_object_common_center_distance_m": min(object_common),
        "checks": checks,
        "pass": all(checks.values()),
    }


def _interface_derived(role: str, candidate: Mapping[str, Any], targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = [
        {"segment_id": str(item["segment_id"]), "pose": _pose7(item["pose"], str(item["segment_id"]))}
        for item in targets
    ]
    target_hash = hash_json(normalized)
    if role == "A":
        return {
            "role": role,
            "selected_candidate_id": candidate["candidate_id"],
            "targets": normalized,
            "preplanner_gate": {
                "pass": True,
                "candidate_contract_target_pose_sha256": target_hash,
                "applied_planner_target_pose_sha256": target_hash,
            },
        }
    value = {
        "role": role,
        "selected_candidate_id": candidate["candidate_id"],
        "targets": normalized,
        "target_pose_sha256": target_hash,
        "checks": {"uniform_candidate_application": True},
        "pass": True,
    }
    value["receipt_sha256"] = hash_json(value)
    return value


def _candidate_target_and_sequence_audit(candidate: Mapping[str, Any]) -> dict[str, Any]:
    layout = candidate["layout"]
    top_down = build_uniform_f4_top_down_clearance_contract_v6(
        object_poses=layout["object_poses"], arm="right"
    )
    if top_down["pass"] is not True:
        raise ValueError("F4 candidate top-down source contract failed")
    top_by_role = {item["role"]: item for item in top_down["groups"]}
    interfaces = {}
    per_order = {}
    target_ids = {}
    target_edit_checks = []
    for order in PROGRAM_ORDERS:
        groups = []
        for role in order:
            group = _build_role_group(
                role=role,
                source_actor_pose=layout["object_poses"][role],
                slot_pose=layout["slot_poses"][role],
                neutral_pose=layout["branch_neutral_pose"],
                top_down_group=top_by_role[role],
            )
            base_targets = deepcopy(group["targets"])
            targets = deepcopy(base_targets)
            preplace = next(
                item for item in targets if item["segment_id"] == f"{role}_preplace"
            )
            original_translation = list(preplace["pose"][:3])
            preplace["pose"][3:] = list(candidate["preplace_approach_orientation_wxyz"])
            if preplace["pose"][:3] != original_translation:
                raise AssertionError("preplace orientation edit changed translation")
            for before, after in zip(base_targets, targets):
                if before["segment_id"] == f"{role}_preplace":
                    target_edit_checks.append(
                        before["pose"][:3] == after["pose"][:3]
                        and after["pose"][3:]
                        == candidate["preplace_approach_orientation_wxyz"]
                    )
                else:
                    target_edit_checks.append(before == after)
            group = {**group, "targets": targets}
            groups.append(group)
            if role not in interfaces:
                derived = _interface_derived(role, candidate, targets)
                interfaces[role] = validate_f4_derivation_interface_v2(
                    derived,
                    role=role,
                    selected_candidate={
                        "candidate_id": candidate["candidate_id"],
                        "candidate_application_sha256": candidate["candidate_sha256"],
                    },
                )
                target_ids[role] = [item["segment_id"] for item in targets]
        nominal = _audit_nominal_noninterference(
            groups=groups,
            object_poses=layout["object_poses"],
            object_order=order,
        )
        per_order["".join(order)] = nominal
    no_waypoint = all(
        target_ids[role]
        == [
            f"{role}_pregrasp",
            f"{role}_grasp",
            f"{role}_lift",
            f"{role}_carry_mid",
            f"{role}_preplace",
            f"{role}_release",
            f"{role}_neutral",
        ]
        for role in ROLES
    )
    checks = {
        "top_down_source_contract_pass": top_down["pass"] is True,
        "all_three_orders_nominal_sequential_noninterference": all(
            item["pass"] is True for item in per_order.values()
        ),
        "all_role_derivation_interfaces_pass": all(
            item["pass"] is True for item in interfaces.values()
        ),
        "exact_seven_segments_no_temporary_waypoint": no_waypoint,
        "candidate_declares_no_waypoint": candidate["added_waypoints"] == []
        and candidate["temporary_waypoint_allowed"] is False,
        "only_preplace_quaternion_changed": bool(target_edit_checks)
        and all(target_edit_checks),
    }
    return {
        "top_down_source_contract_sha256": top_down["receipt_sha256"],
        "per_order_nominal_sequential_noninterference": per_order,
        "derivation_interfaces": interfaces,
        "target_segment_ids": target_ids,
        "checks": checks,
        "pass": all(checks.values()),
    }


def audit_f4_layout_candidate_v2(candidate: Mapping[str, Any]) -> dict[str, Any]:
    layout = candidate["layout"]
    changed = _changed_paths(CLOSURE_LAYOUT, layout)
    invariant_checks = {
        "allowed_layout_diff_only": changed <= ALLOWED_LAYOUT_DIFF_PATHS,
        "common_x_unchanged": layout["common_x_pose"] == CLOSURE_LAYOUT["common_x_pose"],
        "tray_unchanged": layout["tray"] == CLOSURE_LAYOUT["tray"],
        "right_arm_fixed": True,
        "programs_fixed": PROGRAM_ORDERS
        == (("A", "B", "C"), ("A", "C", "B"), ("B", "A", "C")),
        "object_slot_mapping_fixed": list(layout["object_poses"]) == list(ROLES)
        and list(layout["slot_poses"]) == list(ROLES)
        and candidate["object_slot_mapping"]
        == {role: f"slot_{role}" for role in ROLES},
        "right_arm_declaration_exact": candidate["arm"] == "right",
        "program_declaration_exact": candidate["program_ids"]
        == ["F4-ABC", "F4-ACB", "F4-BAC"],
        "verifier_change_forbidden": candidate["verifier_policy"]
        == "unchanged_controlled_multi_future_f1_f4_v1_2_f4",
        "preplace_change_scope_exact": candidate["target_change_scope"]
        == "uniform_A_B_C_preplace_quaternion_only",
    }
    geometry = _generic_geometry_audit(layout)
    frustum = audit_head_camera_frustum_v2(layout)
    target = _candidate_target_and_sequence_audit(candidate)
    checks = {
        "invariants": all(invariant_checks.values()),
        "cpu_geometry": geometry["pass"] is True,
        "camera_frustum_necessary_condition": frustum["pass"] is True,
        "target_interface_and_sequential_noninterference": target["pass"] is True,
    }
    result = {
        "schema_version": "cmf_f4_layout_candidate_cpu_audit_v2",
        "candidate_index": candidate["candidate_index"],
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "changed_layout_paths": sorted(changed),
        "invariant_checks": invariant_checks,
        "geometry": geometry,
        "camera_frustum": frustum,
        "target_and_sequence": target,
        "checks": checks,
        "cpu_pass": all(checks.values()),
        "true_endpoint_ik_pending": True,
        "official_collision_planner_pending": True,
        "complete_three_program_planner_only_pending": True,
        "rendered_segmentation_visibility_pending": True,
        "gpu_ready": False,
        "scientifically_supported": False,
    }
    result["audit_sha256"] = hash_json(result)
    return result


def build_f4_layout_candidate_search_v2() -> dict[str, Any]:
    candidates = preregistered_f4_layout_candidates_v2()
    audits = [audit_f4_layout_candidate_v2(item) for item in candidates]
    first = next((item["candidate_id"] for item in audits if item["cpu_pass"]), None)
    result = {
        "schema_version": SCHEMA_VERSION,
        "candidate_count": len(candidates),
        "maximum_candidate_count": MAXIMUM_CANDIDATE_COUNT,
        "fixed_candidate_order": [item["candidate_id"] for item in candidates],
        "candidate_manifest_sha256": hash_json(candidates),
        "candidates": candidates,
        "cpu_audits": audits,
        "first_cpu_admissible_candidate_id": first,
        "cpu_search_complete": True,
        "selection_complete": False,
        "true_endpoint_ik_pending": True,
        "official_collision_planner_pending": True,
        "complete_three_program_planner_only_pending": True,
        "rendered_segmentation_visibility_pending": True,
        "gpu_ready": False,
        "cpu_pass_must_not_be_reported_as_layout_selected": True,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    result["search_contract_sha256"] = hash_json(result)
    return result


def validate_f4_layout_candidate_search_v2(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_f4_layout_candidate_search_v2()
    if dict(value) != expected:
        raise ValueError("F4 V2 candidate search contract changed or was tampered")
    return expected


def build_single_selected_layout_dispatch_v2(search: Mapping[str, Any]) -> dict[str, Any]:
    verified = validate_f4_layout_candidate_search_v2(search)
    selected = verified["first_cpu_admissible_candidate_id"]
    if selected is None:
        raise ValueError("F4 V2 has no CPU-admissible candidate")
    candidate = next(item for item in verified["candidates"] if item["candidate_id"] == selected)
    result = {
        "schema_version": DISPATCH_SCHEMA_VERSION,
        "search_contract_sha256": verified["search_contract_sha256"],
        "dispatch_candidate_id": selected,
        "dispatch_candidate_sha256": candidate["candidate_sha256"],
        "maximum_layout_dispatch_count": 1,
        "automatic_fallback": False,
        "later_candidate_fallback_forbidden": True,
        "temporary_waypoint_forbidden": True,
        "gpu_authorization_created": False,
        "gpu_ready": False,
        "true_endpoint_ik_pending": True,
        "complete_three_program_planner_only_pending": True,
        "rendered_segmentation_visibility_pending": True,
        "failure_stop": "terminal_higher_level_task_layout_redesign_no_fallback",
    }
    result["dispatch_contract_sha256"] = hash_json(result)
    return result


def validate_selected_layout_runtime_binding_v2(
    planned_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the future one-shot scope to the exact CPU search and c01 dispatch."""

    search = build_f4_layout_candidate_search_v2()
    dispatch = build_single_selected_layout_dispatch_v2(search)
    if planned_spec.get("scope") != SELECTED_LAYOUT_SCOPE:
        raise ValueError("F4 selected-layout V2 scope mismatch")
    if planned_spec.get("f4_layout_candidate_search_v2") != search:
        raise ValueError("F4 selected-layout V2 search contract mismatch")
    if planned_spec.get("f4_single_selected_layout_dispatch_v2") != dispatch:
        raise ValueError("F4 selected-layout V2 dispatch contract mismatch")
    candidate_id = dispatch["dispatch_candidate_id"]
    candidate = next(
        item for item in search["candidates"] if item["candidate_id"] == candidate_id
    )
    checks = {
        "search_hash_exact": planned_spec.get("f4_layout_search_contract_sha256")
        == search["search_contract_sha256"],
        "dispatch_hash_exact": planned_spec.get("f4_layout_dispatch_contract_sha256")
        == dispatch["dispatch_contract_sha256"],
        "candidate_id_exact": planned_spec.get("selected_layout_candidate_id")
        == candidate_id,
        "candidate_hash_exact": planned_spec.get("selected_layout_candidate_sha256")
        == candidate["candidate_sha256"],
        "layout_exact": planned_spec.get("scene_layout") == candidate["layout"],
        "layout_hash_exact": planned_spec.get("scene_layout_sha256")
        == candidate["layout_sha256"],
        "corridor_exact": planned_spec.get("post_stage0_selected_f4_corridor_id")
        == SELECTED_EXISTING_CORRIDOR_ID,
        "no_fallback": planned_spec.get("automatic_fallback") is False,
        "no_temporary_waypoint": planned_spec.get("temporary_waypoint_allowed")
        is False,
        "right_arm": planned_spec.get("arm") == "right",
        "programs_exact": planned_spec.get("canonical_program_ids")
        == ["F4-ABC", "F4-ACB", "F4-BAC"],
    }
    result = {
        "schema_version": "cmf_f4_selected_layout_runtime_binding_v2",
        "search_contract_sha256": search["search_contract_sha256"],
        "dispatch_contract_sha256": dispatch["dispatch_contract_sha256"],
        "candidate_id": candidate_id,
        "candidate_sha256": candidate["candidate_sha256"],
        "layout_sha256": candidate["layout_sha256"],
        "selected_existing_corridor_id": SELECTED_EXISTING_CORRIDOR_ID,
        "checks": checks,
        "pass": all(checks.values()),
        "true_endpoint_ik_pending": True,
        "complete_three_program_planner_only_pending": True,
    }
    result["binding_sha256"] = hash_json(result)
    if not result["pass"]:
        raise ValueError(f"F4 selected-layout V2 binding failed: {checks}")
    return {**result, "candidate": candidate}


def build_selected_layout_base_targets_v2(
    *,
    candidate: Mapping[str, Any],
    object_poses: Mapping[str, Sequence[float]],
    slot_poses: Mapping[str, Sequence[float]],
    neutral_pose: Sequence[float],
    object_order: Sequence[str],
) -> dict[str, Any]:
    """Build the seven existing segments with one uniform preplace quaternion."""

    order = tuple(object_order)
    if order not in PROGRAM_ORDERS:
        raise ValueError("F4 selected-layout V2 program order changed")
    frozen_candidates = {
        item["candidate_id"]: item for item in preregistered_f4_layout_candidates_v2()
    }
    frozen = frozen_candidates.get(candidate.get("candidate_id"))
    if frozen is None or dict(candidate) != frozen:
        raise ValueError("F4 selected-layout targets require an exact frozen V2 candidate")
    if candidate.get("temporary_waypoint_allowed") is not False or candidate.get(
        "added_waypoints"
    ) != []:
        raise ValueError("F4 selected-layout V2 temporary waypoint is forbidden")
    top_down = build_uniform_f4_top_down_clearance_contract_v6(
        object_poses=object_poses, arm="right"
    )
    if top_down["pass"] is not True:
        raise ValueError("F4 selected-layout V2 top-down source contract failed")
    top_by_role = {item["role"]: item for item in top_down["groups"]}
    groups = []
    flattened = []
    post_derivation = {}
    for role in order:
        group = _build_role_group(
            role=role,
            source_actor_pose=object_poses[role],
            slot_pose=slot_poses[role],
            neutral_pose=neutral_pose,
            top_down_group=top_by_role[role],
        )
        targets = deepcopy(group["targets"])
        base_targets = deepcopy(targets)
        preplace = next(
            item for item in targets if item["segment_id"] == f"{role}_preplace"
        )
        preplace["pose"][3:] = list(candidate["preplace_approach_orientation_wxyz"])
        derived = _interface_derived(role, candidate, targets)
        interface = validate_f4_derivation_interface_v2(
            derived,
            role=role,
            selected_candidate={
                "candidate_id": candidate["candidate_id"],
                "candidate_application_sha256": candidate["candidate_sha256"],
            },
        )
        unchanged = all(
            before == after
            for before, after in zip(base_targets, targets)
            if before["segment_id"] != f"{role}_preplace"
        )
        preplace_before = next(
            item
            for item in base_targets
            if item["segment_id"] == f"{role}_preplace"
        )
        checks = {
            "non_preplace_targets_unchanged": unchanged,
            "preplace_translation_unchanged": preplace_before["pose"][:3]
            == preplace["pose"][:3],
            "preplace_quaternion_exact_candidate": preplace["pose"][3:]
            == candidate["preplace_approach_orientation_wxyz"],
            "exact_seven_segments": len(targets) == 7,
            "interface_v2_pass": interface["pass"] is True,
        }
        post_derivation[role] = {
            "target_pose_sha256": interface["target_pose_sha256"],
            "derivation_interface_receipt_sha256": interface["receipt_sha256"],
            "target_segment_ids": [item["segment_id"] for item in targets],
            "checks": checks,
            "pass": all(checks.values()),
        }
        if not post_derivation[role]["pass"]:
            raise ValueError(f"F4 selected-layout V2 {role} target audit failed")
        group = {
            **group,
            "target_start_index": len(flattened),
            "target_count": len(targets),
            "targets": targets,
            "selected_layout_candidate_id": candidate["candidate_id"],
            "selected_layout_candidate_sha256": candidate["candidate_sha256"],
            "preplace_orientation_audit_v2": post_derivation[role],
        }
        groups.append(group)
        flattened.extend(deepcopy(targets))
    nominal = _audit_nominal_noninterference(
        groups=groups,
        object_poses=object_poses,
        object_order=order,
    )
    result = {
        "schema_version": "cmf_f4_selected_layout_base_targets_v2",
        "route_version": "f4_selected_layout_uniform_preplace_orientation_v2",
        "object_order": list(order),
        "object_target_groups": groups,
        "flattened_targets": flattened,
        "post_derivation_target_audit": post_derivation,
        "post_derivation_target_sha256": hash_json(
            [
                {
                    "role": role,
                    "target_pose_sha256": post_derivation[role][
                        "target_pose_sha256"
                    ],
                }
                for role in order
            ]
        ),
        "nominal_sequential_noninterference": nominal,
        "temporary_waypoint_added": False,
        "pass": nominal["pass"] is True
        and all(item["pass"] for item in post_derivation.values()),
    }
    result["receipt_sha256"] = hash_json(result)
    if not result["pass"]:
        raise ValueError("F4 selected-layout V2 base targets failed")
    return result


def finalize_single_selected_layout_dispatch_v2(
    dispatch: Mapping[str, Any],
    *,
    attempted_candidate_id: str,
    complete_planner_only_pass: bool,
    rendered_segmentation_visibility_pass: bool,
) -> dict[str, Any]:
    expected_search = build_f4_layout_candidate_search_v2()
    expected = build_single_selected_layout_dispatch_v2(expected_search)
    if dict(dispatch) != expected:
        raise ValueError("F4 V2 dispatch contract changed or was tampered")
    if attempted_candidate_id != expected["dispatch_candidate_id"]:
        raise ValueError("F4 V2 later-candidate fallback is forbidden")
    passed = bool(complete_planner_only_pass and rendered_segmentation_visibility_pass)
    result = {
        "schema_version": "cmf_f4_single_selected_layout_terminal_v2",
        "dispatch_contract_sha256": expected["dispatch_contract_sha256"],
        "attempted_candidate_id": attempted_candidate_id,
        "layout_dispatch_count": 1,
        "complete_planner_only_pass": bool(complete_planner_only_pass),
        "rendered_segmentation_visibility_pass": bool(
            rendered_segmentation_visibility_pass
        ),
        "pass": passed,
        "automatic_fallback": False,
        "later_candidate_attempt_allowed": False,
        "next_state": (
            "eligible_for_separately_authorized_development_review"
            if passed
            else "higher_level_task_layout_redesign_required"
        ),
    }
    result["terminal_receipt_sha256"] = hash_json(result)
    return result


__all__ = [
    "ALLOWED_LAYOUT_DIFF_PATHS",
    "DISPATCH_SCHEMA_VERSION",
    "IMPLEMENTATION_VERSION",
    "MAXIMUM_CANDIDATE_COUNT",
    "PROGRAM_ORDERS",
    "SCHEMA_VERSION",
    "SELECTED_EXISTING_CORRIDOR_ID",
    "SELECTED_LAYOUT_SCOPE",
    "audit_f4_layout_candidate_v2",
    "audit_head_camera_frustum_v2",
    "build_f4_layout_candidate_search_v2",
    "build_selected_layout_base_targets_v2",
    "build_single_selected_layout_dispatch_v2",
    "finalize_single_selected_layout_dispatch_v2",
    "preregistered_f4_layout_candidates_v2",
    "validate_f4_layout_candidate_search_v2",
    "validate_selected_layout_runtime_binding_v2",
]
