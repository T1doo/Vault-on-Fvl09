"""GPU-preflight contracts for controlled_multi_future_runtime_v3_1.

The module is dependency-light and fail-closed.  It changes implementation and
audit mechanics only; the v1_2 scientific design and 26-D primary action layout
remain unchanged.  GPU probes and Stage 0 are both unauthorized.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import compare_anchors
from .current_hasher import hash_json
from .geometry import actor_target_to_eef_pose, world_axis_offset_pose


DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_1"
ROOT_ORCHESTRATOR_VERSION = "real_sapien_pilot_root_orchestrator_v1_1"
RAW_SCHEMA_VERSION = "cmf_raw_attempt_v2_1_1"
RAW_LAYOUT_VERSION = "controller_effective_setpoint_v1_layout_v2_1"
CURRENT_HASH_VERSION = "current_context_hash_v2"
PHYSICAL_ANCHOR_VERSION = "physical_anchor_v2"
A0_ORCHESTRATOR_VERSION = "A0CurrentAnchorOrchestratorV1_2"
A0_ACTIVITY_SCHEMA_VERSION = "cmf_a0_activity_audit_v2"
REAL_ADAPTER_VERSION = "RoboTwinRealSapienPilotRootAdapterV1_2"
GPU_AUTHORIZATION_SCHEMA_VERSION = "cmf_runtime_v3_1_gpu_authorization_v1_1"
GPU_GUARD_SCHEMA_VERSION = "cmf_gpu_guard_v2_1"
GPU_PROBE_AUTHORIZED = False
STAGE0_AUTHORIZED = False
FORMAL_DATA = False
STAGE0_DATA = False


F1_TARGET_ORDER = ("red", "green", "blue")
F1_IMPLEMENTATION_VERSION = "f1_three_branch_coverage_v3_1"
F1_PREFIX_ID = "f1_cluster_common_pregrasp_v1_1"


def f1_branch_spec_v3_1(target_role: str) -> dict:
    if target_role not in F1_TARGET_ORDER:
        raise ValueError(f"target_role must be one of {F1_TARGET_ORDER}")
    return {
        "program_id": f"F1-{target_role}",
        "target_role": target_role,
        "non_target_roles": [role for role in F1_TARGET_ORDER if role != target_role],
        "arm": "left",
        "container": "062_plasticbox/base3",
        "canonical_prefix_id": F1_PREFIX_ID,
        "target_role_visible_before_prefix_boundary": False,
        "fresh_scene_required": True,
        "neutral_hold_policy": "minimum_boundary_confirmation_only_excluded_extra_frames",
    }


def validate_f1_executed_prefixes(
    branch_receipts: Sequence[Mapping[str, Any]],
    *,
    prefix_end_position_atol: float = 1e-6,
    prefix_end_orientation_atol_rad: float = 1e-6,
    prefix_end_velocity_atol: float = 1e-6,
) -> dict:
    if len(branch_receipts) != 3:
        raise ValueError("F1 v3_1 requires exactly three branch receipts")
    if tuple(item.get("target_role") for item in branch_receipts) != F1_TARGET_ORDER:
        raise ValueError("F1 v3_1 branch order must be red, green, blue")
    prefixes = [item.get("executed_prefix") for item in branch_receipts]
    if not all(isinstance(item, Mapping) for item in prefixes):
        raise ValueError("every F1 branch requires executed-prefix evidence")
    for item in prefixes:
        if item.get("target_role_visible_during_prefix") is not False:
            raise ValueError("F1 target role must remain hidden during actual prefix execution")
        if item.get("neutral_confirmation_step_count") != item.get("neutral_confirmation_minimum_required_steps"):
            raise ValueError("extra neutral hold frames may not extend formal P")
    for key in ("executed_prefix_action_sha256", "executed_prefix_step_count", "canonical_prefix_end_step"):
        values = {item.get(key) for item in prefixes}
        if None in values or len(values) != 1:
            raise ValueError(f"F1 branches must share one actual {key}")
    reference_start = prefixes[0].get("executed_prefix_start_anchor")
    reference_end = prefixes[0].get("executed_prefix_end_anchor")
    if not isinstance(reference_start, Mapping) or not isinstance(reference_end, Mapping):
        raise ValueError("F1 executed prefix requires start/end physical anchors")
    anchor_checks = []
    for item in prefixes:
        start = compare_anchors(
            reference_start,
            item["executed_prefix_start_anchor"],
            position_atol=prefix_end_position_atol,
            orientation_atol_rad=prefix_end_orientation_atol_rad,
            velocity_atol=prefix_end_velocity_atol,
            angular_velocity_atol=prefix_end_velocity_atol,
        )
        end = compare_anchors(
            reference_end,
            item["executed_prefix_end_anchor"],
            position_atol=prefix_end_position_atol,
            orientation_atol_rad=prefix_end_orientation_atol_rad,
            velocity_atol=prefix_end_velocity_atol,
            angular_velocity_atol=prefix_end_velocity_atol,
        )
        anchor_checks.append({"target_role": item.get("target_role"), "start": start, "end": end})
    semantic_pass = [item.get("semantic_probe_pass") is True for item in branch_receipts]
    return {
        "pass": all(semantic_pass) and all(item["start"]["equivalent"] and item["end"]["equivalent"] for item in anchor_checks),
        "actual_prefix_bytes_equal": True,
        "actual_prefix_steps_equal": True,
        "prefix_anchor_checks": anchor_checks,
        "semantic_branch_pass": dict(zip(F1_TARGET_ORDER, semantic_pass)),
    }


F2_IMPLEMENTATION_VERSION = "f2_workspace_reachability_v4_1"
F2_CANDIDATE_IDS = tuple(f"f2_pose_{index}" for index in range(6))


def validate_f2_chained_candidate(result: Mapping[str, Any]) -> dict:
    required_identity = {
        "main_object": "071_can/base1",
        "arm": "left",
        "reference": "074_displaystand/base3",
    }
    for key, expected in required_identity.items():
        if result.get(key) != expected:
            raise ValueError(f"F2 v4_1 identity mismatch: {key}")
    if result.get("candidate_id") not in F2_CANDIDATE_IDS:
        raise ValueError("F2 candidate is not preregistered")
    reset = result.get("planner_reset_receipt")
    if not isinstance(reset, Mapping) or reset.get("reset_performed") is not True:
        raise ValueError("each F2 candidate requires a real planner RNG/state reset receipt")
    for key in ("planner_seed", "rng_state_after_reset_sha256", "planner_instance_id"):
        if reset.get(key) is None:
            raise ValueError(f"F2 planner reset receipt missing {key}")
    for key in (
        "preplace_start_qpos_sha256",
        "preplace_end_qpos_sha256",
        "release_start_qpos_sha256",
        "release_end_qpos_sha256",
    ):
        if not isinstance(result.get(key), str) or not result[key]:
            raise ValueError(f"F2 chained planner receipt missing {key}")
    chain_pass = (
        result.get("chain_continuity_pass") is True
        and result["release_start_qpos_sha256"] == result["preplace_end_qpos_sha256"]
    )
    checks = {
        "planner_reset": True,
        "preplace_planner": result.get("preplace_planner_status") == "Success",
        "release_planner": result.get("release_planner_status") == "Success",
        "chain_continuity": chain_pass,
        "upright_axis": result.get("upright_axis_audited") is True,
        "joint_limit_margin": result.get("joint_limit_margin_pass") is True,
        "carried_swept_geometry": result.get("carried_swept_geometry_pass") is True,
        "facility_distance": result.get("facility_distance_pass") is True,
    }
    return {"verified": all(checks.values()), "checks": checks, **dict(result)}


def select_first_f2_chained_candidate(results: Sequence[Mapping[str, Any]]) -> dict:
    ids = [item.get("candidate_id") for item in results]
    if ids != list(F2_CANDIDATE_IDS[:len(ids)]) or len(results) > len(F2_CANDIDATE_IDS):
        raise ValueError("F2 results must be a fixed-order prefix of six candidates")
    evaluated = [validate_f2_chained_candidate(item) for item in results]
    if evaluated:
        seeds = {item["planner_reset_receipt"]["planner_seed"] for item in evaluated}
        reset_states = {item["planner_reset_receipt"]["rng_state_after_reset_sha256"] for item in evaluated}
        if len(seeds) != 1 or len(reset_states) != 1:
            raise ValueError("F2 candidate queries must reset to one preregistered planner RNG state")
    selected = next((item for item in evaluated if item["verified"]), None)
    return {
        "pass": selected is not None,
        "selected": selected,
        "evaluated": evaluated,
        "terminal_if_exhausted": "f2_stand_layout_impact_review_v5" if len(evaluated) == 6 and selected is None else None,
    }


F3_IMPLEMENTATION_VERSION = "f3_release_dynamics_diagnosis_v3_1"
F3_CORRECTION_VERSION = "f3_deterministic_actor_to_eef_correction_v1"
F3_RELEASE_SAMPLE_POINTS = (
    "before_release",
    "after_release_1",
    "after_release_5",
    "after_release_10",
    "after_release_25",
    "after_release_50",
    "after_release_125",
    "after_release_250",
    "after_rest",
)
F3_REQUIRED_SAMPLE_FIELDS_V3_1 = (
    "sample_step",
    "bottle_position_error_m",
    "bottle_orientation_error_rad",
    "eef_tracking_error_m",
    "eef_tracking_applicable",
    "eef_pose",
    "bottle_pose",
    "target_bottle_pose",
    "commanded_release_eef_pose",
    "bottle_linear_speed_mps",
    "bottle_angular_speed_rps",
    "bottle_footprint_inside_pad",
    "bottle_pad_contact_count",
    "bottle_pad_contact_normals",
    "bottle_pad_contact_impulse",
    "selected_gripper_contact",
    "actual_gripper_joint_qpos",
    "stable_window_pass",
    "support_pass",
)


def classify_f3_release_dynamics_v3_1(
    samples: Mapping[str, Mapping[str, Any]],
    grasp_transform: Mapping[str, Any],
    *,
    position_tolerance_m: float,
    orientation_tolerance_rad: float,
    eef_tracking_tolerance_m: float,
    grasp_translation_drift_tolerance_m: float,
    grasp_orientation_drift_tolerance_rad: float,
) -> dict:
    if tuple(samples) != F3_RELEASE_SAMPLE_POINTS:
        raise ValueError("F3 v3_1 sample points must use the preregistered order")
    for name, sample in samples.items():
        missing_sample_fields = [field for field in F3_REQUIRED_SAMPLE_FIELDS_V3_1 if field not in sample]
        if missing_sample_fields:
            raise ValueError(f"F3 sample {name} missing {missing_sample_fields}")
    required_grasp = (
        "initial_T_eef_actor",
        "before_release_T_eef_actor",
        "grasp_transform_translation_drift",
        "grasp_transform_orientation_drift",
        "grasp_transform_stable",
    )
    missing = [key for key in required_grasp if key not in grasp_transform]
    if missing:
        raise ValueError(f"F3 grasp-transform evidence missing {missing}")
    stable = (
        grasp_transform["grasp_transform_stable"] is True
        and float(grasp_transform["grasp_transform_translation_drift"]) <= grasp_translation_drift_tolerance_m
        and float(grasp_transform["grasp_transform_orientation_drift"]) <= grasp_orientation_drift_tolerance_rad
    )
    before = samples["before_release"]
    final = samples["after_rest"]
    before_accurate = (
        float(before["bottle_position_error_m"]) <= position_tolerance_m
        and float(before["bottle_orientation_error_rad"]) <= orientation_tolerance_rad
    )
    eef_tracking_ok = float(before["eef_tracking_error_m"]) <= eef_tracking_tolerance_m
    final_equivalent = (
        float(final["bottle_position_error_m"]) <= position_tolerance_m
        and float(final["bottle_orientation_error_rad"]) <= orientation_tolerance_rad
        and final.get("bottle_footprint_inside_pad") is True
        and final.get("stable_window_pass") is True
        and final.get("support_pass") is True
    )
    intermediate = [samples[name] for name in F3_RELEASE_SAMPLE_POINTS[1:-1]]
    transient_exceeded = any(
        float(item["bottle_position_error_m"]) > position_tolerance_m
        or float(item["bottle_orientation_error_rad"]) > orientation_tolerance_rad
        for item in intermediate
    )
    if not stable:
        classification = "grasp_slip_or_contact_change"
        next_gate = "grasp_slip_or_contact_impact_review"
        correction_allowed = False
    elif not before_accurate:
        if eef_tracking_ok:
            classification = "pre_release_systematic_offset"
            next_gate = "one_deterministic_actor_to_eef_correction"
            correction_allowed = True
        else:
            classification = "eef_tracking_failure"
            next_gate = "controller_tracking_impact_review"
            correction_allowed = False
    elif final_equivalent:
        classification = "transient_release_dynamics_final_equivalent" if transient_exceeded else "return_equivalence_holds"
        next_gate = "no_repair_needed"
        correction_allowed = False
    else:
        classification = "post_release_final_equivalence_failure"
        next_gate = "pad_initial_pose_physics_impact_review"
        correction_allowed = False
    return {
        "classification": classification,
        "actor_to_eef_correction_allowed": correction_allowed,
        "next_gate": next_gate,
        "grasp_transform_stable": stable,
        "before_release_accurate": before_accurate,
        "eef_tracking_ok": eef_tracking_ok,
        "transient_tolerance_exceeded": transient_exceeded,
        "final_return_equivalence": final_equivalent,
    }


def build_f3_deterministic_correction_spec(
    diagnosis: Mapping[str, Any],
    before_release_sample: Mapping[str, Any],
    *,
    prior_correction_attempt_count: int,
    preplace_height_m: float = 0.10,
) -> dict:
    """Freeze the only permitted correction from measured pre-release poses."""

    if prior_correction_attempt_count != 0:
        raise ValueError("F3 deterministic correction may be created exactly once")
    if (
        diagnosis.get("classification") != "pre_release_systematic_offset"
        or diagnosis.get("actor_to_eef_correction_allowed") is not True
        or diagnosis.get("grasp_transform_stable") is not True
        or diagnosis.get("eef_tracking_ok") is not True
    ):
        raise ValueError("F3 correction Gate is not satisfied")
    required = ("eef_pose", "bottle_pose", "target_bottle_pose", "commanded_release_eef_pose")
    missing = [field for field in required if field not in before_release_sample]
    if missing:
        raise ValueError(f"F3 correction sample missing {missing}")
    eef_pose = np.asarray(before_release_sample["eef_pose"], dtype=np.float64).reshape(7)
    bottle_pose = np.asarray(before_release_sample["bottle_pose"], dtype=np.float64).reshape(7)
    target_bottle_pose = np.asarray(before_release_sample["target_bottle_pose"], dtype=np.float64).reshape(7)
    original_release = np.asarray(before_release_sample["commanded_release_eef_pose"], dtype=np.float64).reshape(7)
    corrected_release = actor_target_to_eef_pose(eef_pose, bottle_pose, target_bottle_pose)
    corrected_preplace = world_axis_offset_pose(corrected_release, float(preplace_height_m))
    payload = {
        "schema_version": "cmf_f3_deterministic_correction_spec_v1",
        "correction_version": F3_CORRECTION_VERSION,
        "prior_correction_attempt_count": 0,
        "maximum_correction_attempt_count": 1,
        "source_classification": diagnosis["classification"],
        "source_before_release_sample_step": before_release_sample.get("sample_step"),
        "measured_eef_pose": eef_pose.tolist(),
        "measured_bottle_pose": bottle_pose.tolist(),
        "target_bottle_pose": target_bottle_pose.tolist(),
        "original_release_eef_pose": original_release.tolist(),
        "corrected_release_eef_pose": corrected_release.tolist(),
        "corrected_preplace_eef_pose": corrected_preplace.tolist(),
        "translation_correction_m": (corrected_release[:3] - original_release[:3]).tolist(),
        "formula": "T_world_eef_corrected = T_world_actor_target @ inverse(T_eef_actor_measured_before_release)",
        "verifier_thresholds_may_be_relaxed": False,
    }
    payload["correction_spec_sha256"] = hash_json(payload)
    return payload


F4_IMPLEMENTATION_VERSION = "f4_segmented_common_carry_v3_1"
F4_ROUTE_ORDER = ("route1_minimum_height_segmented", "route2_carry_neutral_fallback")


def minimum_f4_safe_carry_height(
    obstacle_top_z: Sequence[float],
    *,
    actor_half_height_m: float,
    gripper_below_eef_envelope_m: float,
    frozen_clearance_m: float,
) -> dict:
    tops = np.asarray(obstacle_top_z, dtype=np.float64).reshape(-1)
    values = (actor_half_height_m, gripper_below_eef_envelope_m, frozen_clearance_m)
    if tops.size == 0 or any(float(value) <= 0 for value in values):
        raise ValueError("F4 safe-carry inputs must be positive")
    carried_envelope = max(float(actor_half_height_m), float(gripper_below_eef_envelope_m))
    return {
        "safe_actor_or_gripper_lowest_clearance_z": float(np.max(tops) + frozen_clearance_m),
        "safe_eef_or_actor_center_z": float(np.max(tops) + carried_envelope + frozen_clearance_m),
        "carry_envelope_half_height_m": carried_envelope,
        "carry_envelope_version": "common_x_plus_selected_left_gripper_v1",
    }


def validate_f4_route_results(results: Sequence[Mapping[str, Any]]) -> dict:
    ids = [item.get("route_id") for item in results]
    if ids != list(F4_ROUTE_ORDER[:len(ids)]) or len(results) > 2:
        raise ValueError("F4 route results must follow the frozen Route-1/Route-2 order")
    scene_ids = []
    evaluated = []
    for index, raw in enumerate(results):
        item = dict(raw)
        if item.get("tray_pose_changed") is not False:
            raise ValueError("F4 route may not change tray pose")
        if not isinstance(item.get("scene_instance_id"), str):
            raise ValueError("each F4 route requires a fresh scene_instance_id")
        scene_ids.append(item["scene_instance_id"])
        if item.get("carry_envelope_version") != "common_x_plus_selected_left_gripper_v1":
            raise ValueError("F4 route must audit the combined object/gripper carry envelope")
        segments = item.get("segment_receipts")
        if not isinstance(segments, list) or not segments:
            raise ValueError("F4 route requires ordered segment receipts")
        chain_pass = True
        for segment_index, segment in enumerate(segments):
            for key in ("segment_id", "start_qpos_sha256", "end_qpos_sha256", "planner_status", "executed"):
                if key not in segment:
                    raise ValueError(f"F4 segment missing {key}")
            if segment_index:
                chain_pass = chain_pass and segment["start_qpos_sha256"] == segments[segment_index - 1]["end_qpos_sha256"]
        item["segment_chain_continuity_pass"] = chain_pass
        if index == 1:
            previous = results[0]
            if previous.get("cleanup_pass") is not True:
                raise ValueError("Route 2 is forbidden after Route-1 cleanup uncertainty")
            if previous.get("terminal_status") not in ("failed_planner", "failed_execution", "failed_verifier"):
                raise ValueError("Route 2 requires a terminal non-cleanup Route-1 failure")
        item["verified"] = (
            chain_pass
            and item.get("cleanup_pass") is True
            and item.get("semantic_probe_pass") is True
            and all(segment.get("planner_status") == "Success" and segment.get("executed") is True for segment in segments)
        )
        evaluated.append(item)
    if len(set(scene_ids)) != len(scene_ids):
        raise ValueError("each F4 route must use a distinct fresh scene")
    selected = next((item for item in evaluated if item["verified"]), None)
    return {
        "pass": selected is not None,
        "selected": selected,
        "evaluated": evaluated,
        "terminal_if_exhausted": "f4_tray_layout_impact_review_v4" if len(evaluated) == 2 and selected is None else None,
    }


RUNTIME_V3_1_BUDGET_PROPOSAL = {
    "status": "proposed_for_user_review",
    "approved": False,
    "frozen": False,
    "gpu_probe_authorized": False,
    "A0": {
        "execution_action_count": 0,
        "planner_query_limit": 0,
        "scene_count": 4,
        "scene_pattern": "one_pristine_plus_three_fresh",
        "timeout_seconds": 600,
        "stop_on_failure": True,
    },
    "F1": {"execution_limit": 3, "planner_query_limit_per_branch": 12, "timeout_seconds_per_branch": 1200, "recovery": 0},
    "F2": {"pose_candidate_limit": 6, "execution_limit": 1, "planner_query_limit_total": 16, "timeout_seconds": 1200, "recovery": 0},
    "F3": {"diagnostic_execution_limit": 1, "conditional_correction_execution_limit": 1, "planner_query_limit_per_run": 16, "timeout_seconds_per_run": 1800, "recovery": 0},
    "F4": {"route_limit": 2, "execution_limit_per_route": 1, "planner_query_limit_per_route": 16, "timeout_seconds_per_route": 1800, "recovery": 0},
}
