"""Guard child dispatch for consolidation/template-convergence jobs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback
from typing import Any, Mapping

from ..canonical_artifact import canonical_hash_json, canonical_write_json
from ..f2_dynamic_development_scope_v3 import f2_dynamic_development_budget_v3
from ..f2_exact_replay_v1 import finalize_f2_exact_replay_v1
from ..f2_official_asset_compatibility_matrix_v3 import (
    validate_static_compatibility_matrix_v3,
)
from ..f2_dynamic_search_contract_v3 import validate_cpu_static_screening_v3
from .f2_dynamic_development_scope_runner_v3 import (
    F2DynamicThenDevelopmentRunnerV3,
)
from ..f3_grasp_qualification_runner_v1 import F3GraspQualificationRunnerV1
from ..f3_grasp_qualification_v1 import (
    build_f3_selected_grasp_contract_v1,
)
from ..f4_a_only_execution_qualification_v1 import (
    F4AOnlyExecutionQualificationV1,
)
from ..f4_template_qualification_runner_v1 import (
    F4TemplateQualificationRunnerV1,
)
from ..real_sapien_adapter_f3_grasp_qualification_v1 import (
    RoboTwinRealSapienF3GraspQualificationV1Adapter,
)
from ..real_sapien_adapter_f4_template_qualification_v1 import (
    RoboTwinRealSapienF4TemplateQualificationV1Adapter,
)
from ..root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2
from .development_consolidation_authorization_v1 import (
    IMPLEMENTATION_VERSION,
    load,
    load_consumption,
)
from .gpu_guard_v2_4 import require_atomic_gpu_guard_v2_4


AUDIT = Path("/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计")
F2_MATRIX = AUDIT / "F2_OFFICIAL_ASSET_COMPATIBILITY_MATRIX_V3.json"
F2_SCREENING = AUDIT / "F2_CPU_STATIC_SCREENING_V3.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _adapter_f3(authorization, output):
    candidate = authorization["planned_root_slot_spec"]["selected_grasp_candidate"]
    return RoboTwinRealSapienF3GraspQualificationV1Adapter(
        family="F3",
        output_root=output,
        expected_implementation_source_sha256=authorization[
            "implementation_source_sha256"
        ],
        selected_grasp_candidate=candidate,
    )


def _adapter_f4(authorization, output):
    return RoboTwinRealSapienF4TemplateQualificationV1Adapter(
        family="F4",
        output_root=output,
        expected_implementation_source_sha256=authorization[
            "implementation_source_sha256"
        ],
    )


def _run_f2(authorization, work):
    matrix = validate_static_compatibility_matrix_v3(_load_json(F2_MATRIX))
    screening = validate_cpu_static_screening_v3(_load_json(F2_SCREENING))
    compatibility_authorization = {
        **authorization,
        "matrix_sha256": matrix["matrix_sha256"],
        "screening_sha256": screening["screening_sha256"],
        "budget": f2_dynamic_development_budget_v3(),
    }
    result = F2DynamicThenDevelopmentRunnerV3(
        matrix=matrix,
        screening=screening,
        authorization=compatibility_authorization,
        expected_source_sha256=authorization["implementation_source_sha256"],
        output_dir=work,
    ).run()
    terminal = finalize_f2_exact_replay_v1(result)
    return {
        "result": result,
        "terminal": terminal,
        "scope_completed": True,
        "pass": terminal["status"] == "PASS_TEMPLATE",
    }


def _run_f3_planner_screen(authorization, work):
    adapter = _adapter_f3(authorization, work / "scene_work")
    result = F3GraspQualificationRunnerV1(adapter).planner_screen(
        output_dir=work / "planner_screen",
        planned_root_slot_spec=authorization["planned_root_slot_spec"],
    )
    return {
        "result": result,
        "scope_completed": result["status"] == "planner_screen_completed",
        "pass": result["pass"],
    }


def _run_f3_physical(authorization, work):
    adapter = _adapter_f3(authorization, work / "scene_work")
    candidate = authorization["planned_root_slot_spec"]["selected_grasp_candidate"]
    result = F3GraspQualificationRunnerV1(adapter).physical_candidate(
        output_dir=work / "physical_candidate",
        planned_root_slot_spec=authorization["planned_root_slot_spec"],
        candidate=candidate,
    )
    return {"result": result, "scope_completed": True, "pass": result["pass"]}


def _run_f3_confirmation(authorization, work):
    adapter = _adapter_f3(authorization, work / "scene_work")
    candidate = authorization["planned_root_slot_spec"]["selected_grasp_candidate"]
    runner = F3GraspQualificationRunnerV1(adapter)
    contexts = []
    for index in range(3):
        contexts.append(
            runner.physical_candidate(
                output_dir=work / f"fresh_scene_{index + 1}",
                planned_root_slot_spec=authorization["planned_root_slot_spec"],
                candidate=candidate,
            )
        )
    checks = {
        "exact_three_fresh_scenes": len(contexts) == 3
        and len(
            {
                item.get("cleanup", {}).get("scene_instance_id") for item in contexts
            }
        )
        == 3,
        "same_candidate": all(
            item["candidate_sha256"] == candidate["candidate_sha256"]
            for item in contexts
        ),
        "all_three_pass": all(item["pass"] is True for item in contexts),
        "no_suffix_or_release": all(
            item["suffix_planner_query_count"] == 0
            and item["suffix_execution_count"] == 0
            and item["release_execution_count"] == 0
            for item in contexts
        ),
    }
    result = {
        "schema_version": "cmf_f3_three_scene_confirmation_terminal_v1",
        "selected_grasp_contract": build_f3_selected_grasp_contract_v1(candidate),
        "contexts": contexts,
        "checks": checks,
        "pass": all(checks.values()),
    }
    result["receipt_sha256"] = canonical_hash_json(result)
    canonical_write_json(work / "three_scene_confirmation.json", result, mode=0o600)
    return {"result": result, "scope_completed": True, "pass": result["pass"]}


def _run_full_root(authorization, work, *, family):
    adapter = (
        _adapter_f3(authorization, work / "scene_work")
        if family == "F3"
        else _adapter_f4(authorization, work / "scene_work")
    )
    programs = (
        ["F3-VVHH", "F3-VHVH", "F3-VHHV"]
        if family == "F3"
        else ["F4-ABC", "F4-ACB", "F4-BAC"]
    )
    realization = {
        program: {
            "realization": "r_pc",
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
        }
        for program in programs
    }
    result = RealSapienStrictPrefixRootOrchestratorV1_2(
        adapter, implementation_version=IMPLEMENTATION_VERSION
    ).run_nonformal_root(
        output_dir=work / "development_root",
        planned_root_slot_spec=authorization["planned_root_slot_spec"],
        realization_spec_by_program=realization,
        stage0_data=False,
        stage0_authorized=False,
        development_video_required=True,
    )
    return {
        "result": result,
        "scope_completed": True,
        "pass": result.get("status") == "accepted",
    }


def _run_f4_template(authorization, work):
    adapter = _adapter_f4(authorization, work / "scene_work")
    result = F4TemplateQualificationRunnerV1(adapter).run_candidate(
        output_dir=work / "template_candidate",
        planned_root_slot_spec=authorization["planned_root_slot_spec"],
    )
    infrastructure = result["status"] == "template_candidate_failed_infrastructure"
    return {
        "result": result,
        "scope_completed": not infrastructure,
        "pass": result["pass"],
    }


def _run_f4_a_only(authorization, work):
    source = Path(authorization.get("job_inputs", {}).get("planner_only_output_dir", ""))
    adapter = _adapter_f4(authorization, work / "scene_work")
    result = F4AOnlyExecutionQualificationV1(adapter).run(
        output_dir=work / "a_only",
        planned_root_slot_spec=authorization["planned_root_slot_spec"],
        planner_only_output_dir=source,
    )
    return {"result": result, "scope_completed": True, "pass": result["pass"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = _load_json(args.authorization_receipt)
    scope = raw["approved_scopes"][0]
    authorization = load(args.authorization_receipt, requested_scope=scope)
    consumption_path = os.environ.get("CMF_AUTHORIZATION_CONSUMPTION_RECEIPT")
    guard_path = os.environ.get("CMF_GPU_GUARD_RECEIPT")
    if not consumption_path or not guard_path:
        raise PermissionError("consolidation child lacks Guard binding")
    consumption = load_consumption(Path(consumption_path), authorization)
    guard_receipt = _load_json(Path(guard_path))
    binding = guard_receipt["binding"]
    physical_index = int(binding["physical_gpu_index"])
    gpu_uuid = str(binding["expected_gpu_uuid"])
    if os.environ.get("CUDA_VISIBLE_DEVICES") != gpu_uuid:
        raise RuntimeError("consolidation child GPU UUID mismatch")
    guard = require_atomic_gpu_guard_v2_4(
        authorization,
        consumption,
        expected_uuid=gpu_uuid,
        physical_index=physical_index,
    )
    output = Path(authorization["output_namespace"])
    output.mkdir(parents=True, exist_ok=False)
    outer = {
        "schema_version": "cmf_development_consolidation_job_outer_v1",
        "implementation_version": IMPLEMENTATION_VERSION,
        "authorization_id": authorization["authorization_id"],
        "authorization_receipt_sha256": authorization["receipt_sha256"],
        "authorization_consumption_receipt_sha256": consumption[
            "consumption_receipt_sha256"
        ],
        "job_kind": authorization["job_kind"],
        "family": authorization["family"],
        "scope": scope,
        "guard_binding": guard["binding"],
        "guard_precheck": guard["precheck"],
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "scope_completed": False,
        "pass": False,
        "status": "running",
        "result": None,
    }
    canonical_write_json(output / "receipt.json", outer, mode=0o600)
    try:
        work = output / "work"
        dispatch = {
            "F2_EXACT_REPLAY": lambda: _run_f2(authorization, work),
            "F3_PLANNER_SCREEN": lambda: _run_f3_planner_screen(authorization, work),
            "F3_PHYSICAL_CANDIDATE": lambda: _run_f3_physical(authorization, work),
            "F3_THREE_SCENE_CONFIRMATION": lambda: _run_f3_confirmation(
                authorization, work
            ),
            "F3_FULL_ROOT": lambda: _run_full_root(
                authorization, work, family="F3"
            ),
            "F4_TEMPLATE_CANDIDATE": lambda: _run_f4_template(
                authorization, work
            ),
            "F4_A_ONLY": lambda: _run_f4_a_only(authorization, work),
            "F4_FULL_ROOT": lambda: _run_full_root(
                authorization, work, family="F4"
            ),
        }[authorization["job_kind"]]()
        outer["result"] = dispatch["result"]
        outer["scope_completed"] = dispatch["scope_completed"]
        outer["pass"] = dispatch["pass"]
        outer["status"] = (
            "completed_pass"
            if outer["pass"]
            else "completed_with_failure_evidence"
            if outer["scope_completed"]
            else "failed_infrastructure"
        )
    except BaseException as exc:
        outer["status"] = "failed_infrastructure"
        outer["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    outer["receipt_sha256"] = canonical_hash_json(outer)
    canonical_write_json(output / "receipt.json", outer, mode=0o600)
    return 0 if outer["scope_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
