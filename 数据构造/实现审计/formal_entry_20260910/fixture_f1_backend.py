"""Explicit CPU synthetic backend ONLY. Never a physical sample or production backend."""
import importlib.util,json,hashlib
from pathlib import Path
from copy import deepcopy
import numpy as np


def make_backend(*,spec,realization,output_root,source_sha):
    path=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
    loader=importlib.util.spec_from_file_location('formal_cpu_synthetic_backend',path)
    fixture=importlib.util.module_from_spec(loader);loader.loader.exec_module(fixture)
    from controlled_multi_future.geometry import transform_local_point
    class Backend(fixture.StrictPrefixSyntheticAdapter):
        def build_programs(self,scene): return deepcopy(spec['programs'])
        def capture_current(self,scene):
            current=super().capture_current(scene)
            destination=Path(output_root)/'observations'/('fixture_'+scene.phase.replace(':','_'))
            destination.mkdir(parents=True,exist_ok=True)
            arrays={k:np.full((spec['cameras']['height'],spec['cameras']['width'],3),i+1,dtype=np.uint8) for i,k in enumerate(spec['cameras']['required'])}
            arrays.update(robot_qpos=np.zeros(38),robot_qvel=np.zeros(38))
            np.savez_compressed(destination/'current.npz',**arrays)
            from controlled_multi_future.anchor import capture_physical_anchor_v2
            complete=capture_physical_anchor_v2(robot_qpos=np.zeros(38),robot_qvel=np.zeros(38),robot_drive_target=np.zeros(38),gripper_joint_qpos=np.zeros(4),actor_states={r['role']:{'pose':r['pose'],'linear_velocity':[0,0,0],'angular_velocity':[0,0,0],'sleep_state':False} for r in spec['roles'] if r['dynamic']},facility_poses={r['role']:r['pose'] for r in spec['roles'] if not r['dynamic']},physics_config={'explicit_synthetic_fixture':True},source_commit='explicit_fixture_not_physics',metadata={})
            (destination/'anchor.json').write_text(json.dumps(complete))
            capture={'current_hashes':current,'spec_sha256':spec['spec_sha256'],'capture_source':'explicit_synthetic_fixture','npz_sha256':hashlib.sha256((destination/'current.npz').read_bytes()).hexdigest()}
            (destination/'capture.json').write_text(json.dumps(capture));scene.fixture_capture=destination/'capture.json'
            return current
        def plan_suffix_from_actual_prefix_end_state(self,scene,program,replay):
            result=super().plan_suffix_from_actual_prefix_end_state(scene,program,replay)
            result['execution_spec']['targets'][0]['segment_id']='rest'
            result['execution_spec']['segment_receipts'][0]['segment_id']='rest'
            return result
        def execute_frozen_suffix_spec(self,scene,program,execution_spec,replay,realization_spec):
            result=super().execute_frozen_suffix_spec(scene,program,execution_spec,replay,realization_spec)
            n=100+(spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames'] if realization=='r_inv_motion' else 0)
            streams=result['streams'];audit=result['audit_streams']
            for group in (streams,audit):
                for key,value in list(group.items()):
                    if key=='field_metadata':continue
                    arr=np.asarray(value)
                    group[key]=np.repeat(arr[:1],n if len(arr)==4 else n+1,axis=0)
            streams['controller_effective_setpoint'][:2]=self.arrays['effective_setpoint_actions']
            if realization=='r_inv_path':streams['controller_effective_setpoint'][20,1]=.02
            streams['controller_effective_setpoint'][3,0]={'F1-red':1,'F1-green':2,'F1-blue':3}[program['program_id']]
            streams['requested_command']=streams['controller_effective_setpoint'].copy()
            streams['action_interval_start_timestamps']=np.arange(n)/250
            streams['action_interval_end_timestamps']=np.arange(1,n+1)/250
            streams['state_timestamps']=np.arange(n+1)/250
            streams['realized_qpos']=np.zeros((n+1,38));streams['realized_qvel']=np.zeros((n+1,38))
            streams['realized_eef']=np.tile([0,0,.9,1,0,0,0]*2,(n+1,1))
            if realization=='r_inv_path':streams['realized_eef'][10:30,1]=.02
            box=next(r for r in spec['roles'] if r['role']=='common_box')['pose']
            role=program['target_role']
            for r in spec['roles']:
                pose=np.asarray(r['pose'],dtype=float).copy()
                if r['role']==role:pose[:3]=transform_local_point(box,[0,.047,0])
                audit['role_object_pose__'+r['role']]=np.tile(pose,(n+1,1))
                audit['role_object_pose__'+r['role']][:3]=r['pose']
                for stem in ('linear_velocity','angular_velocity','component_linear_velocity','component_angular_velocity'):
                    audit['role_object_'+stem+'__'+r['role']]=np.zeros((n+1,3))
                    audit['role_object_'+stem+'_measured__'+r['role']]=np.zeros(n+1,dtype=bool)
                audit['role_object_component_velocity_provenance_json__'+r['role']]=np.array(['{}']*(n+1))
            audit['object_pose']=audit['role_object_pose__'+role].copy()
            for key in ('role_object_linear_velocity__'+role,'role_object_angular_velocity__'+role,'eef_linear_velocity','eef_angular_velocity'):
                audit[key]=np.zeros((n+1,3))
            for name in ('left','right'):
                for kind in ('target','velocity_target'):
                    audit[f'{name}_gripper_joint_drive_{kind}']=np.zeros((n+1,1))
            audit['contact_pairs_json']=np.array([json.dumps([{'body_a':'formal_f1_'+role,'body_b':'formal_f1_common_box'}])]*(n+1))
            for key in audit:
                if key!='field_metadata' and key not in audit['field_metadata']:audit['field_metadata'][key]={'status':'derived','source':'explicit synthetic fixture, not measured physics'}
            result['provenance'].update(synthetic=True,formal_current_capture_path=str(scene.fixture_capture),formal_root_id=spec['root_id'],formal_spec_sha256=spec['spec_sha256'],realization_spec=realization_spec)
            return result
    return Backend()
