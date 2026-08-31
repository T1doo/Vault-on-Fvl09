"""Post-Stage-0 F3 contact-preserving shared-prefix repair contract.

The sealed Stage 0 trace lost selected-gripper contact while the common close
continued toward normalized target 0.0.  This additive contract freezes one
program-independent partial-close hypothesis for one no-suffix diagnostic.
It does not alter the F3 candidates, V/H primitives, verifier thresholds, or
the sealed Stage 0 namespace.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .f3_grasp_robustness_v10 import build_f3_common_grasp_contract_v10


SCHEMA_VERSION = "cmf_f3_contact_preserving_shared_prefix_contract_v11"
REPAIR_ID = "f3_contact_preserving_partial_close_v11"
IMPLEMENTATION_VERSION = "controlled_multi_future_post_stage0_f3_v1"
CLOSE_NORMALIZED_TARGET = 0.35
EXPECTED_STATIC_DRIVE_TARGET_M = 0.01575
POST_CLOSE_SETTLE_FRAMES = 250
IMPACT_REVIEW_PAYLOAD_SHA256 = (
    "07882b05fe0cbc1932aab24a9b7a4b669f79e53c10504faacd20078947d93325"
)
PROGRAM_IDS = ("F3-VVHH", "F3-VHVH", "F3-VHHV")


def _sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def build_f3_contact_preserving_prefix_contract_v11() -> dict[str, Any]:
    base = build_f3_common_grasp_contract_v10()
    result = {
        "schema_version": SCHEMA_VERSION,
        "repair_id": REPAIR_ID,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "diagnostic_nonroot": True,
        "impact_review_payload_sha256": IMPACT_REVIEW_PAYLOAD_SHA256,
        "base_grasp_contract_sha256": base["contract_sha256"],
        "program_ids": list(PROGRAM_IDS),
        "close_normalized_target": CLOSE_NORMALIZED_TARGET,
        "expected_static_drive_target_m": EXPECTED_STATIC_DRIVE_TARGET_M,
        "post_close_settle_frames": POST_CLOSE_SETTLE_FRAMES,
        "trace_last_contact_drive_target_m": 0.012549903243780136,
        "trace_first_loss_drive_target_m": 0.012274903245270252,
        "trace_margin_above_last_contact_drive_target_m": (
            EXPECTED_STATIC_DRIVE_TARGET_M - 0.012549903243780136
        ),
        "invariants": {
            "same_repair_all_programs": True,
            "asset_arm_contact_pose_unchanged": True,
            "official_contact_point_id": 0,
            "rotation_candidate_index": 0,
            "vh_axes_amplitudes_programs_unchanged": True,
            "shared_first_v_unchanged": True,
            "release_return_unchanged": True,
            "physical_thresholds_unchanged": True,
            "program_specific_fallback_forbidden": True,
            "online_success_selection_forbidden": True,
            "automatic_retry": False,
            "recovery_attempts": 0,
        },
    }
    result["contract_sha256"] = _sha(result)
    return result


def validate_f3_contact_preserving_prefix_contract_v11(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )
    digest = normalized.pop("contract_sha256", None)
    if not isinstance(digest, str) or digest != _sha(normalized):
        raise ValueError("F3 contact-preserving prefix contract hash mismatch")
    expected = build_f3_contact_preserving_prefix_contract_v11()
    if value != expected:
        raise ValueError("F3 contact-preserving prefix contract differs from v11")
    return dict(expected)


__all__ = [
    "CLOSE_NORMALIZED_TARGET",
    "IMPLEMENTATION_VERSION",
    "PROGRAM_IDS",
    "REPAIR_ID",
    "build_f3_contact_preserving_prefix_contract_v11",
    "validate_f3_contact_preserving_prefix_contract_v11",
]
