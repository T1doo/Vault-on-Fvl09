"""Re-run frozen auditor cases and new V1.2 result classification on CPU fixtures."""
import importlib.util
import sys
import unittest
from unittest.mock import patch
from copy import deepcopy
from pathlib import Path
import json
import auditor_v1_2 as current
from admission_contract import AUDIT, JOB, module, sha, canonical

mp=AUDIT/"F2_RUN3_ADMISSION_APPROVED_MANIFEST_V1.json"
manifest=json.loads(mp.read_text())
b=module(current.BASE_PATH,"run3_legacy_audit_test",current.BASE_SHA)
b.EXPECTED_MANIFEST_PATH=mp
b.EXPECTED_MANIFEST_FILE_SHA256=sha(mp)
b.EXPECTED_MANIFEST_SHA256=manifest["manifest_sha256"]
b.EXPECTED_RUN_ID=manifest["run_id"]
s=importlib.util.spec_from_file_location("f2_v1_frozen_tests",AUDIT/"f2_controlled_insertion_route_gate_postrun_auditor_v1/test_auditor.py")
legacy=importlib.util.module_from_spec(s)
previous=sys.modules.get("auditor")
sys.modules["auditor"]=b
s.loader.exec_module(legacy)
if previous is None: sys.modules.pop("auditor")
else: sys.modules["auditor"]=previous

class FrozenAuditorRegression(legacy.PostrunAuditorTests):
    pass

class ClassificationTests(unittest.TestCase):
    def run_case(self, infrastructure=False, corrupt=False):
        f=legacy.valid_fixture()
        if infrastructure:
            f["job_terminal"]["pass"]=False
            f["job_terminal"]["error"]={"type":"RuntimeError","message":"synthetic infrastructure failure"}
            f["job_terminal"]["result"]=None
            payload=dict(f["job_terminal"]); payload.pop("receipt_sha256")
            f["job_terminal"]["receipt_sha256"]=canonical(payload)
        def rd(p,*args,**kw):
            n=Path(p).name
            if n.endswith(".terminal.json"): return f["guard_terminal"]
            if n.endswith(".start.json"): return f["guard_start"]
            if n=="job_terminal.json":
                if corrupt: raise ValueError("self hash mismatch")
                return f["job_terminal"]
            raise AssertionError(n)
        def strict(*args,**kw): return b.audit_documents(**f)
        with patch.object(current,"validate",return_value=(manifest,{})), patch.object(current,"module",return_value=b), patch.object(current,"read",side_effect=rd), patch.object(b,"audit_from_disk",side_effect=strict):
            return current.audit(mp)
    def test_success(self):
        r=self.run_case()
        self.assertTrue(r["scientific_gate_pass"],r)
        self.assertTrue(r["cleanup_pass"])
        self.assertTrue(r["evidence_integrity_pass"])
    def test_clean_infrastructure_failure(self):
        r=self.run_case(infrastructure=True)
        self.assertTrue(r["infrastructure_failure"],r)
        self.assertTrue(r["evidence_integrity_pass"],r)
        self.assertTrue(r["cleanup_pass"])
        self.assertFalse(r["scientific_gate_pass"])
    def test_corrupt_terminal(self):
        r=self.run_case(corrupt=True)
        self.assertFalse(r["evidence_integrity_pass"])
        self.assertFalse(r["scientific_gate_pass"])

if __name__=="__main__": unittest.main()
