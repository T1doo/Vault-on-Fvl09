#!/usr/bin/env python3
"""CPU-only F4 Guard-to-runner lifecycle integration and negative tests."""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from manifest_contract import (  # noqa: E402
    EXPECTED_CACHE_SUBDIRS,
    GUARD_ENTRY,
    PREPUBLICATION,
    RUNNER_ENTRY,
    canonical_hash,
    load_and_validate_manifest_job,
)


WORKSPACE = Path("/nfs_share/lijunhui")
ENV_PYTHON = WORKSPACE / "Robotwin2/env/bin/python"
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"


def write_new(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def hashed_manifest(value):
    result = deepcopy(value)
    result.pop("manifest_sha256", None)
    result["manifest_sha256"] = canonical_hash(result)
    return result


def hashed_receipt(value):
    result = deepcopy(value)
    result.pop("receipt_sha256", None)
    result["receipt_sha256"] = canonical_hash(result)
    return result


def expect_failure(label, callback, observed):
    try:
        callback()
    except BaseException as exc:
        observed.append(
            {
                "label": label,
                "rejected": True,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        return
    raise AssertionError(f"negative lifecycle case unexpectedly passed: {label}")


def require_runner_preflight_side_effect_free(receipt, output: Path) -> None:
    if (
        output.exists()
        or receipt.get("scene_created") is not False
        or receipt.get("gpu_context_created") is not False
        or receipt.get("output_created") is not False
        or receipt.get("nvidia_smi_called") is not False
        or receipt.get("authorization_consumed") is not False
    ):
        raise RuntimeError("F4 V2 runner-entry preflight created a forbidden side effect")


def historical_regression_checks(manifest, runner_receipt):
    adapter_source = (
        PROJECT
        / "controlled_multi_future/real_sapien_adapter_f4_qualified_root_v1.py"
    ).read_text(encoding="utf-8")
    f4_source_path = PROJECT / "controlled_multi_future/f4_full_program_physical_v1.py"
    tree = ast.parse(f4_source_path.read_text(encoding="utf-8"))
    target_function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "plan_f4_full_program_suffix_from_replayed_prefix_v1"
    )
    assignments = [
        node.lineno
        for node in ast.walk(target_function)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "total_before" for target in node.targets)
    ]
    loads = [
        node.lineno
        for node in ast.walk(target_function)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id == "total_before"
    ]
    accounting = runner_receipt.get("source_planner_query_accounting", {})
    checks = {
        "run10_legacy_010m_check_is_diagnostic": (
            "legacy_fixed_0_10m_check_is_diagnostic" in adapter_source
            and "replacement_checks" in adapter_source
        ),
        "run11_each_program_12_plus_30_equals_42": set(accounting)
        == {"F4-ABC", "F4-ACB", "F4-BAC"}
        and all(
            item.get("target_construction_queries") == 12
            and item.get("chain_queries") == 30
            and item.get("total_queries") == 42
            for item in accounting.values()
        )
        and runner_receipt.get("aggregate_suffix_query_count") == 126,
        "run12_total_before_dominates_all_loads": len(assignments) == 1
        and bool(loads)
        and assignments[0] < min(loads),
        "run13_asset_map_present": set(manifest.get("asset_hashes_by_family", {}))
        == {"F4"}
        and bool(manifest["asset_hashes_by_family"]["F4"]),
        "run14_guard_runner_phase_transition_pass": runner_receipt.get("phase")
        == RUNNER_ENTRY
        and runner_receipt.get("pass") is True,
    }
    return {"checks": checks, "pass": all(checks.values())}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args(argv)
    exact = load_and_validate_manifest_job(
        args.manifest,
        args.job_id,
        phase=PREPUBLICATION,
        require_execution_authorized=False,
    )
    temp_root = Path(
        tempfile.mkdtemp(
            prefix="f4_runtime_v2_lifecycle_",
            dir=str(WORKSPACE / "tmp"),
        )
    )
    observed = []
    runner_receipt = None
    subprocess_receipt = None
    cleanup_pass = False
    try:
        fixture = deepcopy(exact["manifest"])
        fixture["cpu_lifecycle_fixture"] = True
        fixture["run_id"] = fixture["run_id"] + "-cpu-lifecycle-fixture"
        fixture["guard_directory"] = str(temp_root / "guards")
        fixture["cache_directory"] = str(temp_root / "cache")
        fixture["jobs"][0]["output_namespace"] = str(temp_root / "output")
        fixture = hashed_manifest(fixture)
        fixture_path = temp_root / "fixture_manifest.json"
        write_new(fixture_path, fixture)
        guard_entry = load_and_validate_manifest_job(
            fixture_path,
            args.job_id,
            phase=GUARD_ENTRY,
            require_execution_authorized=False,
            allow_lifecycle_fixture=True,
        )
        paths = guard_entry["paths"]
        guard_dir = Path(paths["guard_directory"])
        cache_job = Path(paths["cache_job"])
        output = Path(paths["output"])
        start_path = Path(paths["start_receipt"])
        stdout_path = Path(paths["stdout_log"])
        stderr_path = Path(paths["stderr_log"])
        guard_dir.mkdir(parents=True, exist_ok=False)
        start = hashed_receipt(
            {
                "schema_version": "cmf_f4_development_root_v2_guard_start_v1",
                "run_id": fixture["run_id"],
                "job_id": args.job_id,
                "family": "F4",
                "manifest_sha256": fixture["manifest_sha256"],
                "physical_gpu_index": 0,
                "gpu_uuid": "GPU-CPU-LIFECYCLE-NO-DEVICE",
                "guard_pid": os.getpid(),
                "lease_path": str(temp_root / "physical_gpu_0.lock"),
                "pre_snapshot": {"cpu_lifecycle_fixture": True},
            }
        )
        write_new(start_path, start)
        stdout_path.touch(exist_ok=False)
        stderr_path.touch(exist_ok=False)
        cache_job.mkdir(parents=True, exist_ok=False)
        for name in EXPECTED_CACHE_SUBDIRS:
            (cache_job / name).mkdir(exist_ok=False)
        lease_path = temp_root / "physical_gpu_0.lock"
        lease_path.touch(exist_ok=False)
        environment = dict(os.environ)
        environment.pop("LD_LIBRARY_PATH", None)
        environment.update(
            {
                "CUDA_VISIBLE_DEVICES": "GPU-CPU-LIFECYCLE-NO-DEVICE",
                "CMF_GPU_GUARD_PHYSICAL_INDEX": "0",
                "CMF_GPU_LEASE_PATH": str(lease_path),
                "CMF_F4_GUARD_START_RECEIPT": str(start_path),
                "CMF_F4_CPU_LIFECYCLE_PREFLIGHT": "1",
                "PYTHONPATH": str(PROJECT),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        runner = Path(fixture["runner_script_path"])
        command = [
            str(ENV_PYTHON),
            str(runner),
            "--manifest",
            str(fixture_path),
            "--job-id",
            args.job_id,
            "--preflight-runner-entry",
            "--allow-lifecycle-fixture",
        ]
        completed = subprocess.run(
            command,
            cwd=str(PROJECT),
            env=environment,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if completed.returncode != 0 or len(lines) != 1:
            raise RuntimeError(
                "F4 V2 runner-entry subprocess failed: " + completed.stderr[-2000:]
            )
        runner_receipt = json.loads(lines[0])
        if runner_receipt.get("pass") is not True:
            raise RuntimeError("F4 V2 runner-entry receipt did not pass")
        subprocess_receipt = {
            "command": command,
            "returncode": completed.returncode,
            "stderr": completed.stderr,
        }
        require_runner_preflight_side_effect_free(runner_receipt, output)
        historical = historical_regression_checks(fixture, runner_receipt)
        if historical["pass"] is not True:
            raise RuntimeError(f"F4 historical regression failed: {historical['checks']}")

        def validate_changed(changer):
            changed = deepcopy(fixture)
            changer(changed)
            changed = hashed_manifest(changed)
            path = temp_root / f"negative_{len(observed):02d}.json"
            write_new(path, changed)
            return load_and_validate_manifest_job(
                path,
                args.job_id,
                phase=RUNNER_ENTRY,
                require_execution_authorized=False,
                allow_lifecycle_fixture=True,
                environment=environment,
            )

        expect_failure(
            "guard_directory_missing_at_runner_entry",
            lambda: validate_changed(
                lambda value: value.update(
                    {"guard_directory": str(temp_root / "missing_guard")}
                )
            ),
            observed,
        )
        expect_failure(
            "cache_job_missing_at_runner_entry",
            lambda: validate_changed(
                lambda value: value.update(
                    {"cache_directory": str(temp_root / "missing_cache")}
                )
            ),
            observed,
        )

        valid_start = json.loads(start_path.read_text(encoding="utf-8"))

        def bad_start(field, replacement):
            start_path.unlink()
            changed = deepcopy(valid_start)
            changed[field] = replacement
            changed = hashed_receipt(changed)
            write_new(start_path, changed)
            try:
                load_and_validate_manifest_job(
                    fixture_path,
                    args.job_id,
                    phase=RUNNER_ENTRY,
                    require_execution_authorized=False,
                    allow_lifecycle_fixture=True,
                    environment=environment,
                )
            finally:
                start_path.unlink()
                write_new(start_path, valid_start)

        expect_failure(
            "start_receipt_manifest_hash_wrong",
            lambda: bad_start("manifest_sha256", "0" * 64),
            observed,
        )
        expect_failure(
            "start_receipt_job_id_wrong",
            lambda: bad_start("job_id", "wrong-job"),
            observed,
        )

        output.mkdir(exist_ok=False)
        expect_failure(
            "existing_output",
            lambda: load_and_validate_manifest_job(
                fixture_path,
                args.job_id,
                phase=RUNNER_ENTRY,
                require_execution_authorized=False,
                allow_lifecycle_fixture=True,
                environment=environment,
            ),
            observed,
        )
        output.rmdir()

        expect_failure(
            "wrong_asset_map",
            lambda: validate_changed(
                lambda value: value["asset_hashes_by_family"]["F4"].update(
                    {next(iter(value["asset_hashes_by_family"]["F4"])): "0" * 64}
                )
            ),
            observed,
        )
        expect_failure(
            "wrong_candidate",
            lambda: validate_changed(
                lambda value: value["jobs"][0].update({"candidate_id": "wrong"})
            ),
            observed,
        )
        expect_failure(
            "wrong_program_order",
            lambda: validate_changed(
                lambda value: value["jobs"][0].update(
                    {"program_order": ["F4-ABC", "F4-BAC", "F4-ACB"]}
                )
            ),
            observed,
        )
        expect_failure(
            "wrong_budget",
            lambda: validate_changed(
                lambda value: value["jobs"][0].update({"maximum_fresh_scenes": 8})
            ),
            observed,
        )
        expect_failure(
            "wrong_source_hash",
            lambda: validate_changed(
                lambda value: value.update({"implementation_source_sha256": "0" * 64})
            ),
            observed,
        )
        expect_failure(
            "wrong_planner_terminal",
            lambda: validate_changed(
                lambda value: value["jobs"][0]["source_planner_terminals"][
                    "F4-ABC"
                ].update({"file_sha256": "0" * 64})
            ),
            observed,
        )
        expect_failure(
            "unknown_third_reopen_flag",
            lambda: validate_changed(
                lambda value: value.update({"third_reopening_authorized": False})
            ),
            observed,
        )
        mutated_runner_receipt = deepcopy(runner_receipt)
        mutated_runner_receipt["scene_created"] = True
        expect_failure(
            "runner_preflight_unexpected_scene_or_gpu_or_output",
            lambda: require_runner_preflight_side_effect_free(
                mutated_runner_receipt, output
            ),
            observed,
        )
        if len(observed) != 13 or not all(item["rejected"] for item in observed):
            raise RuntimeError("F4 V2 negative lifecycle matrix incomplete")
    finally:
        shutil.rmtree(temp_root)
        cleanup_pass = not temp_root.exists()

    receipt = {
        "schema_version": "cmf_f4_development_root_runtime_v2_lifecycle_preflight_v1",
        "manifest_sha256": exact["manifest_sha256"],
        "job_id": args.job_id,
        "exact_prepublication_validation_pass": True,
        "guard_entry_validation_pass": True,
        "runner_entry_subprocess": subprocess_receipt,
        "runner_entry_receipt": runner_receipt,
        "negative_tests": observed,
        "negative_test_count": len(observed),
        "historical_regressions": historical,
        "temporary_paths_cleaned": cleanup_pass,
        "scene_created": False,
        "gpu_context_created": False,
        "nvidia_smi_called": False,
        "output_created": False,
        "authorization_consumed": False,
        "pass": runner_receipt is not None
        and runner_receipt.get("pass") is True
        and len(observed) == 13
        and cleanup_pass,
    }
    receipt["receipt_sha256"] = canonical_hash(receipt)
    write_new(args.receipt_out, receipt)
    print(json.dumps(receipt, sort_keys=True, ensure_ascii=False))
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
