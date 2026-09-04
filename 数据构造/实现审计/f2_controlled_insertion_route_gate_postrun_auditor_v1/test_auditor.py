#!/usr/bin/env python3
"""Pure-CPU synthetic tests for the read-only F2 post-run auditor."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

import auditor


def seal(value, key="receipt_sha256"):
    value = deepcopy(value)
    value.pop(key, None)
    value[key] = auditor.canonical_hash(value)
    return value


def snapshot(*, selected=2, selected_util=0, selected_memory=14, selected_pstate="P8"):
    rows = []
    for index, uuid in auditor.GPU_UUIDS.items():
        rows.append(
            {
                "index": index,
                "uuid": uuid,
                "memory_used_mib": selected_memory if index == selected else 14,
                "utilization_gpu_percent": selected_util if index == selected else 0,
                "pstate": selected_pstate if index == selected else "P8",
                "compute_processes": [],
            }
        )
    return {"captured_at": "2026-09-04T00:00:00+00:00", "gpus": rows}


def scene_cleanup(scene_id):
    return {
        "scene_created": True,
        "scene_cleanup_attempted": True,
        "scene_cleanup_succeeded": True,
        "cleanup_safety_pass": True,
        "cleanup_error": None,
        "orphan_process_count": 0,
        "activity_monitor_restoration_succeeded": True,
        "activity_monitor_restoration_error": None,
        "scene_instance_id": scene_id,
        "outer_gpu_release_audit_required": True,
    }


def planner_row(relation, segments, target_hash, scene_id):
    receipts = []
    previous = "start-qpos"
    for index, segment_id in enumerate(segments, start=1):
        end = f"{relation}-end-{index}"
        receipts.append(
            {
                "segment_id": segment_id,
                "start_qpos_sha256": previous,
                "end_qpos_sha256": end,
                "planner_status": "Success",
                "executed": False,
                "planner_query_receipt": {
                    "query_id": index,
                    "source": segment_id,
                    "status": "Success",
                },
            }
        )
        previous = end
    row = {
        "relation": relation,
        "planner_query_cap": len(segments),
        "planner_query_count": len(segments),
        "planner_pass": True,
        "state_restore_receipt": {
            "actual_prefix_end_qpos_sha256": auditor.EXPECTED_PREFIX_QPOS_SHA256,
            "target_segment_ids": list(segments),
            "targets_sha256": target_hash,
            "physical_action_executed": False,
            "gripper_opened": False,
        },
        "planner_reset_receipt": {"synthetic": True},
        "segment_receipts": receipts,
        "terminal_qpos_sha256": receipts[-1]["end_qpos_sha256"],
        "cleanup": scene_cleanup(scene_id),
        "physical_execution_count": 0,
    }
    return seal(row)


def valid_fixture():
    manifest = json.loads(auditor.EXPECTED_MANIFEST_PATH.read_text(encoding="utf-8"))
    inside = planner_row(
        "inside",
        auditor.INSIDE_SEGMENTS,
        auditor.EXPECTED_INSIDE_TARGETS_SHA256,
        "f2-inside-fresh-scene",
    )
    beside = planner_row(
        "beside",
        auditor.BESIDE_SEGMENTS,
        auditor.EXPECTED_BESIDE_TARGETS_SHA256,
        "f2-beside-fresh-scene",
    )
    result = {
        "schema_version": "cmf_f2_controlled_insertion_route_gate_result_v1",
        "gate_name": "F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1",
        "contract": {
            "selected_binding_sha256": auditor.EXPECTED_BINDING_SHA256,
            "actual_prefix_end_qpos_sha256": auditor.EXPECTED_PREFIX_QPOS_SHA256,
            "inside_targets_sha256": auditor.EXPECTED_INSIDE_TARGETS_SHA256,
            "beside_targets_sha256": auditor.EXPECTED_BESIDE_TARGETS_SHA256,
            "inside_target_segment_ids": list(auditor.INSIDE_SEGMENTS),
            "beside_target_segment_ids": list(auditor.BESIDE_SEGMENTS),
        },
        "planner_rows": [inside, beside],
        "planner_query_count": 11,
        "fresh_planner_scene_count": 2,
        "both_chains_pass": True,
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
    job_terminal = seal(
        {
            "schema_version": "cmf_f2_controlled_insertion_route_gate_terminal_v1",
            "manifest_sha256": auditor.EXPECTED_MANIFEST_SHA256,
            "job_id": auditor.EXPECTED_JOB_ID,
            "result": result,
            "error": None,
            "pass": True,
            "physical_execution_count": 0,
            "accepted_root_count": 0,
            "formal_trajectory_count": 0,
            "automatic_continuation": False,
            "formal_data": False,
            "stage1_authorized": False,
        }
    )
    pre = snapshot()
    launch = snapshot()
    post = snapshot()
    lease = (
        auditor.WORKSPACE
        / "Robotwin2/gpu_leases/production_micro_gate_v1/physical_gpu_2.lock"
    )
    guard_start = seal(
        {
            "schema_version": "cmf_production_micro_gate_guard_start_v1",
            "run_id": auditor.EXPECTED_RUN_ID,
            "job_id": auditor.EXPECTED_JOB_ID,
            "family": "F2",
            "manifest_sha256": auditor.EXPECTED_MANIFEST_SHA256,
            "physical_gpu_index": 2,
            "gpu_uuid": auditor.GPU_UUIDS[2],
            "guard_pid": 101,
            "pre_snapshot": pre,
            "lease_path": str(lease),
        }
    )
    guard_dir = Path(manifest["guard_directory"])
    guard_terminal = seal(
        {
            "schema_version": "cmf_production_micro_gate_guard_terminal_v1",
            "run_id": auditor.EXPECTED_RUN_ID,
            "job_id": auditor.EXPECTED_JOB_ID,
            "family": "F2",
            "manifest_sha256": auditor.EXPECTED_MANIFEST_SHA256,
            "physical_gpu_index": 2,
            "gpu_uuid": auditor.GPU_UUIDS[2],
            "guard_pid": 101,
            "child_pid": 102,
            "child_process_group": 102,
            "child_exit_code": 0,
            "timed_out": False,
            "interrupted": None,
            "pre_snapshot": pre,
            "launch_snapshot": launch,
            "post_snapshot": post,
            "post_release_poll_snapshots": [post],
            "cache_removed": True,
            "lease_released": True,
            "cleanup_errors": [],
            "gpu_returned_to_idle_baseline": True,
            "task_owned_cleanup_pass": True,
            "output_exists": True,
            "stdout_path": str(guard_dir / f"{auditor.EXPECTED_JOB_ID}.stdout.log"),
            "stderr_path": str(guard_dir / f"{auditor.EXPECTED_JOB_ID}.stderr.log"),
            "elapsed_seconds": 1.0,
            "status": "completed",
        }
    )
    return {
        "manifest": manifest,
        "job_start": {
            "manifest_sha256": auditor.EXPECTED_MANIFEST_SHA256,
            "job_id": auditor.EXPECTED_JOB_ID,
        },
        "job_terminal": job_terminal,
        "planner_receipts": {"inside": inside, "beside": beside},
        "guard_start": guard_start,
        "guard_terminal": guard_terminal,
        "path_state": {
            "manifest_file_sha256": auditor.EXPECTED_MANIFEST_FILE_SHA256,
            "runner_script_sha256": auditor.EXPECTED_RUNNER_SHA256,
            "guard_script_sha256": auditor.EXPECTED_GUARD_SHA256,
            "output_exists": True,
            "job_start_exists": True,
            "job_terminal_exists": True,
            "inside_planner_receipt_exists": True,
            "beside_planner_receipt_exists": True,
            "guard_start_exists": True,
            "guard_terminal_exists": True,
            "stdout_exists": True,
            "stderr_exists": True,
            "cache_job_exists": False,
            "forbidden_artifact_paths": [],
            "symlink_paths": [],
        },
    }


def reseal_job(fixture):
    rows = fixture["job_terminal"]["result"]["planner_rows"]
    fixture["planner_receipts"] = {
        row["relation"]: deepcopy(row) for row in rows
    }
    fixture["job_terminal"] = seal(fixture["job_terminal"])


def reseal_guard(fixture):
    fixture["guard_terminal"] = seal(fixture["guard_terminal"])


class PostrunAuditorTests(unittest.TestCase):
    def audit(self, fixture):
        return auditor.audit_documents(**fixture)

    def assert_rejected(self, fixture, expected_code):
        report = self.audit(fixture)
        self.assertFalse(report["pass"])
        self.assertEqual(report["failure"]["code"], expected_code)
        payload = dict(report)
        digest = payload.pop("receipt_sha256")
        self.assertEqual(digest, auditor.canonical_hash(payload))

    def test_valid_conjunction_passes(self):
        report = self.audit(valid_fixture())
        self.assertTrue(report["pass"])
        self.assertEqual(report["scientific_result"]["inside"], "5/5")
        self.assertEqual(report["scientific_result"]["beside"], "6/6")
        payload = dict(report)
        digest = payload.pop("receipt_sha256")
        self.assertEqual(digest, auditor.canonical_hash(payload))

    def test_zero_child_exit_does_not_hide_failed_job(self):
        fixture = valid_fixture()
        fixture["job_terminal"]["pass"] = False
        fixture["job_terminal"] = seal(fixture["job_terminal"])
        self.assertEqual(fixture["guard_terminal"]["child_exit_code"], 0)
        self.assertEqual(fixture["guard_terminal"]["status"], "completed")
        self.assert_rejected(fixture, "job_terminal_pass")

    def test_job_terminal_self_hash_is_required(self):
        fixture = valid_fixture()
        fixture["job_terminal"]["pass"] = False
        self.assert_rejected(fixture, "job_terminal_self_hash")

    def test_both_chains_pass_is_required(self):
        fixture = valid_fixture()
        fixture["job_terminal"]["result"]["both_chains_pass"] = False
        reseal_job(fixture)
        self.assert_rejected(fixture, "both_chains_pass")

    def test_inside_requires_all_five_segments(self):
        fixture = valid_fixture()
        row = fixture["job_terminal"]["result"]["planner_rows"][0]
        row["segment_receipts"].pop()
        row["planner_query_count"] = 4
        row["receipt_sha256"] = auditor.canonical_hash(
            {key: value for key, value in row.items() if key != "receipt_sha256"}
        )
        reseal_job(fixture)
        self.assert_rejected(fixture, "inside_planner_summary")

    def test_every_segment_must_pass(self):
        fixture = valid_fixture()
        row = fixture["job_terminal"]["result"]["planner_rows"][1]
        row["segment_receipts"][3]["planner_status"] = "IK_FAIL"
        row["receipt_sha256"] = auditor.canonical_hash(
            {key: value for key, value in row.items() if key != "receipt_sha256"}
        )
        reseal_job(fixture)
        self.assert_rejected(fixture, "beside_segment_not_passed")

    def test_aggregate_must_equal_eleven(self):
        fixture = valid_fixture()
        fixture["job_terminal"]["result"]["planner_query_count"] = 10
        reseal_job(fixture)
        self.assert_rejected(fixture, "job_result_accounting")

    def test_fresh_scene_count_must_equal_two(self):
        fixture = valid_fixture()
        fixture["job_terminal"]["result"]["fresh_planner_scene_count"] = 1
        reseal_job(fixture)
        self.assert_rejected(fixture, "job_result_accounting")

    def test_scene_ids_must_be_distinct(self):
        fixture = valid_fixture()
        inside_id = fixture["job_terminal"]["result"]["planner_rows"][0]["cleanup"]["scene_instance_id"]
        row = fixture["job_terminal"]["result"]["planner_rows"][1]
        row["cleanup"]["scene_instance_id"] = inside_id
        row["receipt_sha256"] = auditor.canonical_hash(
            {key: value for key, value in row.items() if key != "receipt_sha256"}
        )
        reseal_job(fixture)
        self.assert_rejected(fixture, "fresh_scene_uniqueness")

    def test_all_forbidden_result_counts_fail_closed(self):
        for key in (
            "physical_execution_count",
            "branch_execution_count",
            "raw_trajectory_count",
            "video_count",
            "accepted_root_count",
            "formal_trajectory_count",
        ):
            with self.subTest(key=key):
                fixture = valid_fixture()
                fixture["job_terminal"]["result"][key] = 1
                reseal_job(fixture)
                self.assert_rejected(fixture, "job_result_forbidden_count")

    def test_published_planner_receipt_must_match_embedded_row(self):
        fixture = valid_fixture()
        fixture["planner_receipts"]["inside"]["relation"] = "tampered"
        self.assert_rejected(fixture, "inside_planner_file_binding")

    def test_guard_completed_is_insufficient_without_cleanup(self):
        fixture = valid_fixture()
        fixture["guard_terminal"]["task_owned_cleanup_pass"] = False
        reseal_guard(fixture)
        self.assertEqual(fixture["guard_terminal"]["status"], "completed")
        self.assert_rejected(fixture, "guard_cleanup")

    def test_post_gpu_baseline_is_independently_recomputed(self):
        fixture = valid_fixture()
        post = snapshot(selected_util=17, selected_pstate="P0")
        fixture["guard_terminal"]["post_snapshot"] = post
        fixture["guard_terminal"]["post_release_poll_snapshots"] = [post]
        reseal_guard(fixture)
        self.assert_rejected(fixture, "gpu_post_baseline")

    def test_nonzero_child_exit_fails(self):
        fixture = valid_fixture()
        fixture["guard_terminal"]["child_exit_code"] = 1
        reseal_guard(fixture)
        self.assert_rejected(fixture, "guard_child_exit")

    def test_cache_must_be_absent_after_guard(self):
        fixture = valid_fixture()
        fixture["path_state"]["cache_job_exists"] = True
        self.assert_rejected(fixture, "postrun_path_cleanup")

    def test_disk_raw_or_video_artifact_is_rejected(self):
        fixture = valid_fixture()
        fixture["path_state"]["forbidden_artifact_paths"] = ["raw/trace.npz"]
        self.assert_rejected(fixture, "forbidden_disk_artifact")


if __name__ == "__main__":
    unittest.main(verbosity=2)
