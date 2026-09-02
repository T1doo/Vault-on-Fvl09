"""F2 final-grasp V2 planner-only integration.

The production entry point is bound to the official raw-pose generator and
the project planner helpers.  It exposes no callback injection and performs
no gripper, controlled-action, or physical execution call.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_inside_control_search_v2 import (
    capture_f2_runtime_geometry_observation_v4,
    compare_f2_runtime_geometry_v4,
    freeze_f2_final_grasp_pose_v2,
)
from .f2_official_asset_compatibility_matrix_v3 import (
    validate_frozen_asset_layout_binding_v3,
)
from .family_runners_v3_1 import _plan_chain, _planner_reset
from .official_raw_pose_generation_v1 import (
    generate_official_raw_pose_receipt_v1,
    validate_official_raw_pose_receipt_v1,
)


PURPOSE = "f2_final_grasp_v2_stage_a_planner"
QUERY_COUNT = 3
FORBIDDEN_RESULT_FIELDS = frozenset(
    {"runtime_qualified", "candidate_ready", "physical_feasible"}
)


def _self_hashed(value: Mapping[str, Any], key: str, label: str) -> dict[str, Any]:
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"F2 {label} hash mismatch")
    return result


def _certificate(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _self_hashed(value, "certificate_sha256", "geometry certificate")
    if result.get("schema_version") != "cmf_f2_geometry_certificate_v4":
        raise ValueError("F2 geometry certificate schema mismatch")
    return result


def _recipe(value: Mapping[str, Any]) -> dict[str, Any]:
    return _self_hashed(value, "recipe_sha256", "recipe")


def build_f2_final_grasp_stage_a_spec_v2(
    recipe: Mapping[str, Any],
    geometry_certificate: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    slot_id: str,
    panel_sha256: str,
    planner_rng_seed: int,
) -> dict[str, Any]:
    recipe_value = _recipe(recipe)
    certificate = _certificate(geometry_certificate)
    binding_value = validate_frozen_asset_layout_binding_v3(binding)
    key = binding_value["selected_candidate_key"]
    checks = {
        "can_id": recipe_value.get("main_object_model_id")
        == certificate.get("main_object_model_id")
        == key.get("main_object_model_id"),
        "box_id": certificate.get("plastic_box_model_id")
        == key.get("plastic_box_model_id"),
        "arm": recipe_value.get("arm")
        == binding_value.get("selected_execution_arm"),
        "certificate": recipe_value.get("geometry_certificate_sha256")
        == certificate.get("certificate_sha256"),
    }
    if not all(checks.values()):
        raise ValueError("F2 recipe/certificate/binding mismatch")
    if not isinstance(panel_sha256, str) or len(panel_sha256) != 64:
        raise ValueError("F2 panel SHA is invalid")
    scene_spec = {
        "layout_version": binding_value["layout_version"],
        "layout_payload_sha256": binding_value["layout_payload_sha256"],
        "selected_execution_arm": binding_value["selected_execution_arm"],
        "selected_candidate_key": binding_value["selected_candidate_key"],
    }
    value = {
        "schema_version": "cmf_f2_final_grasp_stage_a_spec_v2",
        "purpose": PURPOSE,
        "slot_id": str(slot_id),
        "family": "F2",
        "panel_sha256": panel_sha256,
        "recipe": recipe_value,
        "recipe_sha256": recipe_value["recipe_sha256"],
        "geometry_certificate": certificate,
        "geometry_certificate_sha256": certificate["certificate_sha256"],
        "binding": binding_value,
        "binding_sha256": binding_value["binding_sha256"],
        "scene_spec": scene_spec,
        "scene_spec_sha256": canonical_hash_json(scene_spec),
        "ordered_segments": ["pregrasp", "grasp", "qualification_micro_lift_25mm"],
        "planner_query_limit": QUERY_COUNT,
        "planner_rng_seed": int(planner_rng_seed),
        "old_gravity_drop_builder_allowed": False,
        "arbitrary_callable_injection_allowed": False,
        "physical_execution_count_limit": 0,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_final_grasp_stage_a_spec_v2(
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    value = _self_hashed(spec, "spec_sha256", "Stage-A spec")
    rebuilt = build_f2_final_grasp_stage_a_spec_v2(
        value["recipe"],
        value["geometry_certificate"],
        value["binding"],
        slot_id=value["slot_id"],
        panel_sha256=value["panel_sha256"],
        planner_rng_seed=value["planner_rng_seed"],
    )
    if value != rebuilt:
        raise ValueError("F2 Stage-A spec differs from canonical rebuild")
    return value


def _planner_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pass": result.get("pass") is True,
        "segment_receipts": deepcopy(result.get("segment_receipts", [])),
        "planner_query_count": int(result.get("planner_query_count", 0)),
        "terminal_qpos": deepcopy(result.get("terminal_qpos")),
        "terminal_qpos_sha256": result.get("terminal_qpos_sha256"),
        "controls_retained_in_receipt": False,
    }


def run_f2_final_grasp_stage_a_planner_v2(
    scene,
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    value = validate_f2_final_grasp_stage_a_spec_v2(spec)
    recipe = value["recipe"]
    runtime = capture_f2_runtime_geometry_observation_v4(scene)
    geometry_gate = compare_f2_runtime_geometry_v4(
        value["geometry_certificate"], runtime
    )
    if geometry_gate["pass"] is not True:
        raise ValueError("F2 runtime geometry differs from certificate")
    raw = generate_official_raw_pose_receipt_v1(
        scene, scene.can, recipe, family="F2"
    )
    raw_validation = validate_official_raw_pose_receipt_v1(
        raw, recipe, family="F2"
    )
    if raw_validation["pass"] is not True:
        raise ValueError("F2 official raw-pose receipt failed validation")
    freeze = freeze_f2_final_grasp_pose_v2(
        recipe, raw_pose_generation_receipt=raw
    )
    names = ("pregrasp", "grasp", "qualification_micro_lift_25mm")
    targets = [
        {
            "segment_id": f"f2_final_grasp_v2_{name}",
            "pose": freeze["final_goal_poses"][name],
        }
        for name in names
    ]
    reset = _planner_reset(
        scene,
        planner_seed=value["planner_rng_seed"],
        variant_id=f"{PURPOSE}:{recipe['recipe_id']}",
        arm=recipe["arm"],
    )
    planned = _plan_chain(
        scene, targets, query_limit=QUERY_COUNT, arm=recipe["arm"]
    )
    receipts = planned.get("segment_receipts", [])
    exact_ids = [item["segment_id"] for item in targets]
    observed_ids = [item.get("segment_id") for item in receipts]
    qualified = (
        planned.get("pass") is True
        and len(receipts) == QUERY_COUNT
        and observed_ids == exact_ids
        and all(item.get("planner_status") == "Success" for item in receipts)
    )
    terminal = {
        "schema_version": "cmf_f2_final_grasp_stage_a_terminal_v2",
        "purpose": PURPOSE,
        "slot_id": value["slot_id"],
        "spec_sha256": value["spec_sha256"],
        "panel_sha256": value["panel_sha256"],
        "recipe_id": recipe["recipe_id"],
        "recipe_sha256": recipe["recipe_sha256"],
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "runtime_asset_metadata_receipt_sha256": getattr(
            scene, "_cmf_f2_runtime_asset_metadata_receipt_v4"
        )["receipt_sha256"],
        "runtime_geometry_gate": geometry_gate,
        "raw_pose_generation_receipt": raw,
        "raw_pose_validation": raw_validation,
        "final_grasp_pose_freeze": freeze,
        "planner_rng_reset": canonical_jsonable(reset),
        "planner_rng_seed": value["planner_rng_seed"],
        "planner_result": _planner_summary(planned),
        "ordered_target_ids": exact_ids,
        "ordered_targets_sha256": canonical_hash_json(targets),
        "planner_qualified_for_physical_probe": qualified,
        "runtime_qualified": False,
        "candidate_ready": False,
        "stage1_ready": False,
        "physical_execution_authorized": False,
        "physical_execution_count": 0,
    }
    terminal["receipt_sha256"] = canonical_hash_json(terminal)
    return terminal


def validate_f2_planner_terminal_v2(
    terminal: Mapping[str, Any], spec: Mapping[str, Any]
) -> dict[str, Any]:
    value = _self_hashed(terminal, "receipt_sha256", "planner terminal")
    checked = validate_f2_final_grasp_stage_a_spec_v2(spec)
    if (
        value.get("schema_version") != "cmf_f2_final_grasp_stage_a_terminal_v2"
        or value.get("spec_sha256") != checked["spec_sha256"]
        or value.get("recipe_sha256") != checked["recipe_sha256"]
        or any(value.get(field) is not False for field in FORBIDDEN_RESULT_FIELDS)
        or value.get("physical_execution_count") != 0
    ):
        raise ValueError("F2 planner terminal semantics or binding changed")
    return value


def finalize_f2_planner_panel_v2(
    panel_manifest: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    terminals: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    manifest = _self_hashed(panel_manifest, "panel_sha256", "panel manifest")
    ordered_hashes = manifest["ordered_recipe_sha256s"]
    if not (len(specs) == len(terminals) == len(ordered_hashes)):
        raise ValueError("F2 panel finalizer requires complete ordered coverage")
    checked_specs = [validate_f2_final_grasp_stage_a_spec_v2(item) for item in specs]
    checked_terminals = [
        validate_f2_planner_terminal_v2(terminal, spec)
        for terminal, spec in zip(terminals, checked_specs)
    ]
    if [item["recipe_sha256"] for item in checked_specs] != ordered_hashes:
        raise ValueError("F2 panel spec order differs from manifest")
    passing = [
        item
        for item in checked_terminals
        if item["planner_qualified_for_physical_probe"] is True
    ]
    result = {
        "schema_version": "cmf_f2_planner_panel_terminal_v2",
        "panel_sha256": manifest["panel_sha256"],
        "terminal_receipt_sha256s": [item["receipt_sha256"] for item in checked_terminals],
        "planner_qualified_recipe_sha256s": [item["recipe_sha256"] for item in passing],
        "physical_probe_proposal_survivor_sha256s": [
            item["recipe_sha256"] for item in passing[:4]
        ],
        "planner_qualified_for_physical_probe": bool(passing),
        "runtime_qualified": False,
        "candidate_ready": False,
        "stage1_ready": False,
        "physical_execution_authorized": False,
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


__all__ = [
    "PURPOSE",
    "build_f2_final_grasp_stage_a_spec_v2",
    "finalize_f2_planner_panel_v2",
    "run_f2_final_grasp_stage_a_planner_v2",
    "validate_f2_final_grasp_stage_a_spec_v2",
    "validate_f2_planner_terminal_v2",
]
