from __future__ import annotations

import builtins
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from controlled_multi_future.f3_physical_contact_signal_v8 import (
    CONTACT_PAIR_SCHEMA_VERSION,
    canonical_json_sha256,
)

from gate import canonical_hash, evaluate_preclose_sequence, evaluate_preclose_stage
from proposal import EXPECTED_BUDGET, build_proposal, reject_execution, validate_proposal
from replay import CASE_DIRECTORIES, TRACE_ROOT, replay_sealed_cohort


def shape_identity(body: str, index: int) -> dict:
    value = {
        "available": True,
        "body_name": body,
        "collision_shape_index": index,
        "collision_shape_type": "synthetic",
        "collision_groups": [1, 1, 0, index],
    }
    value["identity_sha256"] = canonical_json_sha256(value)
    return value


def contact_pair(
    body_a: str,
    body_b: str,
    *,
    impulse: float = 0.0,
    separation: float = 0.010,
) -> dict:
    identities = [shape_identity(body_a, 0), shape_identity(body_b, 1)]
    hashes = [item["identity_sha256"] for item in identities]
    return {
        "contact_pair_schema_version": CONTACT_PAIR_SCHEMA_VERSION,
        "body_a": body_a,
        "body_b": body_b,
        "point_count": 1,
        "impulse_norm_sum": impulse,
        "impulse_available": True,
        "shape_identity_available": True,
        "shape_identities": identities,
        "point_evidence": [
            {
                "point_index": 0,
                "impulse_norm": impulse,
                "impulse_available": True,
                "signed_separation_m": separation,
                "signed_separation_available": True,
                "shape_identity_available": True,
                "shape_identity_sha256": hashes,
            }
        ],
    }


def good_snapshot(stage: str = "pregrasp", arm: str = "left") -> dict:
    selected = ["fl_link7", "fl_link8"] if arm == "left" else ["fr_link7", "fr_link8"]
    return {
        "stage": stage,
        "arm": arm,
        "planned_selected_arm_qpos": [0.0] * 6,
        "realized_selected_arm_qpos": [0.002] * 6,
        "planner_goal_eef_pose": [0.0, 0.0, 0.9, 1.0, 0.0, 0.0, 0.0],
        "realized_eef_pose": [0.001, -0.001, 0.901, 1.0, 0.0, 0.0, 0.0],
        "initial_bottle_position_m": [0.18, -0.06, 0.79],
        "realized_bottle_position_m": [0.18, -0.06, 0.79],
        "contact_pairs": [],
        "selected_gripper_links": selected,
        "bottle_actor_name": "f3_main_bottle",
        "support_actor_names": ["table", "f3_original_pad"],
        "selected_arm_commanded": True,
        "opposite_arm_commanded": False,
    }


class PureGateTests(unittest.TestCase):
    def test_good_synthetic_sequence_allows_close_but_nothing_later(self):
        result = evaluate_preclose_sequence(
            good_snapshot("pregrasp"), good_snapshot("grasp")
        )
        self.assertTrue(result["pass"])
        self.assertTrue(result["close_allowed"])
        self.assertFalse(result["stop_before_close"])
        self.assertFalse(result["lift_allowed"])
        self.assertFalse(result["shared_v_allowed"])
        self.assertFalse(result["root_allowed"])
        self.assertFalse(result["raw_allowed"])

    def test_wrong_arm_routing_fails_first(self):
        value = good_snapshot()
        value["selected_arm_commanded"] = False
        value["opposite_arm_commanded"] = True
        result = evaluate_preclose_stage(value)
        self.assertFalse(result["pass"])
        self.assertEqual(result["earliest_failure_code"], "wrong_arm_or_action_routing")
        self.assertTrue(result["stop_before_close"])

    def test_positive_separation_pair_presence_is_not_collision(self):
        value = good_snapshot()
        value["contact_pairs"] = [
            contact_pair("fl_link6", "fl_link4", impulse=0.0, separation=0.013)
        ]
        result = evaluate_preclose_stage(value)
        self.assertTrue(result["pass"])
        row = result["contact_audit"]["relevant_pairs"][0]
        self.assertFalse(row["physical_hit_for_gate"])
        self.assertEqual(row["impulse_norm_sum"], 0.0)

    def test_missing_contact_signal_fails_closed(self):
        value = good_snapshot()
        pair = contact_pair("fl_link6", "fl_link4")
        pair["shape_identity_available"] = False
        value["contact_pairs"] = [pair]
        result = evaluate_preclose_stage(value)
        self.assertFalse(result["pass"])
        self.assertEqual(result["earliest_failure_code"], "contact_signal_incomplete")
        self.assertTrue(result["contact_audit"]["incomplete_signal_pairs"])

    def test_observed_self_collision_stops_before_close(self):
        value = good_snapshot()
        value["contact_pairs"] = [
            contact_pair("fl_link6", "fl_link4", impulse=0.5, separation=-0.001)
        ]
        result = evaluate_preclose_stage(value)
        self.assertEqual(result["earliest_failure_code"], "executing_arm_self_collision")
        self.assertTrue(result["stop_before_close"])

    def test_support_collision_stops_before_close(self):
        value = good_snapshot()
        value["contact_pairs"] = [
            contact_pair("fl_link6", "table", impulse=0.1, separation=-0.001)
        ]
        result = evaluate_preclose_stage(value)
        self.assertEqual(result["earliest_failure_code"], "executing_arm_support_collision")

    def test_nonselected_arm_bottle_contact_is_rejected(self):
        value = good_snapshot("grasp")
        value["contact_pairs"] = [
            contact_pair("fl_link6", "f3_main_bottle", impulse=0.1, separation=-0.001)
        ]
        result = evaluate_preclose_stage(value)
        self.assertEqual(
            result["earliest_failure_code"],
            "premature_or_unexpected_arm_bottle_contact",
        )

    def test_selected_finger_bottle_contact_is_only_allowed_at_grasp(self):
        pair = contact_pair(
            "fl_link7", "f3_main_bottle", impulse=0.01, separation=-0.0001
        )
        pregrasp = good_snapshot("pregrasp")
        pregrasp["contact_pairs"] = [pair]
        grasp = good_snapshot("grasp")
        grasp["contact_pairs"] = [pair]
        self.assertFalse(evaluate_preclose_stage(pregrasp)["pass"])
        self.assertTrue(evaluate_preclose_stage(grasp)["pass"])

    def test_bottle_displacement_is_rejected(self):
        value = good_snapshot()
        value["realized_bottle_position_m"] = [0.195, -0.06, 0.79]
        result = evaluate_preclose_stage(value)
        self.assertEqual(result["earliest_failure_code"], "bottle_displaced_before_close")

    def test_tracking_limits_are_inclusive_and_self_hashed(self):
        value = good_snapshot()
        value["realized_selected_arm_qpos"] = [0.10] * 6
        value["realized_eef_pose"] = [0.03, 0.0, 0.9, 1.0, 0.0, 0.0, 0.0]
        result = evaluate_preclose_stage(value)
        self.assertTrue(result["pass"])
        payload = dict(result)
        digest = payload.pop("receipt_sha256")
        self.assertEqual(digest, canonical_hash(payload))

    def test_pure_gate_performs_no_file_io(self):
        with patch.object(builtins, "open", side_effect=AssertionError("unexpected IO")):
            result = evaluate_preclose_sequence(
                good_snapshot("pregrasp"), good_snapshot("grasp")
            )
        self.assertTrue(result["pass"])


class RealTraceReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = {
            path.relative_to(TRACE_ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in TRACE_ROOT.rglob("*")
            if path.is_file()
        }
        cls.result = replay_sealed_cohort()
        cls.after = {
            path.relative_to(TRACE_ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in TRACE_ROOT.rglob("*")
            if path.is_file()
        }

    def test_exact_four_trace_order_and_read_only_replay(self):
        self.assertEqual(self.result["ordered_cases"], list(CASE_DIRECTORIES))
        self.assertEqual(self.result["case_count"], 4)
        self.assertEqual(self.before, self.after)
        self.assertFalse(self.result["gpu_used"])
        self.assertFalse(self.result["scene_created"])
        self.assertFalse(self.result["planner_called"])
        self.assertFalse(self.result["physical_action_executed"])
        self.assertFalse(self.result["source_artifact_modified"])

    def test_four_of_four_rejected_at_pregrasp_self_collision(self):
        self.assertEqual(self.result["rejected_before_close_count"], 4)
        self.assertTrue(self.result["all_four_rejected_before_close"])
        self.assertTrue(self.result["all_earliest_failures_pregrasp"])
        for row in self.result["rows"]:
            self.assertEqual(row["earliest_failure_stage"], "pregrasp")
            self.assertEqual(
                row["earliest_failure_code"], "executing_arm_self_collision"
            )
            first = row["gate"]["stage_receipts"][0]
            self.assertTrue(
                first["contact_audit"]["executing_arm_self_collision_hits"]
            )

    def test_real_action_routing_is_selected_arm_only(self):
        for row in self.result["rows"]:
            for stage in row["gate"]["stage_receipts"]:
                self.assertTrue(stage["checks"]["selected_arm_commanded"])
                self.assertTrue(stage["checks"]["opposite_arm_not_commanded"])

    def test_real_collision_impulse_and_tracking_evidence(self):
        expected_minimum_impulses = {
            "f3-final-pose-v3-r0005": 76.0,
            "f3-final-pose-v3-r1505": 63.0,
            "f3-final-pose-v3-r2180": 10.0,
            "f3-final-pose-v3-r3677": 35.0,
        }
        for row in self.result["rows"]:
            pregrasp = row["gate"]["stage_receipts"][0]
            impulses = [
                hit["impulse_norm_sum"]
                for hit in pregrasp["contact_audit"][
                    "executing_arm_self_collision_hits"
                ]
            ]
            self.assertGreaterEqual(
                max(impulses), expected_minimum_impulses[row["recipe_id"]]
            )
            self.assertFalse(pregrasp["checks"]["eef_position_tracking"])

    def test_bottle_was_displaced_in_two_grasp_snapshots(self):
        by_recipe = {row["recipe_id"]: row for row in self.result["rows"]}
        for recipe, minimum in (
            ("f3-final-pose-v3-r2180", 0.17),
            ("f3-final-pose-v3-r3677", 0.07),
        ):
            grasp = by_recipe[recipe]["gate"]["stage_receipts"][1]
            self.assertGreater(
                grasp["measurements"]["bottle_preclose_displacement_m"], minimum
            )
            self.assertFalse(grasp["checks"]["bottle_not_displaced_before_close"])


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.proposal = build_proposal(
            {
                "sealed_f3_terminal_receipt_sha256": "a" * 64,
                "cpu_replay_receipt_sha256": "b" * 64,
            }
        )

    def test_exact_finite_budget_and_no_candidates_fabricated(self):
        validated = validate_proposal(self.proposal)
        self.assertEqual(validated["budget"], EXPECTED_BUDGET)
        self.assertEqual(EXPECTED_BUDGET["aggregate_planner_query_cap"], 52)
        self.assertEqual(EXPECTED_BUDGET["aggregate_scene_cap"], 12)
        self.assertEqual(EXPECTED_BUDGET["physical_attempt_cap"], 4)
        self.assertEqual(EXPECTED_BUDGET["shared_v_scene_cap"], 0)
        self.assertEqual(EXPECTED_BUDGET["root_execution_cap"], 0)
        self.assertEqual(EXPECTED_BUDGET["raw_trajectory_cap"], 0)
        self.assertEqual(EXPECTED_BUDGET["formal_trajectory_cap"], 0)
        self.assertTrue(
            all(slot["recipe"] is None for slot in validated["candidate_slots"])
        )

    def test_proposal_cannot_execute(self):
        with self.assertRaises(PermissionError):
            reject_execution(self.proposal)

    def test_any_authorization_flip_is_rejected(self):
        bad = deepcopy(self.proposal)
        bad["authorization"]["gpu_execution_authorized"] = True
        payload = dict(bad)
        payload.pop("manifest_sha256")
        bad["manifest_sha256"] = canonical_hash(payload)
        with self.assertRaises(PermissionError):
            validate_proposal(bad)

    def test_53_queries_is_rejected(self):
        bad = deepcopy(self.proposal)
        bad["budget"]["aggregate_planner_query_cap"] = 53
        payload = dict(bad)
        payload.pop("manifest_sha256")
        bad["manifest_sha256"] = canonical_hash(payload)
        with self.assertRaises(ValueError):
            validate_proposal(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
