import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import runtime
from .policy import EXPECTED

def old_snapshot(scene,adapter,spec):
    materials = [[.3,.3]]
    if not materials or any(v!=[.5,.5] for v in materials):
        raise ValueError('actual bottle material changed')
    return {'actual_materials':materials}

class Tests(unittest.TestCase):
    def test_overlay_changes_only_material_metadata_not_nominal_physics(self):
        path=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/goal_pilot48_v1/f3_upright_design_v1/design_spec.json')
        original=json.loads(path.read_text(encoding='utf-8'))
        with patch.object(runtime.hd.base,'read_spec',return_value=original):
            result=runtime.corrected_spec({})
        self.assertEqual(original['friction_unchanged'],{'static':.5,'dynamic':.5})
        self.assertEqual(result['friction_unchanged'],{'static':EXPECTED[0],'dynamic':EXPECTED[1]})
        for key,value in original.items():
            if key not in ('friction_unchanged','receipt_sha256'):
                self.assertEqual(result[key],value)
        self.assertEqual(result['parent_design_receipt_sha256'],original['receipt_sha256'])

    def test_actual_values_saved_before_rejecting_mismatch(self):
        for valid in (True,False):
            with self.subTest(valid=valid), tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
                evidence={'pass':valid,'actual_shape_materials':[[.5,.5,0.]],'physical_material_written':False}
                with patch.object(runtime.hd.base,'snapshot',old_snapshot), patch.object(runtime.policy,'capture',return_value=evidence):
                    fn=runtime.snapshot_with_material_record(directory)
                    if valid:
                        self.assertEqual(fn(None,None,None)['actual_materials'],[[.3,.3]])
                    else:
                        with self.assertRaisesRegex(ValueError,'unchanged loader baseline'):
                            fn(None,None,None)
                saved=json.loads((Path(directory)/'actual_material_baseline.json').read_text(encoding='utf-8'))
                self.assertEqual(saved['pass'],valid)
                self.assertEqual(saved['actual_shape_materials'],[[.5,.5,0.]])

    def test_unreviewed_scope_rejected_without_runner(self):
        with patch.object(runtime,'private_runner') as runner:
            with self.assertRaises(ValueError):runtime.run({},meter=object())
            runner.assert_not_called()
