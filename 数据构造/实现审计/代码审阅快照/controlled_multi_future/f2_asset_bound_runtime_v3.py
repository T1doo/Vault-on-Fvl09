"""Asset-bound real SAPIEN/CuRobo controller and adapter for F2 redesign V3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .f2_beside_historical_safe_route_v4 import actor_origin_z_for_table_support
from .f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    validate_frozen_asset_layout_binding_v3,
)
from .family_runners_v3_3 import (
    F2ControllerV3_3,
    F2FrozenLayoutConfigurationError,
    _actor_local_geometry_bounds,
    _arm_eef_pose,
    _cache_suffix_controls,
    _entity,
    _pose,
)
from .geometry import (
    actor_target_to_eef_pose,
    compose_pose,
    matrix_pose,
    obb_inside_local_cavity,
    pose_matrix,
    world_axis_offset_pose,
)
from .real_sapien_adapter_v1_2 import _asset_hash_v1_2
from .real_sapien_adapter_v1_3 import RoboTwinRealSapienStrictPrefixAdapterV1_3
from .runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS


ADAPTER_VERSION = "RoboTwinRealSapienF2AssetBoundAdapterV3"
IMPLEMENTATION_VERSION = "controlled_multi_future_f2_asset_redesign_v3"
PLANNER_ONLY_STOP_SCHEMA = "cmf_f2_asset_bound_planner_only_stop_v3"


def _hash_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _actor_pose_centered_on_support(
    *,
    target_geometry_xy,
    support_plane_z_m: float,
    orientation_wxyz,
    local_geometry_center_m,
    half_extents_m,
) -> np.ndarray:
    orientation = np.asarray(orientation_wxyz, dtype=np.float64).reshape(4)
    actor_z = actor_origin_z_for_table_support(
        table_plane_z_m=float(support_plane_z_m),
        actor_quaternion_wxyz=orientation,
        can_local_geometry_center_m=local_geometry_center_m,
        can_half_extents_m=half_extents_m,
    )
    actor = np.asarray(
        [*np.asarray(target_geometry_xy, dtype=np.float64).reshape(2), actor_z, *orientation],
        dtype=np.float64,
    )
    realized_center = compose_pose(
        actor,
        [*np.asarray(local_geometry_center_m, dtype=np.float64), 1.0, 0.0, 0.0, 0.0],
    )
    actor[:2] += np.asarray(target_geometry_xy, dtype=np.float64) - realized_center[:2]
    return actor


def _actual_inside_route(
    *, scene, binding: Mapping[str, Any], current_eef, current_actor, rest
) -> dict[str, Any]:
    cavity = binding["strict_cavity_contract"]
    can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
    local_center_pose = np.asarray(
        [*can_local_center, 1.0, 0.0, 0.0, 0.0], dtype=np.float64
    )
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
    release = actor_target_to_eef_pose(current_eef, current_actor, target_actor)
    drop_release = world_axis_offset_pose(release, 0.10)
    retreat = world_axis_offset_pose(release, 0.16)
    pre_release_actor = world_axis_offset_pose(target_actor, 0.10)
    route = {
        "schema_version": "cmf_f2_asset_bound_inside_route_v3",
        "relation": "inside",
        "main_object": (
            f"071_can/base{binding['selected_candidate_key']['main_object_model_id']}"
        ),
        "arm": "left",
        "reference": (
            f"062_plasticbox/base{binding['selected_candidate_key']['plastic_box_model_id']}"
        ),
        "target_actor_pose": target_actor.tolist(),
        "target_geometry_center_pose": target_geometry.tolist(),
        "pre_release_actor_pose": pre_release_actor.tolist(),
        "release_target_index": 0,
        "settle_steps": 250,
        "sample_steps": [1, 5, 10, 25, 50, 125, 250],
        "targets": [
            {"segment_id": "inside_drop_release_10cm", "pose": drop_release.tolist()},
            {"segment_id": "inside_retreat_16cm", "pose": retreat.tolist()},
            {"segment_id": "f2_rest", "pose": np.asarray(rest).tolist()},
        ],
        "final_target_fit": fit,
        "cavity_contract": dict(cavity),
        "inside_full_obb_verifier_relaxed": False,
        "release_gate_version": "f2_release_safety_then_final_inside_v10",
    }
    route["audit"] = {
        "checks": {
            "actual_actor_geometry": True,
            "full_obb_inside_strict_cavity": fit["pass_true_cavity_obb"] is True,
            "left_arm_fixed": True,
            "release_verifier_unchanged": True,
        },
        "pass": fit["pass_true_cavity_obb"] is True,
    }
    route["receipt_sha256"] = _hash_json(route)
    return route


def _actual_beside_route(
    *, scene, binding: Mapping[str, Any], current_eef, current_actor, rest
) -> dict[str, Any]:
    layout = binding["layout_payload"]
    target_xy = np.asarray(layout["beside_candidate_xy_m"][0], dtype=np.float64)
    can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
    orientation = np.asarray(layout["main_object_orientation_wxyz"], dtype=np.float64)
    target_actor = _actor_pose_centered_on_support(
        target_geometry_xy=target_xy,
        support_plane_z_m=0.74 + float(scene.table_z_bias),
        orientation_wxyz=orientation,
        local_geometry_center_m=can_local_center,
        half_extents_m=can_half,
    )
    release = actor_target_to_eef_pose(current_eef, current_actor, target_actor)
    preplace = world_axis_offset_pose(release, 0.08)
    hub = preplace.copy()
    hub[:2] = (current_eef[:2] + preplace[:2]) / 2.0
    hub[2] = max(float(current_eef[2]), float(preplace[2]))
    targets = [
        {"segment_id": "beside_asset_bound_carry_hub", "pose": hub.tolist()},
        {"segment_id": "beside_asset_bound_preplace", "pose": preplace.tolist()},
        {"segment_id": "beside_asset_bound_release", "pose": release.tolist()},
        {"segment_id": "beside_asset_bound_retreat", "pose": preplace.tolist()},
        {"segment_id": "beside_asset_bound_carry_hub_return", "pose": hub.tolist()},
        {"segment_id": "f2_rest", "pose": np.asarray(rest).tolist()},
    ]
    stand_xy = _pose(scene.stand)[:2]
    radial = float(np.linalg.norm(target_xy - stand_xy))
    passed = 0.12 <= radial <= 0.23
    route = {
        "schema_version": "cmf_f2_asset_bound_beside_route_v3",
        "relation": "beside",
        "main_object": (
            f"071_can/base{binding['selected_candidate_key']['main_object_model_id']}"
        ),
        "arm": "left",
        "reference": (
            f"074_displaystand/base{binding['selected_candidate_key']['beside_reference_model_id']}"
        ),
        "target_actor_pose": target_actor.tolist(),
        "release_target_index": 2,
        "targets": targets,
        "actual_actor_geometry_used": True,
        "candidate_search_enabled": False,
        "strict_final_relation_verifier_relaxed": False,
        "audit": {
            "radial_distance_m": radial,
            "asset_bound_mutual_exclusion_receipt_required": True,
            "pass": passed,
        },
    }
    route["receipt_sha256"] = _hash_json(route)
    return route


def _asset_bound_identity_tracking_contract_v3(
    *, program_id: str, targets, binding_sha256: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    values = [
        {
            "segment_id": str(item["segment_id"]),
            "pose": np.asarray(item["pose"], dtype=np.float64).reshape(7).tolist(),
        }
        for item in targets
    ]
    receipt = {
        "schema_version": "cmf_f2_asset_bound_identity_tracking_contract_v3",
        "program_id": program_id,
        "selected_binding_sha256": binding_sha256,
        "target_segment_ids": [item["segment_id"] for item in values],
        "target_poses": [item["pose"] for item in values],
        "changed_target_indices": [],
        "historical_r7_r8_fixed_asset_compensation_reused": False,
        "online_compensation_or_search": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    receipt["receipt_sha256"] = _hash_json(receipt)
    return values, receipt


def _asset_bound_balanced_preload_spec_v3(binding: Mapping[str, Any], **kwargs) -> dict[str, Any]:
    qpos = np.asarray(kwargs["actual_finger_qpos"], dtype=np.float64).reshape(2)
    if not np.all(np.isfinite(qpos)):
        raise ValueError("F2 asset-bound preload qpos is non-finite")
    modes = [str(value) for value in kwargs["drive_mode"]]
    if modes != ["force", "force"]:
        raise ValueError("F2 asset-bound preload requires force-mode drives")
    lower, upper = -0.01, 0.045
    balanced = float(np.mean(qpos))
    normalized = (balanced - lower) / (upper - lower)
    if not 0.0 < normalized < 1.0:
        raise ValueError("F2 asset-bound balanced preload is outside (0,1)")
    value = {
        "schema_version": "cmf_f2_asset_bound_balanced_preload_release_v3",
        "release_version": "f2_inside_two_stage_balanced_preload_release_v9_numeric_semantics",
        "selected_binding_sha256": binding["binding_sha256"],
        "main_object": (
            f"071_can/base{binding['selected_candidate_key']['main_object_model_id']}"
        ),
        "arm": "left",
        "relation": "inside",
        "actual_finger_qpos_m": qpos.tolist(),
        "current_drive_target_m": np.asarray(
            kwargs["current_drive_target"], dtype=np.float64
        ).reshape(2).tolist(),
        "applied_finger_qf": np.asarray(
            kwargs["applied_finger_qf"], dtype=np.float64
        ).reshape(2).tolist(),
        "estimated_drive_effort_audit_only": np.asarray(
            kwargs["estimated_drive_effort"], dtype=np.float64
        ).reshape(2).tolist(),
        "drive_stiffness": np.asarray(kwargs["drive_stiffness"], dtype=np.float64).reshape(2).tolist(),
        "drive_damping": np.asarray(kwargs["drive_damping"], dtype=np.float64).reshape(2).tolist(),
        "drive_force_limit": np.asarray(kwargs["drive_force_limit"], dtype=np.float64).reshape(2).tolist(),
        "drive_mode": modes,
        "gripper_scale_m": [lower, upper],
        "balanced_drive_target_m": balanced,
        "partial_open_normalized_target": normalized,
        "expected_balanced_joint_targets_m": [balanced, balanced],
        "formula": "mean(actual selected-finger qpos), then normalize by (-0.01,0.045)",
        "post_command_hold_steps": 50,
        "stable_window_frames": 50,
        "disengagement_confirm_frames": 10,
        "candidate_search": False,
        "fallback": False,
        "online_parameter_search": False,
        "final_verifier_changed": False,
        "final_verifier_threshold_changed": False,
        "historical_base1_failure_evidence_reused_as_asset_evidence": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["receipt_sha256"] = _hash_json(value)
    return value


class F2AssetBoundControllerV3(F2ControllerV3_3):
    family = "F2"
    arm = "left"

    def __init__(self, binding: Mapping[str, Any], *, planner_only: bool):
        self.binding = validate_frozen_asset_layout_binding_v3(binding)
        if self.binding["selected_execution_arm"] != "left":
            raise ValueError("current F2 asset-bound runtime scope is left-arm only")
        self.planner_only = bool(planner_only)
        if self.binding.get("provisional_dynamic_candidate") is True and not self.planner_only:
            raise ValueError("provisional F2 candidate binding is planner-only")
        if not self.planner_only and self.binding.get("selected") is not True:
            raise ValueError("F2 execution requires a final selected binding")

    def _bind_scene(self, scene) -> None:
        actual = getattr(scene, "_cmf_f2_asset_binding_v3", None)
        if not isinstance(actual, Mapping) or actual.get("binding_sha256") != self.binding["binding_sha256"]:
            raise F2FrozenLayoutConfigurationError("F2 scene lacks the selected asset binding")
        scene._cmf_f2_active_cavity_contract = dict(
            self.binding["strict_cavity_contract"]
        )
        scene._cmf_f2_scale_support_half_xy_m = list(
            self.binding["layout_payload"]["on_region_half_xy_m"]
        )
        scene._cmf_f2_balanced_preload_spec_builder = lambda **kwargs: (
            _asset_bound_balanced_preload_spec_v3(self.binding, **kwargs)
        )
        scene.f2_asset_binding_identity = {
            "binding_sha256": self.binding["binding_sha256"],
            "main_object_model_id": self.binding["selected_candidate_key"][
                "main_object_model_id"
            ],
            "execution_arm": "left",
        }

    def _require_layout_v2(self, scene, *, require_dynamic_stability=False):
        self._bind_scene(scene)
        layout = self.binding["layout_payload"]
        expected = {
            "can": layout["main_object_pose_xyz"],
            "box": layout["facility_pose_xyz"]["plastic_box"],
            "scale": layout["facility_pose_xyz"]["electronic_scale"],
            "stand": layout["facility_pose_xyz"]["beside_reference"],
        }
        checks = {
            role: bool(
                np.allclose(
                    _pose(getattr(scene, role))[:3],
                    np.asarray(xyz, dtype=np.float64),
                    atol=2e-5,
                    rtol=0.0,
                )
            )
            for role, xyz in expected.items()
        }
        if not all(checks.values()):
            raise F2FrozenLayoutConfigurationError(
                f"F2 asset-bound realized layout differs: {checks}"
            )
        return {
            "layout_version": self.binding["layout_version"],
            "layout_sha256": self.binding["layout_payload_sha256"],
            "checks": checks,
            "dynamic_post_settle_gate_applied": False,
        }

    def canonical_prefix_contract(self, programs):
        if [item.get("program_id") for item in programs] != list(PROGRAM_IDS):
            raise ValueError("F2 asset-bound prefix received changed programs")
        return {
            "prefix_id": "f2_asset_bound_same_object_grasp_lift_v3",
            "family": "F2",
            "arm": "left",
            "ops": ["pregrasp", "grasp", "close", "lift_12cm"],
            "main_object": (
                f"071_can/base{self.binding['selected_candidate_key']['main_object_model_id']}"
            ),
            "selected_binding_sha256": self.binding["binding_sha256"],
            "target_role_read": False,
            "settling_excluded_from_semantic_P": True,
        }

    def audit_task_physical_feasibility(self, scene, program):
        try:
            layout = self._require_layout_v2(scene)
            current_eef = _arm_eef_pose(scene, "left")
            current_actor = _pose(scene.can)
            rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
            inside_route = _actual_inside_route(
                scene=scene,
                binding=self.binding,
                current_eef=current_eef,
                current_actor=current_actor,
                rest=rest,
            )
            roles = set(scene.role_actors) == {"main_can", "box", "scale", "stand"}
            scale_point = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
            checks = {
                "roles": roles,
                "poses_finite": all(np.all(np.isfinite(_pose(actor))) for actor in scene.role_actors.values()),
                "program": program.get("program_id") in PROGRAM_IDS,
                "inside_actual_geometry": inside_route["audit"]["pass"] is True,
                "scale_functional_point": scale_point.size >= 3
                and np.all(np.isfinite(scale_point[:3])),
                "binding_layout": all(layout["checks"].values()),
                "left_arm_fixed": True,
            }
            passed = all(checks.values())
            return {
                "task_feasible": passed,
                "physical_feasible": passed,
                "planner_solvable": None,
                "failure_type": None if passed else "f2_asset_bound_task_physical_gate_v3",
                "evidence": checks,
            }
        except Exception as exc:
            return {
                "task_feasible": False,
                "physical_feasible": False,
                "planner_solvable": None,
                "failure_type": type(exc).__name__,
                "evidence": {"error": str(exc)},
            }

    def plan_and_execute_canonical_prefix(self, scene, prefix_contract, *, capture_anchor):
        self._bind_scene(scene)
        return super().plan_and_execute_canonical_prefix(
            scene, prefix_contract, capture_anchor=capture_anchor
        )

    def validate_replayed_prefix_physical(self, scene, replay):
        self._bind_scene(scene)
        return super().validate_replayed_prefix_physical(scene, replay)

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        self._bind_scene(scene)
        relation = program["steps"][1]["relation"]
        current_eef = _arm_eef_pose(scene, "left")
        current_actor = _pose(scene.can)
        rest = np.asarray(scene.robot.left_original_pose, dtype=np.float64)
        extra: dict[str, Any]
        if relation == "inside":
            route = _actual_inside_route(
                scene=scene,
                binding=self.binding,
                current_eef=current_eef,
                current_actor=current_actor,
                rest=rest,
            )
            if route["audit"]["pass"] is not True:
                raise ValueError("F2 asset-bound inside route audit failed")
            targets, compensation = _asset_bound_identity_tracking_contract_v3(
                program_id=program["program_id"],
                targets=route["targets"],
                binding_sha256=self.binding["binding_sha256"],
            )
            scene._cmf_f2_inside_xy_tracking_compensation_v8 = compensation
            extra = {
                "relation": "inside",
                "variant_id": "inside_asset_bound_actual_geometry_v3",
                "target_actor_pose": route["target_actor_pose"],
                "release_target_index": route["release_target_index"],
                "inside_gravity_drop_route": route,
                "inside_xy_tracking_compensation_v8": compensation,
                "asset_bound_identity_tracking_contract_v3": compensation,
                "inside_full_obb_verifier_relaxed": False,
            }
        elif relation == "on":
            can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
            scale_point = np.asarray(
                scene.scale.get_functional_point(0), dtype=np.float64
            )
            target_actor = _actor_pose_centered_on_support(
                target_geometry_xy=scale_point[:2],
                support_plane_z_m=float(scale_point[2]),
                orientation_wxyz=self.binding["layout_payload"][
                    "main_object_orientation_wxyz"
                ],
                local_geometry_center_m=can_local_center,
                half_extents_m=can_half,
            )
            release = actor_target_to_eef_pose(current_eef, current_actor, target_actor)
            preplace = world_axis_offset_pose(release, 0.10)
            targets = [
                {"segment_id": "on_asset_bound_preplace", "pose": preplace.tolist()},
                {"segment_id": "on_asset_bound_release", "pose": release.tolist()},
                {"segment_id": "on_asset_bound_retreat", "pose": preplace.tolist()},
                {"segment_id": "f2_rest", "pose": rest.tolist()},
            ]
            extra = {
                "relation": "on",
                "variant_id": "on_asset_bound_functional_point_v3",
                "target_actor_pose": target_actor.tolist(),
                "release_target_index": 1,
                "inside_full_obb_verifier_relaxed": False,
            }
        elif relation == "beside":
            route = _actual_beside_route(
                scene=scene,
                binding=self.binding,
                current_eef=current_eef,
                current_actor=current_actor,
                rest=rest,
            )
            if route["audit"]["pass"] is not True:
                raise ValueError("F2 asset-bound beside route audit failed")
            targets = route["targets"]
            extra = {
                "relation": "beside",
                "variant_id": "beside_asset_bound_actual_geometry_v3",
                "target_actor_pose": route["target_actor_pose"],
                "release_target_index": route["release_target_index"],
                "asset_bound_beside_route": route,
                "inside_full_obb_verifier_relaxed": False,
            }
        else:
            raise ValueError("unknown F2 asset-bound relation")
        extra.update(
            {
                "layout_version": self.binding["layout_version"],
                "selected_binding_sha256": self.binding["binding_sha256"],
            }
        )
        return _cache_suffix_controls(
            scene,
            program_id=program["program_id"],
            arm="left",
            targets=targets,
            query_limit=24,
            extra=extra,
        )

    def execute_frozen_suffix_spec(self, scene, program, spec, replay, realization_spec):
        self._bind_scene(scene)
        return super().execute_frozen_suffix_spec(
            scene, program, spec, replay, realization_spec
        )

    def validate_family_suffix_gate(self, receipts):
        result = dict(super().validate_family_suffix_gate(receipts))
        if self.planner_only:
            all_pass = result.get("pass") is True
            result.update(
                {
                    "schema_version": PLANNER_ONLY_STOP_SCHEMA,
                    "all_three_complete_planner_chains_pass": all_pass,
                    "intentional_stop_before_suffix_execution": True,
                    "evidence_complete": True,
                    "pass": False,
                }
            )
        return result

    def audit_passive_on_scene(self, scene) -> dict[str, Any]:
        self._bind_scene(scene)
        import sapien

        can_local_center, can_half = _actor_local_geometry_bounds(scene.can)
        orientation = self.binding["layout_payload"]["main_object_orientation_wxyz"]
        scale_point = np.asarray(scene.scale.get_functional_point(0), dtype=np.float64)
        target_actor = _actor_pose_centered_on_support(
            target_geometry_xy=scale_point[:2],
            support_plane_z_m=float(scale_point[2]),
            orientation_wxyz=orientation,
            local_geometry_center_m=can_local_center,
            half_extents_m=can_half,
        )
        entity = _entity(scene.can)
        entity.set_pose(sapien.Pose(target_actor[:3], target_actor[3:]))
        previous = _pose(scene.can)
        linear = []
        angular = []
        contacts = []
        timestep = float(scene.scene.get_timestep())
        can_name = entity.get_name()
        scale_name = _entity(scene.scale).get_name()
        for _ in range(250):
            scene.scene.step()
            current = _pose(scene.can)
            linear.append(float(np.linalg.norm(current[:3] - previous[:3]) / timestep))
            dot = float(np.clip(abs(np.dot(current[3:], previous[3:])), -1.0, 1.0))
            angular.append(float(2.0 * np.arccos(dot) / timestep))
            contacts.append(
                any(
                    {contact.bodies[0].entity.name, contact.bodies[1].entity.name}
                    == {can_name, scale_name}
                    for contact in scene.scene.get_contacts()
                )
            )
            previous = current
        stable = 50
        checks = {
            "exact_250hz": np.isclose(timestep, 0.004, atol=1e-9, rtol=0.0),
            "exact_250_steps": len(linear) == 250,
            "stable_linear_window": max(linear[-stable:])
            <= PROVISIONAL_RUNTIME_THRESHOLDS["stable_linear_speed_mps"],
            "stable_angular_window": max(angular[-stable:])
            <= PROVISIONAL_RUNTIME_THRESHOLDS["eef_stationary_angular_speed_rps"],
            "continuous_scale_support": all(contacts[-stable:]),
        }
        receipt = {
            "schema_version": "cmf_f2_asset_bound_passive_on_audit_v3",
            "selected_binding_sha256": self.binding["binding_sha256"],
            "checks": checks,
            "maximum_final_linear_speed_mps": max(linear[-stable:]),
            "maximum_final_angular_speed_rps": max(angular[-stable:]),
            "pass": all(checks.values()),
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        receipt["receipt_sha256"] = _hash_json(receipt)
        return receipt


class RoboTwinRealSapienF2AssetBoundAdapterV3(
    RoboTwinRealSapienStrictPrefixAdapterV1_3
):
    def __init__(
        self,
        *,
        output_root: Path,
        expected_implementation_source_sha256: str,
        binding: Mapping[str, Any],
        planner_only: bool,
    ):
        self.f2_binding = validate_frozen_asset_layout_binding_v3(binding)
        super().__init__(
            family="F2",
            output_root=output_root,
            expected_implementation_source_sha256=expected_implementation_source_sha256,
        )
        self.controller_v3_3 = F2AssetBoundControllerV3(
            self.f2_binding, planner_only=planner_only
        )

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = IMPLEMENTATION_VERSION

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        planned = dict(planned_root_slot_spec)
        binding = planned.get("f2_asset_layout_binding_v3")
        if not isinstance(binding, Mapping) or binding.get("binding_sha256") != self.f2_binding["binding_sha256"]:
            raise ValueError("F2 asset-bound planned spec lacks selected binding")
        return super().scene(planned, phase=phase, program=program)

    def _entity_payloads(self, scene):
        payloads = super()._entity_payloads(scene)
        key = self.f2_binding["selected_candidate_key"]
        role_specs = {
            "main_can": ("071_can", key["main_object_model_id"]),
            "box": ("062_plasticbox", key["plastic_box_model_id"]),
            "scale": ("072_electronicscale", key["electronic_scale_model_id"]),
            "stand": ("074_displaystand", key["beside_reference_model_id"]),
        }
        for role, (modelname, model_id) in role_specs.items():
            spec = {
                "modelname": modelname,
                "model_id": int(model_id),
                "collision_mode": "multiple_convex",
            }
            payloads[role]["modelname"] = modelname
            payloads[role]["model_id"] = int(model_id)
            payloads[role]["visual_asset_hash"] = _asset_hash_v1_2(spec, "visual")
            payloads[role]["collision_asset_hash"] = _asset_hash_v1_2(spec, "collision")
        return payloads

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value.update(
            {
                "asset_bound_adapter_version": ADAPTER_VERSION,
                "selected_binding_sha256": self.f2_binding["binding_sha256"],
                "formal_data": False,
                "stage0_data": False,
                "stage1_authorized": False,
            }
        )
        return value


__all__ = [
    "F2AssetBoundControllerV3",
    "RoboTwinRealSapienF2AssetBoundAdapterV3",
]
