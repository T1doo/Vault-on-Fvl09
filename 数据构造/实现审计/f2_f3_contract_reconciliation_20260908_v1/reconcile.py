"""Read-only CPU reconciliation. Does not import a simulator or change old acceptance."""
import sys, json, hashlib, zipfile, itertools, time
from pathlib import Path
import numpy as np
W=Path('/nfs_share/lijunhui'); REPO=W/'Robotwin2/project/RoboTwin'; OUT=Path(__file__).parent
sys.path.insert(0,str(REPO))
from controlled_multi_future.signals import closed_loop_event_metrics
from controlled_multi_future.verifiers.f3 import verify_realized_motion_metrics
from controlled_multi_future.runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS as T
ROOTS={'F2-A':'stage_C_F2A_resume_pilot_1788855821','F2-B':'stage_C_F2B_pilot_1788856533','F3-A':'stage_C_F3A_pilot_1788852570','F3-B':'stage_C_F3B_resume_pilot_1788855368'}
BASE=W/'Robotwin2/datasets/f2_f3_redesign_v1'
MAP={'effective_setpoint':'controller_effective_setpoint','requested_command':'requested_command','component_mask':'component_masks',**{k:k for k in ['left_gripper_joint_drive_target','right_gripper_joint_drive_target','left_gripper_joint_drive_velocity_target','right_gripper_joint_drive_velocity_target']}}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def qdist(a,b):
 a=np.asarray(a);b=np.asarray(b);a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
 return float(2*np.arccos(np.clip(abs(np.dot(a,b)),-1,1)))
def tail_contacts(path,n=50):
 # Stream past large fixed-width unicode arrays; do not load multi-GB contacts into RAM.
 with zipfile.ZipFile(path) as z, z.open('contact_pairs_json.npy') as f:
  ver=np.lib.format.read_magic(f); shape,order,dtype=np.lib.format._read_array_header(f,ver)
  assert not order and len(shape)==1 and dtype.kind=='U'
  skip=max(0,shape[0]-n)*dtype.itemsize
  while skip:
   b=f.read(min(skip,1024*1024)); assert b; skip-=len(b)
  return [json.loads(str(x)) for x in np.frombuffer(f.read(),dtype=dtype)]
def pair(rows,main,other):
 return [any({p.get('body_a'),p.get('body_b')}=={main,other} for p in row) for row in rows]
def metrics(z,start,end,axis):
 e=z['eef_pose'][start:end+1,:3];o=z['object_pose'][start:end+1];c=z['selected_gripper_contact'][start:end+1];a=2 if axis=='V' else 0
 em=closed_loop_event_metrics(e,e[0],a);om=closed_loop_event_metrics(o[:,:3],o[0,:3],a)
 m={'axis':axis,'bottle_orientation_drift':max(qdist(o[0,3:],v[3:]) for v in o),'selected_gripper_contact_fraction':float(c.mean()),'contact_break_count':int(np.count_nonzero(c[:-1]&~c[1:]))}
 for prefix,vals in [('eef',em),('bottle',om)]:
  for k in ['positive_amplitude','negative_amplitude','max_off_axis','return_error']:m[prefix+'_'+k]=vals[k]
 return {'start_row':start,'end_row':end,'metrics':m,'verifier':verify_realized_motion_metrics({'measured':m},T)}
def rotation(q):
 w,x,y,z=np.asarray(q)/np.linalg.norm(q)
 return np.array([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],[2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],[2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])
meta=json.loads((REPO/'assets/objects/071_can/model_data0.json').read_text())
center=np.array(meta['center'])*meta['scale']; half=np.array(meta['extents'])*meta['scale']/2
corners=center+np.array(list(itertools.product([-1,1],repeat=3)))*half

def f2(z,contacts):
 poses=z['object_pose'][-50:]; verts=np.array([corners@rotation(p[3:]).T+p[:3] for p in poses]); low=verts.min(axis=1);high=verts.max(axis=1)
 support={s:float(np.mean(pair(contacts,'f2_redesign_can',s))) for s in ['f2_redesign_box_bottom','f2_redesign_scale','f2_redesign_stand','table']}
 interior_lo=np.array([-.29,-.29,.760]);interior_hi=np.array([-.07,-.07,.86])
 geom_center=(low+high)/2
 # Exact geometry and old support-height tolerance are reported separately, no new acceptance threshold.
 point_inside=np.all((geom_center>=interior_lo)&(geom_center<=interior_hi),axis=1)
 volume_inside=np.all((low>=interior_lo)&(high<=interior_hi),axis=1)
 xy_inside=np.all((low[:,:2]>=interior_lo[:2])&(high[:,:2]<=interior_hi[:2]),axis=1)
 scale_xy=np.all(np.abs(geom_center[:,:2]-[-.02,-.18])<=[.04,.06],axis=1)
 scale_height=np.abs(low[:,2]-.760)<=T['support_height_tolerance_m']
 stand_top=pair(contacts,'f2_redesign_can','f2_redesign_stand')
 old=[]
 for p in poses:
  a=bool(np.all(p[:2]>=[-.29,-.29]) and np.all(p[:2]<=[-.07,-.07]));b=bool(abs(p[0]+.02)<.08 and abs(p[1]+.18)<.08);c=bool(abs(p[0]-.08)<.08 and abs(p[1]+.18)<.08 and not a and not b);old.append([a,b,c])
 return {'world_geometry_source':'metadata bounding box rotated by measured quaternion; conservative box, not convex-mesh volume','final_actor_pose':poses[-1].tolist(),'final_world_aabb_lower':low[-1].tolist(),'final_world_aabb_upper':high[-1].tolist(),'support_contact_fractions':support,'point_inside_volume_fraction':float(point_inside.mean()),'full_conservative_volume_inside_fraction':float(volume_inside.mean()),'footprint_inside_fraction':float(xy_inside.mean()),'scale_region_and_bottom_height_fraction':float((scale_xy&scale_height).mean()),'stand_top_contact_fraction':float(np.mean(stand_top)),'beside_necessary_no_reference_top_contact':not any(stand_top),'beside_annulus_radius_contract':'MISSING_FOR_V3; no radius invented','legacy_predicates_final':old[-1],'legacy_exactly_one_final':sum(old[-1])==1,'stable_linear_speed_max':float(np.linalg.norm(z['object_linear_velocity'][-50:],axis=1).max()),'angular_speed_max':float(np.linalg.norm(z['object_angular_velocity'][-50:],axis=1).max()),'gripper_open_fraction':float((z['gripper_command'][-50:,0]>=.9).mean()),'gripper_contact_fraction':float(z['selected_gripper_contact'][-50:].mean()),'box_bottom_offset_range_m':[float((low[:,2]-.760).min()),float((low[:,2]-.760).max())]}

def main():
 start=time.time();result={'schema':'scientific_contract_raw_reconciliation_v1','baseline_commit':'1854cb2a164fe0a1f3b13cbfa033389aa5acd6d9','old_acceptance_changed':False,'new_accepted_total':None,'gpu_jobs':0,'physical_executions':0,'roots':{},'source_hashes':{}}
 protected=[];full={}; paths=[]
 for rid,folder in ROOTS.items():
  rp=BASE/folder/'root_receipt.json';r=json.loads(rp.read_text()); pp=rp.parent/'prefix_artifact.npz';protected.extend([rp,pp]);pfx=dict(np.load(pp,allow_pickle=False));p=len(pfx['effective_setpoint']); rows=[];full[rid]=[]
  # Locate original shared-V event indices in preserved lineage, linked by exact prefix bytes.
  shared=None;shared_source=None
  candidates=[rp]+[Path(c['trace_path']).parent/'cell_receipt.json' for c in r['cells']]
  for candidate in candidates:
   d=json.loads(candidate.read_text()); cs=d.get('cells',[d])
   for c in cs:
    if c.get('prefix_event_evidence') and c.get('prefix_end_trace_row')==p-1:shared=c['prefix_event_evidence'];shared_source=str(candidate);break
   if shared:break
  for c in r['cells']:
   path=Path(c['trace_path']);paths.append(path); before=sha(path)
   print('READ',rid,c['program_id'],c['realization_id'],flush=True)
   with np.load(path,allow_pickle=False) as data:
    keys=set(data.files); chosen=set(MAP.values())|{'timestamp','joint_qpos','joint_qvel','eef_pose','dual_eef_pose','object_pose','object_linear_velocity','object_angular_velocity','eef_linear_velocity','eef_angular_velocity','gripper_command','selected_gripper_contact','initial_state'}|{k for k in keys if k.startswith('role_object_pose__') or k.startswith('realized_') and ('qpos' in k or 'qvel' in k)}
    z={k:data[k] for k in chosen if k in keys}
   initial={k:v[0].tolist() for k,v in z.items() if k.startswith('role_object_pose__') or k in ['joint_qpos','joint_qvel','dual_eef_pose','gripper_command'] or k.startswith('realized_')}
   terminal={k:v[-1].tolist() for k,v in z.items() if k in initial}
   prefix={}
   for a,b in MAP.items():
    x=z[b][:p];y=pfx[a]; same=x.shape==y.shape and x.dtype==y.dtype and x.tobytes()==y.tobytes()
    prefix[a]={'exact_bytes_including_row0':same,'actual_rows_1_onward_equal':bool(np.array_equal(x[1:],y[1:])),'max_abs_difference':float(np.max(np.abs(x.astype(float)-y.astype(float)))),'different_rows':np.flatnonzero(np.any(x!=y,axis=1)).tolist()}
   inventory=[str(f) for f in path.parent.rglob('*') if f.is_file()]
   rgbkeys=[k for k in keys if any(s in k.lower() for s in ['rgb','image','camera'])]
   contacts=tail_contacts(path)
   row={'cell':rid+'/'+c['program_id']+'/'+c['realization_id'],'trace':str(path),'trace_sha256_before':before,'sample_count':len(z['timestamp']),'stored_row0_signature':digest(initial),'row0':initial,'terminal':terminal,'actual_prefix':prefix,'prefix_artifact':str(pp),'prefix_step_count_excluding_initial':p-1,'original_rgb_npz_keys':rgbkeys,'cell_files':inventory,'full_anchor_missing':['original current head/wrist RGB bundle','camera capture identity/hash','full native snapshot including sleep/contact/solver history','all unregistered scene objects'],'classification':{}}
   row['export_check']={'status':'PARTIAL_REAL_ARRAY_LINKAGE_ONLY','inputs_available':{'state_shape':list(np.r_[z['joint_qpos'][0],z['joint_qvel'][0]].shape),'state_sha256':hashlib.sha256(np.r_[z['joint_qpos'][0],z['joint_qvel'][0]].tobytes()).hexdigest(),'future_shape':list(z['controller_effective_setpoint'][1:].shape),'future_sha256':hashlib.sha256(z['controller_effective_setpoint'][1:].tobytes()).hexdigest(),'future_excludes_initial_row':True,'time_250hz':bool(np.allclose(np.diff(z['timestamp']),.004,rtol=0,atol=1e-9))},'rgb':'MISSING_ORIGINAL','candidate_set':'program names in receipt; no verified current-grounded referring-expression bundle','supervision':{'historical_program_label':c['program_id'],'model_input':False},'audit':{'source':str(path),'model_input':False},'full_model_payload_emitted':False,'H_view_exported':False,'training_run':False}
   row['classification']['current_anchor']='EVIDENCE_MISSING_PARTIAL_ROW0_MEASURED'
   row['classification']['prefix']='CPU_CONFIRMED' if all(v['exact_bytes_including_row0'] for v in prefix.values()) else 'ACTUAL_PREFIX_DIFFERENCE'
   if rid.startswith('F2'):
    row['f2']=f2(z,contacts)
    row['classification']['relation']='ACTUAL_NONCOMPLIANCE_REFERENCE_TOP' if c['program_id']=='beside' and not row['f2']['beside_necessary_no_reference_top_contact'] else 'CPU_GEOMETRY_SUPPORT_EVIDENCE_WITH_FROZEN_REGION_GAPS'
   else:
    ev=[]
    if shared:ev.append({'label':'shared_V','boundary_source':shared_source,**metrics(z,shared['start_row'],shared['end_row'],'V')})
    for e in c['event_segments']:ev.append({'label':e['axis'],**metrics(z,e['start_row'],e['end_row'],e['axis'])})
    row['f3_events']=ev;row['classification']['shared_V']='CPU_CONFIRMED' if shared and ev[0]['verifier']['pass'] else ('ACTUAL_EVENT_FAILURE' if shared else 'EVIDENCE_MISSING')
    row['f3_terminal']={'object_return_position_m':float(np.linalg.norm(z['object_pose'][-1,:3]-z['object_pose'][0,:3])),'object_return_orientation_rad':qdist(z['object_pose'][0,3:],z['object_pose'][-1,3:]),'eef_to_row0_position_m':float(np.linalg.norm(z['eef_pose'][-1,:3]-z['eef_pose'][0,:3])),'eef_to_row0_orientation_rad':qdist(z['eef_pose'][0,3:],z['eef_pose'][-1,3:]),'joint_qpos_to_row0_max_abs':float(np.abs(z['joint_qpos'][-1]-z['joint_qpos'][0]).max()),'joint_qvel_final_max_abs':float(np.abs(z['joint_qvel'][-1]).max()),'object_speed_window_max':float(np.linalg.norm(z['object_linear_velocity'][-50:],axis=1).max()),'eef_speed_window_max':float(np.linalg.norm(z['eef_linear_velocity'][-50:],axis=1).max()),'support_window_fraction':float(np.mean(pair(contacts,'f3_redesign_bottle','f3_redesign_support_pad'))),'gripper_open_fraction':float((z['gripper_command'][-50:,0]>=.9).mean()),'rest_binding':'MISSING_PREDECLARED_NUMERIC_REST; row0 is diagnostic reference, not newly defined rest'}
    row['classification']['rest']='EVIDENCE_MISSING_FIXED_REST_BINDING; MEASURED_TERMINAL_DIFFERS_FROM_ROW0'
   non={k:float(np.max(np.linalg.norm(v[:,:3]-v[0,:3],axis=1))) for k,v in z.items() if k.startswith('role_object_pose__') and k not in ['role_object_pose__bottle','role_object_pose__main_can']};row['saved_non_task_max_displacement_m']=non
   row['trace_sha256_after']=sha(path);assert before==row['trace_sha256_after']; rows.append(row);full[rid].append((initial,terminal));write(OUT/(rid+'_cells.json'),rows)
  comparisons={}
  for k in full[rid][0][0]:
   initial_arrays=[np.asarray(x[0][k]) for x in full[rid]]; terminal_arrays=[np.asarray(x[1][k]) for x in full[rid]]
   comparisons[k]={'row0_exact_all':all(np.array_equal(initial_arrays[0],x) for x in initial_arrays),'row0_max_abs_delta':max(float(np.max(abs(a-b))) for a,b in itertools.combinations(initial_arrays,2)),'terminal_max_abs_delta':max(float(np.max(abs(a-b))) for a,b in itertools.combinations(terminal_arrays,2))}
   if k=='dual_eef_pose':comparisons[k]['terminal_left_position_max_m']=max(float(np.linalg.norm(a[:3]-b[:3])) for a,b in itertools.combinations(terminal_arrays,2));comparisons[k]['terminal_left_orientation_max_rad']=max(qdist(a[3:7],b[3:7]) for a,b in itertools.combinations(terminal_arrays,2))
  result['roots'][rid]={'cells_file':rid+'_cells.json','stored_initial_signature_count':len({x['stored_row0_signature'] for x in rows}),'components':comparisons,'root_receipt_sha256':sha(rp),'prefix_artifact_sha256':sha(pp),'old_accepted':r['accepted'],'new_scientific_acceptance':'NOT_ASSIGNED'}
 result['AB_comparison']={}
 for fam in ['F2','F3']:
  a=full[fam+'-A'][0][0];b=full[fam+'-B'][0][0]
  result['AB_comparison'][fam]={'first_cell_stored_initial_exact':a==b,'per_component_max_abs':{k:float(np.max(np.abs(np.array(a[k])-np.array(b[k])))) for k in a},'layout':'same hardcoded layout per scene source','independent_current':'NOT_PROVEN; original RGB/full anchor missing','classification':'SAME_NOMINAL_SCENE_DIFFERENT_RUN_COHORTS; not proven independent roots'}
 result['source_hashes']={str(p):sha(p) for p in protected+[Path(__file__),REPO/'assets/objects/071_can/model_data0.json']}
 result['elapsed_cpu_wall_seconds']=time.time()-start
 write(OUT/'RECONCILIATION.json',result);print('DONE',flush=True)
if __name__=='__main__':main()
