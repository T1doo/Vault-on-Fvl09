"""Explicit synthetic simulator boundary for the F4 native orchestration tests.

No native simulator/planner is imported or executed; numeric rows below are a
fixture, including deliberately idealized state changes. Never production data.
"""
from pathlib import Path
from copy import deepcopy
import hashlib,json,types
import numpy as np
from fixture_f1_backend import make_backend as make_capture_backend
from scene_plan import hash_json


def make_backend(spec,realization,output,source_sha,qualification,*,events=None,fail_program=None):
 base=make_capture_backend(spec=spec,realization=realization,output_root=output,source_sha=source_sha)
 from controlled_multi_future.geometry import transform_local_point
 events=[] if events is None else events
 class Backend(type(base)):
  def canonical_prefix_contract(self,programs):
   return {'prefix_id':'synthetic_f4_common_X','arm':'right','ops':['common_X_to_tray'],'synthetic':True}
  def plan_suffix_from_actual_prefix_end_state(self,scene,program,replay):
   result=super().plan_suffix_from_actual_prefix_end_state(scene,program,replay)
   name=program['program_id'][-1]+'_neutral';result['execution_spec']['targets'][0]['segment_id']=name;result['execution_spec']['segment_receipts'][0]['segment_id']=name
   return result
  def execute_frozen_suffix_spec(self,scene,program,execution_spec,replay,realization_spec):
   events.append((realization,program['program_id']))
   if fail_program==program['program_id']:raise RuntimeError('explicit synthetic branch interruption')
   result=self.raw.rollout(None,program,realization_spec);streams=result['streams'];audit=result['audit_streams'];n=260+(spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames'] if realization=='r_inv_motion' else 0)
   for group in [streams,audit]:
    for key,value in list(group.items()):
     if key=='field_metadata':continue
     value=np.asarray(value);group[key]=np.repeat(value[:1],n if len(value)==4 else n+1,axis=0)
   streams['controller_effective_setpoint'][:2]=self.arrays['effective_setpoint_actions'];streams['controller_effective_setpoint'][3,0]={'F4-ABC':1,'F4-ACB':2,'F4-BAC':3}[program['program_id']]
   if realization=='r_inv_path':streams['controller_effective_setpoint'][20,1]=.02
   streams['requested_command']=streams['controller_effective_setpoint'].copy();streams['action_interval_start_timestamps']=np.arange(n)/250;streams['action_interval_end_timestamps']=np.arange(1,n+1)/250;streams['state_timestamps']=np.arange(n+1)/250;streams['realized_qpos']=np.zeros((n+1,38));streams['realized_qvel']=np.zeros((n+1,38));streams['realized_eef']=np.tile([0,0,.9,1,0,0,0]*2,(n+1,1))
   if realization=='r_inv_path':streams['realized_eef'][10:30,1]=.02
   rolemap={r['role']:r for r in spec['roles']};order=list(program['program_id'][3:]);placement={role:20+70*order.index(role) for role in order}
   for r in spec['roles']:
    role=r['role'];poses=np.tile(np.asarray(r['pose'],float),(n+1,1))
    if role in order:
     final=np.asarray(rolemap['slot_'+role]['pose'],float).copy();final[2]+=.022;at=placement[role];poses[at-10:at,2]+=.05;poses[at:]=final
    elif role=='common_x':
     final=poses[-1].copy();final[:3]=transform_local_point(rolemap['common_tray']['pose'],[-.0745,.030,0]);poses[2:]=final
    audit['role_object_pose__'+role]=poses
    for stem in ['linear_velocity','angular_velocity','component_linear_velocity','component_angular_velocity']:
     audit['role_object_'+stem+'__'+role]=np.zeros((n+1,3));audit['role_object_'+stem+'_measured__'+role]=np.zeros(n+1,dtype=bool)
    audit['role_object_component_velocity_provenance_json__'+role]=np.array(['{"source":"synthetic"}']*(n+1))
   audit['object_pose']=audit['role_object_pose__'+order[-1]].copy();audit['eef_linear_velocity']=np.zeros((n+1,3));audit['eef_angular_velocity']=np.zeros((n+1,3))
   contacts=[]
   for i in range(n+1):
    row=[{'body_a':'formal_f4_'+r,'body_b':'table'} for r in order if i>=placement[r]]
    if i>=2:row.append({'body_a':'formal_f4_common_x','body_b':'formal_f4_common_tray'})
    contacts.append(json.dumps(row))
   audit['contact_pairs_json']=np.array(contacts)
   for name in ['left','right']:
    for kind in ['target','velocity_target']:audit[name+'_gripper_joint_drive_'+kind]=np.zeros((n+1,1))
   for key in audit:
    if key!='field_metadata' and key not in audit['field_metadata']:audit['field_metadata'][key]={'status':'derived','source':'explicit synthetic F4 fixture; not measured physics'}
   result['provenance'].update(synthetic=True,formal_current_capture_path=str(scene.fixture_capture),formal_root_id=spec['root_id'],formal_spec_sha256=spec['spec_sha256'],realization_spec=realization_spec)
   result['semantic_verifier']={'pass':True,'synthetic':True};result['final_state_equivalence_payload']={**{r+'_pose':audit['role_object_pose__'+r][-1].tolist() for r in ['A','B','C','common_x']},'executing_eef_pose':streams['realized_eef'][-1,:7].tolist(),'executing_gripper_open':True,'execution_arm':'left'};scene.trace.append({'effective_setpoint':streams['controller_effective_setpoint'][3].copy()})
   # Real disk terminal audit sees the fixture state arrays via the same trace path.
   trace={'joint_qpos':streams['realized_qpos'],'joint_qvel':streams['realized_qvel'],'dual_eef_pose':streams['realized_eef'],'gripper_command':np.ones((n+1,2)),'controller_effective_setpoint':np.vstack([np.zeros((1,26)),streams['controller_effective_setpoint']])}
   trace.update({k:v for k,v in audit.items() if k!='field_metadata'})
   def save_trace(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,**trace);return {'path':str(path),'sample_count':n+1,'synthetic':True}
   scene.save_trace=save_trace
   return result
 return Backend()


def fixture_qualification(spec):
 """Explicitly synthetic evidence exercising the real qualification reader only."""
 from native_f4 import qualification_request,PROGRAMS
 from native_f4_qualification import seal
 request=qualification_request(spec);source={'source_layout':request['source_layout'],'arm':'left'};slot={'slot_poses':request['slot_poses']};terminals={};full={}
 stages=[seal({'stage':stage,'stage_physically_qualified':True,'resolved_scene_spec_sha256':spec['spec_sha256'],'synthetic':True},'receipt_sha256') for stage in ['A_ONLY','B_ONLY','C_ONLY','AB_NONINTERFERENCE','AC_NONINTERFERENCE']]
 gate=seal({'pass':True,'resolved_scene_spec_sha256':spec['spec_sha256'],'stages':stages,'synthetic':True},'receipt_sha256')
 for program in PROGRAMS:
  planner=seal({'program_id':program,'program_order':list(program[3:]),'f4_source_grasp_candidate_v1':source,'f4_stage_b_candidate_v1':slot,'synthetic':True},'spec_sha256')
  terminal=seal({'program_id':program,'robot_kinematic_table_world_planner_pass':True,'physical_execution_count':0,'resolved_scene_spec_sha256':spec['spec_sha256'],'spec_sha256':planner['spec_sha256'],'synthetic':True},'receipt_sha256');terminals[program]=terminal
  full[program]=seal({'program_id':program,'role_sequence':list(program[3:]),'source_planner_spec':planner,'source_planner_spec_sha256':planner['spec_sha256'],'source_planner_terminal_receipt_sha256':terminal['receipt_sha256'],'isolation_gate_receipt_sha256':gate['receipt_sha256'],'f4_source_grasp_candidate_v1':source,'f4_stage_b_candidate_v1':slot,'synthetic':True},'spec_sha256')
 return {'schema':'formal_f4_qualification_v1','pass':True,'synthetic':True,'root_id':spec['root_id'],'resolved_scene_spec_sha256':spec['spec_sha256'],'request_sha256':hash_json(request),'source_layout':request['source_layout'],'slot_poses':request['slot_poses'],'isolation_gate':gate,'planner_terminals':terminals,'full_program_specs':full}
