"""Three original full-program templates; exact real B isolation prerequisite."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import traceback
from ..f4_b_isolation_runtime_v1 import runtime as isolation
from ..f4_b_program_runtime_v1.runtime import bound_json
from ..f4_b_runtime_v1.binding import checked,seal,payload,PROGRAMS
from ..f4_b_runtime_v1.stages import physical_spec,root_prerequisites
from realization_utf8_io_v1 import write_new

CAPS=dict(solver_problems=480,fresh_scenes=3,action_scenes=3,collection_attempts=0)
BASE_SHA='cc9a4f29feff325dcf05b453022e5a11f2777796b58d1e1f519abf51fe280347'

def prerequisites(job):
    evidence=bound_json(job,'source_isolation_evidence')
    goal=bound_json(job,'source_isolation_goal_terminal')
    guard=bound_json(job,'source_isolation_guard_terminal')
    manifest=bound_json(job,'source_isolation_manifest','manifest_sha256')
    parent=goal.get('runtime_result') or {}
    if (goal.get('pass') is not True or goal.get('accounting_complete') is not True or
        goal.get('resource_counts')!=dict(solver_problems=720,fresh_scenes=5,action_scenes=5,collection_attempts=0) or
        parent.get('isolation_pass') is not True or parent.get('evidence')!=evidence or
        parent.get('independent_meter',{}).get('pass') is not True or
        guard.get('child_exit_code')!=0 or guard.get('task_owned_cleanup_pass') is not True or
        goal.get('manifest_sha256')!=manifest['manifest_sha256'] or guard.get('manifest_sha256')!=manifest['manifest_sha256'] or
        manifest['jobs'][0].get('runtime_module')!='goal_pilot48_v1.f4_b_isolation_runtime_v1.runtime' or
        evidence.get('status')!='B_ALL_FIVE_ISOLATION_PASS' or len(evidence.get('rows',[]))!=5 or
        [r.get('stage') for r in evidence['rows']]!=list(isolation.STAGES) or
        not all(r.get('physical_pass') is True for r in evidence['rows'])):
        raise ValueError('five real passing B isolation scenes with clean Guard required')
    stage_a,scene,current,sources=isolation.prerequisites(manifest['jobs'][0])
    if job.get('b_scene_spec_sha256')!=scene['planned_scope_spec_sha256'] or job.get('b_payload_sha256')!=payload()['receipt_sha256']:
        raise ValueError('template B source changed')
    for index,row in enumerate(parent.get('rows',[])):
        if row.get('receipt_sha256')!=evidence['rows'][index]['scene_receipt_sha256'] or row.get('physical_pass') is not True:
            raise ValueError('isolation stage evidence link differs')
    if len(parent.get('rows',[]))!=5:raise ValueError('isolation original stage records missing')
    return stage_a,scene,current,sources,evidence

class TemplateEpochRecorder(isolation.EpochRecorder):
    def accounting(self,program_id):
        rows=[r for e in self.epochs for r in e['query_rows']]
        batches=[r for r in rows if r.get('query_type')=='batched_grasp_target_selection']
        singles=[r for r in rows if r.get('query_type')!='batched_grasp_target_selection']
        if len(batches)>12 or len(singles)>40 or any(r.get('batch_size')!=10 or len(r.get('ordered_goal_poses',[]))!=10 for r in batches):
            raise ValueError('template target/chain topology changed')
        return dict(planner_api_calls=len(rows),target_batch_calls=len(batches),target_goal_problems=10*len(batches),
            single_goal_problems=len(singles),solver_problems=10*len(batches)+len(singles),expected_complete_solver_problems=160)

def bound_executor(source,stage_a,isolation_evidence):
    """Reuse frozen bootstrap/cleanup exactly with explicit AST-scoped changes.

    Replaces only executor import, result gate key, and phase label. Physical
    targets, gates, call order and the imported original function remain intact.
    """
    path=Path(isolation.__file__)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=BASE_SHA:raise ValueError('frozen isolation lifecycle source changed')
    tree=ast.parse(path.read_text(encoding='utf-8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_one')
    class Adapt(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            if node.module=='controlled_multi_future.f4_bounded_physical_micro_v1':
                return ast.copy_location(ast.ImportFrom(module='controlled_multi_future.f4_full_program_physical_v1',
                    names=[ast.alias(name='run_f4_full_program_physical_v1',asname='run_f4_bounded_physical_micro_v1')],level=0),node)
            return node
        def visit_Constant(self,node):
            values={'stage_physically_qualified':'full_program_physically_qualified','F4_B_ISOLATION_':'F4_B_TEMPLATE_'}
            if isinstance(node.value,str) and node.value in values:return ast.copy_location(ast.Constant(values[node.value]),node)
            return node
    def full_spec(terminal,**kwargs):
        return physical_spec(terminal,stage_a=stage_a,program_id=source['spec']['program_id'],slot_id=source['spec']['slot_id'],
            planner_reset_nonce=source['spec']['planner_reset_nonce'],isolation_receipt_sha256=isolation_evidence['receipt_sha256'])
    module=ast.fix_missing_locations(ast.Module(body=[Adapt().visit(fn)],type_ignores=[]))
    namespace=dict(vars(isolation));namespace.update(EpochRecorder=TemplateEpochRecorder,
        PROGRAM={p:p for p in PROGRAMS},physical_spec=full_spec)
    exec(compile(module,str(path)+'#template-private-clone','exec'),namespace)
    return namespace['run_one']

def reconcile(output,rows):
    # Reuse independent ledger semantics with a private cap binding; no mutation.
    from ..f4_b_runtime_v1.stages import bound_function
    return bound_function(isolation.reconcile,CAPS=CAPS)(output,rows)

def equivalence(rows):
    from controlled_multi_future.root_orchestrator_v1_1 import compare_three_branch_final_state_payloads
    if len(rows)!=3 or [r.get('program_id') for r in rows]!=list(PROGRAMS) or not all(r.get('physical_pass') is True for r in rows):
        return dict(same_current_pass=False,same_anchor_pass=False,final_state_equivalence={'equivalent':False,'reason':'all_three_programs_required'})
    currents=[r.get('current',{}).get('aggregate_sha256') for r in rows]
    anchors=[r.get('anchor',{}).get('anchor_sha256') for r in rows]
    finals=[dict(program_id=r['program_id'],final_state_equivalence_payload=(r.get('result') or {}).get('physical_result',{}).get('final_state_equivalence_payload')) for r in rows]
    required={'common_x_pose','A_pose','B_pose','C_pose','executing_eef_pose','executing_gripper_open','execution_arm'}
    if any(not isinstance(r['final_state_equivalence_payload'],dict) or set(r['final_state_equivalence_payload'])!=required for r in finals):
        return dict(same_current_pass=False,same_anchor_pass=False,final_state_equivalence={'equivalent':False,'reason':'complete_original_F4_final_state_required'})
    return dict(same_current_pass=bool(currents[0]) and len(set(currents))==1,
        same_anchor_pass=bool(anchors[0]) and len(set(anchors))==1,
        final_state_equivalence=compare_three_branch_final_state_payloads(finals))

def run(manifest):
    job=manifest['jobs'][0]
    if job.get('resource_caps')!=CAPS:raise ValueError('template caps must be480/3/3/0')
    stage_a,scene,current,sources,prior=prerequisites(job)
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    rows=[];error=None
    try:
        for index,pid in enumerate(PROGRAMS,1):
            fn=bound_executor(sources[pid],stage_a,prior)
            row=fn(pid,sources[pid],stage_a,scene,current,out/f'{index:02d}_{pid}')
            rows.append(row);cleanup=row.get('cleanup') or {}
            if not row['physical_pass'] or not cleanup.get('cleanup_safety_pass') or cleanup.get('orphan_process_count')!=0:break
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    meter=meter_error=None
    try:meter=reconcile(out,rows)
    except BaseException as exc:meter_error=dict(type=type(exc).__name__,message=str(exc))
    try:comparisons=equivalence(rows)
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
        comparisons=dict(same_current_pass=False,same_anchor_pass=False,final_state_equivalence={'equivalent':False,'reason':'final_state_validation_error'})
    clean=bool(rows) and all((r.get('cleanup') or {}).get('cleanup_safety_pass') is True and (r.get('cleanup') or {}).get('orphan_process_count')==0 for r in rows)
    infrastructure=error is None and all(r.get('error') is None and r.get('trace_save_error') is None for r in rows)
    science=len(rows)==3 and all(r['physical_pass'] for r in rows) and clean and infrastructure and meter is not None and comparisons['same_current_pass'] and comparisons['same_anchor_pass'] and comparisons['final_state_equivalence']['equivalent']
    evidence=seal(dict(status='B_FULL_PROGRAM_TEMPLATE_PASS' if science else 'B_FULL_PROGRAM_TEMPLATE_FAILED_WITH_EVIDENCE',
        b_scene_spec_sha256=scene['planned_scope_spec_sha256'],b_payload_sha256=payload()['receipt_sha256'],
        isolation_receipt_sha256=prior['receipt_sha256'],rows=[dict(program_id=r['program_id'],physical_pass=r['physical_pass'],scene_receipt_sha256=r['receipt_sha256']) for r in rows],
        **comparisons,**{'pass':science}))
    if science:
        try:root_prerequisites(stage_a=stage_a,planner_envelopes=sources,isolation=prior,template=evidence)
        except BaseException as exc:
            error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc());science=False;infrastructure=False
            evidence['status']='B_TEMPLATE_DOWNSTREAM_BINDING_ERROR';evidence['pass']=False;evidence=seal(evidence)
    write_new(out/'template_evidence.json',evidence)
    terminal=seal(dict(rows=rows,evidence=evidence,error=error,independent_meter=meter,meter_error=meter_error,
        scene_attempts=sum(r['scene_attempts'] for r in rows),accounting_complete=meter is not None,
        scientific_route_pass=science,template_pass=science,skipped_programs=list(PROGRAMS[len(rows):]),
        next_gate='ONE_B_STRICT_PREFIX_ROOT' if science else 'REVIEW_FAILED_TEMPLATE',**{'pass':infrastructure and clean and meter is not None}))
    write_new(out/'runtime_terminal.json',terminal);return terminal
