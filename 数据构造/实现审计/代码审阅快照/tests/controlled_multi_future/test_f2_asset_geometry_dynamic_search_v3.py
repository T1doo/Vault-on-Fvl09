import copy
import hashlib
import json
import unittest

from controlled_multi_future.f2_asset_geometry_layout_v3 import (
    evaluate_asset_derived_layout_cpu_v3,
    evaluate_strict_full_envelope_inside_v3,
)
from controlled_multi_future.f2_dynamic_search_contract_v3 import (
    build_cpu_static_screening_v3,
    decide_bounded_dynamic_search_v3,
    validate_cpu_static_screening_v3,
)
from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
    PROGRAM_IDS,
    REQUIRED_GATE_IDS,
    apply_gate_receipts_v3,
    build_gate_receipt_v3,
    build_static_compatibility_matrix_v3,
    validate_strict_inside_full_envelope_evidence_v3,
)


def hash_json(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def pass_receipts(row):
    inside = evaluate_strict_full_envelope_inside_v3(row)
    if not inside["pass"]:
        raise AssertionError("test candidate must pass full-envelope CPU geometry")
    receipts = []
    predecessor = None
    for gate_id in REQUIRED_GATE_IDS:
        if gate_id == "strict_full_object_inside_margin":
            evidence = inside
        else:
            evidence = {"runtime_or_complete_geometry_evidence": True}
            if gate_id == "on_passive_stability":
                evidence.update(
                    passive_250hz_settle_verified=True,
                    continuous_scale_support=True,
                    stable_window_pass=True,
                )
            elif gate_id == "beside_mutual_exclusion":
                evidence.update(
                    asset_derived_predicates=True,
                    zero_overlap=True,
                    table_clearance_pass=True,
                )
            elif gate_id == "asset_derived_scene_layout":
                evidence.update(
                    fresh_scene_layout_realized=True,
                    facility_clearance_pass=True,
                    layout_payload_sha256=hash_json({"layout_version": "test_v3"}),
                )
            elif gate_id == "same_arm_three_branch_planner":
                evidence.update(
                    selected_execution_arm="left",
                    program_ids=list(PROGRAM_IDS),
                    same_start_qpos_and_seed=True,
                    complete_planner_chains=True,
                    same_main_object_for_all_programs=True,
                    same_execution_arm_for_all_programs=True,
                )
        receipts.append(
            build_gate_receipt_v3(
                row,
                gate_id=gate_id,
                status="passed",
                evidence=evidence,
                predecessor_gate_receipt_sha256=predecessor,
            )
        )
        predecessor = receipts[-1]["gate_receipt_sha256"]
    return receipts


def terminal_rejected(row):
    receipts = []
    predecessor = None
    for gate_id in REQUIRED_GATE_IDS:
        receipts.append(
            build_gate_receipt_v3(
                row,
                gate_id=gate_id,
                status="rejected",
                evidence={"reason": "bounded_dynamic_test_rejection"},
                predecessor_gate_receipt_sha256=predecessor,
            )
        )
        predecessor = receipts[-1]["gate_receipt_sha256"]
    return apply_gate_receipts_v3(row, receipts)


class F2AssetGeometryDynamicSearchV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = build_static_compatibility_matrix_v3()
        cls.screening = build_cpu_static_screening_v3(cls.matrix)

    def test_real_full_envelope_evaluator_does_not_use_center_line_as_acceptance(self):
        row = self.matrix["rows"][50]
        receipt = evaluate_strict_full_envelope_inside_v3(row)
        self.assertTrue(receipt["pass"])
        self.assertEqual(receipt["proposal_source"], "three_axis_center_lines_proposal_only")
        self.assertFalse(receipt["center_line_proposal_is_acceptance_evidence"])
        self.assertTrue(receipt["full_object_envelope_checked"])
        self.assertTrue(receipt["complete_cavity_collision_surface_checked"])
        self.assertEqual(receipt["minimum_signed_margin_m"], 0.005)
        self.assertTrue(
            receipt["orientation_receipts"][receipt["selected_orientation_rank"]][
                "complete_inflated_envelope_collision_free"
            ]
        )
        validate_strict_inside_full_envelope_evidence_v3(
            receipt,
            candidate_key_sha256=row["candidate_key_sha256"],
            expected_asset_record_sha256s=row["asset_record_sha256s"],
        )

    def test_layout_cpu_pass_remains_explicitly_non_dynamic(self):
        row = self.matrix["rows"][50]
        inside = evaluate_strict_full_envelope_inside_v3(row)
        layout = evaluate_asset_derived_layout_cpu_v3(row, inside)
        self.assertTrue(layout["pass"])
        self.assertTrue(layout["static_screen_only"])
        self.assertFalse(layout["passive_on_stability_verified"])
        self.assertFalse(layout["fresh_scene_layout_realization_verified"])
        self.assertFalse(layout["runtime_beside_predicates_verified"])
        self.assertFalse(layout["planner_reachability_verified"])

    def test_full_1650_screening_is_terminal_cpu_only_and_caps_scope_at_12(self):
        checked = validate_cpu_static_screening_v3(self.screening)
        self.assertEqual(checked["row_count"], 1650)
        self.assertEqual(checked["strict_inside_unique_pair_evaluation_count"], 66)
        self.assertGreater(checked["cpu_static_admissible_count"], 12)
        self.assertEqual(checked["dynamic_scope"]["candidate_count"], 12)
        self.assertEqual(
            [item["rank"] for item in checked["dynamic_scope"]["candidates"]],
            list(range(50, 62)),
        )
        self.assertFalse(checked["development_root_authorized"])
        for receipt in checked["terminal_cpu_candidate_receipts"]:
            self.assertEqual(receipt["dynamic_gate_pass_count"], 0)
            self.assertFalse(receipt["selection_eligible"])

    def test_screening_tamper_is_rejected(self):
        value = copy.deepcopy(self.screening)
        value["dynamic_scope"]["candidates"][0]["rank"] = 99
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_cpu_static_screening_v3(value)

    def test_pending_first_candidate_blocks_later_all_pass_candidate(self):
        first_rank = self.screening["dynamic_scope"]["candidates"][0]["rank"]
        second_rank = self.screening["dynamic_scope"]["candidates"][1]["rank"]
        pending = apply_gate_receipts_v3(self.matrix["rows"][first_rank], [])
        passed = apply_gate_receipts_v3(
            self.matrix["rows"][second_rank], pass_receipts(self.matrix["rows"][second_rank])
        )
        decision = decide_bounded_dynamic_search_v3(self.screening, [pending, passed])
        self.assertEqual(decision["status"], "pending_earlier_dynamic_candidate")
        self.assertIsNone(decision["selected_evaluated_row_sha256"])

    def test_first_all_gate_pass_selected_only_after_earlier_terminal_rejection(self):
        ranks = [item["rank"] for item in self.screening["dynamic_scope"]["candidates"]]
        rejected = terminal_rejected(self.matrix["rows"][ranks[0]])
        passed = apply_gate_receipts_v3(
            self.matrix["rows"][ranks[1]], pass_receipts(self.matrix["rows"][ranks[1]])
        )
        decision = decide_bounded_dynamic_search_v3(self.screening, [rejected, passed])
        self.assertEqual(decision["status"], "first_all_gates_candidate_selected_binding_required")
        self.assertEqual(decision["selected_rank"], ranks[1])
        self.assertFalse(decision["development_root_authorized"])

    def test_exhausted_twelve_requires_higher_level_redesign_without_fallback(self):
        ranks = [item["rank"] for item in self.screening["dynamic_scope"]["candidates"]]
        rows = [terminal_rejected(self.matrix["rows"][rank]) for rank in ranks]
        decision = decide_bounded_dynamic_search_v3(self.screening, rows)
        self.assertEqual(
            decision["status"],
            "higher_level_redesign_required_dynamic_scope_exhausted",
        )
        self.assertTrue(decision["higher_level_redesign_required"])
        self.assertFalse(decision["development_root_authorized"])


if __name__ == "__main__":
    unittest.main()
