"""F4 order, support and neutral checks recomputed from original native raw arrays."""
import json
from pathlib import Path
import numpy as np

def verify_f4_disk(*,raw_dir,spec,program):
 from controlled_multi_future.geometry import footprint_inside_local_region,quaternion_orientation_error
 from controlled_multi_future.runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS as T,TRAY_BASE0_SUPPORT_REGION as TRAY
 raw_dir=Path(raw_dir);checks={};completions={}
 try:
  root=raw_dir.parent.parent.parent;roles={r['role']:r for r in spec['roles']};order=list(program['program_id'][3:]);window=int(T['stable_window_frames'])
  prefix=json.loads((root/'canonical_prefix_artifact/canonical_prefix_artifact.json').read_text());end=int(prefix['prefix_step_count'])
  suffix=json.loads((root/'suffix_artifacts'/program['program_id']/'frozen_suffix_artifact.json').read_text());targets=suffix['execution_spec']['targets'];rest=np.asarray(targets[-1]['pose']);checks['frozen_neutral_target']=targets[-1]['segment_id'].endswith('_neutral')
  with np.load(raw_dir/'raw_streams.npz',allow_pickle=False) as z:
   contacts=[json.loads(str(row)) for row in z['audit__contact_pairs_json']];n=len(z['audit__role_object_pose__A']);checks['stable_window_present']=n>=end+window
   def pair_contact(row,a,b):return any({p['body_a'],p['body_b']}=={a,b} for p in row)
   for role in 'ABC':
    poses=z['audit__role_object_pose__'+role];slots=z['audit__role_object_pose__slot_'+role];half=np.asarray(roles[role]['size'])/2;sh=np.asarray(roles['slot_'+role]['size'])/2
    inside=lambda i:footprint_inside_local_region(poses[i],half,slots[i],[-sh[0],-sh[1],-.01],[sh[0],sh[1],.03],(0,1))['pass_support_footprint']
    linear=np.linalg.norm(z['audit__role_object_linear_velocity__'+role],axis=1);angular=np.linalg.norm(z['audit__role_object_angular_velocity__'+role],axis=1)
    checks[role+':final_slot_footprint']=bool(inside(-1));checks[role+':final_linear_stable']=np.max(linear[-window:])<=T['stable_linear_speed_mps'];checks[role+':final_angular_stable']=np.max(angular[-window:])<=T['eef_stationary_angular_speed_rps'];checks[role+':final_table_support']=all(pair_contact(c,'formal_f4_'+role,'table') for c in contacts[-window:])
    good=np.zeros(n,dtype=bool)
    candidates=np.flatnonzero((np.linalg.norm(poses[:,:2]-slots[:,:2],axis=1)<np.linalg.norm(sh[:2]))&(linear<=T['stable_linear_speed_mps'])&(angular<=T['eef_stationary_angular_speed_rps']))
    for i in candidates:
     if i>=end:good[i]=inside(i) and pair_contact(contacts[i],'formal_f4_'+role,'table')
    runs=np.convolve(good.astype(int),np.ones(window,dtype=int),'valid');reached=np.flatnonzero(runs==window)
    checks[role+':observed_completion']=bool(len(reached));completions[role]=int(reached[0]+window-1) if len(reached) else n+1
    if len(reached):checks[role+':completed_slot_preserved']=bool(np.all(good[completions[role]:]))
   checks['observed_order']=sorted('ABC',key=completions.get)==order and len(set(completions.values()))==3
   for index,role in enumerate(order):
    if index:
     stop=min(completions[order[index-1]],n-1);poses=z['audit__role_object_pose__'+role];checks[role+':untouched_until_previous_complete']=np.max(np.linalg.norm(poses[:stop+1,:3]-poses[0,:3],axis=1))<=T['non_target_displacement_m']
   common=z['audit__role_object_pose__common_x'];tray=z['audit__role_object_pose__common_tray'];checks['common_X_in_tray']=footprint_inside_local_region(common[-1],np.asarray(roles['common_x']['size'])/2,tray[-1],TRAY['lower_m'],TRAY['upper_m'],TRAY['horizontal_axes'])['pass_support_footprint'];checks['common_X_prefix_preserved']=np.max(np.linalg.norm(common[end:,:3]-common[end,:3],axis=1))<=T['non_target_displacement_m'];checks['common_X_tray_support']=all(pair_contact(c,'formal_f4_common_x','formal_f4_common_tray') for c in contacts[-window:])
   eef=z['stream__realized_eef'][-1][:7];checks['neutral_position']=np.linalg.norm(eef[:3]-rest[:3])<=T['neutral_position_error_m'];checks['neutral_orientation']=quaternion_orientation_error(eef[3:],rest[3:])<=T['orientation_error'];checks['left_gripper_open']=float(z['stream__gripper_command'][-1][0])>.8
   for r in roles:
    if r in ['A','B','C','common_x']:continue
    poses=z['audit__role_object_pose__'+r];checks['non_task:'+r]=np.max(np.linalg.norm(poses[:,:3]-poses[0,:3],axis=1))<=T['non_target_displacement_m']
 except (OSError,KeyError,ValueError,IndexError,TypeError) as exc:return {'pass':False,'checks':{k:bool(v) for k,v in checks.items()},'error':str(exc),'runner_pass_used':False}
 return {'pass':bool(checks) and all(checks.values()),'checks':{k:bool(v) for k,v in checks.items()},'observed_completion_rows':completions,'runner_pass_used':False,'threshold_source':'original runtime_v2 thresholds and actual frozen role dimensions'}
