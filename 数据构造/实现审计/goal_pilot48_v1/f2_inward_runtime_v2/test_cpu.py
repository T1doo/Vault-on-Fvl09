import copy
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .contract import W, A, build_contract, parent_contract, validate_contract, manifest_lineage, digest, LAYOUT, SLOT
from . import runtime, runner_bridge
from goal_pilot48_v1.f2_inward_runtime_v1.test_cpu import StateTests
from goal_pilot48_v1.f2_inward_runtime_v1.test_issuer import result as meter_result, events as meter_events

class RevisionTests(unittest.TestCase):
    def test_actual_new_contract_and_three_relation_lineage(self):
        old = parent_contract(); new = build_contract()
        self.assertTrue(validate_contract(new))
        self.assertEqual(new['binding']['program_ids'], old['binding']['program_ids'])
        self.assertNotEqual(old['binding']['binding_sha256'], new['binding']['binding_sha256'])
        self.assertNotEqual(old['planned']['planned_root_slot_spec_sha256'], new['planned']['planned_root_slot_spec_sha256'])
        self.assertEqual(new['planned']['seed'], old['planned']['seed'])
        self.assertEqual(new['inward_goals']['C'], old['inward_goals']['C'])
        self.assertEqual(new['inward_goals']['N'], old['inward_goals']['N'])
        self.assertFalse(new['binding']['old_inside_qualification_inherited'])
        self.assertEqual(new['binding']['layout_version'], LAYOUT)
        self.assertEqual(new['planned']['slot_id'], SLOT)

    def test_reject_old_layout_and_old_goal(self):
        with self.assertRaises(ValueError): validate_contract(parent_contract())
        new = build_contract(); old = parent_contract()
        new['inward_goals']['U_new'] = old['inward_goals']['U_new']
        with self.assertRaises(ValueError): validate_contract(new)

    def test_private_globals_no_cross_import_pollution(self):
        from goal_pilot48_v1.f2_inward_runtime_v1 import runtime as parent_runtime
        original = parent_runtime.build_contract
        one = runtime.load_private_runtime({})
        two = runtime.load_private_runtime({})
        self.assertIsNot(one.__dict__, two.__dict__)
        self.assertIs(one.run.__globals__, one.__dict__)
        self.assertIs(parent_runtime.build_contract, original)
        self.assertIsNot(one.build_contract, original)
        self.assertEqual(parent_runtime.build_contract()['binding']['layout_version'], 'f2_beside_inward_layout_v1')

    def test_real_run_entry_builds_new_layout_before_any_scene(self):
        observed = {}
        def adapter(**kwargs):
            observed.update(kwargs)
            raise ImportError('CPU sentinel before real scene/model creation')
        fake_adapter = types.SimpleNamespace(RoboTwinRealSapienF2AssetBoundAdapterV3=adapter)
        fake_context = types.SimpleNamespace(_PinnedSapienRenderDeviceContextV1=object)
        with tempfile.TemporaryDirectory(dir=W / 'Robotwin2/tmp', prefix='f2_revision1_cpu_') as tmp:
            out = Path(tmp) / 'job'
            manifest = {'jobs': [{'output_namespace': str(out)}], 'implementation_source_sha256': 'cpu-not-execution', 'manifest_sha256': 'cpu', **manifest_lineage()}
            with patch.dict(sys.modules, {'controlled_multi_future.f2_asset_bound_runtime_v3': fake_adapter,
                                         'controlled_multi_future.real_sapien_adapter_high_level_v1': fake_context}):
                r = runtime.run(manifest)
            self.assertEqual(observed['binding']['layout_version'], LAYOUT)
            self.assertTrue((out / 'runtime_revision1_lineage.json').exists())
            self.assertEqual(r['fresh_scene_attempts'], 0)
            self.assertEqual(r['ik_problem_attempts'], 0)
            self.assertFalse(r['pass'])
            self.assertEqual(r['error']['type'], 'ImportError')

    def test_real_entry_rejects_unbound_old_manifest(self):
        with tempfile.TemporaryDirectory(dir=W / 'Robotwin2/tmp', prefix='f2_bad_revision_cpu_') as tmp:
            out = Path(tmp) / 'job'
            r = runtime.run({'jobs': [{'output_namespace': str(out)}], 'manifest_sha256': 'cpu-old'})
            self.assertEqual(r['error']['type'], 'ValueError')
            self.assertIn('exact revision1 lineage', r['error']['message'])
            self.assertEqual(r['fresh_scene_attempts'], 0)

    def test_bridge_complete_counting_and_missing_charge_rejected(self):
        for missing in (False, True):
            with tempfile.TemporaryDirectory(dir=W / 'Robotwin2/tmp', prefix='f2_revision_bridge_cpu_') as tmp:
                out = Path(tmp) / 'job'; out.mkdir()
                directory = Path(tmp) / 'job_meter'; directory.mkdir()
                rows = meter_events()
                if missing: rows.pop()
                (directory / 'events.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
                r = {**meter_result(), 'pass': True, 'receipt_sha256': 'cpu-parent'}
                with patch.object(runner_bridge, 'execute', return_value=r):
                    actual = runner_bridge.run({'jobs': [{'output_namespace': str(out)}]})
                self.assertEqual(actual['pass'], not missing)
                self.assertEqual(actual['accounting_complete'], not missing)

if __name__ == '__main__': unittest.main()
