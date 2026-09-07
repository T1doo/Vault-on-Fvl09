"""Late-release-aware acceptance with unchanged original failed Guard evidence."""
import ast
import inspect
from pathlib import Path
from goal_pilot48_v1.f4_b_pilot_acceptance_v1 import audit as original
from goal_pilot48_v1.f4_b_acceptance_audit_v1 import current_recovery as recovery_v1
from goal_pilot48_v1.f4_b_acceptance_audit_v2.audit import run as current_audit_v2
from goal_pilot48_v1.f4_b_late_release_review_v1.review import selected,same_original_baseline
from goal_pilot48_v1.f4_b_runtime_v1.binding import checked,seal
from goal_pilot48_v1.runtime_v3.budget import rows as budget_rows
from goal_pilot48_v1.runtime.issue_f4_b_stage_a import ROOT

LATE_DIR=ROOT/'f4_b_late_release_review_v1'
ACCEPTANCE_SHA='307635844aa6bd9c993b354fabc77d7281cc6e3a400ccec81071ecbec0748a91'
RESOLUTION_SHA='3e782f876ac10b3174c396ef2b46e5eeadd1f644d7b339ece3af4763fd44a89e'

def late_binding(output,*,resolution_path,observation_path,review_path,budget_event_sha256,resource_acceptance_path):
    output=Path(output).resolve()
    resolution=checked(original.read(resolution_path));observation=checked(original.read(observation_path));review=checked(original.read(review_path))
    acceptance=checked(original.read(resource_acceptance_path))
    if (acceptance['receipt_sha256']!=ACCEPTANCE_SHA or resolution['receipt_sha256']!=RESOLUTION_SHA or
        acceptance.get('resource_release_resolved') is not True or acceptance.get('original_guard_cleanup_pass') is not False or
        acceptance.get('original_guard_modified') is not False or acceptance.get('pilot_acceptance_issued') is not False or
        acceptance.get('late_release_resolution_receipt_sha256')!=resolution['receipt_sha256'] or
        acceptance.get('budget_reconciliation_event_sha256')!=budget_event_sha256 or
        acceptance.get('actual_resources')!=resolution['actual_resources_for_main_reconcile']):
        raise ValueError('exact main resource-release acceptance/budget binding required')
    guard_path=output.parent/(output.name+'_guard')/(output.name+'.terminal.json');guard=checked(original.read(guard_path))
    if (resolution.get('job_id')!=output.name or resolution.get('pending_review_receipt_sha256')!=review['receipt_sha256'] or
        resolution.get('original_guard_receipt_sha256')!=guard['receipt_sha256'] or resolution.get('late_observation_receipt_sha256')!=observation['receipt_sha256'] or
        resolution.get('late_baseline_restoration_verified') is not True or resolution.get('resource_release_resolved') is not True or
        resolution.get('original_guard_cleanup_pass_remains_false') is not True or resolution.get('original_POST_CHILD_pass_remains_false') is not True):
        raise ValueError('exact real late-release evidence chain required')
    if guard.get('task_owned_cleanup_pass') is not False or guard.get('gpu_returned_to_idle_baseline') is not False or guard.get('child_exit_code')!=0 or guard.get('lease_released') is not True or guard.get('cache_removed') is not True or guard.get('cleanup_errors')!=[{'type':'CooldownExhausted','message':'GPU baseline not restored'}]:
        raise ValueError('original Guard failure facts changed or another failure exists')
    for path,h in review['immutable_file_hashes'].items():
        if original.sha(path)!=h:raise ValueError('source/raw/original terminal changed after review')
    if observation.get('original_guard_file_sha256')!=original.sha(guard_path) or observation.get('requested_owned_pids')!=[guard['guard_pid'],guard['child_pid']] or observation.get('requested_child_pgid')!=guard['child_process_group'] or observation.get('current_uid')!=review['task_user_uid'] or observation.get('own_pid_and_group_absent') is not True or observation.get('remaining_owned_process_rows')!=[] or observation.get('foreign_processes_signalled') is not False:
        raise ValueError('late ownership observation incomplete')
    gpu=selected(observation['snapshot'],guard['physical_gpu_index'],guard['gpu_uuid'])
    if not same_original_baseline(review['original_pre_selected'],gpu) or gpu!=resolution['late_selected_gpu'] or resolution['late_capture_at']!=observation['snapshot']['captured_at']:
        raise ValueError('late snapshot does not meet unchanged strict baseline')
    events=[r for r in budget_rows() if r['event_sha256']==budget_event_sha256]
    if len(events)!=1 or events[0]['kind']!='RECONCILE' or events[0]['job_id']!=output.name or events[0]['actual']!=resolution['actual_resources_for_main_reconcile']:
        raise ValueError('main budget reconciliation required before candidate acceptance')
    e=events[0]['evidence'];bound=e.get('late_release_resolution_receipt_sha256',e.get('resolution_receipt_sha256'))
    if bound!=resolution['receipt_sha256']:raise ValueError('budget event does not reference this late release')
    return dict(original_guard=guard,original_guard_path=str(guard_path),late_release_resolution=resolution,main_resource_acceptance=acceptance,
        late_observation=observation,budget_event_sha256=budget_event_sha256,
        input_hashes={str(p):original.sha(p) for p in (resolution_path,observation_path,review_path,guard_path,resource_acceptance_path)},late_release_verified=True)

def private_guard_predicate(function,*,kind,late_verified,overrides=None):
    """Replace only the refusal predicate, never copy a Guard with flags true."""
    tree=ast.parse(inspect.getsource(function));replaced=[]
    class Rewrite(ast.NodeTransformer):
        def visit_UnaryOp(self,node):
            text=ast.unparse(node)
            target=(kind=='terminal' and isinstance(node.op,ast.Not) and text.startswith('not all(') and 'task_owned_cleanup_pass' in text)
            target=target or (kind=='recovery' and isinstance(node.op,ast.Not) and text=="not guard.get('task_owned_cleanup_pass')")
            if target:
                replaced.append(text);return ast.copy_location(ast.UnaryOp(op=ast.Not(),operand=ast.Name(id='_late_verified',ctx=ast.Load())),node)
            return self.generic_visit(node)
    tree=ast.fix_missing_locations(Rewrite().visit(tree))
    if len(replaced)!=1:raise ValueError('expected exactly one original Guard refusal predicate')
    namespace=dict(function.__globals__);namespace.update(_late_verified=late_verified);namespace.update(overrides or {})
    exec(compile(tree,inspect.getsourcefile(function)+'#late-release-aware','exec'),namespace)
    return namespace[function.__name__]

def build_candidates(output=original.DEFAULT,*,resolution_path=LATE_DIR/'LATE_RELEASE_RESOLUTION_001.json',
    observation_path=LATE_DIR/'MAIN_HOST_OBSERVATION_004.json',review_path=LATE_DIR/'PENDING_REVIEW_001.json',
    budget_event_sha256='095dcf658a41b151a5bb9a07f3c8675a5571e64ba4ffcd8ca17e50af21f7852f',
    resource_acceptance_path=LATE_DIR/'RESOURCE_RELEASE_ACCEPTANCE_001.json'):
    # No historical data/acceptance is inferred while the late proof is absent.
    for path in (resolution_path,observation_path,review_path,resource_acceptance_path):
        if not Path(path).exists():return seal(dict(status='pending_actual_late_release',eligible_candidate_cells=0,acceptance_issued=False,pilot_cells_modified=False))
    binding=late_binding(output,resolution_path=resolution_path,observation_path=observation_path,review_path=review_path,budget_event_sha256=budget_event_sha256,resource_acceptance_path=resource_acceptance_path)
    terminal_fn=private_guard_predicate(original.terminal_inputs,kind='terminal',late_verified=True)
    recovery_fn=private_guard_predicate(recovery_v1.audit_later_current,kind='recovery',late_verified=True,overrides={'run':current_audit_v2})
    def terminals(path):
        if Path(path).resolve()!=Path(output).resolve():raise ValueError('late release belongs to a different job')
        result,pending=terminal_fn(path)
        if result is not None:
            if result['guard']!=binding['original_guard']:raise ValueError('original Guard was changed by adapter')
            result['late_release_binding']=binding
        return result,pending
    def recovery(**kwargs):
        if Path(kwargs['producer_guard']).resolve()!=Path(binding['original_guard_path']).resolve():raise ValueError('current producer Guard differs')
        return recovery_fn(**kwargs)
    from goal_pilot48_v1.f4_b_runtime_v1.stages import bound_function
    report=bound_function(original.build_candidates,terminal_inputs=terminals,audit_later_current=recovery)(output)
    report.pop('receipt_sha256',None)
    report.update(schema_version='cmf_B_pilot_six_candidate_audit_v2_late_release',late_release_binding=binding,
        original_guard_cleanup_pass=False,late_release_verified=True,original_guard_modified=False)
    return seal(report)
