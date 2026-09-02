import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from controlled_multi_future.canonical_artifact import (
    canonical_hash_json,
    canonical_write_json,
)
from controlled_multi_future.f2_hierarchical_template_search_v1 import (
    build_f2_hierarchical_template_search_v1,
    select_inside_physical_candidates_v1,
)
from controlled_multi_future.f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
    select_f4_stage_a_source_v1,
    select_f4_stage_b_layout_v1,
)
from controlled_multi_future.high_level_bundle_v1 import (
    build_cpu_registry_v1,
    build_parent_authorization_v1,
    issue_job_bundle_v1,
)
from controlled_multi_future.high_level_runtime_specs_v1 import (
    build_f2_runtime_spec_v1,
    build_f3_runtime_spec_v1,
    build_f4_runtime_spec_v1,
)
from controlled_multi_future.probes import high_level_authorization_v1 as auth
from controlled_multi_future.probes import high_level_scope_runner_v1 as scope_runner
from controlled_multi_future.probes import gpu_guard_v2_4 as guard


class HighLevelAuthorizationBundleV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2 = build_f2_hierarchical_template_search_v1()
        cls.f4 = build_f4_hierarchical_template_search_v1()

    def _f4_stage_a_terminal(self):
        gates = self.f4["stage_a_required_gates"]
        return select_f4_stage_a_source_v1(
            self.f4,
            [
                {
                    "candidate_id": item["candidate_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "checks": {
                        name: item["rank"] == 1 for name in gates
                    },
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
                for item in self.f4["stage_a_candidates"]
            ],
        )

    def _f4_stage_b_terminal(self):
        stage_a = self._f4_stage_a_terminal()
        stage_b = build_f4_stage_b_candidates_v1(self.f4, stage_a)
        gates = self.f4["stage_b_required_gates"]
        terminal = select_f4_stage_b_layout_v1(
            self.f4,
            stage_a,
            [
                {
                    "candidate_id": item["candidate_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "checks": {
                        name: item["rank"] == 1 for name in gates
                    },
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
                for item in stage_b["candidates"]
            ],
        )
        return stage_a, terminal

    def test_parent_and_registry_bind_exact_initial_job_set(self):
        parent = build_parent_authorization_v1()
        registry = build_cpu_registry_v1()
        payload = dict(parent)
        digest = payload.pop("parent_user_authorization_sha256")
        self.assertEqual(canonical_hash_json(payload), digest)
        self.assertEqual(set(parent["authorized_job_kinds"]), set(auth.JOB_KINDS))
        self.assertEqual(parent["allowed_physical_gpu_indices"], list(range(8)))
        self.assertFalse(parent["stage1_authorized"])
        self.assertEqual(registry["f2"]["candidate_count"], 12)
        self.assertEqual(registry["f3"]["tuple_count"], 8)
        self.assertEqual(registry["f4"]["candidate_count"], 8)

    def test_job_kind_purpose_binding_rejects_cross_phase_specs(self):
        f2 = build_f2_runtime_spec_v1(
            self.f2["fixed_inside_candidate_order"][0],
            purpose="f2_stage_a_planner",
        )
        self.assertEqual(
            auth._validate_job_spec("F2_STAGE_A_PLANNER", f2), f2
        )
        with self.assertRaises(Exception):
            auth._validate_job_spec("F2_INSIDE_PHYSICAL", f2)
        f3 = build_f3_runtime_spec_v1(
            "f3-asset-grasp-v2-r01", purpose="f3_level1_planner"
        )
        self.assertEqual(auth._validate_job_spec("F3_LEVEL1_PLANNER", f3), f3)
        f4 = build_f4_runtime_spec_v1(
            "f4-source-grasp-hv1-r01", purpose="f4_stage_a_planner"
        )
        self.assertEqual(auth._validate_job_spec("F4_STAGE_A_PLANNER", f4), f4)
        terminal = self._f4_stage_a_terminal()
        stage_b = build_f4_stage_b_candidates_v1(self.f4, terminal)
        f4_stage_b = build_f4_runtime_spec_v1(
            stage_b["fixed_candidate_order"][0],
            purpose="f4_stage_b_planner",
            stage_a_terminal=terminal,
        )
        self.assertEqual(
            auth._validate_job_spec("F4_STAGE_B_PLANNER", f4_stage_b),
            f4_stage_b,
        )
        stage_a, stage_b_terminal = self._f4_stage_b_terminal()
        selected = stage_b_terminal["selected_slot_corridor"]
        f4_physical = build_f4_runtime_spec_v1(
            selected["candidate_id"],
            purpose="f4_single_role_physical",
            stage_a_terminal=stage_a,
            stage_b_terminal=stage_b_terminal,
        )
        self.assertEqual(
            auth._validate_job_spec("F4_A_ONLY_PHYSICAL", f4_physical),
            f4_physical,
        )

    def test_physical_input_requires_rank_ordered_selection_receipt(self):
        candidates = self.f2["inside_candidates"]
        planner = select_inside_physical_candidates_v1(
            self.f2,
            [
                {
                    "candidate_id": item["candidate_id"],
                    "candidate_sha256": item["candidate_sha256"],
                    "planner_success": item["rank"] <= 4,
                }
                for item in candidates
            ],
        )
        selected_id = planner["physical_candidate_ids"][0]
        spec = build_f2_runtime_spec_v1(
            selected_id, purpose="f2_inside_physical"
        )
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as temporary:
            path = Path(temporary) / "selection.json"
            canonical_write_json(path, planner)
            inputs = {
                "selection_receipt_path": str(path.resolve()),
                "selection_receipt_file_sha256": hashlib.sha256(
                    path.read_bytes()
                ).hexdigest(),
                "selection_receipt_sha256": planner["receipt_sha256"],
                "selected_candidate_id": selected_id,
            }
            self.assertEqual(
                auth._validate_job_inputs("F2_INSIDE_PHYSICAL", inputs, spec),
                inputs,
            )
            changed = dict(inputs)
            changed["selected_candidate_id"] = candidates[-1]["candidate_id"]
            with self.assertRaises(Exception):
                auth._validate_job_inputs("F2_INSIDE_PHYSICAL", changed, spec)

    def test_bundle_issuer_rejects_unpublished_commit_before_writes(self):
        spec = build_f2_runtime_spec_v1(
            self.f2["fixed_inside_candidate_order"][0],
            purpose="f2_stage_a_planner",
        )
        with self.assertRaises(ValueError):
            issue_job_bundle_v1(
                job_kind="F2_STAGE_A_PLANNER",
                authorization_id="must-not-write-unpublished-high-level",
                planned_root_slot_spec=spec,
                reviewed_content_commit="0" * 40,
            )

    def test_f4_stage_b_input_is_bound_to_stage_a_selection_and_candidate(self):
        terminal = self._f4_stage_a_terminal()
        stage_b = build_f4_stage_b_candidates_v1(self.f4, terminal)
        candidate_id = stage_b["fixed_candidate_order"][0]
        spec = build_f4_runtime_spec_v1(
            candidate_id,
            purpose="f4_stage_b_planner",
            stage_a_terminal=terminal,
        )
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as temporary:
            path = Path(temporary) / "f4-stage-a-selection.json"
            canonical_write_json(path, terminal)
            inputs = {
                "stage_a_selection_receipt_path": str(path.resolve()),
                "stage_a_selection_receipt_file_sha256": hashlib.sha256(
                    path.read_bytes()
                ).hexdigest(),
                "stage_a_selection_receipt_sha256": terminal[
                    "receipt_sha256"
                ],
                "selected_source_grasp_candidate_id": terminal[
                    "selected_source_grasp"
                ]["candidate_id"],
                "stage_b_candidate_id": candidate_id,
            }
            self.assertEqual(
                auth._validate_job_inputs(
                    "F4_STAGE_B_PLANNER", inputs, spec
                ),
                inputs,
            )
            changed = dict(inputs)
            changed["stage_b_candidate_id"] = stage_b[
                "fixed_candidate_order"
            ][-1]
            with self.assertRaises(Exception):
                auth._validate_job_inputs(
                    "F4_STAGE_B_PLANNER", changed, spec
                )

    def test_f4_a_only_input_is_bound_to_stage_b_selection(self):
        stage_a, terminal = self._f4_stage_b_terminal()
        selected = terminal["selected_slot_corridor"]
        spec = build_f4_runtime_spec_v1(
            selected["candidate_id"],
            purpose="f4_single_role_physical",
            stage_a_terminal=stage_a,
            stage_b_terminal=terminal,
        )
        with tempfile.TemporaryDirectory(
            dir="/nfs_share/lijunhui/Robotwin2/tmp"
        ) as temporary:
            path = Path(temporary) / "f4-stage-b-selection.json"
            canonical_write_json(path, terminal)
            inputs = {
                "stage_b_selection_receipt_path": str(path.resolve()),
                "stage_b_selection_receipt_file_sha256": hashlib.sha256(
                    path.read_bytes()
                ).hexdigest(),
                "stage_b_selection_receipt_sha256": terminal[
                    "receipt_sha256"
                ],
                "selected_candidate_id": selected["candidate_id"],
            }
            self.assertEqual(
                auth._validate_job_inputs(
                    "F4_A_ONLY_PHYSICAL", inputs, spec
                ),
                inputs,
            )

    def test_scope_dispatch_preserves_candidate_terminal(self):
        spec = build_f2_runtime_spec_v1(
            self.f2["fixed_inside_candidate_order"][0],
            purpose="f2_stage_a_planner",
        )
        authorization = {
            "family": "F2",
            "job_kind": "F2_STAGE_A_PLANNER",
            "planned_root_slot_spec": spec,
            "implementation_source_sha256": "a" * 64,
        }
        result = {
            "status": "planner_candidate_failed",
            "pass": False,
            "candidate_sha256": spec["candidate_sha256"],
        }
        with patch.object(scope_runner, "_adapter", return_value=object()), patch(
            "controlled_multi_future.probes.high_level_scope_runner_v1."
            "HighLevelPlannerRunnerV1.run",
            return_value=result,
        ):
            dispatch = scope_runner._dispatch(
                authorization, Path("/nfs_share/lijunhui/Robotwin2/tmp/unused")
            )
        self.assertTrue(dispatch["scope_completed"])
        self.assertFalse(dispatch["pass"])
        self.assertEqual(dispatch["result"]["candidate_sha256"], spec["candidate_sha256"])

    def test_consumption_hash_excludes_only_runtime_path(self):
        authorization = {
            "authorization_id": "x",
            "receipt_sha256": "a" * 64,
            "approved_scopes": ["f2_stage_a_planner"],
            "job_kind": "F2_STAGE_A_PLANNER",
            "family": "F2",
            "scene_seed": 1,
        }
        value = {
            "schema_version": auth.CONSUMPTION_SCHEMA,
            "implementation_version": auth.IMPLEMENTATION_VERSION,
            "authorization_id": "x",
            "authorization_receipt_sha256": "a" * 64,
            "approved_scope": "f2_stage_a_planner",
            "job_kind": "F2_STAGE_A_PLANNER",
            "family": "F2",
            "scene_seed": 1,
            "consumed_at": "2026-09-01T00:00:00+00:00",
            "max_invocations": 1,
        }
        value["consumption_receipt_sha256"] = auth.consumption_sha(value)
        self.assertEqual(auth.validate_consumption(value, authorization), value)

    def test_gpu_guard_dispatches_high_level_load_consume_and_validate(self):
        path = Path("/nfs_share/lijunhui/Robotwin2/tmp/high-level-auth-test.json")
        with patch.object(
            guard, "_authorization_implementation", return_value=auth.IMPLEMENTATION_VERSION
        ), patch.object(guard, "load_high_level_v1", return_value={"loaded": True}) as loader:
            self.assertEqual(
                guard._load_runtime_authorization(
                    path, requested_scope="f2_stage_a_planner"
                ),
                {"loaded": True},
            )
            loader.assert_called_once()
        authorization = {"implementation_version": auth.IMPLEMENTATION_VERSION}
        with patch.object(
            guard, "consume_high_level_v1", return_value={"consumed": True}
        ) as consume:
            self.assertEqual(
                guard._consume_runtime_authorization(
                    authorization, ledger_directory=Path("/nfs_share/lijunhui/Robotwin2/tmp")
                ),
                {"consumed": True},
            )
            consume.assert_called_once()
        with patch.object(
            guard,
            "validate_high_level_consumption_v1",
            return_value={"validated": True},
        ) as validate:
            self.assertEqual(
                guard._validate_runtime_consumption({}, authorization),
                {"validated": True},
            )
            validate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
