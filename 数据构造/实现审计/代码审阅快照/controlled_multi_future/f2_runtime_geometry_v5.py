"""Runtime-true F2 geometry contract after real SAPIEN integration evidence."""

from __future__ import annotations

import json
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_inside_control_search_v2 import (
    ASSET_ROOT,
    GEOMETRY_POSITION_ATOL_M,
    build_f2_geometry_certificate_v4,
    capture_f2_runtime_geometry_observation_v4,
)


MAIN_ACTOR_ORIENTATION_ATOL_RAD = 0.005
STATIC_BOX_ORIENTATION_ATOL_RAD = 1.0e-6
RUN2_EVIDENCE_GATE_SHA256 = (
    "1a53d9c9b511f91477755ff98d763710f5a009127f75bdcec2b0d9b8c051258c"
)


def _model_geometry(modelname: str, model_id: int):
    path = ASSET_ROOT / modelname / f"model_data{int(model_id)}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scale = np.asarray(data["scale"], dtype=np.float64).reshape(-1)
    if scale.size == 1:
        scale = np.repeat(scale, 3)
    center = np.asarray(data["center"], dtype=np.float64) * scale
    dimensions = np.asarray(data["extents"], dtype=np.float64) * scale
    return {
        "center": center,
        "dimensions": dimensions,
        "lower": center - 0.5 * dimensions,
        "upper": center + 0.5 * dimensions,
    }


def build_f2_geometry_certificate_v5(
    *, main_object_model_id: int, plastic_box_model_id: int
) -> dict[str, Any]:
    old = build_f2_geometry_certificate_v4(
        main_object_model_id=main_object_model_id,
        plastic_box_model_id=plastic_box_model_id,
    )
    old.pop("certificate_sha256")
    main = _model_geometry("071_can", main_object_model_id)
    box = _model_geometry("062_plasticbox", plastic_box_model_id)
    for prefix, geometry in (("main_object", main), ("plastic_box", box)):
        old[f"{prefix}_local_lower_m"] = geometry["lower"].tolist()
        old[f"{prefix}_local_upper_m"] = geometry["upper"].tolist()
        old[f"{prefix}_local_center_m"] = geometry["center"].tolist()
        old[f"{prefix}_local_dimensions_m"] = geometry["dimensions"].tolist()
    old.update(
        {
            "schema_version": "cmf_f2_geometry_certificate_v5",
            "source_of_truth": (
                "model_data center/extents multiplied by runtime scale; "
                "confirmed against real SAPIEN actor local bounds"
            ),
            "supersedes_v4_runtime_mismatch_receipt_sha256": RUN2_EVIDENCE_GATE_SHA256,
            "dynamic_actor_spawn_orientation_is_physical_equivalence_not_asset_geometry": True,
            "main_actor_orientation_atol_rad": MAIN_ACTOR_ORIENTATION_ATOL_RAD,
            "static_box_orientation_atol_rad": STATIC_BOX_ORIENTATION_ATOL_RAD,
        }
    )
    old["certificate_sha256"] = canonical_hash_json(old)
    return old


def capture_f2_runtime_geometry_observation_v5(scene) -> dict[str, Any]:
    value = capture_f2_runtime_geometry_observation_v4(scene)
    value["schema_version"] = "cmf_f2_runtime_geometry_observation_v5"
    value.pop("runtime_observation_sha256", None)
    value["runtime_observation_sha256"] = canonical_hash_json(value)
    return value


def compare_f2_runtime_geometry_v5(
    certificate: Mapping[str, Any], runtime_observation: Mapping[str, Any]
) -> dict[str, Any]:
    cert = canonical_jsonable(certificate)
    payload = dict(cert)
    digest = payload.pop("certificate_sha256", None)
    if (
        cert.get("schema_version") != "cmf_f2_geometry_certificate_v5"
        or digest != canonical_hash_json(payload)
    ):
        raise ValueError("F2 V5 geometry certificate is invalid")
    runtime = canonical_jsonable(runtime_observation)
    vector_fields = (
        "main_object_scale",
        "plastic_box_scale",
        "main_object_local_lower_m",
        "main_object_local_upper_m",
        "main_object_local_center_m",
        "main_object_local_dimensions_m",
        "plastic_box_local_lower_m",
        "plastic_box_local_upper_m",
        "plastic_box_local_center_m",
        "plastic_box_local_dimensions_m",
        "cavity_raw_lower_m",
        "cavity_raw_upper_m",
        "cavity_center_m",
    )
    errors = {
        field: float(
            np.max(
                np.abs(
                    np.asarray(runtime[field], dtype=np.float64)
                    - np.asarray(cert[field], dtype=np.float64)
                )
            )
        )
        for field in vector_fields
    }
    main_orientation_error = quaternion_angular_error(
        runtime["main_object_spawn_orientation_wxyz"],
        cert["main_object_spawn_orientation_wxyz"],
    )
    box_orientation_error = quaternion_angular_error(
        runtime["plastic_box_spawn_orientation_wxyz"],
        cert["plastic_box_spawn_orientation_wxyz"],
    )
    checks = {
        "model_ids_match": runtime.get("main_object_model_id")
        == cert["main_object_model_id"]
        and runtime.get("plastic_box_model_id")
        == cert["plastic_box_model_id"],
        "collision_paths_match": runtime.get("main_object_collision_path")
        == cert["main_object_collision_path"]
        and runtime.get("plastic_box_collision_path")
        == cert["plastic_box_collision_path"],
        "asset_hashes_match": all(
            runtime.get(field) == cert[field]
            for field in (
                "main_object_model_data_sha256",
                "plastic_box_model_data_sha256",
                "main_object_collision_sha256",
                "plastic_box_collision_sha256",
            )
        ),
        "runtime_true_geometry_vectors_match_1um": all(
            value <= GEOMETRY_POSITION_ATOL_M for value in errors.values()
        ),
        "dynamic_main_orientation_within_5mrad": main_orientation_error
        <= MAIN_ACTOR_ORIENTATION_ATOL_RAD,
        "static_box_orientation_within_1urad": box_orientation_error
        <= STATIC_BOX_ORIENTATION_ATOL_RAD,
    }
    result = {
        "schema_version": "cmf_f2_runtime_geometry_comparison_v5",
        "certificate_sha256": digest,
        "runtime_observation_sha256": runtime.get("runtime_observation_sha256"),
        "maximum_absolute_errors_m": errors,
        "geometry_position_atol_m": GEOMETRY_POSITION_ATOL_M,
        "main_actor_orientation_error_rad": main_orientation_error,
        "main_actor_orientation_atol_rad": MAIN_ACTOR_ORIENTATION_ATOL_RAD,
        "static_box_orientation_error_rad": box_orientation_error,
        "static_box_orientation_atol_rad": STATIC_BOX_ORIENTATION_ATOL_RAD,
        "checks": checks,
        "status": "PASS"
        if all(checks.values())
        else "F2_RUNTIME_TRUE_GEOMETRY_MISMATCH",
        "pass": all(checks.values()),
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    return result


__all__ = [
    "MAIN_ACTOR_ORIENTATION_ATOL_RAD",
    "STATIC_BOX_ORIENTATION_ATOL_RAD",
    "build_f2_geometry_certificate_v5",
    "capture_f2_runtime_geometry_observation_v5",
    "compare_f2_runtime_geometry_v5",
]
