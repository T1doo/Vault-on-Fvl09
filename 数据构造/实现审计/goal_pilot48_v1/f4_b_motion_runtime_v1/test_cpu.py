"""Private original pipeline/control fixtures; no actual B root is fabricated."""
from copy import deepcopy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from ..runtime_v2.meter import Meter
from ..collection_meter_review_v1.test_cpu import Adapter
from ..f4_b_runtime_v1.binding import PROGRAMS
from ..f4_b_program_runtime_v1.runtime import SOURCE_SHA
from .pipeline import build_pipeline
from . import runtime as r
from .binding import root_inputs

class Tests(unittest.TestCase):
    def test_missing_B_root_cannot_construct_cells_or_execute(self):
        with self.assertRaises(KeyError):root_inputs({})
        meter=SimpleNamespace(closed=False,counts={k:0 for k in r.CAPS})
        with patch.object(r,'build_pipeline',side_effect=AssertionError('no parent root')):
            with self.assertRaises(KeyError):r.run({'jobs':[{'resource_caps':r.CAPS,'requires_live_meter':True}]},meter=meter)
    def test_module_factory_hook_is_actual_function_globals(self):
        pipeline=build_pipeline({},SOURCE_SHA)
        self.assertIs(pipeline.collect_cell.__globals__,pipeline.__dict__)
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            meter=Meter(Path(directory)/'meter',r.CAPS)
            meter.configure_collection_contract({'implementation_source_sha256':SOURCE_SHA,'jobs':[{'family':'F4','requires_live_meter':True,'resource_caps':r.CAPS}]})
            adapters=[]
            def factory(cell,out):a=Adapter();a.family='F4';adapters.append(a);return a
            pipeline.make_adapter=factory
            with meter.instrument_collector_factory(pipeline,profile_for_cell=lambda c:SOURCE_SHA):
                self.assertIs(pipeline.collect_cell.__globals__['make_adapter'],pipeline.make_adapter)
                for pid in PROGRAMS:
                    a=pipeline.make_adapter({},None)
                    with a.scene({'family':'F4','slot_id':'CPU_B'},phase='strict_prefix_branch:'+pid,program={'program_id':pid}):pass
            self.assertIs(pipeline.make_adapter,factory);self.assertEqual(meter.counts['collection_attempts'],3)
            self.assertTrue(all('scene' not in vars(a) for a in adapters));meter.close()
    def test_original_motion_branch_changes_controls_without_planner(self):
        pipeline=build_pipeline({},SOURCE_SHA)
        controls=[{'position':np.zeros((11,6)), 'velocity':np.zeros((11,6))} for _ in range(30)]
        targets=[{'segment_id':f'{i}_carry_mid' if i in (4,14,24) else str(i),'pose':[0,0,1,1,0,0,0]} for i in range(30)]
        spec={'actual_prefix_end_qpos_sha256':'CPU_PARENT','targets':targets}
        cell={'source_suffix':'/nfs_share/lijunhui/Robotwin2/tmp/CPU_NOT_READ/frozen_suffix_artifact.json','variant':'r_inv_motion','targets':targets,'changed_indices':[4,14,24]}
        scene=SimpleNamespace(robot=SimpleNamespace(left_entity=SimpleNamespace(get_qpos=lambda:np.zeros(38))))
        with patch('controlled_multi_future.frozen_suffix_artifact_v1.load_frozen_suffix_artifact',return_value=({'execution_spec':spec},None,controls)),patch('controlled_multi_future.family_runners_v3_1._plan_chain',side_effect=AssertionError('motion must not plan')),patch('controlled_multi_future.family_runners_v3_3.install_frozen_suffix_controls') as install:
            result,new,transforms=pipeline.plan_or_load_controls(cell,scene)
        self.assertEqual(result['new_solver_query_count'],0);self.assertEqual(len(transforms),3);self.assertEqual(install.call_count,1)
        for i in range(30):self.assertEqual(len(new[i]['position']),12 if i in (4,14,24) else 11)
        self.assertTrue(all(len(c['position'])==11 for c in controls))
    def test_B_factory_rejects_F1_and_path_variants(self):
        pipeline=build_pipeline({},SOURCE_SHA)
        for cell in ({'family':'F1','variant':'r_inv_motion'},{'family':'F4','variant':'r_inv_path'}):
            with self.assertRaises(ValueError):pipeline.make_adapter(cell,None)
        pipeline=build_pipeline({'planned_spec':{'slot_id':'CPU_B'}},SOURCE_SHA)
        with self.assertRaises(ValueError):pipeline.make_adapter({'family':'F4','variant':'r_inv_motion',
            'parent_root':'/nfs_share/lijunhui/Robotwin2/datasets/cmf_f4_v22_authorized_root1/development_root','parent_root_id':'CPU_B'},None)
    def test_local_raw_and_artifact_writers_are_private_not_original(self):
        from controlled_multi_future.raw_writer import write_raw_attempt
        from controlled_multi_future.frozen_suffix_artifact_v1 import write_frozen_suffix_artifact
        pipeline=build_pipeline({},SOURCE_SHA)
        self.assertIsNot(pipeline.write_raw_attempt,write_raw_attempt)
        self.assertIsNot(pipeline.write_frozen_suffix_artifact,write_frozen_suffix_artifact)
        self.assertNotIn('write_raw_attempt',pipeline.collect_cell.__code__.co_varnames)

if __name__=='__main__':unittest.main(verbosity=2)
