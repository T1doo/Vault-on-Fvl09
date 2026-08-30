"""Pure-CPU F2 revision-5 gripper-assembly topology contract.

RoboTwin's Aloha embodiment names the terminal move-group link as the palm
(``fl_link6``) and mounts both prismatic finger joints on that link.  The raw
selected-contact signal intentionally remains finger-only; a palm contact may
be allowed as an additional gripper-assembly body, but palm-only contact must
never satisfy grasp continuity.

This module accepts only serializable topology primitives.  It does not import
SAPIEN, inspect a live scene, query a planner, execute an action, authorize a
GPU probe, or authorize Stage 0.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "cmf_f2_validated_gripper_assembly_topology_v1"
DESIGN_VERSION = "controlled_multi_future_f1_f4_v1_2"
IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_3"
IMPLEMENTATION_PROPOSAL = "f2_r5_move_group_palm_contact_classification_v1"

F2_EXECUTION_ARM = "left"
F2_EXPECTED_FINGER_JOINT_COUNT = 2


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty_name(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _unique_names(values: Sequence[str], *, label: str) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{label} must be a sequence of names")
    names = [_nonempty_name(value, label=f"{label} item") for value in values]
    if len(names) != len(set(names)):
        raise ValueError(f"{label} must not contain duplicates")
    return names


def _joint_topology(
    values: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("gripper_joint_topology must be a sequence")
    if len(values) != F2_EXPECTED_FINGER_JOINT_COUNT:
        raise ValueError(
            "F2 Aloha gripper topology must contain exactly two finger joints"
        )
    result = []
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise ValueError(f"gripper joint topology item {index} is not a mapping")
        if set(value) != {
            "joint_name",
            "parent_link_name",
            "child_link_name",
        }:
            raise ValueError(
                "each gripper joint topology item must contain exactly "
                "joint_name, parent_link_name, and child_link_name"
            )
        result.append(
            {
                "joint_name": _nonempty_name(
                    value["joint_name"], label=f"joint {index} name"
                ),
                "parent_link_name": _nonempty_name(
                    value["parent_link_name"], label=f"joint {index} parent"
                ),
                "child_link_name": _nonempty_name(
                    value["child_link_name"], label=f"joint {index} child"
                ),
            }
        )
    if len({item["joint_name"] for item in result}) != len(result):
        raise ValueError("gripper joint names must be unique")
    if len({item["child_link_name"] for item in result}) != len(result):
        raise ValueError("gripper finger child links must be unique")
    return result


def build_f2_gripper_assembly_topology_receipt(
    *,
    arm: str,
    move_group_link_name: str,
    gripper_joint_topology: Sequence[Mapping[str, str]],
    articulation_link_names: Sequence[str],
    selected_contact_signal_link_names: Sequence[str],
    fixed_gripper_link_names: Sequence[str] = (),
) -> dict[str, Any]:
    """Validate the palm/finger topology and return a self-hashed receipt.

    ``selected_contact_signal_link_names`` is the existing finger-contact
    signal source.  The move-group palm is deliberately required to be absent
    from that set, then added only to the assembly bodies allowed by the F2
    body-pair contact audit.
    """

    execution_arm = _nonempty_name(arm, label="arm")
    if execution_arm != F2_EXECUTION_ARM:
        raise ValueError("F2 revision-5 topology is frozen to the left arm")
    palm = _nonempty_name(move_group_link_name, label="move_group_link_name")
    joints = _joint_topology(gripper_joint_topology)
    articulation_links = _unique_names(
        articulation_link_names, label="articulation_link_names"
    )
    selected_signal = _unique_names(
        selected_contact_signal_link_names,
        label="selected_contact_signal_link_names",
    )
    fixed_links = _unique_names(
        fixed_gripper_link_names, label="fixed_gripper_link_names"
    )

    articulation_set = set(articulation_links)
    parent_links = {item["parent_link_name"] for item in joints}
    finger_children = {item["child_link_name"] for item in joints}
    selected_set = set(selected_signal)
    fixed_set = set(fixed_links)
    expected_selected_signal = finger_children | fixed_set

    checks = {
        "left_arm_fixed": execution_arm == F2_EXECUTION_ARM,
        "move_group_palm_exists": palm in articulation_set,
        "exactly_two_finger_joints": len(joints)
        == F2_EXPECTED_FINGER_JOINT_COUNT,
        "palm_is_common_finger_parent": parent_links == {palm},
        "finger_children_exist": finger_children.issubset(articulation_set),
        "fixed_gripper_links_exist": fixed_set.issubset(articulation_set),
        "fixed_links_disjoint_from_fingers": fixed_set.isdisjoint(
            finger_children
        ),
        "palm_distinct_from_finger_and_fixed_links": palm
        not in finger_children | fixed_set,
        "selected_signal_is_exactly_fingers_and_fixed_links": selected_set
        == expected_selected_signal,
        "palm_absent_from_selected_contact_signal": palm not in selected_set,
        "selected_signal_nonempty": bool(selected_set),
    }
    if not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise ValueError(
            "F2 gripper assembly topology failed closed: " + ", ".join(failures)
        )

    additional_allowed = [palm]
    allowed_assembly = sorted(selected_set | {palm})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "design_version": DESIGN_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_proposal": IMPLEMENTATION_PROPOSAL,
        "formal_data": False,
        "stage0_data": False,
        "stage0_authorized": False,
        "family": "F2",
        "arm": execution_arm,
        "move_group_palm_link_name": palm,
        "gripper_joint_topology": joints,
        "articulation_link_names": sorted(articulation_set),
        "fixed_gripper_link_names": sorted(fixed_set),
        "finger_child_link_names": sorted(finger_children),
        "selected_contact_signal_link_names": sorted(selected_set),
        "additional_allowed_gripper_assembly_body_names": additional_allowed,
        "allowed_gripper_assembly_body_names": allowed_assembly,
        "finger_contact_signal_remains_required": True,
        "palm_contact_alone_satisfies_selected_contact": False,
        "classification": {
            "selected_contact_signal": "finger links plus configured fixed finger links",
            "additional_allowed_body_pair_contact": "validated move-group palm only",
        },
        "checks": checks,
        "pass": True,
    }
    payload["receipt_sha256"] = _canonical_sha256(payload)
    # This round trip is also an explicit no-NaN/JSON-safety assertion.
    return json.loads(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    )


def validate_f2_gripper_assembly_topology_receipt(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a serialized receipt without trusting its ``pass`` field."""

    if not isinstance(receipt, Mapping):
        raise ValueError("F2 gripper topology receipt must be a mapping")
    value = json.loads(
        json.dumps(
            receipt,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    )
    receipt_hash = value.pop("receipt_sha256", None)
    if not isinstance(receipt_hash, str) or _canonical_sha256(value) != receipt_hash:
        raise ValueError("F2 gripper topology receipt hash mismatch")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("F2 gripper topology receipt schema mismatch")
    if (
        value.get("formal_data") is not False
        or value.get("stage0_data") is not False
        or value.get("stage0_authorized") is not False
    ):
        raise ValueError("F2 gripper topology receipt cannot authorize data collection")
    if value.get("family") != "F2" or value.get("arm") != F2_EXECUTION_ARM:
        raise ValueError("F2 gripper topology receipt identity mismatch")
    checks = value.get("checks")
    if (
        not isinstance(checks, Mapping)
        or set(checks) != {
            "left_arm_fixed",
            "move_group_palm_exists",
            "exactly_two_finger_joints",
            "palm_is_common_finger_parent",
            "finger_children_exist",
            "fixed_gripper_links_exist",
            "fixed_links_disjoint_from_fingers",
            "palm_distinct_from_finger_and_fixed_links",
            "selected_signal_is_exactly_fingers_and_fixed_links",
            "palm_absent_from_selected_contact_signal",
            "selected_signal_nonempty",
        }
        or not all(item is True for item in checks.values())
        or value.get("pass") is not True
    ):
        raise ValueError("F2 gripper topology receipt checks are not all true")

    palm = _nonempty_name(
        value.get("move_group_palm_link_name"), label="receipt palm"
    )
    joints = _joint_topology(value.get("gripper_joint_topology", ()))
    articulation = set(
        _unique_names(
            value.get("articulation_link_names", ()),
            label="receipt articulation links",
        )
    )
    fixed = set(
        _unique_names(
            value.get("fixed_gripper_link_names", ()),
            label="receipt fixed gripper links",
        )
    )
    finger_children = {item["child_link_name"] for item in joints}
    selected = set(
        _unique_names(
            value.get("selected_contact_signal_link_names", ()),
            label="receipt selected signal links",
        )
    )
    additional = set(
        _unique_names(
            value.get("additional_allowed_gripper_assembly_body_names", ()),
            label="receipt additional assembly bodies",
        )
    )
    allowed = set(
        _unique_names(
            value.get("allowed_gripper_assembly_body_names", ()),
            label="receipt allowed assembly bodies",
        )
    )
    if (
        palm not in articulation
        or {item["parent_link_name"] for item in joints} != {palm}
        or not finger_children.issubset(articulation)
        or not fixed.issubset(articulation)
        or selected != finger_children | fixed
        or palm in selected
        or additional != {palm}
        or allowed != selected | {palm}
        or value.get("finger_child_link_names") != sorted(finger_children)
        or value.get("finger_contact_signal_remains_required") is not True
        or value.get("palm_contact_alone_satisfies_selected_contact") is not False
    ):
        raise ValueError("F2 gripper topology receipt semantic linkage mismatch")
    validated = dict(value)
    validated["receipt_sha256"] = receipt_hash
    return validated
