"""Pre-smoke exact bridge envelopes and production scene validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_planner_integration_v2 import run_f2_final_grasp_stage_a_planner_v2
from .f3_scene_binding_equivalence_v1_1 import (
    audit_f3_scene_binding_equivalence_v1_1,
)
from .f3_planner_integration_v3_1 import (
    run_f3_stage_a_planner_v3_1,
    run_f3_stage_b_planner_v3_1,
)
from .f4_program_planner_integration_v2 import run_f4_program_planner_v2
from .family_runners_v3_1 import _pose
from .planner_qualification_scene_bridges_v2_3_1 import (
    RUNNER_SYMBOLS,
    build_production_scene_bridge_plan_v2_3_1,
    load_f3_stage_b_dependency_registry_v1_1,
)
from .real_sapien_adapter_high_level_v1 import (
    RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
    RoboTwinRealSapienF3AssetGraspV2Adapter,
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
)


class F3ActualSceneBindingMismatch(RuntimeError):
    failure_class = "INFRASTRUCTURE_ERROR"
    failure_code = "F3_ACTUAL_SCENE_BINDING_MISMATCH"

    def __init__(self, evidence: Mapping[str, Any]):
        self.evidence = canonical_jsonable(evidence)
        super().__init__("F3 actual scene binding differs from manifest")


class _AttachCleanupToExceptionContext:
    def __init__(self, inner):
        self.inner = inner
        self.entered = False

    @property
    def cleanup_receipt(self):
        return self.inner.cleanup_receipt

    def __enter__(self):
        value = self.inner.__enter__()
        self.entered = True
        return value

    def __exit__(self, exc_type, exc, tb):
        result = self.inner.__exit__(exc_type, exc, tb)
        if exc is not None:
            exc.cleanup_receipt = canonical_jsonable(
                self.inner.cleanup_receipt or {}
            )
            exc.scene_count = 1 if self.entered else 0
        return result


def _compatibility_registry_v1(registry_v1_1: Mapping[str, Any]):
    value = canonical_jsonable(registry_v1_1)
    legacy = {
        key: item
        for key, item in value.items()
        if key
        not in {
            "registry_sha256",
            "actual_scene_seed",
            "stage_a_scene_instance_id",
        }
    }
    legacy["schema_version"] = "cmf_f3_stage_b_dependency_registry_v1"
    legacy["registry_sha256"] = canonical_hash_json(legacy)
    return legacy


def prepare_exact_job_bridge_envelope_v2_3_1a(
    *,
    job_kind: str,
    job_id: str,
    manifest_entry: Mapping[str, Any],
    manifest_context: Mapping[str, Any],
    manifest_sha256: str,
    planner_reset_nonce: int,
    dependency_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if job_kind not in RUNNER_SYMBOLS:
        raise ValueError("unsupported V2.3.1a bridge job kind")
    dependency_v1_1 = None
    dependency_for_builder = canonical_jsonable(dependency_registry)
    if job_kind == "F3_STAGE_B":
        dependency_v1_1 = load_f3_stage_b_dependency_registry_v1_1(
            dependency_registry
        )
        dependency_for_builder = _compatibility_registry_v1(
            dependency_v1_1["registry"]
        )
    elif dependency_registry is not None:
        raise ValueError("only F3 Stage-B may carry a dependency registry")
    provisional_job = {
        "job_id": str(job_id),
        "manifest_entry": canonical_jsonable(manifest_entry),
        "manifest_context": canonical_jsonable(manifest_context),
        "manifest_sha256": str(manifest_sha256),
        "planner_reset_nonce": int(planner_reset_nonce),
        "dependency_registry": dependency_for_builder,
    }
    plan = build_production_scene_bridge_plan_v2_3_1(
        {
            "job_kind": job_kind,
            "runner_symbol": RUNNER_SYMBOLS[job_kind],
            "job_spec": provisional_job,
        }
    )
    actual_seed = int(plan["legacy_scene_spec"]["seed"])
    if (
        dependency_v1_1 is not None
        and dependency_v1_1["registry"]["actual_scene_seed"] != actual_seed
    ):
        raise ValueError("F3 Stage-B scene seed differs from Stage A")
    bindings = {
        "legacy_scene_spec_sha256": plan["legacy_scene_spec_sha256"],
        "runner_spec_sha256": plan["runner_spec_sha256"],
        "scene_layout_sha256": plan["legacy_scene_spec"].get(
            "scene_layout_sha256"
        ),
        "f2_asset_layout_binding_sha256": plan["legacy_scene_spec"].get(
            "f2_asset_layout_binding_sha256"
        ),
        "f3_expected_scene_binding": (
            provisional_job["manifest_entry"].get("scene_binding")
            if job_kind in {"F3_STAGE_A", "F3_STAGE_B"}
            else None
        ),
    }
    value = {
        "schema_version": "cmf_exact_job_bridge_envelope_v2_3_1a",
        "job_kind": job_kind,
        "job_id": str(job_id),
        "runner_symbol": RUNNER_SYMBOLS[job_kind],
        "legacy_scene_spec": plan["legacy_scene_spec"],
        "legacy_scene_spec_sha256": plan["legacy_scene_spec_sha256"],
        "runner_spec": plan["runner_spec"],
        "runner_spec_sha256": plan["runner_spec_sha256"],
        "actual_scene_seed": actual_seed,
        "scene_and_spec_bindings": bindings,
        "planner_reset_nonce": int(planner_reset_nonce),
        "motiongen_reset_seed_argument": True,
        "reset_receipt_bound_to_authorization": True,
        "numeric_rng_seed_application_proven": False,
        "bitwise_determinism_claimed": False,
    }
    value["bridge_envelope_sha256"] = canonical_hash_json(value)
    return value


def validate_exact_job_bridge_envelope_v2_3_1a(
    value: Mapping[str, Any], *, authorization: Mapping[str, Any]
) -> dict[str, Any]:
    envelope = canonical_jsonable(value)
    payload = dict(envelope)
    digest = payload.pop("bridge_envelope_sha256", None)
    job = authorization["job_spec"]
    if (
        envelope.get("schema_version")
        != "cmf_exact_job_bridge_envelope_v2_3_1a"
        or digest != canonical_hash_json(payload)
        or envelope.get("job_kind") != authorization.get("job_kind")
        or envelope.get("job_id") != job.get("job_id")
        or envelope.get("runner_symbol") != authorization.get("runner_symbol")
        or envelope.get("actual_scene_seed") != authorization.get("scene_seed")
        or envelope.get("actual_scene_seed") != job.get("scene_seed")
        or envelope.get("planner_reset_nonce")
        != job.get("planner_reset_nonce")
        or envelope.get("legacy_scene_spec", {}).get("seed")
        != envelope.get("actual_scene_seed")
        or envelope.get("motiongen_reset_seed_argument") is not True
        or envelope.get("numeric_rng_seed_application_proven") is not False
        or envelope.get("bitwise_determinism_claimed") is not False
    ):
        raise ValueError("V2.3.1a exact bridge envelope binding mismatch")
    return envelope


def _derive_actual_f3_binding(scene, recipe):
    from .planner_qualification_manifests_v2_3 import (
        build_f3_scene_binding_from_values_v1,
    )

    return build_f3_scene_binding_from_values_v1(
        recipe,
        bottle_pose=_pose(scene.bottle).tolist(),
        original_pad_pose=_pose(scene.pad).tolist(),
        central_marker_pose=_pose(scene.central_marker).tolist(),
    )


def _entity_sleep_state(entity):
    components = (
        entity.get_components() if hasattr(entity, "get_components") else []
    )
    for component in components:
        value = getattr(component, "is_sleeping", None)
        if value is not None:
            value = value() if callable(value) else value
            if isinstance(value, (bool, np.bool_)):
                return bool(value)
    return None


def _f3_contact_state(scene):
    result = {"bottle_table_contact": False, "bottle_pad_contact": False}
    get_contacts = getattr(getattr(scene, "scene", None), "get_contacts", None)
    if not callable(get_contacts):
        return {**result, "contact_api_available": False}
    for contact in get_contacts():
        names = {
            str(getattr(getattr(body, "entity", None), "name", "")).lower()
            for body in getattr(contact, "bodies", [])
        }
        if not any("bottle" in name for name in names):
            continue
        result["bottle_table_contact"] |= any("table" in name for name in names)
        result["bottle_pad_contact"] |= any("pad" in name for name in names)
    return {**result, "contact_api_available": True}


def _f3_binding_mismatch_evidence(scene, recipe, expected, actual, seed):
    source_x = -0.18 if recipe["arm"] == "left" else 0.18
    expected_bottle = [source_x, -0.06, 0.785, 0.0, 0.0, 1.0, 0.0]
    expected_pad = [source_x, -0.06, 0.745, 1.0, 0.0, 0.0, 0.0]
    expected_marker = [0.0, -0.05, 0.95, 1.0, 0.0, 0.0, 0.0]
    actual_bottle = _pose(scene.bottle).tolist()
    actual_pad = _pose(scene.pad).tolist()
    actual_marker = _pose(scene.central_marker).tolist()
    delta = [actual_bottle[index] - expected_bottle[index] for index in range(3)]
    evidence = {
        "schema_version": "cmf_f3_scene_binding_mismatch_evidence_v1",
        "asset_model_id": recipe["asset"]["model_id"],
        "scene_seed": int(seed),
        "scene_instance_id": getattr(scene, "_cmf_scene_instance_id", None),
        "canonical_settle_steps": int(
            getattr(scene, "_cmf_canonical_settle_steps", -1)
        ),
        "expected_bottle_pose": expected_bottle,
        "actual_bottle_pose": actual_bottle,
        "position_delta_xyz": delta,
        "position_error_m": float(np.linalg.norm(delta)),
        "orientation_error_rad": float(
            quaternion_angular_error(actual_bottle[3:], expected_bottle[3:])
        ),
        "expected_pad_pose": expected_pad,
        "actual_pad_pose": actual_pad,
        "expected_marker_pose": expected_marker,
        "actual_marker_pose": actual_marker,
        "actor_sleep_state": _entity_sleep_state(scene.bottle),
        "table_pad_contact_state": _f3_contact_state(scene),
        "expected_scene_binding": expected,
        "actual_scene_binding": actual,
        "failure_class": "INFRASTRUCTURE_ERROR",
        "failure_code": "F3_ACTUAL_SCENE_BINDING_MISMATCH",
    }
    evidence["receipt_sha256"] = canonical_hash_json(evidence)
    return evidence


def run_with_production_scene_bridge_v2_3_1a(
    authorization: Mapping[str, Any], *, output_root: Path
) -> dict[str, Any]:
    auth = canonical_jsonable(authorization)
    envelope = validate_exact_job_bridge_envelope_v2_3_1a(
        auth["job_spec"]["bridge_envelope"], authorization=auth
    )
    plan = {
        "schema_version": "cmf_production_scene_bridge_plan_v2_3_1a",
        "job_kind": auth["job_kind"],
        "adapter_kind": auth["family"],
        "legacy_scene_spec": envelope["legacy_scene_spec"],
        "legacy_scene_spec_sha256": envelope["legacy_scene_spec_sha256"],
        "runner_spec": envelope["runner_spec"],
        "runner_spec_sha256": envelope["runner_spec_sha256"],
        "runner_symbol": envelope["runner_symbol"],
        "planner_reset_nonce": envelope["planner_reset_nonce"],
        "actual_scene_seed": envelope["actual_scene_seed"],
    }
    plan["bridge_plan_sha256"] = canonical_hash_json(plan)
    adapter_class = {
        "F2": RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
        "F3": RoboTwinRealSapienF3AssetGraspV2Adapter,
        "F4": RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
    }[plan["adapter_kind"]]
    adapter = adapter_class(
        output_root=Path(output_root),
        expected_implementation_source_sha256=auth[
            "implementation_source_sha256"
        ],
        planned_spec=plan["legacy_scene_spec"],
    )
    context = _AttachCleanupToExceptionContext(
        adapter.scene(
            plan["legacy_scene_spec"],
            phase=auth["job_kind"],
            program=auth["job_spec"]["manifest_entry"].get("program_id"),
        )
    )
    terminal = None
    f3_scene_binding_equivalence = None
    with context as handle:
        scene = handle.scene
        setup_seed = int(getattr(scene, "_cmf_setup_kwargs", {}).get("seed", -1))
        if setup_seed != auth["scene_seed"]:
            raise RuntimeError("actual SAPIEN setup seed differs from authorization")
        scene._cmf_scene_lifecycle = (
            "reconstructed" if auth["job_kind"] == "F3_STAGE_B" else "fresh"
        )
        if plan["adapter_kind"] == "F3":
            recipe = auth["job_spec"]["manifest_entry"]["recipe"]
            actual = _derive_actual_f3_binding(scene, recipe)
            expected = auth["job_spec"]["manifest_entry"]["scene_binding"]
            runtime_entities = adapter._entity_payloads(scene)
            f3_scene_binding_equivalence = audit_f3_scene_binding_equivalence_v1_1(
                recipe=recipe,
                expected_scene_binding=expected,
                actual_scene_binding=actual,
                actual_bottle_pose=_pose(scene.bottle).tolist(),
                actual_pad_pose=_pose(scene.pad).tolist(),
                actual_marker_pose=_pose(scene.central_marker).tolist(),
                scene_seed=auth["scene_seed"],
                scene_instance_id=getattr(scene, "_cmf_scene_instance_id", None),
                canonical_settle_steps=int(
                    getattr(scene, "_cmf_canonical_settle_steps", -1)
                ),
                actor_sleep_state=_entity_sleep_state(scene.bottle),
                contact_state=_f3_contact_state(scene),
                runtime_asset=runtime_entities.get("bottle"),
                runtime_tuple=getattr(scene, "_cmf_f3_asset_grasp_tuple_v2", None),
            )
            if f3_scene_binding_equivalence["pass"] is not True:
                raise F3ActualSceneBindingMismatch(
                    f3_scene_binding_equivalence
                )
            # Planner specs bind the deterministic nominal scene identity.  The
            # dynamic post-settle pose is retained separately in the bridge
            # receipt and must never replace that identity hash.
            scene._cmf_f3_scene_binding_v3_1 = expected
            scene._cmf_f3_scene_binding_equivalence_v1 = (
                f3_scene_binding_equivalence
            )
        if auth["job_kind"] == "F2_STAGE_A":
            terminal = run_f2_final_grasp_stage_a_planner_v2(
                scene, plan["runner_spec"]
            )
        elif auth["job_kind"] == "F3_STAGE_A":
            terminal = run_f3_stage_a_planner_v3_1(scene, plan["runner_spec"])
        elif auth["job_kind"] == "F3_STAGE_B":
            prior_scene = auth["job_spec"]["dependency_registry"][
                "stage_a_scene_instance_id"
            ]
            if getattr(scene, "_cmf_scene_instance_id", None) == prior_scene:
                raise RuntimeError("F3 Stage-B reused Stage-A scene instance")
            terminal = run_f3_stage_b_planner_v3_1(scene, plan["runner_spec"])
        else:
            terminal = run_f4_program_planner_v2(scene, plan["runner_spec"])
    cleanup = context.cleanup_receipt
    if not isinstance(cleanup, Mapping) or cleanup.get("cleanup_safety_pass") is not True:
        raise RuntimeError("V2.3.1a production scene cleanup is uncertain")
    return {
        "bridge_plan": plan,
        "terminal": terminal,
        "f3_scene_binding_equivalence": f3_scene_binding_equivalence,
        "cleanup": canonical_jsonable(cleanup),
    }


__all__ = [
    "F3ActualSceneBindingMismatch",
    "prepare_exact_job_bridge_envelope_v2_3_1a",
    "run_with_production_scene_bridge_v2_3_1a",
    "validate_exact_job_bridge_envelope_v2_3_1a",
]
