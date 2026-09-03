"""Fail-closed proposal manifest for the next bounded F2/F3 Gate."""

from __future__ import annotations

from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable
from .f2_top_contact_pose_selection_v1_1 import (
    build_f2_top_contact_selection_proposal_v1_1,
)
from .f3_rotation1_candidate_proposal_v1 import (
    build_f3_rotation1_candidate_proposal_v1,
)


SCHEMA_VERSION = "cmf_post_recovery_next_gate_proposal_manifest_v1"
STATUS = "PROPOSAL_ONLY_NOT_AUTHORIZATION"


def build_next_gate_proposal_manifest_v1(
    *,
    source_freeze_vault_head: str,
    implementation_source_sha256: str,
    review_packet_sha256: str,
) -> dict[str, Any]:
    f2 = build_f2_top_contact_selection_proposal_v1_1()
    f3 = build_f3_rotation1_candidate_proposal_v1()
    value = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "approved": False,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "source_freeze_vault_head": str(source_freeze_vault_head),
        "implementation_source_sha256": str(implementation_source_sha256),
        "review_packet_sha256": str(review_packet_sha256),
        "allowed_physical_gpu_indices": list(range(8)),
        "one_job_per_gpu": True,
        "root_sharding": False,
        "jobs": [
            {
                "job_id": "f2-top-contact-selection-and-tracking-proposal",
                "family": "F2",
                "proposal_sha256": f2["proposal_sha256"],
                "planner_query_cap": 44,
                "selection_scene_cap": 4,
                "physical_scene_cap": 4,
                "physical_candidate_cap": 4,
                "debug_video_cap": 4,
                "accepted_trajectory_cap": 0,
                "formal_trajectory_cap": 0,
            },
            {
                "job_id": "f3-rotation1-lift-center-proposal",
                "family": "F3",
                "proposal_sha256": f3["proposal_sha256"],
                "planner_query_cap": 40,
                "planner_scene_cap": 8,
                "physical_candidate_cap": 4,
                "conditional_no_suffix_scene_cap": 3,
                "accepted_trajectory_cap": 0,
                "formal_trajectory_cap": 0,
            },
        ],
        "f4": {
            "job_present": False,
            "root_replacement_authorized": False,
            "decision_required": True,
        },
        "stage0_reopened": False,
        "stage1_authorized": False,
        "formal_360_authorized": False,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
    }
    value["manifest_sha256"] = canonical_hash_json(value)
    return value


def validate_next_gate_proposal_manifest_v1(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    value = canonical_jsonable(manifest)
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    expected_f2 = build_f2_top_contact_selection_proposal_v1_1()
    expected_f3 = build_f3_rotation1_candidate_proposal_v1()
    jobs = value.get("jobs")
    checks = {
        "schema": value.get("schema_version") == SCHEMA_VERSION,
        "self_hash": digest == canonical_hash_json(payload),
        "proposal_status": value.get("status") == STATUS,
        "approved_false": value.get("approved") is False,
        "gpu_authorized_false": value.get("gpu_execution_authorized") is False,
        "physical_authorized_false": value.get("physical_execution_authorized")
        is False,
        "exact_gpu_scope": value.get("allowed_physical_gpu_indices")
        == list(range(8)),
        "exact_job_families": isinstance(jobs, list)
        and [item.get("family") for item in jobs] == ["F2", "F3"],
        "f2_proposal_bound": isinstance(jobs, list)
        and len(jobs) == 2
        and jobs[0].get("proposal_sha256") == expected_f2["proposal_sha256"],
        "f3_proposal_bound": isinstance(jobs, list)
        and len(jobs) == 2
        and jobs[1].get("proposal_sha256") == expected_f3["proposal_sha256"],
        "f4_job_absent": value.get("f4", {}).get("job_present") is False
        and value.get("f4", {}).get("root_replacement_authorized") is False,
        "all_later_stages_forbidden": all(
            value.get(key) is False
            for key in (
                "stage0_reopened",
                "stage1_authorized",
                "formal_360_authorized",
                "training_authorized",
                "h_reveal_authorized",
                "compression_authorized",
                "pi05_authorized",
            )
        ),
    }
    result = {
        "schema_version": "cmf_post_recovery_next_gate_proposal_validation_v1",
        "manifest_sha256": digest,
        "checks": checks,
        "pass": all(checks.values()),
        "executable": False,
    }
    result["validation_sha256"] = canonical_hash_json(result)
    return result


def reject_proposal_execution_v1(manifest: Mapping[str, Any]) -> None:
    validation = validate_next_gate_proposal_manifest_v1(manifest)
    if validation["pass"] is not True:
        raise ValueError("next-Gate proposal manifest is invalid")
    raise PermissionError(
        "proposal manifest is intentionally non-executable; a new approved "
        "authorization artifact is required"
    )


__all__ = [
    "SCHEMA_VERSION",
    "STATUS",
    "build_next_gate_proposal_manifest_v1",
    "reject_proposal_execution_v1",
    "validate_next_gate_proposal_manifest_v1",
]
