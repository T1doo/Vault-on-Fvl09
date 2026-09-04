#!/usr/bin/env python3
"""CPU-only exact contract tests for the F3 V2.1 fail-closed hotfix."""

from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


RUNTIME_DIR = Path(__file__).resolve().parent
RUNNER_PATH = RUNTIME_DIR / "job_runner.py"
PROJECT_TMP = Path("/nfs_share/lijunhui/Robotwin2/tmp")


def load_runner():
    spec = importlib.util.spec_from_file_location("cmf_f3_v2_1_test_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import F3 V2.1 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()


def job_contract():
    return dict(runner.EXPECTED_CAPS)


def planner_rows(*, first_only=False):
    rows = []
    for index, recipe_sha in enumerate(runner.EXPECTED_REPLACEMENT_RECIPE_SHA256S):
        passed = not first_only or index == 0
        rows.append(
            {
                "candidate": {"recipe_sha256": recipe_sha},
                "stage_a_pass": passed,
                "stage_b_pass": passed,
                "stage_a_queries": 3,
                **({"stage_b_queries": 7} if passed else {}),
            }
        )
    return rows


def persist_receipt(path, delta, *, result=None, error=None):
    value = {
        "schema_version": "cmf_f3_v2_1_physical_scene_receipt_v1",
        "family": "F3",
        "phase": "F3_CENTRALIZED_REPLACEMENT_PHYSICAL",
        "program": None,
        "current": {},
        "anchor": {},
        "result": {} if result is None else result,
        "error": error,
        "trace": None,
        "video": None,
        "cleanup": {"pass": True},
        "planner_query_count_before": 0,
        "planner_query_count_after": delta,
        "planner_query_delta": delta,
        "planner_accounting_source": "scene_counter_finally",
        "pass": error is None,
    }
    value["receipt_sha256"] = runner.canonical_hash(value)
    runner.write_new(path, value)
    return value


def synthetic_result(receipts, *, rows=None, gate_pass=True):
    rows = planner_rows() if rows is None else rows
    qualification = sum(row["stage_a_queries"] for row in rows) + sum(
        row.get("stage_b_queries", 0) for row in rows
    )
    candidate_order = [runner.EXPECTED_RETAINED_RECIPE_SHA256]
    candidate_order.extend(
        row["candidate"]["recipe_sha256"]
        for row in rows
        if row.get("stage_b_pass") is True
    )
    candidate_order = candidate_order[:4] if any(
        row.get("stage_b_pass") is True for row in rows
    ) else []
    physical_rows = [
        {
            "candidate": {"recipe_sha256": recipe_sha},
            "physical_pass": gate_pass,
            "physical_planner_queries": 0,
            "scene_receipt_sha256": receipt["receipt_sha256"],
        }
        for recipe_sha, receipt in zip(candidate_order, receipts)
    ]
    success_count = sum(row["physical_pass"] is True for row in physical_rows)
    return {
        "planner_rows": rows,
        "replacement_planner_queries": qualification,
        "physical_rows": physical_rows,
        "physical_execution_count": len(physical_rows),
        "physical_success_count": success_count,
        "gate_pass": success_count >= 2,
        "conditional_no_suffix_triggered": success_count >= 2,
        "conditional_no_suffix_executed": False,
        "conditional_no_suffix_scene_count": 0,
        "accepted_trajectory_count": 0,
        "formal_data": False,
    }


def no_physical_result():
    rows = [
        {
            "candidate": {"recipe_sha256": recipe_sha},
            "stage_a_pass": False,
            "stage_b_pass": False,
            "stage_a_queries": 3,
            "failure": "synthetic-stage-a-failure",
        }
        for recipe_sha in runner.EXPECTED_REPLACEMENT_RECIPE_SHA256S
    ]
    return {
        "planner_rows": rows,
        "replacement_planner_queries": 9,
        "physical_rows": [],
        "physical_execution_count": 0,
        "physical_success_count": 0,
        "gate_pass": False,
        "conditional_no_suffix_triggered": False,
        "accepted_trajectory_count": 0,
        "formal_data": False,
    }


class FakeScene:
    def __init__(self):
        self.planner_query_count = 0
        self.bottle = object()
        self.role_actors = {}
        self.trace = []

    def initialize_trace(self, actor, arm, role_actors):
        self.trace = []

    def start_development_video_capture(self, path):
        self.video_path = str(path)

    def finish_development_video_capture(self, terminal_status):
        return {"terminal_status": terminal_status}


class FakeAdapter:
    def capture_current(self, scene):
        return {"current": True}

    def capture_anchor(self, scene):
        return {"anchor": True}


class F3V21Tests(unittest.TestCase):
    def temporary_root(self):
        PROJECT_TMP.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(
            prefix="f3-v2-1-cpu-test-", dir=str(PROJECT_TMP)
        )

    def invoke_main(self, result, root, name):
        output = root / name
        manifest = {"manifest_sha256": "test-manifest"}
        job = {"output_namespace": str(output), **job_contract()}
        clean_environment = {
            "CUDA_VISIBLE_DEVICES": "GPU-test-only-no-cuda-call",
            "CMF_GPU_GUARD_PHYSICAL_INDEX": "7",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        with (
            patch.object(runner, "load_manifest", return_value=(manifest, job)),
            patch.object(runner, "run_gate", return_value=result),
            patch.dict(os.environ, clean_environment, clear=True),
        ):
            exit_code = runner.main(
                [
                    "--manifest",
                    str(root / "unused-test-manifest.json"),
                    "--job-id",
                    runner.EXPECTED_JOB_ID,
                ]
            )
        terminal = json.loads((output / "job_terminal.json").read_text())
        return exit_code, terminal

    def test_exact_58_passes_and_59_fails_closed(self):
        with self.temporary_root() as raw:
            root = Path(raw)
            paths_58 = []
            receipts_58 = []
            for index, delta in enumerate((7, 7, 7, 7)):
                path = root / f"pass_{index}" / "scene_receipt.json"
                receipts_58.append(persist_receipt(path, delta))
                paths_58.append(path)
            result_58 = synthetic_result(receipts_58)
            accounting_58, _rows = runner.build_runtime_accounting(
                result_58, job_contract(), paths_58
            )
            self.assertTrue(accounting_58["pass"])
            self.assertEqual(accounting_58["aggregate_planner_queries"], 58)

            paths_59 = []
            receipts_59 = []
            for index, delta in enumerate((7, 7, 7, 8)):
                path = root / f"fail_{index}" / "scene_receipt.json"
                receipts_59.append(persist_receipt(path, delta))
                paths_59.append(path)
            result_59 = synthetic_result(receipts_59)
            accounting_59, _rows = runner.build_runtime_accounting(
                result_59, job_contract(), paths_59
            )
            self.assertFalse(accounting_59["pass"])
            self.assertEqual(accounting_59["aggregate_planner_queries"], 59)
            self.assertFalse(
                accounting_59["checks"]["aggregate_planner_at_most_58"]
            )
            result_59["runtime_accounting"] = accounting_59
            result_59["conditional_no_suffix_scene_count"] = 0
            terminal_59 = runner.build_terminal(
                "manifest", runner.EXPECTED_JOB_ID, result_59, None
            )
            self.assertFalse(terminal_59["pass"])

    def test_success_exit_zero_and_scientific_failure_exit_one(self):
        success = {
            "gate_pass": True,
            "runtime_accounting": {"pass": True},
            "conditional_no_suffix_executed": False,
            "conditional_no_suffix_scene_count": 0,
        }
        failure = dict(success, gate_pass=False)
        with self.temporary_root() as raw:
            root = Path(raw)
            success_exit, success_terminal = self.invoke_main(
                success, root, "success"
            )
            failure_exit, failure_terminal = self.invoke_main(
                failure, root, "scientific_failure"
            )
        self.assertTrue(success_terminal["pass"])
        self.assertFalse(failure_terminal["pass"])
        self.assertEqual(success_exit, 0)
        self.assertEqual(failure_exit, 1)

    def test_exception_after_three_queries_is_receipted_and_exits_one(self):
        with self.temporary_root() as raw:
            root = Path(raw)
            scene = FakeScene()
            context = SimpleNamespace(cleanup_receipt={"pass": True})

            @contextmanager
            def opened_scene(*args, **kwargs):
                yield scene, context

            helper = SimpleNamespace(opened_scene=opened_scene)
            receipt_paths = []
            recorder = runner.make_audited_physical_scene_recorder(
                helper, receipt_paths
            )

            def exception_after_three(active_scene):
                active_scene.planner_query_count += 3
                raise RuntimeError("synthetic physical failure after three queries")

            first_receipt = recorder(
                family="F3",
                adapter=FakeAdapter(),
                legacy_scene_spec={},
                output=root / "physical_1",
                trace_actor_name="bottle",
                arm="left",
                execute=exception_after_three,
                phase="F3_CENTRALIZED_REPLACEMENT_PHYSICAL",
            )
            self.assertEqual(first_receipt["planner_query_count_before"], 0)
            self.assertEqual(first_receipt["planner_query_count_after"], 3)
            self.assertEqual(first_receipt["planner_query_delta"], 3)
            self.assertIsNotNone(first_receipt["error"])

            second_path = root / "physical_2" / "scene_receipt.json"
            second_receipt = persist_receipt(second_path, 0)
            receipt_paths.append(second_path)
            rows = planner_rows(first_only=True)
            result = synthetic_result(
                [first_receipt, second_receipt], rows=rows, gate_pass=False
            )
            accounting, normalized = runner.build_runtime_accounting(
                result, job_contract(), receipt_paths
            )
            result["runtime_accounting"] = accounting
            result["physical_rows"] = normalized
            exit_code, terminal = self.invoke_main(
                result, root, "exception_terminal"
            )
            self.assertTrue(accounting["pass"])
            self.assertEqual(accounting["physical_planner_queries_by_candidate"][0], 3)
            self.assertFalse(terminal["pass"])
            self.assertEqual(exit_code, 1)

    def test_exact_three_planner_rows_and_no_suffix_are_hard_gates(self):
        with self.temporary_root() as raw:
            root = Path(raw)
            paths = []
            receipts = []
            for index, delta in enumerate((7, 7, 7, 7)):
                path = root / f"receipt_{index}" / "scene_receipt.json"
                receipts.append(persist_receipt(path, delta))
                paths.append(path)
            result = synthetic_result(receipts)
            result["planner_rows"] = result["planner_rows"][::-1]
            accounting, _rows = runner.build_runtime_accounting(
                result, job_contract(), paths
            )
            self.assertFalse(accounting["pass"])
            self.assertFalse(
                accounting["checks"]["planner_rows_exact_replacement_order"]
            )
            result = synthetic_result(receipts)
            result["conditional_no_suffix_executed"] = True
            accounting, _rows = runner.build_runtime_accounting(
                result, job_contract(), paths
            )
            self.assertFalse(accounting["pass"])
            self.assertFalse(accounting["checks"]["no_suffix_scenes_zero"])

    def test_run_gate_preserves_and_fail_closes_no_suffix_source_evidence(self):
        def invoke(source_result):
            fake_base = SimpleNamespace(record_physical_scene=lambda **kwargs: None)
            fake_patched = SimpleNamespace(
                base=fake_base,
                run_gate=lambda manifest, job, output: dict(source_result),
            )
            proposal = {"proposal_sha256": runner.EXPECTED_PROPOSAL_SHA256}
            with patch.object(
                runner,
                "prepare_contract",
                return_value=(
                    fake_patched,
                    proposal,
                    object(),
                    object(),
                    {"pass": True},
                ),
            ):
                return runner.run_gate({}, job_contract(), Path("unused-output"))

        legacy = no_physical_result()
        legacy["conditional_no_suffix_executed"] = False
        normalized = invoke(legacy)
        self.assertIs(normalized["conditional_no_suffix_executed"], False)
        self.assertEqual(normalized["conditional_no_suffix_scene_count"], 0)
        self.assertEqual(
            normalized["conditional_no_suffix_scene_count_source"],
            runner.LEGACY_NO_SUFFIX_COUNT_SOURCE,
        )
        self.assertTrue(normalized["runtime_accounting"]["pass"])

        cases = []
        executed_true = no_physical_result()
        executed_true["conditional_no_suffix_executed"] = True
        cases.append(("executed_true", executed_true, True, None))
        missing_executed = no_physical_result()
        cases.append(("missing_executed", missing_executed, None, None))
        explicit_nonzero = no_physical_result()
        explicit_nonzero.update(
            {
                "conditional_no_suffix_executed": False,
                "conditional_no_suffix_scene_count": 1,
            }
        )
        cases.append(("explicit_nonzero", explicit_nonzero, False, 1))
        explicit_bool = no_physical_result()
        explicit_bool.update(
            {
                "conditional_no_suffix_executed": False,
                "conditional_no_suffix_scene_count": False,
            }
        )
        cases.append(("explicit_bool_not_exact_int", explicit_bool, False, False))

        for label, source, expected_executed, expected_count in cases:
            with self.subTest(label=label):
                with self.assertRaises(runner.RuntimeAccountingError) as caught:
                    invoke(source)
                rejected = caught.exception.result
                if label == "missing_executed":
                    self.assertNotIn("conditional_no_suffix_executed", rejected)
                else:
                    self.assertIs(
                        rejected["conditional_no_suffix_executed"], expected_executed
                    )
                if expected_count is None:
                    self.assertNotIn("conditional_no_suffix_scene_count", rejected)
                else:
                    self.assertIs(
                        rejected["conditional_no_suffix_scene_count"], expected_count
                    )
                self.assertFalse(
                    rejected["runtime_accounting"]["checks"][
                        "no_suffix_scenes_zero"
                    ]
                )

    def test_incomplete_or_negative_receipt_and_count_mismatch_fail_closed(self):
        with self.temporary_root() as raw:
            root = Path(raw)
            paths = []
            receipts = []
            for index, delta in enumerate((7, 7, 7, 7)):
                path = root / f"valid_{index}" / "scene_receipt.json"
                receipts.append(persist_receipt(path, delta))
                paths.append(path)
            result = synthetic_result(receipts)
            result["replacement_planner_queries"] = 29
            accounting, _rows = runner.build_runtime_accounting(
                result, job_contract(), paths
            )
            self.assertFalse(accounting["pass"])
            self.assertFalse(
                accounting["checks"]["qualification_equals_stage_a_plus_stage_b"]
            )

            result = synthetic_result(receipts)
            result["physical_execution_count"] = 3
            accounting, _rows = runner.build_runtime_accounting(
                result, job_contract(), paths
            )
            self.assertFalse(accounting["pass"])
            self.assertFalse(
                accounting["checks"]["physical_rows_equal_execution_count"]
            )
            self.assertFalse(
                accounting["checks"]["one_receipt_per_attempted_physical_candidate"]
            )

            bad_path = root / "negative" / "scene_receipt.json"
            bad_receipt = persist_receipt(bad_path, -1)
            mixed_receipts = receipts[:3] + [bad_receipt]
            mixed_paths = paths[:3] + [bad_path]
            result = synthetic_result(mixed_receipts)
            accounting, _rows = runner.build_runtime_accounting(
                result, job_contract(), mixed_paths
            )
            self.assertFalse(accounting["pass"])
            self.assertFalse(
                accounting["checks"][
                    "physical_receipt_counts_complete_nonnegative"
                ]
            )

    def test_preflight_declares_and_creates_no_scene_gpu_or_output(self):
        with self.temporary_root() as raw:
            root = Path(raw)
            output = root / "must_remain_absent"
            manifest = {"manifest_sha256": "test-manifest"}
            job = {"output_namespace": str(output), **job_contract()}
            proposal = {
                "replacement_candidates": [
                    {"recipe_sha256": value}
                    for value in runner.EXPECTED_REPLACEMENT_RECIPE_SHA256S
                ]
            }
            retained_a = {
                "spec": {"recipe": {"recipe_id": "f3-final-pose-v3-r0005"}}
            }
            retained_b = {"terminal": {"receipt_sha256": "retained"}}
            with (
                patch.object(
                    runner,
                    "load_manifest",
                    return_value=(manifest, job),
                ),
                patch.object(
                    runner,
                    "prepare_contract",
                    return_value=(
                        object(),
                        proposal,
                        retained_a,
                        retained_b,
                        {"pass": True},
                    ),
                ),
            ):
                receipt = runner.preflight(Path("unused"), runner.EXPECTED_JOB_ID)
            self.assertTrue(receipt["pass"])
            self.assertFalse(receipt["output_created"])
            self.assertFalse(receipt["scene_created"])
            self.assertFalse(receipt["gpu_context_created"])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
