"""Authoritative CPU-only lock and registry for the F2/F3/F4 repair."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f3_final_pose_search_v3 import build_f3_final_pose_recipe_universe_v3
from .f4_stage_b_geometry_contract_v2 import legacy_r01_invalidation_v2


SCHEMA_VERSION = "cmf_high_level_generation_repair_v2"
IMPLEMENTATION_VERSION = "controlled_multi_future_high_level_generation_repair_v2_0"


class GenerationRepairExecutionDisabled(ValueError):
    pass


def build_generation_repair_contract_v2() -> dict[str, Any]:
    f3 = build_f3_final_pose_recipe_universe_v3()
    f4 = legacy_r01_invalidation_v2()
    value = {
        "schema_version": SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "scientific_design_version": "controlled_multi_future_f1_f4_v1_2",
        "scope": "F2_F3_F4_CPU_CODE_GENERATION_REPAIR_ONLY",
        "old_terminal_scope_rerun_authorized": False,
        "planner_execution_authorized": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_360_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
        "legacy_terminals": {
            "F2": {
                "receipt_sha256": "1ef7da4cae5a5766c55828f1e06b008ad9f842fd5736de024bbc60c5ccf1a376",
                "corrected_status": "SEARCH_DESIGN_INCOMPLETE",
            },
            "F3": {
                "receipt_sha256": "acf74d004190a37830719d79f5c406b261ec446e0da9bf3a711ffadc12e8e5c7",
                "corrected_status": "TARGET_MUTATED_AFTER_PLANNER_QUALIFICATION_SEARCH_DESIGN_INCOMPLETE",
            },
            "F4": {
                "physical_terminal_sha256": "9381b47bac3270c294ef674fe07479bd7a0710ff065691dd09e01d8872da2ccc",
                "stage_b_selection_sha256": "93310c04143895e831e8976912ec2a6a0028c14d6027129b261920b6fbaf8025",
                "corrected_status": f4["status"],
                "invalidation_receipt_sha256": f4["receipt_sha256"],
            },
        },
        "new_cpu_contracts": {
            "F2": "cmf_f2_inside_control_search_v2",
            "F3": {
                "schema_version": f3["schema_version"],
                "recipe_count": f3["recipe_count"],
                "universe_sha256": f3["universe_sha256"],
            },
            "F4": "cmf_f4_stage_b_geometry_contract_v2",
        },
        "next_authorizable_action": (
            "a separate reviewed planner design and finite attempt budget after "
            "CPU source/snapshot freeze; not authorized by this contract"
        ),
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


def validate_generation_repair_contract_v2(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    expected = build_generation_repair_contract_v2()
    if canonical_jsonable(value) != expected:
        raise ValueError("generation repair V2 contract changed")
    return expected


def assert_high_level_gpu_issuance_disabled_v2() -> None:
    raise GenerationRepairExecutionDisabled(
        "F2/F3/F4 generation repair V2 is CPU/code-only; planner/GPU/physical "
        "authorization requires a separate reviewed design and budget"
    )


__all__ = [
    "GenerationRepairExecutionDisabled",
    "assert_high_level_gpu_issuance_disabled_v2",
    "build_generation_repair_contract_v2",
    "validate_generation_repair_contract_v2",
]
