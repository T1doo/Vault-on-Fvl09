"""Synthetic future-idle fixtures; no actual release/acceptance issued."""
from copy import deepcopy
import unittest
from .review import verify_future_idle,seal,same_original_baseline

class Tests(unittest.TestCase):
    def fixture(self):
        pre=dict(index=7,uuid='GPU-CPU',memory_used_mib=14,utilization_gpu_percent=0,pstate='P8',compute_processes=[])
        review=seal(dict(status='PENDING_REAL_LATE_IDLE_OBSERVATION',immutable_file_hashes={},original_guard_file_sha256='CPU_original',
            guard_pid=10,child_pid=11,child_pgid=11,task_user_uid=100,physical_gpu_index=7,gpu_uuid='GPU-CPU',original_pre_selected=pre,
            original_cooldown_last_captured_at='2026-09-07T04:00:00+00:00',original_guard_receipt_sha256='CPU_guard',
            proposed_actual_resources=dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3,gpu_lease_seconds=1922),CPU_TEST_FIXTURE=True))
        rows=[{**pre,'index':i,'uuid':'GPU-CPU' if i==7 else 'GPU-'+str(i)} for i in range(8)]
        obs=seal(dict(original_guard_file_sha256='CPU_original',job_id='p48_f4_b_motion_001',requested_owned_pids=[10,11],requested_child_pgid=11,
            current_uid=100,own_pid_and_group_absent=True,remaining_owned_process_rows=[],snapshot={'captured_at':'2026-09-07T05:00:00+00:00','gpus':rows},
            selected_gpu=pre,selected_gpu_idle_now=True,observed_at='2026-09-07T05:00:01+00:00',foreign_processes_signalled=False,CPU_TEST_FIXTURE=True))
        return review,obs
    def test_late_idle_can_be_verified_without_changing_original_Guard(self):
        review,obs=self.fixture();before=deepcopy(review)
        result=verify_future_idle(review,obs,now_utc='2026-09-07T05:00:02+00:00')
        self.assertTrue(result['late_baseline_restoration_verified']);self.assertTrue(result['original_guard_cleanup_pass_remains_false'])
        self.assertFalse(result['pilot_acceptance_issued']);self.assertEqual(review,before)
    def test_busy_foreign_gpu_never_accepted(self):
        review,obs=self.fixture();obs['selected_gpu']['compute_processes']=[{'pid':999}]
        obs['snapshot']['gpus'][7]=deepcopy(obs['selected_gpu']);obs=seal(obs)
        with self.assertRaises(ValueError):verify_future_idle(review,obs,now_utc='2026-09-07T05:00:02+00:00')
    def test_old_PID_worker_or_stale_observation_rejected(self):
        review,obs=self.fixture();obs['remaining_owned_process_rows']=[{'pid':11}]
        with self.assertRaises(ValueError):verify_future_idle(review,seal(obs),now_utc='2026-09-07T05:00:02+00:00')
        review,obs=self.fixture()
        with self.assertRaises(ValueError):verify_future_idle(review,obs,now_utc='2026-09-07T05:01:00+00:00')
    def test_baseline_threshold_not_relaxed(self):
        pre=self.fixture()[0]['original_pre_selected']
        for field,value in [('memory_used_mib',65),('utilization_gpu_percent',1),('pstate','P2')]:
            row=deepcopy(pre);row[field]=value;self.assertFalse(same_original_baseline(pre,row))
    def test_production_clock_override_forbidden(self):
        review,obs=self.fixture();review.pop('CPU_TEST_FIXTURE');review=seal(review)
        with self.assertRaises(ValueError):verify_future_idle(review,obs,now_utc='2026-09-07T05:00:02+00:00')

if __name__=='__main__':unittest.main(verbosity=2)
