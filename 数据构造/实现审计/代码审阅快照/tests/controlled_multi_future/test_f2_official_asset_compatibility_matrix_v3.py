import copy
import hashlib
import json
import unittest

from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import (
    ASSET_ROOT,
    EXPECTED_OFFICIAL_IDS,
    PROGRAM_IDS,
    REQUIRED_GATE_IDS,
    apply_gate_receipts_v3,
    build_frozen_asset_layout_binding_v3,
    build_gate_receipt_v3,
    build_static_compatibility_matrix_v3,
    select_first_all_gates_pass_v3,
    validate_frozen_asset_layout_binding_v3,
    validate_static_candidate_row_v3,
    validate_static_compatibility_matrix_v3,
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


def strict_evidence(row):
    value = {
        "evidence_version": "test_full_envelope_geometry_v1",
        "candidate_key_sha256": row["candidate_key_sha256"],
        "full_object_envelope_checked": True,
        "complete_cavity_collision_surface_checked": True,
        "center_line_or_axis_interval_only": False,
        "minimum_signed_margin_m": 0.005,
        "selected_orientation_wxyz": [1.0, 0.0, 0.0, 0.0],
        "asset_record_sha256s": {
            role: row["asset_record_sha256s"][role]
            for role in ("main_object", "plastic_box")
        },
    }
    value["evidence_sha256"] = hash_json(value)
    return value


def all_pass_receipts(row, *, layout=None, arm="left"):
    layout = layout or {"layout_version": "test_asset_derived_layout_v1", "poses": {}}
    receipts = []
    predecessor = None
    for gate_id in REQUIRED_GATE_IDS:
        if gate_id == "strict_full_object_inside_margin":
            evidence = strict_evidence(row)
        else:
            evidence = {"runtime_or_complete_geometry_evidence": True}
            if gate_id == "on_passive_stability":
                evidence.update(
                    {
                        "passive_250hz_settle_verified": True,
                        "continuous_scale_support": True,
                        "stable_window_pass": True,
                    }
                )
            elif gate_id == "beside_mutual_exclusion":
                evidence.update(
                    {
                        "asset_derived_predicates": True,
                        "zero_overlap": True,
                        "table_clearance_pass": True,
                    }
                )
            elif gate_id == "asset_derived_scene_layout":
                evidence.update(
                    {
                        "fresh_scene_layout_realized": True,
                        "facility_clearance_pass": True,
                        "layout_payload_sha256": hash_json(layout),
                    }
                )
            elif gate_id == "same_arm_three_branch_planner":
                evidence.update(
                    {
                        "selected_execution_arm": arm,
                        "program_ids": list(PROGRAM_IDS),
                        "same_start_qpos_and_seed": True,
                        "complete_planner_chains": True,
                        "same_main_object_for_all_programs": True,
                        "same_execution_arm_for_all_programs": True,
                    }
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


class F2OfficialAssetCompatibilityMatrixV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = build_static_compatibility_matrix_v3()

    def test_asset_root_is_canonical_and_snapshot_location_independent(self):
        self.assertEqual(
            str(ASSET_ROOT),
            "/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets/objects",
        )
        self.assertTrue(ASSET_ROOT.is_dir())

    def test_complete_cartesian_product_and_official_inventory(self):
        checked = validate_static_compatibility_matrix_v3(self.matrix)
        self.assertEqual(checked["row_count"], 1650)
        for role, expected in EXPECTED_OFFICIAL_IDS.items():
            self.assertEqual(
                checked["inventory"]["families"][role]["model_ids"],
                list(expected),
            )
        self.assertEqual(checked["rows"][0]["candidate_key"], {
            "main_object_model_id": 0,
            "plastic_box_model_id": 0,
            "electronic_scale_model_id": 0,
            "beside_reference_model_id": 0,
        })
        self.assertEqual(checked["rows"][-1]["candidate_key"], {
            "main_object_model_id": 6,
            "plastic_box_model_id": 10,
            "electronic_scale_model_id": 6,
            "beside_reference_model_id": 4,
        })

    def test_static_rows_are_hash_bound_pending_and_never_preselected(self):
        self.assertIsNone(self.matrix["selected_row_sha256"])
        self.assertFalse(self.matrix["cpu_static_conditions_can_satisfy_dynamic_gates"])
        for row in (self.matrix["rows"][0], self.matrix["rows"][824], self.matrix["rows"][-1]):
            checked = validate_static_candidate_row_v3(row)
            self.assertFalse(checked["selection_eligible"])
            self.assertTrue(all(not checked["gates"][gate]["pass"] for gate in REQUIRED_GATE_IDS))
            self.assertTrue(all(checked["gates"][gate]["status"].startswith("pending_") for gate in REQUIRED_GATE_IDS))

    def test_row_and_matrix_tamper_fail_closed(self):
        row = copy.deepcopy(self.matrix["rows"][0])
        row["candidate_key"]["plastic_box_model_id"] = 9
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_static_candidate_row_v3(row)
        matrix = copy.deepcopy(self.matrix)
        matrix["rows"][0]["selection_eligible"] = True
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_static_compatibility_matrix_v3(matrix)

    def test_center_line_or_submargin_inside_evidence_is_rejected(self):
        row = self.matrix["rows"][0]
        evidence = strict_evidence(row)
        evidence["center_line_or_axis_interval_only"] = True
        evidence["evidence_sha256"] = hash_json({k: v for k, v in evidence.items() if k != "evidence_sha256"})
        with self.assertRaisesRegex(ValueError, "full-envelope evidence failed"):
            validate_strict_inside_full_envelope_evidence_v3(
                evidence, candidate_key_sha256=row["candidate_key_sha256"]
            )
        evidence = strict_evidence(row)
        evidence["minimum_signed_margin_m"] = 0.004999
        evidence["evidence_sha256"] = hash_json({k: v for k, v in evidence.items() if k != "evidence_sha256"})
        with self.assertRaisesRegex(ValueError, "full-envelope evidence failed"):
            validate_strict_inside_full_envelope_evidence_v3(
                evidence, candidate_key_sha256=row["candidate_key_sha256"]
            )

    def test_static_or_incomplete_dynamic_claim_cannot_pass_gate(self):
        row = self.matrix["rows"][0]
        with self.assertRaisesRegex(ValueError, "explicit runtime/complete evidence"):
            build_gate_receipt_v3(
                row,
                gate_id="on_passive_stability",
                status="passed",
                evidence={"aabb_support_looks_large_enough": True},
            )

    def test_pending_earlier_row_prevents_later_selection(self):
        pending = apply_gate_receipts_v3(self.matrix["rows"][0], [])
        later = apply_gate_receipts_v3(
            self.matrix["rows"][1], all_pass_receipts(self.matrix["rows"][1])
        )
        self.assertIsNone(select_first_all_gates_pass_v3([pending, later]))

    def test_first_all_gate_pass_after_terminal_rejection_is_selected(self):
        first = self.matrix["rows"][0]
        rejected_receipt = build_gate_receipt_v3(
            first,
            gate_id="strict_full_object_inside_margin",
            status="rejected",
            evidence={"reason": "full_envelope_margin_failed"},
        )
        rejected = apply_gate_receipts_v3(first, [rejected_receipt])
        # All other Gates remain pending, so a later row is still not selectable.
        second = apply_gate_receipts_v3(
            self.matrix["rows"][1], all_pass_receipts(self.matrix["rows"][1])
        )
        self.assertIsNone(select_first_all_gates_pass_v3([rejected, second]))

        # Terminalize every Gate on the rejected row; then rank 1 is the first pass.
        receipts = [rejected_receipt]
        predecessor = rejected_receipt["gate_receipt_sha256"]
        for gate_id in REQUIRED_GATE_IDS[1:]:
            receipts.append(
                build_gate_receipt_v3(
                    first,
                    gate_id=gate_id,
                    status="rejected",
                    evidence={"reason": "earlier_gate_already_rejected"},
                    predecessor_gate_receipt_sha256=predecessor,
                )
            )
            predecessor = receipts[-1]["gate_receipt_sha256"]
        terminal_rejected = apply_gate_receipts_v3(first, receipts)
        selected = select_first_all_gates_pass_v3([terminal_rejected, second])
        self.assertEqual(selected["rank"], 1)

    def test_frozen_binding_requires_all_gates_and_is_tamper_evident(self):
        row = self.matrix["rows"][0]
        layout = {"layout_version": "test_asset_derived_layout_v1", "poses": {}}
        evaluated = apply_gate_receipts_v3(row, all_pass_receipts(row, layout=layout))
        binding = build_frozen_asset_layout_binding_v3(
            selected_row=evaluated,
            matrix_sha256=self.matrix["matrix_sha256"],
            selected_execution_arm="left",
            layout_version=layout["layout_version"],
            layout_payload=layout,
        )
        checked = validate_frozen_asset_layout_binding_v3(binding)
        self.assertEqual(checked["program_ids"], list(PROGRAM_IDS))
        self.assertTrue(checked["same_main_object_for_all_programs"])
        self.assertTrue(checked["same_execution_arm_for_all_programs"])
        self.assertFalse(checked["branch_specific_asset_or_arm_selection_allowed"])
        tampered = copy.deepcopy(binding)
        tampered["selected_candidate_key"]["main_object_model_id"] = 6
        with self.assertRaisesRegex(ValueError, "binding hash mismatch"):
            validate_frozen_asset_layout_binding_v3(tampered)


if __name__ == "__main__":
    unittest.main()
