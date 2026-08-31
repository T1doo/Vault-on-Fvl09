"""Immutable F4 canonical-neutral binding for Stage-0 smoke v1.1.

The terminal neutral *target specification* is frozen from the canonical
prefix artifact.  It is intentionally distinct from the realized prefix-end
state: the former is exact and hash-addressed, while the latter is compared by
the existing physical-prefix tolerances.

This module never derives a neutral from a post-prefix object pose and never
falls back to the scene-layout ``branch_neutral_pose``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from .current_hasher import hash_json
from .f4_candidate_equivalence_v12 import audit_f4_candidate_equivalence_v12


SCHEMA_VERSION = "cmf_f4_frozen_canonical_neutral_binding_v13"
BINDING_VERSION = "f4_frozen_canonical_neutral_binding_v13"
IMPLEMENTATION_VERSION = "controlled_multi_future_stage0_smoke_v1_1"
CANONICAL_SOURCE = "canonical_prefix_target_neutral_pose"
FORBIDDEN_NEUTRAL_SOURCES = (
    "post_prefix_common_x_pose",
    "recomputed_common_center_high",
    "layout_branch_neutral_pose",
)


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    )


def _pose_exact(value: Sequence[float], label: str) -> list[float]:
    pose = np.asarray(value, dtype=np.float64).reshape(-1)
    if pose.shape != (7,) or not np.all(np.isfinite(pose)):
        raise ValueError(f"{label} must be one finite pose7")
    quaternion_norm = float(np.linalg.norm(pose[3:]))
    if not np.isclose(quaternion_norm, 1.0, rtol=0.0, atol=1.0e-8):
        raise ValueError(f"{label} quaternion must already be normalized")
    # Do not normalize here.  Normalization would silently change the frozen
    # target specification that this binding is meant to preserve exactly.
    return [float(item) for item in pose]


def canonical_neutral_pose_sha256_v13(value: Sequence[float]) -> str:
    return _sha(_pose_exact(value, "canonical terminal neutral pose"))


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def build_f4_frozen_canonical_neutral_binding_v13(
    *,
    canonical_terminal_neutral_pose: Sequence[float],
    canonical_prefix_id: str,
    canonical_prefix_contract_sha256: str,
    canonical_prefix_action_sha256: str,
    semantic_prefix_end_anchor_sha256: str,
    acceptance_prefix_end_anchor_sha256: str,
    prefix_end_tolerance_version: str,
    canonical_terminal_neutral_source: str = CANONICAL_SOURCE,
) -> dict[str, Any]:
    """Build the immutable target-spec binding.

    The only accepted source is the canonical-prefix target.  Callers cannot
    label a layout or post-prefix-derived pose as canonical.
    """

    pose = _pose_exact(
        canonical_terminal_neutral_pose, "canonical terminal neutral pose"
    )
    if canonical_terminal_neutral_source != CANONICAL_SOURCE:
        raise ValueError(
            "F4 v13 neutral must come from the canonical-prefix target; "
            "layout/post-prefix fallback is forbidden"
        )
    if not isinstance(canonical_prefix_id, str) or not canonical_prefix_id:
        raise ValueError("F4 v13 canonical prefix ID must be nonempty")
    if (
        not isinstance(prefix_end_tolerance_version, str)
        or not prefix_end_tolerance_version
    ):
        raise ValueError("F4 v13 prefix-end tolerance version must be nonempty")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "binding_version": BINDING_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "canonical_terminal_neutral_pose": pose,
        "canonical_terminal_neutral_pose_sha256": _sha(pose),
        "canonical_terminal_neutral_source": CANONICAL_SOURCE,
        "canonical_prefix_id": canonical_prefix_id,
        "canonical_prefix_contract_sha256": _require_sha256(
            canonical_prefix_contract_sha256,
            "canonical prefix contract SHA-256",
        ),
        "canonical_prefix_action_sha256": _require_sha256(
            canonical_prefix_action_sha256,
            "canonical prefix action SHA-256",
        ),
        "semantic_prefix_end_anchor_sha256": _require_sha256(
            semantic_prefix_end_anchor_sha256,
            "semantic prefix-end anchor SHA-256",
        ),
        "acceptance_prefix_end_anchor_sha256": _require_sha256(
            acceptance_prefix_end_anchor_sha256,
            "acceptance prefix-end anchor SHA-256",
        ),
        "prefix_end_tolerance_version": prefix_end_tolerance_version,
        "specification_identity_policy": "exact_immutable_target_pose",
        "realized_replay_equivalence_policy": (
            "separate_existing_prefix_end_physical_tolerance"
        ),
        "forbidden_neutral_sources": list(FORBIDDEN_NEUTRAL_SOURCES),
    }
    payload["binding_sha256"] = _sha(payload)
    validate_f4_frozen_canonical_neutral_binding_v13(payload)
    return payload


def validate_f4_frozen_canonical_neutral_binding_v13(
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        raise ValueError("F4 v13 frozen canonical-neutral binding is missing")
    required = {
        "schema_version",
        "binding_version",
        "design_version",
        "implementation_version",
        "formal_data",
        "stage0_data",
        "stage0_authorized",
        "canonical_terminal_neutral_pose",
        "canonical_terminal_neutral_pose_sha256",
        "canonical_terminal_neutral_source",
        "canonical_prefix_id",
        "canonical_prefix_contract_sha256",
        "canonical_prefix_action_sha256",
        "semantic_prefix_end_anchor_sha256",
        "acceptance_prefix_end_anchor_sha256",
        "prefix_end_tolerance_version",
        "specification_identity_policy",
        "realized_replay_equivalence_policy",
        "forbidden_neutral_sources",
        "binding_sha256",
    }
    if set(binding) != required:
        raise ValueError("F4 v13 canonical-neutral binding fields changed")
    if (
        binding.get("schema_version") != SCHEMA_VERSION
        or binding.get("binding_version") != BINDING_VERSION
        or binding.get("design_version")
        != "controlled_multi_future_f1_f4_v1_2"
        or binding.get("implementation_version") != IMPLEMENTATION_VERSION
    ):
        raise ValueError("F4 v13 canonical-neutral binding version mismatch")
    if (
        binding.get("formal_data") is not False
        or binding.get("stage0_data") is not False
        or binding.get("stage0_authorized") is not False
    ):
        raise ValueError("F4 v13 canonical-neutral binding changed data scope")
    if binding.get("canonical_terminal_neutral_source") != CANONICAL_SOURCE:
        raise ValueError("F4 v13 canonical-neutral source is not the prefix target")
    if binding.get("forbidden_neutral_sources") != list(
        FORBIDDEN_NEUTRAL_SOURCES
    ):
        raise ValueError("F4 v13 forbidden neutral-source list changed")
    if (
        binding.get("specification_identity_policy")
        != "exact_immutable_target_pose"
        or binding.get("realized_replay_equivalence_policy")
        != "separate_existing_prefix_end_physical_tolerance"
    ):
        raise ValueError("F4 v13 target/physical equivalence policies changed")
    pose = _pose_exact(
        binding.get("canonical_terminal_neutral_pose"),
        "F4 v13 canonical terminal neutral pose",
    )
    if _sha(pose) != binding.get("canonical_terminal_neutral_pose_sha256"):
        raise ValueError("F4 v13 canonical terminal neutral pose hash mismatch")
    for key in (
        "canonical_prefix_contract_sha256",
        "canonical_prefix_action_sha256",
        "semantic_prefix_end_anchor_sha256",
        "acceptance_prefix_end_anchor_sha256",
    ):
        _require_sha256(binding.get(key), key)
    if not isinstance(binding.get("canonical_prefix_id"), str) or not binding[
        "canonical_prefix_id"
    ]:
        raise ValueError("F4 v13 canonical prefix ID is invalid")
    if not isinstance(
        binding.get("prefix_end_tolerance_version"), str
    ) or not binding["prefix_end_tolerance_version"]:
        raise ValueError("F4 v13 prefix tolerance version is invalid")
    payload = dict(binding)
    digest = payload.pop("binding_sha256", None)
    if not isinstance(digest, str) or _sha(payload) != digest:
        raise ValueError("F4 v13 canonical-neutral binding self-hash mismatch")
    return _copy(binding)


def _candidate_terminal_neutral_pose(
    candidate: Mapping[str, Any], label: str
) -> list[float]:
    if not isinstance(candidate, Mapping):
        raise ValueError(f"{label} candidate is missing")
    contract = candidate.get("candidate_contract_segments")
    applied = candidate.get("applied_planner_targets")
    if not isinstance(contract, list) or not isinstance(applied, list):
        raise ValueError(f"{label} candidate target lists are missing")
    if (
        not contract
        or contract[-1].get("segment_id") != "A_neutral"
        or not applied
        or applied[-1].get("segment_id") != "A_neutral"
    ):
        raise ValueError(f"{label} candidate terminal neutral structure changed")
    contract_pose = _pose_exact(
        contract[-1].get("pose"), f"{label} contract A_neutral"
    )
    applied_pose = _pose_exact(
        applied[-1].get("pose"), f"{label} applied A_neutral"
    )
    if contract_pose != applied_pose:
        raise ValueError(f"{label} candidate has two different A_neutral targets")
    return contract_pose


def build_f4_frozen_canonical_neutral_binding_from_artifacts_v13(
    *,
    canonical_prefix_artifact: Mapping[str, Any],
    corridor_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the pristine A-neutral against the prefix target evidence."""

    if not isinstance(canonical_prefix_artifact, Mapping):
        raise ValueError("F4 v13 canonical prefix artifact is missing")
    if canonical_prefix_artifact.get("family") != "F4":
        raise ValueError("F4 v13 received a non-F4 prefix artifact")
    artifact_payload = dict(canonical_prefix_artifact)
    artifact_digest = artifact_payload.pop("artifact_sha256", None)
    artifact_payload.pop("prefix_arrays_npz_sha256", None)
    if not isinstance(artifact_digest, str) or _sha(
        artifact_payload
    ) != artifact_digest:
        raise ValueError("F4 v13 canonical prefix artifact self-hash failed")
    if not isinstance(corridor_contract, Mapping):
        raise ValueError("F4 v13 pristine corridor contract is missing")
    contract_payload = dict(corridor_contract)
    contract_digest = contract_payload.pop("receipt_sha256", None)
    if (
        corridor_contract.get("pass") is not True
        or not isinstance(contract_digest, str)
        or hash_json(contract_payload) != contract_digest
    ):
        raise ValueError("F4 v13 pristine corridor contract self-hash failed")
    candidates = corridor_contract.get("candidates") if isinstance(
        corridor_contract, Mapping
    ) else None
    if not isinstance(candidates, list) or len(candidates) != 4:
        raise ValueError("F4 v13 pristine corridor contract lacks four candidates")
    candidate_neutrals = [
        _candidate_terminal_neutral_pose(candidate, "pristine")
        for candidate in candidates
    ]
    if any(pose != candidate_neutrals[0] for pose in candidate_neutrals[1:]):
        raise ValueError("F4 v13 pristine candidates do not share one neutral")
    physical = canonical_prefix_artifact.get("prefix_physical_acceptance")
    boundary = physical.get("actual_open_contact_boundary_v5") if isinstance(
        physical, Mapping
    ) else None
    target = (
        boundary.get("target_neutral_pose")
        if isinstance(boundary, Mapping)
        and boundary.get("pass") is True
        and physical.get("pass") is True
        else None
    )
    canonical_target = _pose_exact(
        target, "canonical-prefix physical target neutral pose"
    )
    if canonical_target != candidate_neutrals[0]:
        raise ValueError(
            "F4 pristine candidate neutral differs from canonical-prefix target"
        )
    prefix_contract = canonical_prefix_artifact.get("prefix_contract")
    if not isinstance(prefix_contract, Mapping):
        raise ValueError("F4 v13 prefix contract is missing")
    return build_f4_frozen_canonical_neutral_binding_v13(
        canonical_terminal_neutral_pose=canonical_target,
        canonical_prefix_id=str(prefix_contract.get("prefix_id", "")),
        canonical_prefix_contract_sha256=str(
            canonical_prefix_artifact.get("prefix_contract_sha256", "")
        ),
        canonical_prefix_action_sha256=str(
            canonical_prefix_artifact.get("prefix_action_sha256", "")
        ),
        semantic_prefix_end_anchor_sha256=str(
            canonical_prefix_artifact.get(
                "semantic_prefix_end_anchor_sha256", ""
            )
        ),
        acceptance_prefix_end_anchor_sha256=str(
            canonical_prefix_artifact.get(
                "acceptance_prefix_end_anchor_sha256", ""
            )
        ),
        prefix_end_tolerance_version=str(
            canonical_prefix_artifact.get("prefix_end_tolerance_version", "")
        ),
    )


def bind_f4_candidate_to_canonical_neutral_v13(
    candidate: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate an already-canonical candidate without changing its payload.

    Controller v13 should override the base A-neutral *before* building the
    v11 corridor.  The v11/v12 hashes therefore already cover the frozen pose.
    Adding binding metadata inside the candidate would falsely change the
    meaning of ``base_v11_candidate_application_sha256``; provenance belongs
    in the enclosing contract and candidate receipt instead.  This helper
    refuses to repair a drifting target at the planner boundary.
    """

    validated = validate_f4_frozen_canonical_neutral_binding_v13(binding)
    output = _copy(candidate)
    neutral = _candidate_terminal_neutral_pose(output, "v13")
    if neutral != validated["canonical_terminal_neutral_pose"]:
        raise ValueError(
            "F4 v13 candidate neutral is not the frozen canonical neutral; "
            "late planner-boundary replacement is forbidden"
        )
    return output


def bind_f4_corridor_contract_to_canonical_neutral_v13(
    contract: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    validated = validate_f4_frozen_canonical_neutral_binding_v13(binding)
    if not isinstance(contract, Mapping):
        raise ValueError("F4 v13 corridor contract is missing")
    candidates = contract.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 4:
        raise ValueError("F4 v13 corridor contract must contain four candidates")
    output = _copy(contract)
    old_receipt = output.pop("receipt_sha256", None)
    if not isinstance(old_receipt, str):
        raise ValueError("F4 v13 base corridor receipt hash is missing")
    output["base_v12_receipt_sha256"] = old_receipt
    output["schema_version"] = "cmf_f4_exact_corridor_contract_v13"
    output["implementation_version"] = IMPLEMENTATION_VERSION
    output["frozen_canonical_neutral_binding_v13"] = validated
    output["frozen_canonical_neutral_binding_sha256_v13"] = validated[
        "binding_sha256"
    ]
    output["canonical_terminal_neutral_pose"] = list(
        validated["canonical_terminal_neutral_pose"]
    )
    output["canonical_terminal_neutral_pose_sha256_v13"] = validated[
        "canonical_terminal_neutral_pose_sha256"
    ]
    output["canonical_terminal_neutral_source"] = CANONICAL_SOURCE
    output["candidates"] = [
        bind_f4_candidate_to_canonical_neutral_v13(candidate, validated)
        for candidate in candidates
    ]
    output["receipt_sha256"] = hash_json(output)
    return output


def bind_f4_canonical_prefix_artifact_v13(
    artifact: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    """Attach the binding to an in-memory artifact and renew its hash."""

    validated = validate_f4_frozen_canonical_neutral_binding_v13(binding)
    if not isinstance(artifact, Mapping) or artifact.get("family") != "F4":
        raise ValueError("F4 v13 canonical prefix artifact is missing")
    checks = {
        "prefix_contract_sha256_exact": artifact.get("prefix_contract_sha256")
        == validated["canonical_prefix_contract_sha256"],
        "prefix_action_sha256_exact": artifact.get("prefix_action_sha256")
        == validated["canonical_prefix_action_sha256"],
        "semantic_prefix_end_anchor_sha256_exact": artifact.get(
            "semantic_prefix_end_anchor_sha256"
        )
        == validated["semantic_prefix_end_anchor_sha256"],
        "acceptance_prefix_end_anchor_sha256_exact": artifact.get(
            "acceptance_prefix_end_anchor_sha256"
        )
        == validated["acceptance_prefix_end_anchor_sha256"],
        "prefix_end_tolerance_version_exact": artifact.get(
            "prefix_end_tolerance_version"
        )
        == validated["prefix_end_tolerance_version"],
    }
    if not all(checks.values()):
        raise ValueError("F4 v13 binding does not match canonical prefix artifact")
    output = _copy(artifact)
    arrays_file_hash = output.pop("prefix_arrays_npz_sha256", None)
    old_artifact_hash = output.pop("artifact_sha256", None)
    if not isinstance(old_artifact_hash, str):
        raise ValueError("F4 v13 base canonical prefix artifact hash is missing")
    output["base_canonical_prefix_artifact_sha256_v1"] = old_artifact_hash
    output["implementation_version"] = IMPLEMENTATION_VERSION
    output["f4_frozen_canonical_neutral_binding_v13"] = validated
    output["f4_frozen_canonical_neutral_binding_sha256_v13"] = validated[
        "binding_sha256"
    ]
    output["canonical_terminal_neutral_pose"] = list(
        validated["canonical_terminal_neutral_pose"]
    )
    output["canonical_terminal_neutral_pose_sha256"] = validated[
        "canonical_terminal_neutral_pose_sha256"
    ]
    output["canonical_terminal_neutral_source"] = CANONICAL_SOURCE
    output["artifact_sha256"] = _sha(output)
    if arrays_file_hash is not None:
        output["prefix_arrays_npz_sha256"] = arrays_file_hash
    return output


def build_f4_realized_prefix_end_physical_equivalence_v13(
    *,
    replay: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit realized replay using anchor equivalence, never spec tolerance."""

    validated = validate_f4_frozen_canonical_neutral_binding_v13(binding)
    semantic = replay.get("semantic_prefix_end_equivalence") if isinstance(
        replay, Mapping
    ) else None
    acceptance = replay.get("acceptance_prefix_end_equivalence") if isinstance(
        replay, Mapping
    ) else None
    checks = {
        "semantic_prefix_end_within_physical_tolerance": isinstance(
            semantic, Mapping
        )
        and semantic.get("equivalent") is True,
        "acceptance_prefix_end_within_physical_tolerance": isinstance(
            acceptance, Mapping
        )
        and acceptance.get("equivalent") is True,
        "combined_prefix_end_equivalent": replay.get("prefix_end_equivalent")
        is True,
        "semantic_reference_anchor_exact": isinstance(semantic, Mapping)
        and semantic.get("reference_sha256")
        == validated["semantic_prefix_end_anchor_sha256"],
        "acceptance_reference_anchor_exact": isinstance(acceptance, Mapping)
        and acceptance.get("reference_sha256")
        == validated["acceptance_prefix_end_anchor_sha256"],
        "candidate_spec_tolerance_not_used_for_realized_state": True,
    }
    receipt = {
        "schema_version": "cmf_f4_realized_prefix_end_physical_equivalence_v13",
        "prefix_end_tolerance_version": validated[
            "prefix_end_tolerance_version"
        ],
        "candidate_spec_position_atol_m": None,
        "candidate_spec_orientation_atol_rad": None,
        "semantic_prefix_end_equivalence": _copy(semantic),
        "acceptance_prefix_end_equivalence": _copy(acceptance),
        "checks": checks,
        "pass": all(checks.values()),
        "formal_data": False,
        "stage0_data": False,
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


def audit_f4_frozen_canonical_neutral_spec_identity_v13(
    *,
    frozen_candidate: Mapping[str, Any],
    reconstructed_candidate: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Exact neutral identity layered on the retained v12 1e-5 audit."""

    validated = validate_f4_frozen_canonical_neutral_binding_v13(binding)
    frozen_neutral = _candidate_terminal_neutral_pose(frozen_candidate, "frozen")
    reconstructed_neutral = _candidate_terminal_neutral_pose(
        reconstructed_candidate, "reconstructed"
    )
    v12 = audit_f4_candidate_equivalence_v12(
        frozen_candidate, reconstructed_candidate
    )
    expected_pose = validated["canonical_terminal_neutral_pose"]
    expected_pose_sha = validated["canonical_terminal_neutral_pose_sha256"]
    frozen_targets = _copy(frozen_candidate.get("applied_planner_targets"))
    reconstructed_targets = _copy(
        reconstructed_candidate.get("applied_planner_targets")
    )
    frozen_contract_segments = _copy(
        frozen_candidate.get("candidate_contract_segments")
    )
    reconstructed_contract_segments = _copy(
        reconstructed_candidate.get("candidate_contract_segments")
    )
    target_lists_valid = all(
        isinstance(value, list) and bool(value)
        for value in (
            frozen_targets,
            reconstructed_targets,
            frozen_contract_segments,
            reconstructed_contract_segments,
        )
    )
    checks = {
        "all_applied_target_specs_exact": target_lists_valid
        and frozen_targets == reconstructed_targets,
        "all_contract_target_specs_exact": target_lists_valid
        and frozen_contract_segments == reconstructed_contract_segments,
        "all_applied_segment_ids_exact": target_lists_valid
        and [item.get("segment_id") for item in frozen_targets]
        == [item.get("segment_id") for item in reconstructed_targets],
        "candidate_application_sha256_exact": frozen_candidate.get(
            "candidate_application_sha256"
        )
        == reconstructed_candidate.get("candidate_application_sha256"),
        "frozen_neutral_exact_canonical_target": frozen_neutral == expected_pose,
        "reconstructed_neutral_exact_canonical_target": reconstructed_neutral
        == expected_pose,
        "frozen_and_reconstructed_neutral_exact": frozen_neutral
        == reconstructed_neutral,
        "frozen_neutral_pose_sha256_exact": _sha(frozen_neutral)
        == expected_pose_sha,
        "reconstructed_neutral_pose_sha256_exact": _sha(
            reconstructed_neutral
        )
        == expected_pose_sha,
        "candidate_receipt_binding_reference_exact": True,
        "candidate_receipt_neutral_pose_reference_exact": True,
        "v12_structure_exact_pose_1e5_audit_retained": v12.get("pass") is True,
        "target_spec_and_realized_prefix_state_are_separate": True,
    }
    receipt = {
        "schema_version": "cmf_f4_frozen_canonical_neutral_spec_identity_v13",
        "implementation_version": IMPLEMENTATION_VERSION,
        "candidate_id": frozen_candidate.get("candidate_id"),
        "applied_target_count": len(frozen_targets)
        if isinstance(frozen_targets, list)
        else None,
        "frozen_applied_targets_sha256": _sha(frozen_targets),
        "reconstructed_applied_targets_sha256": _sha(reconstructed_targets),
        "canonical_terminal_neutral_pose": list(expected_pose),
        "canonical_terminal_neutral_pose_sha256": expected_pose_sha,
        "frozen_canonical_neutral_binding_sha256": validated["binding_sha256"],
        "frozen_neutral_pose_sha256": _sha(frozen_neutral),
        "reconstructed_neutral_pose_sha256": _sha(reconstructed_neutral),
        "retained_candidate_equivalence_v12": v12,
        "checks": checks,
        "pass": all(checks.values()),
        "formal_data": False,
        "stage0_data": False,
    }
    receipt["receipt_sha256"] = _sha(receipt)
    return receipt


__all__ = [
    "BINDING_VERSION",
    "CANONICAL_SOURCE",
    "FORBIDDEN_NEUTRAL_SOURCES",
    "IMPLEMENTATION_VERSION",
    "SCHEMA_VERSION",
    "audit_f4_frozen_canonical_neutral_spec_identity_v13",
    "bind_f4_candidate_to_canonical_neutral_v13",
    "bind_f4_canonical_prefix_artifact_v13",
    "bind_f4_corridor_contract_to_canonical_neutral_v13",
    "build_f4_frozen_canonical_neutral_binding_from_artifacts_v13",
    "build_f4_frozen_canonical_neutral_binding_v13",
    "build_f4_realized_prefix_end_physical_equivalence_v13",
    "canonical_neutral_pose_sha256_v13",
    "validate_f4_frozen_canonical_neutral_binding_v13",
]
