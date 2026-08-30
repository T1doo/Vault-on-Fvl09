"""Pure F3 revision-8 physical-contact signal mapping.

PhysX can report near-contact manifolds inside its contact offset even when no
impulse is exchanged.  Pair presence therefore remains audit evidence only.
The hard physical-contact signal uses the preregistered project epsilon or a
non-positive signed separation, and fails closed if signed separation or
collision-shape identity is unavailable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "cmf_f3_physical_contact_signal_v8"
CONTACT_PAIR_SCHEMA_VERSION = "cmf_runtime_contact_pair_v2"
NONZERO_CONTACT_IMPULSE_EPS = 1e-10


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _json_safe(value: Any, *, path: str = "root") -> Any:
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path=path)
    if isinstance(value, np.generic):
        return _json_safe(value.item(), path=path)
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item, path=f"{path}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, float) and not np.isfinite(value):
        raise ValueError(f"non-finite value at {path}")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"non-JSON value at {path}: {type(value).__name__}")


def _finite_nonnegative(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result) or result < 0.0:
        return None
    return result


def _valid_shape_identities(pair: Mapping[str, Any]) -> tuple[bool, list[str]]:
    if pair.get("shape_identity_available") is not True:
        return False, []
    identities = pair.get("shape_identities")
    if not isinstance(identities, list) or len(identities) != 2:
        return False, []
    digests = []
    for identity in identities:
        if not isinstance(identity, Mapping):
            return False, []
        value = _json_safe(identity, path="shape_identity")
        digest = value.pop("identity_sha256", None)
        if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
            return False, []
        digests.append(digest)
    return True, digests


def _point_signal(
    pair: Mapping[str, Any], shape_digests: Sequence[str]
) -> tuple[bool, bool, bool, list[float], list[dict]]:
    point_count = pair.get("point_count")
    points = pair.get("point_evidence")
    if (
        not isinstance(point_count, int)
        or point_count <= 0
        or not isinstance(points, list)
        or len(points) != point_count
    ):
        return False, False, False, [], []
    separation_complete = True
    shape_complete = True
    impulse_complete = True
    separations = []
    evidence = []
    expected_shape_hashes = list(shape_digests)
    for point_index, point in enumerate(points):
        if not isinstance(point, Mapping):
            separation_complete = False
            shape_complete = False
            impulse_complete = False
            evidence.append(
                {
                    "point_index": point_index,
                    "impulse_available": False,
                    "signed_separation_available": False,
                    "shape_identity_available": False,
                }
            )
            continue
        separation = point.get("signed_separation_m")
        separation_available = point.get("signed_separation_available") is True
        try:
            separation_value = float(separation)
        except (TypeError, ValueError):
            separation_value = None
        if (
            not separation_available
            or separation_value is None
            or not np.isfinite(separation_value)
        ):
            separation_complete = False
            separation_value = None
        else:
            separations.append(separation_value)
        point_shape_hashes = point.get("shape_identity_sha256")
        shape_available = bool(
            point.get("shape_identity_available") is True
            and isinstance(point_shape_hashes, list)
            and point_shape_hashes == expected_shape_hashes
            and len(point_shape_hashes) == 2
        )
        if not shape_available:
            shape_complete = False
        point_impulse = _finite_nonnegative(point.get("impulse_norm"))
        point_impulse_available = bool(
            point.get("impulse_available") is True
            and point_impulse is not None
        )
        if not point_impulse_available:
            impulse_complete = False
        evidence.append(
            {
                "point_index": point_index,
                "impulse_norm": point_impulse,
                "impulse_available": point_impulse_available,
                "signed_separation_m": separation_value,
                "signed_separation_available": separation_value is not None,
                "shape_identity_available": shape_available,
                "shape_identity_sha256": point_shape_hashes
                if isinstance(point_shape_hashes, list)
                else [],
            }
        )
    return (
        separation_complete,
        shape_complete,
        impulse_complete,
        separations,
        evidence,
    )


def classify_contact_pair_physical_hit_v8(
    contact_pair: Mapping[str, Any],
) -> dict:
    """Classify one pair; unavailable evidence blocks contact-free progress."""

    if not isinstance(contact_pair, Mapping):
        raise TypeError("F3 contact-pair signal requires a mapping")
    pair = _json_safe(contact_pair, path="contact_pair")
    body_a = pair.get("body_a")
    body_b = pair.get("body_b")
    body_identity_available = bool(
        isinstance(body_a, str)
        and body_a
        and isinstance(body_b, str)
        and body_b
    )
    schema_available = bool(
        pair.get("contact_pair_schema_version")
        == CONTACT_PAIR_SCHEMA_VERSION
    )
    shapes_available, shape_hashes = _valid_shape_identities(pair)
    (
        separations_complete,
        point_shapes_complete,
        point_impulses_complete,
        separations,
        point_evidence,
    ) = _point_signal(pair, shape_hashes)
    impulse = _finite_nonnegative(pair.get("impulse_norm_sum"))
    impulse_available = bool(
        pair.get("impulse_available") is True
        and impulse is not None
        and point_impulses_complete
    )
    shape_evidence_complete = bool(
        shapes_available and point_shapes_complete
    )
    checks = {
        "body_identity_available": body_identity_available,
        "v2_contact_pair_schema_available": schema_available,
        "impulse_available": impulse_available,
        "signed_separation_available_for_all_points": (
            separations_complete
        ),
        "shape_identity_available_for_all_points": (
            shape_evidence_complete
        ),
    }
    evidence_complete = all(checks.values())
    impulse_hit = bool(
        impulse_available and impulse > NONZERO_CONTACT_IMPULSE_EPS
    )
    separation_hit = bool(
        separations and any(value <= 0.0 for value in separations)
    )
    observed_physical_contact = bool(impulse_hit or separation_hit)
    fail_closed_hit = bool(observed_physical_contact or not evidence_complete)
    reasons = [
        reason
        for reason, active in (
            ("impulse_above_epsilon", impulse_hit),
            ("nonpositive_signed_separation", separation_hit),
            ("signal_unavailable_fail_closed", not evidence_complete),
        )
        if active
    ]
    receipt = {
        "schema_version": "cmf_f3_contact_pair_physical_hit_v8",
        "contact_pair_schema_version": pair.get(
            "contact_pair_schema_version"
        ),
        "formal_data": False,
        "stage0_data": False,
        "body_a": body_a,
        "body_b": body_b,
        "pair_presence_is_audit_only": True,
        "physical_contact_definition": (
            "impulse_norm_sum > 1e-10 OR any signed separation <= 0"
        ),
        "nonzero_contact_impulse_eps": NONZERO_CONTACT_IMPULSE_EPS,
        "checks": checks,
        "evidence_complete": evidence_complete,
        "impulse_norm_sum": impulse,
        "minimum_signed_separation_m": min(separations)
        if separations
        else None,
        "maximum_signed_separation_m": max(separations)
        if separations
        else None,
        "shape_identity_sha256": shape_hashes,
        "point_evidence": point_evidence,
        "observed_physical_contact": observed_physical_contact,
        "physical_hit_for_gate": fail_closed_hit,
        "physical_contact_reasons": reasons,
        "missing_signal_policy": "block_contact_free_fail_closed",
    }
    receipt = _json_safe(receipt)
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return validate_contact_pair_physical_hit_v8(receipt)


def validate_contact_pair_physical_hit_v8(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("F3 pair physical-hit receipt must be a mapping")
    value = _json_safe(receipt)
    digest = value.pop("receipt_sha256", None)
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F3 pair physical-hit receipt hash mismatch")
    if (
        value.get("schema_version")
        != "cmf_f3_contact_pair_physical_hit_v8"
        or value.get("nonzero_contact_impulse_eps")
        != NONZERO_CONTACT_IMPULSE_EPS
        or value.get("pair_presence_is_audit_only") is not True
        or value.get("missing_signal_policy")
        != "block_contact_free_fail_closed"
    ):
        raise ValueError("F3 pair physical-hit receipt contract mismatch")
    checks = value.get("checks")
    if not isinstance(checks, Mapping):
        raise ValueError("F3 pair physical-hit checks are missing")
    complete = all(bool(item) for item in checks.values())
    if value.get("evidence_complete") is not complete:
        raise ValueError("F3 pair physical-hit completeness mismatch")
    expected_gate_hit = bool(
        value.get("observed_physical_contact") is True or not complete
    )
    if value.get("physical_hit_for_gate") is not expected_gate_hit:
        raise ValueError("F3 pair physical-hit fail-closed mismatch")
    value["receipt_sha256"] = digest
    return value


def classify_f3_preopen_support_contacts_v8(
    contact_pair_frames: Sequence[Sequence[Mapping[str, Any]]],
    *,
    bottle_actor_name: str,
    gripper_assembly_link_names: Sequence[str],
    support_actor_names: Sequence[str],
) -> dict:
    """Classify physical support contact while retaining pair presence audit."""

    frames = list(contact_pair_frames)
    if not isinstance(bottle_actor_name, str) or not bottle_actor_name:
        raise ValueError("F3 physical contact signal requires a bottle name")
    assembly = {str(value) for value in gripper_assembly_link_names}
    supports = {str(value) for value in support_actor_names}
    if not assembly or not supports:
        raise ValueError("F3 physical contact signal requires assembly/support names")

    pair_presence = {"bottle_support": [], "assembly_support": []}
    physical_hits = {"bottle_support": [], "assembly_support": []}
    all_impulses_available = True
    all_contact_pairs_use_v2_schema = True
    all_signed_separations_available = True
    all_shape_identities_available = True
    relevant_pair_count = 0

    for frame_index, frame in enumerate(frames):
        if not isinstance(frame, (list, tuple)):
            raise TypeError("each F3 contact frame must be a list of pairs")
        for pair_index, pair_raw in enumerate(frame):
            if not isinstance(pair_raw, Mapping):
                raise TypeError("each F3 contact pair must be a mapping")
            pair = _json_safe(pair_raw, path="contact_pair")
            bodies = {str(pair.get("body_a")), str(pair.get("body_b"))}
            if not bodies & supports:
                continue
            categories = []
            if bottle_actor_name in bodies:
                categories.append("bottle_support")
            if bodies & assembly:
                categories.append("assembly_support")
            if not categories:
                continue
            relevant_pair_count += 1
            pair_signal = classify_contact_pair_physical_hit_v8(pair)
            if not pair_signal["checks"][
                "v2_contact_pair_schema_available"
            ]:
                all_contact_pairs_use_v2_schema = False
            impulse = pair_signal["impulse_norm_sum"]
            impulse_available = pair_signal["checks"]["impulse_available"]
            if not impulse_available:
                all_impulses_available = False
            shape_hashes = pair_signal["shape_identity_sha256"]
            shapes_available = pair_signal["checks"][
                "shape_identity_available_for_all_points"
            ]
            if not shapes_available:
                all_shape_identities_available = False
            separations_complete = pair_signal["checks"][
                "signed_separation_available_for_all_points"
            ]
            if not separations_complete:
                all_signed_separations_available = False
            physical_hit = pair_signal["physical_hit_for_gate"]
            record = {
                "frame_index": frame_index,
                "pair_index": pair_index,
                "body_a": pair.get("body_a"),
                "body_b": pair.get("body_b"),
                "contact_pair_schema_version": pair.get(
                    "contact_pair_schema_version"
                ),
                "point_count": pair.get("point_count"),
                "impulse_norm_sum": impulse,
                "impulse_available": impulse_available,
                "minimum_signed_separation_m": pair_signal[
                    "minimum_signed_separation_m"
                ],
                "maximum_signed_separation_m": pair_signal[
                    "maximum_signed_separation_m"
                ],
                "signed_separation_available": separations_complete,
                "shape_identity_available": shapes_available,
                "shape_identity_sha256": shape_hashes,
                "point_evidence": pair_signal["point_evidence"],
                "physical_contact": physical_hit,
                "observed_physical_contact": pair_signal[
                    "observed_physical_contact"
                ],
                "physical_contact_reasons": pair_signal[
                    "physical_contact_reasons"
                ],
                "pair_physical_hit_receipt_sha256": pair_signal[
                    "receipt_sha256"
                ],
            }
            for category in categories:
                pair_presence[category].append(record)
                if physical_hit:
                    physical_hits[category].append(record)

    checks = {
        "all_relevant_pairs_use_v2_contact_schema": (
            all_contact_pairs_use_v2_schema
        ),
        "all_relevant_pair_impulses_available": all_impulses_available,
        "all_relevant_points_have_signed_separation": (
            all_signed_separations_available
        ),
        "all_relevant_points_have_shape_identity": (
            all_shape_identities_available
        ),
        "bottle_has_no_physical_support_contact": not physical_hits[
            "bottle_support"
        ],
        "gripper_assembly_has_no_physical_support_contact": not physical_hits[
            "assembly_support"
        ],
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "contact_pair_schema_version": CONTACT_PAIR_SCHEMA_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "frame_count": len(frames),
        "bottle_actor_name": bottle_actor_name,
        "gripper_assembly_link_names": sorted(assembly),
        "support_actor_names": sorted(supports),
        "pair_presence_is_audit_only": True,
        "physical_contact_definition": (
            "impulse_norm_sum > 1e-10 OR any signed separation <= 0"
        ),
        "nonzero_contact_impulse_eps": NONZERO_CONTACT_IMPULSE_EPS,
        "signed_separation_source": "SAPIEN PhysxContactPoint.separation",
        "shape_identity_source": (
            "contact.shapes matched by identity to body collision-shape index"
        ),
        "missing_signal_policy": "fail_closed",
        "r6_runtime_geometry_gate_required_separately": True,
        "relevant_pair_count": relevant_pair_count,
        "pair_presence_audit": pair_presence,
        "physical_support_hits": physical_hits,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt = _json_safe(receipt)
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return validate_f3_physical_contact_signal_v8(receipt)


def validate_f3_physical_contact_signal_v8(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("F3 physical contact receipt must be a mapping")
    value = _json_safe(receipt)
    digest = value.pop("receipt_sha256", None)
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F3 physical contact receipt hash mismatch")
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("contact_pair_schema_version")
        != CONTACT_PAIR_SCHEMA_VERSION
        or value.get("nonzero_contact_impulse_eps")
        != NONZERO_CONTACT_IMPULSE_EPS
        or value.get("pair_presence_is_audit_only") is not True
        or value.get("missing_signal_policy") != "fail_closed"
        or value.get("r6_runtime_geometry_gate_required_separately")
        is not True
    ):
        raise ValueError("F3 physical contact receipt contract mismatch")
    checks = value.get("checks")
    if not isinstance(checks, Mapping) or value.get("pass") is not all(
        bool(item) for item in checks.values()
    ):
        raise ValueError("F3 physical contact receipt pass/check mismatch")
    value["receipt_sha256"] = digest
    return value


__all__ = [
    "CONTACT_PAIR_SCHEMA_VERSION",
    "NONZERO_CONTACT_IMPULSE_EPS",
    "SCHEMA_VERSION",
    "canonical_json_sha256",
    "classify_contact_pair_physical_hit_v8",
    "classify_f3_preopen_support_contacts_v8",
    "validate_contact_pair_physical_hit_v8",
    "validate_f3_physical_contact_signal_v8",
]
