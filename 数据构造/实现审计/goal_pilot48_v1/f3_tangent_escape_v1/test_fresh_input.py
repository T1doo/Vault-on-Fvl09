"""Saved006 physical inputs, explicit CPU fake GPU-state/factory outputs."""
import json,tempfile,unittest,copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from goal_pilot48_v1.f3_runtime_v5 import micro
from . import live
from .certificate import validate
A=micro.A;D=A.parents[2]/'Robotwin2/datasets'
class Tests(unittest.TestCase):
    def run_case(self,supported=False):
        d=D/'p48_f3_micro_006';full=json.loads((d/'postclose_attached_model.json').read_text(encoding='utf-8'))
        with np.load(d/'physical_trace.npz',allow_pickle=False) as z:
            fields={k:z[k] for k in ('eef_pose','object_pose','contact_pairs_json','timestamp','step_index')}
        rows=[{'eef':fields['eef_pose'][i],'actor_pose':fields['object_pose'][i],'contact_pairs':json.loads(str(fields['contact_pairs_json'][i])),
            'step_index':int(fields['step_index'][i]),'timestamp':float(fields['timestamp'][i])} for i in range(len(fields['object_pose'])-250,len(fields['object_pose']))]
        if supported:
            # Explicit synthetic positive-control fixture; never saved as data.
            first=rows[0];rows=[{**copy.deepcopy(first),'step_index':i,'timestamp':i*.004} for i in range(250)]
        export=json.loads((D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))
        base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))['solver_base_binding']['base_link_world_pose']
        # CPU input test corrects old export's solver transforms to physical base;
        # fake factories below deliberately do not claim a real cache/GPU test.
        from geometry import matrix
        import transforms3d as t3d
        for i,s in enumerate(export['shapes']):
            T=np.linalg.inv(matrix(base))@matrix(s['actor_world_pose'])@matrix(s['shape_local_pose']);s['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist()
            if s['role']!='pad':s['name']=s['role']+'__test'+str(i)
        mg=SimpleNamespace(tensor_args=None);planner=SimpleNamespace(motion_gen=mg,motion_gen_batch=mg,_cmf_solver_base_world_pose=base)
        scene=SimpleNamespace(robot=SimpleNamespace(left_planner=planner),trace=rows,bottle=SimpleNamespace(get_name=lambda:'f3_main_bottle'),pad=SimpleNamespace(get_name=lambda:'f3_original_pad'),selected_gripper_links=lambda:['fl_link7','fl_link8'],_cmf_tangent_scene_id='EXPLICIT_CPU_FIXTURE_006')
        calls=[]
        def query(*args):
            calls.append(1);valid=len(calls)>2
            return {'valid':valid,'status':None if valid else 'MotionGenStatus.INVALID_START_STATE_WORLD_COLLISION'},None
        def factory(cfg,world,cert,**kwargs):
            if supported:
                from support_pair_collision_v1.policy import verify_support_witness
                self.assertTrue(verify_support_witness(cert));self.assertFalse(validate(cert));self.assertEqual(cert['hold']['support_contact_frames'],250)
            else:self.assertTrue(validate(cert));self.assertEqual(cert['hold']['support_contact_frames'],16)
            return mg,{'CPU_FAKE_FACTORY_NOT_GPU_CONFORMANCE':True}
        overlap={'only_attached_bottle_support_pairs_overlap':True,'pairs':[{'link':'attached_bottle','obstacle':'pad__0','clearance_m':-.0045}]}
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as out,patch('geometry.capture_scene_collision_geometry',return_value=export),patch('model_apply.runtime_joint_state',return_value=(full['actual_joint_names'],np.array(full['actual_qpos']))),patch('model_apply.query_state',side_effect=query),patch('goal_pilot48_v1.runtime.support_witness.model_overlap_witness',return_value=overlap),patch('controlled_multi_future.family_runners_v3_1._entity',side_effect=lambda x:x),patch('goal_pilot48_v1.f3_tangent_escape_v1.factory.build_support_aware_motiongen',side_effect=factory),patch('support_pair_collision_v1.factory.build_support_aware_motiongen',side_effect=factory):
            live.prepare(scene,Path(out),lambda *args:full)
            self.assertEqual(scene._cmf_escape_model_branch,'old_supported' if supported else 'tangent_unloading');self.assertEqual(len(calls),4)
            if not supported:
                self.assertEqual(scene._cmf_escape_certificate['table_contact_frames'],0)
                self.assertFalse(scene._cmf_escape_certificate['old_supported_hold_pass'])
    def test_006_actual_hold_preserves16_not250_in_new_schema(self):self.run_case()
    def test_synthetic250_support_keeps_old_branch(self):self.run_case(supported=True)
if __name__=='__main__':unittest.main()
