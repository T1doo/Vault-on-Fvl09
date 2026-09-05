import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from candidate_executor import sequence
from manifest_contract import candidates,check_budget,EXPECTED
from job_runner import record_scene_attempt
from manifest_contract import validate_terminal,canonical
from unittest.mock import patch
import copy
class ExecutorTests(unittest.TestCase):
    def call(self,fail=None):
        seen=[]
        def execute(stage):seen.append("execute_"+stage);return {}
        def window(stage,r):seen.append("gate_"+stage);return {"pass":stage!=fail}
        def close():seen.append("close")
        def hold():seen.append("hold250")
        def lift():seen.append("lift25")
        def verify():seen.append("verify");return {"pass":True}
        return sequence(execute,window,close,hold,lift,verify),seen
    def test_pregrasp_failure_never_grasps_or_closes(self):
        r,s=self.call("pregrasp");self.assertEqual(s,["execute_pregrasp","gate_pregrasp"]);self.assertTrue(r["stop_before_close"])
    def test_grasp_failure_never_closes(self):
        r,s=self.call("grasp");self.assertNotIn("close",s);self.assertNotIn("lift25",s);self.assertFalse(r["pass"])
    def test_success_order(self):
        r,s=self.call();self.assertTrue(r["pass"])
        self.assertEqual(s,["execute_pregrasp","gate_pregrasp","execute_grasp","gate_grasp","close","hold250","lift25","verify"])
        self.assertFalse(r["shared_v_executed"])
    def test_exact_candidates(self):
        self.assertEqual([(r["recipe_id"],r["recipe_sha256"]) for r in candidates()],EXPECTED)
    def test_budget_52_12_4(self):self.assertTrue(check_budget(52,8,4,4))
    def test_53_queries_rejected(self):
        with self.assertRaises(ValueError):check_budget(53,8,4,4)
    def test_13_scenes_rejected(self):
        with self.assertRaises(ValueError):check_budget(52,9,4,4)
    def test_5_physical_rejected(self):
        with self.assertRaises(ValueError):check_budget(52,8,4,5)
    def test_invalid_counter(self):
        with self.assertRaises(ValueError):check_budget(True,8,4,4)

class AccountingTests(unittest.TestCase):
    def attempt(self,prepare=lambda s:None,execute=lambda s:{"pass":True},save=lambda s:None,cleanup_error=False):
        scene=SimpleNamespace(planner_query_count=0)
        context=SimpleNamespace(cleanup_receipt=None)
        @contextmanager
        def opened():
            try:yield scene,context
            finally:
                context.cleanup_receipt={"cleanup_safety_pass":not cleanup_error}
                if cleanup_error:raise RuntimeError("cleanup failure")
        return record_scene_attempt(opened,prepare,execute,save)
    def test_prepare_failure_preserves_zero_and_cleanup(self):
        def fail(s):raise ValueError("target derivation")
        r=self.attempt(prepare=fail)
        self.assertEqual(r["planner_delta"],0);self.assertTrue(r["accounting_complete"])
        self.assertTrue(r["cleanup"]["cleanup_safety_pass"]);self.assertIsNotNone(r["error"])
    def test_execution_failure_preserves_consumed_queries(self):
        def fail(s):s.planner_query_count=2;raise RuntimeError("planner failed")
        r=self.attempt(execute=fail);self.assertEqual(r["planner_delta"],2);self.assertTrue(r["cleanup"]["cleanup_safety_pass"])
    def test_missing_counter_is_unknown_not_zero(self):
        def fail(s):del s.planner_query_count
        r=self.attempt(execute=fail);self.assertIsNone(r["planner_delta"]);self.assertFalse(r["accounting_complete"])
    def test_trace_failure_preserves_accounting_and_cleanup(self):
        def fail(s):raise IOError("trace write")
        r=self.attempt(save=fail);self.assertEqual(r["planner_delta"],0);self.assertTrue(r["cleanup"]["cleanup_safety_pass"])
        self.assertEqual(r["error"][0]["stage"],"trace_finally")
    def test_scene_setup_failure_is_recorded(self):
        def fail():raise RuntimeError("scene init")
        r=record_scene_attempt(fail,None,None,None)
        self.assertEqual(r["planner_delta"],0);self.assertIsNone(r["cleanup"]);self.assertIsNotNone(r["error"])
    def test_cleanup_failure_not_success(self):
        r=self.attempt(cleanup_error=True);self.assertFalse(r["cleanup"]["cleanup_safety_pass"]);self.assertIsNotNone(r["error"])

class TerminalTests(unittest.TestCase):
    def terminal(self):
        rows=[]
        for i in range(2):
            r={"planner_delta":3,"error":None,"cleanup":{"cleanup_safety_pass":True}}
            r["receipt_sha256"]=canonical(r);rows.append(r)
        return {"planner_queries":6,"phase_queries":{"qualification":0,"physical":6},"planner_scenes":0,
            "physical_scenes":2,"physical_attempts":2,"scene_receipts":rows,"error":None,"accounting_complete":True,
            "physical_rows":[{"result":{"pass":True}},{"result":{"pass":True}}],"pass":True,
            "shared_v":0,"no_suffix":0,"root":0,"raw":0,"formal":0}
    def test_consistent_terminal(self):self.assertTrue(validate_terminal(self.terminal()))
    def test_query_mismatch_rejected(self):
        t=self.terminal();t["planner_queries"]=7
        with self.assertRaises(ValueError):validate_terminal(t)
    def test_forged_success_rejected(self):
        t=self.terminal();t["physical_rows"][0]["result"]["pass"]=False
        with self.assertRaises(ValueError):validate_terminal(t)
    def test_forbidden_shared_v_rejected(self):
        t=self.terminal();t["shared_v"]=1
        with self.assertRaises(ValueError):validate_terminal(t)
    def test_scientific_failure_is_valid_failure_receipt(self):
        t=self.terminal();t["physical_rows"][0]["result"]["pass"]=False;t["pass"]=False
        self.assertFalse(validate_terminal(t))

class GuardTests(unittest.TestCase):
    def test_cooldown_polling_bound(self):
        import guarded_launcher as g
        with patch.object(g,"_returned_to_baseline",return_value=False):
            seen=[];r=g.poll_baseline({},4,"GPU-test",snapshot=lambda:{},sleep=seen.append)
        self.assertFalse(r["pass"]);self.assertEqual(r["poll_count"],13);self.assertEqual(seen,[5]*12)
        self.assertTrue(r["lease_held_during_polling"])
    def test_cooldown_success(self):
        import guarded_launcher as g
        with patch.object(g,"_returned_to_baseline",side_effect=[False,True]):
            r=g.poll_baseline({},4,"GPU-test",snapshot=lambda:{},sleep=lambda s:None)
        self.assertTrue(r["pass"]);self.assertEqual(r["poll_count"],2)
    def test_reaped_leader_does_not_skip_worker_kill(self):
        import guarded_launcher as g
        from unittest.mock import Mock
        child=Mock(pid=123)
        with patch.object(g.os,"killpg") as kill:
            self.assertEqual(g._terminate_group(child),[])
        self.assertEqual(kill.call_count,2)
if __name__=="__main__":unittest.main()
