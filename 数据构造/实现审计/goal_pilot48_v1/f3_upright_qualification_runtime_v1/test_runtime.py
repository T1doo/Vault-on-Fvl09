import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import runtime
from .context import Counts
from goal_pilot48_v1.f3_upright_design_v1.test_cpu import snapshot as cpu_snapshot
class Tests(unittest.TestCase):
    def case(self,failure=None,mismatch=False):
        calls=[];specpath=runtime.A/'goal_pilot48_v1/f3_upright_design_v1/design_spec.json';spec=json.loads(specpath.read_text(encoding='utf-8'))
        meter=SimpleNamespace(counts=dict(solver_problems=0,fresh_scenes=0,action_scenes=0,collection_attempts=0))
        class Scene:
            planner_query_count=0;bottle=object();role_actors={}
            robot=SimpleNamespace(left_planner=SimpleNamespace(_cmf_solver_base_world_pose=[0,0,0,1,0,0,0],motion_gen=SimpleNamespace(kinematics=SimpleNamespace(joint_names=['fl_joint'+str(i) for i in range(1,7)]))))
            def initialize_trace(self,*a,**k):
                calls.append('trace')
                if failure=='bootstrap':raise ValueError('bootstrap')
                self.trace=[{'initial':True}]
            def save_trace(self,p):
                calls.append('save')
                if failure=='save':raise ValueError('save')
                with Path(p).open('xb') as f:np.savez_compressed(f,rows=np.zeros((1,1)))
        scene=Scene();adapter=SimpleNamespace(capture_current=lambda s:calls.append('current') or {},capture_anchor=lambda s:calls.append('anchor') or {})
        def make(s,out,c):
            self.local=c
            class Context:
                cleanup_receipt={'cleanup_safety_pass':True}
                def __enter__(self):c.setup();meter.counts['fresh_scenes']+=1;return SimpleNamespace(scene=scene)
                def __exit__(self,*a):calls.append('cleanup')
            return adapter,Context()
        def snap(*args):
            v=cpu_snapshot(spec)
            if failure=='standing':v['pad_physical_contact']=False
            return v
        def IK(scene,targets,native,out,c):
            for _ in range(2 if failure=='IK' else 3):c.ik();meter.counts['solver_problems']+=1
            calls.append('IK');return {'pass':failure!='IK','IK_problems':c.IK}
        def micro(scene,*a):
            self.local.action(scene);meter.counts['action_scenes']=1;scene.planner_query_count=1 if failure=='micro' else 3;meter.counts['solver_problems']+=scene.planner_query_count
            if mismatch:meter.counts['solver_problems']+=1
            calls.append('micro');return {'pass':failure!='micro','native_full_arm_controls_pass':True,'post_lift':{'pass':True},'full_world_restoration_checks':{k:{'valid':True} for k in ('motion_gen','motion_gen_batch')}}
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            caps=dict(solver_problems=6,fresh_scenes=1,action_scenes=1,collection_attempts=0)
            m={'upright_design_spec_path':str(specpath),'upright_design_spec_sha256':runtime.hashlib.sha256(specpath.read_bytes()).hexdigest(),'manifest_sha256':'CPU','reserved':{**caps,'gpu_lease_seconds':1080},'jobs':[{'output_namespace':str(Path(directory)/'run'),'kind':'F3_UPRIGHT_QUALIFICATION','requires_live_meter':True,'resource_caps':caps,'timeout_seconds':900}]}
            with patch.object(runtime,'make',side_effect=make),patch.object(runtime,'snapshot',side_effect=snap),patch.object(runtime,'capture',return_value={}),patch.object(runtime,'Checker',return_value=SimpleNamespace(check=lambda *a:{'pass':True})),patch.object(runtime,'qualify',side_effect=IK),patch.object(runtime,'execute',side_effect=micro),patch('model_apply.bind_actual_solver_base'),patch('model_apply.runtime_joint_state',return_value=(['fl_joint'+str(i) for i in range(1,7)],np.zeros(6))):
                r=runtime.run(m,meter=meter)
        return r,calls
    def test_full_order_and_split_counts6(self):
        r,c=self.case();self.assertTrue(r['qualified']);self.assertTrue(r['micro_pass']);self.assertTrue(r['scientific_route_pass']);self.assertEqual(r['IK_problems'],3);self.assertEqual(r['trajectory_queries'],3);self.assertEqual(c,['current','anchor','trace','IK','micro','save','cleanup'])
    def test_standing_stops_before_current_IK_action(self):
        r,c=self.case('standing');self.assertFalse(r['qualified']);self.assertEqual(r['local_counts']['solver_problems'],0);self.assertEqual(c,['cleanup'])
    def test_bootstrap_error_cannot_IK_or_act(self):
        r,c=self.case('bootstrap');self.assertFalse(r['pass']);self.assertNotIn('IK',c);self.assertNotIn('micro',c);self.assertIn('cleanup',c)
    def test_IK_failure_preserves_partial2(self):
        r,c=self.case('IK');self.assertFalse(r['qualified']);self.assertEqual(r['IK_problems'],2);self.assertEqual(r['trajectory_queries'],0);self.assertNotIn('micro',c)
    def test_micro_failure_keeps3plus1(self):
        r,c=self.case('micro');self.assertFalse(r['qualified']);self.assertEqual(r['local_counts']['solver_problems'],4)
    def test_live_meter_mismatch_fails(self):
        r,c=self.case(mismatch=True);self.assertFalse(r['accounting_complete']);self.assertFalse(r['qualified'])
    def test_trace_save_failure_keeps_cleanup(self):
        r,c=self.case('save');self.assertFalse(r['pass']);self.assertEqual(r['trace_error']['message'],'save');self.assertEqual(c[-1],'cleanup')
    def test_counts_cap_before_calls(self):
        c=Counts();c.setup()
        with self.assertRaises(RuntimeError):c.setup()
        for _ in range(3):c.ik()
        with self.assertRaises(RuntimeError):c.ik()
        c.steps=6000
        with self.assertRaises(RuntimeError):c.step()
if __name__=='__main__':unittest.main()
