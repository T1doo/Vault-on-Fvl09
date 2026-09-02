"""CPU contracts for repaired F2 geometry, grasp and controlled insertion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_asset_geometry_layout_v3 import (
    ROLE_ORIENTATION_WXYZ,
    _asset_path,
    _cavity_proposal,
    _collision_geometry,
)
from .f2_official_asset_compatibility_matrix_v3 import ASSET_ROOT
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    matrix_pose,
    obb_inside_local_cavity,
    pose_matrix,
    relative_pose,
)
from .official_raw_pose_generation_v1 import (
    validate_official_raw_pose_receipt_v1,
)


SCHEMA_VERSION = "cmf_f2_inside_control_search_v2"
IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_generation_repair_v2_0"
ARMS = ("left", "right")
OFFICIAL_ROTATION_INDICES = tuple(range(10))
AXIAL_GRASP_OFFSETS_M = (-0.02, 0.0, 0.02)
PREGRASP_DISTANCES_M = (0.06, 0.09, 0.12)
TARGET_DISTANCE_M = 0.0
GRASP_TRANSLATION_DRIFT_LIMIT_M = 0.005
GRASP_ORIENTATION_DRIFT_LIMIT_RAD = 0.050
TRACKING_ALLOCATION_M = 0.005
SAFETY_MARGIN_M = 0.010
PREINSERT_CLEARANCE_M = 0.030
SLOW_RELEASE_TARGETS = (0.2, 0.4, 0.6, 0.8, 1.0)
SLOW_RELEASE_FRAMES_PER_TARGET = 10
QUALIFICATION_MICRO_LIFT_M = 0.025
POST_LIFT_HOLD_FRAMES = 50
GEOMETRY_POSITION_ATOL_M = 1e-6
GEOMETRY_ORIENTATION_ATOL_RAD = 1e-7
DEFAULT_SCREENING_PATH = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/F2_CPU_STATIC_SCREENING_V3.json"
)


def build_f2_controlled_insertion_contract_v2() -> dict[str, Any]:
    value = {
        "schema_version": "cmf_f2_controlled_insertion_cpu_contract_v2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "geometry_certificate_version": "cmf_f2_geometry_certificate_v4",
        "grasp_recipe_axes": {
            "arms": list(ARMS),
            "official_rotation_candidate_indices": list(
                OFFICIAL_ROTATION_INDICES
            ),
            "axial_grasp_offsets_m": list(AXIAL_GRASP_OFFSETS_M),
            "pregrasp_distances_m": list(PREGRASP_DISTANCES_M),
            "official_contact_points": "all available per selected can asset",
        },
        "final_pose_frozen_before_planner": True,
        "post_close_grasp_transform_thresholds": {
            "translation_m": GRASP_TRANSLATION_DRIFT_LIMIT_M,
            "orientation_rad": GRASP_ORIENTATION_DRIFT_LIMIT_RAD,
        },
        "horizontal_margin_formula": {
            "tracking_allocation_m": TRACKING_ALLOCATION_M,
            "grasp_translation_allocation_m": GRASP_TRANSLATION_DRIFT_LIMIT_M,
            "rotational_envelope": "norm(object_half_extents_xy)*sin(0.050 rad)",
            "safety_margin_m": SAFETY_MARGIN_M,
        },
        "two_phase_planning": [
            "exact_final_pregrasp_grasp_and_25mm_qualification_micro_lift",
            "close_and_settle_250",
            "pre_lift_contact_identity_and_initial_transform_gate_table_support_allowed",
            "execute_qualification_micro_lift_and_hold_50",
            "post_lift_off_table_contact_identity_and_transform_drift_gate",
            "rebuild_suffix_from_post_lift_actual_eef_to_actor_transform",
            "plan_lift_preinsert_descend_retreat_neutral",
        ],
        "minimum_planner_queries": {
            "approach_and_qualification": 3,
            "post_lift_suffix": 5,
            "total": 8,
        },
        "runtime_geometry_derivation": {
            "planned_actor_pose_source": "final_grasp_pose_freeze",
            "target_actor_pose_source": "scene+binding+certificate",
            "opening_normal_source": "runtime_box_pose",
            "horizontal_margin_source": "runtime_true_cavity_fit",
            "external_target_pose_opening_normal_or_margin_allowed": False,
            "runtime_asset_metadata_source": "adapter scene construction; independent of certificate",
        },
        "controlled_insertion": {
            "preinsert_clearance_m": PREINSERT_CLEARANCE_M,
            "support_stability_frames_before_open": 50,
            "slow_release_normalized_targets": list(SLOW_RELEASE_TARGETS),
            "frames_per_release_target": SLOW_RELEASE_FRAMES_PER_TARGET,
            "post_release_settle_frames": 250,
            "primary_10cm_gravity_drop": False,
        },
        "legacy_v1_executor_selected_for_dispatch": False,
        "v2_executor_selected_for_dispatch": False,
        "reason_dispatch_inactive": (
            "CPU/code repair only; a reviewed runtime spec and finite attempt "
            "budget are required before dispatch can be activated"
        ),
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


def _vector3(value: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite vector3")
    return result


def _pose7(value: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be one finite pose7")
    norm = float(np.linalg.norm(result[3:]))
    if norm <= 1e-12:
        raise ValueError(f"{label} quaternion norm must be positive")
    result = result.copy()
    result[3:] /= norm
    return result


def build_f2_geometry_certificate_v4(
    *, main_object_model_id: int, plastic_box_model_id: int
) -> dict[str, Any]:
    can = _collision_geometry("071_can", int(main_object_model_id))
    box = _collision_geometry("062_plasticbox", int(plastic_box_model_id))
    cavity = _cavity_proposal(int(plastic_box_model_id))
    can_model_data_path = (
        ASSET_ROOT / "071_can" / f"model_data{int(main_object_model_id)}.json"
    )
    box_model_data_path = (
        ASSET_ROOT
        / "062_plasticbox"
        / f"model_data{int(plastic_box_model_id)}.json"
    )
    can_model_data = json.loads(can_model_data_path.read_text(encoding="utf-8"))
    box_model_data = json.loads(box_model_data_path.read_text(encoding="utf-8"))
    can_collision_path = _asset_path(
        "071_can", int(main_object_model_id), "collision"
    )
    box_collision_path = _asset_path(
        "062_plasticbox", int(plastic_box_model_id), "collision"
    )

    def file_sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def scale(data: Mapping[str, Any]) -> list[float]:
        value = np.asarray(data.get("scale", [1.0, 1.0, 1.0]), dtype=np.float64).reshape(-1)
        if value.size == 1:
            value = np.repeat(value, 3)
        return _vector3(value, "asset scale").tolist()

    value = {
        "schema_version": "cmf_f2_geometry_certificate_v4",
        "implementation_version": IMPLEMENTATION_VERSION,
        "main_object_model_id": int(main_object_model_id),
        "plastic_box_model_id": int(plastic_box_model_id),
        "main_object_collision_path": can["collision_path"],
        "plastic_box_collision_path": box["collision_path"],
        "main_object_model_data_sha256": file_sha(can_model_data_path),
        "plastic_box_model_data_sha256": file_sha(box_model_data_path),
        "main_object_collision_sha256": file_sha(can_collision_path),
        "plastic_box_collision_sha256": file_sha(box_collision_path),
        "main_object_scale": scale(can_model_data),
        "plastic_box_scale": scale(box_model_data),
        "main_object_spawn_orientation_wxyz": ROLE_ORIENTATION_WXYZ[
            "main_object"
        ].tolist(),
        "plastic_box_spawn_orientation_wxyz": ROLE_ORIENTATION_WXYZ[
            "plastic_box"
        ].tolist(),
        "main_object_local_lower_m": can["lower"].tolist(),
        "main_object_local_upper_m": can["upper"].tolist(),
        "main_object_local_center_m": can["center"].tolist(),
        "main_object_local_dimensions_m": can["dimensions"].tolist(),
        "plastic_box_local_lower_m": box["lower"].tolist(),
        "plastic_box_local_upper_m": box["upper"].tolist(),
        "plastic_box_local_center_m": box["center"].tolist(),
        "plastic_box_local_dimensions_m": box["dimensions"].tolist(),
        "cavity_raw_lower_m": cavity["raw_lower"].tolist(),
        "cavity_raw_upper_m": cavity["raw_upper"].tolist(),
        "cavity_center_m": cavity["center"].tolist(),
        "source_of_truth": "scaled collision mesh and model transform used by f2_asset_geometry_layout_v3",
        "runtime_revalidation_required": True,
        "formal_data": False,
        "stage1_authorized": False,
    }
    value["certificate_sha256"] = canonical_hash_json(value)
    return value


def compare_f2_runtime_geometry_v4(
    certificate: Mapping[str, Any], runtime_observation: Mapping[str, Any]
) -> dict[str, Any]:
    cert = canonical_jsonable(certificate)
    payload = dict(cert)
    digest = payload.pop("certificate_sha256", None)
    if digest != canonical_hash_json(payload):
        raise ValueError("F2 V4 geometry certificate hash mismatch")
    runtime = canonical_jsonable(runtime_observation)
    vector_fields = (
        "main_object_scale",
        "plastic_box_scale",
        "main_object_local_lower_m",
        "main_object_local_upper_m",
        "main_object_local_center_m",
        "main_object_local_dimensions_m",
        "plastic_box_local_lower_m",
        "plastic_box_local_upper_m",
        "plastic_box_local_center_m",
        "plastic_box_local_dimensions_m",
        "cavity_raw_lower_m",
        "cavity_raw_upper_m",
        "cavity_center_m",
    )
    errors = {
        field: float(
            np.max(
                np.abs(
                    _vector3(runtime[field], f"runtime {field}")
                    - _vector3(cert[field], f"certificate {field}")
                )
            )
        )
        for field in vector_fields
    }
    checks = {
        "model_ids_match": runtime.get("main_object_model_id")
        == cert["main_object_model_id"]
        and runtime.get("plastic_box_model_id")
        == cert["plastic_box_model_id"],
        "collision_paths_match": runtime.get("main_object_collision_path")
        == cert["main_object_collision_path"]
        and runtime.get("plastic_box_collision_path")
        == cert["plastic_box_collision_path"],
        "asset_hashes_match": all(
            runtime.get(field) == cert[field]
            for field in (
                "main_object_model_data_sha256",
                "plastic_box_model_data_sha256",
                "main_object_collision_sha256",
                "plastic_box_collision_sha256",
            )
        ),
        "all_geometry_vectors_match_1um": all(
            value <= GEOMETRY_POSITION_ATOL_M for value in errors.values()
        ),
        "spawn_orientations_match": all(
            quaternion_angular_error(
                runtime[field], cert[field]
            )
            <= GEOMETRY_ORIENTATION_ATOL_RAD
            for field in (
                "main_object_spawn_orientation_wxyz",
                "plastic_box_spawn_orientation_wxyz",
            )
        ),
    }
    value = {
        "schema_version": "cmf_f2_cpu_runtime_geometry_comparison_v4",
        "certificate_sha256": digest,
        "maximum_absolute_errors_m": errors,
        "position_atol_m": GEOMETRY_POSITION_ATOL_M,
        "orientation_atol_rad": GEOMETRY_ORIENTATION_ATOL_RAD,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "CPU_RUNTIME_GEOMETRY_CERTIFICATE_MISMATCH",
        "pass": all(checks.values()),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def build_f2_runtime_asset_metadata_receipt_v4(
    entity_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    payloads = canonical_jsonable(entity_payloads)
    if not {"main_can", "box"}.issubset(payloads):
        raise ValueError("F2 runtime metadata requires main_can and box entities")
    can = payloads["main_can"]
    box = payloads["box"]
    if can.get("modelname") != "071_can" or box.get("modelname") != "062_plasticbox":
        raise ValueError("F2 runtime entity roles have unexpected asset families")
    can_id = int(can["model_id"])
    box_id = int(box["model_id"])
    can_model = ASSET_ROOT / "071_can" / f"model_data{can_id}.json"
    box_model = ASSET_ROOT / "062_plasticbox" / f"model_data{box_id}.json"
    can_collision = _asset_path("071_can", can_id, "collision")
    box_collision = _asset_path("062_plasticbox", box_id, "collision")
    cavity = _cavity_proposal(box_id)

    def file_sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    resolved_can_collision_sha = file_sha(can_collision)
    resolved_box_collision_sha = file_sha(box_collision)
    checks = {
        "runtime_collision_hashes_match_resolved_assets": can.get(
            "collision_asset_hash"
        )
        == resolved_can_collision_sha
        and box.get("collision_asset_hash") == resolved_box_collision_sha,
        "runtime_scales_are_finite_positive": all(
            np.all(np.isfinite(_vector3(item["scale"], "runtime scale")))
            and np.all(_vector3(item["scale"], "runtime scale") > 0.0)
            for item in (can, box)
        ),
        "runtime_actor_names_present": bool(can.get("actor_name"))
        and bool(box.get("actor_name")),
    }
    value = {
        "schema_version": "cmf_f2_runtime_asset_metadata_receipt_v4",
        "source": "adapter._entity_payloads(scene) plus independently resolved workspace assets",
        "main_object_model_id": can_id,
        "plastic_box_model_id": box_id,
        "main_object_actor_name": can["actor_name"],
        "plastic_box_actor_name": box["actor_name"],
        "main_object_collision_path": str(
            can_collision.relative_to(
                Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin")
            )
        ),
        "plastic_box_collision_path": str(
            box_collision.relative_to(
                Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin")
            )
        ),
        "main_object_model_data_sha256": file_sha(can_model),
        "plastic_box_model_data_sha256": file_sha(box_model),
        "main_object_collision_sha256": resolved_can_collision_sha,
        "plastic_box_collision_sha256": resolved_box_collision_sha,
        "main_object_scale": can["scale"],
        "plastic_box_scale": box["scale"],
        "main_object_spawn_orientation_wxyz": _pose7(
            can["pose"], "runtime can pose"
        )[3:].tolist(),
        "plastic_box_spawn_orientation_wxyz": _pose7(
            box["pose"], "runtime box pose"
        )[3:].tolist(),
        "cavity_raw_lower_m": cavity["raw_lower"].tolist(),
        "cavity_raw_upper_m": cavity["raw_upper"].tolist(),
        "cavity_center_m": cavity["center"].tolist(),
        "checks": checks,
        "pass": all(checks.values()),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_runtime_asset_metadata_receipt_v4(
    receipt: Mapping[str, Any]
) -> dict[str, Any]:
    value = canonical_jsonable(receipt)
    payload = dict(value)
    digest = payload.pop("receipt_sha256", None)
    if (
        value.get("schema_version")
        != "cmf_f2_runtime_asset_metadata_receipt_v4"
        or digest != canonical_hash_json(payload)
        or value.get("pass") is not True
        or not isinstance(value.get("checks"), Mapping)
        or not all(value["checks"].values())
    ):
        raise ValueError("F2 runtime asset metadata receipt is invalid")
    return value


def build_f2_geometry_certificate_inventory_v4(
    screening_path: Path = DEFAULT_SCREENING_PATH,
) -> dict[str, Any]:
    screening = json.loads(Path(screening_path).read_text(encoding="utf-8"))
    rows = screening.get("terminal_cpu_candidate_receipts")
    if not isinstance(rows, list) or len(rows) != 1650:
        raise ValueError("F2 V4 certificate inventory requires all 1,650 rows")
    pairs = sorted(
        {
            (
                int(row["candidate_key"]["main_object_model_id"]),
                int(row["candidate_key"]["plastic_box_model_id"]),
            )
            for row in rows
        }
    )
    if len(pairs) != 66:
        raise ValueError("F2 V4 certificate inventory expected 66 can/box pairs")
    certificates = []
    failures = []
    for can_id, box_id in pairs:
        try:
            certificates.append(
                build_f2_geometry_certificate_v4(
                    main_object_model_id=can_id,
                    plastic_box_model_id=box_id,
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "main_object_model_id": can_id,
                    "plastic_box_model_id": box_id,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
    value = {
        "schema_version": "cmf_f2_geometry_certificate_inventory_v4",
        "implementation_version": IMPLEMENTATION_VERSION,
        "source_screening_sha256": screening.get("screening_sha256"),
        "source_row_count": len(rows),
        "distinct_pair_count": len(pairs),
        "certificate_count": len(certificates),
        "certificate_failures": failures,
        "certificates": certificates,
        "runtime_qualified_pair_count": 0,
        "grasp_recipe_pool_generated": False,
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["inventory_sha256"] = canonical_hash_json(value)
    return value


def build_f2_grasp_recipe_universe_v2(
    geometry_qualified_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    recipes = []
    for pair in canonical_jsonable(geometry_qualified_pairs):
        contact_count = int(pair["official_can_contact_point_count"])
        if contact_count <= 0:
            raise ValueError("F2 pair has no official contact points")
        for arm in ARMS:
            for contact_id in range(contact_count):
                for rotation_index in OFFICIAL_ROTATION_INDICES:
                    for axial_offset in AXIAL_GRASP_OFFSETS_M:
                        for pregrasp_distance in PREGRASP_DISTANCES_M:
                            rank = len(recipes) + 1
                            value = {
                                "rank": rank,
                                "recipe_id": f"f2-final-grasp-v2-r{rank:06d}",
                                "main_object_model_id": int(pair["main_object_model_id"]),
                                "plastic_box_model_id": int(pair["plastic_box_model_id"]),
                                "geometry_certificate_sha256": pair[
                                    "geometry_certificate_sha256"
                                ],
                                "arm": arm,
                                "official_contact_point_id": contact_id,
                                "official_rotation_candidate_index": rotation_index,
                                "axial_grasp_offset_m": axial_offset,
                                "pregrasp_distance_m": pregrasp_distance,
                                "target_distance_m": TARGET_DISTANCE_M,
                                "selection_rule": "rank only after exact final-pose IK/collision/planner and post-close drift gates",
                                "first_planner_success_selection_forbidden": True,
                                "physical_execution_authorized": False,
                            }
                            value["recipe_sha256"] = canonical_hash_json(value)
                            recipes.append(value)
    result = {
        "schema_version": "cmf_f2_grasp_recipe_universe_v2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "pair_count": len(geometry_qualified_pairs),
        "recipe_count": len(recipes),
        "axes": {
            "arms": list(ARMS),
            "official_rotation_candidate_indices": list(OFFICIAL_ROTATION_INDICES),
            "axial_grasp_offsets_m": list(AXIAL_GRASP_OFFSETS_M),
            "pregrasp_distances_m": list(PREGRASP_DISTANCES_M),
        },
        "recipes": recipes,
        "planner_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    result["universe_sha256"] = canonical_hash_json(result)
    return result


def freeze_f2_final_grasp_pose_v2(
    recipe: Mapping[str, Any],
    *,
    raw_pose_generation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    recipe_value = canonical_jsonable(recipe)
    payload = dict(recipe_value)
    digest = payload.pop("recipe_sha256", None)
    if digest != canonical_hash_json(payload):
        raise ValueError("F2 final-grasp recipe hash mismatch")
    raw_validation = validate_official_raw_pose_receipt_v1(
        raw_pose_generation_receipt, recipe_value, family="F2"
    )
    if raw_validation["pass"] is not True:
        raise ValueError("F2 official raw-pose generation receipt is invalid")
    raw_receipt = canonical_jsonable(raw_pose_generation_receipt)
    actor = _pose7(raw_receipt["actor_pose"], "F2 actor")
    pregrasp = _pose7(
        raw_receipt["selected_raw_pregrasp_pose"], "F2 raw pregrasp"
    )
    grasp = _pose7(
        raw_receipt["selected_raw_grasp_pose"], "F2 raw grasp"
    )
    local = np.zeros(3, dtype=np.float64)
    local[1] = float(recipe_value["axial_grasp_offset_m"])
    shift = pose_matrix(actor)[:3, :3] @ local
    final_pregrasp = pregrasp.copy()
    final_grasp = grasp.copy()
    final_pregrasp[:3] += shift
    final_grasp[:3] += shift
    qualification_micro_lift = final_grasp.copy()
    qualification_micro_lift[2] += QUALIFICATION_MICRO_LIFT_M
    goals = {
        "pregrasp": final_pregrasp.tolist(),
        "grasp": final_grasp.tolist(),
        "qualification_micro_lift_25mm": qualification_micro_lift.tolist(),
    }
    value = {
        "schema_version": "cmf_f2_final_grasp_pose_freeze_v2",
        "recipe_id": recipe_value["recipe_id"],
        "recipe_sha256": digest,
        "raw_pose_generation_receipt_sha256": raw_receipt[
            "receipt_sha256"
        ],
        "raw_pose_generation_validation_sha256": raw_validation[
            "validation_sha256"
        ],
        "planned_actor_pose": actor.tolist(),
        "planned_actor_pose_sha256": canonical_hash_json(actor.tolist()),
        "raw_official_pose_hashes": {
            "pregrasp": canonical_hash_json(pregrasp.tolist()),
            "grasp": canonical_hash_json(grasp.tolist()),
        },
        "axial_shift_world_m": shift.tolist(),
        "final_goal_poses": goals,
        "final_goal_pose_hashes": {
            key: canonical_hash_json(pose) for key, pose in goals.items()
        },
        "ordered_final_planner_input_sha256": canonical_hash_json(
            [
                goals["pregrasp"],
                goals["grasp"],
                goals["qualification_micro_lift_25mm"],
            ]
        ),
        "offset_applied_before_planner_qualification": True,
        "post_qualification_pose_mutation_allowed": False,
    }
    value["final_grasp_pose_freeze_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_final_grasp_qualification_v2(
    recipe: Mapping[str, Any],
    freeze: Mapping[str, Any],
    qualification_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    recipe_value = canonical_jsonable(recipe)
    freeze_value = canonical_jsonable(freeze)
    receipt = canonical_jsonable(qualification_receipt)
    receipt_payload = dict(receipt)
    receipt_digest = receipt_payload.pop("receipt_sha256", None)
    checks = {
        "receipt_hash_valid": receipt_digest
        == canonical_hash_json(receipt_payload),
        "recipe_bound": receipt.get("recipe_sha256")
        == recipe_value.get("recipe_sha256"),
        "freeze_bound": receipt.get("final_grasp_pose_freeze_sha256")
        == freeze_value.get("final_grasp_pose_freeze_sha256"),
        "exact_ordered_input_bound": receipt.get(
            "ordered_planner_input_sha256"
        )
        == freeze_value.get("ordered_final_planner_input_sha256"),
        "exact_goal_hashes_bound": receipt.get("goal_pose_hashes")
        == freeze_value.get("final_goal_pose_hashes"),
        "pregrasp_grasp_and_micro_lift_planner_success": receipt.get(
            "planner_statuses"
        )
        == {
            "pregrasp": "Success",
            "grasp": "Success",
            "qualification_micro_lift_25mm": "Success",
        },
        "ik_collision_planner_checked": receipt.get(
            "ik_collision_planner_checked"
        )
        is True,
        "post_qualification_mutation_absent": receipt.get(
            "post_qualification_pose_mutation"
        )
        is False,
    }
    value = {
        "schema_version": "cmf_f2_final_grasp_qualification_validation_v2",
        "recipe_id": recipe_value.get("recipe_id"),
        "checks": checks,
        "pass": all(checks.values()),
        "physical_execution_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def capture_f2_runtime_geometry_observation_v4(scene) -> dict[str, Any]:
    from .family_runners_v3_1 import _actor_local_geometry_bounds, _pose

    metadata = validate_f2_runtime_asset_metadata_receipt_v4(
        getattr(scene, "_cmf_f2_runtime_asset_metadata_receipt_v4", None)
    )
    can_center, can_half = _actor_local_geometry_bounds(scene.can)
    box_center, box_half = _actor_local_geometry_bounds(scene.box)
    can_center = _vector3(can_center, "runtime can local center")
    can_half = _vector3(can_half, "runtime can half extents")
    box_center = _vector3(box_center, "runtime box local center")
    box_half = _vector3(box_half, "runtime box half extents")
    copied = (
        "main_object_model_id",
        "plastic_box_model_id",
        "main_object_collision_path",
        "plastic_box_collision_path",
        "main_object_model_data_sha256",
        "plastic_box_model_data_sha256",
        "main_object_collision_sha256",
        "plastic_box_collision_sha256",
        "main_object_scale",
        "plastic_box_scale",
        "cavity_raw_lower_m",
        "cavity_raw_upper_m",
        "cavity_center_m",
    )
    value = {key: metadata[key] for key in copied}
    value.update(
        {
            "main_object_local_lower_m": (can_center - can_half).tolist(),
            "main_object_local_upper_m": (can_center + can_half).tolist(),
            "main_object_local_center_m": can_center.tolist(),
            "main_object_local_dimensions_m": (2.0 * can_half).tolist(),
            "plastic_box_local_lower_m": (box_center - box_half).tolist(),
            "plastic_box_local_upper_m": (box_center + box_half).tolist(),
            "plastic_box_local_center_m": box_center.tolist(),
            "plastic_box_local_dimensions_m": (2.0 * box_half).tolist(),
            "main_object_spawn_orientation_wxyz": _pose(scene.can)[3:].tolist(),
            "plastic_box_spawn_orientation_wxyz": _pose(scene.box)[3:].tolist(),
        }
    )
    value["runtime_observation_sha256"] = canonical_hash_json(value)
    return value


def derive_f2_runtime_insertion_geometry_v2(
    scene,
    *,
    binding: Mapping[str, Any],
    geometry_certificate: Mapping[str, Any],
    runtime_geometry_gate: Mapping[str, Any],
) -> dict[str, Any]:
    from .family_runners_v3_1 import _actor_local_geometry_bounds, _pose

    if runtime_geometry_gate.get("pass") is not True:
        raise ValueError("F2 runtime insertion geometry requires a matching certificate")
    cert = canonical_jsonable(geometry_certificate)
    key = canonical_jsonable(binding)["selected_candidate_key"]
    if (
        int(key["main_object_model_id"]) != cert["main_object_model_id"]
        or int(key["plastic_box_model_id"]) != cert["plastic_box_model_id"]
    ):
        raise ValueError("F2 binding asset identity differs from geometry certificate")
    can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
    can_local_center = _vector3(can_local_center, "runtime can local center")
    can_half = _vector3(can_half, "runtime can half extents")
    local_center_pose = np.asarray(
        [*can_local_center, 1.0, 0.0, 0.0, 0.0], dtype=np.float64
    )
    cavity = canonical_jsonable(binding)["strict_cavity_contract"]
    box_pose = _pose7(_pose(scene.box), "runtime box pose")
    target_geometry = compose_pose(
        box_pose,
        [
            *cavity["target_center_local_m"],
            *canonical_jsonable(binding)["inside_object_orientation_wxyz"],
        ],
    )
    target_actor = matrix_pose(
        pose_matrix(target_geometry) @ np.linalg.inv(pose_matrix(local_center_pose))
    )
    fit = obb_inside_local_cavity(
        target_geometry,
        can_half,
        box_pose,
        cavity["lower_m"],
        cavity["upper_m"],
    )
    horizontal_axes = (0, 2)
    lower = np.asarray(fit["local_corner_min"], dtype=np.float64)
    upper = np.asarray(fit["local_corner_max"], dtype=np.float64)
    cavity_lower = np.asarray(cavity["lower_m"], dtype=np.float64)
    cavity_upper = np.asarray(cavity["upper_m"], dtype=np.float64)
    signed_horizontal_margin = min(
        *[
            float(lower[axis] - cavity_lower[axis])
            for axis in horizontal_axes
        ],
        *[
            float(cavity_upper[axis] - upper[axis])
            for axis in horizontal_axes
        ],
    )
    opening_normal = pose_matrix(box_pose)[:3, :3] @ np.asarray(
        [0.0, 1.0, 0.0], dtype=np.float64
    )
    value = {
        "schema_version": "cmf_f2_runtime_insertion_geometry_v2",
        "runtime_geometry_gate_sha256": runtime_geometry_gate[
            "receipt_sha256"
        ],
        "geometry_certificate_sha256": cert["certificate_sha256"],
        "binding_sha256": binding["binding_sha256"],
        "target_actor_pose": target_actor.tolist(),
        "target_geometry_center_pose": target_geometry.tolist(),
        "opening_normal_world": opening_normal.tolist(),
        "signed_horizontal_margin_m": signed_horizontal_margin,
        "runtime_true_cavity_fit": fit,
        "all_executor_geometry_internally_derived": True,
        "external_target_or_margin_input_allowed": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def audit_f2_horizontal_margin_budget_v2(
    *, signed_horizontal_margin_m: float, object_half_extents_m: Sequence[float]
) -> dict[str, Any]:
    half = _vector3(object_half_extents_m, "F2 object half extents")
    rotational_envelope = float(
        np.linalg.norm(half[[0, 2]])
        * np.sin(GRASP_ORIENTATION_DRIFT_LIMIT_RAD)
    )
    required = (
        TRACKING_ALLOCATION_M
        + GRASP_TRANSLATION_DRIFT_LIMIT_M
        + rotational_envelope
        + SAFETY_MARGIN_M
    )
    margin = float(signed_horizontal_margin_m)
    value = {
        "schema_version": "cmf_f2_horizontal_margin_budget_v2",
        "signed_horizontal_margin_m": margin,
        "components_m": {
            "tracking_allocation_m": TRACKING_ALLOCATION_M,
            "grasp_translation_allocation_m": GRASP_TRANSLATION_DRIFT_LIMIT_M,
            "orientation_rotational_envelope_m": rotational_envelope,
            "safety_margin_m": SAFETY_MARGIN_M,
        },
        "required_horizontal_margin_m": required,
        "pass": margin + 1e-12 >= required,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def _audit_f2_grasp_transform_v2(
    *,
    planned_eef_pose: Sequence[float],
    planned_actor_pose: Sequence[float],
    actual_eef_pose: Sequence[float],
    actual_actor_pose: Sequence[float],
    selected_contact_continuous: bool,
    selected_actor_identity_continuous: bool,
    actor_table_contact: bool,
    evidence_complete: bool,
    phase: str,
    require_actor_off_table: bool,
) -> dict[str, Any]:
    planned = relative_pose(
        _pose7(planned_eef_pose, "planned EEF"),
        _pose7(planned_actor_pose, "planned actor"),
    )
    actual = relative_pose(
        _pose7(actual_eef_pose, "actual EEF"),
        _pose7(actual_actor_pose, "actual actor"),
    )
    translation = float(np.linalg.norm(actual[:3] - planned[:3]))
    orientation = quaternion_angular_error(actual[3:], planned[3:])
    checks = {
        "translation_drift_within_5mm": translation
        <= GRASP_TRANSLATION_DRIFT_LIMIT_M,
        "orientation_drift_within_50mrad": orientation
        <= GRASP_ORIENTATION_DRIFT_LIMIT_RAD,
        "selected_finger_contact_continuous": bool(selected_contact_continuous),
        "selected_actor_identity_continuous": bool(
            selected_actor_identity_continuous
        ),
        "evidence_complete": bool(evidence_complete),
    }
    if require_actor_off_table:
        checks["actor_off_table_after_lift"] = not bool(actor_table_contact)
    else:
        checks["table_support_allowed_before_lift"] = True
    value = {
        "schema_version": f"cmf_f2_{phase}_grasp_transform_gate_v2",
        "phase": phase,
        "actor_table_contact_observed": bool(actor_table_contact),
        "actor_off_table_required": bool(require_actor_off_table),
        "planned_eef_to_actor_pose": planned.tolist(),
        "actual_eef_to_actor_pose": actual.tolist(),
        "translation_drift_m": translation,
        "orientation_drift_rad": orientation,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else (
            "POST_LIFT_GRASP_NOT_RETAINED"
            if require_actor_off_table
            else "PRE_LIFT_GRASP_NOT_ACQUIRED"
        ),
        "pass": all(checks.values()),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def audit_f2_post_close_grasp_transform_v2(
    **kwargs: Any,
) -> dict[str, Any]:
    """Pre-lift acquisition Gate; normal table support is explicitly allowed."""

    return _audit_f2_grasp_transform_v2(
        **kwargs,
        phase="pre_lift",
        require_actor_off_table=False,
    )


def audit_f2_post_lift_grasp_transform_v2(
    **kwargs: Any,
) -> dict[str, Any]:
    """Post-micro-lift retention Gate; the selected actor must be off-table."""

    return _audit_f2_grasp_transform_v2(
        **kwargs,
        phase="post_lift",
        require_actor_off_table=True,
    )


def build_f2_controlled_insertion_suffix_v2(
    *,
    actual_eef_pose: Sequence[float],
    actual_actor_pose: Sequence[float],
    target_actor_pose: Sequence[float],
    opening_normal_world: Sequence[float],
    neutral_eef_pose: Sequence[float],
    grasp_gate: Mapping[str, Any],
    margin_gate: Mapping[str, Any],
) -> dict[str, Any]:
    if grasp_gate.get("pass") is not True or margin_gate.get("pass") is not True:
        raise ValueError("F2 suffix requires passing grasp-transform and margin gates")
    actual_eef = _pose7(actual_eef_pose, "actual EEF")
    actual_actor = _pose7(actual_actor_pose, "actual actor")
    target_actor = _pose7(target_actor_pose, "target actor")
    normal = _vector3(opening_normal_world, "opening normal")
    norm = float(np.linalg.norm(normal))
    if norm <= 1e-12:
        raise ValueError("F2 opening normal must be nonzero")
    normal /= norm
    preinsert_actor = target_actor.copy()
    preinsert_actor[:3] += PREINSERT_CLEARANCE_M * normal
    lift_eef = actual_eef.copy()
    lift_eef[2] += 0.12
    preinsert_eef = actor_target_to_eef_pose(
        actual_eef, actual_actor, preinsert_actor
    )
    supported_eef = actor_target_to_eef_pose(
        actual_eef, actual_actor, target_actor
    )
    neutral_eef = _pose7(neutral_eef_pose, "neutral EEF")
    targets = [
        {"segment_id": "f2_v2_lift", "pose": lift_eef.tolist()},
        {"segment_id": "f2_v2_preinsert_30mm", "pose": preinsert_eef.tolist()},
        {"segment_id": "f2_v2_controlled_descend_to_support", "pose": supported_eef.tolist()},
        {"segment_id": "f2_v2_retreat_to_preinsert", "pose": preinsert_eef.tolist()},
        {"segment_id": "f2_v2_neutral", "pose": neutral_eef.tolist()},
    ]
    value = {
        "schema_version": "cmf_f2_controlled_insertion_suffix_v2",
        "actual_grasp_transform_receipt_sha256": grasp_gate[
            "receipt_sha256"
        ],
        "margin_budget_receipt_sha256": margin_gate["receipt_sha256"],
        "actual_eef_to_actor_pose": grasp_gate["actual_eef_to_actor_pose"],
        "target_actor_pose": target_actor.tolist(),
        "opening_normal_world": normal.tolist(),
        "targets": targets,
        "targets_sha256": canonical_hash_json(targets),
        "support_stability_gate_before_open": {
            "required": True,
            "frames": 50,
        },
        "slow_release_schedule": [
            {
                "normalized_open_target": target,
                "control_frames": SLOW_RELEASE_FRAMES_PER_TARGET,
            }
            for target in SLOW_RELEASE_TARGETS
        ],
        "post_release_settle_frames": 250,
        "primary_10cm_gravity_drop": False,
        "gravity_drop_diagnostic_authorized": False,
        "suffix_built_from_actual_grasp_transform": True,
        "physical_execution_authorized": False,
    }
    value["suffix_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_controlled_insertion_event_order_v2(
    events: Sequence[str], *, support_gate_pass: bool
) -> dict[str, Any]:
    expected = [
        "post_close_settle_250",
        "pre_lift_grasp_transform_gate",
        "qualification_micro_lift_25mm",
        "post_lift_hold_50",
        "post_lift_grasp_transform_gate",
        "suffix_planned_from_post_lift_actual_transform",
        "lift",
        "preinsert_30mm",
        "controlled_descend_to_support",
        "support_stability_gate_50",
        *[f"slow_release_{index}" for index in range(1, 6)],
        "post_release_settle_250",
        "retreat_neutral",
    ]
    observed = [str(event) for event in events]
    first_release = next(
        (index for index, event in enumerate(observed) if event.startswith("slow_release_")),
        None,
    )
    support_index = (
        observed.index("support_stability_gate_50")
        if "support_stability_gate_50" in observed
        else None
    )
    checks = {
        "exact_event_order": observed == expected,
        "support_gate_pass": bool(support_gate_pass),
        "support_precedes_release": first_release is not None
        and support_index is not None
        and support_index < first_release,
        "five_monotonic_release_steps": observed[10:15]
        == [f"slow_release_{index}" for index in range(1, 6)],
        "gravity_drop_absent": all("gravity_drop" not in event for event in observed),
    }
    value = {
        "schema_version": "cmf_f2_controlled_insertion_event_order_v2",
        "expected_events": expected,
        "observed_events": observed,
        "checks": checks,
        "pass": all(checks.values()),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def expand_legacy_f2_preload_failure_v2(
    *, candidate_id: str, outer_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    outer = canonical_jsonable(outer_receipt)
    physical = outer.get("result", {}).get("physical_result", {})
    preload = physical.get("preload_entry_gate_v11")
    if not isinstance(preload, Mapping) or preload.get("pass") is not False:
        raise ValueError("legacy F2 receipt is not one preload failure")
    checks = canonical_jsonable(preload.get("checks"))
    failed = sorted(key for key, value in checks.items() if value is not True)
    value = {
        "schema_version": "cmf_f2_legacy_preload_failure_expansion_v2",
        "candidate_id": candidate_id,
        "outer_receipt_sha256": outer.get("receipt_sha256"),
        "preload_entry_gate_v11_sha256": preload.get("receipt_sha256"),
        "hard_checks": checks,
        "failed_hard_checks": failed,
        "final_geometry_gate": preload.get("final_geometry_gate"),
        "unintended_contact_count": len(preload.get("unintended_contacts", [])),
        "corrected_status": "GRASP_NOT_ACQUIRED_OR_RETAINED_BEFORE_PRELOAD_ENTRY",
        "broader_asset_family_exhaustion_supported": False,
        "reexecution_required": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "audit_f2_horizontal_margin_budget_v2",
    "audit_f2_post_close_grasp_transform_v2",
    "audit_f2_post_lift_grasp_transform_v2",
    "build_f2_controlled_insertion_suffix_v2",
    "build_f2_controlled_insertion_contract_v2",
    "build_f2_geometry_certificate_v4",
    "build_f2_geometry_certificate_inventory_v4",
    "build_f2_grasp_recipe_universe_v2",
    "capture_f2_runtime_geometry_observation_v4",
    "compare_f2_runtime_geometry_v4",
    "derive_f2_runtime_insertion_geometry_v2",
    "build_f2_runtime_asset_metadata_receipt_v4",
    "validate_f2_runtime_asset_metadata_receipt_v4",
    "expand_legacy_f2_preload_failure_v2",
    "freeze_f2_final_grasp_pose_v2",
    "validate_f2_final_grasp_qualification_v2",
    "validate_f2_controlled_insertion_event_order_v2",
]
