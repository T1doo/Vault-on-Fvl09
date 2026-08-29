import json
from pathlib import Path
import unittest

import numpy as np

from controlled_multi_future.f3_pre_v_evidence_v4 import (
    F3PreVBoundaryGateFailure,
    HOLD_FRAME_COUNT,
    PRE_V_BOUNDARY_ORDER,
    PRE_V_PREDICATE_ORDER,
    build_f3_pre_v_evidence_v4,
    canonical_json_sha256,
    require_f3_pre_v_gate,
    validate_f3_pre_v_evidence_v4,
)


THRESHOLDS = {
    "eef_linear_speed_mps": 0.010,
    "eef_angular_speed_rps": 0.050,
    "bottle_linear_speed_mps": 0.020,
    "bottle_angular_speed_rps": 0.050,
    "grasp_translation_drift_m": 0.005,
    "grasp_orientation_drift_rad": 0.050,
}


def _boundaries():
    return {
        name: np.asarray([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
        for name in PRE_V_BOUNDARY_ORDER
    }


def _rows():
    return [
        {
            "step_index": np.int64(1000 + index),
            "timestamp": np.float64((1000 + index) / 250.0),
            "eef_linear_velocity": np.zeros(3, dtype=np.float32),
            "eef_angular_velocity": np.zeros(3, dtype=np.float64),
            "actor_linear_velocity": np.zeros(3, dtype=np.float64),
            "actor_angular_velocity": np.zeros(3, dtype=np.float64),
            "selected_gripper_contact": np.bool_(True),
            "selected_contact_actor_name": "f3_main_bottle",
            "contact_pairs": [
                {
                    "body_a": "fl_link7",
                    "body_b": "f3_main_bottle",
                    "point_count": np.int64(2),
                    "impulse_norm_sum": np.float64(0.01),
                }
            ],
        }
        for index in range(HOLD_FRAME_COUNT)
    ]


def _build(*, rows=None, boundaries=None):
    return build_f3_pre_v_evidence_v4(
        hold_rows=_rows() if rows is None else rows,
        boundary_transforms=_boundaries() if boundaries is None else boundaries,
        thresholds=THRESHOLDS,
        expected_actor_name="f3_main_bottle",
        selected_gripper_link_names=("fl_link7", "fl_link8"),
        support_actor_names=("table", "f3_original_pad"),
        planner_metadata={
            "query_count": np.int64(14),
            "segment_receipts": [{"segment_id": "center", "status": "Success"}],
            "trace_path": Path("partial_trace.npz"),
        },
        route_metadata={
            "route_version": "f3_clearance_segmented_slow_carry_v3",
            "central_xy": np.asarray([-0.08, -0.05]),
        },
    )


class F3PreVEvidenceV4Test(unittest.TestCase):
    def test_passing_payload_carries_all_eight_predicates_and_metadata(self):
        evidence = _build()
        self.assertTrue(evidence["pass"])
        self.assertTrue(evidence["eight_predicate_pass"])
        self.assertTrue(evidence["free_space_contact_pass"])
        self.assertEqual(
            tuple(evidence["predicates"]), PRE_V_PREDICATE_ORDER
        )
        self.assertEqual(len(evidence["predicates"]), 8)
        self.assertEqual(evidence["failed_predicates"], [])
        self.assertEqual(evidence["hold_window"]["frame_count"], 50)
        self.assertEqual(len(evidence["hold_window"]["frames"]), 50)
        self.assertEqual(evidence["planner_metadata"]["query_count"], 14)
        self.assertEqual(
            evidence["planner_metadata"]["trace_path"], "partial_trace.npz"
        )
        self.assertEqual(len(evidence["planner_metadata_sha256"]), 64)
        self.assertEqual(len(evidence["route_metadata_sha256"]), 64)
        self.assertEqual(len(evidence["evidence_sha256"]), 64)
        json.dumps(evidence, allow_nan=False)
        self.assertEqual(evidence, validate_f3_pre_v_evidence_v4(evidence))
        self.assertEqual(evidence, require_f3_pre_v_gate(evidence))

    def test_all_eight_predicates_are_independently_reported(self):
        rows = _rows()
        rows[0]["eef_linear_velocity"] = [0.011, 0.0, 0.0]
        rows[1]["eef_angular_velocity"] = [0.051, 0.0, 0.0]
        rows[2]["actor_linear_velocity"] = [0.021, 0.0, 0.0]
        rows[3]["actor_angular_velocity"] = [0.051, 0.0, 0.0]
        rows[4]["selected_gripper_contact"] = False
        rows[5]["selected_contact_actor_name"] = "wrong_actor"
        boundaries = _boundaries()
        boundaries["post_lift"][:3] = [0.006, 0.0, 0.0]
        angle = 0.051
        boundaries["post_center_high"][3:] = [
            np.cos(angle / 2.0),
            np.sin(angle / 2.0),
            0.0,
            0.0,
        ]

        evidence = _build(rows=rows, boundaries=boundaries)
        self.assertFalse(evidence["pass"])
        self.assertEqual(
            evidence["failed_predicates"], list(PRE_V_PREDICATE_ORDER)
        )
        self.assertEqual(
            evidence["grasp_boundaries"]["per_boundary"]["post_lift"][
                "translation_drift_m"
            ],
            0.006,
        )
        self.assertAlmostEqual(
            evidence["grasp_boundaries"]["per_boundary"][
                "post_center_high"
            ]["orientation_drift_rad"],
            angle,
        )

    def test_quaternion_sign_is_orientation_equivalent(self):
        boundaries = _boundaries()
        boundaries["pre_shared_V"][3:] *= -1.0
        evidence = _build(boundaries=boundaries)
        self.assertEqual(
            evidence["grasp_boundaries"]["per_boundary"]["pre_shared_V"][
                "orientation_drift_rad"
            ],
            0.0,
        )
        self.assertTrue(evidence["predicates"]["grasp_orientation_stable"])

    def test_free_space_contacts_are_preserved_and_fail_aggregate_only(self):
        rows = _rows()
        rows[7]["contact_pairs"].append(
            {"body_a": "f3_main_bottle", "body_b": "f3_original_pad"}
        )
        rows[8]["contact_pairs"].append(
            {"body_a": "fl_link8", "body_b": "table"}
        )
        evidence = _build(rows=rows)
        self.assertTrue(evidence["eight_predicate_pass"])
        self.assertFalse(evidence["free_space_contact_pass"])
        self.assertFalse(evidence["pass"])
        self.assertEqual(evidence["failed_predicates"], [])
        self.assertEqual(
            set(evidence["failed_supplemental_checks"]),
            {
                "bottle_has_no_pad_or_table_contact",
                "selected_gripper_has_no_pad_or_table_contact",
            },
        )
        audit = evidence["free_space_contact_audit"]
        self.assertEqual(audit["first_bottle_support_contact_frame"], 7)
        self.assertEqual(
            audit["first_selected_gripper_support_contact_frame"], 8
        )

    def test_structured_exception_detaches_and_hashes_receipt(self):
        rows = _rows()
        rows[0]["selected_gripper_contact"] = False
        evidence = _build(rows=rows)
        error = F3PreVBoundaryGateFailure(evidence)
        evidence["failed_predicates"].clear()
        self.assertEqual(
            error.failed_predicates,
            ("selected_gripper_contact_continuous",),
        )
        self.assertIn("selected_gripper_contact_continuous", str(error))
        receipt = error.to_receipt()
        digest = receipt.pop("failure_receipt_sha256")
        self.assertEqual(digest, canonical_json_sha256(receipt))
        with self.assertRaises(F3PreVBoundaryGateFailure) as caught:
            require_f3_pre_v_gate(error.evidence)
        self.assertEqual(caught.exception.failed_predicates, error.failed_predicates)
        with self.assertRaisesRegex(ValueError, "passing evidence"):
            F3PreVBoundaryGateFailure(_build())

    def test_invalid_window_nonfinite_and_tampering_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "exactly 50"):
            _build(rows=_rows()[:-1])
        nonfinite = _rows()
        nonfinite[0]["actor_linear_velocity"] = [np.nan, 0.0, 0.0]
        with self.assertRaisesRegex(ValueError, "finite"):
            _build(rows=nonfinite)
        evidence = _build()
        evidence["hold_window"]["frames"][0]["eef_linear_speed_mps"] = 1.0
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f3_pre_v_evidence_v4(evidence)


if __name__ == "__main__":
    unittest.main()
