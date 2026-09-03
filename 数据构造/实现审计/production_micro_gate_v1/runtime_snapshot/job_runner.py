#!/usr/bin/env python3
"""Manifest-bound F2/F3/F4 physical micro-qualification family runner."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import traceback


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def load_manifest(path: Path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("unified manifest self-hash mismatch")
    if value.get("approved") is not True:
        raise PermissionError("micro qualification is not approved")
    if file_sha(Path(value["runner_script_path"])) != value["runner_script_sha256"]:
        raise RuntimeError("runner script hash mismatch")
    return value


def save_trace(scene, path: Path):
    receipt = dict(scene.save_trace(path))
    receipt["sha256"] = file_sha(path)
    return receipt


def with_hash(value, key="receipt_sha256"):
    result = dict(value)
    result[key] = canonical_hash(result)
    return result


def assert_runtime_environment(job):
    uuid = os.environ.get("CUDA_VISIBLE_DEVICES")
    physical = os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX")
    if not uuid or physical is None:
        raise PermissionError("child lacks UUID-bound Guard environment")
    if os.environ.get("LD_LIBRARY_PATH"):
        raise RuntimeError("child inherited forbidden LD_LIBRARY_PATH")
    if os.environ.get("CUDA_HOME") != "/nfs_share/lijunhui/Robotwin2/tools/cuda-12.1":
        raise RuntimeError("child CUDA_HOME differs from project contract")
    return {"gpu_uuid": uuid, "physical_gpu_index": int(physical)}


@contextmanager
def opened_scene(adapter, legacy_scene_spec, *, phase, program, family):
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import (
        _PinnedSapienRenderDeviceContextV1,
    )

    context = adapter.scene(legacy_scene_spec, phase=phase, program=program)
    if family in {"F2", "F3"}:
        context = _PinnedSapienRenderDeviceContextV1(context)
    with context as handle:
        yield handle.scene, context


def adapter_for(family, legacy_scene_spec, output_root, source_sha):
    from controlled_multi_future.real_sapien_adapter_high_level_v1 import (
        RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
        RoboTwinRealSapienF3AssetGraspV2Adapter,
        RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
    )

    cls = {
        "F2": RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
        "F3": RoboTwinRealSapienF3AssetGraspV2Adapter,
        "F4": RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
    }[family]
    return cls(
        output_root=Path(output_root),
        expected_implementation_source_sha256=source_sha,
        planned_spec=legacy_scene_spec,
    )


def record_physical_scene(
    *,
    family,
    adapter,
    legacy_scene_spec,
    output,
    trace_actor_name,
    arm,
    execute,
    phase,
    program=None,
):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    current = anchor = video = trace = result = error = None
    cleanup = None
    with opened_scene(
        adapter,
        legacy_scene_spec,
        phase=phase,
        program=program,
        family=family,
    ) as (scene, context):
        try:
            current = adapter.capture_current(scene)
            anchor = adapter.capture_anchor(scene)
            actor = getattr(scene, trace_actor_name)
            scene.initialize_trace(actor, arm, role_actors=scene.role_actors)
            scene.start_development_video_capture(output / "trajectory.mp4")
            result = execute(scene)
        except BaseException as exc:
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        finally:
            if hasattr(scene, "trace") and scene.trace:
                try:
                    trace = save_trace(scene, output / "physical_trace.npz")
                except BaseException as exc:
                    error = error or {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    }
            try:
                video = scene.finish_development_video_capture(
                    terminal_status="pass" if error is None else "failed"
                )
            except BaseException as exc:
                error = error or {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
    cleanup = context.cleanup_receipt
    receipt = with_hash(
        {
            "schema_version": "cmf_production_micro_physical_scene_receipt_v1",
            "family": family,
            "phase": phase,
            "program": program,
            "current": current,
            "anchor": anchor,
            "result": result,
            "error": error,
            "trace": trace,
            "video": video,
            "cleanup": cleanup,
            "pass": error is None and isinstance(result, dict),
        }
    )
    write_new(output / "scene_receipt.json", receipt)
    return receipt


def run_f2(job, output, source_sha):
    from controlled_multi_future.f2_controlled_insertion_physical_v2 import (
        build_f2_controlled_insertion_physical_spec_v2,
        run_f2_controlled_insertion_physical_v2,
    )
    from controlled_multi_future.f2_hierarchical_template_search_v1 import (
        build_f2_hierarchical_template_search_v1,
    )
    from controlled_multi_future.f2_planner_integration_v2 import (
        run_f2_final_grasp_stage_a_planner_v2,
    )
    from controlled_multi_future.f2_recovery_planner_manifest_v1 import (
        build_f2_recovery_planner_manifest_v1,
        build_f2_recovery_stage_a_spec_v1,
    )
    from controlled_multi_future.high_level_runtime_specs_v1 import (
        build_f2_runtime_spec_v1,
    )

    panel = build_f2_recovery_planner_manifest_v1()
    search = build_f2_hierarchical_template_search_v1()
    rows = []
    last_failure = None
    repeated_failure = 0
    success_count = 0
    physical_count = 0
    for index, frozen in enumerate(job["candidates"], start=1):
        if repeated_failure >= 2 or success_count >= 2:
            break
        candidate_dir = output / f"candidate_{index:02d}_{frozen['pair_id']}_{frozen['arm']}"
        candidate_dir.mkdir(parents=True, exist_ok=False)
        entry = next(
            item
            for item in panel["ordered_recipes"]
            if item["pair_id"] == frozen["pair_id"]
            and item["recipe"]["arm"] == frozen["arm"]
            and item["recipe"]["official_contact_point_id"]
            == frozen["contact_point_id"]
            and item["recipe"]["official_rotation_candidate_index"]
            == frozen["rotation_index"]
        )
        stage_a_spec = build_f2_recovery_stage_a_spec_v1(
            panel,
            entry,
            slot_id=f"{job['job_id']}-stage-a-{index}",
            planner_reset_nonce=int(job["planner_reset_nonce_base"]) + index,
        )
        recipe = stage_a_spec["recipe"]
        scene_candidate = next(
            item
            for item in search["inside_candidates"]
            if item["main_object_model_id"] == recipe["main_object_model_id"]
            and item["plastic_box_model_id"] == recipe["plastic_box_model_id"]
            and item["arm"] == recipe["arm"]
        )
        stage_a_scene_spec = build_f2_runtime_spec_v1(
            scene_candidate["candidate_id"], purpose="f2_stage_a_planner"
        )
        stage_a_adapter = adapter_for(
            "F2", stage_a_scene_spec, candidate_dir / "stage_a_scene", source_sha
        )
        stage_a_error = None
        with opened_scene(
            stage_a_adapter,
            stage_a_scene_spec,
            phase="F2_MICRO_STAGE_A",
            program=None,
            family="F2",
        ) as (scene, context):
            try:
                stage_a = run_f2_final_grasp_stage_a_planner_v2(scene, stage_a_spec)
            except BaseException as exc:
                stage_a = None
                stage_a_error = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
        write_new(candidate_dir / "stage_a_spec.json", stage_a_spec)
        stage_a_cleanup = context.cleanup_receipt
        write_new(
            candidate_dir / "stage_a_terminal.json",
            {
                "terminal": stage_a,
                "error": stage_a_error,
                "cleanup": stage_a_cleanup,
            },
        )
        if not isinstance(stage_a, dict) or stage_a.get(
            "planner_qualified_for_physical_probe"
        ) is not True:
            failure = "STAGE_A_PLANNER_OR_BINDING_FAILED"
            rows.append(
                {
                    "candidate": frozen,
                    "planner_pass": False,
                    "physical_attempted": False,
                    "failure_category": failure,
                }
            )
        else:
            physical_spec = build_f2_controlled_insertion_physical_spec_v2(
                stage_a_spec,
                stage_a,
                slot_id=f"{job['job_id']}-physical-{index}",
                planner_reset_nonce=int(job["physical_reset_nonce_base"]) + index,
            )
            write_new(candidate_dir / "physical_spec.json", physical_spec)
            physical_adapter = adapter_for(
                "F2",
                physical_spec["legacy_scene_spec"],
                candidate_dir / "physical_scene",
                source_sha,
            )
            scene_receipt = record_physical_scene(
                family="F2",
                adapter=physical_adapter,
                legacy_scene_spec=physical_spec["legacy_scene_spec"],
                output=candidate_dir / "physical",
                trace_actor_name="can",
                arm=physical_spec["arm"],
                execute=lambda scene, spec=physical_spec: run_f2_controlled_insertion_physical_v2(
                    scene, spec
                ),
                phase="F2_CONTROLLED_INSERTION_PHYSICAL",
            )
            physical_count += 1
            terminal = scene_receipt.get("result") or {}
            passed = terminal.get("physically_qualified") is True
            failure = (
                None
                if passed
                else terminal.get("physical_result", {}).get("earliest_failure")
                or (scene_receipt.get("error") or {}).get("type")
                or "F2_PHYSICAL_GATE_FAILED"
            )
            rows.append(
                {
                    "candidate": frozen,
                    "planner_pass": True,
                    "physical_attempted": True,
                    "physical_pass": passed,
                    "failure_category": failure,
                    "scene_receipt_sha256": scene_receipt["receipt_sha256"],
                }
            )
            if passed:
                success_count += 1
        current_failure = rows[-1].get("failure_category")
        if current_failure is not None and current_failure == last_failure:
            repeated_failure += 1
        elif current_failure is not None:
            repeated_failure = 1
        else:
            repeated_failure = 0
        last_failure = current_failure
    return {
        "family": "F2",
        "rows": rows,
        "planner_pass_count": sum(
            row.get("planner_pass") is True for row in rows
        ),
        "planner_gate_pass": bool(rows)
        and all(row.get("planner_pass") is True for row in rows),
        "physical_execution_count": physical_count,
        "physical_success_count": success_count,
        "stopped_after_same_failure_twice": repeated_failure >= 2,
        "template_qualification_pass": success_count >= 2,
    }


def prepare_f3_scene(scene, adapter, recipe, expected_binding):
    from controlled_multi_future.f3_scene_binding_equivalence_v1 import (
        audit_f3_scene_binding_equivalence_v1,
    )
    from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a import (
        _derive_actual_f3_binding,
        _entity_sleep_state,
        _f3_contact_state,
    )
    from controlled_multi_future.family_runners_v3_1 import _pose

    actual = _derive_actual_f3_binding(scene, recipe)
    entities = adapter._entity_payloads(scene)
    receipt = audit_f3_scene_binding_equivalence_v1(
        recipe=recipe,
        expected_scene_binding=expected_binding,
        actual_scene_binding=actual,
        actual_bottle_pose=_pose(scene.bottle).tolist(),
        actual_pad_pose=_pose(scene.pad).tolist(),
        actual_marker_pose=_pose(scene.central_marker).tolist(),
        scene_seed=int(scene._cmf_setup_kwargs["seed"]),
        scene_instance_id=scene._cmf_scene_instance_id,
        canonical_settle_steps=int(scene._cmf_canonical_settle_steps),
        actor_sleep_state=_entity_sleep_state(scene.bottle),
        contact_state=_f3_contact_state(scene),
        runtime_asset=entities["bottle"],
        runtime_tuple=scene._cmf_f3_asset_grasp_tuple_v2,
    )
    if receipt["pass"] is not True:
        raise RuntimeError(
            "F3_ACTUAL_SCENE_BINDING_NOT_PHYSICALLY_EQUIVALENT"
        )
    scene._cmf_f3_scene_binding_v3_1 = expected_binding
    scene._cmf_f3_scene_binding_equivalence_v1 = receipt
    return receipt


def run_f3(job, output, source_sha):
    from controlled_multi_future.f3_asset_grasp_qualification_v2 import (
        build_f3_asset_grasp_qualification_v2,
    )
    from controlled_multi_future.f3_planner_integration_v3_1 import (
        build_f3_stage_a_planner_spec_v3_1,
        build_f3_stage_b_planner_spec_v3_1,
        run_f3_stage_a_planner_v3_1,
        run_f3_stage_b_planner_v3_1,
    )
    from controlled_multi_future.f3_shared_v_physical_v1 import (
        build_f3_shared_v_physical_spec_v1,
        run_f3_shared_v_physical_v1,
    )
    from controlled_multi_future.high_level_runtime_specs_v1 import (
        build_f3_runtime_spec_v1,
    )
    from controlled_multi_future.planner_qualification_manifests_v2_3 import (
        build_f3_stage_a_panel_manifest_v1,
        build_f3_stage_b_selection_policy_v1,
    )

    panel = build_f3_stage_a_panel_manifest_v1()
    policy = build_f3_stage_b_selection_policy_v1(panel)
    tuples = build_f3_asset_grasp_qualification_v2()["grasp_tuples"]
    rows = []
    physical_count = 0
    success_count = 0
    for index, frozen in enumerate(job["candidates"], start=1):
        entry = next(
            item
            for item in panel["ordered_recipes"]
            if item["stratum"]["asset_model_id"] == frozen["asset_model_id"]
            and item["stratum"]["arm"] == frozen["arm"]
            and item["stratum"]["region"] == frozen["region"]
            and item["contact_point_id"] == frozen["contact_point_id"]
            and item["rotation_index"] == frozen["rotation_index"]
        )
        candidate_dir = output / f"candidate_{index:02d}_bottle{frozen['asset_model_id']}_{frozen['arm']}_{frozen['region']}"
        candidate_dir.mkdir(parents=True, exist_ok=False)
        recipe = entry["recipe"]
        tuple_value = next(
            item
            for item in tuples
            if item["asset"] == recipe["asset"] and item["arm"] == recipe["arm"]
        )
        legacy_a = build_f3_runtime_spec_v1(
            tuple_value["tuple_id"], purpose="f3_level1_planner"
        )
        spec_a = build_f3_stage_a_planner_spec_v3_1(
            recipe,
            entry["scene_binding"],
            slot_id=f"{job['job_id']}-a-{index}",
            panel_sha256=panel["panel_sha256"],
            planner_reset_nonce=int(job["planner_reset_nonce_base"]) + 10 * index,
        )
        adapter_a = adapter_for("F3", legacy_a, candidate_dir / "scene_a", source_sha)
        error = None
        with opened_scene(adapter_a, legacy_a, phase="F3_STAGE_A", program=None, family="F3") as (scene, context):
            try:
                binding_a = prepare_f3_scene(scene, adapter_a, recipe, entry["scene_binding"])
                terminal_a = run_f3_stage_a_planner_v3_1(scene, spec_a)
            except BaseException as exc:
                binding_a = None
                terminal_a = None
                error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        cleanup_a = context.cleanup_receipt
        write_new(candidate_dir / "stage_a.json", {"spec": spec_a, "binding": binding_a, "terminal": terminal_a, "error": error, "cleanup": cleanup_a})
        if not isinstance(terminal_a, dict) or terminal_a.get("stage_a_pass") is not True:
            rows.append({"candidate": frozen, "planner_stage_a_pass": False, "physical_attempted": False, "failure_category": "F3_STAGE_A_PLANNER_OR_BINDING_FAILED"})
            continue
        spec_b = build_f3_stage_b_planner_spec_v3_1(
            terminal_a,
            spec_a,
            slot_id=f"{job['job_id']}-b-{index}",
            selection_policy_sha256=policy["policy_sha256"],
            planner_reset_nonce=int(job["planner_reset_nonce_base"]) + 10 * index + 1,
        )
        legacy_b = build_f3_runtime_spec_v1(
            tuple_value["tuple_id"], purpose="f3_level1_planner"
        )
        adapter_b = adapter_for("F3", legacy_b, candidate_dir / "scene_b", source_sha)
        error_b = None
        with opened_scene(adapter_b, legacy_b, phase="F3_STAGE_B", program=None, family="F3") as (scene, context):
            try:
                binding_b = prepare_f3_scene(scene, adapter_b, recipe, entry["scene_binding"])
                terminal_b = run_f3_stage_b_planner_v3_1(scene, spec_b)
            except BaseException as exc:
                binding_b = None
                terminal_b = None
                error_b = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        cleanup_b = context.cleanup_receipt
        write_new(candidate_dir / "stage_b.json", {"spec": spec_b, "binding": binding_b, "terminal": terminal_b, "error": error_b, "cleanup": cleanup_b})
        if not isinstance(terminal_b, dict) or terminal_b.get("stage_b_pass") is not True:
            rows.append({"candidate": frozen, "planner_stage_a_pass": True, "planner_stage_b_pass": False, "physical_attempted": False, "failure_category": "F3_STAGE_B_PLANNER_OR_BINDING_FAILED"})
            continue
        physical_spec = build_f3_shared_v_physical_spec_v1(
            spec_a,
            terminal_a,
            spec_b,
            terminal_b,
            slot_id=f"{job['job_id']}-physical-{index}",
            planner_reset_nonce=int(job["physical_reset_nonce_base"]) + index,
        )
        write_new(candidate_dir / "physical_spec.json", physical_spec)
        physical_adapter = adapter_for("F3", physical_spec["legacy_scene_spec"], candidate_dir / "physical_scene", source_sha)

        def execute(scene, spec=physical_spec, adapter=physical_adapter, recipe=recipe, expected=entry["scene_binding"]):
            prepare_f3_scene(scene, adapter, recipe, expected)
            return run_f3_shared_v_physical_v1(scene, spec)

        scene_receipt = record_physical_scene(
            family="F3",
            adapter=physical_adapter,
            legacy_scene_spec=physical_spec["legacy_scene_spec"],
            output=candidate_dir / "physical",
            trace_actor_name="bottle",
            arm=physical_spec["arm"],
            execute=execute,
            phase="F3_SHARED_V_PHYSICAL",
        )
        physical_count += 1
        terminal = scene_receipt.get("result") or {}
        physical = terminal.get("physical_result", {})
        gates = physical.get("gates", {})
        stage_a_gate_names = (
            "planner_success",
            "selected_gripper_contact_continuity",
            "bottle_off_support_after_lift",
            "grasp_transform_translation_stable",
            "grasp_transform_orientation_stable",
        )
        stage_b_gate_names = (
            "bottle_linear_stability",
            "bottle_angular_stability",
            "eef_tracking",
            "shared_v_realized_amplitude",
            "shared_v_closed_loop_return",
        )
        stage_a_physical = all(gates.get(name) is True for name in stage_a_gate_names)
        stage_b_loaded = all(gates.get(name) is True for name in stage_b_gate_names)
        passed = terminal.get("shared_v_physically_qualified") is True
        success_count += int(passed)
        failure = None if passed else (
            "F3_STAGE_A_STABLE_GRASP_LIFT_FAILED"
            if not stage_a_physical
            else "F3_STAGE_B_LOADED_V_RETURN_SETTLE_FAILED"
        )
        rows.append(
            {
                "candidate": frozen,
                "planner_stage_a_pass": True,
                "planner_stage_b_pass": True,
                "physical_attempted": True,
                "stage_a_stable_grasp_lift_pass": stage_a_physical,
                "stage_b_loaded_v_return_settle_pass": stage_b_loaded,
                "physical_pass": passed,
                "failure_category": failure,
                "scene_receipt_sha256": scene_receipt["receipt_sha256"],
            }
        )
    return {
        "family": "F3",
        "rows": rows,
        "planner_pass_count": sum(
            row.get("planner_stage_a_pass") is True
            and row.get("planner_stage_b_pass") is True
            for row in rows
        ),
        "planner_gate_pass": bool(rows)
        and all(
            row.get("planner_stage_a_pass") is True
            and row.get("planner_stage_b_pass") is True
            for row in rows
        ),
        "physical_execution_count": physical_count,
        "physical_success_count": success_count,
        "template_qualification_pass": success_count >= 2,
    }


def run_f4(job, output, source_sha):
    from controlled_multi_future.f4_bounded_physical_micro_v1 import (
        build_f4_bounded_physical_micro_spec_v1,
        run_f4_bounded_physical_micro_v1,
    )
    from controlled_multi_future.f4_program_planner_integration_v2 import (
        build_f4_program_planner_spec_v2,
        run_f4_program_planner_v2,
    )
    from controlled_multi_future.high_level_runtime_specs_v1 import (
        build_f4_runtime_spec_v1,
    )
    from controlled_multi_future.planner_qualification_manifests_v2_3 import (
        build_f4_program_panel_manifest_v1_1,
    )
    from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1 import (
        _f4_synthetic_stage_a_terminal,
    )

    panel = build_f4_program_panel_manifest_v1_1()
    source = panel["source_candidate"]
    candidate = panel["candidates"][0]
    program_info = {
        "F4-ABC": ("f4-abc", int(job["planner_reset_nonce_base"]) + 1),
        "F4-ACB": ("f4-acb", int(job["planner_reset_nonce_base"]) + 2),
        "F4-BAC": ("f4-bac", int(job["planner_reset_nonce_base"]) + 3),
    }
    planner_terminals = {}
    for program_id, (slot, nonce) in program_info.items():
        spec = build_f4_program_planner_spec_v2(
            source,
            candidate,
            program_id=program_id,
            slot_id=f"{slot}-planner-source",
            planner_reset_nonce=nonce,
        )
        legacy = build_f4_runtime_spec_v1(
            candidate["candidate_id"],
            purpose="f4_stage_b_planner",
            stage_a_terminal=_f4_synthetic_stage_a_terminal(),
        )
        planner_dir = output / "planner" / program_id
        adapter = adapter_for("F4", legacy, planner_dir / "scene", source_sha)
        error = None
        with opened_scene(adapter, legacy, phase="F4_PROGRAM_PLANNER", program=program_id, family="F4") as (scene, context):
            scene._cmf_scene_lifecycle = "fresh"
            try:
                terminal = run_f4_program_planner_v2(scene, spec)
            except BaseException as exc:
                terminal = None
                error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        planner_cleanup = context.cleanup_receipt
        write_new(planner_dir / "terminal.json", {"spec": spec, "terminal": terminal, "error": error, "cleanup": planner_cleanup})
        planner_terminals[program_id] = {"slot": slot, "nonce": nonce, "terminal": terminal, "pass": isinstance(terminal, dict) and terminal.get("robot_kinematic_table_world_planner_pass") is True}
    stages = ["A_ONLY", "B_ONLY", "C_ONLY", "AB_NONINTERFERENCE", "AC_NONINTERFERENCE"]
    rows = []
    physical_count = 0
    singles_pass = True
    for index, stage in enumerate(stages, start=1):
        if index > 3 and not singles_pass:
            rows.append({"stage": stage, "skipped": True, "reason": "singles_not_all_pass"})
            continue
        program_id = {
            "A_ONLY": "F4-ABC",
            "B_ONLY": "F4-BAC",
            "C_ONLY": "F4-ACB",
            "AB_NONINTERFERENCE": "F4-ABC",
            "AC_NONINTERFERENCE": "F4-ACB",
        }[stage]
        source_planner = planner_terminals[program_id]
        if not source_planner["pass"]:
            rows.append({"stage": stage, "skipped": True, "reason": "required_program_planner_failed"})
            if index <= 3:
                singles_pass = False
            continue
        physical_spec = build_f4_bounded_physical_micro_spec_v1(
            source,
            candidate,
            source_planner["terminal"],
            stage=stage,
            slot_id=source_planner["slot"],
            planner_reset_nonce=source_planner["nonce"],
        )
        stage_dir = output / "physical" / f"{index:02d}_{stage}"
        write_new(stage_dir / "physical_spec.json", physical_spec)
        adapter = adapter_for("F4", physical_spec["legacy_scene_spec"], stage_dir / "scene", source_sha)
        scene_receipt = record_physical_scene(
            family="F4",
            adapter=adapter,
            legacy_scene_spec=physical_spec["legacy_scene_spec"],
            output=stage_dir / "execution",
            trace_actor_name="common_x",
            arm=physical_spec["f4_source_grasp_candidate_v1"]["arm"],
            execute=lambda scene, spec=physical_spec, adapter=adapter: run_f4_bounded_physical_micro_v1(
                scene, spec, capture_anchor_callback=adapter.capture_anchor
            ),
            phase="F4_BOUNDED_PHYSICAL_MICRO",
            program=program_id,
        )
        physical_count += 1
        terminal = scene_receipt.get("result") or {}
        passed = terminal.get("stage_physically_qualified") is True
        if index <= 3 and not passed:
            singles_pass = False
        rows.append(
            {
                "stage": stage,
                "program_id": program_id,
                "planner_pass": True,
                "physical_attempted": True,
                "physical_pass": passed,
                "failure_category": None
                if passed
                else terminal.get("physical_result", {}).get("earliest_failure")
                or (scene_receipt.get("error") or {}).get("type")
                or "F4_PHYSICAL_ISOLATION_GATE_FAILED",
                "scene_receipt_sha256": scene_receipt["receipt_sha256"],
            }
        )
    all_five = len([row for row in rows if row.get("physical_pass") is True]) == 5
    return {
        "family": "F4",
        "planner_programs": planner_terminals,
        "planner_pass_count": sum(
            item["pass"] is True for item in planner_terminals.values()
        ),
        "planner_gate_pass": all(
            item["pass"] is True for item in planner_terminals.values()
        ),
        "rows": rows,
        "physical_execution_count": physical_count,
        "physical_isolation_gate_pass": all_five,
        "full_program_pass": False,
        "template_qualification_pass": False,
        "next_required_gate": "ABC_ACB_BAC_real_physical_programs"
        if all_five
        else "repair_failed_primitive_or_noninterference",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args(argv)
    manifest = load_manifest(args.manifest)
    jobs = {item["job_id"]: item for item in manifest["jobs"]}
    if args.job_id not in jobs:
        raise ValueError("job is outside unified manifest")
    job = jobs[args.job_id]
    environment = assert_runtime_environment(job)
    output = Path(job["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    from controlled_multi_future.runtime_source_lock_v1 import _hash_python_tree

    live_source = _hash_python_tree(PROJECT / "controlled_multi_future")
    if live_source != manifest["implementation_source_sha256"]:
        raise RuntimeError("active controlled source differs from frozen Phase A")
    started = {
        "schema_version": "cmf_production_micro_gate_job_start_v1",
        "run_id": manifest["run_id"],
        "job_id": job["job_id"],
        "family": job["family"],
        "manifest_sha256": manifest["manifest_sha256"],
        "environment": environment,
        "implementation_source_sha256": live_source,
    }
    write_new(output / "job_start.json", with_hash(started))
    error = None
    result = None
    try:
        if job["family"] == "F2":
            result = run_f2(job, output, live_source)
        elif job["family"] == "F3":
            result = run_f3(job, output, live_source)
        elif job["family"] == "F4":
            result = run_f4(job, output, live_source)
        else:
            raise ValueError("unsupported family job")
    except BaseException as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    terminal = {
        "schema_version": "cmf_production_micro_gate_job_terminal_v1",
        "run_id": manifest["run_id"],
        "job_id": job["job_id"],
        "family": job["family"],
        "manifest_sha256": manifest["manifest_sha256"],
        "cpu_contract_pass": True,
        "result": result,
        "error": error,
        "planner_pass": bool(result) and result.get("planner_gate_pass") is True,
        "physical_primitive_pass": bool(result)
        and bool(
            result.get("physical_success_count", 0) > 0
            or result.get("physical_isolation_gate_pass") is True
        ),
        "template_qualification_pass": bool(result)
        and result.get("template_qualification_pass") is True,
        "full_program_pass": bool(result)
        and result.get("full_program_pass") is True,
        "accepted_trajectory_count": 0,
        "formal_data": False,
        "training_data": False,
        "pass": error is None,
    }
    write_new(output / "job_terminal.json", with_hash(terminal))
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
