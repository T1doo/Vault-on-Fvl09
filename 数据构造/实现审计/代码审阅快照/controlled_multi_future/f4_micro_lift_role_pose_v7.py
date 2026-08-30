"""Pure F4 r7 verifier wiring for the A-only micro-lift diagnostic.

Revision 6 preserved two distinct pose streams during the common-X prefix and
the later A diagnostic:

* ``actor_pose`` remained the prefix trace actor (``common_x``); and
* ``role_actor_poses["A"]`` contained the realized A-cube pose.

The revision-6 verifier accidentally used the first stream for A's rise.  It
also treated a zero-impulse speculative A/table manifold as physical support.
This dependency-free module fixes only those two signal-adapter errors.  All
numeric revision-5 micro-lift thresholds and the independent noninterference
Gate are retained unchanged.

This module cannot retroactively accept revision 6.  A passing receipt is a
CPU/verifier result only and requires a fresh source-distinct real execution.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .f4_boundary_micro_lift_v5 import (
    MICRO_LIFT_FRAME_COUNT,
    MICRO_LIFT_TABLE_FREE_TAIL_FRAMES,
    NONZERO_CONTACT_IMPULSE_EPS,
    build_a_micro_lift_gate_receipt_v5,
    canonical_json_sha256,
    validate_a_micro_lift_gate_receipt_v5,
)


SCHEMA_VERSION = "cmf_f4_a_role_pose_micro_lift_gate_v7"
ROW_ADAPTER_SCHEMA_VERSION = "cmf_f4_a_role_pose_micro_lift_rows_v7"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
EXPECTED_ROLE = "A"
TABLE_BODY_NAME = "table"
REQUIRED_NONINTERFERENCE_SCHEMA = "cmf_f4_micro_lift_noninterference_v5"
REQUIRED_NONINTERFERENCE_ROLES = ("common_x", "B", "C")
REQUIRED_NONINTERFERENCE_STAGES = (
    "after_A_pregrasp",
    "after_A_grasp",
    "after_A_micro_lift",
)


def _json_safe(value: Any, *, path: str = "value") -> Any:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise ValueError(f"{path} must be finite")
        return result
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist(), path=path)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} mapping keys must be strings")
            result[key] = _json_safe(item, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [
            _json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(f"{path} contains unsupported type {type(value).__name__}")


def _pose(value: Any, *, label: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if result.shape != (7,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be finite shape (7,)")
    if float(np.linalg.norm(result[3:])) <= 1e-12:
        raise ValueError(f"{label} quaternion must be nonzero")
    return np.ascontiguousarray(result)


def _contact_pairs(value: Any, *, label: str) -> list[dict]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{label} must be a contact sequence")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"{label}[{index}] must be a mapping")
        body_a = item.get("body_a")
        body_b = item.get("body_b")
        if not isinstance(body_a, str) or not body_a:
            raise ValueError(f"{label}[{index}] body_a must be nonempty")
        if not isinstance(body_b, str) or not body_b:
            raise ValueError(f"{label}[{index}] body_b must be nonempty")
        try:
            impulse = float(item.get("impulse_norm_sum", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}[{index}] impulse must be numeric") from exc
        if not np.isfinite(impulse) or impulse < 0.0:
            raise ValueError(
                f"{label}[{index}] impulse must be finite nonnegative"
            )
        result.append(
            {
                "body_a": body_a,
                "body_b": body_b,
                "impulse_norm_sum": impulse,
            }
        )
    return result


def _is_actor_table_pair(pair: Mapping[str, Any], actor_name: str) -> bool:
    names = (pair["body_a"], pair["body_b"])
    return actor_name in names and TABLE_BODY_NAME in names


def _validate_noninterference_receipt(value: Mapping[str, Any]) -> dict:
    if not isinstance(value, Mapping):
        raise TypeError("F4 r7 noninterference receipt must be a mapping")
    receipt = _json_safe(value, path="noninterference_receipt")
    digest = receipt.pop("receipt_sha256", None)
    if receipt.get("schema_version") != REQUIRED_NONINTERFERENCE_SCHEMA:
        raise ValueError("F4 r7 noninterference schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(receipt) != digest:
        raise ValueError("F4 r7 noninterference receipt hash mismatch")
    if set(receipt.get("roles", ())) != set(REQUIRED_NONINTERFERENCE_ROLES):
        raise ValueError("F4 r7 noninterference roles changed")
    stage_pass = receipt.get("stage_pass")
    if not isinstance(stage_pass, Mapping) or set(stage_pass) != set(
        REQUIRED_NONINTERFERENCE_STAGES
    ):
        raise ValueError("F4 r7 noninterference stages changed")
    if receipt.get("pass") != all(value is True for value in stage_pass.values()):
        raise ValueError("F4 r7 noninterference aggregate mismatch")
    stages = receipt.get("stages")
    if not isinstance(stages, list) or len(stages) != len(
        REQUIRED_NONINTERFERENCE_STAGES
    ):
        raise ValueError("F4 r7 noninterference stage receipts changed")
    stage_by_id = {
        item.get("stage_id"): item
        for item in stages
        if isinstance(item, Mapping)
    }
    if set(stage_by_id) != set(REQUIRED_NONINTERFERENCE_STAGES):
        raise ValueError("F4 r7 noninterference stage receipt IDs changed")
    if any(
        stage_by_id[stage_id].get("pass") is not stage_pass[stage_id]
        for stage_id in REQUIRED_NONINTERFERENCE_STAGES
    ):
        raise ValueError("F4 r7 noninterference stage receipt mismatch")
    return _json_safe(value, path="noninterference_receipt")


def build_a_role_pose_micro_lift_rows_v7(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    source_trace_indices: Sequence[int],
    expected_actor_name: str,
    role: str = EXPECTED_ROLE,
) -> dict:
    """Adapt dense trace rows into v5 Gate rows using A's explicit role stream."""

    if role != EXPECTED_ROLE:
        raise ValueError("F4 r7 micro-lift role must remain A")
    if not isinstance(expected_actor_name, str) or not expected_actor_name:
        raise ValueError("F4 r7 expected A actor name must be nonempty")
    if isinstance(trace_rows, (str, bytes)) or not isinstance(
        trace_rows, Sequence
    ):
        raise TypeError("F4 r7 trace_rows must be a sequence")
    if len(trace_rows) < MICRO_LIFT_FRAME_COUNT:
        raise ValueError(
            f"F4 r7 requires at least {MICRO_LIFT_FRAME_COUNT} micro-lift rows"
        )
    if isinstance(source_trace_indices, (str, bytes)) or not isinstance(
        source_trace_indices, Sequence
    ):
        raise TypeError("F4 r7 source_trace_indices must be a sequence")
    if len(source_trace_indices) != len(trace_rows):
        raise ValueError("F4 r7 trace rows and source indices differ in length")
    indices = []
    for raw in source_trace_indices:
        if isinstance(raw, bool) or not isinstance(raw, (int, np.integer)):
            raise TypeError("F4 r7 source trace indices must be integers")
        indices.append(int(raw))
    if any(right <= left for left, right in zip(indices, indices[1:])):
        raise ValueError("F4 r7 source trace indices must be strictly increasing")

    gate_rows = []
    frame_audit = []
    for frame_index, (raw, source_index) in enumerate(zip(trace_rows, indices)):
        if not isinstance(raw, Mapping):
            raise TypeError(f"F4 r7 trace row {frame_index} must be a mapping")
        role_poses = raw.get("role_actor_poses")
        if not isinstance(role_poses, Mapping) or role not in role_poses:
            raise ValueError(
                f"F4 r7 trace row {frame_index} lacks role_actor_poses[{role!r}]"
            )
        role_pose = _pose(
            role_poses[role], label=f"F4 r7 trace row {frame_index} role A pose"
        )
        trace_actor_pose = raw.get("actor_pose")
        trace_actor_pose_audit = (
            None
            if trace_actor_pose is None
            else _pose(
                trace_actor_pose,
                label=f"F4 r7 trace row {frame_index} trace actor pose",
            ).tolist()
        )
        selected = raw.get("selected_gripper_contact")
        if not isinstance(selected, (bool, np.bool_)):
            raise TypeError("F4 r7 selected gripper contact must be bool")
        count = raw.get("selected_gripper_contact_count")
        if (
            isinstance(count, bool)
            or not isinstance(count, (int, np.integer))
            or int(count) < 0
        ):
            raise TypeError("F4 r7 selected contact count must be nonnegative int")
        selected_actor_name = raw.get("selected_contact_actor_name")
        if not isinstance(selected_actor_name, str):
            raise TypeError("F4 r7 selected contact actor name must be str")
        contacts = _contact_pairs(
            raw.get("contact_pairs"), label=f"F4 r7 trace row {frame_index} contacts"
        )
        table_impulses = [
            item["impulse_norm_sum"]
            for item in contacts
            if _is_actor_table_pair(item, expected_actor_name)
        ]
        pair_present = bool(table_impulses)
        impulse_sum = float(sum(table_impulses))
        nonzero_contact = any(
            value > NONZERO_CONTACT_IMPULSE_EPS for value in table_impulses
        )
        gate_rows.append(
            {
                "actor_pose": role_pose.tolist(),
                "selected_gripper_contact": bool(selected),
                "selected_gripper_contact_count": int(count),
                "selected_contact_actor_name": selected_actor_name,
                "actor_table_contact": bool(nonzero_contact),
                "contact_pairs": contacts,
                "source_trace_index": source_index,
            }
        )
        frame_audit.append(
            {
                "frame_index": frame_index,
                "source_trace_index": source_index,
                "role": role,
                "role_actor_pose": role_pose.tolist(),
                "trace_actor_pose_audit_only": trace_actor_pose_audit,
                "actor_table_pair_present": pair_present,
                "actor_table_pair_impulse_norm_sum": impulse_sum,
                "actor_table_nonzero_impulse_contact": bool(nonzero_contact),
            }
        )

    tail = frame_audit[-MICRO_LIFT_TABLE_FREE_TAIL_FRAMES:]
    adapter = {
        "schema_version": ROW_ADAPTER_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "role": role,
        "expected_actor_name": expected_actor_name,
        "frame_count": len(gate_rows),
        "source_trace_indices": indices,
        "actor_pose_source": 'trace_rows[*].role_actor_poses["A"]',
        "trace_actor_pose_status": (
            "audit_only_prefix_actor_stream_never_used_for_A_rise"
        ),
        "actor_table_pair_presence_status": "audit_only",
        "physical_table_contact_definition": (
            "A/table pair impulse_norm_sum > nonzero_contact_impulse_eps"
        ),
        "nonzero_contact_impulse_eps": NONZERO_CONTACT_IMPULSE_EPS,
        "frame_audit": frame_audit,
        "gate_rows": gate_rows,
        "summary": {
            "actor_start_z_m": gate_rows[0]["actor_pose"][2],
            "actor_end_z_m": gate_rows[-1]["actor_pose"][2],
            "actor_rise_m": (
                gate_rows[-1]["actor_pose"][2]
                - gate_rows[0]["actor_pose"][2]
            ),
            "actor_table_pair_presence_count": sum(
                item["actor_table_pair_present"] for item in frame_audit
            ),
            "actor_table_nonzero_impulse_contact_count": sum(
                item["actor_table_nonzero_impulse_contact"]
                for item in frame_audit
            ),
            "tail_pair_presence": [
                item["actor_table_pair_present"] for item in tail
            ],
            "tail_nonzero_impulse_contact": [
                item["actor_table_nonzero_impulse_contact"] for item in tail
            ],
            "tail_impulse_norm_sum": [
                item["actor_table_pair_impulse_norm_sum"] for item in tail
            ],
        },
        "checks": {
            "role_specific_pose_present_every_frame": True,
            "source_trace_indices_strictly_increasing": True,
            "trace_actor_pose_not_used_as_A_pose": True,
            "table_pair_presence_and_nonzero_contact_separated": True,
        },
        "pass": True,
    }
    adapter = _json_safe(adapter)
    adapter["receipt_sha256"] = canonical_json_sha256(adapter)
    return adapter


def build_a_role_pose_micro_lift_gate_receipt_v7(
    *,
    targets: Sequence[Mapping[str, Any]],
    realized_pregrasp_pose: Sequence[float],
    realized_grasp_pose: Sequence[float],
    pregrasp_linear_velocity: Sequence[float],
    pregrasp_angular_velocity: Sequence[float],
    grasp_linear_velocity: Sequence[float],
    grasp_angular_velocity: Sequence[float],
    preclose_right_gripper_joint_qpos: Sequence[float],
    trace_rows: Sequence[Mapping[str, Any]],
    source_trace_indices: Sequence[int],
    expected_actor_name: str,
    allowed_nonzero_contact_pairs: Sequence[Sequence[str]],
    noninterference_receipt: Mapping[str, Any],
) -> dict:
    """Build the corrected r7 A micro-lift plus noninterference receipt."""

    adapter = build_a_role_pose_micro_lift_rows_v7(
        trace_rows=trace_rows,
        source_trace_indices=source_trace_indices,
        expected_actor_name=expected_actor_name,
    )
    gate_v5 = build_a_micro_lift_gate_receipt_v5(
        targets=targets,
        realized_pregrasp_pose=realized_pregrasp_pose,
        realized_grasp_pose=realized_grasp_pose,
        pregrasp_linear_velocity=pregrasp_linear_velocity,
        pregrasp_angular_velocity=pregrasp_angular_velocity,
        grasp_linear_velocity=grasp_linear_velocity,
        grasp_angular_velocity=grasp_angular_velocity,
        preclose_right_gripper_joint_qpos=preclose_right_gripper_joint_qpos,
        micro_lift_rows=adapter["gate_rows"],
        expected_actor_name=expected_actor_name,
        allowed_nonzero_contact_pairs=allowed_nonzero_contact_pairs,
    )
    validate_a_micro_lift_gate_receipt_v5(gate_v5)
    noninterference = _validate_noninterference_receipt(
        noninterference_receipt
    )
    checks = {
        "role_pose_adapter_pass": adapter["pass"],
        "micro_lift_gate_pass": gate_v5["pass"],
        "selected_actor_identity": gate_v5["checks"][
            "selected_actor_identity"
        ],
        "selected_contact_fraction": gate_v5["checks"][
            "selected_contact_fraction"
        ],
        "selected_contact_break_count": gate_v5["checks"][
            "selected_contact_break_count"
        ],
        "bilateral_contact": gate_v5["checks"]["bilateral_contact"],
        "noninterference_gate_pass": noninterference["pass"],
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "formal_data": False,
        "stage0_data": False,
        "diagnostic_only": True,
        "role": EXPECTED_ROLE,
        "expected_actor_name": expected_actor_name,
        "role_pose_adapter": adapter,
        "micro_lift_gate_v5_thresholds_unchanged": True,
        "micro_lift_gate": gate_v5,
        "noninterference_gate": noninterference,
        "scene_layout_changed": False,
        "right_arm_changed": False,
        "targets_changed_from_revision6": False,
        "numeric_threshold_changed": False,
        "revision6_retroactive_acceptance_allowed": False,
        "fresh_source_distinct_execution_required": True,
        "checks": checks,
        "pass": all(checks.values()),
    }
    receipt = _json_safe(receipt)
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return receipt


def validate_a_role_pose_micro_lift_gate_receipt_v7(
    receipt: Mapping[str, Any],
) -> dict:
    if not isinstance(receipt, Mapping):
        raise TypeError("F4 r7 role-pose micro-lift receipt must be a mapping")
    value = _json_safe(receipt)
    digest = value.pop("receipt_sha256", None)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F4 r7 role-pose micro-lift schema mismatch")
    if not isinstance(digest, str) or canonical_json_sha256(value) != digest:
        raise ValueError("F4 r7 role-pose micro-lift receipt hash mismatch")
    if value.get("revision6_retroactive_acceptance_allowed") is not False:
        raise ValueError("F4 r7 cannot retroactively accept revision 6")
    if value.get("fresh_source_distinct_execution_required") is not True:
        raise ValueError("F4 r7 must require a fresh source-distinct execution")
    if value.get("numeric_threshold_changed") is not False:
        raise ValueError("F4 r7 numeric thresholds changed")
    if value.get("pass") != all(value.get("checks", {}).values()):
        raise ValueError("F4 r7 role-pose micro-lift aggregate mismatch")
    validate_a_micro_lift_gate_receipt_v5(value["micro_lift_gate"])
    _validate_noninterference_receipt(value["noninterference_gate"])
    adapter = value.get("role_pose_adapter")
    if not isinstance(adapter, Mapping):
        raise ValueError("F4 r7 role-pose adapter receipt is missing")
    adapter_copy = dict(adapter)
    adapter_hash = adapter_copy.pop("receipt_sha256", None)
    if (
        adapter_copy.get("schema_version") != ROW_ADAPTER_SCHEMA_VERSION
        or not isinstance(adapter_hash, str)
        or canonical_json_sha256(adapter_copy) != adapter_hash
    ):
        raise ValueError("F4 r7 role-pose adapter receipt hash mismatch")
    return _json_safe(receipt)


__all__ = [
    "EXPECTED_ROLE",
    "ROW_ADAPTER_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "build_a_role_pose_micro_lift_gate_receipt_v7",
    "build_a_role_pose_micro_lift_rows_v7",
    "validate_a_role_pose_micro_lift_gate_receipt_v7",
]
