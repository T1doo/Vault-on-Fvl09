"""Goal-callable F4-B source Stage-A only; scene creation requires outer Guard.

The original runner runs in a private globals namespace. Both writes that used
to replace receipt.json are redirected to separate exclusive UTF-8 artifacts.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MethodType
import traceback

from ..f4_b_runtime_v1.binding import payload, runtime_spec, validate_runtime, validate_stage_a, seal, SEED, PROPOSAL
from ..f4_b_runtime_v1.stages import bound_function
from ..f4_b_runtime_v1.adapter import make_adapter
from realization_utf8_io_v1 import write_new

PROJECT = Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
SOURCE_SHA = '3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7'
CAPS = dict(solver_problems=156, fresh_scenes=1, action_scenes=0, collection_attempts=0)
ROLES = ('A', 'B', 'C')
SEGMENTS = ('pregrasp', 'grasp', 'lift_mid', 'lift', 'neutral')

def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_inputs():
    """CPU inventory; caller adds Guard/meter/runtime-stack locks to its job."""
    from controlled_multi_future.runtime_source_lock_v1 import _hash_python_tree
    source = _hash_python_tree(PROJECT / 'controlled_multi_future')
    if source != SOURCE_SHA:
        raise ValueError('frozen active controlled source changed')
    parent = Path(__file__).resolve().parent.parent
    paths = [PROPOSAL, parent.parent / 'realization_utf8_io_v1.py']
    paths += sorted((parent/'f4_b_runtime_v1').glob('*.py'))
    paths += sorted(Path(__file__).resolve().parent.glob('*.py'))
    # Imported runtime source is locked as a complete tree, not selected files.
    return dict(implementation_source_sha256=source,
        controlled_source_root=str(PROJECT/'controlled_multi_future'),
        files={str(p):file_sha(p) for p in paths}, payload_sha256=payload()['receipt_sha256'],
        missing_from_this_local_inventory='outer Goal contract must also bind Robot/CuRobo/assets/environment and meter')

def count_problem_rows(rows, api_count):
    if type(api_count) is not int or not isinstance(rows,list) or api_count != len(rows):
        raise ValueError('incomplete API receipts')
    ids=[row.get('query_id') for row in rows]
    if ids != list(range(1,api_count+1)):
        raise ValueError('query receipt gap/duplicate/reset')
    batch = [r for r in rows if r.get('query_type')=='batched_grasp_target_selection']
    single = [r for r in rows if r.get('query_type')!='batched_grasp_target_selection']
    if len(batch)>12 or len(single)>15:
        raise ValueError('source Stage-A exceeded frozen 12 batch /15 chain topology')
    for row in batch:
        if row.get('batch_size') != 10 or len(row.get('ordered_goal_poses',[])) != 10:
            raise ValueError('frozen grasp batch N changed')
    total=10*len(batch)+len(single)
    if total>CAPS['solver_problems']:
        raise ValueError('Goal problem cap exceeded')
    return dict(planner_api_calls=api_count, target_batch_calls=len(batch),
        target_goal_pose_problems=10*len(batch), chain_goal_pose_problems=len(single),
        solver_problems=total, normal_full_path=total==135 and api_count==27)

def independent_meter_counts(output):
    path=Path(output).parent/(Path(output).name+'_meter')/'events.jsonl'
    raw=path.read_bytes()
    if not raw or not raw.endswith(b'\n'):
        raise ValueError('missing/incomplete independent Goal event ledger')
    counts={key:0 for key in CAPS}
    charge_rows=0
    for line in raw.decode('utf-8').splitlines():
        event=json.loads(line)
        if event.get('kind')!='CHARGE':continue
        key=event.get('resource');amount=event.get('amount');total=event.get('total')
        if key not in counts or type(amount) is not int or amount<=0 or type(total) is not int:
            raise ValueError('invalid independent Goal CHARGE row')
        counts[key]+=amount;charge_rows+=1
        if counts[key]!=total or total>CAPS[key]:
            raise ValueError('independent Goal ledger progression/cap mismatch')
    if not charge_rows or counts['fresh_scenes']!=1:
        raise ValueError('Stage-A ledger lacks its one fresh scene')
    return dict(path=str(path),file_sha256=hashlib.sha256(raw).hexdigest(),counts=counts,charge_rows=charge_rows)

class ExclusiveLegacyWriter:
    def __init__(self, directory): self.directory=Path(directory);self.paths=[]
    def __call__(self,path,value,**kwargs):
        expected=self.directory/'receipt.json'
        if Path(path)!=expected:
            raise ValueError('unexpected legacy writer target')
        filename='started.json' if value.get('status')=='running' else 'terminal.json'
        target=self.directory/filename
        write_new(target,value);self.paths.append(str(target))

class TrackedContext:
    def __init__(self,inner,state):self.inner=inner;self.state=state;self.scene=None
    @property
    def cleanup_receipt(self):return self.inner.cleanup_receipt
    def __enter__(self):
        self.state['context_enter_attempts']+=1
        handle=self.inner.__enter__();self.scene=handle.scene;self.state['scene_entered']=True
        if getattr(self.scene.robot,'communication_flag',False):
            error=RuntimeError('unmetered worker planner forbidden')
            self.inner.__exit__(type(error),error,error.__traceback__)
            raise error
        from controlled_multi_future.real_sapien_adapter_v1_2 import _initialize_a0_native_planner_counters
        try:
            self.state['counter_bootstrap']=_initialize_a0_native_planner_counters(self.scene)
        except BaseException as exc:
            self.inner.__exit__(type(exc),exc,exc.__traceback__)
            raise
        return handle
    def __exit__(self,*args):
        capture_error=None
        try:
            if self.scene is not None:
                self.state['query_rows']=deepcopy(getattr(self.scene,'planner_queries',[]))
                self.state['api_count']=getattr(self.scene,'planner_query_count',None)
                self.state['actual_seed']=getattr(self.scene,'_cmf_setup_kwargs',{}).get('seed')
        except BaseException as exc:
            capture_error=exc
        result=self.inner.__exit__(*args)
        if capture_error is not None:raise capture_error
        return result

def make_stage_runner(adapter, directory, state, *, overrides=None):
    from controlled_multi_future.high_level_planner_runner_v1 import HighLevelPlannerRunnerV1
    validate_runtime(adapter.planned_spec)
    original_scene=adapter.scene
    adapter.scene=lambda *a,**kw:TrackedContext(original_scene(*a,**kw),state)
    writer=ExclusiveLegacyWriter(directory)
    changes=dict(validate_f4_runtime_spec_v1=validate_runtime,canonical_write_json=writer)
    changes.update(overrides or {})  # CPU fixtures use local callables, never shared patches.
    runner=HighLevelPlannerRunnerV1(adapter)
    runner.run=MethodType(bound_function(HighLevelPlannerRunnerV1.run,**changes),runner)
    return runner,writer

def qualify(result,state,spec):
    """Derive original source gates from real per-segment outcomes, not labels."""
    counts=count_problem_rows(state['query_rows'],state['api_count'])
    rows=result.get('planner_result',{}).get('segment_receipts',[])
    by_id={r.get('segment_id'):r for r in rows}
    targets=result.get('targets',[])
    expected=[r+'_'+s for r in ROLES for s in SEGMENTS]
    structure=[t.get('segment_id') for t in targets]==expected and len(by_id)==15
    checks={'rendered_visibility':result.get('rendered_visibility',{}).get('pass') is True}
    for role in ROLES:
        checks[role+'_pregrasp_grasp_lift_planner']=structure and all(
            by_id.get(role+'_'+s,{}).get('planner_status')=='Success' for s in SEGMENTS[:4])
    neutrals=[t['pose'] for t in targets if t.get('segment_id','').endswith('_neutral')]
    checks['all_roles_return_one_neutral']=structure and len(neutrals)==3 and neutrals[0]==neutrals[1]==neutrals[2] and all(
        by_id.get(role+'_neutral',{}).get('planner_status')=='Success' for role in ROLES)
    scene_id=(result.get('cleanup') or {}).get('scene_instance_id')
    passed=(result.get('pass') is True and all(checks.values()) and counts['normal_full_path']
        and state['actual_seed']==SEED and bool(scene_id))
    b=payload()
    evidence=seal(dict(schema_version='cmf_f4_b_source_stage_a_evidence_v1',
        status='B_SOURCE_STAGE_A_PASS' if passed else 'B_SOURCE_STAGE_A_FAILED_WITH_EVIDENCE',
        source_candidate_sha256=b['source']['candidate_sha256'],payload_sha256=b['receipt_sha256'],
        scene_seed=state['actual_seed'],scene_instance_id=scene_id,physical_execution_count=0,
        planner_query_count=state['api_count'],goal_problem_accounting=counts,
        planned_scope_spec_sha256=spec['planned_scope_spec_sha256'],
        source_terminal_receipt_sha256=result.get('receipt_sha256'),checks=checks,**{'pass':passed}))
    if passed:
        validate_stage_a(evidence)
        # Exercise the actual downstream validator/builder before publishing a
        # success receipt, not just a field-name compatibility approximation.
        runtime_spec('f4_stage_b_planner',stage_a=evidence)
    return evidence

def run(manifest):
    job=manifest['jobs'][0]
    if job.get('resource_caps')!=CAPS:
        raise ValueError('F4-B Stage-A requires exact 156/1/0/0 caps')
    inputs=source_inputs();spec=runtime_spec()
    if job.get('b_payload_sha256')!=inputs['payload_sha256'] or job.get('planned_scene_spec_sha256')!=spec['planned_scope_spec_sha256']:
        raise ValueError('job is not bound to the one exact B source scene')
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    write_new(out/'source_inputs.json',inputs);write_new(out/'planned_spec.json',spec)
    state=dict(context_enter_attempts=0,scene_entered=False,query_rows=[],api_count=None,actual_seed=None)
    result=evidence=error=None
    try:
        adapter=make_adapter(output_root=out/'scene_work',source_sha256=SOURCE_SHA,planned_spec=spec)
        runner,writer=make_stage_runner(adapter,out/'stage_a',state)
        result=runner.run(output_dir=out/'stage_a',planned_spec=spec)
        evidence=qualify(result,state,spec)
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    write_new(out/'query_rows.json',state)
    cleanup=(result or {}).get('cleanup')
    cleanup_pass=isinstance(cleanup,dict) and cleanup.get('cleanup_safety_pass') is True and cleanup.get('orphan_process_count')==0
    try:counts=count_problem_rows(state['query_rows'],state['api_count']);known=True
    except (ValueError,TypeError):counts=None;known=False
    meter_receipt=meter_error=None
    try:
        meter_receipt=independent_meter_counts(out)
        expected=dict(solver_problems=None if counts is None else counts['solver_problems'],
            fresh_scenes=state['context_enter_attempts'],action_scenes=0,collection_attempts=0)
        if meter_receipt['counts']!=expected:raise ValueError('native receipt N disagrees with independent Goal meter')
        meter_receipt['pass']=True
    except BaseException as exc:
        known=False;meter_error=dict(type=type(exc).__name__,message=str(exc))
    if evidence is not None and evidence['pass'] and not known:
        evidence['pass']=False;evidence['status']='B_SOURCE_STAGE_A_INFRASTRUCTURE_ACCOUNTING_STOP';evidence=seal(evidence)
    if evidence is not None:write_new(out/'source_stage_a_evidence.json',evidence)
    # A normal finite planner failure can leave complete evidence; an arbitrary
    # runner error is infrastructure, never silently relabelled as science.
    internal=(result or {}).get('error')
    scientific_error=internal and (internal.get('type')=='PlannerCandidateNoValidGrasp' or
        (internal.get('type')=='RuntimeError' and internal.get('message')=='F4 Stage-A rendered visibility failed'))
    infrastructure_ok=error is None and (not internal or scientific_error)
    known=known and state['scene_entered'] and state['actual_seed']==SEED
    terminal=seal(dict(schema_version='cmf_goal_f4_b_source_stage_a_terminal_v2',
        scene_attempts=state['context_enter_attempts'],accounting_complete=bool(known),
        pass_=False,scientific_route_pass=evidence is not None and evidence['pass'],
        qualification_pass=evidence is not None and evidence['pass'],
        local_solver_accounting=counts,independent_meter=meter_receipt,meter_error=meter_error,
        result=result,evidence=evidence,error=error,cleanup=cleanup,
        physical_execution_count=0,collection_attempts=0,
        next_gate='THREE_EXACT_B_PROGRAM_PLANNER_TERMINALS' if evidence is not None and evidence['pass'] else 'REVIEW_B_SOURCE_FAILURE_NO_DOWNSTREAM_EXECUTION'))
    terminal.pop('pass_',None);terminal['pass']=bool(infrastructure_ok and cleanup_pass and known)
    terminal=seal(terminal);write_new(out/'runtime_terminal.json',terminal)
    return terminal
