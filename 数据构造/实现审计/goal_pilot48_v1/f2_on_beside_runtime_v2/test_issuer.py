import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from goal_pilot48_v1.runtime import issue_f2_beside_serialization as issuer
from goal_pilot48_v1.runtime.issue_f2_single_relation import CAPS,W

class Tests(unittest.TestCase):
    def test_new_beside_runtime_real_source_inputs_cpu_preflight(self):
        from goal_pilot48_v1.runtime_v3 import manifest_contract,budget
        job='p48_f2_beside_qualification_serialization_cpu_fixture'
        reservation={'kind':'RESERVE','job_id':job,'reserved':dict(CAPS),'event_sha256':'CPU_FIXTURE_NOT_REAL_RESERVATION'}
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes();m=issuer.build_manifest(job,reservation)
        self.assertEqual(before,ledger.read_bytes());self.assertEqual(m['qualification_relation'],'beside')
        self.assertEqual(m['jobs'][0]['runtime_module'],'goal_pilot48_v1.f2_on_beside_runtime_v2.runner_bridge')
        self.assertEqual(m['reserved']['solver_problems'],4);self.assertTrue(m['on_original_failed_terminal_unchanged'])
        with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='beside_jsonfix_cpu_') as tmp:
            p=Path(tmp)/'CPU_FIXTURE_NOT_ISSUED.json'
            with p.open('x',encoding='utf-8') as f:json.dump(m,f,ensure_ascii=False)
            with patch.object(budget,'snapshot',return_value={'active_reservations':{job:reservation}}),patch.object(budget,'rows',return_value=[reservation]):
                manifest_contract.load_manifest(p,execution=False)
        self.assertEqual(before,ledger.read_bytes())
