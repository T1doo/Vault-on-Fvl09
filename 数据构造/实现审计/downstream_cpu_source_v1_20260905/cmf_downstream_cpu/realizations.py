"""Real-rollout variation builder/executor and raw/video pairing bridge."""
import copy,math
from pathlib import Path
import numpy as np
from .io import canonical,seal,sha,write_new

RULES={'r_pc':{'transport_z_offset_m':0.,'duration_scale':1.},
 'r_inv_path':{'transport_z_offset_m':.015,'duration_scale':1.},
 'r_inv_motion':{'transport_z_offset_m':0.,'duration_scale':1.10}}

def build_spec(root,program,operations,realization):
    if root['family'] not in ('F1','F4') or realization not in RULES:raise ValueError('family/realization')
    if root['programs'].get(program['program_id'])!=canonical(program):raise ValueError('candidate/program binding')
    if not operations or any(x['kind'] not in ('move','gripper','hold','verify','prefix_replay','focus_actor') for x in operations):raise ValueError('operation schema')
    if any(x.get('arm') not in ('left','right') for x in operations if x['kind'] in ('move','gripper','hold')):raise ValueError('arm routing')
    rule=copy.deepcopy(RULES[realization]);targets=copy.deepcopy(operations);changed=[]
    for i,op in enumerate(targets):
        if op['kind']=='move' and op.get('noncritical_transport') is True:
            if op.get('boundary_critical') is True:raise ValueError('critical boundary marked variable')
            op['target_pose'][2]+=rule['transport_z_offset_m'];op['duration_scale']=rule['duration_scale'];changed.append(i)
    if realization!='r_pc' and not changed:raise ValueError('no declared noncritical transport; do not invent a variant')
    query_count=sum(x['kind']=='move' and not x.get('reuse_frozen_control',False) for x in targets)
    value={'schema_version':'cmf_realization_spec_v1','root_id':root['root_id'],'family':root['family'],
      'program_id':program['program_id'],'program_semantic_sha256':canonical(program),'candidate_universe_sha256':root['candidate_universe_sha256'],
      'current_sha256':root['current_sha256'],'anchor_sha256':root['anchor_sha256'],'realization':realization,
      'base_operation_sha256':canonical(operations),'operations':targets,'variation_rule':rule,'variation_rule_sha256':canonical(rule),
      'modified_operation_indices':changed,'arm_routing':[x.get('arm') for x in targets],'primary_frequency_hz':250,
      'budget':{'planner_queries':query_count,'fresh_scenes':1,'rollouts':1,'automatic_retry':False,'timeout_seconds':3600},
      'origin_required':'new_real_rollout','collection_authorized':False,'status':'CPU_IMPLEMENTED_ADAPTER_BINDING_AND_EXECUTION_REVIEW_REQUIRED'}
    return seal(value)

def retime_control_for_new_execution(control,scale):
    """Change future commands before a NEW rollout, never resample accepted raw."""
    if scale not in (1.,1.10):raise ValueError('unregistered speed rule')
    result=copy.deepcopy(control)
    if scale==1.:return result
    q=np.asarray(control['position'],dtype=float);v=np.asarray(control['velocity'],dtype=float)
    if q.ndim!=2 or q.shape!=v.shape or len(q)<2 or not np.all(np.isfinite(q)) or not np.all(np.isfinite(v)):raise ValueError('planner controls')
    n=math.ceil((len(q)-1)*scale)+1;old=np.arange(len(q));new=np.linspace(0,len(q)-1,n)
    result['position']=np.column_stack([np.interp(new,old,q[:,i]) for i in range(q.shape[1])]).astype(np.asarray(control['position']).dtype)
    result['velocity']=np.column_stack([np.interp(new,old,v[:,i])/scale for i in range(v.shape[1])]).astype(np.asarray(control['velocity']).dtype)
    return result

def preflight(spec,adapter):
    p=dict(spec);h=p.pop('receipt_sha256',None)
    if h!=canonical(p):raise ValueError('realization spec hash')
    required=('open_fresh_scene','restore_anchor','plan_move','execute_move','set_gripper','hold','verify_program','collect_streams_and_video','cleanup_receipt')
    if any(not callable(getattr(adapter,k,None)) for k in required):raise ValueError('incomplete concrete adapter binding')
    if any(op.get('reuse_frozen_control') for op in spec['operations']) and not callable(getattr(adapter,'load_frozen_control',None)):raise ValueError('frozen-control loader missing')
    for kind in ('prefix_replay','focus_actor'):
        if any(op['kind']==kind for op in spec['operations']) and not callable(getattr(adapter,kind,None)):raise ValueError(kind+' binding missing')
    return {'dispatch':'execute_realization','planner_query_cap':spec['budget']['planner_queries'],
            'scene_cap':1,'adapter_methods':list(required),'GPU_used':False,'collection_authorized':False}

def execute_realization(spec,adapter,authority):
    """Operational orchestration; external Guard/UUID/lease proof stays mandatory."""
    preflight(spec,adapter)
    a=dict(authority);h=a.pop('receipt_sha256',None)
    if h!=canonical(a) or a.get('authorized') is not True or a.get('spec_receipt_sha256')!=spec['receipt_sha256'] or a.get('guard_verified') is not True:raise PermissionError('new real rollout is not authorized')
    if a.get('scope')!='REALIZATION_REAL_GPU_ROLLOUT':raise PermissionError('CPU tests cannot authorize collection')
    query_count=0;result=None
    with adapter.open_fresh_scene(spec) as scene:
        anchor=adapter.restore_anchor(scene,spec)
        if anchor.get('equivalent') is not True:raise ValueError('anchor mismatch')
        for op in spec['operations']:
            if op['kind']=='prefix_replay':
                if adapter.prefix_replay(scene,op).get('pass') is not True:raise ValueError('prefix replay failed')
            elif op['kind']=='focus_actor':adapter.focus_actor(scene,op['actor_role'])
            elif op['kind']=='move':
                if op.get('reuse_frozen_control'):
                    control=adapter.load_frozen_control(scene,op)
                else:
                    query_count+=1
                    if query_count>spec['budget']['planner_queries']:raise RuntimeError('planner budget')
                    control=adapter.plan_move(scene,op)
                adapter.execute_move(scene,op,retime_control_for_new_execution(control,op.get('duration_scale',1.)))
            elif op['kind']=='gripper':adapter.set_gripper(scene,op)
            elif op['kind']=='hold':adapter.hold(scene,op)
            elif adapter.verify_program(scene,op).get('pass') is not True:raise ValueError('program checkpoint failed')
        verifier=adapter.verify_program(scene,spec)
        if verifier.get('pass') is not True:raise ValueError('same-intent verification failed')
        result=adapter.collect_streams_and_video(scene,spec)
        result.update(verifier=verifier,planner_query_count=query_count,anchor_receipt=anchor)
    cleanup=adapter.cleanup_receipt()
    if cleanup.get('cleanup_safety_pass') is not True or cleanup.get('orphan_process_count')!=0:raise RuntimeError('cleanup evidence')
    result['cleanup']=cleanup;return result

def save_real_rollout(spec,rollout,output,*,rollout_id):
    from controlled_multi_future.raw_writer import write_raw_attempt,verify_raw_artifact_integrity
    from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
    if rollout.get('origin_kind')!='real_rollout' or rollout.get('synthetic') is not False:raise ValueError('derived/synthetic views cannot be new realizations')
    if not rollout_id or rollout.get('derived_from_raw_id') is not None:raise ValueError('rollout identity')
    output=Path(output)
    raw=write_raw_attempt(output/'raw',rollout['streams'],rollout['audit_streams'],rollout['provenance'])
    integrity=verify_raw_artifact_integrity(output/'raw')
    video=validate_development_trajectory_mp4_receipt_v1(rollout['video_receipt'],expected_path=Path(rollout['video_receipt']['path']))
    if integrity['pass'] is not True or video['pass'] is not True:raise ValueError('raw/video integrity')
    pairing=seal({'schema_version':'cmf_realization_pairing_v1','root_id':spec['root_id'],'program_id':spec['program_id'],
      'program_semantic_sha256':spec['program_semantic_sha256'],'candidate_universe_sha256':spec['candidate_universe_sha256'],
      'current_sha256':spec['current_sha256'],'anchor_sha256':spec['anchor_sha256'],'realization':spec['realization'],
      'raw_id':canonical({'rollout_id':rollout_id,'manifest':raw}),'rollout_id':rollout_id,'origin_kind':'real_rollout',
      'spec_receipt_sha256':spec['receipt_sha256'],'variation_rule_sha256':spec['variation_rule_sha256'],
      'raw_manifest_sha256':integrity['integrity_sidecar']['manifest_payload_sha256'],'raw_integrity_pass':True,'video_integrity_pass':True,
      'family_verifier_receipt':rollout['verifier'],'cleanup':rollout['cleanup'],'stage_authorization_granted':False})
    write_new(output/'pairing.json',pairing);return pairing

class SapienOperationAdapter:
    """Concrete motion/trace bridge; family-specific scene/anchor/verifier are bound hooks."""
    def __init__(self,scene_factory,anchor_verifier,program_verifier,output,*,provenance,family_adapter=None):
        self.scene_factory=scene_factory;self.anchor_verifier=anchor_verifier;self.program_verifier=program_verifier
        self.output=Path(output);self.provenance=provenance;self.context=None;self.family_adapter=family_adapter
    def open_fresh_scene(self,spec):self.context=self.scene_factory(spec);return self.context
    def restore_anchor(self,scene,spec):return self.anchor_verifier(scene,spec)
    def prefix_replay(self,scene,op):
        from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
        from controlled_multi_future.canonical_prefix_replay_v1 import replay_canonical_prefix
        manifest,arrays=load_canonical_prefix_artifact(Path(op['artifact_directory']))
        if manifest['artifact_sha256']!=op['artifact_sha256']:raise ValueError('prefix artifact changed')
        a=self.family_adapter
        if a is None:raise ValueError('concrete family adapter not bound')
        a.initialize_prefix_replay_trace(scene)
        replay=replay_canonical_prefix(scene,manifest=manifest,arrays=arrays,reference_current=op['reference_current'],capture_current=a.capture_current,capture_anchor=a.capture_anchor)
        physical=a.validate_replayed_prefix_physical(scene,replay)
        return {'pass':physical.get('pass') is True,'replay':replay,'physical':physical}
    def focus_actor(self,scene,role):
        actor=scene.role_actors[role] if role in getattr(scene,'role_actors',{}) else getattr(scene,role.lower())
        scene.set_trace_contact_actor(actor)
    def plan_move(self,scene,op):
        from controlled_multi_future.family_runners_v3_1 import _plan_chain
        before=int(getattr(scene,'planner_query_count',0))
        result=_plan_chain(scene,[{'segment_id':op['operation_id'],'pose':op['target_pose']}],query_limit=before+1,arm=op['arm'])
        if result['pass'] is not True:raise RuntimeError('variant move planner failed')
        return result['controls'][0]
    def execute_move(self,scene,op,control):
        from controlled_multi_future.family_runners_v3_1 import _execute_control
        return _execute_control(scene,control,op['operation_id'],arm=op['arm'])
    def set_gripper(self,scene,op):
        from controlled_multi_future.family_runners_v3_1 import _must_action,_arm_tag
        action=scene.open_gripper(_arm_tag(op['arm'])) if op['command']=='open' else scene.close_gripper(_arm_tag(op['arm']),pos=op['position'])
        return _must_action(scene,action,op['operation_id'])
    def hold(self,scene,op):
        from controlled_multi_future.family_runners_v3_1 import _wait_and_record
        return _wait_and_record(scene,op['steps'])
    def verify_program(self,scene,spec):return self.program_verifier(scene,spec)
    def collect_streams_and_video(self,scene,spec):
        from controlled_multi_future.probes.runtime_trace import trace_rows_to_raw_streams
        path=self.output/'source_trace.npz';scene.save_trace(path)
        streams,audit=trace_rows_to_raw_streams(scene.trace)
        provenance={**scene.trace_provenance(),**self.provenance,'trace_source_path':str(path),'trace_source_sha256':sha(path),
           'synthetic':False,'realization_spec_sha256':spec['receipt_sha256'],'formal_data':False,'stage0_data':False,'stage0_authorized':False}
        return {'streams':streams,'audit_streams':audit,'provenance':provenance,'origin_kind':'real_rollout','synthetic':False}
    def cleanup_receipt(self):return self.context.cleanup_receipt

def execute_to_artifacts(spec,adapter,authority,output,*,rollout_id):
    """Failed attempts are retained; no raw/variant copying or automatic retry."""
    try:
        result=execute_realization(spec,adapter,authority)
        if 'video_receipt' not in result:result['video_receipt']=result['cleanup']['development_video_receipt']
        return save_real_rollout(spec,result,output,rollout_id=rollout_id)
    except Exception as exc:
        cleanup=None
        try:cleanup=adapter.cleanup_receipt()
        except Exception:pass
        failure=seal({'schema_version':'cmf_realization_failure_v1','spec_receipt_sha256':spec['receipt_sha256'],
            'rollout_id':rollout_id,'error':{'type':type(exc).__name__,'message':str(exc)},'cleanup':cleanup,'accepted':False,'automatic_retry':False})
        write_new(Path(output)/'failure.json',failure)
        return failure
