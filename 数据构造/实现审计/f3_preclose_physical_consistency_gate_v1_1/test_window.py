import unittest
from copy import deepcopy
import importlib.util
from pathlib import Path
from gate import evaluate_window, base
import gate
gate.canonical_hash = base.canonical_hash
gate.evaluate_preclose_sequence = base.evaluate_preclose_sequence
gate.evaluate_preclose_stage = base.evaluate_preclose_stage
gate.gate_contract = base.gate_contract
# Reuse only V1 synthetic fixture constructors.
s = importlib.util.spec_from_file_location("fixtures", Path(__file__).resolve().parent.parent / "f3_preclose_physical_consistency_gate_v1/test_gate.py")
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent / "f3_preclose_physical_consistency_gate_v1"))
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class WindowTests(unittest.TestCase):
    def fixture(self):
        b = m.good_snapshot("pregrasp")
        rows = [{"row_index": i, "contact_signal_complete": True, "contact_pairs": [],
                 "bottle_position_m": list(b["initial_bottle_position_m"])} for i in (1,2,3)]
        return b, rows
    def test_good_window(self):
        b,r = self.fixture()
        v = evaluate_window(b,r,start=0,end=3)
        self.assertTrue(v["pass"])
        self.assertFalse(v["close_permitted_by_this_check"])
    def test_transient_mid_segment_self_collision(self):
        b,r = self.fixture()
        r[1]["contact_pairs"] = [m.contact_pair("fl_link6","fl_link4",impulse=.4,separation=-.001)]
        v = evaluate_window(b,r,start=0,end=3)
        self.assertFalse(v["pass"]); self.assertEqual(v["first_failure"]["row_index"],2)
    def test_transient_mid_segment_support_collision(self):
        b,r = self.fixture()
        r[1]["contact_pairs"] = [m.contact_pair("fl_link6","table",impulse=.4,separation=-.001)]
        self.assertFalse(evaluate_window(b,r,start=0,end=3)["pass"])
    def test_bottle_bump_then_return(self):
        b,r = self.fixture(); r[1]["bottle_position_m"][0] += .03
        v=evaluate_window(b,r,start=0,end=3)
        self.assertFalse(v["pass"]); self.assertAlmostEqual(v["maximum_bottle_displacement_m"],.03)
    def test_incomplete_contact_signal_in_middle_row(self):
        b,r=self.fixture(); r[1]["contact_signal_complete"]=False
        self.assertFalse(evaluate_window(b,r,start=0,end=3)["pass"])
    def test_missing_row_rejected(self):
        b,r=self.fixture()
        with self.assertRaises(ValueError): evaluate_window(b,r[:2],start=0,end=3)
    def test_positive_separation(self):
        b,r=self.fixture(); r[1]["contact_pairs"]=[m.contact_pair("fl_link6","fl_link4")]
        self.assertTrue(evaluate_window(b,r,start=0,end=3)["pass"])
    def test_incomplete_pair(self):
        b,r=self.fixture(); p=m.contact_pair("fl_link6","table"); p["shape_identity_available"]=False
        r[1]["contact_pairs"]=[p]
        self.assertFalse(evaluate_window(b,r,start=0,end=3)["pass"])

if __name__ == "__main__": unittest.main()
