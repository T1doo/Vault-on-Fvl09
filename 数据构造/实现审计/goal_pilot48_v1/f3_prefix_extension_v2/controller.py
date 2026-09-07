"""Private runtime extension; execution requires a separately issued Goal job."""
import ast,copy,inspect,types
from pathlib import Path
import numpy as np
from goal_pilot48_v1.f3_runtime_v4 import micro
from .locked_tail import original_tail

def after_micro_sequence(micro_result,record_pass,restore_full_world,extend15,extend40,tail):
    """Pure ordering seam: none of the continuation callbacks run on failed micro."""
    if micro_result.get('pass') is not True:return micro_result
    record_pass(micro_result)
    restore_full_world()
    extend15();extend40()
    return tail()

def execute(scene,proposal,out):
    from controlled_multi_future import family_runners_v3_3 as old
    from controlled_multi_future.family_runners_v3_1 import _plan_chain,_execute_control as original_execute_control,_arm_eef_pose,_planner_reset
    from controlled_multi_future.geometry import relative_pose
    from model_apply import query_state,runtime_joint_state
    from goal_mapping import actual_flange_goal_to_reported_command
    from realization_utf8_io_v1 import write_new
    out=Path(out);result=micro.execute(scene,proposal,out)
    initial_count=scene.planner_query_count
    if result.get('pass') is not True:return result
    if initial_count!=3:raise ValueError('fresh V4 micro must consume exactly three query problems')
    baseline=result['post_lift']['lift_execution_receipt']['start_trace_row']
    baseline_row=scene.trace[baseline]
    transform=relative_pose(baseline_row['eef'],baseline_row['actor_pose'])
    extension=out/'shared_v_extension';extension.mkdir(exist_ok=False)
    def record_pass(value):
        write_new(extension/'fresh_micro_pass_before_continuation.json',{'micro_pass':True,'result':value,
            'trace_baseline_row':baseline,'query_counter':initial_count,'same_fresh_scene':True})
    def restore():
        # Never carry the supported bottle/pad exclusion into free space.
        full=micro._build_full_attached_bottle_model(scene,extension)
        names,q=runtime_joint_state(scene);checks={}
        for name in ('motion_gen','motion_gen_batch'):
            mg=getattr(scene.robot.left_planner,name)
            if 'Support' in type(mg.world_coll_checker).__name__:raise ValueError('support-specific checker survived restoration')
            checks[name]=query_state(mg,q,names)[0]
        write_new(extension/'full_world_restoration.json',{'checks':checks,'all_world_pairs_restored':True,
            'attachment':full,'high_level_start_checks':2,'planner_queries':0})
        if not all(r['valid'] for r in checks.values()):raise RuntimeError('full world restore rejects actual postmicro state')
    def execute_native_checked(s,control,label,arm='left'):
        from goal_pilot48_v1.f3_native_self_pair_v1.checker import check_controls
        names,q=runtime_joint_state(scene)
        checked=check_controls(control['position'],list(scene.robot.left_planner.motion_gen.kinematics.joint_names),names,q)
        write_new(extension/(label+'.native_self_pair_gate.json'),checked)
        if not checked['pass']:raise RuntimeError(label+' native self pair gate failed before controls')
        return original_execute_control(s,control,label,arm=arm)
    def plan_actual(s,targets,**kwargs):
        if s is not scene:raise ValueError('cross-scene continuation')
        if scene.planner_query_count+len(targets)>14:raise ValueError('total fourteen single-query cap')
        commands=[]
        for t in targets:
            v=copy.deepcopy(t);v['pose']=actual_flange_goal_to_reported_command(scene.robot,scene.robot.left_planner,np.asarray(t['pose'])).tolist();commands.append(v)
        return _plan_chain(scene,commands,query_limit=scene.planner_query_count+len(commands),arm='left')
    def move_actual(s,pose,label):
        plan=plan_actual(s,[{'pose':list(pose),'segment_id':label}])
        if not plan['pass']:raise RuntimeError(label+' planner failure')
        execute_native_checked(scene,plan['controls'][0],label,arm='left')
        return plan['controls'][0]
    def extend(d,label):
        goal=np.array(_arm_eef_pose(scene,'left'));goal[2]+=d;move_actual(scene,goal,label)
    def tail():
        env=dict(old.__dict__);env.update(_plan_chain=plan_actual,_move_left=move_actual,_execute_control=execute_native_checked)
        fn=types.FunctionType(original_tail.__code__,env)
        # Exact old amplitudes/count/holds, no grasp chooser or pregrasp reconstruction.
        assert old.F3_V_NOMINAL_AMPLITUDE_M_V3_3==.055
        assert old.F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2==50
        reset=_planner_reset(scene,planner_seed=old.PLANNER_SEED,variant_id=proposal['proposal_id']+':sharedV',arm='left')
        prefix=fn(scene,0,baseline,transform,{'contract_sha256':proposal['receipt_sha256']},{},
            {'source':'same fresh qualified micro recipe; original grasp chooser not called','recipe_id':proposal['proposal_id']},reset)
        accepted=prefix['prefix_physical_acceptance']['pass']
        return {**result,'pass':bool(accepted),'fresh_micro_pass':True,'shared_v_executed':True,
            'shared_v_prefix':prefix,'total_queries':scene.planner_query_count,'earliest_failed_stage':None if accepted else 'shared_v_prefix_gate'}
    return after_micro_sequence(result,record_pass,restore,lambda:extend(.015,'f3_prefix_complete_lift4cm'),lambda:extend(.04,'f3_prefix_lift8cm'),tail)

def run(manifest):
    """Original lifecycle cloned with private execute and one bounded-counter edit."""
    source=inspect.getsource(micro.run);tree=ast.parse(source);changes=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Compare) and isinstance(node.left,ast.Constant) and node.left.value==0 and len(node.comparators)==2:
            last=node.comparators[-1]
            if isinstance(last,ast.Constant) and last.value==3:last.value=14;changes+=1
    if changes!=1:raise ValueError('locked lifecycle query bound AST mismatch')
    namespace=dict(micro.__dict__);namespace['execute']=execute
    exec(compile(ast.fix_missing_locations(tree),str(Path(__file__)),'exec'),namespace)
    return namespace['run'](manifest)
