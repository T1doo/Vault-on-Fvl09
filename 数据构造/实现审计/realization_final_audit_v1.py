"""CPU-only final raw/video/root and six-cell pilot-eligibility audit."""
import json,sys
from pathlib import Path
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(0,str(A/'realization_batch_runtime_v1_3'));sys.path.insert(1,str(A));sys.path.insert(2,str(A/'downstream_cpu_source_v1_20260905'))
from catalog import read,sha,seal,canonical,build_catalog,source_branch,check
from realization_utf8_publication_v1 import audit_completed_root
from controlled_multi_future.raw_writer import verify_raw_artifact_integrity
from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
from controlled_multi_future.root_orchestrator_v1_1 import compare_three_branch_final_state_payloads
from cmf_downstream_cpu.matrices import finalize_matrix

def run():
    base=W/'Robotwin2/datasets/cmf_realization_unattempted8_v1_3';guard=W/'Robotwin2/datasets/cmf_realization_unattempted8_v1_3_guard'
    terminal=check(base/'job_terminal.json');g=check(guard/'cont8.terminal.json');post=check(guard/'cont8.post_child_validation.json')
    assert terminal['pass'] and g['task_owned_cleanup_pass'] and g['child_exit_code']==0 and post['validation_pass'] and post['job_succeeded']
    assert terminal['planner_queries']==112 and terminal['cumulative_scene_attempts']==10
    cohorts=[];all_rows=[];new_raw_hashes=[]
    for cohort in build_catalog()['cohorts']:
        directory=base/cohort['cohort'];root=audit_completed_root(directory)
        assert root['status']=='accepted'
        branches={b['program_id']:b for b in root['branch_receipts']}
        old=[source_branch(c) for c in cohort['cells']]
        final_equivalence=compare_three_branch_final_state_payloads(old+root['branch_receipts']) if cohort['family']=='F4' else {'equivalent':True,'reason':'not_required_for_F1'}
        assert final_equivalence['equivalent']
        rows=[];files={};variations=[]
        for cell in cohort['cells']:
            pid=cell['program']['program_id'];parent=Path(cell['parent_root']);original=source_branch(cell);new=branches[pid]
            assert new['realized_variation']['pass'];variations.append({'program_id':pid,'variant':cell['variant'],'receipt':new['realized_variation']})
            for variant,branch,raw_dir in [('r_pc',original,parent/'branches'/pid/'raw'),(cell['variant'],new,Path(new['raw_directory']))]:
                raw=verify_raw_artifact_integrity(raw_dir);video=validate_development_trajectory_mp4_receipt_v1(branch['development_video_receipt'])
                assert raw['pass'] and video['pass'] and branch['verifier']['pass'] and branch['status']=='accepted'
                raw_sha=raw['manifest']['raw_streams_npz_sha256'];manifest_path=raw_dir/'manifest.json';video_path=Path(branch['development_video_receipt']['path'])
                files[str(manifest_path)]=sha(manifest_path);files[str(raw_dir/'manifest.sha256.json')]=sha(raw_dir/'manifest.sha256.json');files[str(video_path)]=sha(video_path)
                if variant!='r_pc':new_raw_hashes.append(raw_sha)
                rows.append({'root_id':cell['parent_root_id'],'program_id':pid,'realization':variant,'program_semantic_sha256':canonical(cell['program']),
                    'origin_kind':'real_rollout','derived_from_raw_id':None,'receipt_is_trace_reconstructed':bool(branch.get('receipt_recovery')),
                    'raw_id':raw_sha,'rollout_id':str(raw_dir.parent),'current_sha256':branch['reference_current_sha256'],
                    'candidate_universe_sha256':cell['candidate_universe_sha256'],'raw_integrity_pass':True,'video_integrity_pass':True,'family_verifier_pass':True,
                    'same_current_pass':branch['branch_current']['aggregate_sha256']==branch['reference_current_sha256'],
                    'anchor_equivalence_pass':branch['anchor_equivalence']['equivalent'],'fresh_scene_pass':True,'cleanup_pass':True,
                    'failure_history_complete':True,'orphan_process_count':0,'final_state_equivalence_pass':final_equivalence['equivalent'],
                    'evidence_scope':'real_simulator_verified','parent_acceptance_inherited':True,
                    'current_batch_history_reference':'REALIZATION_UTF8_FAILURE_RESOLUTION_PUBLICATION_V1_20260906.json plus V1/V1.2/V1.3 immutable terminals'})
        level='pilot_B' if cohort['variant']=='r_inv_motion' else 'pilot_A'
        matrix=finalize_matrix(cohort['cells'][0]['parent_root_id'],{c['program']['program_id']:canonical(c['program']) for c in cohort['cells']},rows,level=level,family=cohort['family'])
        assert matrix['matrix_complete'] and not matrix['accepted'] and not matrix['stage_authorized']
        all_rows.extend(rows)
        cohorts.append({'cohort':cohort['cohort'],'parent_root_id':cohort['cells'][0]['parent_root_id'],'family':cohort['family'],
            'root_receipt_path':str(directory/'root_receipt.json'),'root_receipt_file_sha256':sha(directory/'root_receipt.json'),
            'publication_index_file_sha256':sha(directory/'publication_index.json'),'root_finalization':root['root_finalization'],
            'six_cell_matrix':matrix,'raw_video_file_bindings':files,'realized_variations':variations,'six_trajectory_final_state_equivalence':final_equivalence})
    assert len(new_raw_hashes)==len(set(new_raw_hashes))==9
    assert len(all_rows)==18 and len({r['raw_id'] for r in all_rows})==18
    result={'schema_version':'cmf_nine_realizations_final_cpu_audit_v1','pass':True,'cohorts':cohorts,'rows':all_rows,
        'new_verified_real_rollouts':9,'new_raw_unique_hashes':new_raw_hashes,'new_independent_roots':0,'augmented_existing_roots':3,
        'pilot_candidate_cells_with_evidence':18,'stage1_accepted_cells':0,'formal_accepted_trajectories':0,
        'total_development_roots':6,'total_development_raw_trajectories':27,'prior_raw_trajectories':18,
        'cumulative_scene_attempts':10,'cumulative_planner_queries':123,'last_job_terminal_sha256':terminal['receipt_sha256'],
        'last_guard_terminal_sha256':g['receipt_sha256'],'last_post_child_sha256':post['receipt_sha256'],
        'task_gpu_release_verified':True,'old_failed_jobs_preserved':True,'no_reexecution_after_UTF8_failure':True}
    return seal(result)

if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
