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


class HighLevelAuthorizationBundleV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f2 = build_f2_hierarchical_template_search_v1()

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


if __name__ == "__main__":
    unittest.main()
