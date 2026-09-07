"""S1 per-cell read-only checks, bounded by the outer180s CPU subprocess."""
import ast,json,time,traceback,zipfile
import numpy as np
from .common import *

def equal(a,b):
    a=np.asarray(a);b=np.asarray(b)
    return a.shape==b.shape and bool(np.array_equal(a,b,equal_nan=True) if a.dtype.kind in 'fc' and b.dtype.kind in 'fc' else np.array_equal(a,b))

def primary_converter(source):
    tree=ast.parse(source.read_text(encoding='utf-8'))
    helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_planner_interval_arrays')
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='trace_rows_to_raw_streams')
    stop=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='audit_streams' for t in n.targets))
    fn.body=fn.body[:stop]+[ast.parse('return streams, (planner_active, planner_query_ids, planner_sources, planner_starts, planner_ends)').body[0]]
    ns={'np':np};exec(compile(ast.fix_missing_locations(ast.Module(body=[helper,fn],type_ignores=[])),str(source)+':unchanged_primary_mapping','exec'),ns)
    return ns['trace_rows_to_raw_streams']

def trace_primary(trace):
    mapping={'effective_setpoint':'controller_effective_setpoint','requested_command':'requested_command','planner_goal_eef_pose':'planner_goal_eef_pose',
      'gripper_command':'gripper_command','component_mask':'component_masks','joint_qpos':'joint_qpos','joint_qvel':'joint_qvel','dual_eef':'dual_eef_pose',
      'planner_goal_active':'planner_goal_active','planner_query_id':'planner_query_id','planner_goal_source':'planner_goal_source','timestamp':'timestamp','initial_state':'initial_state'}
    arrays={k:trace[v] for k,v in mapping.items()};count=len(arrays['timestamp'])
    return [{k:(bool(v[i]) if k=='initial_state' else v[i]) for k,v in arrays.items()} for i in range(count)]

def open_array(archive,name):
    stream=archive.open(name+'.npy');version=np.lib.format.read_magic(stream)
    shape,fortran,dtype=np.lib.format._read_array_header(stream,version)
    if fortran or dtype.hasobject or len(shape)!=1:raise ValueError('unexpected JSON array layout')
    return stream,shape,dtype

def perform(row,lock):
    from controlled_multi_future import raw_writer as raw
    from realization_current_layout_audit_v1 import audit as current_audit
    path=Path(row['paths']['rollout']);current=Path(row['paths']['current']);stages={}
    for p,h in row['files'].items():
        if sha(p)!=h:raise ValueError('locked input changed '+p)
    integrity=raw.verify_raw_artifact_integrity(path/'raw')
    if not integrity['pass']:raise ValueError('original raw integrity failed')
    m=integrity['manifest'];n=m['action_count'];stages['integrity']=integrity['checks']
    with np.load(path/'raw/raw_streams.npz',allow_pickle=False) as saved,np.load(path/'trace_source.npz',allow_pickle=False) as trace:
        streams={k[8:]:saved[k] for k in saved.files if k.startswith('stream__')};streams['field_metadata']=m['stream_field_metadata']
        audit={k[7:]:saved[k] for k in saved.files if k.startswith('audit__') and k!='audit__contact_pairs_json'}
        raw.validate_raw_streams(streams);raw.validate_simulator_timing(m['provenance']);raw.validate_planner_goal_audit(streams,audit,m['provenance'])
        stages['original_primary_timing_planner_validators']=True
        source=P/'controlled_multi_future/probes/runtime_trace.py'
        if row['cell']['family']=='F1':source=W/'Robotwin2/tmp/cmf_f1_parent_317387b/数据构造/实现审计/代码审阅快照/controlled_multi_future/probes/runtime_trace.py'
        derived,intervals=primary_converter(source)(trace_primary(trace));matches={}
        for field,values in streams.items():
            matches[field]=values==derived[field] if field=='field_metadata' else equal(values,derived[field])
        if not all(matches.values()):raise ValueError('trace-to-raw primary mismatch '+str([k for k,v in matches.items() if not v]))
        stages['primary_trace_to_raw_all_fields']=matches
        interval_names=('planner_goal_active','planner_query_id','planner_goal_source','planner_goal_start_step','planner_goal_end_step')
        generated=dict(zip(interval_names,intervals));generated['planner_goal_available']=intervals[0]
        audit_matches={}
        for field,value in audit.items():
            if field=='contact_count':continue
            expected=generated[field] if field in generated else trace['joint_qf'] if field=='realized_joint_qf' else trace[field]
            audit_matches[field]=equal(value,expected)
        if not all(audit_matches.values()):raise ValueError('trace-to-raw audit mismatch '+str([k for k,v in audit_matches.items() if not v]))
        # JSON columns are3–8GB when expanded because Unicode pads every row.
        # Stream real chunks instead of allocating that whole matrix or faking
        # shape-only data. Original audit validators run on every actual block.
        total=0;blocks=0
        with zipfile.ZipFile(path/'raw/raw_streams.npz') as rz,zipfile.ZipFile(path/'trace_source.npz') as tz:
            rs,rshape,rdtype=open_array(rz,'audit__contact_pairs_json');ts,tshape,tdtype=open_array(tz,'contact_pairs_json')
            if rshape!=tshape or rshape!=(n+1,):raise ValueError('contact JSON row count differs')
            with rs,ts:
                for start in range(0,n+1,32):
                    length=min(32,n+1-start);rb=rs.read(length*rdtype.itemsize);tb=ts.read(length*tdtype.itemsize)
                    r=np.frombuffer(rb,dtype=rdtype);t=np.frombuffer(tb,dtype=tdtype)
                    if len(r)!=length or len(t)!=length or not equal(r,t):raise ValueError('contact JSON raw/trace row mismatch')
                    if not equal(np.asarray([len(json.loads(s)) for s in t],dtype=np.int64),audit['contact_count'][start:start+length]):raise ValueError('contact_count not derived from same trace row')
                    chunk={k:(v[start:start+length-1] if k in raw.PLANNER_AUDIT_FIELDS else v[start:start+length]) for k,v in audit.items()}
                    chunk.update(contact_pairs_json=r,field_metadata=m['audit_field_metadata'])
                    raw.validate_audit_streams(chunk,length-1);raw.validate_real_runtime_audit_fields(chunk,m['provenance'])
                    blocks+=1;total+=length
        audit_matches['contact_pairs_json']=True;audit_matches['contact_count']=True
        stages['audit_trace_to_raw_all_fields']=audit_matches;stages['audit_actual_chunk_checks']={'blocks':blocks,'state_rows':total,'all_state_rows_covered':total==n+1,'planner_rows_checked_globally':n}
        current_result=current_audit(current,path/'trace_source.npz')
        if not current_result['pass'] or current_result['unique_articulation_dofs']!=38 or current_result['model_visible_robot_state_dimension']!=76:raise ValueError('current storage contract')
        if not equal(streams['realized_qpos'][0],trace['joint_qpos'][0]) or not equal(streams['realized_qvel'][0],trace['joint_qvel'][0]):raise ValueError('raw/current row0 alignment')
        stages['current_38_76_initial_row']=current_result
    for p,h in row['files'].items():
        if sha(p)!=h:raise ValueError('input changed during CPU check '+p)
    return {'pass':True,'checks':stages,'actions':n,'states':n+1,'action_dim':26,'frequency_hz':250,
      'primary_source_file':str(source),'primary_source_sha256':sha(source),
      'stage0_wrapper_not_used_reason':'validate_raw_artifact_contract requires stage0_authorized=true, not applicable to nonformal pilot; underlying original validators used without altering flags',
      'scientific_family_verifier_rerun':False,'H_views_generated':False,'model_run':False}

def run(index):
    lock=checked(OUT/'INPUT_LOCK_001.json');row=lock['cells'][index];began=time.monotonic();result=None;error=None
    try:
        for p,h in lock['source_files'].items():
            if sha(p)!=h:raise ValueError('locked checker source changed '+p)
        result=perform(row,lock)
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    value=seal({'schema_version':'no_training_S1_cell_structure_time_v1','input_lock_receipt_sha256':lock['receipt_sha256'],'cell_index':index,
      'cell_identity':{k:row['cell'][k] for k in ('family','pilot','program_id','realization')},'pass':error is None and result is not None and result['pass'],
      'result':result,'error':error,'elapsed_seconds':time.monotonic()-began,'timeout_seconds':180,'raw_modified':False,'pilot_registration_modified':False,'suite_complete':False})
    write(OUT/'cells'/('%02d.json'%index),value);print('S1_CELL',index,'PASS' if value['pass'] else 'FAIL',round(value['elapsed_seconds'],3),'' if error is None else error['message'],flush=True)
    return value
if __name__=='__main__':
    import sys
    run(int(sys.argv[1]))
