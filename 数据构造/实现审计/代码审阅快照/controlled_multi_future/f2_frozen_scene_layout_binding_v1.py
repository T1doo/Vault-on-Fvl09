"""Immutable F2 Stage-0 replacement binding for the intended v2 layout."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .current_hasher import hash_json
from .f2_mutually_exclusive_region_layout_v2 import LAYOUT as LEGACY_LAYOUT_V2


SCHEMA_VERSION = "cmf_f2_frozen_scene_layout_binding_v1"
LAYOUT_VERSION = str(LEGACY_LAYOUT_V2["layout_version"])
Q_WXYZ = [0.5, 0.5, 0.5, 0.5]


def _copy(value: Any) -> Any:
    return json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    )


def frozen_f2_scene_layout_v1() -> dict[str, Any]:
    """Return both role-explicit and legacy-consumer fields, byte-stably."""

    value = {
        "layout_version": LAYOUT_VERSION,
        "can_xyz": _copy(LEGACY_LAYOUT_V2["can_xyz"]),
        "box_xyz": _copy(LEGACY_LAYOUT_V2["box_xyz"]),
        "scale_xyz": _copy(LEGACY_LAYOUT_V2["scale_xyz"]),
        "stand_xyz": _copy(LEGACY_LAYOUT_V2["stand_xyz"]),
        "stand_q_wxyz": _copy(LEGACY_LAYOUT_V2["stand_q_wxyz"]),
        "main_object_pose": [*LEGACY_LAYOUT_V2["can_xyz"], *Q_WXYZ],
        "plastic_box_pose": [*LEGACY_LAYOUT_V2["box_xyz"], *Q_WXYZ],
        "electronic_scale_pose": [*LEGACY_LAYOUT_V2["scale_xyz"], *Q_WXYZ],
        "beside_reference_pose": [
            *LEGACY_LAYOUT_V2["stand_xyz"],
            *LEGACY_LAYOUT_V2["stand_q_wxyz"],
        ],
        "distractor_poses": {},
        "obstacle_pose": None,
    }
    return _copy(value)


def legacy_f2_layout_core(layout: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(layout, Mapping):
        raise ValueError("F2 scene layout must be a mapping")
    keys = (
        "layout_version",
        "can_xyz",
        "box_xyz",
        "scale_xyz",
        "stand_xyz",
        "stand_q_wxyz",
    )
    if any(key not in layout for key in keys):
        raise ValueError("F2 scene layout lacks legacy runner fields")
    return _copy({key: layout[key] for key in keys})


def build_f2_frozen_scene_layout_binding_v1() -> dict[str, Any]:
    layout = frozen_f2_scene_layout_v1()
    value = {
        "schema_version": SCHEMA_VERSION,
        "design_version": "controlled_multi_future_f1_f4_v1_2",
        "implementation_version": "controlled_multi_future_stage0_smoke_v1_2",
        "scene_layout_version": LAYOUT_VERSION,
        "scene_layout": layout,
        "layout_payload_sha256": hash_json(layout),
        "legacy_layout_core_sha256": hash_json(legacy_f2_layout_core(layout)),
        "object_modelnames": {
            "main_object": "071_can",
            "plastic_box": "062_plasticbox",
            "electronic_scale": "072_electronicscale",
            "beside_reference": "074_displaystand",
        },
        "object_model_ids": {
            "main_object": 1,
            "plastic_box": 2,
            "electronic_scale": 0,
            "beside_reference": 3,
        },
        "execution_arm": "left",
        "scene_seed": 20260829,
        "source_layout_module": "f2_mutually_exclusive_region_layout_v2.LAYOUT",
        "scientific_programs_unchanged": True,
        "verifier_unchanged": True,
    }
    value["binding_sha256"] = hash_json(value)
    return value


def validate_f2_frozen_scene_layout_binding_v1(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("F2 frozen scene-layout binding is missing")
    result = _copy(value)
    digest = result.pop("binding_sha256", None)
    expected = build_f2_frozen_scene_layout_binding_v1()
    expected_digest = expected.pop("binding_sha256")
    if result != expected or digest != expected_digest or hash_json(result) != digest:
        raise ValueError("F2 frozen scene-layout binding changed")
    return {**result, "binding_sha256": digest}


__all__ = [
    "LAYOUT_VERSION",
    "build_f2_frozen_scene_layout_binding_v1",
    "frozen_f2_scene_layout_v1",
    "legacy_f2_layout_core",
    "validate_f2_frozen_scene_layout_binding_v1",
]
