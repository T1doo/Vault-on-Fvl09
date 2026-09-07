"""Late-release negative fixtures; no real acceptance or budget write."""
from pathlib import Path
import unittest
from unittest.mock import patch
from . import audit

def terminal_fixture():
    guard={'task_owned_cleanup_pass':False,'gpu_returned_to_idle_baseline':False,'lease_released':True}
    if not all(guard.get(k) is True for k in ('task_owned_cleanup_pass','gpu_returned_to_idle_baseline','lease_released')):
        raise ValueError('original guard blocked')
    return guard

def recovery_fixture():
    guard={'task_owned_cleanup_pass':False,'child_exit_code':0}
    if not guard.get('task_owned_cleanup_pass') or guard['child_exit_code']!=0:
        raise ValueError('producer guard blocked')
    return guard

class Tests(unittest.TestCase):
    def test_original_failed_guard_is_never_virtualized(self):
        t=audit.private_guard_predicate(terminal_fixture,kind='terminal',late_verified=True)
        r=audit.private_guard_predicate(recovery_fixture,kind='recovery',late_verified=True)
        self.assertFalse(t()['task_owned_cleanup_pass']);self.assertFalse(t()['gpu_returned_to_idle_baseline']);self.assertFalse(r()['task_owned_cleanup_pass'])
    def test_no_verified_late_gate_still_rejects(self):
        for fn,kind in ((terminal_fixture,'terminal'),(recovery_fixture,'recovery')):
            with self.assertRaises(ValueError):audit.private_guard_predicate(fn,kind=kind,late_verified=False)()
    def test_missing_late_files_pending_before_any_old_acceptance(self):
        with patch.object(audit,'late_binding',side_effect=AssertionError('not permitted yet')):
            report=audit.build_candidates(resolution_path='/nfs_share/lijunhui/Robotwin2/tmp/NO_LATE_PROOF',observation_path='unused',review_path='unused',budget_event_sha256='unused')
        self.assertEqual(report['eligible_candidate_cells'],0);self.assertFalse(report['acceptance_issued'])
    def test_real_late_resolution_and_budget_binding_only_no_six_cell_audit(self):
        b=audit.late_binding(audit.original.DEFAULT,resolution_path=audit.LATE_DIR/'LATE_RELEASE_RESOLUTION_001.json',
            observation_path=audit.LATE_DIR/'MAIN_HOST_OBSERVATION_004.json',review_path=audit.LATE_DIR/'PENDING_REVIEW_001.json',
            budget_event_sha256='095dcf658a41b151a5bb9a07f3c8675a5571e64ba4ffcd8ca17e50af21f7852f',
            resource_acceptance_path=audit.LATE_DIR/'RESOURCE_RELEASE_ACCEPTANCE_001.json')
        self.assertTrue(b['late_release_verified']);self.assertFalse(b['original_guard']['task_owned_cleanup_pass'])
        # Compile actual predicates to ensure no surprise AST mismatch later.
        audit.private_guard_predicate(audit.original.terminal_inputs,kind='terminal',late_verified=True)
        audit.private_guard_predicate(audit.recovery_v1.audit_later_current,kind='recovery',late_verified=True,overrides={'run':audit.current_audit_v2})

if __name__=='__main__':unittest.main(verbosity=2)
