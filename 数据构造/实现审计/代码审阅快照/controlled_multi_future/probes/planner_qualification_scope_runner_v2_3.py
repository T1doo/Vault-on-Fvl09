"""Exact child dispatcher for V2.3.1 planner wiring jobs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from ..canonical_artifact import canonical_hash_json, canonical_write_json
from ..planner_qualification_scene_bridges_v2_3_1 import (
    RUNNER_SYMBOLS,
    run_with_production_scene_bridge_v2_3_1,
)
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4
from .planner_qualification_authorization_v2_3_1 import (
    load,
    validate_consumption,
)


JOB_KINDS = frozenset({"F2_STAGE_A", "F3_STAGE_A", "F3_STAGE_B", "F4_PROGRAM"})


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _planner_pass(job_kind, terminal):
    return {
        "F2_STAGE_A": terminal.get("planner_qualified_for_physical_probe") is True,
        "F3_STAGE_A": terminal.get("stage_a_pass") is True,
        "F3_STAGE_B": terminal.get("stage_b_pass") is True,
        "F4_PROGRAM": terminal.get("robot_kinematic_table_world_planner_pass") is True,
    }[job_kind]


def dispatch_authorized_job_v2_3_1(authorization, *, output: Path):
    kind = authorization["job_kind"]
    if kind not in JOB_KINDS or authorization.get("runner_symbol") != RUNNER_SYMBOLS[kind]:
        raise RuntimeError("V2.3.1 dispatcher has no exact production runner")
    bridge = run_with_production_scene_bridge_v2_3_1(
        authorization, output_root=Path(output) / "scene_work"
    )
    terminal = bridge["terminal"]
    planner_pass = _planner_pass(kind, terminal)
    planner_count = (
        terminal.get("planner_query_accounting", {}).get("total_queries")
        if kind == "F4_PROGRAM"
        else terminal.get("planner_result", {}).get("planner_query_count")
    )
    if not isinstance(planner_count, int) or not 0 <= planner_count <= authorization["planner_query_limit"]:
        raise RuntimeError("V2.3.1 terminal planner query count is invalid")
    if terminal.get("physical_execution_count") != 0:
        raise RuntimeError("V2.3.1 planner job reported physical execution")
    if kind == "F3_STAGE_A":
        canonical_write_json(output / "stage_a_spec.json", bridge["bridge_plan"]["runner_spec"], exclusive=True, mode=0o600)
        canonical_write_json(output / "stage_a_terminal.json", terminal, exclusive=True, mode=0o600)
    value = {
        "schema_version": "cmf_planner_qualification_dispatch_terminal_v2_3_1",
        "job_kind": kind,
        "runner_symbol": authorization["runner_symbol"],
        "bridge_plan_sha256": bridge["bridge_plan"]["bridge_plan_sha256"],
        "job_terminal": terminal,
        "job_terminal_receipt_sha256": terminal["receipt_sha256"],
        "cleanup": bridge["cleanup"],
        "planner_query_count": planner_count,
        "planner_pass": planner_pass,
        "failure_class": None if planner_pass else "PLANNER_CANDIDATE_FAIL",
        "scope_completed": True,
        "physical_execution_count": 0,
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = _load_json(args.authorization_receipt)
    scope = raw["approved_scopes"][0]
    authorization = load(
        args.authorization_receipt,
        requested_scope=scope,
        expected_output_namespace=raw["output_namespace"],
    )
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("V2.3.1 child lacks Guard environment")
    consumption = validate_consumption(_load_json(Path(consumption_path)), authorization)
    guard_receipt = _load_json(Path(guard_path))
    binding = guard_receipt["binding"]
    physical_index = int(binding["physical_gpu_index"])
    gpu_uuid = str(binding["expected_gpu_uuid"])
    guard = require_atomic_gpu_guard_v2_4(
        authorization,
        {**consumption, "path": consumption_path},
        expected_uuid=gpu_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    try:
        dispatch = dispatch_authorized_job_v2_3_1(authorization, output=output)
        status = "completed_pass" if dispatch["planner_pass"] else "completed_planner_candidate_fail"
        outer = {
            "schema_version": "cmf_planner_qualification_outer_terminal_v2_3_1",
            "implementation_version": authorization["implementation_version"],
            "authorization_id": authorization["authorization_id"],
            "authorization_receipt_sha256": authorization["receipt_sha256"],
            "consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
            "guard_binding": guard["binding"],
            "job_kind": authorization["job_kind"],
            "status": status,
            "failure_class": dispatch["failure_class"],
            "scope_completed": True,
            "dispatch": dispatch,
            "physical_execution_count": 0,
            "trajectory_count": 0,
            "formal_data": False,
            "stage1_authorized": False,
        }
    except BaseException as exc:
        outer = {
            "schema_version": "cmf_planner_qualification_outer_terminal_v2_3_1",
            "implementation_version": authorization["implementation_version"],
            "authorization_id": authorization["authorization_id"],
            "authorization_receipt_sha256": authorization["receipt_sha256"],
            "consumption_receipt_sha256": consumption["consumption_receipt_sha256"],
            "guard_binding": guard["binding"],
            "job_kind": authorization["job_kind"],
            "status": "failed_infrastructure",
            "failure_class": "INFRASTRUCTURE_ERROR",
            "scope_completed": False,
            "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
            "physical_execution_count": 0,
            "trajectory_count": 0,
            "formal_data": False,
            "stage1_authorized": False,
        }
    outer["receipt_sha256"] = canonical_hash_json(outer)
    canonical_write_json(output / "receipt.json", outer, exclusive=True, mode=0o600)
    return 0 if outer["scope_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
