"""Per-segment joint-limit evidence using the existing exact-limit policy."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

import numpy as np


AUDIT_VERSION = "cmf_joint_limit_audit_v3_4_1_exact_existing_limits"


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def audit_terminal_qpos_against_joint_limits(
    active_joints: Sequence[Any], terminal_qpos: Sequence[float]
) -> dict[str, Any]:
    qpos = np.asarray(terminal_qpos, dtype=np.float64).reshape(-1)
    joints = list(active_joints)
    if len(joints) != len(qpos) or not np.all(np.isfinite(qpos)):
        raise ValueError("joint-limit audit qpos/joint count is invalid")
    limits = np.asarray(
        [
            np.asarray(joint.get_limits(), dtype=np.float64).reshape(-1, 2)[0]
            for joint in joints
        ],
        dtype=np.float64,
    )
    margins = np.minimum(qpos - limits[:, 0], limits[:, 1] - qpos)
    finite = np.isfinite(margins)
    minimum = float(np.min(margins[finite])) if np.any(finite) else None
    within = bool(
        np.all((~np.isfinite(limits[:, 0])) | (qpos >= limits[:, 0]))
        and np.all((~np.isfinite(limits[:, 1])) | (qpos <= limits[:, 1]))
    )
    result = {
        "joint_limit_audit_version": AUDIT_VERSION,
        "terminal_qpos": qpos.tolist(),
        "terminal_qpos_sha256": hashlib.sha256(
            np.ascontiguousarray(qpos).tobytes()
        ).hexdigest(),
        "terminal_joint_limit_margin_rad": [
            float(value) if np.isfinite(value) else None for value in margins
        ],
        "minimum_terminal_joint_limit_margin_rad": minimum,
        "terminal_qpos_within_joint_limits": within,
        "joint_limit_threshold_changed": False,
        "evidence_complete": True,
    }
    result["receipt_sha256"] = _sha(result)
    return result


__all__ = ["AUDIT_VERSION", "audit_terminal_qpos_against_joint_limits"]
