"""Three real B motion realizations, zero new planner calls; no pilot ledger writes."""
from copy import deepcopy
from pathlib import Path
import traceback
from ..f4_b_runtime_v1.binding import seal
from ..runtime.issue_f4_b_stage_a import sha,read
from .binding import root_inputs,catalog
from .pipeline import build_pipeline
from realization_utf8_io_v1 import write_new
CAPS=dict(solver_problems=0,fresh_scenes=3,action_scenes=3,collection_attempts=3)

def finalize(directory,branches,parent_branches,*,parent_root):
    from controlled_multi_future.root_orchestrator_v1_1 import finalize_three_branch_root_v1_1,compare_three_branch_final_state_payloads
    disk=[read(directory/'branches'/b['program_id']/'receipt.provisional.json') for b in branches]
    final=deepcopy(disk);clean=bool(final) and all((b.get('cleanup') or {}).get('cleanup_safety_pass') is True and (b.get('cleanup') or {}).get('orphan_process_count')==0 for b in final)
    original=finalize_three_branch_root_v1_1(final,reference_current_sha256=final[0]['reference_current_sha256'] if final else '',root_cleanup_pass=clean)
    expected={'common_x_pose','A_pose','B_pose','C_pose','executing_eef_pose','executing_gripper_open','execution_arm'}
    combined=[*parent_branches,*final]
    complete=len(final)==3 and len(parent_branches)==3 and all(set(b.get('final_state_equivalence_payload') or {})==expected for b in combined)
    cross=compare_three_branch_final_state_payloads(combined) if complete else {'equivalent':False,'reason':'all_six_complete_final_states_required'}
    accepted=original.get('accepted') is True and cross['equivalent'] is True
    # Finalize divergence first, then write exactly these same branch objects.
    for branch in final:write_new(directory/'branches'/branch['program_id']/'receipt.json',branch)
    root=seal(dict(schema_version='cmf_development_existing_root_realization_cohort_v1',status='accepted' if accepted else 'incomplete',
        parent_root=str(parent_root),parent_root_receipt_file_sha256=sha(Path(parent_root)/'root_receipt.json'),
        parent_root_id=read(Path(parent_root)/'planned_root_slot_spec.json')['slot_id'],
        planned_root_slot_spec_sha256=sha(Path(parent_root)/'planned_root_slot_spec.json'),cohort='F4_B_motion',variant='r_inv_motion',
        branch_receipts=final,cleanup_records=[b.get('cleanup') for b in final],root_finalization=original,
        cross_pc_motion_final_state_equivalence=cross,new_independent_root_count=0,formal_data=False,stage1_authorized=False))
    write_new(directory/'root_receipt.json',root)
    if accepted:
        files={b['program_id']:sha(directory/'branches'/b['program_id']/'receipt.json') for b in final}
        write_new(directory/'publication_index.json',seal(dict(schema_version='cmf_collector_publication_index_v1',
            planned_root_slot_spec_sha256=root['planned_root_slot_spec_sha256'],
            root_receipt_file_sha256=sha(directory/'root_receipt.json'),branch_files=files,publication_complete=True,stage_authorization_granted=False)))
    return root

def run(manifest,*,meter):
    job=manifest['jobs'][0]
    if job.get('resource_caps')!=CAPS or job.get('requires_live_meter') is not True or meter.closed or any(meter.counts.values()):raise ValueError('B motion requires live clean meter and0/3/3/3')
    root,bound,parent=root_inputs(job);cells=catalog(root,bound,parent)
    if job.get('catalog_sha256')!=cells['receipt_sha256'] or job.get('root_artifact_files')!=cells['dependencies']:raise ValueError('motion catalog/root artifacts were not frozen exactly')
    out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False);write_new(out/'catalog.json',cells)
    pipeline=build_pipeline(bound,manifest['implementation_source_sha256']);branches=[];error=None;cohort=None
    try:
        with meter.instrument_collector_factory(pipeline,profile_for_cell=lambda c:manifest['implementation_source_sha256']):
            for cell in cells['cells']:
                write_new(out/'attempts'/(cell['cell_id']+'.start.json'),seal({'cell':cell,'manifest_sha256':manifest['manifest_sha256']}))
                row=pipeline.collect_cell(cell,out/'branches'/cell['program']['program_id'],shared_current_dir=out/'current')
                branches.append(row)
                if row['status']!='accepted':break
        cohort=finalize(out,branches,parent['branch_receipts'],parent_root=root)
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    counts=dict(meter.counts)
    known=len(branches)==counts['fresh_scenes']==counts['collection_attempts'] and all(b.get('accounting_complete') is True and b.get('planner_query_delta')==0 for b in branches)
    known=known and counts['solver_problems']==0 and sum(len(h.records) for h in meter.collection_hooks)==counts['collection_attempts']
    science=error is None and known and counts==CAPS and cohort is not None and cohort['status']=='accepted'
    terminal=seal(dict(scene_attempts=counts['fresh_scenes'],collection_attempts=counts['collection_attempts'],accounting_complete=known,
        resource_counts=counts,error=error,cohort=cohort,cells=[{'cell_id':b['cell_id'],'status':b['status']} for b in branches],
        scientific_route_pass=science,accepted_variant_trajectory_count=3 if science else 0,new_independent_root_count=0,
        pilot_cells_ledger_modified=False,**{'pass':error is None and known and all(not b.get('global_stop') for b in branches)}))
    write_new(out/'runtime_terminal.json',terminal);return terminal
