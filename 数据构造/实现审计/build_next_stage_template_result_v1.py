"""Audit completed V1.3 family jobs and publish the unified result/handoff."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.development_video_capture_v1 import (
    validate_development_trajectory_mp4_receipt_v1,
)
from controlled_multi_future.raw_writer import verify_raw_artifact_integrity


ROOT = Path("/nfs_share/lijunhui")
AUDIT = ROOT / "Vault-on-Fvl09/数据构造/实现审计"
F1 = ROOT / "Robotwin2/datasets/controlled_multi_future_post_stage0_f1_batch_pilot_v1/post_stage0_f1_batch_pilot_v1_run4"
F2 = ROOT / "Robotwin2/datasets/controlled_multi_future_post_stage0_f2_asset_redesign_v3/post_stage0_f2_asset_redesign_dynamic_v3_run2"
F3 = ROOT / "Robotwin2/datasets/controlled_multi_future_post_stage0_f3_v2_1/closure_v1_f3_common_grasp_prefix_v2_1_seed20260829_run4"
F4 = ROOT / "Robotwin2/datasets/controlled_multi_future_post_stage0_f4_selected_layout_v2/f4_selected_layout_v2_c01_planner_only_seed20260829_run4"
GUARDS = {
    "F1": AUDIT / "gpu_guards/controlled_multi_future_post_stage0_f1_batch_pilot_v1/post_stage0_f1_batch_pilot_v1_run4.guard.json",
    "F2": AUDIT / "gpu_guards/controlled_multi_future_post_stage0_f2_asset_redesign_v3/post_stage0_f2_asset_redesign_dynamic_v3_run2.guard.json",
    "F3": AUDIT / "gpu_guards/controlled_multi_future_post_stage0_f3_v2_1/closure_v1_f3_common_grasp_prefix_v2_1_seed20260829_run4.guard.json",
    "F4": AUDIT / "gpu_guards/controlled_multi_future_post_stage0_f4_selected_layout_v2/f4_selected_layout_v2_c01_planner_only_seed20260829_run4.guard.json",
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def self_hash(value, field):
    payload = dict(value)
    claimed = payload.pop(field, None)
    return isinstance(claimed, str) and hash_json(payload) == claimed


def write_new(path: Path, data: bytes):
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path: Path, value):
    write_new(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
    )


def audit_guard(family):
    path = GUARDS[family]
    value = read(path)
    if not self_hash(value, "guard_receipt_sha256"):
        raise RuntimeError(f"{family} Guard self-hash failed")
    checks = {
        "terminal": value.get("status") in ("completed", "completed_child_failed"),
        "task_owned_cleanup": value.get("task_owned_cleanup_pass") is True,
        "orphan_zero": int(value.get("orphan_process_count", -1)) == 0,
        "gpu_release": value.get("gpu_returned_to_idle_baseline") is True
        and value.get("postcheck_release", {}).get("verified") is True,
        "source_lock": value.get("post_source_lock_pass") is True,
        "cache_cleanup": value.get("job_cache_cleanup", {}).get("succeeded") is True,
        "lease_release": value.get("gpu_lease_release", {}).get("released") is True,
    }
    if not all(checks.values()):
        raise RuntimeError(f"{family} Guard cleanup failed: {checks}")
    return {
        "path": str(path),
        "file_sha256": file_sha(path),
        "payload_sha256": value["guard_receipt_sha256"],
        "status": value["status"],
        "physical_gpu_index": value["binding"]["physical_gpu_index"],
        "expected_gpu_uuid": value["binding"]["expected_gpu_uuid"],
        "child_pid": value.get("child_pid"),
        "elapsed_seconds": value.get("elapsed_seconds"),
        "checks": checks,
    }


def audit_f1():
    scope_path = F1 / "batch/f1_batch_scope_receipt.json"
    scope = read(scope_path)
    if not self_hash(scope, "receipt_sha256") or scope.get("pass") is not True:
        raise RuntimeError("F1 scope receipt failed")
    finalizer = scope["finalizer"]
    if not self_hash(finalizer, "report_sha256") or finalizer.get("pass") is not True:
        raise RuntimeError("F1 finalizer failed")
    root_dirs = sorted((F1 / "batch/root_attempts").glob("f1-batch-pilot-v1-primary-*"))
    roots = []
    branches = []
    raw_bytes = 0
    mp4_bytes = 0
    reference_currents = set()
    layout_hashes = set()
    display_hashes = set()
    for root_dir in root_dirs:
        root_receipt_path = root_dir / "f1_batch_pilot_root_receipt.json"
        root_receipt = read(root_receipt_path)
        if not self_hash(root_receipt, "receipt_sha256"):
            raise RuntimeError(f"F1 root receipt hash failed: {root_dir.name}")
        if root_receipt.get("pass") is not True or root_receipt.get("accepted_development_root") is not True:
            raise RuntimeError(f"F1 root not accepted: {root_dir.name}")
        planned = read(root_dir / "root/planned_root_slot_spec.json")
        layout_hashes.add(planned["scene_layout_sha256"])
        display_hashes.add(planned["candidate_display_order_sha256"])
        current = read(root_dir / "root/reference_current_hashes.json")
        reference_currents.add(current["aggregate_sha256"])
        roots.append({
            "root_id": root_dir.name,
            "receipt_file_sha256": file_sha(root_receipt_path),
            "receipt_payload_sha256": root_receipt["receipt_sha256"],
            "elapsed_seconds": root_receipt["elapsed_seconds"],
            "planner_query_count": root_receipt["budget_counts"]["planner_query_count"],
            "trajectory_count": root_receipt["trajectory_count"],
        })
        for branch_path in sorted((root_dir / "root/branches").glob("*/receipt.json")):
            branch = read(branch_path)
            raw_dir = branch_path.parent / "raw"
            raw = verify_raw_artifact_integrity(raw_dir)
            if raw.get("pass") is not True:
                raise RuntimeError(f"raw integrity failed: {raw_dir}")
            manifest = raw["manifest"]
            labels = manifest.get("formal_data") is False and manifest.get("stage0_data") is False and manifest.get("stage0_authorized") is False
            video = validate_development_trajectory_mp4_receipt_v1(
                branch["development_video_receipt"],
                expected_path=branch_path.parent / "video/trajectory.mp4",
            )
            checks = {
                "accepted": branch.get("status") == "accepted",
                "verifier": branch.get("verifier", {}).get("pass") is True,
                "raw": raw["pass"] is True,
                "raw_labels": labels,
                "video": video["pass"] is True,
                "same_current": branch.get("branch_current", {}).get("aggregate_sha256") == current["aggregate_sha256"],
                "anchor": branch.get("anchor_equivalence", {}).get("equivalent") is True,
            }
            if not all(checks.values()):
                raise RuntimeError(f"F1 branch audit failed: {branch_path}: {checks}")
            raw_path = raw_dir / "raw_streams.npz"
            video_path = branch_path.parent / "video/trajectory.mp4"
            raw_bytes += raw_path.stat().st_size
            mp4_bytes += video_path.stat().st_size
            branches.append({
                "root_id": root_dir.name,
                "program_id": branch["program_id"],
                "receipt_file_sha256": file_sha(branch_path),
                "raw_file_sha256": manifest["raw_streams_npz_sha256"],
                "raw_bytes": raw_path.stat().st_size,
                "mp4_file_sha256": branch["development_video_receipt"]["file_sha256"],
                "mp4_bytes": video_path.stat().st_size,
                "checks": checks,
            })
    checks = {
        "five_roots": len(roots) == 5,
        "fifteen_branches": len(branches) == 15,
        "five_unique_currents": len(reference_currents) == 5,
        "five_layout_rotations": len(layout_hashes) == 5,
        "five_display_rotations": len(display_hashes) == 5,
        "no_reserve": scope.get("reserve_activations") == [],
        "budget": scope.get("budget_validation", {}).get("pass") is True,
        "finalizer": finalizer.get("status") == "COMPLETED_FIVE_ACCEPTED_ROOTS"
        and finalizer.get("accepted_root_count") == 5
        and finalizer.get("accepted_trajectory_count") == 15
        and finalizer.get("root_success_rate") == 1.0,
    }
    if not all(checks.values()):
        raise RuntimeError(f"F1 aggregate audit failed: {checks}")
    return {
        "status": "COMPLETED_FIVE_ACCEPTED_ROOTS",
        "pass": True,
        "scope_receipt_path": str(scope_path),
        "scope_receipt_file_sha256": file_sha(scope_path),
        "scope_receipt_payload_sha256": scope["receipt_sha256"],
        "finalizer_report_sha256": finalizer["report_sha256"],
        "accepted_root_count": 5,
        "accepted_trajectory_count": 15,
        "root_success_rate": 1.0,
        "reserve_activation_count": 0,
        "budget_counts": scope["budget_validation"]["counts"],
        "raw_count": 15,
        "raw_total_bytes": raw_bytes,
        "mp4_count": 15,
        "mp4_total_bytes": mp4_bytes,
        "mean_root_elapsed_seconds": finalizer["mean_attempted_root_elapsed_seconds"],
        "roots": roots,
        "branches": branches,
        "checks": checks,
    }


def main():
    guards = {family: audit_guard(family) for family in ("F1", "F2", "F3", "F4")}
    f1 = audit_f1()
    f2_path = F2 / "receipt.json"
    f2 = read(f2_path)
    f3_path = F3 / "F3CommonGraspPrefixV2_1/receipt.json"
    f3 = read(f3_path)
    f4_path = F4 / "F4SelectedLayoutV2PlannerOnly/receipt.json"
    f4 = read(f4_path)
    if f2.get("status") != "failed_infrastructure" or f2.get("pass") is not False:
        raise RuntimeError("unexpected F2 terminal")
    if f3.get("status") != "failed_f3_common_grasp_prefix_v2_1_diagnostic" or f3.get("pass") is not False or not self_hash(f3, "receipt_sha256"):
        raise RuntimeError("unexpected F3 terminal")
    if f4.get("status") != "failed_f4_post_stage0_planner_only_v1" or f4.get("pass") is not False or not self_hash(f4, "receipt_sha256"):
        raise RuntimeError("unexpected F4 terminal")
    first_program = f4.get("program_receipts", [{}])[0]
    first_query = first_program.get("planner_receipt", {}).get("evidence", {}).get("planner_query_receipts", [{}])[0]
    result = {
        "schema_version": "cmf_next_stage_template_development_result_v1",
        "status": "COMPLETED_WITH_MIXED_TEMPLATE_EVIDENCE",
        "source_version": "V1.3",
        "implementation_source_sha256": "9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72",
        "F1": f1,
        "F2": {
            "status": f2["status"],
            "pass": False,
            "failure_type": f2["error"]["type"],
            "failure_message": f2["error"]["message"],
            "development_execution_count": 0,
            "physical_conclusion": None,
            "receipt_path": str(f2_path),
            "receipt_file_sha256": file_sha(f2_path),
            "next": "fix NumPy bool JSON normalization, rerun only under a new versioned scope",
        },
        "F3": {
            "status": f3["status"],
            "pass": False,
            "planner_query_count": f3["budget_counts"]["planner_query_count"],
            "prefix_execution_count": f3["budget_counts"]["execution_attempt_count"],
            "recovery_count": 0,
            "failure_message": f3["error"],
            "physical_conclusion": "F3CommonGraspPrefixV2_1 close=0.50 is not stable for the current bottle/grasp template",
            "receipt_path": str(f3_path),
            "receipt_file_sha256": file_sha(f3_path),
            "receipt_payload_sha256": f3["receipt_sha256"],
            "next": "task/asset/grasp redesign impact review",
        },
        "F4": {
            "status": "failed_selected_layout_no_fallback",
            "pass": False,
            "planner_query_count": f4["budget_counts"]["planner_query_count"],
            "prefix_execution_count": f4["budget_counts"]["canonical_prefix_reference_execution_count"],
            "suffix_execution_count": 0,
            "release_execution_count": 0,
            "first_failed_segment": first_query.get("source"),
            "first_planner_status": first_query.get("status"),
            "motiongen_status": first_query.get("motiongen_result_side_channel", [{}])[0].get("fields", {}).get("status"),
            "rendered_visibility_pass": False,
            "automatic_fallback_used": False,
            "receipt_path": str(f4_path),
            "receipt_file_sha256": file_sha(f4_path),
            "receipt_payload_sha256": f4["receipt_sha256"],
            "next": "higher-level task/layout/camera redesign; no temporary waypoint",
        },
        "guards": guards,
        "stage1_ready_families": ["F1"],
        "stage1_blocked_families": ["F2", "F3", "F4"],
        "canonical_stage1_authorized": False,
        "formal_data_authorized": False,
        "formal_trajectory_increment": 0,
        "training_authorized": False,
        "h_reveal_authorized": False,
        "compression_authorized": False,
        "pi05_authorized": False,
    }
    result["report_sha256"] = hash_json(result)
    write_json(AUDIT / "NEXT_STAGE_TEMPLATE_DEVELOPMENT_RESULT_V1.json", result)
    f1_report = dict(f1)
    f1_report["schema_version"] = "cmf_f1_batch_generation_pilot_v1_durable_report"
    f1_report["formal_data"] = False
    f1_report["stage0_data"] = False
    f1_report["stage1_authorized"] = False
    f1_report["formal_trajectory_increment"] = 0
    f1_report["report_sha256"] = hash_json(f1_report)
    write_json(AUDIT / "F1_BATCH_GENERATION_PILOT_V1_REPORT.json", f1_report)
    markdown = f"""# F1 batch-generation pilot V1 report

- Status: `COMPLETED_FIVE_ACCEPTED_ROOTS`
- Accepted roots: **5/5**
- Accepted development trajectories: **15/15**
- Root success rate: **100%**
- Raw: **15** ({f1['raw_total_bytes']} bytes)
- MP4: **15** ({f1['mp4_total_bytes']} bytes)
- Planner queries: **{f1['budget_counts']['planner_query_count']}**
- Executions: **{f1['budget_counts']['execution_attempt_count']}**
- Recovery: **0**
- Fresh scenes: **{f1['budget_counts']['fresh_scene_count']}**
- Reserve activations: **0**
- Mean root elapsed: **{f1['mean_root_elapsed_seconds']:.3f} s**
- Formal trajectory increment: **0**

All five roots use distinct current hashes, role-position rotations and candidate-display rotations. Every branch has raw, MP4 and passing verifier evidence. This is a development scale pilot, not formal-360 data and not canonical Stage 1 authorization.
"""
    write_new(AUDIT / "F1_BATCH_GENERATION_PILOT_V1_REPORT.md", markdown.encode())
    unified_md = f"""# Next-stage template development result V1

## Outcome

- F1: **PASS**, 5/5 roots and 15/15 development trajectories.
- F2: **infrastructure failure**, NumPy bool JSON serialization before development execution; no new physical conclusion.
- F3: **real physical failure**, close=0.50 did not maintain grasp/off-support state.
- F4: **planner failure**, c01 failed at A_pregrasp IK; no fallback.
- Stage-1-ready family: **F1 only**.
- Canonical Stage 1 remains unauthorized.

Report SHA: `{result['report_sha256']}`
"""
    write_new(AUDIT / "NEXT_STAGE_TEMPLATE_DEVELOPMENT_RESULT_V1.md", unified_md.encode())
    handoff = f"""# GPT review handoff — next-stage template result V1

```yaml
source: 9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72
stage0: STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE
stage0_reopened: false

F1:
  status: PASS
  roots: 5/5
  trajectories: 15/15 development r_pc
  raw: 15
  mp4: 15
  planner_queries: 230
  executions: 15
  recovery: 0
  reserve_activations: 0
  formal_increment: 0

F2:
  status: FAILED_INFRASTRUCTURE
  error: numpy.bool_ is not JSON serializable
  development_execution_count: 0
  physical_conclusion: null

F3:
  status: FAILED_PHYSICAL
  planner_queries: 7
  prefix_executions: 1
  failure: unstable grasp/contact and bottle still on pad/table

F4:
  status: FAILED_PLANNER_NO_FALLBACK
  prefix_executions: 1
  planner_queries: 11
  first_failed_segment: A_pregrasp
  motiongen_status: IK_FAIL
  rendered_visibility_pass: false

stage1_ready_families: [F1]
canonical_stage1_authorized: false
formal_data_authorized: false
training_authorized: false
h_reveal_authorized: false
compression_authorized: false
pi05_authorized: false
```

Interpretation: F1 has passed the requested scale-pilot test, but these 15 trajectories remain development data. F2 has no new physics result because it failed while serializing its first dynamic audit receipt. F3 now has genuine evidence that the current V2_1 grasp template is physically unstable. F4 c01 is rejected without fallback because the first A pregrasp endpoint is IK-infeasible and the visibility aggregate also fails. Full Stage 1 remains blocked by F2/F3/F4.

Machine report: `NEXT_STAGE_TEMPLATE_DEVELOPMENT_RESULT_V1.json` (`{result['report_sha256']}`).
"""
    write_new(AUDIT / "GPT_REVIEW_HANDOFF_NEXT_STAGE_TEMPLATE_V1.md", handoff.encode())
    print(json.dumps({
        "report_sha256": result["report_sha256"],
        "f1_report_sha256": f1_report["report_sha256"],
        "raw_count": 15,
        "mp4_count": 15,
        "raw_total_bytes": f1["raw_total_bytes"],
        "mp4_total_bytes": f1["mp4_total_bytes"],
    }, indent=2))


if __name__ == "__main__":
    main()
