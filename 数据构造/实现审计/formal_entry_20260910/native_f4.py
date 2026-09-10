"""Explicit-layout F4 bridge to qualified native planning/execution (lazy GPU boundary).

Qualification evidence is a mandatory input: no old source terminal, synthetic
stage-A terminal, or fixed default layout is silently selected by this bridge.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json,types
import numpy as np
from scene_plan import validate_resolved,hash_json,require

PROGRAMS=('F4-ABC','F4-ACB','F4-BAC')
REALIZATIONS=('r_pc','r_inv_path','r_inv_motion')

def qualification_request(spec):
 validate_resolved(spec);require(spec['family']=='F4','F4 family required')
 by={r['role']:r for r in spec['roles']}
 require({'A','B','C','common_x','common_tray','slot_A','slot_B','slot_C'}<=set(by),'F4 role map incomplete')
 return {'schema':'formal_f4_qualification_request_v1','root_id':spec['root_id'],'resolved_scene_spec_sha256':spec['spec_sha256'],
         'source_layout':{r:by[r]['pose'] for r in 'ABC'},'slot_poses':{r:by['slot_'+r]['pose'] for r in 'ABC'},
         'common_x_pose':by['common_x']['pose'],'common_tray_pose':by['common_tray']['pose'],
         'program_ids':list(PROGRAMS),'arm_schedule':{'prefix':'right','suffix':'left'},
         'required_evidence':['layout_bound_source_grasp','three_exact_planner_terminals','isolation_gate','full_program_specs'],
         'qualification_executed':False,'physical_execution_authorized':False}

def _sha_file(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_qualification(spec,authorization):
 request=qualification_request(spec);binding=authorization.get('f4_qualification')
 require(isinstance(binding,dict) and set(binding)=={'path','sha256'},'F4 new-layout qualification evidence required')
 from portable_v2 import origin
 path=origin(binding['path'])
 require(_sha_file(path)==binding['sha256'],'qualification file hash mismatch')
 q=json.loads(path.read_text());require(q.get('schema')=='formal_f4_qualification_v1' and q.get('pass') is True,'qualification not passed')
 require(q.get('resolved_scene_spec_sha256')==spec['spec_sha256'] and q.get('root_id')==spec['root_id'],'qualification scene/root mismatch')
 require(q.get('request_sha256')==hash_json(request),'qualification request mismatch')
 require(q.get('source_layout')==request['source_layout'] and q.get('slot_poses')==request['slot_poses'],'qualification physical layout mismatch')
 gate=q['isolation_gate'];require([s.get('stage') for s in gate.get('stages',[])]==['A_ONLY','B_ONLY','C_ONLY','AB_NONINTERFERENCE','AC_NONINTERFERENCE'] and all(s.get('stage_physically_qualified')is True and s.get('resolved_scene_spec_sha256')==spec['spec_sha256'] and s.get('receipt_sha256')==hash_json({k:v for k,v in s.items() if k!='receipt_sha256'}) for s in gate['stages']),'five real isolation stages required');require(gate.get('pass') is True and gate.get('resolved_scene_spec_sha256')==spec['spec_sha256'],'isolation gate missing or unrelated')
 require(gate.get('receipt_sha256')==hash_json({k:v for k,v in gate.items() if k!='receipt_sha256'}),'isolation gate hash')
 require(set(q['full_program_specs'])==set(PROGRAMS) and set(q['planner_terminals'])==set(PROGRAMS),'three programs qualification required')
 for program in PROGRAMS:
  full=q['full_program_specs'][program];terminal=q['planner_terminals'][program]
  require(full.get('spec_sha256')==hash_json({k:v for k,v in full.items() if k!='spec_sha256'}),'full program hash')
  require(terminal.get('receipt_sha256')==hash_json({k:v for k,v in terminal.items() if k!='receipt_sha256'}),'planner terminal hash')
  require(terminal.get('program_id')==program and terminal.get('robot_kinematic_table_world_planner_pass') is True and terminal.get('physical_execution_count')==0,'passing real planner terminal required')
  require(terminal.get('resolved_scene_spec_sha256')==spec['spec_sha256'],'planner terminal wrong new scene')
  planner=full['source_planner_spec'];require(planner.get('spec_sha256')==hash_json({k:v for k,v in planner.items() if k!='spec_sha256'}),'source planner spec hash')
  require(planner['f4_source_grasp_candidate_v1']==full['f4_source_grasp_candidate_v1'] and planner['f4_stage_b_candidate_v1']==full['f4_stage_b_candidate_v1'],'nested planner candidate binding')
  require(planner['program_id']==program and planner['program_order']==list(program[3:]),'nested planner program binding')
  require(full.get('source_planner_terminal_receipt_sha256')==terminal['receipt_sha256'] and full.get('source_planner_spec_sha256')==terminal['spec_sha256'],'terminal/full spec chain')
  require(full.get('isolation_gate_receipt_sha256')==gate['receipt_sha256'],'full spec isolation gate binding')
  require(full['f4_source_grasp_candidate_v1']['source_layout']==request['source_layout'] and full['f4_source_grasp_candidate_v1']['arm']=='left','source layout/arm mismatch')
  require(full['f4_stage_b_candidate_v1']['slot_poses']==request['slot_poses'],'target slots mismatch')
  require(full['program_id']==program and full['role_sequence']==list(program[3:]),'full ordered program mismatch')
 return q

def path_targets(targets,offset):
 require(np.isfinite(offset) and 0<abs(offset)<=.05,'bounded path offset')
 result=deepcopy(targets);changed=[]
 for target in result:
  if target['segment_id'] in {r+'_carry_mid' for r in 'ABC'}:
   pose=np.array(target['pose'],dtype=float);pose[1]+=offset;target['pose']=pose.tolist();changed.append(target['segment_id'])
 require(set(changed)=={r+'_carry_mid' for r in 'ABC'} and len(changed)==3,'exactly three transport waypoints required')
 return result

def create_roles(scene,spec,*,box,visual_box,asset,pose):
 result={}
 for r in spec['roles']:
  name=r['role'];require(name not in result,'duplicate role');p=pose(r['pose'][:3],r['pose'][3:]);half=np.array(r['size'])/2
  if r['asset']=='primitive_box':actor=box(scene,p,half,color=r['color'],is_static=not r['dynamic'],name='formal_f4_'+name)
  elif r['asset']=='visual_box':actor=visual_box(scene,p,half,color=r['color'],name='formal_f4_'+name)
  elif r['asset']=='008_tray:model0' and name=='common_tray':actor=asset(scene,p,'008_tray',convex=True,is_static=True,model_id=0)
  else:raise ValueError('unsupported F4 asset '+r['asset'])
  actor.set_name('formal_f4_'+name);actor._cmf_half_extents=half;actor._cmf_geometry_source='frozen_formal_role_size';result[name]=actor
  setattr(scene,'tray' if name=='common_tray' else name.lower(),actor)
 scene.role_actors=result;return result

def context_class(base):
 class Context(base):
  def __enter__(self):
   from controlled_multi_future.probes.action_feasibility_v2 import _scene_resources
   from controlled_multi_future.real_sapien_adapter_v1_2 import CANONICAL_SETTLE_STEPS
   from envs.utils import create_box,create_visual_box,create_actor
   from native_f1_factory import bind_cameras
   import sapien
   require(not self._a0_phase,'formal F4 not diagnostic A0');scenes,args_factory=_scene_resources();spec=self.planned_spec
   class Scene(scenes['F4']):
    def initialize_trace(self,*args,**kwargs):
     self._formal_completed_trace_queries=getattr(self,'_formal_completed_trace_queries',0)+int(getattr(self,'planner_query_count',0))
     archive=getattr(self,'_formal_trace_epoch_dir',None)
     if archive is not None and hasattr(self,'trace') and len(self.trace):
      archive=Path(archive);archive.mkdir(parents=True,exist_ok=True);epoch=int(getattr(self,'_formal_trace_epoch',0));self.save_trace(archive/('epoch_'+str(epoch)+'.npz'));self._formal_trace_epoch=epoch+1
     return super().initialize_trace(*args,**kwargs)
    def load_actors(self):create_roles(self,spec,box=create_box,visual_box=create_visual_box,asset=create_actor,pose=sapien.Pose)
   try:
    scene=Scene();self._scene=scene;args=args_factory('F4',self.output_root/self.scene_instance_id);args['seed']=spec['seed'];scene._cmf_planned_root_slot_spec=deepcopy(spec);scene.setup_demo(**args);bind_cameras(scene,spec)
    for _ in range(CANONICAL_SETTLE_STEPS):scene.scene.step()
    scene._cmf_setup_kwargs=args;scene._cmf_canonical_settle_steps=CANONICAL_SETTLE_STEPS;scene._cmf_scene_instance_id=self.scene_instance_id;scene._cmf_adapter_version='formal_f4_native_20260910';scene._cmf_sealed_implementation_source_sha256=self.sealed_implementation_source_sha256;scene._cmf_sealed_source_binding=self.sealed_source_binding;scene._cmf_scene_context_v1_2=self;self.handle.scene=scene
    return self.handle
   except BaseException as exc:self.__exit__(type(exc),exc,exc.__traceback__);raise
 return Context

def native_adapter(spec,realization,output,source_sha,qualification):
 # All simulator-native imports occur after root authorization and evidence checks.
 from controlled_multi_future.real_sapien_adapter_f4_qualified_root_v1 import RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter as Qualified
 from controlled_multi_future.real_sapien_adapter_f4_selected_layout_v2 import RoboTwinRealSapienF4SelectedLayoutV2Adapter as Selected
 from controlled_multi_future import real_sapien_adapter_v1_2 as base
 from controlled_multi_future.real_sapien_adapter_v1_1 import _dual_entity_values
 from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
 from controlled_multi_future import f4_full_program_physical_v1 as full
 from controlled_multi_future.family_runners_v3_1 import _wait_and_record
 Context=context_class(base.RoboTwinSceneContextV1_2)
 class Adapter(Qualified):
  def __init__(self):
   Selected.__init__(self,family='F4',output_root=Path(output),expected_implementation_source_sha256=source_sha)
   self.planned_spec=deepcopy(spec);self.f4_candidate=qualification['source_candidate'] if qualification.get('qualification_building') else qualification['full_program_specs']['F4-ABC']['f4_source_grasp_candidate_v1'];self.full_program_specs={k:full.validate_f4_full_program_physical_spec_v1(v) for k,v in qualification['full_program_specs'].items()}
  def scene(self,planned_root_slot_spec,*,phase,program=None):
   require(planned_root_slot_spec['spec_sha256']==spec['spec_sha256'],'native scene spec mismatch')
   return _PinnedSapienRenderDeviceContextV1(Context(family='F4',planned_spec=planned_root_slot_spec,phase=phase,program=program,output_root=self.output_root,sealed_implementation_source_sha256=self._sealed_implementation_source_sha256,sealed_source_binding=self._sealed_source_binding))
  def build_programs(self,scene):return deepcopy(spec['programs'])
  def _entity_payloads(self,scene):
   registry={};existing=base.ROLE_ASSETS_V1_2['F4']
   for r in spec['roles']:
    if r['asset']=='008_tray:model0':registry[r['role']]=deepcopy(existing['common_tray']);continue
    visual=r['asset']=='visual_box';registry[r['role']]={'modelname':'procedural_box','model_id':None,'static_or_dynamic':'dynamic' if r['dynamic'] else 'static','collision_mode':'visual_only' if visual else 'box','procedural_creation':base._procedural(creation_api='create_visual_box' if visual else 'create_box',half_size=(np.array(r['size'])/2).tolist(),color=r['color'],collision_enabled=not visual,visual_only=visual,is_static=not r['dynamic'])}
   env=dict(base.RoboTwinRealSapienPilotRootAdapterV1_2._entity_payloads.__globals__);env['ROLE_ASSETS_V1_2']={**base.ROLE_ASSETS_V1_2,'F4':registry}
   return types.FunctionType(base.RoboTwinRealSapienPilotRootAdapterV1_2._entity_payloads.__code__,env)(self,scene)
  def capture_current(self,scene):
   before=int(getattr(scene,'step_lim',0));current=super().capture_current(scene);rgb=scene.cameras.get_rgb();arrays={k:np.asarray(rgb[k]['rgb']).copy() for k in spec['cameras']['required']};arrays.update(robot_qpos=_dual_entity_values(scene.robot,'get_qpos'),robot_qvel=_dual_entity_values(scene.robot,'get_qvel'));anchor=self.capture_anchor(scene)
   require(int(getattr(scene,'step_lim',0))==before,'capture stepped physics')
   require(all(arrays[k].dtype==np.uint8 and arrays[k].shape==(spec['cameras']['height'],spec['cameras']['width'],3) for k in spec['cameras']['required']),'capture camera shape')
   dest=Path(self.output_root)/'observations'/scene._cmf_scene_instance_id;dest.mkdir(parents=True,exist_ok=True);path=dest/'current.npz'
   if not path.exists():
    np.savez_compressed(path,**arrays);(dest/'anchor.json').write_text(json.dumps(anchor,sort_keys=True));(dest/'capture.json').write_text(json.dumps({'current_hashes':current,'spec_sha256':spec['spec_sha256'],'camera_config':self._camera_configuration(scene,rgb),'scene_instance_id':scene._cmf_scene_instance_id,'capture_source':'native_original_t0','npz_sha256':_sha_file(path)},sort_keys=True))
   scene._formal_current_capture_path=dest/'capture.json'
   with np.load(path,allow_pickle=False) as saved:require(set(saved.files)==set(arrays) and all(np.array_equal(saved[k],v) for k,v in arrays.items()),'capture write/readback mismatch')
   return current
  def plan_suffix_from_actual_prefix_end_state(self,scene,program,replay):
   planner=full.plan_f4_full_program_suffix_from_replayed_prefix_v1
   if realization=='r_inv_path':
    original=planner.__globals__['build_f4_stage_b_targets_v1']
    def targets(s,p):
     ts,audit=original(s,p);ts=path_targets(ts,spec['variant_rules']['r_inv_path']['safe_horizontal_y_offset_m']);return ts,{**audit,'native_f4_path_offset_y_m':spec['variant_rules']['r_inv_path']['safe_horizontal_y_offset_m']}
    env={**planner.__globals__,'build_f4_stage_b_targets_v1':targets};planner=types.FunctionType(planner.__code__,env)
   return planner(scene,program,replay,self.full_program_specs[program['program_id']])
  def execute_frozen_suffix_spec(self,scene,program,execution_spec,replay,realization_spec):
   if realization=='r_inv_motion':
    frames=spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames'];require(type(frames)is int and 0<frames<=250,'bounded motion hold');_wait_and_record(scene,frames)
   result=full.execute_f4_frozen_full_program_suffix_v1(scene,program,execution_spec,replay,realization_spec)
   result.setdefault('provenance',{}).update(formal_current_capture_path=str(scene._formal_current_capture_path),formal_root_id=spec['root_id'],formal_spec_sha256=spec['spec_sha256'])
   return result
 return Adapter()

def call_budget():
 return {'family':'F4','cohorts':3,'collection_cells':9,'strict_prefix_cohort':'r_pc_only',
  'per_cohort_calls':{'pristine_scene':1,'candidate_feasibility_scenes':3,'canonical_prefix_action_scene':1,'suffix_preflight_action_scenes':3,'branch_collection_action_scenes':3},
  'base_without_qualification_or_recovery':{'fresh_scenes':33,'action_scenes':21,'collection_attempts':9,'solver_query_ceiling':450},
  'qualification_additional':{'fresh_scenes':8,'action_scenes':5,'collection_attempts':0,'planner_terminals':3,'physical_isolation_stages':5,'solver_query_ceiling':376,'native_call':'native_f4_qualification.run_native_qualification'},
  'qualification_cost_source':'must bind actual authorized qualification job manifests; not silently included in nine cells',
  'native_calls':['Context -> F4Scene.setup_demo -> explicit create_roles','FormalF1RecoverableOrchestrator.run_nonformal_root','plan_f4_full_program_suffix_from_replayed_prefix_v1','execute_f4_frozen_full_program_suffix_v1'],
  'gpu_authorized':False}

def run_native_root(spec,output,authorization):
 validate_resolved(spec);require(spec['family']=='F4','F4 family');require(authorization.get('gpu_execution_authorized')is True,'GPU is not authorized in CPU implementation Goal');require(authorization.get('spec_sha256')==spec['spec_sha256'],'authorization scene mismatch')
 source_files=authorization.get('source_files',{});require(all(source_files.get(str(Path(__file__).with_name(name).resolve()))==_sha_file(Path(__file__).with_name(name)) for name in ['native_f4.py','native_f1_factory.py','native_f1_orchestrator.py','family_entry.py','native_raw_contract.py','native_f4_disk_verifier.py','portable_v2.py','scene_plan.py']),'native F4 source not frozen')
 qualification=load_qualification(spec,authorization);source_sha=authorization['implementation_source_sha256'];output=Path(output)
 from native_f1_orchestrator import FormalF1RecoverableOrchestrator
 from family_entry import write,finalize_structure,cohort_root
 state_file=output/'f4_state.json';state=json.loads(state_file.read_text()) if state_file.exists() else {'spec_sha256':spec['spec_sha256'],'source_files':source_files,'completed':{},'status':'READY'}
 require(state['spec_sha256']==spec['spec_sha256'] and state['source_files']==source_files,'resume spec/source mismatch');require(state['status']!='RUNNING' or authorization.get('owned_cleanup_reconciled')is True,'interrupted F4 cohort requires owned cleanup reconciliation')
 for realization in REALIZATIONS:
  receipt=cohort_root(output,realization)/'root_receipt.json'
  if realization in state['completed']:
   require(_sha_file(receipt)==state['completed'][realization],'completed receipt changed');continue
  require(state['status'] not in ['FAILED','RUNNING'] or authorization.get('recovery_authorized')is True,'failed F4 cohort requires separately budgeted recovery')
  state.update(status='RUNNING',active=realization);write(state_file,state)
  try:
   run_native_cohort(spec,realization,output/realization,source_sha,qualification);receipt=cohort_root(output,realization)/'root_receipt.json'
   require(json.loads(receipt.read_text()).get('status')=='accepted','F4 cohort failed');state['completed'][realization]=_sha_file(receipt);state.update(status='READY',active=None);write(state_file,state)
  except BaseException as exc:state.update(status='FAILED',error_type=type(exc).__name__,error=str(exc));write(state_file,state);raise
 result=finalize_structure(spec=spec,output=output);result['qualification_sha256']=authorization['f4_qualification']['sha256'];result['full_terminal_equivalence']=audit_terminals(spec,output);result['pass']=result['pass'] and result['full_terminal_equivalence']['pass'];result['research_eligible']=bool(result['pass'] and result.get('native_physical_evidence')is True and result.get('independent_semantic_recomputed')is True);state['status']='STRUCTURE_READY' if result['pass'] else 'INCOMPLETE';write(output/'f4_native_result.json',result);write(state_file,state);return result

def run_native_cohort(spec,realization,output,source_sha,qualification):
 from native_f1_orchestrator import FormalF1RecoverableOrchestrator
 from family_entry import write
 output=Path(output);pointer=output/'cohort_pointer.json';previous=json.loads(pointer.read_text()) if pointer.exists() else None;attempt=previous['attempt']+1 if previous else 1
 require(attempt<=2,'F4 finite recovery cap exhausted')
 if previous:require(previous['spec_sha256']==spec['spec_sha256'] and previous['source_sha256']==source_sha,'F4 recovery source/spec mismatch')
 attempt_output=output if attempt==1 else output/('recovery_'+str(attempt));root=attempt_output/'root';reuse={}
 if previous:
  relative=Path(previous['root_relative']);require(not relative.is_absolute() and '..' not in relative.parts,'recovery path');old=output/relative
  for program in PROGRAMS:
   branch=old/'branches'/program
   if (branch/'receipt.json').exists() and json.loads((branch/'receipt.json').read_text()).get('status')=='accepted':reuse[program]=branch
 adapter=native_adapter(spec,realization,attempt_output/'scene_instances',source_sha,qualification);planned=deepcopy(spec);planned['slot_id']=spec['root_id'];planned['candidate_display_order']=list(PROGRAMS)
 orchestrator=FormalF1RecoverableOrchestrator(adapter,implementation_version='formal_f4_native_20260910');orchestrator.reuse_cells=reuse
 if previous and (old/'canonical_prefix_artifact').exists():orchestrator.reuse_prefix_dir=old/'canonical_prefix_artifact'
 payload={'root_relative':str(root.relative_to(output)),'attempt':attempt,'spec_sha256':spec['spec_sha256'],'source_sha256':source_sha,'reused_programs':sorted(reuse),'status':'STARTED'};write(pointer,payload)
 try:
  result=orchestrator.run_nonformal_root(output_dir=root,planned_root_slot_spec=planned,realization_spec_by_program={p:{'realization':realization,'variant_rules':spec['variant_rules'],'formal_data':False,'entry_spec_sha256':spec['spec_sha256']} for p in PROGRAMS},stage0_data=False,stage0_authorized=False,development_video_required=False);payload['status']=result['status'];return result
 finally:
  if payload['status']=='STARTED':payload['status']='EXCEPTION'
  write(pointer,payload)

def audit_terminals(spec,output):
 """Source-bound raw terminal world/arm audit across all nine real trajectories."""
 from family_entry import cohort_root
 tol=spec['terminal_tolerances'];terminals=[];checks={};roles={r['role']:r for r in spec['roles']}
 def angle(a,b):
  a=np.asarray(a);b=np.asarray(b);return float(2*np.arccos(np.clip(abs(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))),0,1)))
 def pose_equal(a,b,position,orientation):return np.linalg.norm(a[:3]-b[:3])<=position and angle(a[3:],b[3:])<=orientation
 for realization in REALIZATIONS:
  root=cohort_root(output,realization)
  for program in PROGRAMS:
   key=program+':'+realization;branch=root/'branches'/program
   try:
    receipt=json.loads((branch/'receipt.json').read_text());trace=branch/'trace_source.npz';require(_sha_file(trace)==receipt['trace_source']['sha256'],'trace binding');terminal={}
    with np.load(trace,allow_pickle=False) as z:
     for field in ['joint_qpos','joint_qvel','dual_eef_pose','gripper_command']:
      terminal[field]=z[field][-1].copy();require(np.isfinite(z[field]).all(),'finite trace required')
     for role,r in roles.items():
      poses=z['role_object_pose__'+role];terminal[role]=poses[-1].copy()
      if role not in ['A','B','C','common_x']:
       require(np.max(np.linalg.norm(poses[:,:3]-poses[0,:3],axis=1))<=tol['non_task_position_m'],'non-task translation');require(all(angle(p[3:],poses[0,3:])<=tol['non_task_orientation_rad'] for p in poses),'non-task orientation')
      if r['dynamic']:
       require(np.linalg.norm(z['role_object_linear_velocity__'+role][-1])<=tol['non_task_linear_speed_m_s'],'terminal role speed');require(np.linalg.norm(z['role_object_angular_velocity__'+role][-1])<=tol['non_task_angular_speed_rad_s'],'terminal role angular speed')
    require(np.max(np.abs(terminal['joint_qvel']))<=tol['joint_speed_rad_s'],'robot terminal speed');terminals.append(terminal);checks[key]=True
   except (KeyError,ValueError,OSError) as exc:checks[key]=False;checks[key+':error']=str(exc)
 if len(terminals)==9:
  ref=terminals[0];eq=[]
  for t in terminals:
   eq.append(np.max(np.abs(t['joint_qpos']-ref['joint_qpos']))<=tol['joint_position_rad'] and np.max(np.abs(t['gripper_command']-ref['gripper_command']))<=tol['gripper_fraction'] and all(pose_equal(t['dual_eef_pose'][a:a+7],ref['dual_eef_pose'][a:a+7],tol['eef_position_m'],tol['eef_orientation_rad']) for a in [0,7]) and all(pose_equal(t[r],ref[r],tol['object_position_m'],tol['object_orientation_rad']) for r in roles))
  checks['all_nine_full_terminal_equivalent']=all(eq)
 else:checks['all_nine_full_terminal_equivalent']=False
 return {'pass':len(terminals)==9 and all(v is True for k,v in checks.items() if not k.endswith(':error')),'checks':checks,'tolerances':tol,'source':'actual trace arrays; no runner pass used'}
