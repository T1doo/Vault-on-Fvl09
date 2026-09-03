"""Targeted two-pair F2 planner manifest for production recovery.

This is a development qualification manifest, not an execution authorization.
It retains the current static-margin pair and the only historical pair whose
old full insertion chain was planner-solvable, then selects at most one
Stage-A survivor per pair and arm for bounded physical qualification.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
)
from .f2_inside_control_search_v2 import (
    build_f2_geometry_certificate_v4,
    build_f2_grasp_recipe_universe_v2,
)
from .f2_planner_integration_v2 import (
    build_f2_final_grasp_stage_a_spec_v2,
    validate_f2_planner_terminal_v2,
)
from .high_level_runtime_specs_v1 import build_f2_runtime_spec_v1


PAIR_ORDER = ((0, 2), (5, 8))
ARMS = ("left", "right")
CONTACT_IDS = tuple(range(16))
ROTATION_INDICES = (0, 5)


def _pair_id(can_id: int, box_id: int) -> str:
    return f"can{int(can_id)}-box{int(box_id)}"


def build_f2_recovery_planner_manifest_v1() -> dict[str, Any]:
    search = build_f2_hierarchical_template_search_v1()
    pair_rows = {
        (item["main_object_model_id"], item["plastic_box_model_id"]): item
        for item in search["collapsed_pairs"]
        if (item["main_object_model_id"], item["plastic_box_model_id"])
        in PAIR_ORDER
    }
    if tuple(pair_rows) != PAIR_ORDER:
        raise ValueError("F2 recovery pair order differs from frozen order")
    certificates = {
        _pair_id(*pair): build_f2_geometry_certificate_v4(
            main_object_model_id=pair[0], plastic_box_model_id=pair[1]
        )
        for pair in PAIR_ORDER
    }
    bindings: dict[str, dict[str, Any]] = {}
    for pair in PAIR_ORDER:
        key = _pair_id(*pair)
        candidates = {
            item["arm"]: item
            for item in search["inside_candidates"]
            if (
                item["main_object_model_id"],
                item["plastic_box_model_id"],
            )
            == pair
        }
        if set(candidates) != set(ARMS):
            raise ValueError(f"F2 recovery pair {key} lacks both arms")
        bindings[key] = {
            arm: build_f2_runtime_spec_v1(
                candidates[arm]["candidate_id"], purpose="f2_stage_a_planner"
            )["f2_asset_layout_binding_v3"]
            for arm in ARMS
        }
    universe = build_f2_grasp_recipe_universe_v2(
        [
            {
                "main_object_model_id": pair[0],
                "plastic_box_model_id": pair[1],
                "official_can_contact_point_count": pair_rows[pair][
                    "official_can_contact_point_count"
                ],
                "geometry_certificate_sha256": certificates[
                    _pair_id(*pair)
                ]["certificate_sha256"],
            }
            for pair in PAIR_ORDER
        ]
    )
    recipes = [
        item
        for item in universe["recipes"]
        if item["official_contact_point_id"] in CONTACT_IDS
        and item["official_rotation_candidate_index"] in ROTATION_INDICES
        and item["axial_grasp_offset_m"] == 0.0
        and item["pregrasp_distance_m"] == 0.09
    ]
    if len(recipes) != 128:
        raise AssertionError("F2 recovery panel must contain exactly 128 recipes")
    ordered = []
    for rank, recipe in enumerate(recipes, start=1):
        key = _pair_id(
            recipe["main_object_model_id"], recipe["plastic_box_model_id"]
        )
        item = {
            "panel_rank": rank,
            "pair_id": key,
            "stratum": {"pair_id": key, "arm": recipe["arm"]},
            "recipe_id": recipe["recipe_id"],
            "recipe_sha256": recipe["recipe_sha256"],
            "certificate_sha256": certificates[key]["certificate_sha256"],
            "binding_sha256": bindings[key][recipe["arm"]]["binding_sha256"],
            "recipe": recipe,
        }
        item["entry_sha256"] = canonical_hash_json(item)
        ordered.append(item)
    value = {
        "schema_version": "cmf_f2_recovery_planner_manifest_v1",
        "pair_order": [
            {
                "pair_id": _pair_id(*pair),
                "main_object_model_id": pair[0],
                "plastic_box_model_id": pair[1],
                "selection_basis": "current_static_margin_pair"
                if pair == (0, 2)
                else "historical_full_chain_planner_survivor_pair",
            }
            for pair in PAIR_ORDER
        ],
        "certificates_by_pair": certificates,
        "bindings_by_pair_and_arm": bindings,
        "ordered_recipes": ordered,
        "ordered_recipe_sha256s": [item["recipe_sha256"] for item in ordered],
        "recipe_count": len(ordered),
        "stratum_order": [
            {"pair_id": _pair_id(*pair), "arm": arm}
            for pair in PAIR_ORDER
            for arm in ARMS
        ],
        "stage_a_queries_per_recipe": 3,
        "maximum_stage_a_queries": 384,
        "maximum_physical_survivors": 4,
        "selection_per_stratum": "lowest panel-rank passing Stage-A terminal",
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
    }
    value["manifest_sha256"] = canonical_hash_json(value)
    return value


def build_f2_recovery_stage_a_spec_v1(
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any],
    *,
    slot_id: str,
    planner_reset_nonce: int,
) -> dict[str, Any]:
    value = canonical_jsonable(manifest)
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash_json(payload):
        raise ValueError("F2 recovery manifest hash mismatch")
    matches = [
        item
        for item in value["ordered_recipes"]
        if item["entry_sha256"] == entry.get("entry_sha256")
    ]
    if len(matches) != 1 or matches[0] != canonical_jsonable(entry):
        raise ValueError("F2 recovery entry is outside the frozen manifest")
    selected = matches[0]
    pair_id = selected["pair_id"]
    recipe = selected["recipe"]
    return build_f2_final_grasp_stage_a_spec_v2(
        recipe,
        value["certificates_by_pair"][pair_id],
        value["bindings_by_pair_and_arm"][pair_id][recipe["arm"]],
        slot_id=slot_id,
        panel_sha256=value["manifest_sha256"],
        planner_reset_nonce=planner_reset_nonce,
    )


def select_f2_recovery_physical_survivors_v1(
    manifest: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    terminals: Sequence[Mapping[str, Any]],
) -> list[str]:
    value = canonical_jsonable(manifest)
    if len(specs) != len(terminals):
        raise ValueError("F2 recovery specs and terminals must align")
    passing = []
    for spec, terminal in zip(specs, terminals):
        checked = validate_f2_planner_terminal_v2(terminal, spec)
        if checked.get("planner_qualified_for_physical_probe") is True:
            passing.append((canonical_jsonable(spec), checked))
    selected = []
    for stratum in value["stratum_order"]:
        matches = [
            terminal["recipe_sha256"]
            for spec, terminal in passing
            if _pair_id(
                spec["recipe"]["main_object_model_id"],
                spec["recipe"]["plastic_box_model_id"],
            )
            == stratum["pair_id"]
            and spec["recipe"]["arm"] == stratum["arm"]
        ]
        if matches:
            selected.append(matches[0])
    if len(selected) > 4:
        raise AssertionError("F2 recovery selected more than four survivors")
    return selected


__all__ = [
    "PAIR_ORDER",
    "build_f2_recovery_planner_manifest_v1",
    "build_f2_recovery_stage_a_spec_v1",
    "select_f2_recovery_physical_survivors_v1",
]
