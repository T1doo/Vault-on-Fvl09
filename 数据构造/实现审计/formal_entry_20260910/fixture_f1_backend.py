"""Explicit CPU simulation boundary, never native physical collection evidence."""
import importlib.util,json,hashlib
from pathlib import Path
from copy import deepcopy
import numpy as np


def physical_contact(a,b,position,normal=(0,0,1),separation=-.0001,impulse=0.):
    from controlled_multi_future.f3_physical_contact_signal_v8 import canonical_json_sha256
    identities=[]
    for i,name in enumerate((a,b)):
        x={'available':True,'body_name':name,'body_collision_shape_index':i,'shape_type':'explicit_fixture','local_pose':[0,0,0,1,0,0,0],'collision_groups':[1,1,0,i],'contact_offset_m':.02,'rest_offset_m':0.,'identity_source':'explicit_cpu_fixture'};x['identity_sha256']=canonical_json_sha256(x);identities.append(x)
    return {'contact_pair_schema_version':'cmf_runtime_contact_pair_v2','body_a':a,'body_b':b,'point_count':1,'impulse_norm_sum':impulse,'impulse_available':True,'shape_identity_available':True,'shape_identities':identities,'point_evidence':[{'point_index':0,'impulse_norm':impulse,'impulse_available':True,'signed_separation_m':separation,'signed_separation_available':True,'shape_identity_available':True,'shape_identity_sha256':[x['identity_sha256'] for x in identities],'position':list(position),'normal':list(normal)}]}


def make_backend(*,spec,realization,output_root,source_sha):
    path=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
    loader=importlib.util.spec_from_file_location('formal_cpu_synthetic_backend',path);fixture=importlib.util.module_from_spec(loader);loader.loader.exec_module(fixture)
    from controlled_multi_future.geometry import transform_local_point
    from file_source_pin import inventory,bundle_hash
    from f1_disk_verifier import STAGES,frozen_contract
    contract=frozen_contract(spec);source_bundle=bundle_hash(inventory())
    class Backend(fixture.StrictPrefixSyntheticAdapter):
        def build_programs(self,scene):return deepcopy(spec['programs'])
        def capture_current(self,scene):
            current=super().capture_current(scene);destination=Path(output_root)/'observations'/('fixture_'+scene.phase.replace(':','_'));destination.mkdir(parents=True,exist_ok=True)
            arrays={k:np.full((spec['cameras']['height'],spec['cameras']['width'],3),i+1,dtype=np.uint8) for i,k in enumerate(spec['cameras']['required'])};arrays.update(robot_qpos=np.zeros(38),robot_qvel=np.zeros(38))
            np.savez_compressed(destination/'current.npz',**arrays)
            from controlled_multi_future.anchor import capture_physical_anchor_v2
            complete=capture_physical_anchor_v2(robot_qpos=np.zeros(38),robot_qvel=np.zeros(38),robot_drive_target=np.zeros(38),gripper_joint_qpos=np.zeros(4),actor_states={r['role']:{'pose':r['pose'],'linear_velocity':[0,0,0],'angular_velocity':[0,0,0],'sleep_state':False} for r in spec['roles'] if r['dynamic']},facility_poses={r['role']:r['pose'] for r in spec['roles'] if not r['dynamic']},physics_config={'explicit_synthetic_fixture':True},source_commit='explicit_fixture_not_physics',metadata={})
            (destination/'anchor.json').write_text(json.dumps(complete))
            capture={'current_hashes':current,'root_id':spec['root_id'],'spec_sha256':spec['spec_sha256'],'source_bundle_sha256':source_bundle,'capture_source':'explicit_synthetic_fixture','npz_sha256':hashlib.sha256((destination/'current.npz').read_bytes()).hexdigest()}
            (destination/'capture.json').write_text(json.dumps(capture));scene.fixture_capture=destination/'capture.json';return current
        def plan_suffix_from_actual_prefix_end_state(self,scene,program,replay):
            result=super().plan_suffix_from_actual_prefix_end_state(scene,program,replay);prototype=deepcopy(result);targets=[];receipts=[];controls=[]
            names=[n for n in STAGES if n not in ('post_prefix_hold','gripper_close','gripper_open','release_settle','rest_settle')]
            for i,name in enumerate(names):
                pose=[0,0,.9,1,0,0,0]
                if name=='safe_horizontal' and realization=='r_inv_path':pose[1]=contract['path']['offset_y_m']
                targets.append({'segment_id':name,'pose':pose});receipt=deepcopy(prototype['execution_spec']['segment_receipts'][0]);receipt.update(segment_id=name,goal_eef_pose=pose);receipts.append(receipt)
                control=deepcopy(prototype['_execution_controls'][0]);control['position']=np.zeros((3,6),dtype=np.float32);control['position'][:,0]=(i+1)*.001+{'F1-red':.01,'F1-green':.02,'F1-blue':.03}[program['program_id']];control['position'][:,1]=pose[1];control['velocity']=np.zeros((3,6),dtype=np.float32);control['_cmf_planner_query'].update(query_id=i+1,source=name,goal_eef_pose=pose);controls.append(control)
            result['execution_spec'].update(targets=targets,segment_receipts=receipts,formal_path_baseline_pose=[0,0,.9,1,0,0,0],formal_path_prescribed_offset_y_m=contract['path']['offset_y_m'] if realization=='r_inv_path' else 0.0);result['_execution_controls']=controls
            # Existing fixture receipt parser reports its own bounded planner counter.
            return result
        def execute_frozen_suffix_spec(self,scene,program,execution_spec,replay,realization_spec):
            result=super().execute_frozen_suffix_spec(scene,program,execution_spec,replay,realization_spec)
            from controlled_multi_future.family_runners_v3_3 import _cached_controls
            controls=_cached_controls(scene,execution_spec);by_controls={t['segment_id']:v for t,v in zip(execution_spec['targets'],controls)}
            stages=[];row=3
            for name in STAGES:
                length=contract['motion']['additional_frames'] if name=='post_prefix_hold' and realization=='r_inv_motion' else 0 if name=='post_prefix_hold' else 75 if name.endswith('_settle') else 4 if name.startswith('gripper_') else 3
                stages.append({'name':name,'start_row':row,'end_row':row+length});row+=length
            n=row;streams=result['streams'];audit=result['audit_streams']
            for group in (streams,audit):
                for key,value in list(group.items()):
                    if key=='field_metadata':continue
                    arr=np.asarray(value);group[key]=np.repeat(arr[:1],n if len(arr)==4 else n+1,axis=0)
            actions=np.zeros((n,26));actions[:2]=self.arrays['effective_setpoint_actions'];actions[2]=actions[1];eef=np.tile([0,0,.9,1,0,0,0]*2,(n+1,1))
            for stage in stages:
                name=stage['name'];a,b=stage['start_row'],stage['end_row'];actions[a:b]=actions[a-1]
                if name in by_controls:
                    actions[a:b,:6]=by_controls[name]['position'];actions[a:b,12:18]=by_controls[name]['velocity']
                    target=next(t['pose'] for t in execution_spec['targets'] if t['segment_id']==name);eef[a+1:b+1,:7]=target
            streams['controller_effective_setpoint']=actions;streams['requested_command']=actions.copy();streams['action_interval_start_timestamps']=np.arange(n)/250;streams['action_interval_end_timestamps']=np.arange(1,n+1)/250;streams['state_timestamps']=np.arange(n+1)/250
            streams['realized_qpos']=np.zeros((n+1,38));streams['realized_qvel']=np.zeros((n+1,38));streams['realized_eef']=eef
            box=next(r for r in spec['roles'] if r['role']=='common_box')['pose'];role=program['target_role']
            for r in spec['roles']:
                pose=np.asarray(r['pose'],dtype=float).copy()
                if r['role']==role:pose[:3]=transform_local_point(box,[0,.047,0])
                audit['role_object_pose__'+r['role']]=np.tile(pose,(n+1,1));audit['role_object_pose__'+r['role']][:4]=r['pose']
                for stem in ('linear_velocity','angular_velocity','component_linear_velocity','component_angular_velocity'):
                    audit['role_object_'+stem+'__'+r['role']]=np.zeros((n+1,3));audit['role_object_'+stem+'_measured__'+r['role']]=np.zeros(n+1,dtype=bool)
                audit['role_object_component_velocity_provenance_json__'+r['role']]=np.array(['{}']*(n+1))
            # Auxiliary object_pose deliberately remains red, as in native prefix trace.
            audit['object_pose']=audit['role_object_pose__red'].copy()
            for key in ('eef_linear_velocity','eef_angular_velocity'):audit[key]=np.zeros((n+1,3))
            audit['realized_left_gripper_joint_qpos']=np.full((n+1,2),.045)
            for name in ('left','right'):
                for kind in ('target','velocity_target'):audit[f'{name}_gripper_joint_drive_{kind}']=np.zeros((n+1,1))
            support=physical_contact('formal_f1_'+role,'formal_f1_common_box',transform_local_point(box,[0,.025,0]))
            contact_rows=[json.dumps([support])]*(n+1)
            grasp_stage=next(x for x in stages if x['name']=='gripper_close')
            grasp=physical_contact('formal_f1_'+role,'fixture_finger',transform_local_point(box,[0,.047,0]),normal=(1,0,0),impulse=.001)
            for index in range(grasp_stage['start_row']+1,grasp_stage['end_row']+1):contact_rows[index]=json.dumps([support,grasp])
            audit['contact_pairs_json']=np.array(contact_rows);audit['selected_contact_actor_name']=np.array(['formal_f1_'+role]*(n+1))
            for key in audit:
                if key!='field_metadata' and key not in audit['field_metadata']:audit['field_metadata'][key]={'status':'derived','source':'explicit synthetic fixture, not measured physics'}
            result['provenance'].update(synthetic=True,formal_current_capture_path=str(scene.fixture_capture),formal_root_id=spec['root_id'],formal_spec_sha256=spec['spec_sha256'],source_bundle_sha256=source_bundle,realization_spec=realization_spec,audit_role_mapping={'target_role':role,'target_role_pose_field':'role_object_pose__'+role},formal_f1_stages={'executing_arm':'left','sample_rate_hz':250,'program_id':program['program_id'],'realization_id':realization,'prefix_acceptance_end_row':3,'subject_actor_name':'formal_f1_'+role,'robot_link_names':['fixture_finger'],'gripper_link_names':['fixture_finger'],'gripper_scale_m':[-.01,.045],'stages':stages},formal_f1_contract=contract)
            return result
    return Backend()
