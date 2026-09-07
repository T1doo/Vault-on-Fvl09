"""Actual generic dispatcher; explicit CPU-only runtime/meter fixtures."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from goal_pilot48_v1.runtime_v2 import job_runner
class Meter:
    def __init__(self,*a):
        self.counts=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0)
        self.setup_action_calls=0;self.model_constructions=0;self.warmups_skipped=0;self.collection_hooks=[]
    def configure_collection_contract(self,m):pass
    def install(self):pass
    def close(self):pass
class Tests(unittest.TestCase):
    def case(self,count):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'CPU_ONLY'
            m={'manifest_sha256':'CPU_ONLY_IN_MEMORY','jobs':[{'family':'F3','job_id':'CPU_ONLY','kind':'F3_MICRO','model_variant':'ONE_SIDED_UNLOADING_V2',
                'output_namespace':str(out),'runtime_module':'goal_pilot48_v1.f3_runtime_v6.micro','resource_caps':dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0)}]}
            runtime=SimpleNamespace(run=lambda m:{'pass':True,'accounting_complete':True,'scene_attempts':1,'trajectory_queries':count})
            with patch.object(job_runner,'load_manifest',return_value=m),patch.object(job_runner,'Meter',Meter),patch.object(job_runner.importlib,'import_module',return_value=runtime):
                code=job_runner.main(['--manifest',str(out/'NOT_WRITTEN.json')])
            result=json.loads((out/'goal_terminal.json').read_text(encoding='utf-8'))
        return code,result
    def test_local2_vs_meter3_rejected(self):
        code,r=self.case(2);self.assertEqual(code,1);self.assertFalse(r['accounting_complete'])
    def test_local3_vs_meter3_passes(self):
        code,r=self.case(3);self.assertEqual(code,0);self.assertTrue(r['accounting_complete'])
if __name__=='__main__':unittest.main()
