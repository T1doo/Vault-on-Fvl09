"""Static foundation for the bounded F2 official-asset redesign matrix.

This module deliberately does not initialize SAPIEN, a planner, or CUDA.  It
enumerates the complete official asset Cartesian product and freezes its order
and provenance.  No static row is selectable: full-envelope inside geometry,
on stability, beside/layout validity, and same-arm planner reachability all
require separately hash-bound evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_f2_official_asset_compatibility_matrix_v3"
ROW_SCHEMA_VERSION = "cmf_f2_official_asset_candidate_row_v3"
EVALUATED_ROW_SCHEMA_VERSION = "cmf_f2_official_asset_evaluated_row_v3"
GATE_RECEIPT_SCHEMA_VERSION = "cmf_f2_official_asset_gate_receipt_v3"
BINDING_SCHEMA_VERSION = "cmf_f2_frozen_asset_layout_binding_v3"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_f2_asset_redesign_v3"

# The review snapshot contains code only, not a second mutable copy of the
# official assets.  Bind both active and snapshot imports to the same audited
# canonical RoboTwin asset tree so inventory hashes cannot depend on where the
# Python module happens to be imported from.
REPO_ROOT = Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin")
ASSET_ROOT = REPO_ROOT / "assets" / "objects"

ASSET_FAMILIES = {
    "main_object": "071_can",
    "plastic_box": "062_plasticbox",
    "electronic_scale": "072_electronicscale",
    "beside_reference": "074_displaystand",
}
EXPECTED_OFFICIAL_IDS = {
    "main_object": (0, 1, 2, 3, 5, 6),
    "plastic_box": tuple(range(11)),
    "electronic_scale": (0, 1, 2, 5, 6),
    "beside_reference": (0, 1, 2, 3, 4),
}
EXECUTION_ARM_ORDER = ("left", "right")
PROGRAM_IDS = ("F2-inside", "F2-on", "F2-beside")
REQUIRED_GATE_IDS = (
    "strict_full_object_inside_margin",
    "on_passive_stability",
    "beside_mutual_exclusion",
    "asset_derived_scene_layout",
    "same_arm_three_branch_planner",
)
MINIMUM_STRICT_INSIDE_MARGIN_M = 0.005


def _copy(value: Any) -> Any:
    return canonical_jsonable(value)


def _hash_json(value: Any) -> str:
    return canonical_hash_json(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_file(root: Path, family: str, model_id: int, kind: str) -> Path:
    family_root = root / family
    candidates = (
        family_root / kind / f"base{model_id}.glb",
        family_root / kind / f"textured{model_id}.obj",
        family_root / f"base{model_id}.glb",
        family_root / f"textured{model_id}.obj",
    )
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FileNotFoundError(f"missing official {kind} asset for {family}/base{model_id}")
    return path


def discover_official_asset_inventory_v3(asset_root: Path = ASSET_ROOT) -> dict[str, Any]:
    """Discover and hash the four finite official F2 asset families."""

    root = Path(asset_root)
    families: dict[str, Any] = {}
    for role, family in ASSET_FAMILIES.items():
        family_root = root / family
        ids = tuple(
            sorted(
                int(path.stem.removeprefix("model_data"))
                for path in family_root.glob("model_data*.json")
            )
        )
        if ids != EXPECTED_OFFICIAL_IDS[role]:
            raise ValueError(
                f"official F2 {role} ID inventory changed: {ids!r} != "
                f"{EXPECTED_OFFICIAL_IDS[role]!r}"
            )
        points_info = family_root / "points_info.json"
        if not points_info.is_file():
            raise FileNotFoundError(points_info)
        records = []
        for model_id in ids:
            model_data = family_root / f"model_data{model_id}.json"
            visual = _asset_file(root, family, model_id, "visual")
            collision = _asset_file(root, family, model_id, "collision")
            record = {
                "role": role,
                "modelname": family,
                "model_id": model_id,
                "model_data_path": str(model_data.relative_to(REPO_ROOT)),
                "model_data_sha256": _sha256_file(model_data),
                "visual_path": str(visual.relative_to(REPO_ROOT)),
                "visual_sha256": _sha256_file(visual),
                "collision_path": str(collision.relative_to(REPO_ROOT)),
                "collision_sha256": _sha256_file(collision),
                "points_info_path": str(points_info.relative_to(REPO_ROOT)),
                "points_info_sha256": _sha256_file(points_info),
            }
            record["asset_record_sha256"] = _hash_json(record)
            records.append(record)
        families[role] = {
            "modelname": family,
            "model_ids": list(ids),
            "records": records,
        }
    result = {
        "schema_version": "cmf_f2_official_asset_inventory_v3",
        "families": families,
    }
    result["inventory_sha256"] = _hash_json(result)
    return result


def _inventory_record_index(inventory: Mapping[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    result = {}
    for role, family in inventory["families"].items():
        for record in family["records"]:
            result[(role, int(record["model_id"]))] = dict(record)
    return result


def _validate_inventory_v3(inventory: Mapping[str, Any]) -> dict[str, Any]:
    value = _copy(inventory)
    digest = value.pop("inventory_sha256", None)
    if not isinstance(digest, str) or _hash_json(value) != digest:
        raise ValueError("F2 official asset inventory hash mismatch")
    families = value.get("families")
    if not isinstance(families, Mapping) or set(families) != set(ASSET_FAMILIES):
        raise ValueError("F2 official asset inventory family set changed")
    for role, modelname in ASSET_FAMILIES.items():
        family = families[role]
        if family.get("modelname") != modelname:
            raise ValueError("F2 official asset inventory modelname changed")
        if tuple(family.get("model_ids", ())) != EXPECTED_OFFICIAL_IDS[role]:
            raise ValueError("F2 official asset inventory IDs changed")
        records = family.get("records")
        if not isinstance(records, list) or len(records) != len(EXPECTED_OFFICIAL_IDS[role]):
            raise ValueError("F2 official asset inventory records missing")
        for expected_id, raw in zip(EXPECTED_OFFICIAL_IDS[role], records):
            record = dict(raw)
            record_digest = record.pop("asset_record_sha256", None)
            if not isinstance(record_digest, str) or _hash_json(record) != record_digest:
                raise ValueError("F2 official asset record hash mismatch")
            if record.get("role") != role or record.get("modelname") != modelname:
                raise ValueError("F2 official asset record identity changed")
            if record.get("model_id") != expected_id:
                raise ValueError("F2 official asset record order changed")
            for name in ("model_data_sha256", "visual_sha256", "collision_sha256", "points_info_sha256"):
                if not isinstance(record.get(name), str) or len(record[name]) != 64:
                    raise ValueError("F2 official asset record lacks a source hash")
    return {**value, "inventory_sha256": digest}


def _candidate_tuple(key: Mapping[str, Any]) -> tuple[int, int, int, int]:
    return tuple(
        int(key[name])
        for name in (
            "main_object_model_id",
            "plastic_box_model_id",
            "electronic_scale_model_id",
            "beside_reference_model_id",
        )
    )


def _pending_gate(gate_id: str) -> dict[str, Any]:
    pending_status = {
        "strict_full_object_inside_margin": "pending_full_envelope_geometry",
        "on_passive_stability": "pending_runtime_physics",
        "beside_mutual_exclusion": "pending_asset_derived_runtime_layout",
        "asset_derived_scene_layout": "pending_fresh_scene_realization",
        "same_arm_three_branch_planner": "pending_runtime_planner",
    }[gate_id]
    return {
        "gate_id": gate_id,
        "status": pending_status,
        "pass": False,
        "evidence_receipt_sha256": None,
        "static_evidence_is_sufficient": False,
    }


def enumerate_static_candidate_rows_v3(inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return all 1,650 candidates in immutable lexicographic rank order."""

    index = _inventory_record_index(inventory)
    ids = {
        role: tuple(inventory["families"][role]["model_ids"])
        for role in ASSET_FAMILIES
    }
    rows = []
    rank = 0
    for can_id in ids["main_object"]:
        for box_id in ids["plastic_box"]:
            for scale_id in ids["electronic_scale"]:
                for stand_id in ids["beside_reference"]:
                    key = {
                        "main_object_model_id": int(can_id),
                        "plastic_box_model_id": int(box_id),
                        "electronic_scale_model_id": int(scale_id),
                        "beside_reference_model_id": int(stand_id),
                    }
                    asset_records = {
                        role: index[(role, model_id)]
                        for role, model_id in (
                            ("main_object", can_id),
                            ("plastic_box", box_id),
                            ("electronic_scale", scale_id),
                            ("beside_reference", stand_id),
                        )
                    }
                    row = {
                        "schema_version": ROW_SCHEMA_VERSION,
                        "rank": rank,
                        "candidate_key": key,
                        "candidate_key_sha256": _hash_json(key),
                        "asset_record_sha256s": {
                            role: value["asset_record_sha256"]
                            for role, value in asset_records.items()
                        },
                        "allowed_execution_arm_order": list(EXECUTION_ARM_ORDER),
                        "program_ids": list(PROGRAM_IDS),
                        "same_main_object_required_for_all_programs": True,
                        "same_execution_arm_required_for_all_programs": True,
                        "branch_specific_asset_or_arm_selection_allowed": False,
                        "gates": {
                            gate_id: _pending_gate(gate_id)
                            for gate_id in REQUIRED_GATE_IDS
                        },
                        "selection_eligible": False,
                        "formal_data": False,
                        "stage0_data": False,
                        "stage1_authorized": False,
                    }
                    row["row_sha256"] = _hash_json(row)
                    rows.append(row)
                    rank += 1
    return rows


def validate_static_candidate_row_v3(row: Mapping[str, Any], *, expected_rank: int | None = None) -> dict[str, Any]:
    value = _copy(row)
    digest = value.pop("row_sha256", None)
    if not isinstance(digest, str) or _hash_json(value) != digest:
        raise ValueError("F2 static candidate row hash mismatch")
    if value.get("schema_version") != ROW_SCHEMA_VERSION:
        raise ValueError("F2 static candidate row schema mismatch")
    if expected_rank is not None and value.get("rank") != expected_rank:
        raise ValueError("F2 static candidate row rank mismatch")
    if value.get("candidate_key_sha256") != _hash_json(value.get("candidate_key")):
        raise ValueError("F2 static candidate key hash mismatch")
    gates = value.get("gates")
    if not isinstance(gates, Mapping) or set(gates) != set(REQUIRED_GATE_IDS):
        raise ValueError("F2 static candidate Gate set changed")
    if any(gates[gate_id].get("gate_id") != gate_id for gate_id in REQUIRED_GATE_IDS):
        raise ValueError("F2 static candidate Gate identity changed")
    if any(item.get("pass") is not False for item in gates.values()):
        raise ValueError("F2 static candidate cannot contain a passed dynamic gate")
    if value.get("selection_eligible") is not False:
        raise ValueError("F2 static candidate cannot be selection eligible")
    if value.get("program_ids") != list(PROGRAM_IDS):
        raise ValueError("F2 program semantics changed")
    if value.get("formal_data") or value.get("stage0_data") or value.get("stage1_authorized"):
        raise ValueError("F2 redesign static row exceeds authorization")
    return {**value, "row_sha256": digest}


def build_static_compatibility_matrix_v3(asset_root: Path = ASSET_ROOT) -> dict[str, Any]:
    inventory = discover_official_asset_inventory_v3(asset_root)
    rows = enumerate_static_candidate_rows_v3(inventory)
    result = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "inventory": inventory,
        "matrix_axes": [
            "main_object_model_id",
            "plastic_box_model_id",
            "electronic_scale_model_id",
            "beside_reference_model_id",
        ],
        "ordering": "ascending_lexicographic_official_model_ids",
        "row_count": len(rows),
        "rows": rows,
        "required_gate_ids": list(REQUIRED_GATE_IDS),
        "selection_contract": "first_all_gates_pass_in_rank_order",
        "selection_status": "not_selected_pending_dynamic_gates",
        "selected_row_sha256": None,
        "cpu_static_conditions_can_satisfy_dynamic_gates": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    result["matrix_sha256"] = _hash_json(result)
    return result


def validate_static_compatibility_matrix_v3(matrix: Mapping[str, Any]) -> dict[str, Any]:
    value = _copy(matrix)
    digest = value.pop("matrix_sha256", None)
    if not isinstance(digest, str) or _hash_json(value) != digest:
        raise ValueError("F2 static compatibility matrix hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("row_count") != 1650:
        raise ValueError("F2 static compatibility matrix schema/count mismatch")
    inventory = _validate_inventory_v3(value.get("inventory", {}))
    inventory_index = _inventory_record_index(inventory)
    rows = value.get("rows")
    if not isinstance(rows, list) or len(rows) != 1650:
        raise ValueError("F2 static compatibility matrix rows missing")
    previous_key = None
    for rank, row in enumerate(rows):
        checked = validate_static_candidate_row_v3(row, expected_rank=rank)
        key = _candidate_tuple(checked["candidate_key"])
        if previous_key is not None and key <= previous_key:
            raise ValueError("F2 static candidate order is not strictly lexicographic")
        previous_key = key
        expected_hashes = {
            role: inventory_index[(role, model_id)]["asset_record_sha256"]
            for role, model_id in zip(ASSET_FAMILIES, key)
        }
        if checked["asset_record_sha256s"] != expected_hashes:
            raise ValueError("F2 candidate row asset hashes differ from inventory")
    if value.get("selected_row_sha256") is not None:
        raise ValueError("F2 static matrix must not preselect an asset tuple")
    if value.get("selection_status") != "not_selected_pending_dynamic_gates":
        raise ValueError("F2 static matrix selection status changed")
    return {**value, "matrix_sha256": digest}


def validate_strict_inside_full_envelope_evidence_v3(
    evidence: Mapping[str, Any], *, candidate_key_sha256: str,
    expected_asset_record_sha256s: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Reject center-line/AABB-only evidence as proof of full-object fit."""

    value = _copy(evidence)
    digest = value.pop("evidence_sha256", None)
    if not isinstance(digest, str) or _hash_json(value) != digest:
        raise ValueError("F2 strict-inside evidence hash mismatch")
    checks = {
        "candidate_bound": value.get("candidate_key_sha256") == candidate_key_sha256,
        "full_object_envelope": value.get("full_object_envelope_checked") is True,
        "complete_cavity_surface": value.get("complete_cavity_collision_surface_checked") is True,
        "not_center_line_only": value.get("center_line_or_axis_interval_only") is False,
        "finite_signed_margin": isinstance(value.get("minimum_signed_margin_m"), (int, float)),
        "minimum_margin": isinstance(value.get("minimum_signed_margin_m"), (int, float))
        and float(value["minimum_signed_margin_m"]) >= MINIMUM_STRICT_INSIDE_MARGIN_M,
        "orientation_frozen": isinstance(value.get("selected_orientation_wxyz"), list)
        and len(value["selected_orientation_wxyz"]) == 4,
        "asset_hashes_bound": isinstance(value.get("asset_record_sha256s"), Mapping)
        and set(value["asset_record_sha256s"]) == {"main_object", "plastic_box"},
    }
    if not all(checks.values()):
        raise ValueError(f"F2 strict full-envelope evidence failed: {checks}")
    if expected_asset_record_sha256s is not None:
        expected = {
            role: expected_asset_record_sha256s[role]
            for role in ("main_object", "plastic_box")
        }
        if value["asset_record_sha256s"] != expected:
            raise ValueError("F2 strict full-envelope evidence asset hashes differ")
    return {**value, "evidence_sha256": digest}


def _validate_non_inside_pass_evidence_v3(gate_id: str, evidence: Mapping[str, Any]) -> None:
    if evidence.get("runtime_or_complete_geometry_evidence") is not True:
        raise ValueError("F2 non-inside Gate pass requires explicit runtime/complete evidence")
    required_true = {
        "on_passive_stability": (
            "passive_250hz_settle_verified",
            "continuous_scale_support",
            "stable_window_pass",
        ),
        "beside_mutual_exclusion": (
            "asset_derived_predicates",
            "zero_overlap",
            "table_clearance_pass",
        ),
        "asset_derived_scene_layout": (
            "fresh_scene_layout_realized",
            "facility_clearance_pass",
        ),
        "same_arm_three_branch_planner": (
            "same_start_qpos_and_seed",
            "complete_planner_chains",
            "same_main_object_for_all_programs",
            "same_execution_arm_for_all_programs",
        ),
    }[gate_id]
    if any(evidence.get(name) is not True for name in required_true):
        raise ValueError(f"F2 {gate_id} pass evidence is incomplete")
    if gate_id == "asset_derived_scene_layout":
        digest = evidence.get("layout_payload_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("F2 layout Gate lacks a payload hash")
    if gate_id == "same_arm_three_branch_planner":
        if evidence.get("selected_execution_arm") not in EXECUTION_ARM_ORDER:
            raise ValueError("F2 planner Gate lacks one valid shared arm")
        if evidence.get("program_ids") != list(PROGRAM_IDS):
            raise ValueError("F2 planner Gate program set changed")


def build_gate_receipt_v3(
    static_row: Mapping[str, Any],
    *,
    gate_id: str,
    status: str,
    evidence: Mapping[str, Any],
    predecessor_gate_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    row = validate_static_candidate_row_v3(static_row)
    if gate_id not in REQUIRED_GATE_IDS or status not in ("passed", "rejected"):
        raise ValueError("invalid F2 compatibility Gate result")
    evidence_value = _copy(evidence)
    if gate_id == "strict_full_object_inside_margin" and status == "passed":
        evidence_value = validate_strict_inside_full_envelope_evidence_v3(
            evidence_value,
            candidate_key_sha256=row["candidate_key_sha256"],
            expected_asset_record_sha256s=row["asset_record_sha256s"],
        )
    elif status == "passed":
        _validate_non_inside_pass_evidence_v3(gate_id, evidence_value)
    gate_index = REQUIRED_GATE_IDS.index(gate_id)
    if gate_index == 0:
        if predecessor_gate_receipt_sha256 is not None:
            raise ValueError("F2 first Gate cannot have a predecessor")
    elif not isinstance(predecessor_gate_receipt_sha256, str) or len(
        predecessor_gate_receipt_sha256
    ) != 64:
        raise ValueError("F2 dynamic Gate requires the previous Gate receipt hash")
    receipt = {
        "schema_version": GATE_RECEIPT_SCHEMA_VERSION,
        "gate_id": gate_id,
        "gate_sequence_index": gate_index,
        "predecessor_gate_receipt_sha256": predecessor_gate_receipt_sha256,
        "status": status,
        "pass": status == "passed",
        "candidate_key_sha256": row["candidate_key_sha256"],
        "static_row_sha256": row["row_sha256"],
        "evidence": evidence_value,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    receipt["gate_receipt_sha256"] = _hash_json(receipt)
    return receipt


def apply_gate_receipts_v3(
    static_row: Mapping[str, Any], receipts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    row = validate_static_candidate_row_v3(static_row)
    by_gate: dict[str, dict[str, Any]] = {}
    for raw in receipts:
        receipt = _copy(raw)
        digest = receipt.pop("gate_receipt_sha256", None)
        if not isinstance(digest, str) or _hash_json(receipt) != digest:
            raise ValueError("F2 Gate receipt hash mismatch")
        if receipt.get("schema_version") != GATE_RECEIPT_SCHEMA_VERSION:
            raise ValueError("F2 Gate receipt schema mismatch")
        if receipt.get("candidate_key_sha256") != row["candidate_key_sha256"]:
            raise ValueError("F2 Gate receipt belongs to another candidate")
        gate_id = receipt.get("gate_id")
        if gate_id not in REQUIRED_GATE_IDS or gate_id in by_gate:
            raise ValueError("F2 Gate receipt is unknown or duplicated")
        if receipt.get("status") not in ("passed", "rejected"):
            raise ValueError("F2 Gate receipt has nonterminal status")
        if receipt.get("pass") is not (receipt["status"] == "passed"):
            raise ValueError("F2 Gate receipt pass/status mismatch")
        if receipt["status"] == "passed":
            if gate_id == "strict_full_object_inside_margin":
                validate_strict_inside_full_envelope_evidence_v3(
                    receipt.get("evidence", {}),
                    candidate_key_sha256=row["candidate_key_sha256"],
                    expected_asset_record_sha256s=row["asset_record_sha256s"],
                )
            else:
                _validate_non_inside_pass_evidence_v3(
                    gate_id, receipt.get("evidence", {})
                )
        by_gate[gate_id] = {**receipt, "gate_receipt_sha256": digest}
    gates = _copy(row["gates"])
    previous_digest = None
    encountered_gap = False
    for gate_id in REQUIRED_GATE_IDS:
        receipt = by_gate.get(gate_id)
        if receipt is None:
            encountered_gap = True
            continue
        if encountered_gap:
            raise ValueError("F2 Gate receipts cannot skip an earlier Gate")
        expected_index = REQUIRED_GATE_IDS.index(gate_id)
        if receipt.get("gate_sequence_index") != expected_index:
            raise ValueError("F2 Gate receipt sequence index changed")
        if receipt.get("predecessor_gate_receipt_sha256") != previous_digest:
            raise ValueError("F2 Gate receipt predecessor chain mismatch")
        previous_digest = receipt["gate_receipt_sha256"]
    for gate_id, receipt in by_gate.items():
        gates[gate_id] = {
            "gate_id": gate_id,
            "status": receipt["status"],
            "pass": receipt["pass"],
            "evidence_receipt_sha256": receipt["gate_receipt_sha256"],
            "static_evidence_is_sufficient": False,
        }
    eligible = all(gates[gate_id]["pass"] is True for gate_id in REQUIRED_GATE_IDS)
    result = {
        "schema_version": EVALUATED_ROW_SCHEMA_VERSION,
        "rank": row["rank"],
        "candidate_key": row["candidate_key"],
        "candidate_key_sha256": row["candidate_key_sha256"],
        "static_row_sha256": row["row_sha256"],
        "asset_record_sha256s": row["asset_record_sha256s"],
        "allowed_execution_arm_order": row["allowed_execution_arm_order"],
        "program_ids": row["program_ids"],
        "gates": gates,
        "gate_receipts": by_gate,
        "selection_eligible": eligible,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    result["evaluated_row_sha256"] = _hash_json(result)
    return result


def validate_evaluated_candidate_row_v3(row: Mapping[str, Any]) -> dict[str, Any]:
    value = _copy(row)
    digest = value.pop("evaluated_row_sha256", None)
    if not isinstance(digest, str) or _hash_json(value) != digest:
        raise ValueError("F2 evaluated row hash mismatch")
    if value.get("schema_version") != EVALUATED_ROW_SCHEMA_VERSION:
        raise ValueError("F2 evaluated row schema mismatch")
    if value.get("candidate_key_sha256") != _hash_json(value.get("candidate_key")):
        raise ValueError("F2 evaluated candidate key hash mismatch")
    if value.get("program_ids") != list(PROGRAM_IDS):
        raise ValueError("F2 evaluated row program semantics changed")
    hashes = value.get("asset_record_sha256s")
    if not isinstance(hashes, Mapping) or set(hashes) != set(ASSET_FAMILIES):
        raise ValueError("F2 evaluated row asset hashes missing")
    gates = value.get("gates")
    receipts = value.get("gate_receipts")
    if not isinstance(gates, Mapping) or set(gates) != set(REQUIRED_GATE_IDS):
        raise ValueError("F2 evaluated row Gate set changed")
    if not isinstance(receipts, Mapping) or not set(receipts).issubset(REQUIRED_GATE_IDS):
        raise ValueError("F2 evaluated row receipts invalid")
    for gate_id in REQUIRED_GATE_IDS:
        gate = gates[gate_id]
        status = gate.get("status")
        if str(status).startswith("pending_"):
            if gate_id in receipts or gate.get("pass") is not False:
                raise ValueError("F2 pending Gate cannot carry terminal evidence")
            continue
        if status not in ("passed", "rejected") or gate_id not in receipts:
            raise ValueError("F2 terminal Gate lacks a receipt")
        receipt = dict(receipts[gate_id])
        receipt_digest = receipt.pop("gate_receipt_sha256", None)
        if not isinstance(receipt_digest, str) or _hash_json(receipt) != receipt_digest:
            raise ValueError("F2 evaluated Gate receipt hash mismatch")
        if gate.get("evidence_receipt_sha256") != receipt_digest:
            raise ValueError("F2 evaluated Gate does not bind its receipt")
        if receipt.get("gate_id") != gate_id or receipt.get("status") != status:
            raise ValueError("F2 evaluated Gate/receipt result differs")
        expected_index = REQUIRED_GATE_IDS.index(gate_id)
        expected_predecessor = (
            None
            if expected_index == 0
            else receipts[REQUIRED_GATE_IDS[expected_index - 1]][
                "gate_receipt_sha256"
            ]
        )
        if receipt.get("gate_sequence_index") != expected_index or receipt.get(
            "predecessor_gate_receipt_sha256"
        ) != expected_predecessor:
            raise ValueError("F2 evaluated Gate receipt chain changed")
        if receipt.get("candidate_key_sha256") != value["candidate_key_sha256"]:
            raise ValueError("F2 evaluated Gate receipt candidate differs")
        if receipt.get("pass") is not (status == "passed") or gate.get("pass") is not receipt.get("pass"):
            raise ValueError("F2 evaluated Gate pass/status mismatch")
        if status == "passed":
            if gate_id == "strict_full_object_inside_margin":
                validate_strict_inside_full_envelope_evidence_v3(
                    receipt.get("evidence", {}),
                    candidate_key_sha256=value["candidate_key_sha256"],
                    expected_asset_record_sha256s=hashes,
                )
            else:
                _validate_non_inside_pass_evidence_v3(gate_id, receipt.get("evidence", {}))
    eligible = all(gates[gate_id].get("pass") is True for gate_id in REQUIRED_GATE_IDS)
    if value.get("selection_eligible") is not eligible:
        raise ValueError("F2 evaluated row eligibility differs from Gate conjunction")
    if value.get("formal_data") or value.get("stage0_data") or value.get("stage1_authorized"):
        raise ValueError("F2 evaluated row exceeds authorization")
    return {**value, "evaluated_row_sha256": digest}


def select_first_all_gates_pass_v3(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Select only the first eligible row; never skip an unresolved earlier row."""

    ordered = sorted((_copy(row) for row in rows), key=lambda item: int(item["rank"]))
    for expected_rank, raw in enumerate(ordered):
        row = validate_evaluated_candidate_row_v3(raw)
        if int(row["rank"]) != expected_rank:
            raise ValueError("F2 evaluated rows must be a complete rank prefix")
        gates = row.get("gates", {})
        statuses = [gates.get(gate_id, {}).get("status") for gate_id in REQUIRED_GATE_IDS]
        if any(str(status).startswith("pending_") for status in statuses):
            return None
        all_pass = all(gates[gate_id].get("pass") is True for gate_id in REQUIRED_GATE_IDS)
        if all_pass:
            if row.get("selection_eligible") is not True:
                raise ValueError("F2 all-pass row is not marked eligible")
            return row
        if not any(status == "rejected" for status in statuses):
            raise ValueError("F2 nonpassing evaluated row lacks terminal rejection")
    return None


def build_frozen_asset_layout_binding_v3(
    *,
    selected_row: Mapping[str, Any],
    matrix_sha256: str,
    selected_execution_arm: str,
    layout_version: str,
    layout_payload: Mapping[str, Any],
    preceding_evaluated_rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    prefix = [*preceding_evaluated_rows, selected_row]
    selected = select_first_all_gates_pass_v3(prefix)
    if (
        selected is None
        or selected.get("evaluated_row_sha256")
        != selected_row.get("evaluated_row_sha256")
    ):
        raise ValueError("F2 binding requires a verified first-all-Gates rank prefix")
    planner = selected["gate_receipts"]["same_arm_three_branch_planner"]["evidence"]
    if selected_execution_arm not in EXECUTION_ARM_ORDER:
        raise ValueError("F2 selected execution arm is not allowed")
    if planner.get("selected_execution_arm") != selected_execution_arm:
        raise ValueError("F2 planner receipt arm differs from binding arm")
    layout_receipt = selected["gate_receipts"]["asset_derived_scene_layout"]["evidence"]
    layout_sha = _hash_json(layout_payload)
    if layout_receipt.get("layout_payload_sha256") != layout_sha:
        raise ValueError("F2 selected layout differs from Gate evidence")
    value = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "matrix_sha256": matrix_sha256,
        "selected_evaluated_row_sha256": selected["evaluated_row_sha256"],
        "selected_candidate_key": selected["candidate_key"],
        "asset_record_sha256s": selected["asset_record_sha256s"],
        "selected_execution_arm": selected_execution_arm,
        "layout_version": layout_version,
        "layout_payload": _copy(layout_payload),
        "layout_payload_sha256": layout_sha,
        "program_ids": list(PROGRAM_IDS),
        "same_main_object_for_all_programs": True,
        "same_execution_arm_for_all_programs": True,
        "branch_specific_asset_or_arm_selection_allowed": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["binding_sha256"] = _hash_json(value)
    return value


def validate_frozen_asset_layout_binding_v3(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _copy(value)
    digest = result.pop("binding_sha256", None)
    if not isinstance(digest, str) or _hash_json(result) != digest:
        raise ValueError("F2 frozen asset/layout binding hash mismatch")
    if result.get("schema_version") != BINDING_SCHEMA_VERSION:
        raise ValueError("F2 frozen asset/layout binding schema mismatch")
    if result.get("layout_payload_sha256") != _hash_json(result.get("layout_payload")):
        raise ValueError("F2 frozen asset/layout payload hash mismatch")
    if result.get("layout_version") != result.get("layout_payload", {}).get("layout_version"):
        raise ValueError("F2 frozen asset/layout version mismatch")
    key = result.get("selected_candidate_key")
    if not isinstance(key, Mapping):
        raise ValueError("F2 frozen asset/layout candidate key missing")
    candidate = _candidate_tuple(key)
    if any(model_id not in EXPECTED_OFFICIAL_IDS[role] for role, model_id in zip(ASSET_FAMILIES, candidate)):
        raise ValueError("F2 frozen asset/layout candidate is not official")
    hashes = result.get("asset_record_sha256s")
    if not isinstance(hashes, Mapping) or set(hashes) != set(ASSET_FAMILIES):
        raise ValueError("F2 frozen asset/layout asset hashes missing")
    if any(not isinstance(item, str) or len(item) != 64 for item in hashes.values()):
        raise ValueError("F2 frozen asset/layout asset hash invalid")
    for name in ("matrix_sha256", "selected_evaluated_row_sha256"):
        if not isinstance(result.get(name), str) or len(result[name]) != 64:
            raise ValueError(f"F2 frozen asset/layout {name} invalid")
    if result.get("selected_execution_arm") not in EXECUTION_ARM_ORDER:
        raise ValueError("F2 frozen asset/layout arm invalid")
    if result.get("program_ids") != list(PROGRAM_IDS):
        raise ValueError("F2 frozen asset/layout programs changed")
    if result.get("formal_data") or result.get("stage0_data") or result.get("stage1_authorized"):
        raise ValueError("F2 frozen asset/layout binding exceeds authorization")
    return {**result, "binding_sha256": digest}


__all__ = [
    "ASSET_FAMILIES",
    "EXPECTED_OFFICIAL_IDS",
    "EXECUTION_ARM_ORDER",
    "MINIMUM_STRICT_INSIDE_MARGIN_M",
    "PROGRAM_IDS",
    "REQUIRED_GATE_IDS",
    "apply_gate_receipts_v3",
    "build_frozen_asset_layout_binding_v3",
    "build_gate_receipt_v3",
    "build_static_compatibility_matrix_v3",
    "discover_official_asset_inventory_v3",
    "enumerate_static_candidate_rows_v3",
    "select_first_all_gates_pass_v3",
    "validate_frozen_asset_layout_binding_v3",
    "validate_evaluated_candidate_row_v3",
    "validate_static_candidate_row_v3",
    "validate_static_compatibility_matrix_v3",
    "validate_strict_inside_full_envelope_evidence_v3",
]
