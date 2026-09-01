"""Hierarchical F2 template search that solves INSIDE before ON/BESIDE.

The former 1,650-row matrix repeats each can/box pair across scale/stand
choices.  Stage A deliberately collapses those irrelevant repetitions and
freezes at most twelve distinct ``(can, box, arm)`` candidates.  Scale and
stand are not permitted to influence Stage-A rank.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_f2_hierarchical_template_search_v1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f2_hierarchical_template_search_v1"
SCOPE = "F2_HIERARCHICAL_TEMPLATE_SEARCH_V1"
SCREENING_PATH = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/F2_CPU_STATIC_SCREENING_V3.json"
)
CAN_ASSET_ROOT = Path(
    "/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets/objects/071_can"
)
MAXIMUM_INSIDE_CANDIDATES = 12
MAXIMUM_REAL_INSIDE_EXECUTIONS = 3
MAXIMUM_STAGE_B_LAYOUT_CANDIDATES = 8
ARMS = ("left", "right")
PROGRAM_IDS = ("F2-inside", "F2-on", "F2-beside")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _can_contact_counts(asset_root: Path = CAN_ASSET_ROOT) -> dict[int, int]:
    values = {}
    for path in Path(asset_root).glob("model_data*.json"):
        model_id = int(path.stem.removeprefix("model_data"))
        data = _load_json(path)
        values[model_id] = len(data.get("contact_points_pose") or [])
    return values


def _workspace_margin_m(xyz: Sequence[float]) -> float:
    lower = (-0.45, -0.35, 0.78)
    upper = (0.45, 0.20, 1.02)
    point = (float(xyz[0]), float(xyz[1]), float(xyz[2]))
    return min(
        *[point[index] - lower[index] for index in range(3)],
        *[upper[index] - point[index] for index in range(3)],
    )


def collapse_inside_pairs_v1(
    screening: Mapping[str, Any], *, can_asset_root: Path = CAN_ASSET_ROOT
) -> list[dict[str, Any]]:
    receipts = canonical_jsonable(screening).get("terminal_cpu_candidate_receipts")
    if not isinstance(receipts, list) or len(receipts) != 1650:
        raise ValueError("F2 V1 requires the complete 1,650-row CPU screening")
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for receipt in receipts:
        key = receipt.get("candidate_key", {})
        pair = (
            int(key.get("main_object_model_id", -1)),
            int(key.get("plastic_box_model_id", -1)),
        )
        groups.setdefault(pair, []).append(receipt)
    if len(groups) != 66:
        raise ValueError("F2 V1 expected 66 distinct can/box pairs")
    contact_counts = _can_contact_counts(can_asset_root)
    collapsed = []
    for (can_id, box_id), rows in sorted(groups.items()):
        passing = [row for row in rows if row.get("cpu_static_admissible") is True]
        if not passing:
            continue
        representative = sorted(
            passing,
            key=lambda row: (
                -float(row["inside_cpu_evidence"]["minimum_signed_margin_m"]),
                int(row["rank"]),
            ),
        )[0]
        evidence = representative["inside_cpu_evidence"]
        layout = representative["layout_cpu_receipt"]["layout"]
        source_xyz = layout["main_object_pose_xyz"]
        inside_xyz = [
            *layout["inside_region_center_xy_m"],
            0.90,
        ]
        record = {
            "main_object_model_id": can_id,
            "plastic_box_model_id": box_id,
            "strict_inside_margin_m": float(evidence["minimum_signed_margin_m"]),
            "official_can_contact_point_count": int(contact_counts.get(can_id, 0)),
            "workspace_margin_m": min(
                _workspace_margin_m([source_xyz[0], source_xyz[1], 0.90]),
                _workspace_margin_m(inside_xyz),
            ),
            "selected_inside_orientation_wxyz": deepcopy(
                evidence["selected_orientation_wxyz"]
            ),
            "representative_static_rank": int(representative["rank"]),
            "representative_static_row_sha256": representative["static_row_sha256"],
            "inside_cpu_evidence_sha256": representative[
                "inside_cpu_evidence_sha256"
            ],
            "repeated_scale_stand_row_count": len(rows),
            "admissible_repeated_scale_stand_row_count": len(passing),
            "scale_or_stand_used_for_stage_a_rank": False,
        }
        record["pair_sha256"] = canonical_hash_json(record)
        collapsed.append(record)
    return sorted(
        collapsed,
        key=lambda item: (
            -item["strict_inside_margin_m"],
            -item["official_can_contact_point_count"],
            -item["workspace_margin_m"],
            item["main_object_model_id"],
            item["plastic_box_model_id"],
        ),
    )


def _diverse_pair_subset(collapsed: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    # Six pairs become twelve arm-specific candidates.  The first pass covers
    # each feasible can ID once and prefers a previously unseen box ID when
    # rank-compatible; the second pass fills any remainder in global rank.
    selected: list[dict[str, Any]] = []
    used_pairs: set[tuple[int, int]] = set()
    used_boxes: set[int] = set()
    can_ids = sorted({int(item["main_object_model_id"]) for item in collapsed})
    for can_id in can_ids:
        candidates = [item for item in collapsed if item["main_object_model_id"] == can_id]
        unseen = [item for item in candidates if item["plastic_box_model_id"] not in used_boxes]
        chosen = (unseen or candidates)[0]
        pair = (chosen["main_object_model_id"], chosen["plastic_box_model_id"])
        if pair not in used_pairs:
            selected.append(deepcopy(chosen))
            used_pairs.add(pair)
            used_boxes.add(int(chosen["plastic_box_model_id"]))
        if len(selected) == MAXIMUM_INSIDE_CANDIDATES // 2:
            return selected
    for item in collapsed:
        pair = (item["main_object_model_id"], item["plastic_box_model_id"])
        if pair not in used_pairs:
            selected.append(deepcopy(item))
            used_pairs.add(pair)
        if len(selected) == MAXIMUM_INSIDE_CANDIDATES // 2:
            break
    if len(selected) != MAXIMUM_INSIDE_CANDIDATES // 2:
        raise ValueError("F2 V1 could not freeze six diverse inside pairs")
    return selected


def build_f2_hierarchical_template_search_v1(
    screening: Mapping[str, Any] | None = None,
    *,
    screening_path: Path = SCREENING_PATH,
    can_asset_root: Path = CAN_ASSET_ROOT,
) -> dict[str, Any]:
    source = _load_json(screening_path) if screening is None else canonical_jsonable(screening)
    collapsed = collapse_inside_pairs_v1(source, can_asset_root=can_asset_root)
    pairs = _diverse_pair_subset(collapsed)
    candidates = []
    for pair in pairs:
        for arm in ARMS:
            candidate = {
                "rank": len(candidates) + 1,
                "candidate_id": f"f2-inside-hv1-r{len(candidates) + 1:02d}",
                "main_object_model_id": pair["main_object_model_id"],
                "plastic_box_model_id": pair["plastic_box_model_id"],
                "arm": arm,
                "inside_pair_sha256": pair["pair_sha256"],
                "strict_inside_margin_m": pair["strict_inside_margin_m"],
                "official_can_contact_point_count": pair[
                    "official_can_contact_point_count"
                ],
                "workspace_margin_m": pair["workspace_margin_m"],
                "inside_actor_orientation_wxyz": deepcopy(
                    pair["selected_inside_orientation_wxyz"]
                ),
                "official_grasp_contact_point_id": 0,
                "official_grasp_rotation_selection_rule": (
                    "first_planner_success_in_official_ROTATE_NUM_order"
                ),
                "grasp_pre_distance_m": 0.09,
                "grasp_target_distance_m": 0.0,
                "asset_derived_layout_transform": (
                    "identity" if arm == "left" else "bilateral_x_mirror"
                ),
                "electronic_scale_model_id": None,
                "beside_reference_model_id": None,
                "scale_or_stand_used_for_stage_a_rank": False,
                "stage_a_sequence": [
                    "fresh_scene",
                    "grasp_lift_planner",
                    "inside_preplace_release_planner",
                ],
                "automatic_retry": False,
                "online_fallback": False,
            }
            candidate["candidate_sha256"] = canonical_hash_json(candidate)
            candidates.append(candidate)
    if len(candidates) != MAXIMUM_INSIDE_CANDIDATES:
        raise AssertionError("F2 V1 inside candidate bound changed")
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scope": SCOPE,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "family": "F2",
        "program_ids": list(PROGRAM_IDS),
        "source_screening_sha256": source.get("screening_sha256"),
        "source_row_count": len(source["terminal_cpu_candidate_receipts"]),
        "distinct_can_box_pair_count": 66,
        "cpu_admissible_distinct_pair_count": len(collapsed),
        "collapsed_pairs": collapsed,
        "collapsed_pairs_sha256": canonical_hash_json(collapsed),
        "inside_candidates": candidates,
        "fixed_inside_candidate_order": [item["candidate_id"] for item in candidates],
        "maximum_inside_candidates": MAXIMUM_INSIDE_CANDIDATES,
        "maximum_real_inside_executions": MAXIMUM_REAL_INSIDE_EXECUTIONS,
        "inside_planner_rule": "all 12 tuples receive fresh-scene grasp/lift and inside preplace/release planner checks",
        "inside_physical_rule": "only the first three lowest-rank planner-passing tuples receive one real inside execution",
        "inside_freeze_rule": "freeze the first real inside success and never revisit another inside tuple in this work package",
        "stage_a_exhaustion_status": (
            "DIVERSE_INSIDE_SEARCH_EXHAUSTED_REQUIRES_BROADER_ASSET_FAMILY"
        ),
        "stage_b_allowed_only_after_inside_success": True,
        "maximum_stage_b_layout_candidates": MAXIMUM_STAGE_B_LAYOUT_CANDIDATES,
        "stage_b_dimensions": [
            "electronic_scale_model_id",
            "beside_reference_model_id",
            "asset_derived_layout",
        ],
        "stage_b_required_gates": [
            "on_passive_stability",
            "beside_runtime_stability",
            "mutual_exclusion",
            "rendered_visibility",
            "same_arm_three_branch_reachability",
        ],
        "root_rule": "one inside/on/beside root only after Stage A and Stage B both freeze",
        "success_status": "PASS_F2_TEMPLATE",
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "training_authorized": False,
    }
    value["search_contract_sha256"] = canonical_hash_json(value)
    return value


def validate_f2_hierarchical_template_search_v1(
    value: Mapping[str, Any],
    screening: Mapping[str, Any] | None = None,
    *,
    screening_path: Path = SCREENING_PATH,
    can_asset_root: Path = CAN_ASSET_ROOT,
) -> dict[str, Any]:
    expected = build_f2_hierarchical_template_search_v1(
        screening, screening_path=screening_path, can_asset_root=can_asset_root
    )
    if canonical_jsonable(value) != expected:
        raise ValueError("F2 hierarchical template search V1 contract changed")
    return expected


def select_inside_physical_candidates_v1(
    contract: Mapping[str, Any], planner_receipts: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    checked = validate_f2_hierarchical_template_search_v1(contract)
    by_id = {str(item.get("candidate_id")): canonical_jsonable(item) for item in planner_receipts}
    order = checked["fixed_inside_candidate_order"]
    if set(by_id) != set(order):
        raise ValueError("F2 Stage-A planner receipts must cover all twelve candidates")
    candidates = {item["candidate_id"]: item for item in checked["inside_candidates"]}
    ordered = [by_id[candidate_id] for candidate_id in order]
    for receipt in ordered:
        candidate = candidates[receipt["candidate_id"]]
        if (
            receipt.get("candidate_sha256") != candidate["candidate_sha256"]
            or not isinstance(receipt.get("planner_success"), bool)
        ):
            raise ValueError("F2 Stage-A planner receipt is not candidate-bound")
    selected = [item["candidate_id"] for item in ordered if item["planner_success"]][
        :MAXIMUM_REAL_INSIDE_EXECUTIONS
    ]
    value = {
        "schema_version": "cmf_f2_hierarchical_inside_planner_terminal_v1",
        "search_contract_sha256": checked["search_contract_sha256"],
        "planner_receipts": ordered,
        "physical_candidate_ids": selected,
        "maximum_real_inside_executions": MAXIMUM_REAL_INSIDE_EXECUTIONS,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def select_first_inside_success_v1(
    contract: Mapping[str, Any],
    planner_terminal: Mapping[str, Any],
    physical_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checked = validate_f2_hierarchical_template_search_v1(contract)
    selected_ids = list(planner_terminal.get("physical_candidate_ids", []))
    by_id = {str(item.get("candidate_id")): canonical_jsonable(item) for item in physical_receipts}
    if set(by_id) != set(selected_ids):
        raise ValueError("F2 physical inside receipts must cover selected tuples")
    candidates = {item["candidate_id"]: item for item in checked["inside_candidates"]}
    ordered = [by_id[candidate_id] for candidate_id in selected_ids]
    passing = []
    for receipt in ordered:
        candidate = candidates[receipt["candidate_id"]]
        if receipt.get("candidate_sha256") != candidate["candidate_sha256"]:
            raise ValueError("F2 physical inside receipt hash mismatch")
        if (
            receipt.get("strict_inside_verifier_pass") is True
            and receipt.get("cleanup_safety_pass") is True
            and receipt.get("orphan_process_count") == 0
        ):
            passing.append(candidate)
    selected = passing[0] if passing else None
    value = {
        "schema_version": "cmf_f2_hierarchical_inside_physical_terminal_v1",
        "search_contract_sha256": checked["search_contract_sha256"],
        "physical_receipts": ordered,
        "frozen_inside_candidate": selected,
        "stage_b_authorized_by_result": selected is not None,
        "status": (
            "INSIDE_PASS_REQUIRES_STAGE_B_LAYOUT_SEARCH"
            if selected is not None
            else checked["stage_a_exhaustion_status"]
        ),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = [
    "MAXIMUM_INSIDE_CANDIDATES",
    "MAXIMUM_REAL_INSIDE_EXECUTIONS",
    "MAXIMUM_STAGE_B_LAYOUT_CANDIDATES",
    "build_f2_hierarchical_template_search_v1",
    "collapse_inside_pairs_v1",
    "select_first_inside_success_v1",
    "select_inside_physical_candidates_v1",
    "validate_f2_hierarchical_template_search_v1",
]
