"""Fresh-layout native F4 qualification producer; no simulator import at module load.

Uses the successful source grasp policy as a profile, recomputes layout geometry,
executes three independent real planner scenes and five physical isolation scenes.
This callable is unexecuted in the CPU preparation Goal.
"""
import ast,inspect,json,types,time,sys
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from scene_plan import hash_json,require,validate_resolved
from native_f4 import qualification_request,_sha_file
STAGES=('A_ONLY','B_ONLY','C_ONLY','AB_NONINTERFERENCE','AC_NONINTERFERENCE')
STAGE_PROGRAM={'A_ONLY':'F4-ABC','B_ONLY':'F4-BAC','C_ONLY':'F4-ACB','AB_NONINTERFERENCE':'F4-ABC','AC_NONINTERFERENCE':'F4-ACB'}

def seal(value,key):
 value=deepcopy(value);value.pop(key,None);value[key]=hash_json(value);return value

def bind_builder_to_scene(builder,explicit_scene):
 """Replace only the old fixed-layout factory expression; old source is untouched.

 The replaced expression includes its synthetic-stage-A argument, so that helper
 is never called. Real new-layout terminals still traverse original validation.
 """
 tree=ast.parse(inspect.getsource(builder));replacements=[]
 class Replace(ast.NodeTransformer):
  def visit_Call(self,node):
   if isinstance(node.func,ast.Name) and node.func.id=='build_f4_runtime_spec_v1':
    replacements.append(node);return ast.copy_location(ast.Name(id='_new_explicit_scene',ctx=ast.Load()),node)
   return self.generic_visit(node)
 tree=Replace().visit(tree);require(len(replacements)==1,'exact one legacy scene factory replacement required');ast.fix_missing_locations(tree);env={**builder.__globals__,'_new_explicit_scene':deepcopy(explicit_scene)};exec(compile(tree,inspect.getsourcefile(builder) or '<f4-builder>','exec'),env);return env[builder.__name__]

def prepare_candidates(spec,profile):
 validate_resolved(spec);request=qualification_request(spec)
 from controlled_multi_future.f4_stage_b_geometry_contract_v2 import audit_f4_stage_b_candidate_geometry_v2
 source=deepcopy(profile['f4_source_grasp_candidate_v1']);slot=deepcopy(profile['f4_stage_b_candidate_v1'])
 require(source['arm']=='left' and source['block_half_extents_m']==[.022,.022,.022],'preserved source arm/size profile')
 source.update(candidate_id=spec['root_id']+'-source',source_layout=request['source_layout'],source_layout_sha256=hash_json(request['source_layout']),source_profile_sha256=profile['f4_source_grasp_candidate_v1']['candidate_sha256'])
 source['f1_15_of_15_execution_claim_applies_to_candidate']=False;source['common_x_tray_changed']=True;source['new_layout_qualification_pending']=True
 source['A_pregrasp_xyz_m']=(np.asarray(request['source_layout']['A'][:3])+np.asarray(source['grasp_policy']['pregrasp_offset_world_m'])).tolist()
 source['minimum_pairwise_block_surface_clearance_m']=min(np.max(np.abs(np.asarray(request['source_layout'][a][:3])-np.asarray(request['source_layout'][b][:3])))-.044 for a,b in [('A','B'),('A','C'),('B','C')]);source=seal(source,'candidate_sha256')
 geometry=audit_f4_stage_b_candidate_geometry_v2(source_layout=source['source_layout'],slot_poses=request['slot_poses'],corridor_policy=slot['corridor_policy'],arm=source['arm'])
 require(geometry['construction_valid'] is True,'new F4 layout fails native geometry qualification')
 slot.update(candidate_id=spec['root_id']+'-slots',source_grasp_candidate_sha256=source['candidate_sha256'],slot_poses=request['slot_poses'],slot_layout_sha256=hash_json(request['slot_poses']),slot_poses_sha256=hash_json(request['slot_poses']),source_grasp_candidate_id=source['candidate_id'],program_state_transition_audit_sha256=geometry['geometry_contract_sha256'],program_state_transition_audit=geometry,minimum_terminal_clearance_m=geometry['minimum_terminal_clearance_m'],minimum_swept_clearance_m=geometry['minimum_swept_clearance_m'],construction_valid=True,construction_failure_codes=[],online_fallback=False,source_profile_sha256=profile['f4_stage_b_candidate_v1']['candidate_sha256']);slot=seal(slot,'candidate_sha256')
 return source,slot

@contextmanager
def preserve_trace(scene,folder):
 try:yield
 finally:
  if hasattr(scene,'trace') and len(scene.trace):scene.save_trace(Path(folder)/'trace.npz')

def run_native_qualification(spec,output,authorization):
 validate_resolved(spec);require(authorization.get('gpu_execution_authorized')is True and authorization.get('qualification_execution_authorized')is True,'separate native qualification authorization required');require(authorization.get('spec_sha256')==spec['spec_sha256'],'qualification authorization scene mismatch')
 frozen=authorization.get('source_files',{})
 for name in ['native_f4.py','native_f4_qualification.py','native_f1_factory.py']:
  path=Path(__file__).with_name(name).resolve();require(frozen.get(str(path))==_sha_file(path),'qualification source not frozen')
 from portable_v2 import origin
 binding=authorization['f4_source_profile'];path=origin(binding['path']);require(_sha_file(path)==binding['sha256'],'source profile identity')
 payload=json.loads(path.read_text());profile=payload.get('planned_root_slot_spec',payload);source,slot=prepare_candidates(spec,profile)
 from native_f4 import native_adapter,PROGRAMS
 from controlled_multi_future.f4_program_planner_integration_v2 import build_f4_program_planner_spec_v2,run_f4_program_planner_v2
 from controlled_multi_future import f4_bounded_physical_micro_v1 as micro
 from controlled_multi_future import f4_full_program_physical_v1 as full
 from family_entry import write
 output=Path(output);require(not output.exists() or not any(output.iterdir()),'qualification requires independent new output');output.mkdir(parents=True,exist_ok=True)
 request=qualification_request(spec);write(output/'request.json',request);planned=deepcopy(spec);planned['slot_id']=spec['root_id'];planned['planned_scope_spec_sha256']=spec['spec_sha256'];terminals={};planner_specs={};cleanup=[];queries=0
 qualification_building={'qualification_building':True,'source_candidate':source,'full_program_specs':{}}
 for index,program in enumerate(PROGRAMS):
  nonce=int(spec['seed'])+index;planner=build_f4_program_planner_spec_v2(source,slot,program_id=program,slot_id=spec['root_id']+'-'+program+'-planner-source',planner_reset_nonce=nonce);planner_specs[program]=planner;folder=output/'planner'/program
  adapter=native_adapter(spec,'r_pc',folder/'scene_instances',authorization['implementation_source_sha256'],qualification_building);context=adapter.scene(planned,phase='F4_PROGRAM_PLANNER',program={'program_id':program})
  terminal=None;scene=None;started_wall=time.time();execution_started=False
  try:
   with context as handle:
    scene=handle.scene;scene._formal_trace_epoch_dir=folder/'trace_epochs';scene._cmf_scene_lifecycle='fresh';adapter.capture_current(scene);require(adapter.audit_current_rendered_visibility(scene,phase='F4_QUALIFICATION')['pass']is True,'actual current role visibility failed');scene.initialize_trace(scene.a,'left',role_actors=scene.role_actors);scene.planner_query_limit=planner['planner_query_limit'];execution_started=True
    with preserve_trace(scene,folder):terminal=run_f4_program_planner_v2(scene,planner)
    terminal['resolved_scene_spec_sha256']=spec['spec_sha256'];terminal=seal(terminal,'receipt_sha256')
  finally:
   ended_wall=time.time();actual_queries=(int(getattr(scene,'planner_query_count',0))+int(getattr(scene,'_formal_completed_trace_queries',0))) if scene is not None else 0;queries+=actual_queries
   write(folder/'result.json',{'spec':planner,'terminal':terminal,'cleanup':context.cleanup_receipt,'started_wall':started_wall,'ended_wall':ended_wall,'solver_query_count':actual_queries,'scene_created':scene is not None,'planner_started':execution_started,'physical_execution_started':False,'exception_type':sys.exc_info()[0].__name__ if sys.exc_info()[0] else None})
  require(context.cleanup_receipt and context.cleanup_receipt.get('cleanup_safety_pass')is True,'planner own cleanup incomplete');cleanup.append(context.cleanup_receipt);require(terminal and terminal['robot_kinematic_table_world_planner_pass']is True,'new layout program planner failed');terminals[program]=terminal
 builder=bind_builder_to_scene(micro.build_f4_bounded_physical_micro_spec_v1,planned);stage_terminals=[]
 for stage in STAGES:
  program=STAGE_PROGRAM[stage];p=planner_specs[program];job=builder(source,slot,terminals[program],stage=stage,slot_id=spec['root_id']+'-'+program,planner_reset_nonce=p['planner_reset_nonce']);folder=output/'isolation'/stage;adapter=native_adapter(spec,'r_pc',folder/'scene_instances',authorization['implementation_source_sha256'],qualification_building);context=adapter.scene(planned,phase='F4_BOUNDED_PHYSICAL_MICRO',program={'program_id':program});terminal=None;scene=None;started_wall=time.time();execution_started=False
  try:
   with context as handle:
    scene=handle.scene;scene._formal_trace_epoch_dir=folder/'trace_epochs';adapter.capture_current(scene);require(adapter.audit_current_rendered_visibility(scene,phase='F4_QUALIFICATION')['pass']is True,'actual current role visibility failed');scene.initialize_trace(scene.common_x,'left',role_actors=scene.role_actors);scene.planner_query_limit=job['planner_query_limit']+24;execution_started=True
    with preserve_trace(scene,folder):terminal=micro.run_f4_bounded_physical_micro_v1(scene,job,capture_anchor_callback=adapter.capture_anchor)
    terminal.update(resolved_scene_spec_sha256=spec['spec_sha256'],trace_sha256=_sha_file(folder/'trace.npz'));terminal=seal(terminal,'receipt_sha256')
  finally:
   ended_wall=time.time();actual_queries=(int(getattr(scene,'planner_query_count',0))+int(getattr(scene,'_formal_completed_trace_queries',0))) if scene is not None else 0;queries+=actual_queries
   write(folder/'result.json',{'spec':job,'terminal':terminal,'cleanup':context.cleanup_receipt,'started_wall':started_wall,'ended_wall':ended_wall,'solver_query_count':actual_queries,'scene_created':scene is not None,'physical_execution_started':execution_started,'exception_type':sys.exc_info()[0].__name__ if sys.exc_info()[0] else None})
  require(context.cleanup_receipt and context.cleanup_receipt.get('cleanup_safety_pass')is True,'isolation own cleanup incomplete');cleanup.append(context.cleanup_receipt);require(terminal and terminal['stage_physically_qualified']is True,'new layout isolation failed');stage_terminals.append(terminal)
 gate=seal({'resolved_scene_spec_sha256':spec['spec_sha256'],'pass':len(stage_terminals)==5,'stages':stage_terminals,'owned_cleanup':cleanup},'receipt_sha256');full_builder=bind_builder_to_scene(full.build_f4_full_program_physical_spec_v1,planned)
 full_specs={p:full_builder(source,slot,terminals[p],program_id=p,slot_id=planner_specs[p]['slot_id'],planner_reset_nonce=planner_specs[p]['planner_reset_nonce'],isolation_gate_receipt_sha256=gate['receipt_sha256']) for p in PROGRAMS}
 result={'schema':'formal_f4_qualification_v1','root_id':spec['root_id'],'resolved_scene_spec_sha256':spec['spec_sha256'],'request_sha256':hash_json(request),'source_layout':request['source_layout'],'slot_poses':request['slot_poses'],'planner_terminals':terminals,'isolation_gate':gate,'full_program_specs':full_specs,'source_profile_file_sha256':binding['sha256'],'pass':True,'actual_usage':{'fresh_scenes':8,'action_scenes':5,'collection_attempts':0,'solver_queries':queries}}
 write(output/'qualification.json',result);return result
