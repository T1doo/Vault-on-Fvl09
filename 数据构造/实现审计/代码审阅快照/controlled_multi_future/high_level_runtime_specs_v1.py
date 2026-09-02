"""CPU-only planned runtime specs for the high-level template redesign.

These builders bind immutable candidates to fresh-scene runtime inputs.  They
do not authorize a GPU process and do not create output directories.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_dynamic_search_contract_v3 import _strict_cavity_from_inside_evidence
from .f2_hierarchical_template_search_v1 import (
    SCREENING_PATH,
    build_f2_hierarchical_template_search_v1,
)
from .f2_official_asset_compatibility_matrix_v3 import (
    BINDING_SCHEMA_VERSION,
    DESIGN_VERSION,
    PROGRAM_IDS as F2_PROGRAM_IDS,
    validate_frozen_asset_layout_binding_v3,
)
from .f3_asset_grasp_qualification_v2 import (
    build_f3_asset_grasp_qualification_v2,
)
from .f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
)
from .f4_post_stage0_layout_v1 import LAYOUT as F4_REFERENCE_LAYOUT


IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_runtime_specs_v1"
ALLOWED_PURPOSES = {
    "f2_stage_a_planner",
    "f2_inside_physical",
    "f3_level1_planner",
    "f3_level2_physical",
    "f3_three_scene_confirmation",
    "f3_temporal_root",
    "f4_stage_a_planner",
    "f4_stage_b_planner",
    "f4_single_role_physical",
    "f4_temporal_root",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _candidate(values, *, identity_field: str, identity: str, label: str):
    matches = [item for item in values if item.get(identity_field) == identity]
    if len(matches) != 1:
        raise ValueError(f"{label} is outside the frozen candidate set")
    return deepcopy(matches[0])


def _mirror_layout_x(layout: Mapping[str, Any]) -> dict[str, Any]:
    value = canonical_jsonable(layout)
    value["main_object_pose_xyz"][0] *= -1.0
    for pose in value["facility_pose_xyz"].values():
        pose[0] *= -1.0
    value["inside_region_center_xy_m"][0] *= -1.0
    value["on_region_center_xy_m"][0] *= -1.0
    for point in value["beside_candidate_xy_m"]:
        point[0] *= -1.0
    value["layout_version"] = "f2_hierarchical_stage_a_right_mirror_v1"
    return value


def build_f2_stage_a_binding_v1(
    candidate: Mapping[str, Any],
    *,
    screening: Mapping[str, Any] | None = None,
    screening_path: Path = SCREENING_PATH,
) -> dict[str, Any]:
    source = _load_json(screening_path) if screening is None else canonical_jsonable(screening)
    contract = build_f2_hierarchical_template_search_v1(source)
    frozen = _candidate(
        contract["inside_candidates"],
        identity_field="candidate_id",
        identity=str(candidate.get("candidate_id")),
        label="F2 Stage-A candidate",
    )
    if frozen != canonical_jsonable(candidate):
        raise ValueError("F2 Stage-A candidate payload changed")
    pair = next(
        item
        for item in contract["collapsed_pairs"]
        if item["pair_sha256"] == frozen["inside_pair_sha256"]
    )
    receipt = next(
        item
        for item in source["terminal_cpu_candidate_receipts"]
        if item["static_row_sha256"] == pair["representative_static_row_sha256"]
    )
    key = deepcopy(receipt["candidate_key"])
    if (
        key["main_object_model_id"] != frozen["main_object_model_id"]
        or key["plastic_box_model_id"] != frozen["plastic_box_model_id"]
    ):
        raise ValueError("F2 Stage-A representative row differs from frozen pair")
    layout = deepcopy(receipt["layout_cpu_receipt"]["layout"])
    if frozen["arm"] == "right":
        layout = _mirror_layout_x(layout)
    else:
        layout["layout_version"] = "f2_hierarchical_stage_a_left_v1"
    cavity = _strict_cavity_from_inside_evidence(receipt["inside_cpu_evidence"])
    cavity["coordinate_frame"] = (
        f"062_plasticbox/base{key['plastic_box_model_id']} actor-local xyz"
    )
    value = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "matrix_sha256": source["matrix_sha256"],
        "cpu_screening_sha256": source["screening_sha256"],
        "dynamic_scope_sha256": contract["search_contract_sha256"],
        "selected_evaluated_row_sha256": receipt["static_row_sha256"],
        "selected_candidate_key": key,
        "asset_record_sha256s": deepcopy(receipt["asset_record_sha256s"]),
        "selected_execution_arm": frozen["arm"],
        "strict_cavity_contract": cavity,
        "inside_object_orientation_wxyz": deepcopy(
            frozen["inside_actor_orientation_wxyz"]
        ),
        "layout_version": layout["layout_version"],
        "layout_payload": layout,
        "layout_payload_sha256": canonical_hash_json(layout),
        "program_ids": list(F2_PROGRAM_IDS),
        "same_main_object_for_all_programs": True,
        "same_execution_arm_for_all_programs": True,
        "branch_specific_asset_or_arm_selection_allowed": False,
        "provisional_dynamic_candidate": True,
        "selected": False,
        "development_execution_authorized": False,
        "hierarchical_stage_a_candidate_id": frozen["candidate_id"],
        "hierarchical_stage_a_candidate_sha256": frozen["candidate_sha256"],
        "scale_and_stand_are_fixed_inert_stage_a_scene_assets": True,
        "scale_or_stand_used_for_stage_a_rank": False,
        "right_layout_transform_is_position_x_mirror_only": frozen["arm"] == "right",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["binding_sha256"] = canonical_hash_json(value)
    return validate_frozen_asset_layout_binding_v3(value)


def build_f2_runtime_spec_v1(
    candidate_id: str,
    *,
    purpose: str,
    screening: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if purpose not in {"f2_stage_a_planner", "f2_inside_physical"}:
        raise ValueError("invalid F2 high-level runtime purpose")
    contract = build_f2_hierarchical_template_search_v1(screening)
    candidate = _candidate(
        contract["inside_candidates"],
        identity_field="candidate_id",
        identity=candidate_id,
        label="F2 Stage-A candidate",
    )
    binding = build_f2_stage_a_binding_v1(candidate, screening=screening)
    value = {
        "schema_version": "cmf_f2_high_level_runtime_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "slot_id": f"{purpose}-{candidate['rank']:02d}",
        "scope": purpose,
        "family": "F2",
        "arm": candidate["arm"],
        "seed": 2026091100 + int(candidate["rank"]),
        "generator": "controlled_multi_future_f2_hierarchical_runtime_v1",
        "purpose": purpose,
        "candidate": candidate,
        "candidate_sha256": candidate["candidate_sha256"],
        "parent_search_contract_sha256": contract["search_contract_sha256"],
        "f2_asset_layout_binding_v3": binding,
        "f2_asset_layout_binding_sha256": binding["binding_sha256"],
        "planner_only": purpose == "f2_stage_a_planner",
        "maximum_physical_execution_count": 0
        if purpose == "f2_stage_a_planner"
        else 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_scope_spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_runtime_spec_v1(
    value: Mapping[str, Any], *, screening: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    candidate = normalized.get("candidate")
    purpose = normalized.get("purpose")
    if not isinstance(candidate, Mapping) or not isinstance(purpose, str):
        raise ValueError("F2 runtime spec is incomplete")
    expected = build_f2_runtime_spec_v1(
        str(candidate.get("candidate_id")), purpose=purpose, screening=screening
    )
    if normalized != expected:
        raise ValueError("F2 runtime spec changed")
    return expected


def build_f3_runtime_spec_v1(tuple_id: str, *, purpose: str) -> dict[str, Any]:
    if purpose not in {
        "f3_level1_planner",
        "f3_level2_physical",
        "f3_three_scene_confirmation",
        "f3_temporal_root",
    }:
        raise ValueError("invalid F3 high-level runtime purpose")
    contract = build_f3_asset_grasp_qualification_v2()
    candidate = _candidate(
        contract["grasp_tuples"],
        identity_field="tuple_id",
        identity=tuple_id,
        label="F3 grasp tuple",
    )
    physical_limits = {
        "f3_level1_planner": 0,
        "f3_level2_physical": 1,
        "f3_three_scene_confirmation": 3,
        "f3_temporal_root": 3,
    }
    value = {
        "schema_version": "cmf_f3_high_level_runtime_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "slot_id": f"{purpose}-{candidate['rank']:02d}",
        "scope": purpose,
        "family": "F3",
        "arm": candidate["arm"],
        "seed": 2026091200 + int(candidate["rank"]),
        "generator": "controlled_multi_future_f3_asset_grasp_runtime_v2",
        "purpose": purpose,
        "f3_asset_grasp_tuple_v2": candidate,
        "f3_asset_grasp_tuple_sha256": candidate["tuple_sha256"],
        "parent_qualification_sha256": contract["qualification_sha256"],
        "planner_only": purpose == "f3_level1_planner",
        "maximum_physical_execution_count": physical_limits[purpose],
        "suffix_allowed": purpose == "f3_temporal_root",
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["planned_scope_spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_runtime_spec_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    candidate = normalized.get("f3_asset_grasp_tuple_v2")
    purpose = normalized.get("purpose")
    if not isinstance(candidate, Mapping) or not isinstance(purpose, str):
        raise ValueError("F3 runtime spec is incomplete")
    expected = build_f3_runtime_spec_v1(
        str(candidate.get("tuple_id")), purpose=purpose
    )
    if normalized != expected:
        raise ValueError("F3 runtime spec changed")
    return expected


def _f4_stage_a_scene_layout(candidate: Mapping[str, Any]) -> dict[str, Any]:
    value = canonical_jsonable(F4_REFERENCE_LAYOUT)
    value["layout_version"] = (
        f"f4_hierarchical_stage_a_source_grasp_v1_r{int(candidate['rank']):02d}"
    )
    value["object_poses"] = deepcopy(candidate["source_layout"])
    value["stage_a_slot_placeholders_fixed_not_searched"] = True
    value["stage_a_source_grasp_candidate_sha256"] = candidate[
        "candidate_sha256"
    ]
    return value


def _validate_f4_stage_a_terminal_for_stage_b_v1(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    payload = dict(normalized)
    digest = payload.pop("receipt_sha256", None)
    contract = build_f4_hierarchical_template_search_v1()
    source = normalized.get("selected_source_grasp")
    expected_source = next(
        (
            item
            for item in contract["stage_a_candidates"]
            if isinstance(source, Mapping)
            and item["candidate_id"] == source.get("candidate_id")
            and item["candidate_sha256"] == source.get("candidate_sha256")
        ),
        None,
    )
    if (
        normalized.get("schema_version")
        not in {
            "cmf_f4_hierarchical_stage_a_terminal_v1",
            "cmf_f4_hierarchical_stage_a_sequential_terminal_v1",
        }
        or digest != canonical_hash_json(payload)
        or normalized.get("search_contract_sha256")
        != contract["search_contract_sha256"]
        or expected_source is None
        or canonical_jsonable(source) != expected_source
        or normalized.get("stage_b_authorized_by_result") is not True
        or normalized.get("status")
        != "SOURCE_GRASP_PASS_REQUIRES_STAGE_B_SLOT_SEARCH"
    ):
        raise ValueError("F4 Stage-A terminal does not authorize Stage B")
    return normalized


def _f4_stage_b_scene_layout(
    source: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    value = canonical_jsonable(F4_REFERENCE_LAYOUT)
    value["layout_version"] = (
        f"f4_hierarchical_stage_b_slot_corridor_v1_r{int(candidate['rank']):02d}"
    )
    value["object_poses"] = deepcopy(source["source_layout"])
    value["slot_poses"] = deepcopy(candidate["slot_poses"])
    value["stage_a_source_grasp_candidate_sha256"] = source[
        "candidate_sha256"
    ]
    value["stage_b_slot_corridor_candidate_sha256"] = candidate[
        "candidate_sha256"
    ]
    value["stage_b_corridor_policy"] = candidate["corridor_policy"]
    value["stage_a_slot_placeholders_fixed_not_searched"] = False
    return value


def _validate_f4_stage_b_terminal_for_physical_v1(
    value: Mapping[str, Any],
    *,
    stage_a_terminal: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    payload = dict(normalized)
    digest = payload.pop("receipt_sha256", None)
    contract = build_f4_hierarchical_template_search_v1()
    stage_b = build_f4_stage_b_candidates_v1(contract, stage_a_terminal)
    selected = normalized.get("selected_slot_corridor")
    expected = next(
        (
            item
            for item in stage_b["candidates"]
            if isinstance(selected, Mapping)
            and item["candidate_id"] == selected.get("candidate_id")
            and item["candidate_sha256"] == selected.get("candidate_sha256")
        ),
        None,
    )
    if (
        normalized.get("schema_version")
        != "cmf_f4_hierarchical_stage_b_terminal_v1"
        or digest != canonical_hash_json(payload)
        or normalized.get("stage_b_contract_sha256")
        != stage_b["stage_b_contract_sha256"]
        or expected is None
        or canonical_jsonable(selected) != expected
        or normalized.get("single_role_physical_authorized_by_result")
        is not True
        or normalized.get("status")
        != "SLOT_CORRIDOR_PASS_REQUIRES_A_ONLY_EXECUTION"
    ):
        raise ValueError("F4 Stage-B terminal does not authorize A-only physical")
    return normalized


def build_f4_runtime_spec_v1(
    candidate_id: str,
    *,
    purpose: str,
    stage_a_terminal: Mapping[str, Any] | None = None,
    stage_b_terminal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if purpose not in {
        "f4_stage_a_planner",
        "f4_stage_b_planner",
        "f4_single_role_physical",
    }:
        raise ValueError("invalid F4 high-level runtime purpose")
    contract = build_f4_hierarchical_template_search_v1()
    if purpose == "f4_stage_a_planner":
        if stage_a_terminal is not None or stage_b_terminal is not None:
            raise ValueError("F4 Stage-A spec cannot carry a Stage-A terminal")
        source = _candidate(
            contract["stage_a_candidates"],
            identity_field="candidate_id",
            identity=candidate_id,
            label="F4 Stage-A candidate",
        )
        candidate = source
        layout = _f4_stage_a_scene_layout(source)
        rank = int(source["rank"])
        seed = 2026091300 + rank
        stage_b = None
        terminal = None
    else:
        if stage_a_terminal is None:
            raise ValueError("F4 Stage-B spec requires the passing Stage-A terminal")
        terminal = _validate_f4_stage_a_terminal_for_stage_b_v1(
            stage_a_terminal
        )
        source = terminal["selected_source_grasp"]
        stage_b = build_f4_stage_b_candidates_v1(contract, terminal)
        physical_terminal = None
        if purpose == "f4_single_role_physical":
            if stage_b_terminal is None:
                raise ValueError(
                    "F4 A-only spec requires the passing Stage-B terminal"
                )
            physical_terminal = _validate_f4_stage_b_terminal_for_physical_v1(
                stage_b_terminal, stage_a_terminal=terminal
            )
            if physical_terminal["selected_slot_corridor"]["candidate_id"] != candidate_id:
                raise ValueError("F4 A-only candidate differs from Stage-B selection")
        elif stage_b_terminal is not None:
            raise ValueError("F4 Stage-B planner spec cannot carry Stage-B terminal")
        candidate = _candidate(
            stage_b["candidates"],
            identity_field="candidate_id",
            identity=candidate_id,
            label="F4 Stage-B candidate",
        )
        layout = _f4_stage_b_scene_layout(source, candidate)
        rank = int(candidate["rank"])
        seed = (
            2026091500 + rank
            if purpose == "f4_single_role_physical"
            else 2026091400 + rank
        )
    value = {
        "schema_version": "cmf_f4_high_level_runtime_spec_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "slot_id": f"{purpose}-{rank:02d}",
        "scope": purpose,
        "family": "F4",
        "arm": source["arm"],
        "seed": seed,
        "generator": "controlled_multi_future_f4_hierarchical_runtime_v1",
        "purpose": purpose,
        "f4_source_grasp_candidate_v1": source,
        "f4_source_grasp_candidate_sha256": source["candidate_sha256"],
        "parent_search_contract_sha256": contract["search_contract_sha256"],
        "scene_layout": layout,
        "scene_layout_sha256": canonical_hash_json(layout),
        "stage_a_slot_search_active": False,
        "stage_b_slot_search_active": purpose == "f4_stage_b_planner",
        "selected_stage_b_layout_active": purpose
        == "f4_single_role_physical",
        "maximum_physical_execution_count": 1
        if purpose == "f4_single_role_physical"
        else 0,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    if purpose in {"f4_stage_b_planner", "f4_single_role_physical"}:
        value.update(
            {
                "f4_stage_a_terminal_v1": terminal,
                "f4_stage_a_terminal_sha256": terminal["receipt_sha256"],
                "f4_stage_b_contract_v1": stage_b,
                "f4_stage_b_contract_sha256": stage_b[
                    "stage_b_contract_sha256"
                ],
                "f4_stage_b_candidate_v1": candidate,
                "f4_stage_b_candidate_sha256": candidate[
                    "candidate_sha256"
                ],
            }
        )
        if purpose == "f4_single_role_physical":
            value.update(
                {
                    "f4_stage_b_terminal_v1": physical_terminal,
                    "f4_stage_b_terminal_sha256": physical_terminal[
                        "receipt_sha256"
                    ],
                    "single_role": "A",
                    "common_x_completed_first": True,
                }
            )
    value["planned_scope_spec_sha256"] = canonical_hash_json(value)
    return value


def validate_f4_runtime_spec_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    purpose = normalized.get("purpose")
    if not isinstance(purpose, str):
        raise ValueError("F4 runtime spec is incomplete")
    candidate = (
        normalized.get("f4_stage_b_candidate_v1")
        if purpose in {"f4_stage_b_planner", "f4_single_role_physical"}
        else normalized.get("f4_source_grasp_candidate_v1")
    )
    if not isinstance(candidate, Mapping):
        raise ValueError("F4 runtime spec candidate is incomplete")
    expected = build_f4_runtime_spec_v1(
        str(candidate.get("candidate_id")),
        purpose=purpose,
        stage_a_terminal=(
            normalized.get("f4_stage_a_terminal_v1")
            if purpose in {"f4_stage_b_planner", "f4_single_role_physical"}
            else None
        ),
        stage_b_terminal=(
            normalized.get("f4_stage_b_terminal_v1")
            if purpose == "f4_single_role_physical"
            else None
        ),
    )
    if normalized != expected:
        raise ValueError("F4 runtime spec changed")
    return expected


def job_budget_v1(purpose: str) -> dict[str, Any]:
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError("unknown high-level runtime purpose")
    limits = {
        "f2_stage_a_planner": (12, 1, 0, 3600),
        "f2_inside_physical": (12, 1, 1, 5400),
        "f3_level1_planner": (10, 1, 0, 3600),
        "f3_level2_physical": (10, 1, 1, 5400),
        "f3_three_scene_confirmation": (30, 3, 3, 10800),
        "f3_temporal_root": (72, 4, 3, 14400),
        "f4_stage_a_planner": (48, 1, 0, 5400),
        "f4_stage_b_planner": (42, 1, 0, 5400),
        "f4_single_role_physical": (32, 1, 1, 7200),
        "f4_temporal_root": (96, 4, 3, 14400),
    }
    planner, scenes, executions, timeout = limits[purpose]
    value = {
        "schema_version": "cmf_high_level_runtime_job_budget_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "purpose": purpose,
        "planner_query_limit": planner,
        "fresh_scene_limit": scenes,
        "physical_execution_limit": executions,
        "controlled_action_limit": executions,
        "physics_step_limit": -1,
        "allowed_physical_gpu_indices": list(range(8)),
        "one_project_job_per_gpu": True,
        "one_root_one_gpu": True,
        "root_sharding_authorized": False,
        "maximum_scope_invocations": 1,
        "automatic_retry": False,
        "recovery_attempts": 0,
        "timeout_seconds": timeout,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["budget_receipt_sha256"] = canonical_hash_json(value)
    return value


def validate_job_budget_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    purpose = normalized.get("purpose")
    if not isinstance(purpose, str):
        raise ValueError("high-level runtime budget lacks purpose")
    expected = job_budget_v1(purpose)
    if normalized != expected:
        raise ValueError("high-level runtime budget changed")
    return expected


__all__ = [
    "ALLOWED_PURPOSES",
    "build_f2_runtime_spec_v1",
    "build_f2_stage_a_binding_v1",
    "build_f3_runtime_spec_v1",
    "build_f4_runtime_spec_v1",
    "job_budget_v1",
    "validate_f2_runtime_spec_v1",
    "validate_f3_runtime_spec_v1",
    "validate_f4_runtime_spec_v1",
    "validate_job_budget_v1",
]
