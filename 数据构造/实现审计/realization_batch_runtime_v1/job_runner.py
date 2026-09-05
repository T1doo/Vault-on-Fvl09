"""Finite serial nine-cell development batch; no retries or Stage1 promotion."""
import argparse,copy,json,sys,time
from pathlib import Path
from catalog import W,A,read,seal,sha
from pipeline import collect_cell,write_new

def finalize_cohort(cohort,directory,branches):
    sys.path.insert(0,str(A/'downstream_cpu_source_v1_20260905'))
    from cmf_downstream_cpu.collector_publication import publish_final_branch,register_completed_root
    from controlled_multi_future.root_orchestrator_v1_1 import finalize_three_branch_root_v1_1
    # Read actual provisional files, not a separately reconstructed success view.
    disk=[read(directory/'branches'/b['program_id']/'receipt.provisional.json') for b in branches]
    final=copy.deepcopy(disk)
    cleanup=[b.get('cleanup') or {} for b in final]
    cleanup_ok=bool(cleanup) and all(c.get('cleanup_safety_pass') is True and c.get('orphan_process_count')==0 for c in cleanup)
    current=final[0]['reference_current_sha256'] if final else ''
    check=finalize_three_branch_root_v1_1(final,reference_current_sha256=current,root_cleanup_pass=cleanup_ok)
    for branch in final:publish_final_branch(directory,branch)
    root={'schema_version':'cmf_development_existing_root_realization_cohort_v1','status':'accepted' if check['accepted'] else 'incomplete',
        'parent_root_id':cohort['cells'][0]['parent_root_id'],'cohort':cohort['cohort'],'variant':cohort['variant'],
        'planned_root_slot_spec_sha256':sha(Path(cohort['cells'][0]['parent_root'])/'planned_root_slot_spec.json'),
        'branch_receipts':final,'cleanup_records':cleanup,'root_finalization':check,
        'new_independent_root_count':0,'stage1_authorized':False,'formal_data':False}
    write_new(directory/'root_receipt.json',root)
    if check['accepted']:register_completed_root(directory)
    return {'cohort':cohort['cohort'],'status':root['status'],'root_receipt_path':str(directory/'root_receipt.json'),
        'root_receipt_file_sha256':sha(directory/'root_receipt.json'),'new_independent_root_count':0}

def run_batch(manifest,*,collector=collect_cell):
    catalog=read(manifest['catalog_path']);job=manifest['jobs'][0];output=Path(job['output_namespace'])
    output.mkdir(parents=True,exist_ok=False);branches=[];cohorts=[];error=None;global_stop=False;started=time.monotonic()
    try:
        for cohort in catalog['cohorts']:
            directory=output/cohort['cohort'];own=[]
            for cell in cohort['cells']:
                # Exclusive durable start also prevents accidental cell reissue.
                write_new(directory/'attempts'/(cell['cell_id']+'.start.json'),seal({'cell':cell,'attempt_number':1,'manifest_sha256':manifest['manifest_sha256']}))
                branch=collector(cell,directory/'branches'/cell['program']['program_id'],shared_current_dir=directory/'current')
                branches.append(branch);own.append(branch)
                write_new(directory/'attempts'/(cell['cell_id']+'.terminal.json'),seal({'cell_id':cell['cell_id'],'branch_status':branch['status'],
                    'planner_query_delta':branch['planner_query_delta'],'accounting_complete':branch['accounting_complete'],'global_stop':branch['global_stop']}))
                print(json.dumps({'cell_id':cell['cell_id'],'status':branch['status'],'queries':branch['planner_query_delta']},ensure_ascii=False),flush=True)
                if branch['global_stop']:global_stop=True;break
            cohorts.append(finalize_cohort(cohort,directory,own))
            if global_stop:break
    except BaseException as exc:
        error={'type':type(exc).__name__,'message':str(exc)};global_stop=True
    starts=list(output.glob('*/attempts/*.start.json'))
    known=len(starts)==len(branches) and all(b['accounting_complete'] for b in branches)
    count=sum(b['planner_query_delta'] for b in branches) if known else None
    passed=not global_stop and error is None and len(branches)==9 and len(cohorts)==3 and all(c['status']=='accepted' for c in cohorts)
    terminal=seal({'schema_version':'cmf_realization_batch_terminal_v1','manifest_sha256':manifest['manifest_sha256'],'pass':passed,
        'error':error,'global_stop':global_stop,'accounting_complete':known,'planner_queries':count,'fresh_scene_attempts':len(starts),
        'completed_cell_receipts':len(branches),'raw_trajectory_count':sum(b.get('raw_written') is True for b in branches),
        'accepted_variant_trajectory_count':sum(b['status']=='accepted' for b in branches),
        'new_independent_root_count':0,'stage1_accepted_trajectory_count':0,'formal_trajectory_count':0,
        'cells':[{'cell_id':b['cell_id'],'status':b['status'],'planner_query_delta':b['planner_query_delta'],'accounting_complete':b['accounting_complete'],'global_stop':b['global_stop']} for b in branches],
        'cohorts':cohorts,'elapsed_seconds':time.monotonic()-started})
    write_new(output/'job_terminal.json',terminal)
    return terminal

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--job-id');p.add_argument('--preflight-only',action='store_true');args=p.parse_args(argv)
    from manifest_contract import load_manifest
    m=load_manifest(args.manifest,runner=not args.preflight_only)
    if args.job_id is not None and args.job_id!=m['jobs'][0]['job_id']:raise ValueError('job identity')
    if args.preflight_only:
        import unittest
        from test_cpu import RealArtifactTests
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RealArtifactTests))
        return 0 if result.wasSuccessful() else 1
    return 0 if run_batch(m)['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
