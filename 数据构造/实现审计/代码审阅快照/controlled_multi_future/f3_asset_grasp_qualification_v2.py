"""Asset-level F3 bottle and grasp qualification contract.

This is a pure-CPU contract.  It inventories every official ``001_bottle``
model, freezes a bounded four-asset/eight-grasp search, and keeps the F3
VVHH/VHVH/VHHV scientific semantics unchanged.  Planner and physical results
must be supplied later as candidate-bound receipts.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_f3_asset_grasp_qualification_v2"
IMPLEMENTATION_VERSION = "controlled_multi_future_f3_asset_grasp_qualification_v2"
SCOPE = "F3_ASSET_GRASP_QUALIFICATION_V2"
ASSET_ROOT = Path(
    "/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets/objects/001_bottle"
)
PROGRAM_IDS = ("F3-VVHH", "F3-VHVH", "F3-VHHV")
OFFICIAL_SHAKE_MODEL_IDS = tuple(range(20))
OFFICIAL_ADJUST_MODEL_IDS = (13, 16)
MAXIMUM_SELECTED_ASSETS = 4
GRASP_CONTRACTS_PER_ASSET = 2
MAXIMUM_GRASP_TUPLES = 8
MAXIMUM_PHYSICAL_TUPLES = 4
OFFICIAL_SHAKE_RUNTIME_MASS_KG = 0.01
GRIPPER_COMPATIBLE_DIAMETER_RANGE_M = (0.060, 0.110)
SUITABLE_HEIGHT_RANGE_M = (0.200, 0.280)

REQUIRED_LEVEL2_GATES = (
    "planner_success",
    "selected_gripper_contact_continuity",
    "bottle_off_support_after_lift",
    "grasp_transform_translation_stable",
    "grasp_transform_orientation_stable",
    "bottle_linear_stability",
    "bottle_angular_stability",
    "eef_tracking",
    "shared_v_realized_amplitude",
    "shared_v_closed_loop_return",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _model_id(path: Path) -> int:
    return int(path.stem.removeprefix("model_data"))


def _scaled_extents(data: Mapping[str, Any]) -> list[float]:
    extents = [float(value) for value in data["extents"]]
    scale = [float(value) for value in data["scale"]]
    if len(extents) != 3 or len(scale) != 3:
        raise ValueError("F3 bottle extents/scale must be three-dimensional")
    return [left * right for left, right in zip(extents, scale)]


def build_official_bottle_inventory_v2(asset_root: Path = ASSET_ROOT) -> dict[str, Any]:
    paths = sorted(Path(asset_root).glob("model_data*.json"), key=_model_id)
    ids = [_model_id(path) for path in paths]
    if ids != list(range(23)):
        raise ValueError("F3 official bottle inventory must contain model IDs 0..22")
    records = []
    for path in paths:
        model_id = _model_id(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        scaled = _scaled_extents(data)
        radial = [scaled[0], scaled[2]]
        diameter = max(radial)
        regularity = max(radial) / min(radial)
        contact_count = len(data.get("contact_points_pose") or [])
        shake_compatible = model_id in OFFICIAL_SHAKE_MODEL_IDS
        adjust_compatible = model_id in OFFICIAL_ADJUST_MODEL_IDS
        suitable = bool(
            data.get("stable") is True
            and contact_count >= 8
            and bool(data.get("orientation_point"))
            and GRIPPER_COMPATIBLE_DIAMETER_RANGE_M[0]
            <= diameter
            <= GRIPPER_COMPATIBLE_DIAMETER_RANGE_M[1]
            and SUITABLE_HEIGHT_RANGE_M[0] <= scaled[1] <= SUITABLE_HEIGHT_RANGE_M[1]
            and shake_compatible
        )
        record = {
            "model_id": model_id,
            "model_data_path": str(path),
            "model_data_sha256": _sha256_file(path),
            "scaled_extents_m": scaled,
            "long_axis_model_axis": 1,
            "body_height_m": scaled[1],
            "maximum_radial_diameter_m": diameter,
            "radial_regularity_ratio": regularity,
            "stable_metadata": data.get("stable") is True,
            "contact_point_count": contact_count,
            "contact_group_count": len(data.get("contact_points_group") or []),
            "functional_matrix_count": len(data.get("functional_matrix") or []),
            "orientation_point_available": bool(data.get("orientation_point")),
            "official_shake_task_compatible": shake_compatible,
            "official_adjust_task_compatible": adjust_compatible,
            "model_data_mass_available": False,
            "official_shake_runtime_mass_kg": (
                OFFICIAL_SHAKE_RUNTIME_MASS_KG if shake_compatible else None
            ),
            "center_of_mass_metadata_available": False,
            "lower_center_of_mass_claim_allowed": False,
            "gripper_diameter_screen_range_m": list(
                GRIPPER_COMPATIBLE_DIAMETER_RANGE_M
            ),
            "cpu_suitable": suitable,
        }
        record["record_sha256"] = canonical_hash_json(record)
        records.append(record)
    value = {
        "schema_version": "cmf_f3_official_bottle_inventory_v2",
        "asset_root": str(Path(asset_root)),
        "model_ids": ids,
        "model_count": len(records),
        "official_shake_model_ids": list(OFFICIAL_SHAKE_MODEL_IDS),
        "official_adjust_model_ids": list(OFFICIAL_ADJUST_MODEL_IDS),
        "records": records,
        "mass_metadata_finding": (
            "model_data has no mass field; official shake tasks set actor mass to 0.01 kg"
        ),
        "center_of_mass_finding": (
            "no authoritative per-model center-of-mass metadata is available; no lower-CoM ranking claim is made"
        ),
    }
    value["inventory_sha256"] = canonical_hash_json(value)
    return value


def _asset_rank_key(record: Mapping[str, Any]) -> tuple[Any, ...]:
    # Narrow, regular bodies around 82 mm are preferred after hard suitability.
    # Rich official contact metadata precedes task-list membership; base13 is
    # therefore not privileged merely because adjust_bottle names it.
    return (
        abs(float(record["maximum_radial_diameter_m"]) - 0.082),
        float(record["radial_regularity_ratio"]),
        -int(record["contact_point_count"]),
        -int(record["functional_matrix_count"]),
        -int(record["official_adjust_task_compatible"]),
        int(record["model_id"]),
    )


def select_bottle_assets_v2(inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = canonical_jsonable(inventory)["records"]
    eligible = [record for record in records if record["cpu_suitable"] is True]
    selected = sorted(eligible, key=_asset_rank_key)[:MAXIMUM_SELECTED_ASSETS]
    if len(selected) != MAXIMUM_SELECTED_ASSETS:
        raise ValueError("F3 asset qualification requires four suitable official bottles")
    return selected


def _grasp_tuple(
    *, rank: int, asset: Mapping[str, Any], variant_index: int
) -> dict[str, Any]:
    if variant_index not in (0, 1):
        raise ValueError("F3 V2 grasp variant must be 0 or 1")
    region = "lower_body" if variant_index == 0 else "upper_body"
    fraction = -0.15 if variant_index == 0 else 0.15
    arm = "left" if variant_index == 0 else "right"
    contact_id = 0 if variant_index == 0 else 3
    model_id = int(asset["model_id"])
    value = {
        "rank": rank,
        "tuple_id": f"f3-asset-grasp-v2-r{rank:02d}",
        "asset": {"modelname": "001_bottle", "model_id": model_id},
        "asset_record_sha256": asset["record_sha256"],
        "arm": arm,
        "grasp_region": region,
        "long_axis_model_axis": 1,
        "region_center_fraction_from_geometric_center": fraction,
        "region_center_offset_m": fraction * float(asset["body_height_m"]),
        "official_contact_point_id": contact_id,
        "local_orientation_source": "official_contact_point_pose",
        "pregrasp_distance_m": 0.09,
        "target_distance_m": 0.0,
        "close_normalized_target": 0.50,
        "post_close_settle_frames": 250,
        "genuinely_distinct_height_region": True,
        "program_independent": True,
        "vh_axes_changed": False,
        "programs_changed": False,
        "verifier_thresholds_changed": False,
        "online_fallback": False,
    }
    value["tuple_sha256"] = canonical_hash_json(value)
    return value


def build_f3_asset_grasp_qualification_v2(
    asset_root: Path = ASSET_ROOT,
) -> dict[str, Any]:
    inventory = build_official_bottle_inventory_v2(asset_root)
    assets = select_bottle_assets_v2(inventory)
    tuples = []
    for asset in assets:
        for variant_index in range(GRASP_CONTRACTS_PER_ASSET):
            tuples.append(
                _grasp_tuple(
                    rank=len(tuples) + 1,
                    asset=asset,
                    variant_index=variant_index,
                )
            )
    if len(tuples) != MAXIMUM_GRASP_TUPLES:
        raise AssertionError("F3 V2 grasp tuple bound changed")
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "family": "F3",
        "program_ids": list(PROGRAM_IDS),
        "inventory": inventory,
        "inventory_sha256": inventory["inventory_sha256"],
        "selected_assets": deepcopy(assets),
        "selected_asset_model_ids": [item["model_id"] for item in assets],
        "maximum_selected_assets": MAXIMUM_SELECTED_ASSETS,
        "grasp_contracts_per_asset": GRASP_CONTRACTS_PER_ASSET,
        "maximum_grasp_tuples": MAXIMUM_GRASP_TUPLES,
        "maximum_physical_tuples": MAXIMUM_PHYSICAL_TUPLES,
        "fixed_tuple_order": [item["tuple_id"] for item in tuples],
        "grasp_tuples": tuples,
        "level1_sequence": [
            "pregrasp",
            "grasp",
            "lift",
            "central",
            "one_V",
            "return",
        ],
        "level2_sequence": [
            "fresh_scene",
            "approach",
            "grasp",
            "close",
            "lift",
            "central",
            "settle",
            "V_plus",
            "V_minus",
            "return",
            "settle",
        ],
        "required_level2_gates": list(REQUIRED_LEVEL2_GATES),
        "three_scene_confirmation_required": 3,
        "root_allowed_only_after_three_scene_pass": True,
        "exhaustion_status": (
            "OFFICIAL_BOTTLE_GRASP_SEARCH_EXHAUSTED_REQUIRES_OBJECT_FAMILY_REDESIGN"
        ),
        "success_status": "PASS_F3_STABLE_GRASP_AND_TEMPORAL_ROOT",
        "block_substitution_allowed": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "training_authorized": False,
    }
    value["qualification_sha256"] = canonical_hash_json(value)
    return value


def validate_f3_asset_grasp_qualification_v2(
    value: Mapping[str, Any], asset_root: Path = ASSET_ROOT
) -> dict[str, Any]:
    expected = build_f3_asset_grasp_qualification_v2(asset_root)
    if canonical_jsonable(value) != expected:
        raise ValueError("F3 asset/grasp qualification V2 contract changed")
    return expected


def select_level2_tuples_v2(
    contract: Mapping[str, Any], planner_receipts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    checked = validate_f3_asset_grasp_qualification_v2(contract)
    by_id = {str(item.get("tuple_id")): canonical_jsonable(item) for item in planner_receipts}
    if set(by_id) != set(checked["fixed_tuple_order"]):
        raise ValueError("F3 V2 planner receipts must cover all eight tuples")
    ordered = [by_id[tuple_id] for tuple_id in checked["fixed_tuple_order"]]
    tuples = {item["tuple_id"]: item for item in checked["grasp_tuples"]}
    for receipt in ordered:
        expected = tuples[receipt["tuple_id"]]
        if (
            receipt.get("tuple_sha256") != expected["tuple_sha256"]
            or not isinstance(receipt.get("planner_success"), bool)
        ):
            raise ValueError("F3 V2 planner receipt is not tuple-bound")
    selected = [item["tuple_id"] for item in ordered if item["planner_success"]][
        :MAXIMUM_PHYSICAL_TUPLES
    ]
    value = {
        "schema_version": "cmf_f3_asset_grasp_level1_terminal_v2",
        "qualification_sha256": checked["qualification_sha256"],
        "planner_receipts": ordered,
        "level2_tuple_ids": selected,
        "maximum_physical_tuples": MAXIMUM_PHYSICAL_TUPLES,
        "level1_exhausted": not selected,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def select_stable_grasp_v2(
    contract: Mapping[str, Any],
    level1_terminal: Mapping[str, Any],
    physical_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checked = validate_f3_asset_grasp_qualification_v2(contract)
    selected_ids = list(level1_terminal.get("level2_tuple_ids", []))
    by_id = {str(item.get("tuple_id")): canonical_jsonable(item) for item in physical_receipts}
    if set(by_id) != set(selected_ids):
        raise ValueError("F3 V2 physical receipts must cover the selected bounded set")
    tuples = {item["tuple_id"]: item for item in checked["grasp_tuples"]}
    ordered = [by_id[tuple_id] for tuple_id in selected_ids]
    passing = []
    for receipt in ordered:
        expected = tuples[receipt["tuple_id"]]
        gates = receipt.get("gates")
        if receipt.get("tuple_sha256") != expected["tuple_sha256"]:
            raise ValueError("F3 V2 physical receipt tuple hash mismatch")
        if (
            isinstance(gates, Mapping)
            and set(gates) == set(REQUIRED_LEVEL2_GATES)
            and all(gates[name] is True for name in REQUIRED_LEVEL2_GATES)
            and receipt.get("sequence_complete") is True
            and receipt.get("cleanup_safety_pass") is True
            and receipt.get("orphan_process_count") == 0
        ):
            passing.append(expected)
    selected = passing[0] if passing else None
    value = {
        "schema_version": "cmf_f3_asset_grasp_level2_terminal_v2",
        "qualification_sha256": checked["qualification_sha256"],
        "physical_receipts": ordered,
        "selected_stable_grasp": selected,
        "status": (
            "STABLE_GRASP_REQUIRES_THREE_FRESH_SCENES"
            if selected is not None
            else checked["exhaustion_status"]
        ),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "ASSET_ROOT",
    "MAXIMUM_GRASP_TUPLES",
    "MAXIMUM_PHYSICAL_TUPLES",
    "MAXIMUM_SELECTED_ASSETS",
    "PROGRAM_IDS",
    "REQUIRED_LEVEL2_GATES",
    "build_f3_asset_grasp_qualification_v2",
    "build_official_bottle_inventory_v2",
    "select_bottle_assets_v2",
    "select_level2_tuples_v2",
    "select_stable_grasp_v2",
    "validate_f3_asset_grasp_qualification_v2",
]
