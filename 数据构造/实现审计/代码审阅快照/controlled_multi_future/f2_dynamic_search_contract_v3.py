"""Bounded CPU screening and dynamic-candidate selection contract for F2 V3."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .f2_asset_geometry_layout_v3 import (
    evaluate_asset_derived_layout_cpu_v3,
    evaluate_strict_full_envelope_inside_v3,
)
from .f2_official_asset_compatibility_matrix_v3 import (
    BINDING_SCHEMA_VERSION,
    DESIGN_VERSION,
    IMPLEMENTATION_VERSION,
    PROGRAM_IDS,
    REQUIRED_GATE_IDS,
    validate_frozen_asset_layout_binding_v3,
    validate_evaluated_candidate_row_v3,
    validate_static_compatibility_matrix_v3,
)


SCREENING_SCHEMA_VERSION = "cmf_f2_cpu_static_screening_v3"
DYNAMIC_SCOPE_SCHEMA_VERSION = "cmf_f2_bounded_dynamic_candidate_scope_v3"
MAX_DYNAMIC_CANDIDATES = 12


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


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


def _decision(value: dict[str, Any]) -> dict[str, Any]:
    value["decision_sha256"] = _hash_json(value)
    return value


def _rebind_inside_receipt(receipt: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    """Reuse pair-only geometry while binding each Cartesian row independently."""

    value = _copy(receipt)
    value.pop("evidence_sha256", None)
    value["candidate_key_sha256"] = row["candidate_key_sha256"]
    value["candidate_key"] = row["candidate_key"]
    value["asset_record_sha256s"] = {
        role: row["asset_record_sha256s"][role]
        for role in ("main_object", "plastic_box")
    }
    value["pair_geometry_reused_across_scale_and_reference_rows"] = True
    value["evidence_sha256"] = _hash_json(value)
    return value


def build_cpu_static_screening_v3(
    matrix: Mapping[str, Any], *, max_dynamic_candidates: int = MAX_DYNAMIC_CANDIDATES
) -> dict[str, Any]:
    """Terminalize CPU screens for all rows without passing any dynamic Gate."""

    checked = validate_static_compatibility_matrix_v3(matrix)
    if max_dynamic_candidates != MAX_DYNAMIC_CANDIDATES:
        raise ValueError("F2 dynamic-candidate cap is frozen at 12")
    pair_cache: dict[tuple[int, int], dict[str, Any]] = {}
    row_receipts = []
    admissible = []
    for row in checked["rows"]:
        key = row["candidate_key"]
        pair = (
            int(key["main_object_model_id"]),
            int(key["plastic_box_model_id"]),
        )
        if pair not in pair_cache:
            pair_cache[pair] = evaluate_strict_full_envelope_inside_v3(row)
            inside = pair_cache[pair]
        else:
            inside = _rebind_inside_receipt(pair_cache[pair], row)
        layout = evaluate_asset_derived_layout_cpu_v3(row, inside)
        cpu_pass = inside.get("pass") is True and layout.get("pass") is True
        gate_statuses = {
            gate_id: row["gates"][gate_id]["status"] for gate_id in REQUIRED_GATE_IDS
        }
        if not all(str(status).startswith("pending_") for status in gate_statuses.values()):
            raise ValueError("F2 CPU screening received a non-pending dynamic Gate")
        receipt = {
            "schema_version": "cmf_f2_cpu_static_candidate_receipt_v3",
            "rank": row["rank"],
            "candidate_key": row["candidate_key"],
            "candidate_key_sha256": row["candidate_key_sha256"],
            "static_row_sha256": row["row_sha256"],
            "asset_record_sha256s": row["asset_record_sha256s"],
            "inside_cpu_evidence_sha256": inside["evidence_sha256"],
            "inside_cpu_evidence": inside,
            "inside_cpu_status": inside["status"],
            "layout_cpu_receipt_sha256": layout["receipt_sha256"],
            "layout_cpu_receipt": layout,
            "layout_cpu_status": layout["status"],
            "cpu_static_admissible": cpu_pass,
            "dynamic_gate_statuses": gate_statuses,
            "dynamic_gate_pass_count": 0,
            "selection_eligible": False,
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        receipt["receipt_sha256"] = _hash_json(receipt)
        row_receipts.append(receipt)
        if cpu_pass:
            admissible.append(receipt)
    scoped = admissible[:MAX_DYNAMIC_CANDIDATES]
    scope_rows = [
        {
            "scope_index": index,
            "rank": item["rank"],
            "candidate_key": item["candidate_key"],
            "candidate_key_sha256": item["candidate_key_sha256"],
            "cpu_static_candidate_receipt_sha256": item["receipt_sha256"],
            "dynamic_status": "pending_dynamic_gates",
        }
        for index, item in enumerate(scoped)
    ]
    scope = {
        "schema_version": DYNAMIC_SCOPE_SCHEMA_VERSION,
        "ordering": "first_cpu_static_admissible_rows_in_global_rank_order",
        "maximum_dynamic_candidates": MAX_DYNAMIC_CANDIDATES,
        "candidate_count": len(scope_rows),
        "candidates": scope_rows,
        "fallback_beyond_candidate_12_allowed": False,
        "skip_pending_earlier_candidate_allowed": False,
        "no_all_gate_pass_outcome": "higher_level_redesign_required",
        "selected_candidate_evaluated_row_sha256": None,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    scope["scope_sha256"] = _hash_json(scope)
    result = {
        "schema_version": SCREENING_SCHEMA_VERSION,
        "matrix_sha256": checked["matrix_sha256"],
        "row_count": len(row_receipts),
        "terminal_cpu_candidate_receipts": row_receipts,
        "strict_inside_unique_pair_evaluation_count": len(pair_cache),
        "cpu_static_admissible_count": len(admissible),
        "dynamic_scope": scope,
        "status": (
            "pending_bounded_dynamic_candidate_audit"
            if scope_rows
            else "higher_level_redesign_required_no_cpu_static_admissible_candidate"
        ),
        "selected_binding": None,
        "development_root_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    result["screening_sha256"] = _hash_json(result)
    return result


def validate_cpu_static_screening_v3(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _copy(value)
    digest = result.pop("screening_sha256", None)
    if not isinstance(digest, str) or _hash_json(result) != digest:
        raise ValueError("F2 CPU static screening hash mismatch")
    if result.get("schema_version") != SCREENING_SCHEMA_VERSION or result.get("row_count") != 1650:
        raise ValueError("F2 CPU static screening schema/count mismatch")
    receipts = result.get("terminal_cpu_candidate_receipts")
    if not isinstance(receipts, list) or len(receipts) != 1650:
        raise ValueError("F2 CPU static screening receipts missing")
    for rank, raw in enumerate(receipts):
        receipt = dict(raw)
        receipt_digest = receipt.pop("receipt_sha256", None)
        if not isinstance(receipt_digest, str) or _hash_json(receipt) != receipt_digest:
            raise ValueError("F2 CPU static candidate receipt hash mismatch")
        if receipt.get("rank") != rank or receipt.get("dynamic_gate_pass_count") != 0:
            raise ValueError("F2 CPU static receipt rank/Gate count invalid")
        if receipt.get("selection_eligible") is not False:
            raise ValueError("F2 CPU static receipt cannot select a candidate")
        inside = dict(receipt.get("inside_cpu_evidence", {}))
        inside_digest = inside.pop("evidence_sha256", None)
        if inside_digest != receipt.get("inside_cpu_evidence_sha256") or _hash_json(inside) != inside_digest:
            raise ValueError("F2 CPU static inside evidence hash mismatch")
        layout = dict(receipt.get("layout_cpu_receipt", {}))
        layout_digest = layout.pop("receipt_sha256", None)
        if layout_digest != receipt.get("layout_cpu_receipt_sha256") or _hash_json(layout) != layout_digest:
            raise ValueError("F2 CPU static layout receipt hash mismatch")
        statuses = receipt.get("dynamic_gate_statuses", {})
        if set(statuses) != set(REQUIRED_GATE_IDS) or not all(
            str(status).startswith("pending_") for status in statuses.values()
        ):
            raise ValueError("F2 CPU static receipt forged a dynamic Gate")
    scope = dict(result.get("dynamic_scope", {}))
    scope_digest = scope.pop("scope_sha256", None)
    if not isinstance(scope_digest, str) or _hash_json(scope) != scope_digest:
        raise ValueError("F2 bounded dynamic scope hash mismatch")
    candidates = scope.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > MAX_DYNAMIC_CANDIDATES:
        raise ValueError("F2 bounded dynamic scope exceeds 12 candidates")
    admissible_ranks = [
        item["rank"] for item in receipts if item["cpu_static_admissible"] is True
    ][:MAX_DYNAMIC_CANDIDATES]
    if [item.get("rank") for item in candidates] != admissible_ranks:
        raise ValueError("F2 bounded dynamic scope skipped/reordered static candidates")
    if result.get("selected_binding") is not None or result.get("development_root_authorized") is not False:
        raise ValueError("F2 CPU screening cannot authorize a development root")
    return {**result, "screening_sha256": digest}


def decide_bounded_dynamic_search_v3(
    screening: Mapping[str, Any], evaluated_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Enforce first-all-Gates within the frozen <=12 candidate scope."""

    checked = validate_cpu_static_screening_v3(screening)
    candidates = checked["dynamic_scope"]["candidates"]
    if len(evaluated_rows) > len(candidates):
        raise ValueError("F2 dynamic evidence exceeds the frozen candidate scope")
    selected = None
    terminal_rejected_count = 0
    for scope_index, raw in enumerate(evaluated_rows):
        row = validate_evaluated_candidate_row_v3(raw)
        candidate = candidates[scope_index]
        if row["rank"] != candidate["rank"] or row["candidate_key_sha256"] != candidate["candidate_key_sha256"]:
            raise ValueError("F2 dynamic evidence skipped or reordered a candidate")
        statuses = [row["gates"][gate_id]["status"] for gate_id in REQUIRED_GATE_IDS]
        if any(str(status).startswith("pending_") for status in statuses):
            return _decision({
                "status": "pending_earlier_dynamic_candidate",
                "pending_scope_index": scope_index,
                "selected_evaluated_row_sha256": None,
                "higher_level_redesign_required": False,
            })
        if row["selection_eligible"] is True:
            selected = row
            break
        if not any(status == "rejected" for status in statuses):
            raise ValueError("F2 terminal dynamic candidate lacks rejection evidence")
        terminal_rejected_count += 1
    if selected is not None:
        return _decision({
            "status": "first_all_gates_candidate_selected_binding_required",
            "selected_scope_index": terminal_rejected_count,
            "selected_rank": selected["rank"],
            "selected_evaluated_row_sha256": selected["evaluated_row_sha256"],
            "higher_level_redesign_required": False,
            "development_root_authorized": False,
        })
    exhausted = len(candidates) > 0 and len(evaluated_rows) == len(candidates)
    return _decision({
        "status": (
            "higher_level_redesign_required_dynamic_scope_exhausted"
            if exhausted
            else "pending_next_dynamic_candidate"
        ),
        "terminal_rejected_count": terminal_rejected_count,
        "selected_evaluated_row_sha256": None,
        "higher_level_redesign_required": exhausted or not candidates,
        "development_root_authorized": False,
    })


def _strict_cavity_from_inside_evidence(inside: Mapping[str, Any]) -> dict[str, Any]:
    raw_lower = [float(value) for value in inside["raw_cavity_proposal_lower_m"]]
    raw_upper = [float(value) for value in inside["raw_cavity_proposal_upper_m"]]
    margin = float(inside["minimum_signed_margin_m"])
    strict_lower = [value + margin for value in raw_lower]
    strict_upper = [value - margin for value in raw_upper]
    if any(lower >= upper for lower, upper in zip(strict_lower, strict_upper)):
        raise ValueError("F2 strict cavity collapsed after margin")
    return {
        "lower_m": strict_lower,
        "upper_m": strict_upper,
        "target_center_local_m": [
            (lower + upper) / 2.0 for lower, upper in zip(strict_lower, strict_upper)
        ],
        "safety_margin_per_side_m": margin,
        "full_envelope_evidence_sha256": inside["evidence_sha256"],
        "derivation": "full margin-inflated envelope vs every convex collision piece LP certificate",
    }


def build_provisional_dynamic_candidate_binding_v3(
    screening: Mapping[str, Any], *, scope_index: int
) -> dict[str, Any]:
    """Bind one <=12 candidate for passive/planner-only audit, never execution."""

    checked = validate_cpu_static_screening_v3(screening)
    candidates = checked["dynamic_scope"]["candidates"]
    if not isinstance(scope_index, int) or not 0 <= scope_index < len(candidates):
        raise ValueError("F2 provisional candidate scope index is invalid")
    candidate = candidates[scope_index]
    receipt = checked["terminal_cpu_candidate_receipts"][candidate["rank"]]
    if receipt["cpu_static_admissible"] is not True:
        raise ValueError("F2 provisional candidate did not pass CPU static screening")
    inside = receipt["inside_cpu_evidence"]
    layout_receipt = receipt["layout_cpu_receipt"]
    cavity = _strict_cavity_from_inside_evidence(inside)
    cavity["coordinate_frame"] = (
        f"062_plasticbox/base{candidate['candidate_key']['plastic_box_model_id']} actor-local xyz"
    )
    layout = layout_receipt["layout"]
    value = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "matrix_sha256": checked["matrix_sha256"],
        "cpu_screening_sha256": checked["screening_sha256"],
        "dynamic_scope_sha256": checked["dynamic_scope"]["scope_sha256"],
        "selected_evaluated_row_sha256": receipt["static_row_sha256"],
        "selected_candidate_key": candidate["candidate_key"],
        "asset_record_sha256s": receipt["asset_record_sha256s"],
        "selected_execution_arm": "left",
        "strict_cavity_contract": cavity,
        "inside_object_orientation_wxyz": inside["selected_orientation_wxyz"],
        "layout_version": layout["layout_version"],
        "layout_payload": layout,
        "layout_payload_sha256": layout_receipt["layout_payload_sha256"],
        "program_ids": list(PROGRAM_IDS),
        "same_main_object_for_all_programs": True,
        "same_execution_arm_for_all_programs": True,
        "branch_specific_asset_or_arm_selection_allowed": False,
        "provisional_dynamic_candidate": True,
        "selected": False,
        "development_execution_authorized": False,
        "dynamic_scope_index": scope_index,
        "cpu_static_candidate_receipt_sha256": receipt["receipt_sha256"],
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["binding_sha256"] = _hash_json(value)
    return validate_frozen_asset_layout_binding_v3(value)


def build_dynamic_selected_asset_layout_binding_v3(
    *,
    screening: Mapping[str, Any],
    evaluated_rows: Sequence[Mapping[str, Any]],
    selected_execution_arm: str,
    layout_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the selected <=12-scope candidate after first-all-Gates proof."""

    checked = validate_cpu_static_screening_v3(screening)
    decision = decide_bounded_dynamic_search_v3(checked, evaluated_rows)
    if decision["status"] != "first_all_gates_candidate_selected_binding_required":
        raise ValueError("F2 dynamic search has not selected a candidate")
    selected = validate_evaluated_candidate_row_v3(
        evaluated_rows[int(decision["selected_scope_index"])]
    )
    if selected["evaluated_row_sha256"] != decision["selected_evaluated_row_sha256"]:
        raise ValueError("F2 dynamic decision/selected row mismatch")
    planner = selected["gate_receipts"]["same_arm_three_branch_planner"]["evidence"]
    if planner.get("selected_execution_arm") != selected_execution_arm:
        raise ValueError("F2 selected binding arm differs from planner evidence")
    layout = selected["gate_receipts"]["asset_derived_scene_layout"]["evidence"]
    layout_sha = _hash_json(layout_payload)
    if layout.get("layout_payload_sha256") != layout_sha:
        raise ValueError("F2 selected binding layout differs from runtime evidence")
    inside = selected["gate_receipts"]["strict_full_object_inside_margin"]["evidence"]
    cavity = {
        **_strict_cavity_from_inside_evidence(inside),
        "coordinate_frame": (
            f"062_plasticbox/base{selected['candidate_key']['plastic_box_model_id']} actor-local xyz"
        ),
    }
    value = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "matrix_sha256": checked["matrix_sha256"],
        "cpu_screening_sha256": checked["screening_sha256"],
        "dynamic_scope_sha256": checked["dynamic_scope"]["scope_sha256"],
        "selection_decision_sha256": decision["decision_sha256"],
        "selected_evaluated_row_sha256": selected["evaluated_row_sha256"],
        "selected_candidate_key": selected["candidate_key"],
        "asset_record_sha256s": selected["asset_record_sha256s"],
        "selected_execution_arm": selected_execution_arm,
        "strict_cavity_contract": cavity,
        "inside_object_orientation_wxyz": inside["selected_orientation_wxyz"],
        "layout_version": layout_payload.get("layout_version"),
        "layout_payload": _copy(layout_payload),
        "layout_payload_sha256": layout_sha,
        "program_ids": list(PROGRAM_IDS),
        "same_main_object_for_all_programs": True,
        "same_execution_arm_for_all_programs": True,
        "branch_specific_asset_or_arm_selection_allowed": False,
        "provisional_dynamic_candidate": False,
        "selected": True,
        "development_execution_authorized": False,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
    }
    value["binding_sha256"] = _hash_json(value)
    return validate_frozen_asset_layout_binding_v3(value)


__all__ = [
    "MAX_DYNAMIC_CANDIDATES",
    "build_cpu_static_screening_v3",
    "build_dynamic_selected_asset_layout_binding_v3",
    "build_provisional_dynamic_candidate_binding_v3",
    "decide_bounded_dynamic_search_v3",
    "validate_cpu_static_screening_v3",
]
