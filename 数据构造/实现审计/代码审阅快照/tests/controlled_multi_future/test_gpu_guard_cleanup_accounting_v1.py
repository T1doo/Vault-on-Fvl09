import unittest
from controlled_multi_future.probes.gpu_guard_v2_4 import build_task_owned_cleanup_audit_v1
class TestGpuGuardCleanupAccountingV1(unittest.TestCase):
 def test_external_arrival_is_not_task_cleanup_failure(self):
  x=build_task_owned_cleanup_audit_v1(child_exited=True,orphan_pids=[],owned_process_cleanup_errors=[],job_cache_cleanup={"succeeded":True},lease_release={"released":True},post_error=None,post_release={"verified":False,"new_compute_processes":[{"pid":123}]});self.assertTrue(x["task_owned_cleanup_pass"]);self.assertTrue(x["external_process_detected_after_release"]);self.assertFalse(x["gpu_returned_to_idle_baseline"]);self.assertFalse(x["cleanup_uncertain"])
 def test_unknown_memory_without_external_is_uncertain(self):
  x=build_task_owned_cleanup_audit_v1(child_exited=True,orphan_pids=[],owned_process_cleanup_errors=[],job_cache_cleanup={"succeeded":True},lease_release={"released":True},post_error=None,post_release={"verified":False,"new_compute_processes":[]});self.assertTrue(x["cleanup_uncertain"])
 def test_owned_orphan_is_uncertain(self):
  x=build_task_owned_cleanup_audit_v1(child_exited=True,orphan_pids=[9],owned_process_cleanup_errors=[],job_cache_cleanup={"succeeded":True},lease_release={"released":True},post_error=None,post_release={"verified":True,"new_compute_processes":[]});self.assertFalse(x["task_owned_cleanup_pass"]);self.assertTrue(x["cleanup_uncertain"])
if __name__=="__main__":unittest.main()
