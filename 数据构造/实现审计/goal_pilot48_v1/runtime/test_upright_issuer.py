import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import issue_upright_qualification as issuer

class Tests(unittest.TestCase):
    def test_pure_first_scope_and_generic_guard_contract(self):
        from goal_pilot48_v1.runtime_v3 import manifest_contract, budget
        j = 'p48_f3_upright_qualification_cpu_fixture'
        reservation = dict(kind='RESERVE', job_id=j, reserved=dict(issuer.CAPS), event_sha256='CPU-only')
        before = (issuer.ROOT/'budget_ledger.jsonl').read_bytes()
        m = issuer.build_manifest(j, reservation)
        self.assertEqual(before, (issuer.ROOT/'budget_ledger.jsonl').read_bytes())
        self.assertEqual(m['jobs'][0]['kind'], 'F3_UPRIGHT_QUALIFICATION')
        self.assertEqual(m['jobs'][0]['timeout_seconds'], 900)
        self.assertTrue(m['jobs'][0]['requires_live_meter'])
        self.assertFalse(m['confirmation_authorized_by_this_manifest'])
        self.assertFalse(m['shared_v_authorized'])
        self.assertNotIn('recipe_spec_path', m)
        self.assertNotIn('pregrasp_route_revision', m)
        with tempfile.TemporaryDirectory(dir=issuer.W/'Robotwin2/tmp', prefix='upright_issuer_cpu_') as directory:
            path = Path(directory)/'NOT_ISSUED.json'
            with path.open('x', encoding='utf-8') as stream:
                json.dump(m, stream, ensure_ascii=False)
            with patch.object(budget, 'snapshot', return_value={'active_reservations':{j:reservation}}), patch.object(budget, 'rows', return_value=[reservation]):
                manifest_contract.load_manifest(path, execution=False)

    def test_wrong_scope_or_budget_rejected(self):
        with self.assertRaises(ValueError):
            issuer.build_manifest('p48_f3_confirmation_001', {})
        with self.assertRaises(ValueError):
            issuer.build_manifest('p48_f3_upright_qualification_cpu_fixture', {})

if __name__ == '__main__':
    unittest.main()
