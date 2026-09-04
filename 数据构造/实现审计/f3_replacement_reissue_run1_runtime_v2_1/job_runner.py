#!/usr/bin/env python3
"""Fail-closed V2.1 runtime for the still-unconsumed F3 reissue.

V2.1 preserves the V2 candidate/program/physical-Gate contract.  It only
repairs terminal exit semantics and makes physical planner accounting an
immutable property of each physical-scene receipt, including exception paths.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import operator
import os
from pathlib import Path
import subprocess
import traceback
from unittest.mock import patch


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
VAULT = WORKSPACE / "Vault-on-Fvl09"
AUDIT = VAULT / "数据构造/实现审计"
THIS_RUNNER = Path(__file__).resolve()
THIS_GUARD = THIS_RUNNER.with_name("guarded_launcher.py")

V2_RUNNER = AUDIT / "f3_replacement_reissue_run1_runtime_v2/job_runner.py"
V2_RUNNER_SHA256 = "d95d1c71fb3ebdf93d8d4918dad8b5cc2acfc395906be2421952d1aea826136c"
V2_GUARD = AUDIT / "f3_replacement_reissue_run1_runtime_v2/guarded_launcher.py"
V2_GUARD_SHA256 = "57e31200d585120363628fef35401f3f0fc50f6c4ef47bf13d30c8f2b721398d"
V2_MANIFEST = AUDIT / "F3_ZERO_SCENE_WIRING_REISSUE_APPROVED_RUN1_MANIFEST_V2.json"
V2_MANIFEST_FILE_SHA256 = "e0d85ab17ee19ef04f298fbef4cf9c2a5ca0d06af99b5ecca0295b15c38de0fa"
V2_PREFLIGHT = AUDIT / "F3_ZERO_SCENE_WIRING_REISSUE_RUN1_PREFLIGHT_V2.json"
V2_PREFLIGHT_FILE_SHA256 = "3efabc0e67271d8a6533e9f4fffd26ec805bf1498f115c60f0846e2e4dfbe973"
PLAN = AUDIT / "CMF_F2_F3_F4_NEXT_EXECUTION_PLAN_V1_20260904.md"
PLAN_SHA256 = "f219a4e57f617b322a9526f939bf9498716f4e428ba220bbd80e64e21e7cfe12"
EXTERNAL_DECISION = AUDIT / "EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_20260904.md"
EXTERNAL_DECISION_FILE_SHA256 = "790fc6e3e48694d212bb1c1a8833d270f2dc0dbe4748a605f319003787fd0dcd"

EXPECTED_SOURCE = "3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7"
EXPECTED_HEAD = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
EXPECTED_STATUS = "APPROVED_F3_ZERO_SCENE_WIRING_REISSUE_RUN1_V2_1"
EXPECTED_JOB_ID = "f3-centralized-replacements-zero-scene-reissue-run1-v2-1"
EXPECTED_MODE = "F3_CENTRALIZED_REPLACEMENT_GATE_ZERO_SCENE_REISSUE_V2_1"
EXPECTED_PROPOSAL_SHA256 = "5203ca62afba5a594edabfd57ef0a0aa3e12106895ecf508478e4111f3451dd2"
EXPECTED_TUPLES = [
    ["bottle5", "right", "lower_body", "contact2", "rotation1", "r1505"],
    ["bottle4", "left", "upper_body", "contact0", "rotation6", "r2180"],
    ["bottle13", "right", "upper_body", "contact2", "rotation5", "r3677"],
]
EXPECTED_REPLACEMENT_RECIPE_SHA256S = [
    "88f1c0bcb521d4fc7e9b1e64b24d94f1c7d81f1703fba19cd3f622d74c591c49",
    "176bc2a145a17bf13a70ec365ed144fefcb4689a6eb4379b6d8db0645f1cefb1",
    "3d945ce11eef1ba911621dd14238ad0eb7d91e167c6aa61a8de861cca18bde44",
]
EXPECTED_RETAINED_RECIPE_SHA256 = (
    "3638a9e93f5101b1e7a9370fe7c4735c5a1a062e890d7ac66d47f6f182cf333f"
)
LEGACY_NO_SUFFIX_COUNT_SOURCE = (
    "derived_v2_1_from_hash_bound_legacy_v1_explicit_executed_false"
)
EXPLICIT_NO_SUFFIX_COUNT_SOURCE = "reported_by_hash_bound_execution_body"
EXPECTED_CAPS = {
    "replacement_qualification_planner_query_cap": 30,
    "physical_planner_query_cap_per_candidate": 7,
    "physical_candidate_cap": 4,
    "aggregate_planner_query_cap": 58,
    "planner_scene_cap": 6,
    "physical_scene_cap": 4,
    "aggregate_scene_cap": 10,
    "conditional_no_suffix_scene_cap_in_this_job": 0,
    "reserved_next_no_suffix_scene_cap": 3,
    "formal_trajectory_cap": 0,
}


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


def workspace_path(value, label, *, must_file=False):
    path = Path(str(value)).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise ValueError(f"{label} is outside workspace")
    if must_file and not path.is_file():
        raise ValueError(f"{label} is missing")
    return path


def exact_int(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer, not bool")
    try:
        return int(operator.index(value))
    except TypeError as exc:
        raise ValueError(f"{label} must be an integer") from exc


def load_v2():
    immutable = {
        V2_RUNNER: V2_RUNNER_SHA256,
        V2_GUARD: V2_GUARD_SHA256,
        V2_MANIFEST: V2_MANIFEST_FILE_SHA256,
        V2_PREFLIGHT: V2_PREFLIGHT_FILE_SHA256,
        PLAN: PLAN_SHA256,
        EXTERNAL_DECISION: EXTERNAL_DECISION_FILE_SHA256,
    }
    for path, expected in immutable.items():
        if file_sha(path) != expected:
            raise RuntimeError(f"immutable F3 V2/V2.1 lineage changed: {path.name}")
    spec = importlib.util.spec_from_file_location("cmf_f3_reissue_v2_for_v2_1", V2_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load immutable F3 reissue V2 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v2 = load_v2()


def load_manifest(path: Path, job_id: str, *, phase: str):
    """Validate a future V2.1 manifest without accepting the V2 namespace."""

    manifest_path = workspace_path(path, "manifest", must_file=True)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("F3 V2.1 manifest self-hash mismatch")
    if value.get("status") != EXPECTED_STATUS or value.get("approved") is not True:
        raise PermissionError("F3 V2.1 manifest is not approved")
    if any(
        value.get(key) is not True
        for key in (
            "gpu_execution_authorized",
            "planner_execution_authorized",
            "physical_execution_authorized",
        )
    ):
        raise PermissionError("F3 V2.1 execution scope changed")
    if (
        value.get("implementation_source_sha256") != EXPECTED_SOURCE
        or python_tree_sha(PROJECT / "controlled_multi_future") != EXPECTED_SOURCE
    ):
        raise ValueError("F3 V2.1 controlled source differs from freeze")
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
        raise ValueError("F3 V2.1 GPU scheduling contract changed")
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
            raise ValueError(f"forbidden F3 V2.1 stage enabled: {key}")

    file_bindings = (
        ("runner_script_path", "runner_script_sha256"),
        ("guard_script_path", "guard_script_sha256"),
        ("execution_plan_path", "execution_plan_file_sha256"),
        ("external_review_decision_path", "external_review_decision_file_sha256"),
        ("v2_manifest_path", "v2_manifest_file_sha256"),
        ("v2_runner_path", "v2_runner_file_sha256"),
        ("v2_guard_path", "v2_guard_file_sha256"),
        ("v2_preflight_path", "v2_preflight_file_sha256"),
        ("v2_supersession_receipt_path", "v2_supersession_receipt_file_sha256"),
        ("wiring_overlay_path", "wiring_overlay_file_sha256"),
        ("failed_runner_path", "failed_runner_file_sha256"),
        ("failed_terminal_path", "failed_terminal_file_sha256"),
        ("retained_stage_a_path", "retained_stage_a_file_sha256"),
        ("retained_stage_b_path", "retained_stage_b_file_sha256"),
    )
    for path_key, sha_key in file_bindings:
        bound = workspace_path(value[path_key], path_key, must_file=True)
        if file_sha(bound) != value[sha_key]:
            raise ValueError(f"F3 V2.1 bound file hash changed: {path_key}")
    if (
        workspace_path(value["runner_script_path"], "runner_script_path", must_file=True)
        != THIS_RUNNER
        or workspace_path(
            value["guard_script_path"], "guard_script_path", must_file=True
        )
        != THIS_GUARD
    ):
        raise ValueError("F3 V2.1 manifest selected a different runtime path")
    if (
        value["execution_plan_file_sha256"] != PLAN_SHA256
        or value["external_review_decision_file_sha256"]
        != EXTERNAL_DECISION_FILE_SHA256
        or value["v2_manifest_file_sha256"] != V2_MANIFEST_FILE_SHA256
        or value["v2_runner_file_sha256"] != V2_RUNNER_SHA256
        or value["v2_guard_file_sha256"] != V2_GUARD_SHA256
        or value["v2_preflight_file_sha256"] != V2_PREFLIGHT_FILE_SHA256
        or value.get("reissue_ordinal") != 1
        or value.get("v1_consumed") is not False
        or value.get("v2_consumed") is not False
        or value.get("same_reissue_ordinal") is not True
        or value.get("second_reissue") is not False
    ):
        raise ValueError("F3 V2.1 decision/supersession lineage changed")

    assets = value.get("asset_hashes_by_family", {}).get("F3", {})
    if not assets:
        raise ValueError("F3 V2.1 asset map missing")
    for relative, expected in assets.items():
        if file_sha(PROJECT / relative) != expected:
            raise ValueError(f"F3 V2.1 asset changed: {relative}")

    jobs = value.get("jobs")
    if (
        not isinstance(jobs, list)
        or len(jobs) != 1
        or jobs[0].get("job_id") != job_id
        or job_id != EXPECTED_JOB_ID
    ):
        raise ValueError("F3 V2.1 exact job lookup failed")
    job = jobs[0]
    if (
        job.get("family") != "F3"
        or job.get("mode") != EXPECTED_MODE
        or job.get("proposal_sha256") != EXPECTED_PROPOSAL_SHA256
        or job.get("replacement_tuples") != EXPECTED_TUPLES
        or any(job.get(key) != expected for key, expected in EXPECTED_CAPS.items())
        or job.get("conditional_no_suffix_executed_in_this_job") is not False
        or job.get("retained_survivor_qualification_rerun") is not False
        or job.get("automatic_retry") is not False
        or job.get("fallback_allowed") is not False
        or job.get("second_reissue_allowed") is not False
    ):
        raise ValueError("F3 V2.1 exact tuple/budget/stop contract changed")

    output = workspace_path(job["output_namespace"], "F3 V2.1 output")
    guard_dir = workspace_path(value["guard_directory"], "F3 V2.1 guard directory")
    cache_job = workspace_path(value["cache_directory"], "F3 V2.1 cache directory") / job_id
    if output.exists():
        raise FileExistsError("F3 V2.1 output namespace must be new")
    if phase in {"guard", "preflight"} and (guard_dir.exists() or cache_job.exists()):
        raise FileExistsError("F3 V2.1 Guard/cache paths must be new")
    if phase == "runner" and (not guard_dir.is_dir() or not cache_job.is_dir()):
        raise ValueError("F3 V2.1 runner lacks Guard-created paths")
    return value, job


def prepare_contract(manifest, job):
    return v2.prepare_contract(manifest, job)


def preflight(manifest_path, job_id):
    manifest, job = load_manifest(manifest_path, job_id, phase="preflight")
    _patched, proposal, retained_a, retained_b, overlay_preflight = prepare_contract(
        manifest, job
    )
    return {
        "schema_version": "cmf_f3_zero_scene_wiring_reissue_v2_1_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "overlay_preflight": overlay_preflight,
        "replacement_recipe_sha256s": [
            item["recipe_sha256"] for item in proposal["replacement_candidates"]
        ],
        "retained_recipe_id": retained_a["spec"]["recipe"]["recipe_id"],
        "retained_stage_b_receipt_sha256": retained_b["terminal"]["receipt_sha256"],
        "budget_contract": {key: job[key] for key in EXPECTED_CAPS},
        "physical_planner_accounting_source": "physical_scene_receipt",
        "terminal_exit_zero_iff_terminal_pass": True,
        "conditional_no_suffix_executed_in_this_job": False,
        "reissue_ordinal": 1,
        "v1_consumed": False,
        "v2_consumed": False,
        "output_created": False,
        "scene_created": False,
        "gpu_context_created": False,
        "pass": True,
    }


def write_new(path, value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable

    serializable = canonical_jsonable(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(serializable, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _planner_snapshot(scene, label, error_holder):
    try:
        value = exact_int(getattr(scene, "planner_query_count"), label)
        return value
    except BaseException as exc:
        if error_holder.get("error") is None:
            error_holder["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        return None


def make_audited_physical_scene_recorder(helper, receipt_paths):
    """Return a recorder that persists planner before/after/delta in finally."""

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
        from controlled_multi_future.canonical_artifact import canonical_jsonable

        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
        current = anchor = video = trace = result = None
        planner_before = planner_after = planner_delta = None
        error_holder = {"error": None}
        with helper.opened_scene(
            adapter,
            legacy_scene_spec,
            phase=phase,
            program=program,
            family=family,
        ) as (scene, context):
            planner_counter_initialized_by_v2_1 = not hasattr(
                scene, "planner_query_count"
            )
            if planner_counter_initialized_by_v2_1:
                # The shared planner helper follows the same initialize-if-
                # absent convention.  Installing zero here makes the physical
                # before snapshot explicit without resetting an existing
                # scene counter.
                scene.planner_query_count = 0
            planner_before = _planner_snapshot(
                scene, "planner_query_count_before", error_holder
            )
            try:
                current = adapter.capture_current(scene)
                anchor = adapter.capture_anchor(scene)
                actor = getattr(scene, trace_actor_name)
                scene.initialize_trace(actor, arm, role_actors=scene.role_actors)
                scene.start_development_video_capture(output / "trajectory.mp4")
                result = execute(scene)
            except BaseException as exc:
                if error_holder["error"] is None:
                    error_holder["error"] = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    }
            finally:
                if hasattr(scene, "trace") and scene.trace:
                    try:
                        trace = helper.save_trace(scene, output / "physical_trace.npz")
                    except BaseException as exc:
                        if error_holder["error"] is None:
                            error_holder["error"] = {
                                "type": type(exc).__name__,
                                "message": str(exc),
                                "traceback": traceback.format_exc(),
                            }
                try:
                    video = scene.finish_development_video_capture(
                        terminal_status=(
                            "pass" if error_holder["error"] is None else "failed"
                        )
                    )
                except BaseException as exc:
                    if error_holder["error"] is None:
                        error_holder["error"] = {
                            "type": type(exc).__name__,
                            "message": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                # This snapshot is deliberately in the physical-scene finally
                # block.  It therefore survives an exception from execute().
                planner_after = _planner_snapshot(
                    scene, "planner_query_count_after", error_holder
                )
                if planner_before is not None and planner_after is not None:
                    planner_delta = planner_after - planner_before
        cleanup = context.cleanup_receipt
        receipt = canonical_jsonable({
            "schema_version": "cmf_f3_v2_1_physical_scene_receipt_v1",
            "family": family,
            "phase": phase,
            "program": program,
            "current": current,
            "anchor": anchor,
            "result": result,
            "error": error_holder["error"],
            "trace": trace,
            "video": video,
            "cleanup": cleanup,
            "planner_query_count_before": planner_before,
            "planner_query_count_after": planner_after,
            "planner_query_delta": planner_delta,
            "planner_counter_initialized_by_v2_1": (
                planner_counter_initialized_by_v2_1
            ),
            "planner_accounting_source": "scene_counter_finally",
            "pass": (
                error_holder["error"] is None
                and isinstance(result, dict)
                and planner_delta is not None
                and planner_delta >= 0
            ),
        })
        receipt["receipt_sha256"] = canonical_hash(receipt)
        receipt_path = output / "scene_receipt.json"
        write_new(receipt_path, receipt)
        receipt_paths.append(receipt_path)
        return receipt

    return record_physical_scene


def _read_physical_receipt(path):
    path = workspace_path(path, "physical scene receipt", must_file=True)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(receipt)
    digest = payload.pop("receipt_sha256", None)
    self_hash_valid = digest == canonical_hash(payload)
    count_complete = True
    try:
        before = exact_int(
            receipt.get("planner_query_count_before"), "planner_query_count_before"
        )
        after = exact_int(
            receipt.get("planner_query_count_after"), "planner_query_count_after"
        )
        delta = exact_int(receipt.get("planner_query_delta"), "planner_query_delta")
    except ValueError:
        before = after = delta = None
        count_complete = False
    if count_complete and (before < 0 or after < 0 or delta < 0 or after - before != delta):
        count_complete = False
    return {
        "path": str(path),
        "receipt": receipt,
        "receipt_sha256": digest,
        "self_hash_valid": self_hash_valid,
        "planner_query_count_before": before,
        "planner_query_count_after": after,
        "planner_query_delta": delta,
        "planner_count_complete_nonnegative": count_complete,
    }


def _candidate_sha(row):
    candidate = row.get("candidate") if isinstance(row, dict) else None
    return candidate.get("recipe_sha256") if isinstance(candidate, dict) else None


def _safe_nonnegative_query(value):
    try:
        parsed = exact_int(value, "planner query count")
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def normalize_no_suffix_count(result):
    """Add only the legacy count that V1 omitted; never rewrite execution truth."""

    if "conditional_no_suffix_scene_count" in result:
        result["conditional_no_suffix_scene_count_source"] = (
            EXPLICIT_NO_SUFFIX_COUNT_SOURCE
        )
        return
    if result.get("conditional_no_suffix_executed") is False:
        # The exact hash-bound V1 execution body explicitly reports that it
        # did not execute the conditional diagnostic, but its legacy result
        # schema omitted the corresponding count.  V2.1 may derive only this
        # absent count; a missing/non-False execution field is never repaired.
        result["conditional_no_suffix_scene_count"] = 0
        result["conditional_no_suffix_scene_count_source"] = (
            LEGACY_NO_SUFFIX_COUNT_SOURCE
        )


def build_runtime_accounting(result, job, receipt_paths):
    """Validate all accounting, sourcing physical queries only from receipts."""

    planner_rows = result.get("planner_rows")
    planner_rows = planner_rows if isinstance(planner_rows, list) else []
    exact_three = len(planner_rows) == 3
    planner_order = [_candidate_sha(row) for row in planner_rows]

    a_counts = []
    b_counts = []
    planner_row_fields_complete = exact_three
    stage_b_shape_consistent = exact_three
    for row in planner_rows:
        a_value = _safe_nonnegative_query(row.get("stage_a_queries"))
        stage_a_pass = row.get("stage_a_pass") is True
        if stage_a_pass:
            b_value = _safe_nonnegative_query(row.get("stage_b_queries"))
        else:
            b_value = 0
            if row.get("stage_b_pass") is not False or "stage_b_queries" in row:
                stage_b_shape_consistent = False
        if a_value is None or b_value is None:
            planner_row_fields_complete = False
        a_counts.append(0 if a_value is None else a_value)
        b_counts.append(0 if b_value is None else b_value)

    qualification_reported = _safe_nonnegative_query(
        result.get("replacement_planner_queries")
    )
    qualification_derived = sum(a_counts) + sum(b_counts)
    qualification = (
        qualification_reported if qualification_reported is not None else -1
    )
    planner_scenes = len(planner_rows) + sum(
        row.get("stage_a_pass") is True for row in planner_rows
    )

    physical_rows = result.get("physical_rows")
    physical_rows = physical_rows if isinstance(physical_rows, list) else []
    try:
        physical_execution_count = exact_int(
            result.get("physical_execution_count"), "physical_execution_count"
        )
    except ValueError:
        physical_execution_count = -1
    receipt_records = [_read_physical_receipt(path) for path in receipt_paths]

    physical_row_receipt_match = len(physical_rows) == len(receipt_records)
    if physical_row_receipt_match:
        for row, record in zip(physical_rows, receipt_records):
            if row.get("scene_receipt_sha256") != record["receipt_sha256"]:
                physical_row_receipt_match = False
                break

    expected_physical_candidate_order = []
    new_survivors = [
        EXPECTED_REPLACEMENT_RECIPE_SHA256S[index]
        for index, row in enumerate(planner_rows[:3])
        if row.get("stage_b_pass") is True
    ]
    if new_survivors:
        expected_physical_candidate_order = (
            [EXPECTED_RETAINED_RECIPE_SHA256] + new_survivors
        )[:4]
    physical_candidate_order = [_candidate_sha(row) for row in physical_rows]

    deltas = [record["planner_query_delta"] for record in receipt_records]
    physical_counts_complete = all(
        record["self_hash_valid"]
        and record["planner_count_complete_nonnegative"]
        and record["receipt"].get("family") == "F3"
        and record["receipt"].get("phase")
        == "F3_CENTRALIZED_REPLACEMENT_PHYSICAL"
        for record in receipt_records
    )
    physical_total = sum(value for value in deltas if value is not None)
    physical_scenes = len(receipt_records)
    aggregate_queries = qualification + physical_total
    aggregate_scenes = planner_scenes + physical_scenes

    normalized_physical_rows = []
    for index, row in enumerate(physical_rows):
        normalized = dict(row)
        old_terminal_value = normalized.get("physical_planner_queries")
        record = receipt_records[index] if index < len(receipt_records) else None
        normalized.update(
            {
                "returned_terminal_physical_planner_queries_diagnostic": old_terminal_value,
                "physical_planner_queries": (
                    record["planner_query_delta"] if record is not None else None
                ),
                "physical_planner_accounting_source": "physical_scene_receipt",
                "physical_scene_receipt_path": (
                    record["path"] if record is not None else None
                ),
            }
        )
        normalized_physical_rows.append(normalized)

    physical_success_count = sum(
        row.get("physical_pass") is True for row in physical_rows
    )
    no_suffix_scene_count = _safe_nonnegative_query(
        result.get("conditional_no_suffix_scene_count")
    )
    no_suffix_zero = (
        result.get("conditional_no_suffix_executed") is False
        and no_suffix_scene_count == 0
        and job.get("conditional_no_suffix_scene_cap_in_this_job") == 0
    )
    checks = {
        "exact_three_planner_rows": exact_three,
        "planner_rows_exact_replacement_order": planner_order
        == EXPECTED_REPLACEMENT_RECIPE_SHA256S,
        "planner_row_query_fields_complete_nonnegative": planner_row_fields_complete,
        "stage_b_scene_shape_consistent": stage_b_shape_consistent,
        "stage_a_queries_at_most_9": sum(a_counts) <= 9,
        "stage_b_queries_at_most_21": sum(b_counts) <= 21,
        "qualification_reported_nonnegative": qualification_reported is not None,
        "qualification_equals_stage_a_plus_stage_b": qualification_reported
        == qualification_derived,
        "qualification_at_most_30": 0
        <= qualification
        <= job["replacement_qualification_planner_query_cap"],
        "physical_rows_equal_execution_count": len(physical_rows)
        == physical_execution_count,
        "one_receipt_per_attempted_physical_candidate": len(receipt_records)
        == physical_execution_count,
        "physical_row_receipt_hashes_match": physical_row_receipt_match,
        "physical_candidate_order_consistent": physical_candidate_order
        == expected_physical_candidate_order,
        "physical_receipt_counts_complete_nonnegative": physical_counts_complete,
        "each_physical_at_most_7": physical_counts_complete
        and all(
            value is not None
            and value <= job["physical_planner_query_cap_per_candidate"]
            for value in deltas
        ),
        "physical_candidates_at_most_4": 0
        <= physical_execution_count
        <= job["physical_candidate_cap"],
        "physical_success_count_consistent": result.get("physical_success_count")
        == physical_success_count,
        "gate_pass_consistent": result.get("gate_pass")
        is (physical_success_count >= 2),
        "planner_scenes_at_most_6": planner_scenes <= job["planner_scene_cap"],
        "physical_scenes_equal_receipt_count": physical_scenes
        == physical_execution_count,
        "physical_scenes_at_most_4": physical_scenes
        <= job["physical_scene_cap"],
        "aggregate_scenes_identity": aggregate_scenes
        == planner_scenes + physical_scenes,
        "aggregate_scenes_at_most_10": aggregate_scenes
        <= job["aggregate_scene_cap"],
        "aggregate_planner_identity": aggregate_queries
        == qualification + physical_total,
        "aggregate_planner_at_most_58": 0
        <= aggregate_queries
        <= job["aggregate_planner_query_cap"],
        "no_suffix_scenes_zero": no_suffix_zero,
    }
    accounting = {
        "schema_version": "cmf_f3_reissue_v2_1_runtime_accounting_v1",
        "planner_rows_expected_order": EXPECTED_REPLACEMENT_RECIPE_SHA256S,
        "planner_rows_observed_order": planner_order,
        "stage_a_planner_queries": a_counts,
        "stage_b_planner_queries": b_counts,
        "replacement_qualification_planner_queries_reported": qualification_reported,
        "replacement_qualification_planner_queries_derived": qualification_derived,
        "physical_scene_receipts": receipt_records,
        "physical_planner_queries_by_candidate": deltas,
        "physical_planner_queries": physical_total,
        "aggregate_planner_queries": aggregate_queries,
        "planner_scenes": planner_scenes,
        "physical_scenes": physical_scenes,
        "aggregate_scenes": aggregate_scenes,
        "conditional_no_suffix_scenes": no_suffix_scene_count,
        "conditional_no_suffix_scene_count_source": result.get(
            "conditional_no_suffix_scene_count_source"
        ),
        "reserved_next_no_suffix_scene_cap": job[
            "reserved_next_no_suffix_scene_cap"
        ],
        "checks": checks,
        "pass": all(checks.values()),
    }
    return accounting, normalized_physical_rows


class RuntimeAccountingError(RuntimeError):
    def __init__(self, result):
        super().__init__(
            f"F3 V2.1 runtime accounting failed: "
            f"{result.get('runtime_accounting', {}).get('checks')}"
        )
        self.result = result


def run_gate(manifest, job, output):
    patched, proposal, _retained_a, _retained_b, overlay_preflight = prepare_contract(
        manifest, job
    )
    receipt_paths = []
    audited_recorder = make_audited_physical_scene_recorder(
        patched.base, receipt_paths
    )
    with patch.object(patched.base, "record_physical_scene", audited_recorder):
        result = patched.run_gate(manifest, job, output)
    normalize_no_suffix_count(result)
    accounting, normalized_physical_rows = build_runtime_accounting(
        result, job, receipt_paths
    )
    result.update(
        {
            "runtime_version": "f3_replacement_reissue_run1_runtime_v2_1",
            "wiring_overlay_sha256": v2.v1.OVERLAY_SHA256,
            "wiring_overlay_preflight": overlay_preflight,
            "proposal_sha256": proposal["proposal_sha256"],
            "physical_rows": normalized_physical_rows,
            "runtime_accounting": accounting,
            "physical_planner_accounting_source": "physical_scene_receipt",
            "reserved_next_no_suffix_scene_cap": 3,
            "reissue_ordinal": 1,
            "second_reissue_allowed": False,
        }
    )
    if accounting["pass"] is not True:
        raise RuntimeAccountingError(result)
    return result


def build_terminal(manifest_sha256, job_id, result, error):
    terminal = {
        "schema_version": "cmf_f3_zero_scene_wiring_reissue_v2_1_terminal_v1",
        "manifest_sha256": manifest_sha256,
        "job_id": job_id,
        "result": result,
        "error": error,
        "pass": (
            error is None
            and isinstance(result, dict)
            and result.get("gate_pass") is True
            and result.get("runtime_accounting", {}).get("pass") is True
            and result.get("conditional_no_suffix_executed") is False
            and _safe_nonnegative_query(
                result.get("conditional_no_suffix_scene_count")
            )
            == 0
        ),
        "reissue_ordinal": 1,
        "second_reissue_allowed": False,
        "conditional_no_suffix_executed_in_this_job": False,
        "formal_data": False,
        "stage1_authorized": False,
    }
    terminal["receipt_sha256"] = canonical_hash(terminal)
    return terminal


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_only:
        print(json.dumps(preflight(args.manifest, args.job_id), sort_keys=True))
        return 0
    manifest, job = load_manifest(args.manifest, args.job_id, phase="runner")
    if (
        not os.environ.get("CUDA_VISIBLE_DEVICES")
        or os.environ.get("CMF_GPU_GUARD_PHYSICAL_INDEX") is None
        or os.environ.get("LD_LIBRARY_PATH")
    ):
        raise PermissionError("F3 V2.1 runner lacks clean UUID-bound Guard environment")
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
        if isinstance(exc, RuntimeAccountingError):
            result = exc.result
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    terminal = build_terminal(manifest["manifest_sha256"], args.job_id, result, error)
    write_new(output / "job_terminal.json", terminal)
    return 0 if terminal["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
