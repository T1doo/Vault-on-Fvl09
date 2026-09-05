import unittest
import fcntl
import tempfile
from pathlib import Path
from manifest_contract import require_held_lease, exact_root_decision, F4ManifestContractError
from guarded_launcher import poll_baseline

class AuthorityCooldownTests(unittest.TestCase):
    def snap(self, busy=False, uuid="GPU-test"):
        return {"gpus":[{"index":2,"uuid":uuid,"memory_used_mib":14,"utilization_gpu_percent":91 if busy else 0,
                        "pstate":"P0" if busy else "P8","compute_processes":[]}]}
    def test_unlocked_and_held(self):
        with tempfile.TemporaryDirectory(dir="/nfs_share/lijunhui/Robotwin2/tmp") as d:
            p=Path(d)/"lease"; p.touch()
            with self.assertRaises(F4ManifestContractError): require_held_lease(p)
            with p.open("r+") as h:
                fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.assertTrue(require_held_lease(p))
    def test_transient_busy(self):
        seq=iter([self.snap(True),self.snap()])
        r=poll_baseline(self.snap(),2,"GPU-test",snapshot=lambda:next(seq),sleep=lambda _:None)
        self.assertTrue(r["pass"]); self.assertEqual(r["poll_count"],2)
    def test_never_idle(self):
        r=poll_baseline(self.snap(),2,"GPU-test",snapshot=lambda:self.snap(True),sleep=lambda _:None)
        self.assertFalse(r["pass"]); self.assertEqual(r["poll_count"],13)
    def test_uuid_change(self):
        r=poll_baseline(self.snap(),2,"GPU-test",snapshot=lambda:self.snap(uuid="GPU-other"),sleep=lambda _:None)
        self.assertFalse(r["pass"])
    def test_snapshot_error(self):
        def fail(): raise RuntimeError("synthetic snapshot failure")
        self.assertFalse(poll_baseline(self.snap(),2,"GPU-test",snapshot=fail,sleep=lambda _:None)["pass"])
    def test_denial_quoting_token_is_not_approval(self):
        self.assertFalse(exact_root_decision({"decision":"DENY",
           "authorized":False,"text":"APPROVE_ONE_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2"}))
    def test_exact_positive(self):
        d={"schema_version":"cmf_external_execution_decision_v1","decision":"F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2",
           "authorized":True,"candidate":"f4-slot-corridor-hv2-r01","programs":["F4-ABC","F4-ACB","F4-BAC"],
           "maximum_root_invocations":1,"maximum_accepted_development_roots":1,
           "maximum_accepted_development_trajectories":3,"maximum_formal_trajectories":0}
        self.assertTrue(exact_root_decision(d))
        d["maximum_root_invocations"]=True
        self.assertFalse(exact_root_decision(d))

if __name__=="__main__": unittest.main()
