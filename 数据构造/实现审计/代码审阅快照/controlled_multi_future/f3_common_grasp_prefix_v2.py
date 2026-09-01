"""Closure-V1 F3 common grasp prefix V2.

Exactly one program-independent change is frozen: normalized close target 0.50.
All grasp geometry, lift/carry, settling, shared V, programs and physical Gate
thresholds remain unchanged.
"""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_grasp_robustness_v10 import build_f3_common_grasp_contract_v10


SCHEMA_VERSION = "cmf_f3_common_grasp_prefix_v2"
CONTRACT_VERSION = "F3CommonGraspPrefixV2"
IMPLEMENTATION_VERSION = "controlled_multi_future_post_stage0_closure_f3_v2"
PROGRAM_IDS = ("F3-VVHH", "F3-VHVH", "F3-VHHV")
CLOSE_NORMALIZED_TARGET = 0.50
POST_CLOSE_SETTLE_FRAMES = 250


def _sha(value: Mapping[str, Any]) -> str:
    return canonical_hash_json(value)


def build_f3_common_grasp_prefix_v2() -> dict[str, Any]:
    base = build_f3_common_grasp_contract_v10()
    value = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "stage1_authorized": False,
        "diagnostic_nonroot": True,
        "base_grasp_contract_sha256": base["contract_sha256"],
        "program_ids": list(PROGRAM_IDS),
        "close_normalized_target": CLOSE_NORMALIZED_TARGET,
        "post_close_settle_frames": POST_CLOSE_SETTLE_FRAMES,
        "trace_evidence": {
            "source_partial_trace_sha256": "9f5ebdedb1c92c80726cf2962701ee2f916f9e13865ca93329f1ebf56bd4801b",
            "contact_window_normalized_command": [0.50, 0.55],
            "contact_window_frame_count": 16,
            "contact_window_contact_fraction": 1.0,
            "contact_window_max_translation_drift_m": 0.00029656233183558294,
            "contact_window_max_orientation_drift_rad": 0.006627327065100992,
            "first_loss_normalized_command": 0.39899497487437185,
            "last_true_normalized_command": 0.40226130653266334,
            "predicted_drive_target_at_0_50_m": 0.01761985455502952,
            "first_loss_drive_target_m": 0.0121099092066288,
            "normalized_margin_above_loss": 0.09773869346733666,
        },
        "invariants": {
            "one_contract_all_programs": True,
            "grasp_local_pose_orientation_unchanged": True,
            "official_contact_point_id": 0,
            "rotation_candidate_index": 0,
            "lift_clearance_unchanged": True,
            "post_close_settle_unchanged": True,
            "prefix_end_boundary_unchanged": True,
            "shared_first_v_unchanged": True,
            "vh_programs_unchanged": True,
            "release_return_unchanged": True,
            "verifier_thresholds_unchanged": True,
            "program_specific_fallback_forbidden": True,
            "online_success_selection_forbidden": True,
            "automatic_retry": False,
            "recovery_attempts": 0,
        },
    }
    value["contract_sha256"] = _sha(value)
    return value


def validate_f3_common_grasp_prefix_v2(value: Mapping[str, Any]) -> dict[str, Any]:
    normalized = canonical_jsonable(value)
    digest = normalized.pop("contract_sha256", None)
    if not isinstance(digest, str) or digest != _sha(normalized):
        raise ValueError("F3CommonGraspPrefixV2 hash mismatch")
    expected = build_f3_common_grasp_prefix_v2()
    if value != expected:
        raise ValueError("F3CommonGraspPrefixV2 differs from frozen contract")
    return dict(expected)


__all__ = ["CLOSE_NORMALIZED_TARGET", "CONTRACT_VERSION", "IMPLEMENTATION_VERSION", "PROGRAM_IDS", "build_f3_common_grasp_prefix_v2", "validate_f3_common_grasp_prefix_v2"]
