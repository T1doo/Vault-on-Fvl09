"""V2.3.1a manifest bundle with the F4 query-accounting correction."""

from __future__ import annotations

from typing import Any

from .canonical_artifact import canonical_hash_json
from .planner_qualification_manifests_v2_3 import (
    build_f2_planner_panel_manifest_v1,
    build_f3_stage_a_panel_manifest_v1,
    build_f3_stage_b_selection_policy_v1,
    build_f4_program_panel_manifest_v1_1,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_pre_smoke_hotfix_v2_3_1a"


def build_manifest_bundle_v2_3_1a() -> dict[str, Any]:
    f2 = build_f2_planner_panel_manifest_v1()
    f3a = build_f3_stage_a_panel_manifest_v1()
    f3b = build_f3_stage_b_selection_policy_v1(f3a)
    f4 = build_f4_program_panel_manifest_v1_1()
    value = {
        "schema_version": "cmf_planner_qualification_manifest_bundle_v2_3_1a",
        "implementation_version": IMPLEMENTATION_VERSION,
        "f2_panel_sha256": f2["panel_sha256"],
        "f3_stage_a_panel_sha256": f3a["panel_sha256"],
        "f3_stage_b_policy_sha256": f3b["policy_sha256"],
        "f4_panel_sha256": f4["panel_sha256"],
        "manifests": {
            "F2": f2,
            "F3_STAGE_A": f3a,
            "F3_STAGE_B": f3b,
            "F4": f4,
        },
        "f4_query_accounting_single_source": {
            "target_construction_query_limit_per_job": 12,
            "chain_query_limit_per_job": 30,
            "total_query_limit_per_job": 42,
            "maximum_panel_queries": 1008,
            "source_manifest_sha256": f4["panel_sha256"],
        },
        "physical_execution_authorized": False,
        "stage1_authorized": False,
    }
    value["bundle_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["IMPLEMENTATION_VERSION", "build_manifest_bundle_v2_3_1a"]
