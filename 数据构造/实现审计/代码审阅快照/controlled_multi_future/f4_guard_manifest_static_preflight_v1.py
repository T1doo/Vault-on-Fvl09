"""CPU-only structural preflight for a proposed F4 Guard manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import canonical_hash_json, canonical_jsonable


SCHEMA_VERSION = "cmf_f4_guard_manifest_static_preflight_v1"
REQUIRED_TOP_LEVEL = frozenset(
    {
        "status",
        "approved",
        "source_freeze_vault_head",
        "implementation_source_sha256",
        "robotwin_tracked_head",
        "guard_script_path",
        "guard_script_sha256",
        "runner_script_path",
        "runner_script_sha256",
        "asset_hashes_by_family",
        "allowed_physical_gpu_indices",
        "jobs",
        "stage0_reopened",
        "stage1_authorized",
        "formal_360_authorized",
        "training_authorized",
        "h_reveal_authorized",
        "compression_authorized",
        "pi05_authorized",
        "manifest_sha256",
    }
)
REQUIRED_JOB = frozenset(
    {
        "job_id",
        "family",
        "mode",
        "output_namespace",
        "maximum_root_invocations",
        "maximum_canonical_prefix_generations",
        "maximum_exact_prefix_replays",
        "maximum_suffix_preflights",
        "maximum_branch_executions",
        "maximum_planner_queries",
        "maximum_fresh_scenes",
        "maximum_robot_action_scenes",
        "maximum_debug_videos",
        "maximum_raw_trajectories",
        "maximum_accepted_development_roots",
        "maximum_accepted_development_trajectories",
        "maximum_formal_trajectories",
        "automatic_retry",
        "fallback_allowed",
        "second_replacement_allowed",
    }
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_f4_guard_manifest_static_v1(
    manifest: Mapping[str, Any],
    *,
    workspace_root: Path,
    project_root: Path,
) -> dict[str, Any]:
    value = canonical_jsonable(manifest)
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    jobs = value.get("jobs")
    job = jobs[0] if isinstance(jobs, list) and len(jobs) == 1 else {}
    assets = value.get("asset_hashes_by_family", {}).get("F4", {})
    workspace = Path(workspace_root).resolve()
    project = Path(project_root).resolve()

    def bound_file(path_key: str, hash_key: str) -> bool:
        try:
            path = Path(value[path_key]).resolve()
            return (
                str(path).startswith(str(workspace) + "/")
                and path.is_file()
                and _file_sha(path) == value[hash_key]
            )
        except (KeyError, OSError, TypeError, ValueError):
            return False

    asset_checks = {}
    if isinstance(assets, Mapping):
        for relative, expected in assets.items():
            path = project / str(relative)
            asset_checks[str(relative)] = (
                path.is_file() and _file_sha(path) == expected
            )
    output = Path(job.get("output_namespace", workspace)).resolve()
    checks = {
        "all_guard_top_level_inputs_present": REQUIRED_TOP_LEVEL <= set(value),
        "self_hash_valid": digest == canonical_hash_json(payload),
        "proposal_not_authorized": value.get("approved") is False,
        "exact_gpu_scope": value.get("allowed_physical_gpu_indices")
        == list(range(8)),
        "exactly_one_f4_job": isinstance(jobs, list)
        and len(jobs) == 1
        and job.get("family") == "F4",
        "all_job_budget_fields_present": REQUIRED_JOB <= set(job),
        "exact_reviewed_caps": {
            key: job.get(key)
            for key in (
                "maximum_root_invocations",
                "maximum_canonical_prefix_generations",
                "maximum_exact_prefix_replays",
                "maximum_suffix_preflights",
                "maximum_branch_executions",
                "maximum_planner_queries",
                "maximum_fresh_scenes",
                "maximum_robot_action_scenes",
                "maximum_debug_videos",
                "maximum_raw_trajectories",
                "maximum_accepted_development_roots",
                "maximum_accepted_development_trajectories",
                "maximum_formal_trajectories",
            )
        }
        == {
            "maximum_root_invocations": 1,
            "maximum_canonical_prefix_generations": 1,
            "maximum_exact_prefix_replays": 3,
            "maximum_suffix_preflights": 3,
            "maximum_branch_executions": 3,
            "maximum_planner_queries": 136,
            "maximum_fresh_scenes": 8,
            "maximum_robot_action_scenes": 4,
            "maximum_debug_videos": 3,
            "maximum_raw_trajectories": 3,
            "maximum_accepted_development_roots": 1,
            "maximum_accepted_development_trajectories": 3,
            "maximum_formal_trajectories": 0,
        },
        "no_retry_fallback_or_second_replacement": job.get("automatic_retry")
        is False
        and job.get("fallback_allowed") is False
        and job.get("second_replacement_allowed") is False,
        "guard_file_hash_bound": bound_file(
            "guard_script_path", "guard_script_sha256"
        ),
        "runner_file_hash_bound": bound_file(
            "runner_script_path", "runner_script_sha256"
        ),
        "f4_asset_map_nonempty": isinstance(assets, Mapping) and bool(assets),
        "all_f4_assets_exist_and_match": bool(asset_checks)
        and all(asset_checks.values()),
        "new_output_namespace": str(output).startswith(str(workspace) + "/")
        and not output.exists(),
        "later_stages_forbidden": all(
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
        "schema_version": SCHEMA_VERSION,
        "manifest_sha256": digest,
        "checks": checks,
        "asset_checks": asset_checks,
        "pass": all(checks.values()),
        "executable": False,
        "gpu_initialized": False,
    }
    result["validation_sha256"] = canonical_hash_json(result)
    return result


def reject_f4_proposal_execution_v1(manifest: Mapping[str, Any]) -> None:
    if manifest.get("approved") is not False:
        raise ValueError("F4 proposal rejection requires approved=false")
    raise PermissionError("F4 Guard-complete proposal is not an execution authorization")


__all__ = [
    "REQUIRED_JOB",
    "REQUIRED_TOP_LEVEL",
    "SCHEMA_VERSION",
    "audit_f4_guard_manifest_static_v1",
    "reject_f4_proposal_execution_v1",
]

