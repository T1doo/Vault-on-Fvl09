"""Only negative terminal fixtures while the real producer is still running."""
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch
from realization_utf8_io_v1 import write_new
from . import audit

class Tests(unittest.TestCase):
    def test_missing_producer_terminal_is_pending_not_accepted(self):
        with tempfile.TemporaryDirectory(dir=audit.W/'Robotwin2/tmp') as directory:
            terminal,pending=audit.terminal_inputs(Path(directory)/'p48_f4_b_motion_CPU')
            self.assertIsNone(terminal);self.assertEqual(pending['eligible_candidate_cells'],0)
            self.assertEqual(pending['status'],'pending_producer_terminal')
    def test_provisional_is_never_read_as_final(self):
        with tempfile.TemporaryDirectory(dir=audit.W/'Robotwin2/tmp') as directory:
            out=Path(directory);write_new(out/'branches/F4-ABC/receipt.provisional.json',{'status':'accepted','CPU_fixture':True})
            with self.assertRaisesRegex(ValueError,'provisional receipt'):
                audit.audit_motion_branch(out,'F4-ABC',{},None)
    def test_pure_builder_stops_before_any_raw_or_recovery_when_pending(self):
        pending={'status':'pending_producer_terminal','eligible_candidate_cells':0,'missing_files':['CPU_fixture']}
        with patch.object(audit,'terminal_inputs',return_value=(None,pending)),patch.object(audit,'root_inputs',side_effect=AssertionError('must not run acceptance')):
            result=audit.build_candidates(Path('/nfs_share/lijunhui/Robotwin2/tmp/CPU_only'))
        self.assertEqual(result['eligible_candidate_cells'],0);self.assertFalse(result['acceptance_issued']);self.assertFalse(result['pilot_cells_modified'])
    def test_six_memory_only_candidates_match_actual_48_cell_schema(self):
        document=audit.read(audit.ROOT/'pilot_cells.json');before=deepcopy(document)
        template=next(c for c in document['cells'] if c['status']=='accepted_existing')['evidence']
        candidates=[]
        for i,(pid,real) in enumerate((p,r) for p in audit.PROGRAMS for r in ('r_pc','r_inv_motion')):
            e=deepcopy(template);e.update(family='F4',pilot='B',program_id=pid,realization=real,root_id='CPU_fixture_B',
                current_sha256='CPU_B_current',candidate_universe_sha256='CPU_B_candidates',raw_id='CPU_B_raw_'+str(i),
                trace_sha256='CPU_B_trace_'+str(i),rollout_id='CPU_B_rollout_'+str(i),video_sha256='CPU_B_video_'+str(i),
                pilot_input_accepted=False,CPU_SCHEMA_FIXTURE_NOT_REAL_EVIDENCE=True)
            candidates.append(dict(family='F4',pilot='B',program_id=pid,realization=real,status='verified_candidate_pending_main_registration',evidence=e))
        result=audit.preview_registration(document,candidates)
        self.assertTrue(result['pass']);self.assertEqual(result['registered_accepted'],24);self.assertEqual(document,before)
    def test_wrong_pre_post_GPU_UUID_rejected(self):
        row={'index':7,'uuid':'GPU-CPU-fixture'}
        guard={'physical_gpu_index':7,'gpu_uuid':'GPU-CPU-fixture',**{k:{'gpus':[dict(row)]} for k in ('pre_snapshot','launch_snapshot','post_snapshot')}}
        start={'physical_gpu_index':7,'gpu_uuid':'GPU-CPU-fixture','pre_snapshot':{'gpus':[dict(row)]}}
        self.assertEqual(audit.gpu_identity(guard,start)['physical_gpu_index'],7)
        guard['post_snapshot']['gpus'][0]['uuid']='GPU-other'
        with self.assertRaises(ValueError):audit.gpu_identity(guard,start)

if __name__=='__main__':unittest.main(verbosity=2)
