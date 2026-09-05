import unittest
import json
from copy import deepcopy
from pathlib import Path
from admission_contract import *
from auditor_v1_2 import audit
MANIFEST= AUDIT/"F2_RUN3_ADMISSION_APPROVED_MANIFEST_V1.json"
class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.m=json.loads(MANIFEST.read_text())
        self.parent=json.loads(PARENT.read_text())
        self.p=json.loads(PROPOSAL.read_text())
        self.d=json.loads(DECISION.read_text())
    def test_exact_values(self):
        self.assertEqual(validate_values(self.m,self.parent,self.p,self.d)["TMPDIR"],82)
    def test_denial_reference_does_not_authorize(self):
        self.d["f2"]["decision"]="DENY "+TOKEN
        with self.assertRaises(ValueError): validate_values(self.m,self.parent,self.p,self.d)
    def test_wrong_ordinal(self):
        self.m["dispatch_ordinal"]=4
        with self.assertRaises(ValueError): validate_values(self.m,self.parent,self.p,self.d)
    def test_authority_missing(self):
        for key in ("third_dispatch_authorized","scene_execution_authorized","planner_execution_authorized"):
            m=deepcopy(self.m); m.pop(key)
            with self.assertRaises(ValueError): validate_values(m,self.parent,self.p,self.d)
    def test_no_physical(self):
        self.m["physical_execution_authorized"]=True
        with self.assertRaises(ValueError): validate_values(self.m,self.parent,self.p,self.d)
    def test_query_cap_change(self):
        self.m["jobs"][0]["planner_query_cap"]=12
        with self.assertRaises(ValueError): validate_values(self.m,self.parent,self.p,self.d)
    def test_path_overlength(self):
        self.m["cache_directory"]="/nfs_share/lijunhui/"+("x"*110)
        self.p["future_approved_manifest_delta"]["cache_directory"]=self.m["cache_directory"]
        with self.assertRaises(ValueError): validate_values(self.m,self.parent,self.p,self.d)
    def test_auditor_missing_terminal_cannot_pass(self):
        r=audit(MANIFEST)
        self.assertFalse(r["pass"])
        self.assertFalse(r["scientific_gate_pass"])
        self.assertIn("evidence_integrity_pass",r)
        self.assertIn("infrastructure_failure",r)
        self.assertIn("cleanup_pass",r)
if __name__=="__main__": unittest.main()
