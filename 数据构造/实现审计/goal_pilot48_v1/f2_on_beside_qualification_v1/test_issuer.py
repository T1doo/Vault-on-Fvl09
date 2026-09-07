import copy,json,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
from goal_pilot48_v1.runtime import issue_f2_on_beside as issuer

class Tests(unittest.TestCase):
    def test_pure_builder_actual_sources_and_generic_cpu_preflight(self):
        from goal_pilot48_v1.runtime_v3 import manifest_contract,budget
        job='p48_f2_on_beside_qualification_cpu_fixture'
        reservation={'kind':'RESERVE','job_id':job,'reserved':dict(issuer.CAPS),'event_sha256':'CPU_SYNTHETIC_NOT_A_REAL_RESERVATION'}
        files=[issuer.ROOT/name for name in ('budget_ledger.jsonl','attempts.jsonl','STATE.json','pilot_cells.json')]
        before={p:p.read_bytes() for p in files}
        m=issuer.build_manifest(job,reservation)
        self.assertEqual({p:p.read_bytes() for p in files},before)
        self.assertEqual(m['allowed_physical_gpu_indices'],list(range(8)));self.assertEqual(m['jobs'][0]['timeout_seconds'],3600)
        self.assertEqual(m['reserved']['gpu_lease_seconds'],3780);self.assertTrue(m['jobs'][0]['requires_live_meter'])
        self.assertEqual(m['qualification_relation_order'],['on','beside']);self.assertFalse(m['inside_contact_permission_used'])
        with tempfile.TemporaryDirectory(dir=issuer.W/'Robotwin2/tmp',prefix='onbeside_manifest_cpu_') as tmp:
            path=Path(tmp)/'CPU_FIXTURE_NOT_ISSUED.json'
            with path.open('x',encoding='utf-8') as f:json.dump(m,f,ensure_ascii=False)
            with patch.object(budget,'snapshot',return_value={'active_reservations':{job:reservation}}),patch.object(budget,'rows',return_value=[reservation]):
                loaded=manifest_contract.load_manifest(path,execution=False)
            self.assertEqual(loaded['manifest_sha256'],m['manifest_sha256'])
            original=manifest_contract.checked
            start_path=Path(m['guard_directory'])/(job+'.start.json')
            def checked(p,*a,**kw):
                if Path(p)==start_path:return {'physical_gpu_index':2,'gpu_uuid':'CPU_EXPECTED_UUID','manifest_sha256':m['manifest_sha256'],'guard_pid':999}
                return original(p,*a,**kw)
            with patch.object(budget,'snapshot',return_value={'active_reservations':{job:reservation}}),patch.object(budget,'rows',return_value=[reservation]),patch.object(manifest_contract,'checked',side_effect=checked),patch.object(os,'getppid',return_value=999),patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'CPU_WRONG_UUID','CMF_GPU_LEASE_PATH':str(issuer.W/'Robotwin2/gpu_leases/production_micro_gate_v1/physical_gpu_2.lock')}):
                with self.assertRaisesRegex(PermissionError,'Guard environment'):manifest_contract.load_manifest(path,runner=True)
        self.assertEqual({p:p.read_bytes() for p in files},before)
    def test_namespace_caps_hash_and_gpu_scope_fail_closed(self):
        with self.assertRaises(ValueError):issuer.fresh('p48_f2_inside_qualification_wrong')
        with self.assertRaises(ValueError):issuer.build_manifest('p48_f2_on_beside_qualification_cpu_fixture',{})
        p=str(issuer.PARENT)
        with self.assertRaises(ValueError):issuer.merge_checked({p:'bad'},{p:issuer.sha(p)})
