"""Real generic dispatcher path with CPU fake meter/runtime, no GPU or reserve."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from goal_pilot48_v1.runtime import issue_tangent_micro as issuer
from goal_pilot48_v1.runtime_v2 import job_runner

class FakeMeter:
    def __init__(self,*args):
        self.counts=dict(solver_problems=3,fresh_scenes=1,action_scenes=1,collection_attempts=0)
        self.setup_action_calls=0;self.model_constructions=0;self.warmups_skipped=0;self.collection_hooks=[]
    def configure_collection_contract(self,m):pass
    def install(self):pass
    def close(self):pass

class Tests(unittest.TestCase):
    def run_case(self,local_queries):
        job='p48_f3_tangent_micro_cpu_dispatch_probe'
        m=issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=dict(issuer.CAPS),event_sha256='0'*64))
        self.assertEqual(m['jobs'][0]['kind'],'F3_MICRO')
        runtime=SimpleNamespace(run=lambda manifest:dict(accounting_complete=True,scene_attempts=1,trajectory_queries=local_queries,pass_=True))
        runtime.run=lambda manifest:{'accounting_complete':True,'scene_attempts':1,'trajectory_queries':local_queries,'pass':True}
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            out=Path(directory)/'CPU_FIXTURE';m['jobs'][0]['output_namespace']=str(out)
            body=dict(m);body.pop('manifest_sha256');m['manifest_sha256']=issuer.digest(body)
            with patch.object(job_runner,'load_manifest',return_value=m),patch.object(job_runner,'Meter',FakeMeter),patch.object(job_runner.importlib,'import_module',return_value=runtime):
                code=job_runner.main(['--manifest',str(Path(directory)/'IN_MEMORY_ONLY.json')])
            terminal=json.loads((out/'goal_terminal.json').read_text(encoding='utf-8'))
        return code,terminal
    def test_local2_meter3_is_accounting_failure(self):
        code,t=self.run_case(2);self.assertEqual(code,1);self.assertFalse(t['accounting_complete']);self.assertFalse(t['pass'])
    def test_local3_meter3_is_accounting_success(self):
        code,t=self.run_case(3);self.assertEqual(code,0);self.assertTrue(t['accounting_complete']);self.assertTrue(t['pass'])
if __name__=='__main__':unittest.main()
