"""Generate CPU-only eligibility, realization proposals and pending schemas."""
import argparse,json
from pathlib import Path
from .io import canonical,sha,seal,write_new
from .schemas import build_stage1,build_stage2_pending
from .realizations import build_spec

W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
def read(p):return json.loads(Path(p).read_text())

def build_reuse_candidates():
    report_path=A/'F1_BATCH_GENERATION_PILOT_V1_REPORT.json';report=read(report_path)
    batch=Path(report['scope_receipt_path']).parent
    pools={};f1_roots=[]
    for pilot,root in zip(('A','B'),report['roots'][:2]):
        directory=batch/'root_attempts'/root['root_id']/'root';f1_roots.append(directory)
        for branch in [b for b in report['branches'] if b['root_id']==root['root_id']]:
            path=directory/'branches'/branch['program_id']/'receipt.json'
            if sha(path)!=branch['receipt_file_sha256']:raise ValueError('F1 source receipt changed')
            raw=path.parent/'raw/raw_streams.npz'
            if sha(raw)!=branch['raw_file_sha256']:raise ValueError('F1 source raw changed')
            pools[('F1',pilot,branch['program_id'])]=[{'root_id':root['root_id'],'branch_receipt_path':str(path),'branch_receipt_file_sha256':sha(path),
                 'raw_file_sha256':sha(raw),'acceptance_source':str(report_path),'acceptance_source_sha256':sha(report_path),'reuse_approved':False}]
    publication=read(A/'F4_ROOT1_ACCEPTED_VIA_RESOLUTION_PUBLICATION_V1.json');acceptance_path=Path(publication['acceptance_path'])
    if sha(acceptance_path)!=publication['acceptance_file_sha256']:raise ValueError('F4 acceptance changed')
    accepted=read(acceptance_path);f4root=W/'Robotwin2/datasets/cmf_f4_v22_authorized_root1/development_root'
    for pid in ('F4-ABC','F4-ACB','F4-BAC'):
        p=acceptance_path.parent/'branches'/(pid+'.resolved.json');d=read(p)
        pools[('F4','A',pid)]=[{'root_id':accepted['original_root_identity'],'resolved_branch_path':str(p),'resolved_branch_file_sha256':sha(p),
          'resolution_sha256':d['resolution_sha256'],'acceptance_source':str(acceptance_path),'acceptance_source_sha256':sha(acceptance_path),'reuse_approved':False}]
    return pools,f1_roots[0],f4root

def operation_proposals(directory,family):
    frozen_path=directory/'candidate_frozen_root_spec.json';frozen=read(frozen_path);reference=read(directory/'reference_current_hashes.json');anchor=read(directory/'reference_anchor.json')
    prefix_path=directory/'canonical_prefix_artifact/canonical_prefix_artifact.json';prefix=read(prefix_path)
    root={'root_id':frozen['planned_root_slot_spec']['slot_id'],'family':family,'candidate_universe_sha256':frozen['candidate_universe_sha256'],
      'current_sha256':reference['aggregate_sha256'],'anchor_sha256':anchor['anchor_sha256'],'programs':{p['program_id']:canonical(p) for p in frozen['programs']}}
    specs=[];source_bindings=[]
    for program in frozen['programs']:
        pid=program['program_id'];path=directory/'suffix_artifacts'/pid/'frozen_suffix_artifact.json';suffix=read(path);targets=suffix['execution_spec']['targets']
        ops=[{'kind':'prefix_replay','operation_id':'common_prefix','artifact_directory':str(prefix_path.parent),'artifact_sha256':prefix['artifact_sha256'],'reference_current':reference,'planner_queries':0}]
        if family=='F1':ops.append({'kind':'focus_actor','operation_id':'select_target_actor','actor_role':suffix['execution_spec']['target_role']})
        for t in targets:
            name=t['segment_id']
            if family=='F4' and name.endswith('_neutral_start'):ops.append({'kind':'focus_actor','operation_id':name+'_focus','actor_role':name.split('_')[0]})
            transport=name in ('carry_hub_low','carry_hub_high','safe_horizontal') if family=='F1' else name.endswith('_carry_mid')
            ops.append({'kind':'move','operation_id':name,'arm':'left','target_pose':t['pose'],'noncritical_transport':transport,'boundary_critical':not transport})
            if name=='target_grasp' or (family=='F4' and name.endswith('_grasp')):ops.append({'kind':'gripper','operation_id':name+'_close','arm':'left','command':'close','position':0.})
            if name=='release' or (family=='F4' and name.endswith('_release')):
                ops.append({'kind':'gripper','operation_id':name+'_open','arm':'left','command':'open','position':1.})
                if family=='F1':ops.append({'kind':'hold','operation_id':'release_settle','arm':'left','steps':75})
            if name=='rest' or (family=='F4' and name.endswith('_neutral')):
                ops.append({'kind':'hold','operation_id':name+'_settle','arm':'left','steps':75})
                ops.append({'kind':'verify','operation_id':name+'_verify','role':name.split('_')[0] if family=='F4' else 'selected','program_id':pid})
        for realization in ('r_inv_path','r_inv_motion'):specs.append(build_spec(root,program,ops,realization))
        source_bindings.append({'path':str(path),'file_sha256':sha(path),'frozen_target_count':len(targets)})
    return {'family':family,'specs':specs,'sources':source_bindings+[{'path':str(frozen_path),'file_sha256':sha(frozen_path)},{'path':str(prefix_path),'file_sha256':sha(prefix_path)}]}

def generate(output):
    output=Path(output)
    if output.exists():raise FileExistsError('new CPU proposal namespace required')
    pools,f1,f4=build_reuse_candidates()
    stage1=build_stage1(pools);stage2=build_stage2_pending()
    realizations=seal({'schema_version':'cmf_f1_f4_realization_cpu_proposals_v1','families':[operation_proposals(f1,'F1'),operation_proposals(f4,'F4')],
      'collection_authorized':False,'realization_operation_plan_implemented':True,'concrete_family_scene_anchor_verifier_bindings_pending':True,
      'query_budget_rule':'one real plan_move call per frozen suffix target; prefix replay uses zero planner queries; reused target construction is immutable CPU input',
      'GPU_validation_performed':False,'stage1_authorized':False})
    for name,data in [('STAGE1_48_CELL_ELIGIBILITY.json',stage1),('STAGE2_PENDING_SLOT_SCHEMAS.json',stage2),('F1_F4_REALIZATION_CPU_PROPOSALS.json',realizations)]:write_new(output/name,data)
    return {'stage1_cells':len(stage1['cells']),'potential_reuse_cells':sum(c['candidate_raw_available'] for c in stage1['cells']),
       'stage1_accepted':0,'stage2_primary':len(stage2['primary_slots']),'stage2_reserves':len(stage2['ordered_reserves']),
       'realization_proposal_count':sum(len(f['specs']) for f in realizations['families']),
       'per_realization_planner_caps':{f['family']:sorted({s['budget']['planner_queries'] for s in f['specs']}) for f in realizations['families']},'GPU_used':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(generate(a.output),sort_keys=True))
