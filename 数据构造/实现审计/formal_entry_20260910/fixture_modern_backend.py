"""Explicit synthetic cell-engine boundary for native-root lifecycle CPU tests.
No simulated robot success is claimed. Real finalizers/exporters consume its arrays.
"""
import json,copy,hashlib
from pathlib import Path
import numpy as np
from controlled_multi_future.redesign_f2_f3_v2.canonical import canonical_sha256,sha256_file,atomic_write_json
from controlled_multi_future.redesign_f2_f3_v2.finalizer import _prefix_artifact_hash
from controlled_multi_future.redesign_f2_f3_v2.f2_geometry_v2 import _rotation
PREFIX=101

def cell(*,spec,output,root_id,program_id,realization_id,artifact,collection,**kwargs):
 output=Path(output);output.mkdir(parents=True);f=spec['family'];resolved=spec['resolved_scene_spec'];motion=realization_id=='r_inv_motion';path=realization_id=='r_inv_path';n=650+(75 if motion else 0);p_end=PREFIX-1
 roles={r['role']:r['pose'] for r in resolved['roles'] if r['role']!='box'}
 if f=='F2':
  x,y,z=spec['f2']['box_center_xyz'];roles.update({k:[x,y,z,1,0,0,0] for k in ['box_bottom','box_left','box_right','box_front','box_back']})
 roles.update(table=[0,0,.74,1,0,0,0],wall=[0,.5,.8,1,0,0,0]);main='main_can' if f=='F2' else 'bottle';origin=np.asarray(roles[main]);obj=np.tile(origin,(n,1));eef=np.tile([0,0,1.05,1,0,0,0],(n,1)).astype(float)
 contact=np.ones(n,bool);contact[-100:]=False;grip=np.zeros((n,2));grip[-100:]=1
 base={'joint_qpos':np.zeros((n,38)),'joint_qvel':np.zeros((n,38)),'joint_qf':np.zeros((n,38)),'eef_pose':eef,'object_pose':obj,'gripper_command':grip,'selected_gripper_contact':contact,'step_index':np.arange(n),'timestamp':np.arange(n)*.004,'initial_state':np.arange(n)==0}
 for key in ['object_linear_velocity','object_angular_velocity','eef_linear_velocity','eef_angular_velocity']:base[key]=np.zeros((n,3))
 for r,p in roles.items():
  base['role_object_pose__'+r]=np.tile(p,(n,1));base['role_object_linear_velocity__'+r]=np.zeros((n,3));base['role_object_angular_velocity__'+r]=np.zeros((n,3))
 c={'schema_version':'synthetic_cell_fixture','synthetic':True,'root_id':root_id,'family':f,'program_id':program_id,'realization_id':realization_id,'scene_spec_sha256':spec['spec_sha256'],'candidate_set':copy.deepcopy(resolved['programs']),'trace_path':str(output/'trace.npz'),'status':'cell_pass','collection':collection,'realization_contract':{**spec['realization_requirements'][realization_id],'variant_applied':True},'prefix_end_trace_row':p_end,'exit_target':eef[-1].tolist(),'rest_target':eef[-1].tolist()}
 if f=='F2':
  target=resolved['targets'][program_id];desired=np.asarray(target.get('target',target.get('center',spec['f2']['box_center_xyz'])),dtype=float).copy()
  if program_id=='inside':desired[2]=.760
  final=np.r_[desired-_rotation(origin[3:])@np.array(spec['f2']['support_point_local_xyz']),origin[3:]];obj[PREFIX:]=final
  eef[PREFIX:301,0]=np.linspace(0,.1,301-PREFIX);eef[301:,0]=.1;c['exit_target']=eef[-1].tolist()
  if path:
   eef[110,1]=-.04; eef[150,1]=-.04
  if motion:
   eef[PREFIX:]=[0,0,1.05,1,0,0,0];c['exit_target']=eef[-1].tolist();c['motion_hold_segments']=[{'label':'after_transport','start_row':110,'end_row':145,'frames':35},{'label':'at_support','start_row':160,'end_row':200,'frames':40}]
  support=spec['f2']['support_identity_by_relation'][program_id];pairs=[{'body_a':'f2_redesign_can','body_b':support}];c['support_end_trace_row']=n-101;c['release_start_trace_row']=n-100
 else:
  def event(start,length,axis):
   end=start+length-1;v=np.interp(np.arange(length),[0,length//3,2*length//3,length-1],[0,-.047,.047,0]);dim=2 if axis=='V' else 0
   eef[start:end+1,dim]+=v;obj[start:end+1,dim]+=v;return end
  event(10,91,'V');c['prefix_event_evidence']={'start_row':10,'end_row':100,'verifier':{'pass':True}}
  suffix=list(program_id[1:]);c['expected_suffix_event_order']=suffix;c['event_segments']=[]
  for i,a in enumerate(suffix):
   start=180+i*(110 if motion else 90);end=event(start,101 if motion else 81,a);c['event_segments'].append({'event_index':i+1,'axis':a,'start_row':start,'end_row':end,'duration_rows':end-start+1,'hold_frames':[25,30,25] if motion else [20,20,20]})
  if path:eef[120,1]=-.03
  pairs=[{'body_a':'f3_redesign_bottle','body_b':'f3_redesign_support_pad'}]
 if path:
  c['variant_waypoints_actual']=[{'label':label,'target':eef[i].tolist(),'trace_row':i} for label,i in zip(['detour_start','detour_target_offset','target'],[120,150,160])]
 base['role_object_pose__'+main]=obj.copy();base['contact_pairs_json']=np.asarray([json.dumps(pairs) if f=='F2' or i>=n-100 else '[]' for i in range(n)])
 effective=np.zeros((n,26));effective[PREFIX:,0]=2 if path else 1;effective[PREFIX:,2]=np.arange(n-PREFIX)*.0001
 if motion:effective[PREFIX:]=1
 base['controller_effective_setpoint']=effective;base['requested_command']=effective.copy();base['component_masks']=np.ones((n,26),bool)
 for k in ['left_gripper_joint_drive_target','right_gripper_joint_drive_target','left_gripper_joint_drive_velocity_target','right_gripper_joint_drive_velocity_target']:base[k]=np.zeros((n,2))
 np.savez_compressed(output/'trace.npz',**base)
 current=output/'current';current.mkdir();images={name+'__rgb':np.full((240,320,3),7,np.uint8) for name in resolved['cameras']['required']};np.savez_compressed(current/'rgb.npz',**images)
 state={'joint_qpos':base['joint_qpos'][0].tolist(),'joint_qvel':base['joint_qvel'][0].tolist(),'joint_qf':base['joint_qf'][0].tolist(),'eef_pose':eef[0].tolist(),'gripper_command':grip[0].tolist(),'role_object_pose':roles,'role_object_linear_velocity':{r:[0.,0.,0.] for r in roles},'role_object_angular_velocity':{r:[0.,0.,0.] for r in roles},'left_gripper_drive_target':[0.,0.],'right_gripper_drive_target':[0.,0.],'left_gripper_drive_velocity_target':[0.,0.],'right_gripper_drive_velocity_target':[0.,0.]};state['state76_sha256']=hashlib.sha256(np.zeros(76,dtype=float).tobytes()).hexdigest();atomic_write_json(current/'state.json',state)
 anchor={'schema_version':'cmf_f2_f3_anchor_bundle_v2','state':state,'scene_spec':spec,'synthetic':True};atomic_write_json(current/'anchor.json',anchor)
 meta={'root_id':root_id,'cell_key':program_id+':'+realization_id,'required_camera_names':resolved['cameras']['required'],'camera_names':resolved['cameras']['required'],'camera_images':{k.removesuffix('__rgb'):{'dtype':'uint8','shape':list(v.shape),'sha256':hashlib.sha256(v.tobytes()).hexdigest()} for k,v in images.items()},'rgb_npz_sha256':sha256_file(current/'rgb.npz'),'state_json_sha256':sha256_file(current/'state.json'),'anchor_json_sha256':sha256_file(current/'anchor.json'),'state_sha256':state['state76_sha256'],'rest_target':c['rest_target'] if f=='F3' else None,'synthetic':True};meta['capture_metadata_sha256']=canonical_sha256(meta);atomic_write_json(current/'capture_metadata.json',meta)
 mapping={'effective_setpoint':'controller_effective_setpoint','requested_command':'requested_command','component_mask':'component_masks','left_gripper_joint_drive_target':'left_gripper_joint_drive_target','right_gripper_joint_drive_target':'right_gripper_joint_drive_target','left_gripper_joint_drive_velocity_target':'left_gripper_joint_drive_velocity_target','right_gripper_joint_drive_velocity_target':'right_gripper_joint_drive_velocity_target'}
 if artifact is None:
  artifact=output.parent/'prefix_artifact.npz';np.savez_compressed(artifact,**{k:base[v][:PREFIX] for k,v in mapping.items()})
 c['prefix_sha256']=_prefix_artifact_hash(artifact);c['trace']={'path':c['trace_path'],'sample_count':n};atomic_write_json(output/'cell_receipt.json',c);return c
