import hashlib
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from controlled_multi_future.common_scope_counter_schema_v3_4_1 import (
    add_planner_query_counts,
    build_execution_attempt_counts,
    build_planner_query_counts,
    build_primary_failure_cleanup_receipt,
    classify_evidence_field,
    validate_planner_query_counts,
)
from controlled_multi_future.f2_preload_entry_evidence_gate_v11 import (
    audit_f2_preload_entry_evidence_gate_v11,
)
from controlled_multi_future.f2_release_gates_v10 import (
    FINAL_MAX_ANGULAR_SPEED_RPS,
    SAFETY_MAX_ANGULAR_SPEED_RPS,
)
from controlled_multi_future.f3_three_context_diagnostic_runner_v11 import (
    PROGRAM_IDS,
    finalize_f3_three_context_diagnostics_v11,
)
from controlled_multi_future.f4_exact_corridor_application_v11 import (
    audit_f4_exact_corridor_results_v11,
    build_f4_exact_A_corridors_v11,
)
from controlled_multi_future.family_runners_v3_3 import (
    F1ControllerV3_3,
    _time_dilated_closed_loop_event_targets,
)
from controlled_multi_future.joint_limit_audit_v3_4_1 import (
    audit_terminal_qpos_against_joint_limits,
)
from controlled_multi_future.runtime_v3_4_1_budget_v1 import (
    STATIC_SCOPE_ACTIVITY_ENVELOPES,
)


VAULT = Path("/nfs_share/lijunhui/Vault-on-Fvl09")


class FakeJoint:
    def __init__(self, lower, upper):
        self.limits = [[lower, upper]]

    def get_limits(self):
        return self.limits


def f2_rows(angular=0.07927758109713366):
    return [
        {
            "actor_linear_velocity": [0.019, 0.0, 0.0],
            "actor_angular_velocity": [0.0, 0.0, angular],
            "selected_gripper_contact": True,
            "selected_contact_actor_name": "f2_main_can",
            "contact_signal_complete": True,
            "contact_pairs": [
                {"body_a": "f2_main_can", "body_b": "fl_link7"}
            ],
        }
        for _ in range(60)
    ]


def base_A_targets():
    q = [1.0, 0.0, 0.0, 0.0]
    return [
        {"segment_id": "A_pregrasp", "pose": [0.16, 0.00, 0.98, *q]},
        {"segment_id": "A_grasp", "pose": [0.16, 0.01, 0.90, *q]},
        {"segment_id": "A_lift", "pose": [0.16, 0.01, 0.92, *q]},
        {"segment_id": "A_carry_mid", "pose": [0.155, 0.08, 1.00, *q]},
        {"segment_id": "A_preplace", "pose": [0.15, 0.15, 1.00, *q]},
        {"segment_id": "A_release", "pose": [0.15, 0.15, 0.90, *q]},
        {"segment_id": "A_neutral", "pose": [0.20, -0.12, 1.01, *q]},
    ]


class RuntimeV341HardeningTest(unittest.TestCase):
    def test_planner_counter_identity_and_execution_lifecycle(self):
        first = build_planner_query_counts(
            canonical_prefix=1,
            target_construction=4,
            suffix_control_chain=11,
        )
        self.assertEqual(first["scope_total"], 16)
        self.assertEqual(validate_planner_query_counts(first), first)
        added = add_planner_query_counts(
            build_planner_query_counts(canonical_prefix=1),
            build_planner_query_counts(
                target_construction=4, suffix_control_chain=11
            ),
        )
        self.assertEqual(added["scope_total"], 16)
        execution = build_execution_attempt_counts(
            dispatch_started=1,
            controller_entered=1,
            terminal_receipt_written=1,
        )
        self.assertEqual(execution["budget_count_field"], "dispatch_started")

    def test_primary_failure_is_not_overwritten_by_cleanup(self):
        result = build_primary_failure_cleanup_receipt(
            primary_failure={
                "stage": "preload_entry",
                "type": "GateFailure",
                "message": "angular diagnostic",
            },
            cleanup_status={"attempted": True, "passed": True, "uncertainty": False},
            receipt_propagation_status="propagated",
        )
        self.assertEqual(result["primary_failure"]["stage"], "preload_entry")
        self.assertTrue(result["cleanup_status"]["passed"])
        missing = classify_evidence_field(
            field_name="joint_margin", present=False, condition_pass=None
        )
        self.assertEqual(missing["classification"], "infrastructure_schema_failure")
        self.assertIsNone(missing["condition_pass"])

    def test_f1_recorded_4_plus_11_is_computed_from_receipt(self):
        path = VAULT / (
            "数据构造/实现审计/probe_outputs/"
            "nonformal_runtime_v3_4_f1_shared_regression_seed20260829_run2/"
            "root/suffix_preflight/F1-red/suffix_preflight_failure_receipt.json"
        )
        receipt = json.loads(path.read_text())
        partial = receipt["controller_partial_evidence"]
        target = partial["extra"]["target_construction_planner_audit"]
        target_count = int(target["batch_call_count"])
        total_count = int(receipt["planner_query_count"])
        chain_count = total_count - target_count
        self.assertEqual((target_count, chain_count, total_count), (4, 11, 15))
        source = inspect.getsource(F1ControllerV3_3.plan_suffix_from_actual_prefix_end_state)
        self.assertIn("target_construction_planner_query_receipts", source)
        self.assertIn("suffix_control_chain_planner_query_receipts", source)
        self.assertIn("len(chain_receipts) != len(controls)", source)

    def test_f2_079_enters_existing_safety_envelope_but_final_remains_strict(self):
        geometry = {
            "opening_projection_inside": True,
            "rim_clearance_m": 0.025,
            "rim_clearance_pass": True,
            "can_geometry_center_pose": [0, 0, 1, 1, 0, 0, 0],
            "geometry_evidence_complete": True,
        }
        receipt = audit_f2_preload_entry_evidence_gate_v11(
            f2_rows(),
            can_actor_name="f2_main_can",
            selected_contact_signal_link_names=("fl_link7", "fl_link8"),
            allowed_gripper_assembly_body_names=("fl_link6", "fl_link7", "fl_link8"),
            final_geometry_gate=geometry,
        )
        self.assertTrue(receipt["pass"])
        self.assertFalse(
            receipt["legacy_final_like_diagnostics"][
                "angular_at_or_below_final_like_v6_threshold"
            ]
        )
        self.assertEqual(SAFETY_MAX_ANGULAR_SPEED_RPS, 1.0)
        self.assertEqual(FINAL_MAX_ANGULAR_SPEED_RPS, 0.05)
        v10 = Path(
            "/nfs_share/lijunhui/Robotwin2/project/RoboTwin/controlled_multi_future/"
            "f2_release_gates_v10.py"
        )
        self.assertEqual(
            hashlib.sha256(v10.read_bytes()).hexdigest(),
            "6a4910f6da4e6f90fb78083ff675b4ec5a3cfaf0b52fe29495958a7a449310c9",
        )

    def test_f3_canonical_ids_and_diagnostic_finalizer_nonroot(self):
        cleanup = [
            {"cleanup_safety_pass": True, "orphan_process_count": 0}
            for _ in range(8)
        ]
        branches = []
        for index, program_id in enumerate(PROGRAM_IDS):
            branches.append(
                {
                    "program_id": program_id,
                    "status": "passed",
                    "scene_instance_id": f"scene-{index}",
                    "diagnostic_context_id": "grasp_context_"
                    + program_id.split("-", 1)[1],
                    "diagnostic_nonroot": True,
                    "release_executed": False,
                    "prefix_replay": {
                        "executed_prefix_action_sha256": "a" * 64
                    },
                }
            )
        result = finalize_f3_three_context_diagnostics_v11(
            branches, cleanup_records=cleanup
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["accepted_root_increment"], 0)
        self.assertFalse(result["generic_root_final_state_equivalence_called"])
        event = _time_dilated_closed_loop_event_targets(
            np.asarray([0, 0, 1, 1, 0, 0, 0], dtype=np.float64),
            axis="V",
            amplitude_m=0.05,
            segment_prefix="test",
        )
        self.assertEqual(len(event), 7)
        self.assertEqual(
            STATIC_SCOPE_ACTIVITY_ENVELOPES[
                "F3_three_context_targeted_v11"
            ]["planner_query_count"],
            42,
        )
        self.assertEqual(
            STATIC_SCOPE_ACTIVITY_ENVELOPES["F3_full_root_v3_4_1"][
                "planner_query_count"
            ],
            96,
        )

    def test_f4_exact_candidate_application_and_joint_evidence(self):
        contract = build_f4_exact_A_corridors_v11(base_A_targets())
        self.assertTrue(contract["pass"])
        ids1 = contract["candidates"][0]["applied_planner_segment_ids"]
        ids3 = contract["candidates"][2]["applied_planner_segment_ids"]
        ids4 = contract["candidates"][3]["applied_planner_segment_ids"]
        self.assertEqual(
            [
                len(item["applied_planner_targets"])
                for item in contract["candidates"]
            ],
            [8, 7, 7, 8],
        )
        self.assertIn("A_restore_topdown_mid", ids1)
        self.assertIn("A_lower_preplace", ids3)
        self.assertIn("A_lower_corridor_entry", ids4)
        self.assertIn("A_lower_carry_mid", ids4)
        self.assertTrue(all(ids[-2:] == ["A_release", "A_neutral"] for ids in (ids1, ids3, ids4)))
        audit = audit_terminal_qpos_against_joint_limits(
            [FakeJoint(-1, 1), FakeJoint(-2, 2)], [0.0, 1.0]
        )
        self.assertTrue(audit["terminal_qpos_within_joint_limits"])
        self.assertEqual(audit["minimum_terminal_joint_limit_margin_rad"], 1.0)
        incomplete = audit_f4_exact_corridor_results_v11(
            contract,
            [
                {
                    "candidate_id": contract["candidates"][0]["candidate_id"],
                    "preplanner_contract_application_exact": True,
                    "qpos_chain_continuous": True,
                    "release_and_neutral_in_chain": True,
                    "execution_attempt_count": 0,
                    "cleanup_pass": True,
                    "segment_receipts": [{"planner_status": "Success"}],
                }
            ],
        )
        self.assertFalse(incomplete["evidence_complete"])
        self.assertEqual(incomplete["failure_type"], "infrastructure_schema_failure")


if __name__ == "__main__":
    unittest.main()
