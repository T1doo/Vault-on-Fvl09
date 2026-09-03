"""Production scene bridges for V2.3.1 planner wiring smoke jobs."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_hierarchical_template_search_v1 import build_f2_hierarchical_template_search_v1
from .f2_planner_integration_v2 import (
    build_f2_final_grasp_stage_a_spec_v2,
    run_f2_final_grasp_stage_a_planner_v2,
)
from .f3_asset_grasp_qualification_v2 import build_f3_asset_grasp_qualification_v2
from .f3_planner_integration_v3_1 import (
    build_f3_stage_a_planner_spec_v3_1,
    build_f3_stage_b_planner_spec_v3_1,
    run_f3_stage_a_planner_v3_1,
    run_f3_stage_b_planner_v3_1,
)
from .f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    select_f4_stage_a_source_v1,
)
from .f4_program_planner_integration_v2 import (
    build_f4_program_planner_spec_v2,
    run_f4_program_planner_v2,
)
from .family_runners_v3_1 import _pose
from .high_level_runtime_specs_v1 import (
    build_f2_runtime_spec_v1,
    build_f3_runtime_spec_v1,
    build_f4_runtime_spec_v1,
)
from .planner_qualification_manifests_v2_3 import (
    build_f3_scene_binding_from_values_v1,
)
from .real_sapien_adapter_high_level_v1 import (
    RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
    RoboTwinRealSapienF3AssetGraspV2Adapter,
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
)


RUNNER_SYMBOLS = {
    "F2_STAGE_A": "controlled_multi_future.f2_planner_integration_v2.run_f2_final_grasp_stage_a_planner_v2",
    "F3_STAGE_A": "controlled_multi_future.f3_planner_integration_v3_1.run_f3_stage_a_planner_v3_1",
    "F3_STAGE_B": "controlled_multi_future.f3_planner_integration_v3_1.run_f3_stage_b_planner_v3_1",
    "F4_PROGRAM": "controlled_multi_future.f4_program_planner_integration_v2.run_f4_program_planner_v2",
}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workspace_file(value: Any, label: str) -> Path:
    path = Path(str(value)).resolve()
    if not str(path).startswith("/nfs_share/lijunhui/") or not path.is_file():
        raise ValueError(f"{label} is not one immutable workspace file")
    return path


def load_f3_stage_b_dependency_registry_v1(
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    value = canonical_jsonable(registry)
    payload = dict(value)
    digest = payload.pop("registry_sha256", None)
    required = {
        "schema_version", "stage_a_spec_path", "stage_a_spec_file_sha256",
        "stage_a_spec_sha256", "stage_a_terminal_path",
        "stage_a_terminal_file_sha256", "stage_a_terminal_receipt_sha256",
        "stage_a_terminal_qpos_sha256", "scene_binding_sha256",
    }
    if (
        set(payload) != required
        or value.get("schema_version") != "cmf_f3_stage_b_dependency_registry_v1"
        or digest != canonical_hash_json(payload)
    ):
        raise ValueError("F3 Stage-B dependency registry schema/hash mismatch")
    spec_path = _workspace_file(value["stage_a_spec_path"], "F3 Stage-A spec")
    terminal_path = _workspace_file(
        value["stage_a_terminal_path"], "F3 Stage-A terminal"
    )
    if (
        _file_sha(spec_path) != value["stage_a_spec_file_sha256"]
        or _file_sha(terminal_path) != value["stage_a_terminal_file_sha256"]
    ):
        raise ValueError("F3 Stage-B dependency file SHA mismatch")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    if (
        spec.get("spec_sha256") != value["stage_a_spec_sha256"]
        or terminal.get("receipt_sha256")
        != value["stage_a_terminal_receipt_sha256"]
        or terminal.get("stage_a_terminal_qpos_sha256")
        != value["stage_a_terminal_qpos_sha256"]
        or canonical_hash_json(terminal.get("scene_binding"))
        != value["scene_binding_sha256"]
    ):
        raise ValueError("F3 Stage-B dependency content binding mismatch")
    return {"registry": value, "stage_a_spec": spec, "stage_a_terminal": terminal}


def build_f3_stage_b_dependency_registry_v1(
    *, stage_a_spec_path: Path, stage_a_terminal_path: Path
) -> dict[str, Any]:
    spec_path = _workspace_file(stage_a_spec_path, "F3 Stage-A spec")
    terminal_path = _workspace_file(stage_a_terminal_path, "F3 Stage-A terminal")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    value = {
        "schema_version": "cmf_f3_stage_b_dependency_registry_v1",
        "stage_a_spec_path": str(spec_path),
        "stage_a_spec_file_sha256": _file_sha(spec_path),
        "stage_a_spec_sha256": spec["spec_sha256"],
        "stage_a_terminal_path": str(terminal_path),
        "stage_a_terminal_file_sha256": _file_sha(terminal_path),
        "stage_a_terminal_receipt_sha256": terminal["receipt_sha256"],
        "stage_a_terminal_qpos_sha256": terminal["stage_a_terminal_qpos_sha256"],
        "scene_binding_sha256": canonical_hash_json(terminal["scene_binding"]),
    }
    value["registry_sha256"] = canonical_hash_json(value)
    return value


def build_f3_stage_b_dependency_registry_v1_1(
    *,
    stage_a_spec_path: Path,
    stage_a_terminal_path: Path,
    actual_scene_seed: int,
    stage_a_scene_instance_id: str,
) -> dict[str, Any]:
    base = build_f3_stage_b_dependency_registry_v1(
        stage_a_spec_path=stage_a_spec_path,
        stage_a_terminal_path=stage_a_terminal_path,
    )
    terminal = json.loads(
        Path(base["stage_a_terminal_path"]).read_text(encoding="utf-8")
    )
    if (
        not isinstance(stage_a_scene_instance_id, str)
        or not stage_a_scene_instance_id
        or terminal.get("scene_instance_id") != stage_a_scene_instance_id
    ):
        raise ValueError("F3 Stage-B registry scene instance mismatch")
    value = {
        **{key: item for key, item in base.items() if key != "registry_sha256"},
        "schema_version": "cmf_f3_stage_b_dependency_registry_v1_1",
        "actual_scene_seed": int(actual_scene_seed),
        "stage_a_scene_instance_id": stage_a_scene_instance_id,
    }
    value["registry_sha256"] = canonical_hash_json(value)
    return value


def load_f3_stage_b_dependency_registry_v1_1(
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    value = canonical_jsonable(registry)
    payload = dict(value)
    digest = payload.pop("registry_sha256", None)
    if (
        value.get("schema_version")
        != "cmf_f3_stage_b_dependency_registry_v1_1"
        or digest != canonical_hash_json(payload)
        or not isinstance(value.get("actual_scene_seed"), int)
        or not isinstance(value.get("stage_a_scene_instance_id"), str)
        or not value["stage_a_scene_instance_id"]
    ):
        raise ValueError("F3 Stage-B V1.1 dependency registry mismatch")
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
    loaded = load_f3_stage_b_dependency_registry_v1(legacy)
    if (
        loaded["stage_a_terminal"].get("scene_instance_id")
        != value["stage_a_scene_instance_id"]
    ):
        raise ValueError("F3 Stage-B V1.1 registry terminal scene mismatch")
    return {**loaded, "registry": value}


def _f4_synthetic_stage_a_terminal():
    contract = build_f4_hierarchical_template_search_v1()
    gates = contract["stage_a_required_gates"]
    return select_f4_stage_a_source_v1(
        contract,
        [
            {
                "candidate_id": item["candidate_id"],
                "candidate_sha256": item["candidate_sha256"],
                "checks": {gate: item["rank"] == 1 for gate in gates},
                "cleanup_safety_pass": True,
                "orphan_process_count": 0,
            }
            for item in contract["stage_a_candidates"]
        ],
    )


def build_production_scene_bridge_plan_v2_3_1(
    authorization: Mapping[str, Any],
) -> dict[str, Any]:
    auth = canonical_jsonable(authorization)
    job_kind = auth["job_kind"]
    job = auth["job_spec"]
    if auth.get("runner_symbol") != RUNNER_SYMBOLS.get(job_kind):
        raise ValueError("V2.3.1 runner symbol differs from production resolution")
    entry = job["manifest_entry"]
    nonce = int(job["planner_reset_nonce"])
    if job_kind == "F2_STAGE_A":
        recipe = entry["recipe"]
        search = build_f2_hierarchical_template_search_v1()
        candidate = next(
            item
            for item in search["inside_candidates"]
            if item["main_object_model_id"]
            == recipe["main_object_model_id"]
            and item["plastic_box_model_id"]
            == recipe["plastic_box_model_id"]
            and item["arm"] == recipe["arm"]
        )
        legacy = build_f2_runtime_spec_v1(
            candidate["candidate_id"], purpose="f2_stage_a_planner"
        )
        pair_id = (
            f"can{recipe['main_object_model_id']}-"
            f"box{recipe['plastic_box_model_id']}"
        )
        context = job["manifest_context"]
        certificate = (
            context["certificates_by_pair"][pair_id]
            if "certificates_by_pair" in context
            else context["certificate"]
        )
        binding = (
            context["bindings_by_pair_and_arm"][pair_id][recipe["arm"]]
            if "bindings_by_pair_and_arm" in context
            else context["bindings_by_arm"][recipe["arm"]]
        )
        runner_spec = build_f2_final_grasp_stage_a_spec_v2(
            recipe,
            certificate,
            binding,
            slot_id=job["job_id"],
            panel_sha256=job["manifest_sha256"],
            planner_reset_nonce=nonce,
        )
        adapter_kind = "F2"
    elif job_kind in {"F3_STAGE_A", "F3_STAGE_B"}:
        recipe = entry["recipe"]
        grasp = build_f3_asset_grasp_qualification_v2()
        tuple_value = next(
            item
            for item in grasp["grasp_tuples"]
            if item["asset"]["model_id"] == recipe["asset"]["model_id"]
            and item["arm"] == recipe["arm"]
        )
        legacy = build_f3_runtime_spec_v1(
            tuple_value["tuple_id"], purpose="f3_level1_planner"
        )
        if job_kind == "F3_STAGE_A":
            runner_spec = build_f3_stage_a_planner_spec_v3_1(
                recipe,
                entry["scene_binding"],
                slot_id=job["job_id"],
                panel_sha256=job["manifest_sha256"],
                planner_reset_nonce=nonce,
            )
        else:
            dependency = load_f3_stage_b_dependency_registry_v1(
                job["dependency_registry"]
            )
            runner_spec = build_f3_stage_b_planner_spec_v3_1(
                dependency["stage_a_terminal"],
                dependency["stage_a_spec"],
                slot_id=job["job_id"],
                selection_policy_sha256=job["manifest_sha256"],
                planner_reset_nonce=nonce,
            )
        adapter_kind = "F3"
    elif job_kind == "F4_PROGRAM":
        source = job["manifest_context"]["source_candidate"]
        candidate = job["manifest_context"]["candidate"]
        stage_a = _f4_synthetic_stage_a_terminal()
        legacy = build_f4_runtime_spec_v1(
            candidate["candidate_id"],
            purpose="f4_stage_b_planner",
            stage_a_terminal=stage_a,
        )
        runner_spec = build_f4_program_planner_spec_v2(
            source,
            candidate,
            program_id=entry["program_id"],
            slot_id=job["job_id"],
            planner_reset_nonce=nonce,
        )
        adapter_kind = "F4"
    else:
        raise ValueError("V2.3.1 scene bridge job kind is unsupported")
    value = {
        "schema_version": "cmf_production_scene_bridge_plan_v2_3_1",
        "job_kind": job_kind,
        "adapter_kind": adapter_kind,
        "legacy_scene_spec": legacy,
        "legacy_scene_spec_sha256": legacy["planned_scope_spec_sha256"],
        "runner_spec": runner_spec,
        "runner_spec_sha256": runner_spec["spec_sha256"],
        "runner_symbol": RUNNER_SYMBOLS[job_kind],
        "planner_reset_nonce": nonce,
        "motiongen_reset_seed_argument": True,
        "numeric_rng_seed_application_proven": False,
        "bitwise_determinism_claimed": False,
    }
    value["bridge_plan_sha256"] = canonical_hash_json(value)
    return value


def derive_actual_f3_scene_binding_v2_3_1(scene, recipe: Mapping[str, Any]):
    return build_f3_scene_binding_from_values_v1(
        recipe,
        bottle_pose=_pose(scene.bottle).tolist(),
        original_pad_pose=_pose(scene.pad).tolist(),
        central_marker_pose=_pose(scene.central_marker).tolist(),
    )


def run_with_production_scene_bridge_v2_3_1(
    authorization: Mapping[str, Any], *, output_root: Path
) -> dict[str, Any]:
    plan = build_production_scene_bridge_plan_v2_3_1(authorization)
    auth = canonical_jsonable(authorization)
    adapter_class = {
        "F2": RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
        "F3": RoboTwinRealSapienF3AssetGraspV2Adapter,
        "F4": RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
    }[plan["adapter_kind"]]
    adapter = adapter_class(
        output_root=Path(output_root),
        expected_implementation_source_sha256=auth["implementation_source_sha256"],
        planned_spec=plan["legacy_scene_spec"],
    )
    context = adapter.scene(
        plan["legacy_scene_spec"],
        phase=auth["job_kind"],
        program=auth["job_spec"]["manifest_entry"].get("program_id"),
    )
    terminal = None
    with context as handle:
        scene = handle.scene
        scene._cmf_scene_lifecycle = (
            "reconstructed" if auth["job_kind"] == "F3_STAGE_B" else "fresh"
        )
        if plan["adapter_kind"] == "F3":
            recipe = auth["job_spec"]["manifest_entry"]["recipe"]
            actual = derive_actual_f3_scene_binding_v2_3_1(scene, recipe)
            expected = auth["job_spec"]["manifest_entry"]["scene_binding"]
            receipt = {
                "schema_version": "cmf_f3_actual_scene_binding_receipt_v2_3_1",
                "expected_scene_binding": expected,
                "actual_scene_binding": actual,
                "actual_derived_from_runtime_scene": True,
                "expected_fields_copied_as_actual": False,
                "pass": actual == expected,
            }
            receipt["receipt_sha256"] = canonical_hash_json(receipt)
            if receipt["pass"] is not True:
                raise ValueError("F3 actual scene binding differs from manifest")
            scene._cmf_f3_scene_binding_v3_1 = actual
        if auth["job_kind"] == "F2_STAGE_A":
            terminal = run_f2_final_grasp_stage_a_planner_v2(
                scene, plan["runner_spec"]
            )
        elif auth["job_kind"] == "F3_STAGE_A":
            terminal = run_f3_stage_a_planner_v3_1(scene, plan["runner_spec"])
        elif auth["job_kind"] == "F3_STAGE_B":
            terminal = run_f3_stage_b_planner_v3_1(scene, plan["runner_spec"])
        else:
            terminal = run_f4_program_planner_v2(scene, plan["runner_spec"])
    cleanup = context.cleanup_receipt
    if not isinstance(cleanup, Mapping) or cleanup.get("cleanup_safety_pass") is not True:
        raise RuntimeError("V2.3.1 production scene cleanup is uncertain")
    return {
        "bridge_plan": plan,
        "terminal": terminal,
        "cleanup": canonical_jsonable(cleanup),
    }


__all__ = [
    "RUNNER_SYMBOLS",
    "build_f3_stage_b_dependency_registry_v1",
    "build_production_scene_bridge_plan_v2_3_1",
    "derive_actual_f3_scene_binding_v2_3_1",
    "load_f3_stage_b_dependency_registry_v1",
    "run_with_production_scene_bridge_v2_3_1",
]
