"""Two independent fresh manifests; external reservations, no ledger writes."""
import copy,re
from pathlib import Path
from goal_pilot48_v1.runtime.issue_f2_on_beside import ROOT,W,sha,checked,digest,merge_checked,parent_evidence
from goal_pilot48_v1.runtime_v3.migration import bindings as migrate
CAPS={'solver_problems':4,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0,'gpu_lease_seconds':1980}
PARENT=ROOT/'jobs/p48_f2_on_beside_qualification_001.json'
def fresh(job,relation):
    prefix='p48_f2_on_release_revision1_' if relation=='on' else 'p48_f2_beside_qualification_'
    if not re.fullmatch(prefix+'[a-z0-9_]+',job):raise ValueError('wrong new relation namespace')
    paths=[ROOT/'jobs'/(job+'.json'),W/'Robotwin2/datasets'/job,W/'Robotwin2/datasets'/(job+'_guard'),W/'Robotwin2/datasets'/(job+'_meter'),W/'Robotwin2/cache/p48'/job]
    if any(p.exists() for p in paths):raise FileExistsError('consumed relation namespace')
def build_manifest(job_id,reservation,*,relation):
    if relation not in ('on','beside'):raise ValueError('only on/beside')
    fresh(job_id,relation)
    if reservation.get('kind')!='RESERVE' or reservation.get('job_id')!=job_id or reservation.get('reserved')!=CAPS or not reservation.get('event_sha256'):raise ValueError('exact main reservation required')
    from goal_pilot48_v1.f2_single_relation_qualification_v1.spec import build_spec
    parent_evidence() # original clearance success+all hashes still required
    p=checked(PARENT,'manifest_sha256')
    for table in ('source_files','input_files'):
        for f,h in p[table].items():
            if sha(f)!=h:raise ValueError('consumed parent dependency changed '+f)
    data=W/'Robotwin2/datasets/p48_f2_on_beside_qualification_001';gp=data.with_name(data.name+'_guard')/(data.name+'.terminal.json')
    goal=checked(data/'goal_terminal.json');local=checked(data/'job_terminal.json');guard=checked(gp)
    for r in (goal,guard):
        if r['job_id']!=data.name or r['manifest_sha256']!=p['manifest_sha256']:raise ValueError('parent terminal identity')
    nested=goal['runtime_result'];payload=dict(nested);h=payload.pop('receipt_sha256')
    if digest(payload)!=h or nested['local_terminal_receipt_sha256']!=local['receipt_sha256'] or local['manifest_sha256']!=p['manifest_sha256']:raise ValueError('parent nested local binding')
    if not goal['accounting_complete'] or not guard['task_owned_cleanup_pass'] or not guard['gpu_returned_to_idle_baseline'] or not guard['lease_released']:raise ValueError('parent accounting/cleanup pending')
    if goal['resource_counts']!={'solver_problems':2,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0} or local['scientific_route_pass'] or local['unattempted_relations']!=['beside']:raise ValueError('unexpected parent result')
    failed=checked(data/'on/model_016_plan_1_done.json')
    side=failed['segment_receipts'][0]['planner_query_receipt']['motiongen_result_side_channel'][0]['fields']
    if failed['pass'] or side['status']!='MotionGenStatus.IK_FAIL' or local['branches'][0]['relation']!='on':raise ValueError('not the reviewed release failure')
    spec=build_spec(relation);m=copy.deepcopy(p);m.pop('manifest_sha256');m.update(migrate(p));root=ROOT/'f2_single_relation_qualification_v1'
    sources=[*root.glob('*.py'),*(ROOT/'f2_on_release_revision_v1').glob('*.py'),Path(__file__).resolve()]
    merge_checked(m['source_files'],{str(q):sha(q) for q in sources})
    inputs=[PARENT,data/'goal_terminal.json',data/'job_terminal.json',gp,data/'on/model_016_plan_1_done.json',data/'on/suffix_spec.json']
    if relation=='on':inputs += list((ROOT/'f2_on_release_failure_review_v1').glob('*.json'))+[ROOT/'f2_on_release_failure_review_v1/REPORT.md'];merge_checked(m['source_files'],{str(q):sha(q) for q in (ROOT/'f2_on_release_failure_review_v1').glob('*.py')})
    if relation=='on':
        review=checked(ROOT/'f2_on_release_failure_review_v1/ANALYSIS_001.json')
        merge_checked(m['input_files'],review['source_files'])
    merge_checked(m['input_files'],{str(q):sha(q) for q in inputs})
    m.update(run_id=job_id,parent_job_id=data.name,qualification_relation=relation,single_relation_qualification_spec_sha256=digest(spec),
      failure_class='F2_on_release_fullworld_padding_recipe' if relation=='on' else 'F2_beside_unattempted_qualification',
      evidence_based_revision=1 if relation=='on' else 0,parent_relation_status=spec['parent_relation_status'],
      reserved=dict(CAPS),reservation_event_sha256=reservation['event_sha256'],guard_directory=str(W/'Robotwin2/datasets'/(job_id+'_guard')),
      qualification_relation_order=[relation],high_level_state_check_cap=6 if relation=='on' else 10,high_level_state_check_breakdown={relation:6 if relation=='on' else 10})
    m['jobs']=[{'job_id':job_id,'family':'F2','kind':'F2_SINGLE_RELATION_QUALIFICATION','output_namespace':str(W/'Robotwin2/datasets'/job_id),
      'timeout_seconds':1800,'requires_live_meter':True,'runtime_module':'goal_pilot48_v1.f2_single_relation_qualification_v1.runner_bridge','runtime_file':str(root/'runner_bridge.py'),
      'test_module':'goal_pilot48_v1.f2_single_relation_qualification_v1.test_all','resource_caps':{k:v for k,v in CAPS.items() if k!='gpu_lease_seconds'}}]
    m['manifest_sha256']=digest(m);return m
def build_on_revision_manifest(job_id,reservation):return build_manifest(job_id,reservation,relation='on')
def build_beside_manifest(job_id,reservation):return build_manifest(job_id,reservation,relation='beside')
