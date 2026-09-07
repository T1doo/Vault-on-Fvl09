import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from goal_pilot48_v1.runtime import issue_f2_single_relation as issuer

class Tests(unittest.TestCase):
    def test_two_pure_builders_real_parent_failed_and_unattempted(self):
        from goal_pilot48_v1.runtime_v3 import manifest_contract,budget
        files=[issuer.ROOT/n for n in ('STATE.json','budget_ledger.jsonl','attempts.jsonl','pilot_cells.json')];before={p:p.read_bytes() for p in files}
        for relation,job in (('on','p48_f2_on_release_revision1_cpu_fixture'),('beside','p48_f2_beside_qualification_cpu_fixture')):
            reserve={'kind':'RESERVE','job_id':job,'reserved':dict(issuer.CAPS),'event_sha256':'CPU_FIXTURE_NOT_REAL_RESERVATION'}
            m=issuer.build_manifest(job,reserve,relation=relation)
            self.assertEqual(m['qualification_relation_order'],[relation]);self.assertEqual(m['reserved']['solver_problems'],4)
            self.assertEqual(m['jobs'][0]['timeout_seconds'],1800);self.assertEqual(m['reserved']['gpu_lease_seconds'],1980)
            self.assertEqual(m['parent_relation_status'],'FAILED_RELEASE_IK' if relation=='on' else 'UNATTEMPTED')
            with tempfile.TemporaryDirectory(dir=issuer.W/'Robotwin2/tmp',prefix='single_relation_cpu_') as tmp:
                path=Path(tmp)/'CPU_FIXTURE_NOT_ISSUED.json'
                with path.open('x',encoding='utf-8') as f:json.dump(m,f,ensure_ascii=False)
                with patch.object(budget,'snapshot',return_value={'active_reservations':{job:reserve}}),patch.object(budget,'rows',return_value=[reserve]):
                    checked=manifest_contract.load_manifest(path,execution=False)
                self.assertEqual(checked['manifest_sha256'],m['manifest_sha256'])
        self.assertEqual({p:p.read_bytes() for p in files},before)
    def test_wrong_namespace_or_reservation_rejected(self):
        with self.assertRaises(ValueError):issuer.fresh('p48_f2_on_beside_qualification_001','on')
        with self.assertRaises(ValueError):issuer.build_on_revision_manifest('p48_f2_on_release_revision1_cpu_fixture',{})
