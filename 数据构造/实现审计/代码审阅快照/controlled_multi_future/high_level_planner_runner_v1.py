"""Fresh-scene planner-only runners for F2/F3/F4 high-level candidates."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_write_json
from .family_runners_v3_1 import (
    BLOCK_HALF_EXTENTS,
    _actor_local_geometry_bounds,
    _arm_original_pose,
    _arm_tag,
    _plan_chain,
    _planner_reset,
    _pose,
)
from .family_runners_v3_3 import (
    _audited_planner_assisted_target_construction,
)
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    matrix_pose,
    obb_inside_local_cavity,
    pose_matrix,
    relative_pose,
    world_axis_offset_pose,
)
from .high_level_runtime_specs_v1 import (
    IMPLEMENTATION_VERSION,
    job_budget_v1,
    validate_f2_runtime_spec_v1,
    validate_f3_runtime_spec_v1,
    validate_f4_runtime_spec_v1,
)
from .project_cube_grasp_pose_v1 import build_project_cube_grasp_poses
from .f4_top_down_block_carry_v8 import (
    TARGET_ORIENTATION_ATOL_RAD,
    TARGET_POSITION_ATOL_M,
    _audit_nominal_noninterference,
)


def _pose7(value: Any, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite pose7")
    return result


def _targets_payload(targets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "segment_id": str(item["segment_id"]),
            "pose": _pose7(item["pose"], str(item["segment_id"])).tolist(),
        }
        for item in targets
    ]


def _planner_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pass": result.get("pass") is True,
        "segment_receipts": deepcopy(result.get("segment_receipts", [])),
        "planner_query_count": int(result.get("planner_query_count", 0)),
        "terminal_qpos": deepcopy(result.get("terminal_qpos")),
        "terminal_qpos_sha256": result.get("terminal_qpos_sha256"),
        "control_count": len(result.get("controls", [])),
        "controls_retained_in_receipt": False,
    }


def _chosen_grasp(
    scene,
    actor,
    *,
    arm: str,
    variant_id: str,
    pregrasp_distance_m: float,
    target_distance_m: float,
    fixed_contact_point_id: int | None,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    fixed = None if fixed_contact_point_id is None else (fixed_contact_point_id,)
    built, audit = _audited_planner_assisted_target_construction(
        scene,
        actor,
        arm=arm,
        variant_id=variant_id,
        callback=lambda: scene.choose_grasp_pose(
            actor,
            arm_tag=_arm_tag(arm),
            pre_dis=float(pregrasp_distance_m),
            target_dis=float(target_distance_m),
            **(
                {}
                if fixed_contact_point_id is None
                else {"contact_point_id": int(fixed_contact_point_id)}
            ),
        ),
        fixed_contact_point_ids=fixed,
    )
    if not isinstance(built, (list, tuple)) or len(built) != 2:
        raise RuntimeError("official grasp target construction returned invalid pair")
    pregrasp = _pose7(built[0], "official pregrasp")
    grasp = _pose7(built[1], "official grasp")
    if audit.get("callback_selected_candidate_planner_status") != "Success":
        raise RuntimeError("official grasp target construction selected no planner-success pose")
    return pregrasp, grasp, audit


def build_f2_stage_a_targets_v1(scene, spec: Mapping[str, Any]):
    candidate = spec["candidate"]
    binding = spec["f2_asset_layout_binding_v3"]
    arm = candidate["arm"]
    pregrasp, grasp, audit = _chosen_grasp(
        scene,
        scene.can,
        arm=arm,
        variant_id=f"f2_hierarchical_stage_a:{candidate['candidate_id']}",
        pregrasp_distance_m=candidate["grasp_pre_distance_m"],
        target_distance_m=candidate["grasp_target_distance_m"],
        fixed_contact_point_id=candidate["official_grasp_contact_point_id"],
    )
    current_actor = _pose(scene.can)
    can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
    local_center_pose = np.asarray(
        [*can_local_center, 1.0, 0.0, 0.0, 0.0], dtype=np.float64
    )
    cavity = binding["strict_cavity_contract"]
    target_geometry = compose_pose(
        _pose(scene.box),
        [
            *cavity["target_center_local_m"],
            *binding["inside_object_orientation_wxyz"],
        ],
    )
    target_actor = matrix_pose(
        pose_matrix(target_geometry) @ np.linalg.inv(pose_matrix(local_center_pose))
    )
    fit = obb_inside_local_cavity(
        target_geometry,
        can_half,
        _pose(scene.box),
        cavity["lower_m"],
        cavity["upper_m"],
    )
    if fit.get("pass_true_cavity_obb") is not True:
        raise RuntimeError("F2 Stage-A strict target actor geometry does not fit cavity")
    release = actor_target_to_eef_pose(grasp, current_actor, target_actor)
    preplace = world_axis_offset_pose(release, 0.16)
    drop_release = world_axis_offset_pose(release, 0.10)
    lift = world_axis_offset_pose(grasp, 0.12)
    rest = _arm_original_pose(scene, arm)
    targets = [
        {"segment_id": "f2_stage_a_pregrasp", "pose": pregrasp},
        {"segment_id": "f2_stage_a_grasp", "pose": grasp},
        {"segment_id": "f2_stage_a_lift_12cm", "pose": lift},
        {"segment_id": "f2_stage_a_inside_preplace_16cm", "pose": preplace},
        {"segment_id": "f2_stage_a_inside_release_10cm", "pose": drop_release},
        {"segment_id": "f2_stage_a_neutral", "pose": rest},
    ]
    return _targets_payload(targets), {
        "target_construction_audit": audit,
        "target_actor_pose": target_actor.tolist(),
        "target_geometry_center_pose": target_geometry.tolist(),
        "strict_full_obb_fit": fit,
        "inside_release_is_10cm_gravity_drop_entry": True,
    }


def _f3_region_shift_world(scene, candidate: Mapping[str, Any]) -> np.ndarray:
    actor_rotation = pose_matrix(_pose(scene.bottle))[:3, :3]
    local = np.zeros(3, dtype=np.float64)
    local[int(candidate["long_axis_model_axis"])] = float(
        candidate["region_center_offset_m"]
    )
    return actor_rotation @ local


def build_f3_level1_targets_v1(scene, spec: Mapping[str, Any]):
    candidate = spec["f3_asset_grasp_tuple_v2"]
    arm = candidate["arm"]
    pregrasp, grasp, audit = _chosen_grasp(
        scene,
        scene.bottle,
        arm=arm,
        variant_id=f"f3_asset_grasp_level1:{candidate['tuple_id']}",
        pregrasp_distance_m=candidate["pregrasp_distance_m"],
        target_distance_m=candidate["target_distance_m"],
        fixed_contact_point_id=candidate["official_contact_point_id"],
    )
    shift = _f3_region_shift_world(scene, candidate)
    pregrasp = pregrasp.copy()
    grasp = grasp.copy()
    pregrasp[:3] += shift
    grasp[:3] += shift
    lift = world_axis_offset_pose(grasp, 0.10)
    central = grasp.copy()
    central[:3] = [0.0, -0.05, 0.95]
    v_positive = world_axis_offset_pose(central, 0.055)
    targets = [
        {"segment_id": "f3_level1_pregrasp", "pose": pregrasp},
        {"segment_id": "f3_level1_grasp", "pose": grasp},
        {"segment_id": "f3_level1_lift", "pose": lift},
        {"segment_id": "f3_level1_central", "pose": central},
        {"segment_id": "f3_level1_one_V", "pose": v_positive},
        {"segment_id": "f3_level1_return", "pose": central},
    ]
    return _targets_payload(targets), {
        "target_construction_audit": audit,
        "grasp_region_world_shift_m": shift.tolist(),
        "one_V_amplitude_m": 0.055,
        "one_V_axis": "+z_table",
    }


def _f4_role_grasp(scene, candidate: Mapping[str, Any], role: str):
    actor = getattr(scene, role.lower())
    arm = candidate["arm"]
    if candidate["grasp_policy"]["policy"] == "project_cube_grasp_pose_v1":
        pregrasp, grasp, contract = build_project_cube_grasp_poses(
            _pose(actor),
            cube_half_extents_m=BLOCK_HALF_EXTENTS,
            arm=arm,
            pregrasp_distance_m=0.09,
        )
        audit = {
            "schema_version": "cmf_f4_project_cube_target_construction_v1",
            "role": role,
            "arm": arm,
            "contract": contract,
            "planner_assisted_batch_call_count": 0,
        }
    else:
        pregrasp, grasp, target_audit = _chosen_grasp(
            scene,
            actor,
            arm=arm,
            variant_id=f"f4_hierarchical_stage_a:{candidate['candidate_id']}:{role}",
            pregrasp_distance_m=0.09,
            target_distance_m=0.0,
            fixed_contact_point_id=None,
        )
        audit = {
            "schema_version": "cmf_f4_f1_derived_target_construction_v1",
            "role": role,
            "arm": arm,
            "target_construction_audit": target_audit,
            "f1_15_of_15_execution_claim_applies": True,
        }
    return pregrasp, grasp, audit


def build_f4_stage_a_targets_v1(scene, spec: Mapping[str, Any]):
    candidate = spec["f4_source_grasp_candidate_v1"]
    arm = candidate["arm"]
    rest = _arm_original_pose(scene, arm)
    neutral = rest.copy()
    neutral[:3] = [-0.11 if arm == "left" else 0.11, 0.02, 0.95]
    targets = []
    audits = {}
    for role in ("A", "B", "C"):
        pregrasp, grasp, audit = _f4_role_grasp(scene, candidate, role)
        lift_mid = world_axis_offset_pose(grasp, 0.04)
        lift = world_axis_offset_pose(grasp, 0.08)
        targets.extend(
            [
                {"segment_id": f"{role}_pregrasp", "pose": pregrasp},
                {"segment_id": f"{role}_grasp", "pose": grasp},
                {"segment_id": f"{role}_lift_mid", "pose": lift_mid},
                {"segment_id": f"{role}_lift", "pose": lift},
                {"segment_id": f"{role}_neutral", "pose": neutral},
            ]
        )
        audits[role] = audit
    return _targets_payload(targets), {
        "role_target_construction_audits": audits,
        "shared_neutral_pose": neutral.tolist(),
        "stage_a_contains_no_slot_target": True,
        "f1_uniform_two_4cm_lifts": True,
    }


def _build_f4_prior_slot_preservation_v1(
    nominal: Mapping[str, Any],
    target_actor_poses: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    per_role = {}
    for index, role in enumerate(("A", "B", "C")):
        evidence = nominal["per_role"][role]
        prior_roles = ("A", "B", "C")[:index]
        comparisons = []
        for prior in prior_roles:
            observed = _pose7(
                evidence["state_of_other_blocks_before_role"][prior],
                f"F4 {role} prior {prior} observed state",
            )
            target = _pose7(
                target_actor_poses[prior],
                f"F4 {role} prior {prior} frozen slot target",
            )
            position_error = float(np.linalg.norm(observed[:3] - target[:3]))
            orientation_error = quaternion_angular_error(
                observed[3:], target[3:]
            )
            comparisons.append(
                {
                    "prior_role": prior,
                    "position_error_m": position_error,
                    "orientation_error_rad": orientation_error,
                    "position_atol_m": TARGET_POSITION_ATOL_M,
                    "orientation_atol_rad": TARGET_ORIENTATION_ATOL_RAD,
                    "pass": position_error <= TARGET_POSITION_ATOL_M
                    and orientation_error <= TARGET_ORIENTATION_ATOL_RAD,
                }
            )
        prior_at_slots = all(item["pass"] for item in comparisons)
        avoids_prior = all(
            prior not in collisions
            for collisions in evidence["segment_non_target_collisions"].values()
            for prior in prior_roles
        )
        per_role[role] = {
            "prior_roles": list(prior_roles),
            "prior_role_pose_comparisons": comparisons,
            "prior_roles_at_frozen_slots": prior_at_slots,
            "transport_avoids_prior_slots": avoids_prior,
            "pass": prior_at_slots and avoids_prior,
        }
    value = {
        "schema_version": "cmf_f4_stage_b_prior_slot_preservation_v1",
        "position_atol_m": TARGET_POSITION_ATOL_M,
        "orientation_atol_rad": TARGET_ORIENTATION_ATOL_RAD,
        "per_role": per_role,
        "pass": nominal.get("pass") is True
        and all(item["pass"] for item in per_role.values()),
        "nominal_only_runtime_contact_audit_still_required": True,
        "raw_quaternion_component_comparison_forbidden": True,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def build_f4_stage_b_targets_v1(scene, spec: Mapping[str, Any]):
    source_candidate = spec["f4_source_grasp_candidate_v1"]
    slot_candidate = spec["f4_stage_b_candidate_v1"]
    arm = source_candidate["arm"]
    rest = _arm_original_pose(scene, arm)
    neutral = rest.copy()
    neutral[:3] = [-0.11 if arm == "left" else 0.11, 0.02, 0.95]
    targets = []
    groups = []
    audits = {}
    target_actor_poses = {}
    role_segment_ids = {}
    for role in ("A", "B", "C"):
        actor = getattr(scene, role.lower())
        source_actor = _pose(actor)
        pregrasp, grasp, audit = _f4_role_grasp(
            scene, source_candidate, role
        )
        lift_mid = world_axis_offset_pose(grasp, 0.04)
        lift = world_axis_offset_pose(grasp, 0.08)
        slot = _pose7(slot_candidate["slot_poses"][role], f"F4 {role} slot")
        target_actor = source_actor.copy()
        target_actor[:3] = slot[:3] + np.asarray(
            [0.0, 0.0, BLOCK_HALF_EXTENTS[2]], dtype=np.float64
        )
        release = actor_target_to_eef_pose(grasp, source_actor, target_actor)
        preplace = world_axis_offset_pose(release, 0.10)
        retreat = preplace.copy()
        carry_mid = lift.copy()
        if slot_candidate["corridor_policy"] == "lower_carry_height":
            carry_mid[:2] = 0.5 * (lift[:2] + preplace[:2])
            carry_mid[2] = max(float(lift[2]), float(preplace[2]))
        elif (
            slot_candidate["corridor_policy"]
            == "f1_uniform_cluster_center_carry_hub"
        ):
            carry_mid[:2] = neutral[:2]
            carry_mid[2] = max(
                float(lift[2]), float(preplace[2]), float(neutral[2])
            )
        else:
            raise ValueError("F4 Stage-B corridor policy changed")
        group_targets = [
            {"segment_id": f"{role}_neutral_start", "pose": neutral},
            {"segment_id": f"{role}_pregrasp", "pose": pregrasp},
            {"segment_id": f"{role}_grasp", "pose": grasp},
            {"segment_id": f"{role}_lift_mid", "pose": lift_mid},
            {"segment_id": f"{role}_lift", "pose": lift},
            {"segment_id": f"{role}_carry_mid", "pose": carry_mid},
            {"segment_id": f"{role}_preplace", "pose": preplace},
            {"segment_id": f"{role}_release", "pose": release},
            {"segment_id": f"{role}_retreat", "pose": retreat},
            {"segment_id": f"{role}_neutral", "pose": neutral},
        ]
        payload = _targets_payload(group_targets)
        targets.extend(payload)
        role_segment_ids[role] = [item["segment_id"] for item in payload]
        target_actor_poses[role] = target_actor.tolist()
        groups.append(
            {
                "role": role,
                "targets": payload,
                "frozen_eef_to_actor_pose": relative_pose(
                    grasp, source_actor
                ).tolist(),
                "target_actor_pose": target_actor.tolist(),
            }
        )
        audits[role] = {
            "target_construction": audit,
            "source_actor_pose": source_actor.tolist(),
            "slot_pose": slot.tolist(),
            "target_actor_pose": target_actor.tolist(),
            "release_eef_pose": release.tolist(),
            "corridor_policy": slot_candidate["corridor_policy"],
        }
    object_poses = {
        role: _pose(getattr(scene, role.lower())).tolist()
        for role in ("A", "B", "C")
    }
    nominal = _audit_nominal_noninterference(
        groups=groups,
        object_poses=object_poses,
        object_order=("A", "B", "C"),
    )
    prior_slot_preservation = _build_f4_prior_slot_preservation_v1(
        nominal, target_actor_poses
    )
    return targets, {
        "role_target_construction_audits": audits,
        "role_target_segment_ids": role_segment_ids,
        "shared_neutral_pose": neutral.tolist(),
        "slot_corridor_candidate_id": slot_candidate["candidate_id"],
        "slot_corridor_candidate_sha256": slot_candidate[
            "candidate_sha256"
        ],
        "corridor_policy": slot_candidate["corridor_policy"],
        "nominal_noninterference": nominal,
        "prior_slot_preservation": prior_slot_preservation,
        "stage_b_planner_only": True,
        "release_execution_count": 0,
    }


def _f4_stage_b_checks(
    planned: Mapping[str, Any],
    target_audit: Mapping[str, Any],
    visibility: Mapping[str, Any],
) -> dict[str, bool]:
    by_id = {
        str(item.get("segment_id")): item
        for item in planned.get("segment_receipts", [])
    }
    checks = {}
    for role in ("A", "B", "C"):
        ids = target_audit["role_target_segment_ids"][role]
        checks[f"complete_{role}_neutral_grasp_slot_neutral"] = all(
            isinstance(by_id.get(segment_id), Mapping)
            and by_id[segment_id].get("planner_status") == "Success"
            for segment_id in ids
        )
    checks.update(
        {
            "rendered_visibility": visibility.get("pass") is True,
            "noninterference": target_audit["nominal_noninterference"].get(
                "pass"
            )
            is True,
            "prior_slot_preservation": target_audit[
                "prior_slot_preservation"
            ].get("pass")
            is True,
        }
    )
    return checks


def rederive_f4_stage_b_candidate_checks_v1(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = deepcopy(dict(result))
    payload = dict(normalized)
    digest = payload.pop("receipt_sha256", None)
    if (
        normalized.get("schema_version")
        != "cmf_high_level_planner_candidate_terminal_v1"
        or normalized.get("purpose") != "f4_stage_b_planner"
        or digest != canonical_hash_json(payload)
        or normalized.get("physical_execution_count") != 0
        or normalized.get("planner_result", {}).get("pass") is not True
        or normalized.get("cleanup_safety_pass") is not True
        or normalized.get("orphan_process_count") != 0
    ):
        raise ValueError("F4 Stage-B source result is not rederivable")
    audit = deepcopy(normalized["target_construction"])
    target_actor_poses = {
        role: audit["role_target_construction_audits"][role][
            "target_actor_pose"
        ]
        for role in ("A", "B", "C")
    }
    corrected_prior = _build_f4_prior_slot_preservation_v1(
        audit["nominal_noninterference"], target_actor_poses
    )
    audit["prior_slot_preservation"] = corrected_prior
    checks = _f4_stage_b_checks(
        normalized["planner_result"],
        audit,
        normalized["rendered_visibility"],
    )
    value = {
        "schema_version": "cmf_f4_stage_b_candidate_check_overlay_v1",
        "source_result_receipt_sha256": digest,
        "candidate_id": normalized["candidate_id"],
        "candidate_sha256": normalized["candidate_sha256"],
        "original_checks": deepcopy(normalized.get("checks")),
        "corrected_prior_slot_preservation": corrected_prior,
        "checks": checks,
        "cleanup_safety_pass": True,
        "orphan_process_count": 0,
        "physical_execution_count": 0,
        "pass": all(checks.values()),
        "reexecution_required": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


class HighLevelPlannerRunnerV1:
    def __init__(self, adapter):
        self.adapter = adapter

    def run(self, *, output_dir: Path, planned_spec: Mapping[str, Any]) -> dict[str, Any]:
        family = str(planned_spec.get("family"))
        if family == "F2":
            spec = validate_f2_runtime_spec_v1(planned_spec)
            if spec["purpose"] != "f2_stage_a_planner":
                raise ValueError("planner runner received non-planner F2 purpose")
            builder = build_f2_stage_a_targets_v1
            trace_actor_name = "can"
        elif family == "F3":
            spec = validate_f3_runtime_spec_v1(planned_spec)
            if spec["purpose"] != "f3_level1_planner":
                raise ValueError("planner runner received non-planner F3 purpose")
            builder = build_f3_level1_targets_v1
            trace_actor_name = "bottle"
        elif family == "F4":
            spec = validate_f4_runtime_spec_v1(planned_spec)
            if spec["purpose"] not in {
                "f4_stage_a_planner",
                "f4_stage_b_planner",
            }:
                raise ValueError("planner runner received non-planner F4 purpose")
            builder = (
                build_f4_stage_a_targets_v1
                if spec["purpose"] == "f4_stage_a_planner"
                else build_f4_stage_b_targets_v1
            )
            trace_actor_name = "a"
        else:
            raise ValueError("planner runner family must be F2, F3, or F4")
        if self.adapter.planned_spec != spec:
            raise ValueError("planner runner adapter/spec binding mismatch")
        budget = job_budget_v1(spec["purpose"])
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        context = self.adapter.scene(
            spec,
            phase=f"{spec['purpose']}:{spec['slot_id']}",
            program=None,
        )
        scene = None
        receipt: dict[str, Any] = {
            "schema_version": "cmf_high_level_planner_candidate_terminal_v1",
            "implementation_version": IMPLEMENTATION_VERSION,
            "family": family,
            "purpose": spec["purpose"],
            "slot_id": spec["slot_id"],
            "planned_scope_spec_sha256": spec["planned_scope_spec_sha256"],
            "budget_receipt_sha256": budget["budget_receipt_sha256"],
            "candidate_id": (
                spec["candidate"]["candidate_id"]
                if family == "F2"
                else spec["f3_asset_grasp_tuple_v2"]["tuple_id"]
                if family == "F3"
                else (
                    spec["f4_stage_b_candidate_v1"]["candidate_id"]
                    if spec["purpose"] == "f4_stage_b_planner"
                    else spec["f4_source_grasp_candidate_v1"]["candidate_id"]
                )
            ),
            "candidate_sha256": (
                spec["candidate_sha256"]
                if family == "F2"
                else spec["f3_asset_grasp_tuple_sha256"]
                if family == "F3"
                else (
                    spec["f4_stage_b_candidate_sha256"]
                    if spec["purpose"] == "f4_stage_b_planner"
                    else spec["f4_source_grasp_candidate_sha256"]
                )
            ),
            "arm": spec["arm"],
            "fresh_scene_count": 0,
            "physical_execution_count": 0,
            "planner_query_count": 0,
            "status": "running",
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        try:
            with context as handle:
                scene = handle.scene
                receipt["fresh_scene_count"] = 1
                receipt["current"] = self.adapter.capture_current(scene)
                if family == "F4":
                    render_binding = getattr(
                        scene, "_cmf_render_device_binding_v1", None
                    )
                    if (
                        not isinstance(render_binding, Mapping)
                        or render_binding.get("pass") is not True
                    ):
                        raise RuntimeError(
                            "F4 scene lacks selected render-device binding"
                        )
                    receipt["render_device_binding"] = deepcopy(render_binding)
                    visibility = self.adapter.audit_current_rendered_visibility(
                        scene, phase=spec["purpose"]
                    )
                    receipt["rendered_visibility"] = visibility
                    if (
                        spec["purpose"] == "f4_stage_a_planner"
                        and visibility.get("pass") is not True
                    ):
                        raise RuntimeError("F4 Stage-A rendered visibility failed")
                trace_actor = getattr(scene, trace_actor_name)
                scene.initialize_trace(
                    trace_actor, spec["arm"], role_actors=scene.role_actors
                )
                scene.planner_query_limit = int(budget["planner_query_limit"])
                targets, target_audit = builder(scene, spec)
                reset = _planner_reset(
                    scene,
                    planner_seed=20260829,
                    variant_id=f"high_level_planner:{spec['slot_id']}",
                    arm=spec["arm"],
                )
                planned = _plan_chain(
                    scene,
                    targets,
                    query_limit=int(budget["planner_query_limit"]),
                    arm=spec["arm"],
                )
                receipt["targets"] = targets
                receipt["target_construction"] = target_audit
                receipt["planner_reset_receipt"] = reset
                receipt["planner_result"] = _planner_payload(planned)
                receipt["planner_query_count"] = int(scene.planner_query_count)
                if family == "F4" and spec["purpose"] == "f4_stage_b_planner":
                    receipt["checks"] = _f4_stage_b_checks(
                        planned, target_audit, receipt["rendered_visibility"]
                    )
                receipt["status"] = (
                    "planner_candidate_pass"
                    if planned.get("pass") is True
                    and (
                        family != "F4"
                        or spec["purpose"] != "f4_stage_b_planner"
                        or all(receipt["checks"].values())
                    )
                    else "planner_candidate_failed"
                )
        except BaseException as exc:
            receipt["status"] = "planner_candidate_failed_execution_or_infrastructure"
            receipt["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            if scene is not None:
                receipt["planner_query_count"] = int(
                    getattr(scene, "planner_query_count", 0)
                )
        cleanup = context.cleanup_receipt
        receipt["cleanup"] = cleanup
        receipt["cleanup_safety_pass"] = (
            isinstance(cleanup, Mapping)
            and cleanup.get("cleanup_safety_pass") is True
            and int(cleanup.get("orphan_process_count", -1)) == 0
        )
        receipt["orphan_process_count"] = (
            int(cleanup.get("orphan_process_count", -1))
            if isinstance(cleanup, Mapping)
            else -1
        )
        receipt["budget_checks"] = {
            "fresh_scene_within_limit": receipt["fresh_scene_count"]
            <= budget["fresh_scene_limit"],
            "planner_queries_within_limit": receipt["planner_query_count"]
            <= budget["planner_query_limit"],
            "physical_execution_zero": receipt["physical_execution_count"] == 0,
        }
        if not receipt["cleanup_safety_pass"]:
            receipt["status"] = "planner_candidate_failed_cleanup_uncertain"
        receipt["pass"] = (
            receipt["status"] == "planner_candidate_pass"
            and receipt["cleanup_safety_pass"]
            and all(receipt["budget_checks"].values())
        )
        receipt["elapsed_seconds"] = time.time() - started
        receipt["receipt_sha256"] = canonical_hash_json(receipt)
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        return receipt


__all__ = [
    "HighLevelPlannerRunnerV1",
    "_build_f4_prior_slot_preservation_v1",
    "build_f2_stage_a_targets_v1",
    "build_f3_level1_targets_v1",
    "build_f4_stage_a_targets_v1",
    "build_f4_stage_b_targets_v1",
    "rederive_f4_stage_b_candidate_checks_v1",
]
