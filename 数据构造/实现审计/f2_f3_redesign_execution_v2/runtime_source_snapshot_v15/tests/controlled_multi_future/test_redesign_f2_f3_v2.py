from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from controlled_multi_future.redesign_f2_f3_v2.eligibility import empty_index, load_for_research, set_cell, write_index
from controlled_multi_future.redesign_f2_f3_v2.f2_geometry_v2 import synthetic_boundary_checks, verify_expected_relation
from controlled_multi_future.redesign_f2_f3_v2.observations import model_envelopes
from controlled_multi_future.redesign_f2_f3_v2.pilot_contract import expected_cells, planned_root_contract
from controlled_multi_future.redesign_f2_f3_v2.scene_spec import candidate_set_for, scene_spec
from controlled_multi_future.redesign_f2_f3_v2.strict_exit import StrictExitError, strict_negative_tests, validate_inputs_supervision_audit, validate_observable_inputs


class V2ContractTests(unittest.TestCase):
    def test_ab_specs_are_real_layout_variants(self):
        a = scene_spec("F2-A-v2"); b = scene_spec("F2-B-v2")
        self.assertNotEqual(a["spec_sha256"], b["spec_sha256"])
        self.assertNotEqual(a["f2"]["box_center_xyz"], b["f2"]["box_center_xyz"])
        self.assertEqual(a["f2"]["support_identity_by_relation"]["beside"], "table")
        self.assertAlmostEqual(a["f2"]["beside_target_xy"][0], 0.20)
        self.assertAlmostEqual(a["f2"]["beside_table_z"], 0.740)

    def test_beside_is_not_stand_top(self):
        checks = synthetic_boundary_checks()
        self.assertTrue(all(checks.values()))
        spec = scene_spec("F2-A-v2")
        result = verify_expected_relation(program_id="beside", pose=[0.08, -0.18, 0.825], spec=spec, contact={"stand_top_contact": True})
        self.assertFalse(result["pass"])

    def test_execution_order_supports_new_first_cells(self):
        f2 = planned_root_contract("F2-A-v2"); f3 = planned_root_contract("F3-A-v2")
        self.assertEqual(f2["execution_order"][0], "beside:r_pc")
        self.assertEqual(f3["execution_order"][0], "VHVH:r_pc")
        self.assertEqual(len(expected_cells("F2-A-v2")), 6)

    def test_strict_inputs_have_no_target(self):
        self.assertTrue(strict_negative_tests()["pass"])
        candidates = candidate_set_for(scene_spec("F2-A-v2"))
        value = {"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidates}
        validate_observable_inputs(value)
        with self.assertRaises(StrictExitError):
            validate_observable_inputs({**value, "target": candidates[0]})

    def test_f3_candidate_schema_is_ordered(self):
        value = {"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidate_set_for(scene_spec("F3-A-v2"))}
        self.assertEqual({c["event_sequence"] for c in value["candidate_set"]}, {"VVHH", "VHVH", "VHHV"})
        validate_observable_inputs(value)

    def test_envelopes_keep_target_out_of_inputs(self):
        bundle = {"images": {"head_camera": np.zeros((2, 2, 3), dtype=np.uint8)}, "state": {"joint_qpos": [0.0] * 38, "joint_qvel": [0.0] * 38}, "metadata": {"source": "test"}}
        candidates = candidate_set_for(scene_spec("F3-A-v2")); value = model_envelopes(bundle=bundle, future=np.zeros((3, 26)), candidates=candidates, target=candidates[0])
        self.assertNotIn("target", value["inputs"]); self.assertIn("target", value["supervision"]); self.assertIn("audit", value)
        validate_inputs_supervision_audit(inputs={"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidates}, supervision=value["supervision"], audit=value["audit"])

    def test_eligibility_blocks_legacy_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eligibility.json"; index = empty_index(); set_cell(index, cell_key="F2-A-v2:beside:r_pc", historical="ACCEPTED_IN_V1_HISTORY", current="BLOCKED", reasons=["legacy"]); write_index(path, index)
            with self.assertRaises(PermissionError): load_for_research(path, "F2-A-v2:beside:r_pc")


if __name__ == "__main__":
    unittest.main()
