"""Explicit-spec F2/F3 native orchestration; CPU imports do not load SAPIEN.

Uses preserved cell primitives with new scene subclasses, not the pilot root runner.
"""
import copy,json,os,time
from pathlib import Path
import numpy as np
from scene_plan import hash_json,require,validate_resolved
LIVE=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin')

def compatible_spec(resolved):
 validate_resolved(resolved)
 from controlled_multi_future.redesign_f2_f3_v2.factory import load_model_spec
 from controlled_multi_future.redesign_f2_f3_v2.scene_spec import _BASE_F2,_BASE_F3
 require(resolved['variant_rules']['r_inv_path']['postprefix_detour_m']==(.04 if resolved['family']=='F2' else .03),'native detour binding')
 require(resolved['variant_rules']['r_inv_motion']['time_scale']==(1.0 if resolved['family']=='F2' else 1.5),'native timing profile binding')
 f=resolved['family'];require(f in ['F2','F3'],'F2/F3 only');by={r['role']:r for r in resolved['roles']}
 # Reference asset geometry is loaded from its own immutable model files, not root A/B.
 family=copy.deepcopy(_BASE_F2 if f=='F2' else _BASE_F3)
 if f=='F2':
  for name,size,z in [('box',[.24,.24,.10],.805),('scale',[.08,.12,.01],.755),('stand',[.10,.10,.07],.790)]:
   require(by[name]['size']==size and by[name]['pose'][2]==z and by[name]['pose'][3:]==[1,0,0,0],'unsupported F2 geometry: '+name)
  x,y=by['box']['pose'][:2];inside=resolved['targets']['inside'];require(np.allclose(inside['lower'],[x-.11,y-.11,.760],rtol=0,atol=1e-10) and np.allclose(inside['upper'],[x+.11,y+.11,.855],rtol=0,atol=1e-10),'box target geometry mismatch')
  require(resolved['targets']['on']['half_xy']==[.04,.06] and resolved['targets']['on']['center']==by['scale']['pose'][:2]+[.760],'scale target mismatch')
  beside=resolved['targets']['beside'];require(beside['support']=='table' and beside['reference']=='stand' and beside['forbid_reference_top'] is True and beside['annulus']==[.105,.205] and beside['target'][2]==.740,'beside contract mismatch')
 else:
  require(by['original_pad']['size']==[.15,.15,.01] and by['original_pad']['pose'][2]==.745,'unsupported pad geometry')
  require(resolved['targets']['central']['amplitude_m']==.047 and resolved['targets']['central']['V']==[0,0,1] and resolved['targets']['central']['H']==[1,0,0],'F3 axis/profile changed')
 asset=load_model_spec(LIVE/'assets','071_can' if f=='F2' else '114_bottle',model_id=0 if f=='F2' else 1,asset_id='formal_'+f).to_receipt();family['asset_binding']=asset
 if f=='F2':
  x,y=by['box']['pose'][:2];family.update(layout_id='formal_explicit_geometry',box_center_xyz=[x,y,.755],box_inner_lower_xyz=[x-.11,y-.11,.760],box_inner_upper_xyz=[x+.11,y+.11,.855],scale_center_xyz=by['scale']['pose'][:3],stand_center_xyz=by['stand']['pose'][:3],box_support_z=.760,beside_target_xy=resolved['targets']['beside']['target'][:2],support_point_local_xyz=asset['collision_support_point_local'],collision_bounds_local_xyz=asset['collision_bounds_local'],support_point_source='asset collision bounds source hashes',support_identity_by_relation={'inside':'f2_redesign_box_bottom','on':'f2_redesign_scale','beside':'table'})
 else:family.update(pad_center_xyz=by['original_pad']['pose'][:3],central_marker_xyz=resolved['targets']['central']['position_m'],time_scale=resolved['variant_rules']['r_pc']['time_scale'])
 requirements={'r_pc':{'kind':'baseline','variant_name':'direct_frozen_control'},'r_inv_path':{'kind':'path','variant_name':'post_prefix_lateral_detour','waypoint_count':3,'detour_axis':'y','detour_offset_m':-.04 if f=='F2' else -.03,'required_waypoint_labels':['detour_start','detour_target_offset','target']},'r_inv_motion':{'kind':'motion','variant_name':'extended_event_holds','baseline_hold_frames':[20,20,20],'alternative_hold_frames':[25,30,25],'required_hold_delta_frames':[5,10,5]}}
 value={'root_id':resolved['root_id'],'family':f,'scene_seed':resolved['seed'],'layout_variant':'FORMAL_EXPLICIT','resolved_scene_spec':copy.deepcopy(resolved),'spec_sha256':resolved['spec_sha256'],f.lower():family,'realization_requirements':requirements,'candidate_set_schema':{'relations' if f=='F2' else 'programs':[p['program_id'] for p in resolved['programs']]}}
 value['planner_query_limit_per_scene']=40 if f=='F2' else 60
 value['native_binding_sha256']=hash_json(value)
 return value

def f2_motion_check(baseline,alternative):
 require(baseline['program_id']==alternative['program_id'],'motion changed program')
 segments=alternative.get('motion_hold_segments',[])
 checks=[]
 with np.load(alternative['trace_path'],allow_pickle=False) as a, np.load(baseline['trace_path'],allow_pickle=False) as b:
  for seg,(label,frames) in zip(segments,[('after_transport',35),('at_support',40)]):
   start,end=seg['start_row'],seg['end_row']
   ok=type(start) is int and type(end) is int and 0<=start<end<len(a['eef_pose']) and end-start==frames and seg['frames']==frames and seg['label']==label
   if ok:
    commanded=a['controller_effective_setpoint'][start+1:end+1];eef=a['eef_pose'][start:end+1,:3]
    ok=np.all(commanded==commanded[0]) and np.max(np.linalg.norm(eef-eef[0],axis=1))<=.010
   checks.append(bool(ok))
  changed=not np.array_equal(a['controller_effective_setpoint'][alternative['prefix_end_trace_row']+1:],b['controller_effective_setpoint'][baseline['prefix_end_trace_row']+1:])
 return {'pass':len(segments)==2 and len(checks)==2 and all(checks) and changed,'hold_checks':checks,'suffix_changed':changed,'prefix_cohort':'trajectory_invariance'}

def root_finalize(output,spec,cells):
 from controlled_multi_future.redesign_f2_f3_v2 import finalizer as verifier
 expected={(p['program_id'],r) for p in spec['resolved_scene_spec']['programs'] for r in ['r_pc','r_inv_path','r_inv_motion']}
 found={(c['program_id'],c['realization_id']) for c in cells};checks={'matrix':len(cells)==9 and found==expected,'identities':all(c['root_id']==spec['root_id'] and c['scene_spec_sha256']==spec['spec_sha256'] for c in cells)}
 details=[];bundles=[]
 for c in cells:
  cell_dir=Path(c['trace_path']).parent
  artifact=output/'prefix_artifact.npz' if c['realization_id']=='r_pc' else Path(c['prefix_artifact_path'])
  result=verifier.finalize_cell(cell_dir=cell_dir,spec=spec,expected_relation=c['program_id'] if spec['family']=='F2' else None,artifact_path=artifact);details.append(result)
  meta=json.loads((cell_dir/'current/capture_metadata.json').read_text());bundles.append((meta['state_sha256'],hash_json(meta['camera_images']),verifier._anchor_signature(cell_dir/'current')))
 checks['cells']=len(details)==9 and all(d['pass'] for d in details);checks['same_current_anchor']=len(set(bundles))==1
 variants=[]
 for program,_ in sorted(expected):
  if any(x['program_id']==program for x in variants):continue
  baseline=next((c for c in cells if c['program_id']==program and c['realization_id']=='r_pc'),None)
  for realization in ['r_inv_path','r_inv_motion']:
   alt=next((c for c in cells if c['program_id']==program and c['realization_id']==realization),None)
   if baseline is None or alt is None:variants.append({'program_id':program,'realization':realization,'pass':False});continue
   # Use the original independent stage comparison with formal requirements injected
   # into an isolated function globals copy, never mutate old module globals.
   import types
   env=dict(verifier._variant_check.__globals__);env['frozen_realization_requirements']=lambda root_id,r:copy.deepcopy(spec['realization_requirements'][r])
   if spec['family']=='F2' and realization=='r_inv_motion':
    variants.append({'program_id':program,'realization':realization,**f2_motion_check(baseline,alt)});continue
   check=types.FunctionType(verifier._variant_check.__code__,env)(baseline,alt)
   check['legacy_all_prefix_gate_diagnostic']=check.pop('pass');check['prefix_cohort']='trajectory_invariance';check['pass']=bool(check['variant_contract_pass'] and check['variant_effect_observed'])
   variants.append({'program_id':program,'realization':realization,**check})
 checks['variants']=len(variants)==6 and all(v['pass'] for v in variants)
 # Non-task state remains source-equivalent and cross-branch terminal state is checked for F3.
 terminal=[];drifts=[];tol=spec['resolved_scene_spec']['terminal_tolerances']
 expected_roles={r['role'] for r in spec['resolved_scene_spec']['roles'] if r['role'] not in ('main_can','bottle','box')}
 expected_roles.update(['table','wall'])
 if spec['family']=='F2':expected_roles.update(['box_bottom','box_left','box_right','box_front','box_back'])
 def angle(a,b):
  return 2*np.arccos(np.clip(np.abs(np.dot(a/np.linalg.norm(a),b/np.linalg.norm(b))),0,1))
 for c in cells:
  with np.load(c['trace_path'],allow_pickle=False) as z:
   fixed=['role_object_pose__'+r for r in expected_roles]
   require(all(k in z.files for k in fixed),'missing expected non-task role')
   drifts.append(all(np.max(np.linalg.norm(z[k][:,:3]-z[k][0,:3],axis=1))<=tol['non_task_position_m'] and angle(z[k][-1,3:],z[k][0,3:])<=tol['non_task_orientation_rad'] for k in fixed))
   if spec['family']=='F3':
    require(all('role_object_linear_velocity__'+r in z.files and 'role_object_angular_velocity__'+r in z.files for r in expected_roles),'missing terminal role velocities')
    drifts.append(all(np.linalg.norm(z['role_object_linear_velocity__'+r][-1])<=tol['non_task_linear_speed_m_s'] and np.linalg.norm(z['role_object_angular_velocity__'+r][-1])<=tol['non_task_angular_speed_rad_s'] for r in expected_roles))
    terminal.append({'q':z['joint_qpos'][-1].copy(),'v':z['joint_qvel'][-1].copy(),'object':z['object_pose'][-1].copy(),'eef':z['eef_pose'][-1].copy(),'gripper':z['gripper_command'][-1].copy()})
 checks['non_task_drift']=bool(drifts) and all(drifts)
 def equivalent(a,b):
  return all([np.max(np.abs(a['q']-b['q']))<=tol['joint_position_rad'],np.max(np.abs(a['v']))<=tol['joint_speed_rad_s'],np.linalg.norm(a['object'][:3]-b['object'][:3])<=tol['object_position_m'],angle(a['object'][3:],b['object'][3:])<=tol['object_orientation_rad'],np.linalg.norm(a['eef'][:3]-b['eef'][:3])<=tol['eef_position_m'],angle(a['eef'][3:],b['eef'][3:])<=tol['eef_orientation_rad'],np.max(np.abs(a['gripper']-b['gripper']))<=tol['gripper_fraction']])
 checks['terminal_equivalence']=True if spec['family']=='F2' else bool(terminal) and all(equivalent(t,terminal[0]) for t in terminal)
 return {'schema':'formal_f2f3_root_finalizer_v1','root_id':spec['root_id'],'scene_spec_sha256':spec['spec_sha256'],'strict_prefix_cohort':'r_pc_only','checks':checks,'cell_finalizers':details,'variant_checks':variants,'pass':all(checks.values()),'synthetic':spec['resolved_scene_spec'].get('synthetic',False),'physics_verified':all(checks.values()) and not spec['resolved_scene_spec'].get('synthetic',False)}

def _run_native_root(resolved,output,authorization):
 validate_resolved(resolved)
 require(authorization.get('gpu_execution_authorized') is True,'GPU is not authorized in CPU implementation Goal')
 require(authorization.get('spec_sha256')==resolved['spec_sha256'],'authorization spec binding')
 require(authorization.get('copy_destination') is not None,'copy destination required before native action')
 import hashlib
 required_source=[p for p in Path(__file__).parent.glob('*.py') if not p.name.startswith('test_')]
 required_source.extend((LIVE/'controlled_multi_future').rglob('*.py'))
 required_source.extend((LIVE/'envs').rglob('*.py'))
 frozen=authorization.get('source_files',{})
 require(all(frozen.get(str(p.resolve()))==hashlib.sha256(p.read_bytes()).hexdigest() for p in required_source),'native source not frozen')
 qualification=authorization.get('qualification')
 require(type(qualification) is dict and Path(qualification['path']).is_file(),'missing three-program qualification')
 require(hashlib.sha256(Path(qualification['path']).read_bytes()).hexdigest()==qualification['sha256'],'qualification file changed')
 q=json.loads(Path(qualification['path']).read_text())
 require(q.get('spec_sha256')==resolved['spec_sha256'] and q.get('pass') is True and q.get('programs')==[p['program_id'] for p in resolved['programs']],'qualification identity')
 require(q.get('source_files')==frozen and len(q.get('evidence',[]))==6 and all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'] for x in q['evidence']),'qualification source changed')
 import native_cells as cells
 from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json
 from controlled_multi_future.redesign_f2_f3_v2 import finalizer
 output=Path(output);output.mkdir(parents=True,exist_ok=True);spec=compatible_spec(resolved)
 state_path=output/'formal_state.json';state=json.loads(state_path.read_text()) if state_path.exists() else {'spec_sha256':resolved['spec_sha256'],'source_files':frozen,'cells':[],'attempts':[]}
 require(state['spec_sha256']==resolved['spec_sha256'] and state.get('source_files')==frozen,'resume changed spec/source')
 if any(a['status']=='STARTED' for a in state['attempts']):require(authorization.get('prior_attempt_reconciled') is True,'interrupted attempt requires source/resource reconciliation')
 artifact=output/'prefix_artifact.npz';meta=output/'prefix_evidence.json'
 # Verify every reused cell from disk, not runner status.
 for c in state['cells']:
  disk=json.loads((Path(c['trace_path']).parent/'cell_receipt.json').read_text())
  require(c['root_id']==resolved['root_id'] and c['scene_spec_sha256']==resolved['spec_sha256'] and c['program_id'] in [p['program_id'] for p in resolved['programs']] and c['realization_id'] in resolved['realizations'],'resume identity')
  require(all(disk.get(k)==c.get(k) for k in ['root_id','program_id','realization_id','scene_spec_sha256','trace_path']),'checkpoint vs disk identity')
  require(c.get('frozen_trace_sha256')==hashlib.sha256(Path(c['trace_path']).read_bytes()).hexdigest(),'resume trace hash')
  result=finalizer.finalize_cell(cell_dir=Path(c['trace_path']).parent,spec=spec,expected_relation=c['program_id'] if spec['family']=='F2' else None,artifact_path=artifact if c['realization_id']=='r_pc' else Path(c['prefix_artifact_path']))
  require(result['pass'],'resume source failed independent verifier')
 programs=[p['program_id'] for p in resolved['programs']]
 for realization in ['r_pc','r_inv_path','r_inv_motion']:
  for program in programs:
   if any(c['program_id']==program and c['realization_id']==realization for c in state['cells']):continue
   key=program+'__'+realization;attempt=1+sum(x['cell']==key for x in state['attempts']);require(attempt<=2,'finite cell retry exhausted')
   directory=output/(key+f'__attempt{attempt}');started=time.monotonic();state['attempts'].append({'cell':key,'attempt':attempt,'status':'STARTED','started_wall':time.time()});atomic_write_json(state_path,state)
   kwargs={'spec':spec,'output':directory,'root_id':resolved['root_id'],'program_id':program,'realization_id':realization,'artifact':artifact if artifact.exists() else None,'collection':True}
   try:
    c=cells._f2_cell(**kwargs,f2_route_mode='side_then_geometry_target',f2_lift_clearance_m=resolved['control_profile']['lift_clearance_m']) if spec['family']=='F2' else cells._f3_cell(**kwargs,prefix_meta=meta if meta.exists() else None)
    # Persist execution end before verification or any usage parsing.
    atomic_write_json(directory/'end_evidence.json',{'ended_wall':time.time(),'elapsed_seconds':time.monotonic()-started,'status':c['status']})
    require(c['status']=='cell_pass','cell failed; no later dispatch')
    if not artifact.exists():cells._save_prefix(output,c)
    result=finalizer.finalize_cell(cell_dir=directory,spec=spec,expected_relation=program if spec['family']=='F2' else None,artifact_path=artifact);require(result['pass'],'independent cell failed')
    c['prefix_artifact_path']=str(artifact);c['frozen_trace_sha256']=hashlib.sha256(Path(c['trace_path']).read_bytes()).hexdigest();c['cell_local_verified']=True;c['independent_cell_finalizer_path']=str(directory/'independent_finalizer_v2.json');state['cells'].append(c);state['attempts'][-1]['status']='VERIFIED';atomic_write_json(state_path,state)
   except BaseException:
    state['attempts'][-1]['status']='FAILED';atomic_write_json(state_path,state);raise
 result=root_finalize(output,spec,state['cells']);atomic_write_json(output/'formal_root_finalizer.json',result)
 if result['pass']:
  from formal_export import seal_modern_source,copy_sealed_root
  index=output/'source_seal/source_index.json'
  if not index.exists():index=seal_modern_source(output,resolved,state['cells'],result)
  require(authorization.get('copy_destination') is not None,'complete root requires copy destination')
  result['copy']=copy_sealed_root(index,authorization['copy_destination'])
 return result

def qualify_native_root(resolved,output,authorization):
 """Three explicit disposable full-program qualifications, never collection slots."""
 import hashlib
 validate_resolved(resolved)
 require(authorization.get('gpu_execution_authorized') is True and authorization.get('phase')=='qualification' and authorization.get('spec_sha256')==resolved['spec_sha256'],'qualification authorization')
 required=[*[p for p in Path(__file__).parent.glob('*.py') if not p.name.startswith('test_')],*(LIVE/'controlled_multi_future').rglob('*.py'),*(LIVE/'envs').rglob('*.py')]
 require(all(authorization.get('source_files',{}).get(str(p.resolve()))==hashlib.sha256(p.read_bytes()).hexdigest() for p in required),'qualification source not frozen')
 import native_cells as cells
 from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json
 from controlled_multi_future.redesign_f2_f3_v2.finalizer import finalize_cell
 output=Path(output);output.mkdir(parents=True,exist_ok=False);spec=compatible_spec(resolved);evidence=[];passed=[]
 for program in [p['program_id'] for p in resolved['programs']]:
  directory=output/program;start=time.monotonic()
  kwargs={'spec':spec,'output':directory,'root_id':resolved['root_id'],'program_id':program,'realization_id':'r_pc','artifact':None,'collection':False}
  c=cells._f2_cell(**kwargs,f2_route_mode='side_then_geometry_target',f2_lift_clearance_m=resolved['control_profile']['lift_clearance_m']) if spec['family']=='F2' else cells._f3_cell(**kwargs,prefix_meta=None)
  atomic_write_json(directory/'qualification_end.json',{'elapsed_seconds':time.monotonic()-start,'end_wall':time.time(),'runner_status':c['status']})
  if c['status']!='cell_pass':break
  artifact_dir=directory/'qualification_prefix';artifact_dir.mkdir();artifact=cells._save_prefix(artifact_dir,c)
  v=finalize_cell(cell_dir=directory,spec=spec,expected_relation=program if spec['family']=='F2' else None,artifact_path=artifact)
  for p in [directory/'independent_finalizer_v2.json',Path(c['trace_path'])]:evidence.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'program':program})
  if not v['pass']:break
  passed.append(program)
 result={'schema':'formal_three_program_qualification_v1','spec_sha256':resolved['spec_sha256'],'programs':passed,'pass':len(passed)==3,'evidence':evidence,'source_files':authorization['source_files'],'production_collection_count':0}
 atomic_write_json(output/'qualification.json',result);return result


def run_native_root(resolved,output,authorization):
 import fcntl
 validate_resolved(resolved)
 require(authorization.get('gpu_execution_authorized') is True,'native GPU execution not authorized')
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 with output.with_suffix('.root.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  try:return _run_native_root(resolved,output,authorization)
  finally:fcntl.flock(lock,fcntl.LOCK_UN)


def call_budget(family):
 require(family in ('F2','F3'),'family')
 per_scene=40 if family=='F2' else 60
 return {'qualification':{'fresh_scenes':3,'action_scenes':3,'collection_attempts':0,'solver_query_ceiling':3*per_scene},'collection':{'fresh_scenes':9,'action_scenes':9,'collection_attempts':9,'solver_query_ceiling':9*per_scene},'prefix_generation':'included in first collection cell; separate qualification prefixes are not collection data','recovery_max':{'fresh_scenes':9,'action_scenes':9,'collection_attempts':9,'solver_query_ceiling':9*per_scene},'per_cell_attempt_cap':2,'cleanup_in_job_lease':True}
