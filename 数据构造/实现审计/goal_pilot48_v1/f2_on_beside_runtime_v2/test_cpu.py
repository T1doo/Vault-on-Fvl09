import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from .runtime import json_values,LiveBackend
from goal_pilot48_v1.f2_on_beside_runtime_v1 import runtime as old,gates
from goal_pilot48_v1.f2_on_final_serialization_review_v1 import recover

class Tests(unittest.TestCase):
    def test_actual_old_trace_final_recompute_and_old_error_reproduced(self):
        result=recover.run();saved=recover.load(recover.OUT/'RECOVERY_REVIEW_001.json');self.assertEqual(result,saved)
        self.assertTrue(result['derived_final_predicates_pass']);self.assertTrue(result['original_error_reproduced'])
        self.assertFalse(result['original_suffix_pass']);self.assertFalse(result['full_root_or_pilot_acceptance'])
    def test_actual_old_final_call_vs_new_boundary_same_values(self):
        scene,spec,_,_=recover.scene_from_trace();held=recover.load(recover.D/'on/model_019_original_held_gate.json')
        def save(label,value):recover.digest(value);return value
        backend=LiveBackend.__new__(LiveBackend);backend.scene=scene;backend.spec=spec;backend.transport=held;backend.models=SimpleNamespace(save=save)
        with self.assertRaisesRegex(TypeError,'bool_'):old.LiveBackend.final_gate(backend)
        actual=backend.final_gate();self.assertTrue(actual['pass']);self.assertTrue(all(type(v) is bool for v in actual['checks'].values()))
    def test_false_numpy_bool_and_nonfinite_do_not_become_pass(self):
        backend=LiveBackend.__new__(LiveBackend);backend.scene=backend.spec=backend.transport=None
        backend.models=SimpleNamespace(save=lambda label,value:value)
        with patch.object(gates,'final',return_value={'pass':np.bool_(False),'checks':{'support':np.bool_(False)}}):
            result=backend.final_gate();self.assertIs(result['pass'],False);self.assertIs(result['checks']['support'],False)
        with self.assertRaises(ValueError):recover.digest(json_values({'x':np.float64(np.nan)}))
        self.assertEqual(json_values({'x':np.int64(7),'a':np.array([True,False])}),{'x':7,'a':[True,False]})
