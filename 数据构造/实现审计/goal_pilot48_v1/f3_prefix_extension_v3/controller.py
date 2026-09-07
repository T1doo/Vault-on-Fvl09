"""Second fresh V5 micro + restored-full-world prefix, CPU-wired only."""
import ast,copy,inspect,types,hashlib
from pathlib import Path
import numpy as np
from goal_pilot48_v1.f3_runtime_v5 import micro
from .boundaries import execute_micro,record,tail_with_markers
from .locked_tail import original_tail
from .prerequisite import restored,load as load_prior

def after_micro_sequence(micro_result,record_pass,restore_full_world,extend15,extend40,tail):
    if micro_result.get('pass') is not True:return micro_result
    if not restored(micro_result):raise ValueError('full-world restoration prerequisite failed')
    restore_full_world();record_pass(micro_result);extend15();extend40();return tail()
def lift_extension_goal(actual,distance):
    if distance not in (.015,.04):raise ValueError('fixed lift continuation distances only')
    goal=np.asarray(actual,dtype=float).copy()
    if goal.shape!=(7,) or not np.isfinite(goal).all():raise ValueError('bad actual lift pose')
    goal[2]+=distance;return goal
def check_budget(count,target_count):
    if type(count)is not int or type(target_count)is not int or target_count<1 or count+target_count>14:raise ValueError('fourteen total single-query cap')

def execute(scene,proposal,out):
    from controlled_multi_future import family_runners_v3_3 as old
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_execute_control,_arm_eef_pose,_planner_reset
    from model_apply import runtime_joint_state
    from goal_mapping import actual_flange_goal_to_reported_command
    from realization_utf8_io_v1 import write_new
    out=Path(out);result=execute_micro(scene,proposal,out)
    if result.get('pass') is not True:return result
    if scene.planner_query_count!=3:raise ValueError('fresh V5 micro exact three query budget')
    if not restored(result):raise ValueError('missing actual full-world restoration')
    baseline=result['post_lift']['lift_execution_receipt']['start_trace_row']
    if scene._cmf_extension_boundaries['post_close']['trace_row']!=baseline:raise ValueError('postclose hook/physical gate baseline mismatch')
    transform=np.asarray(scene._cmf_extension_boundaries['post_close']['relative_pose'])
    extension=out/'shared_v_extension';extension.mkdir(exist_ok=False)
    def full_world_check():
        lease=getattr(scene,'_cmf_tangent_lease',None)
        if lease is not None and lease.state!='expired':raise ValueError('micro model certificate still active')
        for key in ('motion_gen','motion_gen_batch'):
            checker=getattr(scene.robot.left_planner,key).world_coll_checker
            if hasattr(checker,'support_pair_policy_version'):raise ValueError('pair exclusion survived full-world restoration')
    def record_pass(value):
        write_new(extension/'second_fresh_micro_pass_before_continuation.json',{'micro_pass':True,'full_world_restored':True,'result':value,
            'same_scene_id':scene._cmf_scene_instance_id,'first_confirmation':scene._cmf_first_confirmation,'early_boundaries':scene._cmf_extension_boundaries})
    def execute_checked(s,control,label,arm='left'):
        from goal_pilot48_v1.f3_native_self_pair_v1.checker import check_controls
        full_world_check();names,q=runtime_joint_state(scene)
        gate=check_controls(control['position'],list(scene.robot.left_planner.motion_gen.kinematics.joint_names),names,q)
        write_new(extension/(label+'.native_self_pair_gate.json'),gate)
        if not gate['pass']:raise RuntimeError(label+' native pair failed before execution')
        record(scene,label+'_start');_execute_control(s,control,label,arm=arm);record(scene,label+'_end')
    def plan_actual(s,targets,**kwargs):
        if s is not scene:raise ValueError('cross-scene plan')
        full_world_check();check_budget(scene.planner_query_count,len(targets));commands=[]
        for target in targets:
            v=copy.deepcopy(target);v['pose']=actual_flange_goal_to_reported_command(scene.robot,scene.robot.left_planner,np.asarray(target['pose'])).tolist();commands.append(v)
        return _plan_chain(scene,commands,query_limit=scene.planner_query_count+len(commands),arm='left')
    def move_actual(s,pose,label):
        plan=plan_actual(s,[{'pose':list(pose),'segment_id':label}])
        if not plan['pass']:raise RuntimeError(label+' plan failed')
        execute_checked(scene,plan['controls'][0],label,arm='left');return plan['controls'][0]
    def extend(distance,label):move_actual(scene,lift_extension_goal(_arm_eef_pose(scene,'left'),distance),label)
    def tail():
        env=dict(old.__dict__);env.update(_plan_chain=plan_actual,_move_left=move_actual,_execute_control=execute_checked)
        fn=tail_with_markers(original_tail,env)
        if old.F3_V_NOMINAL_AMPLITUDE_M_V3_3!=.055 or old.F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2!=50:raise ValueError('frozen V contract changed')
        if len(old._time_dilated_closed_loop_event_targets(np.array([0.,0.,1.,1.,0.,0.,0.]),axis='V',amplitude_m=.055,segment_prefix='contract_check'))!=7:raise ValueError('seven point V changed')
        reset=_planner_reset(scene,planner_seed=old.PLANNER_SEED,variant_id=proposal['proposal_id']+':sharedV',arm='left')
        prefix=fn(scene,0,baseline,transform,{'contract_sha256':proposal['receipt_sha256']},{},
            {'source':'fresh V5 micro recipe, no old grasp chooser','recipe_id':proposal['proposal_id']},reset)
        accepted=prefix['prefix_physical_acceptance']['pass']
        if scene.planner_query_count!=14:raise ValueError('completed V prefix did not consume exact14 single problems')
        arrays=prefix.pop('arrays')
        with (extension/'prefix_arrays.npz').open('xb') as f:np.savez_compressed(f,**arrays)
        prefix['prefix_arrays_sha256']=hashlib.sha256((extension/'prefix_arrays.npz').read_bytes()).hexdigest()
        prefix['actual_boundary_records']=scene._cmf_extension_boundaries
        write_new(extension/'prefix_result.json',prefix)
        return {**result,'pass':bool(accepted),'fresh_micro_pass':True,'shared_v_executed':True,'shared_v_prefix':prefix,
            'total_queries':14,'earliest_failed_stage':None if accepted else 'shared_v_prefix_gate'}
    try:return after_micro_sequence(result,record_pass,full_world_check,lambda:extend(.015,'f3_prefix_complete_lift4cm'),lambda:extend(.04,'f3_prefix_lift8cm'),tail)
    finally:write_new(extension/'actual_boundary_records.json',scene._cmf_extension_boundaries)

def run(manifest):
    first=load_prior(manifest)
    source=inspect.getsource(micro.run);tree=ast.parse(source);changes=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Compare) and isinstance(node.left,ast.Constant) and node.left.value==0 and len(node.comparators)==2:
            last=node.comparators[-1]
            if isinstance(last,ast.Constant) and last.value==3:last.value=14;changes+=1
    if changes!=1:raise ValueError('V5 lifecycle budget AST mismatch')
    def bound_execute(scene,proposal,out):scene._cmf_first_confirmation=first;return execute(scene,proposal,out)
    namespace=dict(micro.__dict__);namespace['execute']=bound_execute
    exec(compile(ast.fix_missing_locations(tree),str(Path(__file__)),'exec'),namespace)
    return namespace['run'](manifest)
