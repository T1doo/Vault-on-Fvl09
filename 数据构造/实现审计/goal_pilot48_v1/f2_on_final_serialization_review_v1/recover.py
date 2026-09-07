"""Recompute original final predicates from immutable measured trace only."""
import json,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from goal_pilot48_v1.f2_on_beside_runtime_v1 import gates
from goal_pilot48_v1.f2_on_beside_runtime_v1.spec import W,A,load,sha,digest
from goal_pilot48_v1.f2_on_beside_runtime_v2.runtime import json_values
D=W/'Robotwin2/datasets/p48_f2_on_release_revision1_001';OUT=Path(__file__).parent;P=W/'Robotwin2/project/RoboTwin'

def tail_field(path,name,n):
    # contact Unicode matrices are large; stream just the final original rows.
    with zipfile.ZipFile(path) as archive,archive.open(name+'.npy') as stream:
        version=np.lib.format.read_magic(stream)
        shape,fortran,dtype=np.lib.format._read_array_header(stream,version)
        if fortran or dtype.hasobject or len(shape)!=1:raise ValueError('unexpected saved contact array layout')
        count=min(n,shape[0]);stream.seek((shape[0]-count)*dtype.itemsize,1)
        data=stream.read(count*dtype.itemsize)
        if len(data)!=count*dtype.itemsize:raise ValueError('truncated trace field')
        return np.frombuffer(data,dtype=dtype)

def non_json_scalars(v,path='$'):
    if isinstance(v,np.generic):return [{'path':path,'type':type(v).__name__,'value':v.item()}]
    if isinstance(v,dict):return [r for k,x in v.items() for r in non_json_scalars(x,path+'.'+k)]
    if isinstance(v,(list,tuple)):return [r for i,x in enumerate(v) for r in non_json_scalars(x,path+'[%s]'%i)]
    return []

def scene_from_trace():
    import sapien
    import ast,copy,transforms3d as t3d
    # Importing envs initializes unrelated clutter registries. Extract only
    # the exact Actor API class; its methods are unchanged and no actor is built.
    source=P/'envs/utils/actor_utils.py';tree=ast.parse(source.read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Actor')
    namespace={'np':np,'sapien':sapien,'t3d':t3d,'deepcopy':copy.deepcopy}
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),cls],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(source)+':CPU_Actor_API','exec'),namespace);Actor=namespace['Actor']
    trace_path=D/'on/qualification_trace.npz';spec=load(D/'on/suffix_spec.json');qualification=load(D/'qualification_spec.json')
    binding=qualification['binding'];world=load(D/'on/model_024_released_full.json')['world'];frames=50
    contacts=tail_field(trace_path,'contact_pairs_json',frames)
    roles=('main_can','box','scale','stand')
    with np.load(trace_path,allow_pickle=False) as t:
        pose_values={role:t['role_object_pose__'+role][-1].copy() for role in roles}
        linear={role:t['role_object_linear_velocity__'+role][-frames:].copy() for role in roles}
        angular=t['object_angular_velocity'][-frames:].copy();eef=t['eef_pose'][-1].copy()
        eeflv=t['eef_linear_velocity'][-frames:].copy();eefav=t['eef_angular_velocity'][-frames:].copy()
        gripper=float(t['gripper_command'][-1,0]);steps=t['step_index'];length=len(steps);final_step=int(steps[-1])
    paths={'main_can':'071_can/model_data0.json','box':'062_plasticbox/model_data2.json','scale':'072_electronicscale/model_data0.json','stand':'074_displaystand/model_data0.json'}
    actors={};assets=[]
    for role in roles:
        source=P/'assets/objects'/paths[role];assets.append(source)
        config=load(source);value=pose_values[role]
        actual=[s for s in world['shapes'] if s['role']==('held_can' if role=='main_can' else role)]
        if not actual:raise ValueError('actual actor registry missing '+role)
        if not np.allclose(config['scale'],actual[0]['shape_scale'],atol=1e-7,rtol=0):raise ValueError('saved actor scale differs from metadata')
        entity=SimpleNamespace(get_pose=lambda value=value:sapien.Pose(value[:3],value[3:]),get_name=lambda name=actual[0]['actor_name']:name)
        actor=Actor.__new__(Actor);actor.actor=entity;actor.config=config;actors[role]=actor
    rows=[{'actor_linear_velocity':linear['main_can'][i].tolist(),'actor_angular_velocity':angular[i].tolist(),
      'eef_linear_velocity':eeflv[i].tolist(),'eef_angular_velocity':eefav[i].tolist(),
      'role_actor_linear_velocities':{role:linear[role][i].tolist() for role in roles},'contact_pairs':json.loads(contacts[i])} for i in range(frames)]
    scene=SimpleNamespace(can=actors['main_can'],box=actors['box'],scale=actors['scale'],stand=actors['stand'],trace=rows,
      trace_role_actors=actors,trace_actor=actors['main_can'],robot=SimpleNamespace(get_left_ee_pose=lambda:eef.tolist()),
      is_left_gripper_open=lambda:gripper>.8,_cmf_f2_active_cavity_contract=binding['strict_cavity_contract'],
      _cmf_f2_scale_support_half_xy_m=binding['layout_payload']['on_region_half_xy_m'])
    return scene,spec,assets,{'trace_states':length,'last_step':final_step,'final_window_frames':frames,'gripper_command':gripper,
      'reconstruction_kind':'CPU_READ_ONLY_ACTOR_API_PROXIES_FROM_MEASURED_TRACE_NOT_A_SIMULATOR_SCENE'}

def run():
    old=load(D/'on/suffix_terminal.json');branch=load(D/'on/branch_terminal.json');held_path=D/'on/model_019_original_held_gate.json';held=load(held_path)
    if old['error']!={'type':'TypeError','message':'Object of type bool_ is not JSON serializable'} or old['solver_problems']!=4:raise ValueError('not the exact serialization failure')
    if (D/'on/model_035_original_final_gate.json').exists() or any((D/'on').glob('*original_final_gate.json')):raise ValueError('unexpected original final receipt exists')
    if held['pass'] is not True or not all(s['result']['pass'] is True for s in old['stages']):raise ValueError('earlier prerequisite did not pass')
    scene,spec,assets,meta=scene_from_trace();result=gates.final(scene,spec,held);scalars=non_json_scalars(result)
    try:digest(result);reproduced=False
    except TypeError as e:reproduced=str(e)=='Object of type bool_ is not JSON serializable'
    converted=json_values(result);digest(converted)
    files=[D/'goal_terminal.json',D/'job_terminal.json',D/'on/qualification_trace.npz',D/'on/suffix_terminal.json',D/'on/suffix_spec.json',D/'on/branch_terminal.json',held_path,D/'qualification_spec.json',D/'on/model_024_released_full.json',
      D.with_name(D.name+'_guard')/(D.name+'.terminal.json'),Path(__file__),A/'goal_pilot48_v1/f2_on_beside_runtime_v1/gates.py',
      A/'goal_pilot48_v1/f2_on_beside_runtime_v2/runtime.py',P/'controlled_multi_future/family_runners_v3_3.py',P/'controlled_multi_future/family_runners_v3_1.py',P/'envs/utils/actor_utils.py',*assets]
    r={'schema_version':'f2_on_final_serialization_append_only_review_v1','original_suffix_pass':old['pass'],'original_scientific_route_pass':branch['scientific_route_pass'],
      'error_class':'FINAL_RECEIPT_NUMPY_SCALAR_SERIALIZATION_INFRASTRUCTURE','original_error_reproduced':reproduced,
      'non_json_scalar_fields':scalars,'recomputed_original_final_gate':converted,'measured_trace_summary':meta,
      'original_earlier_stages_pass':True,'new_GPU_or_physical_execution':False,'old_terminal_or_trace_modified':False,
      'derived_final_predicates_pass':converted['pass'],'full_root_or_pilot_acceptance':False,
      'unique_fix':'normalize_numpy_scalars_to_identical_Python_values_at_final_receipt_boundary_no_predicate_change',
      'no_successful_action_rerun_recommended':True,'main_append_only_qualification_adoption_required':True,
      'files':{str(p):sha(p) for p in files}}
    r['receipt_sha256']=digest(r);return r

if __name__=='__main__':
    from realization_utf8_io_v1 import write_new
    r=run();write_new(OUT/'RECOVERY_REVIEW_001.json',r)
    print(json.dumps({'error_reproduced':r['original_error_reproduced'],'checks':r['recomputed_original_final_gate']['checks'],
      'derived_final_predicates_pass':r['derived_final_predicates_pass'],'numpy_fields':r['non_json_scalar_fields'],'receipt_sha256':r['receipt_sha256']}))
