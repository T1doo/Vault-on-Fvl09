"""Exact top-contact F2 strict-prefix development-root runtime."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_asset_bound_runtime_v3 import (
    F2AssetBoundControllerV3,
    RoboTwinRealSapienF2AssetBoundAdapterV3,
)
from .f2_inside_control_search_v2 import freeze_f2_final_grasp_pose_v2
from .f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    validate_frozen_asset_layout_binding_v3,
)
from .f2_precontact_tracking_recovery_v1 import (
    audit_f2_preclose_tracking_gate_v1,
)
from .f2_top_contact_development_root_proposal_v1 import (
    SELECTED,
    build_f2_top_contact_development_root_proposal_v1,
)
from .family_runners_v3_1 import (
    _arm_tag,
    _must_action,
    _plan_chain,
    _planner_reset,
)
from .family_runners_v3_3 import (
    PLANNER_SEED,
    _arm_eef_pose,
    _entity,
    _pose,
    _prefix_physical_acceptance,
    _prefix_reference_result,
    _settle_prefix_with_replay_operator,
)
from .geometry import relative_pose, world_axis_offset_pose
from .high_level_physical_runner_v1 import _execute_planned_segment
from .official_raw_pose_generation_v1 import generate_official_raw_pose_receipt_v1
from .runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS


IMPLEMENTATION_VERSION = "f2_top_contact_strict_prefix_root_runtime_v1"
ADAPTER_VERSION = "RoboTwinRealSapienF2TopContactRootV1Adapter"


def build_f2_top_contact_selected_binding_v1(
    source_binding: Mapping[str, Any],
) -> dict[str, Any]:
    source = validate_frozen_asset_layout_binding_v3(source_binding)
    expected_key = {
        "main_object_model_id": SELECTED["main_object_model_id"],
        "plastic_box_model_id": SELECTED["plastic_box_model_id"],
        "electronic_scale_model_id": SELECTED["electronic_scale_model_id"],
        "beside_reference_model_id": SELECTED["beside_reference_model_id"],
    }
    if (
        source["selected_candidate_key"] != expected_key
        or source["selected_execution_arm"] != "left"
        or source.get("provisional_dynamic_candidate") is not True
        or source.get("selected") is not False
    ):
        raise ValueError("F2 source binding differs from the approved micro-Gate scene")
    value = deepcopy(source)
    value.pop("binding_sha256", None)
    value.update(
        {
            "implementation_version": IMPLEMENTATION_VERSION,
            "selection_decision_source": "post_recovery_F2_top_contact_micro_gate_2_of_2",
            "selection_decision_terminal_receipt_sha256": (
                "72d206826288b432d3170397697b26076384e6a3e9ad1515c1fc75f7a9857874"
            ),
            "selected_top_contact_recipe_sha256": SELECTED["recipe_sha256"],
            "provisional_dynamic_candidate": False,
            "selected": True,
            "development_execution_authorized": False,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
    )
    value["binding_sha256"] = canonical_hash_json(value)
    return validate_frozen_asset_layout_binding_v3(value)


def build_f2_top_contact_planned_root_spec_v1(
    selected_binding: Mapping[str, Any],
) -> dict[str, Any]:
    binding = validate_frozen_asset_layout_binding_v3(selected_binding)
    if (
        binding.get("selected") is not True
        or binding.get("selected_top_contact_recipe_sha256")
        != SELECTED["recipe_sha256"]
    ):
        raise ValueError("F2 root requires the selected top-contact binding")
    value = {
        "schema_version": "cmf_f2_top_contact_planned_root_spec_v1",
        "slot_id": "f2-top-contact-development-rpc-root-v1",
        "family": "F2",
        "seed": 20260829,
        "generator": IMPLEMENTATION_VERSION,
        "program_ids": list(PROGRAM_IDS),
        "f2_asset_layout_binding_v3": canonical_jsonable(binding),
        "selected_top_contact_candidate": canonical_jsonable(SELECTED),
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_root_slot_spec_sha256"] = canonical_hash_json(value)
    return value


class F2TopContactRootControllerV1(F2AssetBoundControllerV3):
    def __init__(self, binding: Mapping[str, Any], recipe: Mapping[str, Any]):
        super().__init__(binding, planner_only=False)
        proposal = build_f2_top_contact_development_root_proposal_v1()
        expected = proposal["selected_candidate"]["full_recipe"]
        recipe_value = canonical_jsonable(recipe)
        if recipe_value != expected:
            raise ValueError("F2 root recipe differs from the approved proposal")
        self.recipe = recipe_value
        self.proposal_sha256 = proposal["proposal_sha256"]

    def canonical_prefix_contract(self, programs):
        base = super().canonical_prefix_contract(programs)
        return {
            **base,
            "prefix_id": "f2_top_contact8_rotation0_same_can_grasp_lift12cm_v1",
            "exact_top_contact_recipe_sha256": self.recipe["recipe_sha256"],
            "official_contact_point_id": 8,
            "official_rotation_candidate_index": 0,
            "pregrasp_distance_m": 0.09,
            "preclose_tracking_position_atol_m": 0.005,
            "preclose_tracking_orientation_atol_rad": 0.05,
            "proposal_sha256": self.proposal_sha256,
        }

    def plan_and_execute_canonical_prefix(
        self, scene, prefix_contract, *, capture_anchor
    ):
        self._bind_scene(scene)
        expected_contract = self.canonical_prefix_contract(
            [
                {"program_id": program_id}
                for program_id in PROGRAM_IDS
            ]
        )
        if canonical_jsonable(prefix_contract) != expected_contract:
            raise ValueError("F2 top-contact prefix contract changed")
        self.initialize_prefix_replay_trace(scene)
        raw = generate_official_raw_pose_receipt_v1(
            scene, scene.can, self.recipe, family="F2"
        )
        freeze = freeze_f2_final_grasp_pose_v2(
            self.recipe, raw_pose_generation_receipt=raw
        )
        grasp = np.asarray(freeze["final_goal_poses"]["grasp"], dtype=np.float64)
        lift = world_axis_offset_pose(grasp, 0.12)
        targets = [
            {
                "segment_id": "f2_v2_pregrasp",
                "pose": freeze["final_goal_poses"]["pregrasp"],
            },
            {
                "segment_id": "f2_v2_grasp",
                "pose": freeze["final_goal_poses"]["grasp"],
            },
            {"segment_id": "f2_top_contact_lift_12cm", "pose": lift.tolist()},
        ]
        reset = _planner_reset(
            scene,
            planner_seed=PLANNER_SEED,
            variant_id=(
                "f2_top_contact_root_prefix:"
                + self.recipe["recipe_sha256"]
            ),
            arm="left",
        )
        planned = _plan_chain(scene, targets, query_limit=3, arm="left")
        if (
            planned.get("pass") is not True
            or len(planned.get("segment_receipts", [])) != 3
        ):
            raise RuntimeError("F2 top-contact canonical prefix planner failed")
        start = len(scene.trace) - 1
        executions = [
            _execute_planned_segment(scene, planned["controls"], targets, index, "left")
            for index in (0, 1)
        ]
        tracking = audit_f2_preclose_tracking_gate_v1(executions)
        if tracking["pass"] is not True:
            scene._cmf_prefix_failure_receipt = {
                "failure": "PRECONTACT_ARM_TRACKING_FAILURE",
                "preclose_tracking_gate": tracking,
                "close_executed": False,
            }
            raise RuntimeError("F2 top-contact prefix preclose tracking Gate failed")
        _must_action(
            scene,
            scene.close_gripper(_arm_tag("left"), pos=0.0),
            "f2_top_contact_prefix_close",
        )
        post_close = len(scene.trace) - 1 - start
        post_close_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.can)
        )
        executions.append(
            _execute_planned_segment(
                scene, planned["controls"], targets, 2, "left"
            )
        )
        post_lift = len(scene.trace) - 1 - start
        semantic_end = len(scene.trace) - 1
        semantic_anchor = capture_anchor(scene)
        settling = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
        _settle_prefix_with_replay_operator(scene, settling)
        acceptance_anchor = capture_anchor(scene)
        acceptance_transform = relative_pose(
            _arm_eef_pose(scene, "left"), _pose(scene.can)
        )
        translation_drift = float(
            np.linalg.norm(acceptance_transform[:3] - post_close_transform[:3])
        )
        orientation_drift = quaternion_angular_error(
            acceptance_transform[3:], post_close_transform[3:]
        )
        acceptance = _prefix_physical_acceptance(
            scene,
            roles=("main_can",),
            require_selected_contact=True,
            expected_contact_actor_name=_entity(scene.can).get_name(),
            extra_checks={
                "preclose_tracking_gate": tracking["pass"] is True,
                "grasp_transform_translation_stable": translation_drift <= 0.005,
                "grasp_transform_orientation_stable": orientation_drift <= 0.05,
            },
        )
        acceptance.update(
            {
                "preclose_tracking_gate": tracking,
                "grasp_transform_translation_drift_m": translation_drift,
                "grasp_transform_orientation_drift_rad": orientation_drift,
            }
        )
        return _prefix_reference_result(
            scene,
            start_action=start,
            semantic_end_action=semantic_end,
            semantic_end_anchor=semantic_anchor,
            acceptance_end_anchor=acceptance_anchor,
            settling_steps=settling,
            extra={
                "reference_event_boundaries": {
                    "post_close": post_close,
                    "post_lift": post_lift,
                },
                "official_raw_pose_generation_receipt": raw,
                "final_grasp_pose_freeze": freeze,
                "exact_prefix_targets": targets,
                "exact_prefix_targets_sha256": canonical_hash_json(targets),
                "prefix_planner_reset_receipt": reset,
                "prefix_execution_receipts": executions,
                "prefix_physical_acceptance": acceptance,
            },
        )


class RoboTwinRealSapienF2TopContactRootV1Adapter(
    RoboTwinRealSapienF2AssetBoundAdapterV3
):
    def __init__(
        self,
        *,
        output_root: Path,
        expected_implementation_source_sha256: str,
        binding: Mapping[str, Any],
        recipe: Mapping[str, Any],
    ):
        super().__init__(
            output_root=output_root,
            expected_implementation_source_sha256=expected_implementation_source_sha256,
            binding=binding,
            planner_only=False,
        )
        self.controller_v3_3 = F2TopContactRootControllerV1(binding, recipe)

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = IMPLEMENTATION_VERSION


__all__ = [
    "ADAPTER_VERSION",
    "F2TopContactRootControllerV1",
    "IMPLEMENTATION_VERSION",
    "RoboTwinRealSapienF2TopContactRootV1Adapter",
    "build_f2_top_contact_planned_root_spec_v1",
    "build_f2_top_contact_selected_binding_v1",
]

