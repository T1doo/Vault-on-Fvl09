"""Real immutable root resource-resolution binding; no scene/collection."""
from pathlib import Path
import unittest
from unittest.mock import patch
from .binding import root_inputs,ACCEPTANCE
from goal_pilot48_v1.runtime.issue_f4_b_stage_a import A,W,sha

def real_job():
    out=W/'Robotwin2/datasets/p48_f4_b_root_001';paths=dict(source_root_goal_terminal=out/'goal_terminal.json',
        source_root_guard_terminal=out.parent/'p48_f4_b_root_001_guard/p48_f4_b_root_001.terminal.json',
        source_root_manifest=A/'goal_pilot48_v1/jobs/p48_f4_b_root_001.json',
        source_root_resource_acceptance=A/'goal_pilot48_v1/f4_b_acceptance_audit_v1/RESOURCE_ACCOUNTING_ACCEPTANCE_001.json')
    job={}
    for name,path in paths.items():job[name+'_path']=str(path);job[name+'_file_sha256']=sha(path)
    return job

class Tests(unittest.TestCase):
    def test_real_failed_goal_plus_exact_resolution_permits_only_B_motion_preparation(self):
        root,bound,receipt=root_inputs(real_job())
        self.assertEqual(root.parent.name,'p48_f4_b_root_001');self.assertEqual(receipt['status'],'accepted')
        self.assertEqual(bound['planned_spec']['seed'],2026090604)
        self.assertFalse((root/'current/current_arrays.npz').exists())
    def test_missing_budget_reconcile_chain_rejected(self):
        with patch('goal_pilot48_v1.f4_b_motion_runtime_v2.binding.budget_rows',return_value=[]):
            with self.assertRaises(ValueError):root_inputs(real_job())
    def test_changed_resource_acceptance_file_hash_rejected(self):
        job=real_job();job['source_root_resource_acceptance_file_sha256']='0'*64
        with self.assertRaises(ValueError):root_inputs(job)

if __name__=='__main__':unittest.main(verbosity=2)
