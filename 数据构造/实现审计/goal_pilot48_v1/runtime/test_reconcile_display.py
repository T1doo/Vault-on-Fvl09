import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import reconcile_display as module

class Tests(unittest.TestCase):
    def test_completed_display_keeps_scientific_denominator(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'render';meter=Path(directory)/'render_meter';meter.mkdir()
            events=[{'kind':'CHARGE','resource':'fresh_scenes','amount':1},{'kind':'METER_CLOSED'}]
            with (meter/'events.jsonl').open('x',encoding='utf-8') as stream:
                for event in events:stream.write(json.dumps(event)+'\n')
            manifest={'manifest_sha256':'M','guard_directory':str(Path(directory)/'guard'),
                      'jobs':[{'kind':'HD_SAVED_STATE_RENDER','family':'DISPLAY','output_namespace':str(out)}]}
            guard={'job_id':'J','manifest_sha256':'M','task_owned_cleanup_pass':True,
                   'gpu_returned_to_idle_baseline':True,'child_pid':123,'elapsed_seconds':1.2,'receipt_sha256':'G'}
            terminal={'job_id':'J','manifest_sha256':'M','accounting_complete':True,'pass':True,
                      'runtime_result':{'render_pass':True,'scientific_route_pass':False},
                      'resource_counts':dict(solver_problems=0,fresh_scenes=1,action_scenes=0,collection_attempts=0)}
            with patch.object(module,'checked',side_effect=[manifest,guard,terminal]), \
                 patch.object(module,'sha',return_value='CPU'), \
                 patch.object(module.budget,'rows',return_value=[]), \
                 patch.object(module.budget,'reconcile',return_value={'event_sha256':'E'}) as reconcile, \
                 patch.object(module.budget,'append'), \
                 patch.object(module.budget,'read',return_value={'pilot_input_accepted':24}), \
                 patch.object(module.budget,'atomic') as atomic:
                module.main('J')
                state=atomic.call_args.args[1]
                self.assertEqual(state['pilot_input_accepted'],24)
                self.assertEqual(state['last_job']['status'],'DISPLAY_RENDER_COMPLETED_PENDING_VISUAL_REVIEW')
                self.assertEqual(reconcile.call_args.args[1]['gpu_lease_seconds'],3)

    def test_duplicate_is_read_only(self):
        with patch.object(module.budget,'rows',return_value=[{'kind':'RECONCILE','job_id':'J','event_sha256':'E'}]), \
             patch.object(module.budget,'reconcile') as reconcile,patch.object(module.budget,'atomic') as atomic:
            module.main('J');reconcile.assert_not_called();atomic.assert_not_called()

    def test_non_display_job_rejected(self):
        with patch.object(module.budget,'rows',return_value=[]), \
             patch.object(module,'checked',return_value={'jobs':[{'kind':'F3_MICRO','family':'F3'}]}), \
             patch.object(module.budget,'reconcile') as reconcile:
            with self.assertRaises(ValueError):module.main('J')
            reconcile.assert_not_called()
