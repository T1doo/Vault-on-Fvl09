import inspect
import json
import unittest
from pathlib import Path

from controlled_multi_future.f2_balanced_preload_release_v9 import (
    RELEASE_VERSION as F2_RELEASE_VERSION,
)
from controlled_multi_future.f3_symmetric_staged_release_v9 import (
    RELEASE_VERSION as F3_RELEASE_VERSION,
)
from controlled_multi_future.f4_json_canonicalization_v9 import (
    CANONICALIZATION_VERSION,
)
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F3ControllerV3_3,
)
from controlled_multi_future.pre_stage0_authorization_v3 import (
    APPROVED_SCOPE_REVISION_MAP,
    load_parent_user_authorization,
)
from controlled_multi_future.probes.runtime_trace import TRACE_SCHEMA_VERSION
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    current_source_bindings_v3_3,
)
from controlled_multi_future.raw_writer import REAL_RUNTIME_REQUIRED_AUDIT_FIELDS
from controlled_multi_future.runtime_v3_3_budget_v1 import (
    budget_artifact,
    validate_static_scope_activity_envelope,
)
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import (
    planned_scope_spec,
)


AUDIT_ROOT = Path(
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计"
)
PARENT = AUDIT_ROOT / "USER_AUTHORIZATION_RUNTIME_V3_3_REVISION9_REPAIRS_GPU0_20260830.json"
BUDGET = AUDIT_ROOT / "PRE_STAGE0_RUNTIME_V3_3_SCOPE_BUDGET_V1_8.json"


class Revision9IntegrationTest(unittest.TestCase):
    def test_f2_balanced_gate_precedes_full_open_and_changes_no_planner_count(self):
        source = inspect.getsource(F2ControllerV3_3.execute_frozen_suffix_spec)
        balance = source.index("build_f2_balanced_preload_release_spec_v9")
        gate = source.index("audit_f2_release_safety_gate_v10")
        block = source.index("F2 release-safety Gate v10 blocked full-open")
        full_open = source.index("f2_{spec['relation']}_release")
        self.assertLess(balance, gate)
        self.assertLess(gate, block)
        self.assertLess(block, full_open)
        self.assertIn("audit_f2_final_inside_success_gate_v10", source)
        self.assertNotIn("true_cavity_obb_pass=verify_true_cavity_obb", source[gate:full_open])
        self.assertEqual(
            validate_static_scope_activity_envelope(
                "F2_diagnosis_root_per_revision"
            )["source_bound_static_envelope"],
            {"planner_query_count": 32, "execution_attempt_count": 3},
        )
        self.assertEqual(
            F2_RELEASE_VERSION,
            "f2_inside_two_stage_balanced_preload_release_v9",
        )

    def test_f3_two_partial_stages_and_gate_precede_full_open(self):
        source = inspect.getsource(F3ControllerV3_3.execute_frozen_suffix_spec)
        balance = source.index("f3_release_balanced_preload")
        disengage = source.index("f3_release_slow_disengagement")
        gate = source.index("audit_f3_symmetric_staged_release_gate_v9")
        block = source.index("F3 symmetric staged-release Gate blocked full-open")
        full_open = source.index("f3_release_full_open")
        self.assertTrue(balance < disengage < gate < block < full_open)
        self.assertIn("bottle_orientation_error_rad", source)
        self.assertIn("bottle_footprint_inside_pad", source)
        self.assertEqual(
            validate_static_scope_activity_envelope(
                "F3_prefix_root_per_revision"
            )["source_bound_static_envelope"],
            {"planner_query_count": 96, "execution_attempt_count": 3},
        )
        self.assertEqual(
            F3_RELEASE_VERSION,
            "f3_post_release_roll_symmetric_staged_release_v9",
        )

    def test_real_trace_effort_semantics_are_explicit_and_required(self):
        self.assertEqual(
            TRACE_SCHEMA_VERSION,
            "cmf_runtime_trace_pose_consistent_velocity_effort_v3",
        )
        required = set(REAL_RUNTIME_REQUIRED_AUDIT_FIELDS)
        for field in (
            "realized_left_gripper_joint_qvel",
            "realized_left_gripper_joint_qf",
            "left_gripper_joint_drive_target_error",
            "left_gripper_joint_drive_velocity_error",
            "left_gripper_joint_drive_stiffness",
            "left_gripper_joint_drive_damping",
            "left_gripper_joint_drive_force_limit",
            "left_gripper_joint_drive_mode",
            "estimated_left_gripper_joint_drive_effort",
        ):
            self.assertIn(field, required)
        trace_source = inspect.getsource(
            __import__(
                "controlled_multi_future.probes.runtime_trace",
                fromlist=["dummy"],
            )
        )
        self.assertIn("not actuator/contact effort", trace_source)
        self.assertIn("not measured force", trace_source)

    def test_f4_fix_is_only_json_canonicalization(self):
        self.assertEqual(
            CANONICALIZATION_VERSION,
            "f4_numpy_json_safe_canonicalization_v9",
        )
        source = inspect.getsource(
            __import__(
                "controlled_multi_future.f4_top_down_block_carry_v8",
                fromlist=["dummy"],
            )
        )
        self.assertIn("json_safe_clone_v9", source)
        self.assertIn("scene_layout_changed", source)
        self.assertIn("program_changed", source)
        self.assertIn("verifier_threshold_changed", source)

    def test_revision9_parent_budget_gpu0_and_exact_scope_map_match(self):
        parent = load_parent_user_authorization(PARENT)
        budget = budget_artifact()
        self.assertEqual(
            budget,
            json.loads(BUDGET.read_text(encoding="utf-8")),
        )
        self.assertEqual(parent["allowed_physical_gpu_indices"], [0])
        self.assertFalse(parent["parallel_independent_jobs"])
        self.assertEqual(
            parent["approved_scope_revision_map"],
            APPROVED_SCOPE_REVISION_MAP,
        )
        self.assertEqual(
            budget["maximum_new_implementation_revisions_per_family"],
            9,
        )
        for scope, expected in APPROVED_SCOPE_REVISION_MAP.items():
            spec = planned_scope_spec(scope, revision_index=9)
            self.assertEqual(spec["family"], expected["family"])
            self.assertEqual(spec["implementation_revision_index"], 9)
            self.assertEqual(spec["maximum_full_root_execution_per_revision"], 1)
            self.assertFalse(spec["stage0_authorized"])

    def test_revision9_source_bindings_cover_all_new_semantic_components(self):
        bindings = current_source_bindings_v3_3()
        for key in (
            "f2_balanced_preload_release_sha256",
            "f3_symmetric_staged_release_sha256",
            "f4_json_canonicalization_sha256",
            "runtime_trace_sha256",
            "raw_writer_sha256",
            "f3_release_diagnosis_contract_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64)
        self.assertEqual(len(bindings["implementation_source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
