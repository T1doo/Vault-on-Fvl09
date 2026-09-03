#!/usr/bin/env python3
"""Approved F2 11-query controlled-insertion planner-only Gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import traceback

import numpy as np


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
BASE_HELPER = WORKSPACE / "Robotwin2/production_micro_gate_v1/job_runner.py"
BASE_HELPER_SHA256 = "376ddfbe07b1c9ae3e6e3b2d1975344a8605c6e81e49f27e92241c88a851a1d4"
EXPECTED_SOURCE = "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
EXPECTED_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_STATUS = "APPROVED_F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1"
EXPECTED_JOB_ID = "f2-controlled-insertion-route-gate-run1"
EXPECTED_DECISION_SHA256 = "85023b5726611f6ed1b30365fae096c84e97c3973e1fab1bb2000d5251c540f4"
EXPECTED_BINDING_SHA256 = "985515944a97b59621067e662b2e33614ebc08c772de74659c01a1c8ae559f0d"
EXPECTED_RECIPE_ID = "f2-final-grasp-v2-r000725"
EXPECTED_RECIPE_SHA256 = "f7270daf416afb1b84e230be7dd2418ac0e5a31d2461943da3bd77c6777cfe5e"
EXPECTED_PREFIX_QPOS_SHA256 = "8d4cb7b0571c0ba740e0406b32d4041f0dc73f48b0879a4b91567e8445f477b9"

SEALED_ROOT = (
    WORKSPACE
    / "Robotwin2/datasets/controlled_multi_future_f2_top_contact_root_v1"
    / "f2-top-contact-development-rpc-root-v1-run1/root"
)
SEALED_PLANNED_SPEC = SEALED_ROOT / "planned_root_slot_spec.json"
SEALED_PLANNED_SPEC_SHA256 = "a08e699b8e77e48588d5fe930e8eaa27ed88e5f445f8725a0990b4cc8f703659"
SEALED_BOUNDARY = (
    SEALED_ROOT / "suffix_preflight/F2-inside/preflight_boundary_receipt.json"
)
SEALED_BOUNDARY_SHA256 = "87431d38bd5e79e155dce09db6fbf1bdac93496435df8772981b27ff3210f3a0"
SEALED_TRACE = SEALED_ROOT / "canonical_prefix_reference_trace.npz"
SEALED_TRACE_SHA256 = "6e031c3caaab0b0c928551c8574fd9fe71ed4661bd34813363de3554c0a7bddf"
SEALED_INSIDE_EVIDENCE = (
    SEALED_ROOT / "suffix_preflight/F2-inside/controller_partial_evidence.json"
)
SEALED_INSIDE_EVIDENCE_SHA256 = "b6c0a009c144d165ebb49b88e396934079495a04a3ce7b81cfa651fe1935a14b"
SEALED_BESIDE_EVIDENCE = (
    SEALED_ROOT / "suffix_preflight/F2-beside/controller_partial_evidence.json"
)
SEALED_BESIDE_EVIDENCE_SHA256 = "2b170587406e8a3bad6b45245a27c042f299fc3d7b3addf6c1b523b61b5d170b"

INSIDE_SEGMENTS = (
    "inside_controlled_high_carry",
    "f2_v2_preinsert_30mm",
    "f2_v2_controlled_descend_to_support",
    "f2_v2_retreat_to_preinsert",
    "f2_v2_neutral",
)
BESIDE_SEGMENTS = (
    "beside_asset_bound_carry_hub",
    "beside_asset_bound_preplace",
    "beside_asset_bound_release",
    "beside_asset_bound_retreat",
    "beside_asset_bound_carry_hub_return",
    "f2_rest",
)


def canonical_hash(value) -> str:
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


def python_tree_sha(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_base():
    if file_sha(BASE_HELPER) != BASE_HELPER_SHA256:
        raise RuntimeError("sealed F2 helper runner changed")
    spec = importlib.util.spec_from_file_location(
        "cmf_f2_route_gate_base_helper", BASE_HELPER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed F2 helper runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base()


def workspace_path(value, label, *, must_file=False):
    path = Path(str(value)).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise ValueError(f"{label} is outside workspace")
    if must_file and not path.is_file():
        raise ValueError(f"{label} is missing")
    return path


def _file_binding(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha(path) != expected:
        raise ValueError(f"sealed F2 {label} changed")


def _self_hashed(value, key, label):
    payload = dict(value)
    digest = payload.pop(key, None)
    if digest != canonical_hash(payload):
        raise ValueError(f"sealed F2 {label} self-hash mismatch")


def _quaternion_error(first, second) -> float:
    a = np.asarray(first, dtype=np.float64).reshape(4)
    b = np.asarray(second, dtype=np.float64).reshape(4)
    a /= np.linalg.norm(a)
    b /= np.linalg.norm(b)
    return float(2.0 * np.arccos(np.clip(abs(np.dot(a, b)), -1.0, 1.0)))


def load_sealed_contract():
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    from controlled_multi_future.family_runners_v3_1 import hash_array
    from controlled_multi_future.geometry import (
        actor_target_to_eef_pose,
        pose_matrix,
        relative_pose,
        world_axis_offset_pose,
    )
    from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
        validate_frozen_asset_layout_binding_v3,
    )

    for path, expected, label in (
        (SEALED_PLANNED_SPEC, SEALED_PLANNED_SPEC_SHA256, "planned root spec"),
        (SEALED_BOUNDARY, SEALED_BOUNDARY_SHA256, "prefix boundary"),
        (SEALED_TRACE, SEALED_TRACE_SHA256, "canonical prefix trace"),
        (SEALED_INSIDE_EVIDENCE, SEALED_INSIDE_EVIDENCE_SHA256, "inside evidence"),
        (SEALED_BESIDE_EVIDENCE, SEALED_BESIDE_EVIDENCE_SHA256, "beside evidence"),
    ):
        _file_binding(path, expected, label)

    planned = json.loads(SEALED_PLANNED_SPEC.read_text(encoding="utf-8"))
    _self_hashed(planned, "planned_root_slot_spec_sha256", "planned root spec")
    binding = validate_frozen_asset_layout_binding_v3(
        planned["f2_asset_layout_binding_v3"]
    )
    selected = canonical_jsonable(planned["selected_top_contact_candidate"])
    exact_candidate = {
        "main_object_model_id": 0,
        "plastic_box_model_id": 2,
        "arm": "left",
        "official_contact_point_id": 8,
        "official_rotation_candidate_index": 0,
        "recipe_id": EXPECTED_RECIPE_ID,
    }
    if (
        binding["binding_sha256"] != EXPECTED_BINDING_SHA256
        or binding["selected_candidate_key"]["main_object_model_id"] != 0
        or binding["selected_candidate_key"]["plastic_box_model_id"] != 2
        or binding["selected_execution_arm"] != "left"
        or any(selected.get(key) != value for key, value in exact_candidate.items())
        or selected.get("recipe_sha256") != EXPECTED_RECIPE_SHA256
    ):
        raise ValueError("sealed F2 selected binding/candidate changed")

    boundary = json.loads(SEALED_BOUNDARY.read_text(encoding="utf-8"))
    _self_hashed(boundary, "boundary_receipt_sha256", "prefix boundary")
    replay = boundary["prefix_replay"]
    qpos = np.asarray(replay["actual_prefix_end_qpos"], dtype=np.float64)
    if (
        qpos.shape != (38,)
        or replay["actual_prefix_end_qpos_sha256"] != EXPECTED_PREFIX_QPOS_SHA256
        or hash_array(qpos) != EXPECTED_PREFIX_QPOS_SHA256
        or boundary.get("same_current_pass") is not True
        or boundary.get("replayed_prefix_physical_acceptance", {}).get("pass") is not True
    ):
        raise ValueError("sealed F2 actual prefix-end qpos/evidence changed")

    with np.load(SEALED_TRACE, allow_pickle=False) as trace:
        if not np.array_equal(qpos, trace["joint_qpos"][-1]):
            raise ValueError("sealed qpos differs from canonical trace terminal")
        eef = np.asarray(trace["eef_pose"][-1], dtype=np.float64)
        actor = np.asarray(trace["role_object_pose__main_can"][-1], dtype=np.float64)
    actual_transform = relative_pose(eef, actor)

    inside_evidence = json.loads(
        SEALED_INSIDE_EVIDENCE.read_text(encoding="utf-8")
    )
    _self_hashed(inside_evidence, "receipt_sha256", "inside controller evidence")
    inside_extra = inside_evidence["extra"]
    if (
        inside_evidence["actual_prefix_end_qpos_sha256"]
        != EXPECTED_PREFIX_QPOS_SHA256
        or inside_extra["selected_binding_sha256"] != EXPECTED_BINDING_SHA256
        or inside_extra["inside_gravity_drop_route"]["audit"]["pass"] is not True
    ):
        raise ValueError("sealed F2 inside evidence binding changed")
    target_actor = np.asarray(
        inside_extra["inside_gravity_drop_route"]["target_actor_pose"],
        dtype=np.float64,
    )
    neutral = np.asarray(
        inside_extra["inside_gravity_drop_route"]["targets"][-1]["pose"],
        dtype=np.float64,
    )

    beside_evidence = json.loads(
        SEALED_BESIDE_EVIDENCE.read_text(encoding="utf-8")
    )
    _self_hashed(beside_evidence, "receipt_sha256", "beside controller evidence")
    beside_template_actor = np.asarray(
        beside_evidence["extra"]["asset_bound_beside_route"]["target_actor_pose"],
        dtype=np.float64,
    )
    candidate_xy = np.asarray(
        binding["layout_payload"]["beside_candidate_xy_m"][2], dtype=np.float64
    )
    if not np.array_equal(candidate_xy, np.asarray([0.08000000000000002, 0.07])):
        raise ValueError("F2 frozen beside layout candidate index 2 changed")
    stand_xy = np.asarray(
        binding["layout_payload"]["facility_pose_xyz"]["beside_reference"][:2],
        dtype=np.float64,
    )
    radial = float(np.linalg.norm(candidate_xy - stand_xy))
    if not 0.12 <= radial <= 0.23:
        raise ValueError("F2 beside index 2 left the frozen annulus")

    box_pose = np.asarray(
        [
            *binding["layout_payload"]["facility_pose_xyz"]["plastic_box"],
            *binding["layout_payload"]["facility_orientation_wxyz"]["plastic_box"],
        ],
        dtype=np.float64,
    )
    opening_normal = pose_matrix(box_pose)[:3, :3] @ np.asarray(
        [0.0, 1.0, 0.0], dtype=np.float64
    )
    opening_normal /= np.linalg.norm(opening_normal)
    supported = actor_target_to_eef_pose(eef, actor, target_actor)
    preinsert = supported.copy()
    preinsert[:3] += 0.030 * opening_normal
    high_carry = preinsert.copy()
    high_carry[2] = max(float(eef[2]), float(preinsert[2]))
    inside_targets = [
        {"segment_id": INSIDE_SEGMENTS[0], "pose": high_carry.tolist()},
        {"segment_id": INSIDE_SEGMENTS[1], "pose": preinsert.tolist()},
        {"segment_id": INSIDE_SEGMENTS[2], "pose": supported.tolist()},
        {"segment_id": INSIDE_SEGMENTS[3], "pose": preinsert.tolist()},
        {"segment_id": INSIDE_SEGMENTS[4], "pose": neutral.tolist()},
    ]

    beside_actor = beside_template_actor.copy()
    beside_actor[:2] = candidate_xy
    release = actor_target_to_eef_pose(eef, actor, beside_actor)
    preplace = world_axis_offset_pose(release, 0.08)
    hub = preplace.copy()
    hub[:2] = (eef[:2] + preplace[:2]) / 2.0
    hub[2] = max(float(eef[2]), float(preplace[2]))
    beside_targets = [
        {"segment_id": BESIDE_SEGMENTS[0], "pose": hub.tolist()},
        {"segment_id": BESIDE_SEGMENTS[1], "pose": preplace.tolist()},
        {"segment_id": BESIDE_SEGMENTS[2], "pose": release.tolist()},
        {"segment_id": BESIDE_SEGMENTS[3], "pose": preplace.tolist()},
        {"segment_id": BESIDE_SEGMENTS[4], "pose": hub.tolist()},
        {"segment_id": BESIDE_SEGMENTS[5], "pose": neutral.tolist()},
    ]
    return {
        "planned": planned,
        "binding": binding,
        "selected": selected,
        "actual_prefix_end_qpos": qpos,
        "actual_prefix_end_qpos_sha256": EXPECTED_PREFIX_QPOS_SHA256,
        "sealed_prefix_end_eef_pose": eef,
        "sealed_prefix_end_actor_pose": actor,
        "sealed_actual_eef_to_actor_transform": actual_transform,
        "frozen_strict_cavity_target_actor_pose": target_actor,
        "opening_normal_world": opening_normal,
        "neutral_eef_pose": neutral,
        "beside_template_actor_pose": beside_template_actor,
        "inside_targets": inside_targets,
        "beside_targets": beside_targets,
        "inside_targets_sha256": canonical_hash(inside_targets),
        "beside_targets_sha256": canonical_hash(beside_targets),
        "beside_candidate_index": 2,
        "beside_candidate_xy_m": candidate_xy.tolist(),
        "beside_radial_distance_m": radial,
    }


def load_manifest(path: Path, job_id: str, *, phase: str):
    manifest_path = workspace_path(path, "manifest", must_file=True)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("F2 route-Gate manifest self-hash mismatch")
    if value.get("status") != EXPECTED_STATUS or value.get("approved") is not True:
        raise PermissionError("F2 route-Gate manifest is not approved")
    if (
        value.get("gpu_execution_authorized") is not True
        or value.get("planner_execution_authorized") is not True
        or value.get("physical_execution_authorized") is not False
    ):
        raise PermissionError("F2 route-Gate execution scope changed")
    if (
        value.get("implementation_source_sha256") != EXPECTED_SOURCE
        or python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_SOURCE
    ):
        raise ValueError("F2 controlled source differs from freeze")
    head = subprocess.run(
        ["git", "-C", str(PROJECT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "-C", str(PROJECT), "status", "--porcelain", "--untracked-files=no"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    if value.get("robotwin_tracked_head") != EXPECTED_HEAD or head != EXPECTED_HEAD or tracked:
        raise ValueError("official RoboTwin tracked source changed")
    if (
        value.get("allowed_physical_gpu_indices") != list(range(8))
        or value.get("one_job_per_gpu") is not True
        or value.get("root_sharding") is not False
    ):
        raise ValueError("F2 GPU scheduling contract changed")
    for key in (
        "stage0_reopened",
        "stage1_authorized",
        "formal_360_authorized",
        "training_authorized",
        "h_reveal_authorized",
        "compression_authorized",
        "pi05_authorized",
        "formal_data",
    ):
        if value.get(key) is not False:
            raise ValueError(f"forbidden F2 stage enabled: {key}")
    for path_key, sha_key in (
        ("runner_script_path", "runner_script_sha256"),
        ("guard_script_path", "guard_script_sha256"),
        ("external_review_decision_path", "external_review_decision_file_sha256"),
        ("sealed_planned_spec_path", "sealed_planned_spec_file_sha256"),
        ("sealed_boundary_path", "sealed_boundary_file_sha256"),
        ("sealed_trace_path", "sealed_trace_file_sha256"),
        ("sealed_inside_evidence_path", "sealed_inside_evidence_file_sha256"),
        ("sealed_beside_evidence_path", "sealed_beside_evidence_file_sha256"),
    ):
        bound = workspace_path(value[path_key], path_key, must_file=True)
        if file_sha(bound) != value[sha_key]:
            raise ValueError(f"F2 bound file hash changed: {path_key}")
    if value["external_review_decision_file_sha256"] != EXPECTED_DECISION_SHA256:
        raise ValueError("F2 external decision binding changed")
    assets = value.get("asset_hashes_by_family", {}).get("F2", {})
    if not assets:
        raise ValueError("F2 asset map missing")
    for relative, expected in assets.items():
        if file_sha(PROJECT / relative) != expected:
            raise ValueError(f"F2 asset changed: {relative}")
    jobs = value.get("jobs")
    if (
        not isinstance(jobs, list)
        or len(jobs) != 1
        or jobs[0].get("job_id") != job_id
        or job_id != EXPECTED_JOB_ID
    ):
        raise ValueError("F2 exact job lookup failed")
    job = jobs[0]
    exact = {
        "family": "F2",
        "mode": "F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1",
        "planner_query_cap": 11,
        "fresh_planner_scene_cap": 2,
        "physical_execution_cap": 0,
        "branch_execution_cap": 0,
        "raw_trajectory_cap": 0,
        "video_cap": 0,
        "accepted_root_cap": 0,
        "formal_trajectory_cap": 0,
        "inside_planner_query_cap": 5,
        "beside_planner_query_cap": 6,
        "beside_frozen_layout_candidate_index": 2,
    }
    if any(job.get(key) != expected for key, expected in exact.items()):
        raise ValueError("F2 reviewed job/caps changed")
    if (
        job.get("automatic_retry") is not False
        or job.get("fallback_allowed") is not False
        or job.get("target_search_allowed") is not False
        or job.get("root_retry_allowed") is not False
        or job.get("automatic_continuation") is not False
        or job.get("primary_10cm_gravity_drop") is not False
        or job.get("open_gripper_during_gate") is not False
    ):
        raise ValueError("F2 forbidden retry/search/gravity-drop behavior enabled")
    output = workspace_path(job["output_namespace"], "F2 output")
    guard_dir = workspace_path(value["guard_directory"], "F2 guard directory")
    cache_job = workspace_path(value["cache_directory"], "F2 cache directory") / job_id
    if output.exists():
        raise FileExistsError("F2 output namespace must be new")
    if phase in {"guard", "preflight"} and (guard_dir.exists() or cache_job.exists()):
        raise FileExistsError("F2 Guard/cache paths must be new")
    if phase == "runner" and (not guard_dir.is_dir() or not cache_job.is_dir()):
        raise ValueError("F2 runner lacks Guard-created paths")
    return value, job


def contract_summary(contract):
    return {
        "selected_binding_sha256": contract["binding"]["binding_sha256"],
        "selected_recipe_id": contract["selected"]["recipe_id"],
        "selected_recipe_sha256": contract["selected"]["recipe_sha256"],
        "actual_prefix_end_qpos_sha256": contract["actual_prefix_end_qpos_sha256"],
        "sealed_prefix_end_eef_pose": contract["sealed_prefix_end_eef_pose"].tolist(),
        "sealed_prefix_end_actor_pose": contract["sealed_prefix_end_actor_pose"].tolist(),
        "sealed_actual_eef_to_actor_transform": contract[
            "sealed_actual_eef_to_actor_transform"
        ].tolist(),
        "frozen_strict_cavity_target_actor_pose": contract[
            "frozen_strict_cavity_target_actor_pose"
        ].tolist(),
        "opening_normal_world": contract["opening_normal_world"].tolist(),
        "inside_target_segment_ids": [
            item["segment_id"] for item in contract["inside_targets"]
        ],
        "inside_targets_sha256": contract["inside_targets_sha256"],
        "beside_target_segment_ids": [
            item["segment_id"] for item in contract["beside_targets"]
        ],
        "beside_targets_sha256": contract["beside_targets_sha256"],
        "beside_candidate_index": contract["beside_candidate_index"],
        "beside_candidate_xy_m": contract["beside_candidate_xy_m"],
        "beside_radial_distance_m": contract["beside_radial_distance_m"],
        "primary_10cm_gravity_drop": False,
        "open_gripper_during_planner_gate": False,
        "future_physical_contract_not_authorized": {
            "support_stability_before_open_frames": 50,
            "slow_release_normalized_targets": [0.2, 0.4, 0.6, 0.8, 1.0],
            "post_release_settle_frames": 250,
            "final_strict_inside_required": True,
        },
    }


def preflight(manifest_path, job_id):
    manifest, _job = load_manifest(manifest_path, job_id, phase="preflight")
    contract = load_sealed_contract()
    return {
        "schema_version": "cmf_f2_controlled_insertion_route_gate_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "contract": contract_summary(contract),
        "inside_target_count": 5,
        "beside_target_count": 6,
        "aggregate_planner_query_cap": 11,
        "output_created": False,
        "scene_created": False,
        "gpu_context_created": False,
        "physical_execution_authorized": False,
        "pass": True,
    }


def _derive_live_targets(scene, contract, relation):
    from controlled_multi_future.f2_asset_bound_runtime_v3 import (
        _actor_pose_centered_on_support,
    )
    from controlled_multi_future.family_runners_v3_1 import (
        _arm_eef_pose,
        _arm_original_pose,
    )
    from controlled_multi_future.family_runners_v3_3 import (
        _actor_local_geometry_bounds,
        _entity,
        _pose,
    )
    from controlled_multi_future.geometry import (
        actor_target_to_eef_pose,
        compose_pose,
        matrix_pose,
        pose_matrix,
        world_axis_offset_pose,
    )

    import sapien

    qpos = contract["actual_prefix_end_qpos"]
    robot = scene.robot.left_entity
    robot.set_qpos(qpos)
    robot.set_qvel(np.zeros_like(qpos))
    can_entity = _entity(scene.can)
    actor = contract["sealed_prefix_end_actor_pose"]
    can_entity.set_pose(sapien.Pose(actor[:3], actor[3:]))
    if hasattr(can_entity, "set_velocity"):
        can_entity.set_velocity(np.zeros(3, dtype=np.float64))
    if hasattr(can_entity, "set_angular_velocity"):
        can_entity.set_angular_velocity(np.zeros(3, dtype=np.float64))

    live_qpos = np.asarray(robot.get_qpos(), dtype=np.float64)
    live_eef = np.asarray(_arm_eef_pose(scene, "left"), dtype=np.float64)
    live_actor = np.asarray(_pose(scene.can), dtype=np.float64)
    sealed_eef = contract["sealed_prefix_end_eef_pose"]
    if not np.array_equal(live_qpos, qpos):
        raise ValueError("F2 live planner scene did not restore sealed qpos exactly")
    if (
        float(np.linalg.norm(live_eef[:3] - sealed_eef[:3])) > 1e-5
        or _quaternion_error(live_eef[3:], sealed_eef[3:]) > 1e-5
        or float(np.linalg.norm(live_actor[:3] - actor[:3])) > 1e-7
        or _quaternion_error(live_actor[3:], actor[3:]) > 1e-7
    ):
        raise ValueError("F2 live planner scene differs from sealed prefix state")

    binding = contract["binding"]
    neutral = np.asarray(_arm_original_pose(scene, "left"), dtype=np.float64)
    if (
        float(np.linalg.norm(neutral[:3] - contract["neutral_eef_pose"][:3])) > 1e-6
        or _quaternion_error(neutral[3:], contract["neutral_eef_pose"][3:]) > 1e-6
    ):
        raise ValueError("F2 live neutral pose differs from sealed neutral")

    if relation == "inside":
        local_center, _half = _actor_local_geometry_bounds(scene.can)
        local_center_pose = np.asarray(
            [*local_center, 1.0, 0.0, 0.0, 0.0], dtype=np.float64
        )
        cavity = binding["strict_cavity_contract"]
        box_pose = _pose(scene.box)
        target_geometry = compose_pose(
            box_pose,
            [
                *cavity["target_center_local_m"],
                *binding["inside_object_orientation_wxyz"],
            ],
        )
        target_actor = matrix_pose(
            pose_matrix(target_geometry)
            @ np.linalg.inv(pose_matrix(local_center_pose))
        )
        expected_target = contract["frozen_strict_cavity_target_actor_pose"]
        if (
            float(np.linalg.norm(target_actor[:3] - expected_target[:3])) > 1e-6
            or _quaternion_error(target_actor[3:], expected_target[3:]) > 1e-7
        ):
            raise ValueError("F2 live strict-cavity target differs from sealed target")
        opening = pose_matrix(box_pose)[:3, :3] @ np.asarray(
            [0.0, 1.0, 0.0], dtype=np.float64
        )
        opening /= np.linalg.norm(opening)
        if not np.allclose(opening, contract["opening_normal_world"], atol=1e-8, rtol=0.0):
            raise ValueError("F2 live opening normal differs from sealed contract")
        supported = actor_target_to_eef_pose(sealed_eef, actor, target_actor)
        preinsert = supported.copy()
        preinsert[:3] += 0.030 * opening
        high_carry = preinsert.copy()
        high_carry[2] = max(float(sealed_eef[2]), float(preinsert[2]))
        targets = [
            {"segment_id": INSIDE_SEGMENTS[0], "pose": high_carry.tolist()},
            {"segment_id": INSIDE_SEGMENTS[1], "pose": preinsert.tolist()},
            {"segment_id": INSIDE_SEGMENTS[2], "pose": supported.tolist()},
            {"segment_id": INSIDE_SEGMENTS[3], "pose": preinsert.tolist()},
            {"segment_id": INSIDE_SEGMENTS[4], "pose": neutral.tolist()},
        ]
        expected_hash = contract["inside_targets_sha256"]
    elif relation == "beside":
        candidate_xy = np.asarray(contract["beside_candidate_xy_m"], dtype=np.float64)
        local_center, half = _actor_local_geometry_bounds(scene.can)
        target_actor = _actor_pose_centered_on_support(
            target_geometry_xy=candidate_xy,
            support_plane_z_m=0.74 + float(scene.table_z_bias),
            orientation_wxyz=binding["layout_payload"]["main_object_orientation_wxyz"],
            local_geometry_center_m=local_center,
            half_extents_m=half,
        )
        expected = contract["beside_template_actor_pose"].copy()
        expected[:2] = candidate_xy
        if (
            float(np.linalg.norm(target_actor[:3] - expected[:3])) > 1e-6
            or _quaternion_error(target_actor[3:], expected[3:]) > 1e-7
        ):
            raise ValueError("F2 live beside index-2 target differs from sealed layout")
        release = actor_target_to_eef_pose(sealed_eef, actor, target_actor)
        preplace = world_axis_offset_pose(release, 0.08)
        hub = preplace.copy()
        hub[:2] = (sealed_eef[:2] + preplace[:2]) / 2.0
        hub[2] = max(float(sealed_eef[2]), float(preplace[2]))
        targets = [
            {"segment_id": BESIDE_SEGMENTS[0], "pose": hub.tolist()},
            {"segment_id": BESIDE_SEGMENTS[1], "pose": preplace.tolist()},
            {"segment_id": BESIDE_SEGMENTS[2], "pose": release.tolist()},
            {"segment_id": BESIDE_SEGMENTS[3], "pose": preplace.tolist()},
            {"segment_id": BESIDE_SEGMENTS[4], "pose": hub.tolist()},
            {"segment_id": BESIDE_SEGMENTS[5], "pose": neutral.tolist()},
        ]
        expected_hash = contract["beside_targets_sha256"]
    else:
        raise ValueError("unknown F2 planner-only relation")
    frozen_targets = (
        contract["inside_targets"]
        if relation == "inside"
        else contract["beside_targets"]
    )
    if len(targets) != len(frozen_targets) or any(
        live["segment_id"] != frozen["segment_id"]
        or not np.allclose(
            np.asarray(live["pose"], dtype=np.float64),
            np.asarray(frozen["pose"], dtype=np.float64),
            atol=1e-6,
            rtol=0.0,
        )
        for live, frozen in zip(targets, frozen_targets)
    ):
        raise ValueError("F2 live targets differ from CPU-frozen targets")
    targets = json.loads(json.dumps(frozen_targets))
    if canonical_hash(targets) != expected_hash:
        raise ValueError("F2 frozen target hash changed")
    return targets, {
        "actual_prefix_end_qpos_sha256": contract["actual_prefix_end_qpos_sha256"],
        "live_prefix_end_eef_pose": live_eef.tolist(),
        "live_prefix_end_actor_pose": live_actor.tolist(),
        "target_actor_pose": target_actor.tolist(),
        "target_segment_ids": [item["segment_id"] for item in targets],
        "targets_sha256": expected_hash,
        "physical_action_executed": False,
        "gripper_opened": False,
    }


def run_gate(manifest, job, output):
    from controlled_multi_future.f2_asset_bound_runtime_v3 import (
        RoboTwinRealSapienF2AssetBoundAdapterV3,
    )
    from controlled_multi_future.family_runners_v3_1 import _plan_chain, _planner_reset

    contract = load_sealed_contract()
    rows = []
    total_queries = 0
    for relation, query_cap, reset_seed in (
        ("inside", 5, 2026090401),
        ("beside", 6, 2026090402),
    ):
        adapter = RoboTwinRealSapienF2AssetBoundAdapterV3(
            output_root=output / f"{relation}_scene_adapter",
            expected_implementation_source_sha256=manifest[
                "implementation_source_sha256"
            ],
            binding=contract["binding"],
            planner_only=True,
        )
        cleanup = None
        with base.opened_scene(
            adapter,
            contract["planned"],
            phase=f"F2_CONTROLLED_INSERTION_ROUTE_GATE_{relation.upper()}",
            program=None,
            family="F2",
        ) as (scene, context):
            targets, state_receipt = _derive_live_targets(
                scene, contract, relation
            )
            reset = _planner_reset(
                scene,
                planner_seed=reset_seed,
                variant_id=f"f2_controlled_insertion_route_gate_v1:{relation}",
                arm="left",
            )
            planned = _plan_chain(
                scene, targets, query_limit=query_cap, arm="left"
            )
        cleanup = context.cleanup_receipt
        queries = len(planned["segment_receipts"])
        total_queries += queries
        row = {
            "relation": relation,
            "planner_query_cap": query_cap,
            "planner_query_count": queries,
            "planner_pass": planned.get("pass") is True,
            "state_restore_receipt": state_receipt,
            "planner_reset_receipt": reset,
            "segment_receipts": planned["segment_receipts"],
            "terminal_qpos": planned["terminal_qpos"],
            "terminal_qpos_sha256": planned["terminal_qpos_sha256"],
            "cleanup": cleanup,
            "physical_execution_count": 0,
        }
        row["receipt_sha256"] = canonical_hash(row)
        base.write_new(output / f"{relation}_planner_receipt.json", row)
        rows.append(row)
    if total_queries > 11 or len(rows) != 2:
        raise RuntimeError("F2 planner-only Gate accounting exceeded reviewed cap")
    return {
        "schema_version": "cmf_f2_controlled_insertion_route_gate_result_v1",
        "gate_name": "F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1",
        "contract": contract_summary(contract),
        "planner_rows": rows,
        "planner_query_count": total_queries,
        "fresh_planner_scene_count": len(rows),
        "both_chains_pass": all(row["planner_pass"] for row in rows),
        "physical_execution_count": 0,
        "branch_execution_count": 0,
        "raw_trajectory_count": 0,
        "video_count": 0,
        "accepted_root_count": 0,
        "formal_trajectory_count": 0,
        "automatic_continuation": False,
        "separate_external_review_required_before_root": True,
        "formal_data": False,
    }


def write_new(path, value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    base.write_new(Path(path), canonical_jsonable(value))


def main(argv=None):
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--job-id", default=EXPECTED_JOB_ID)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.contract_only:
        contract = load_sealed_contract()
        print(json.dumps(contract_summary(contract), sort_keys=True))
        return 0
    if args.manifest is None:
        raise ValueError("F2 manifest is required outside contract-only mode")
    if args.preflight_only:
        print(json.dumps(preflight(args.manifest, args.job_id), sort_keys=True))
        return 0
    manifest, job = load_manifest(args.manifest, args.job_id, phase="runner")
    if (
        not os.environ.get("CUDA_VISIBLE_DEVICES")
        or os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX") is None
        or os.environ.get("LD_LIBRARY_PATH")
    ):
        raise PermissionError("F2 runner lacks clean UUID-bound Guard environment")
    output = Path(job["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    write_new(
        output / "job_start.json",
        {"manifest_sha256": manifest["manifest_sha256"], "job_id": args.job_id},
    )
    error = None
    result = None
    try:
        result = run_gate(manifest, job, output)
    except BaseException as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    terminal = canonical_jsonable({
        "schema_version": "cmf_f2_controlled_insertion_route_gate_terminal_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": args.job_id,
        "result": result,
        "error": error,
        "pass": error is None
        and bool(result)
        and result.get("both_chains_pass") is True,
        "physical_execution_count": 0,
        "accepted_root_count": 0,
        "formal_trajectory_count": 0,
        "automatic_continuation": False,
        "formal_data": False,
        "stage1_authorized": False,
    })
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(output / "job_terminal.json", terminal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
