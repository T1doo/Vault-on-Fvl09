"""B motion after resource-only correction; shared current acceptance is separate."""
from pathlib import Path
from goal_pilot48_v1.f4_b_motion_runtime_v1 import runtime as old
from goal_pilot48_v1.f4_b_runtime_v1.stages import bound_function
from goal_pilot48_v1.f4_b_runtime_v1.binding import seal,checked
from realization_current_layout_audit_v1 import audit as current_audit
from realization_utf8_io_v1 import write_new,load_json
from .binding import root_inputs

def run(manifest,*,meter):
    out=Path(manifest['jobs'][0]['output_namespace'])
    def inner_write(path,value):
        path=Path(path)
        targets={out/'runtime_terminal.json':out/'pipeline_terminal.json',out/'publication_index.json':out/'pipeline_publication_index.json'}
        return write_new(targets.get(path,path),value)
    finalize=bound_function(old.finalize,write_new=inner_write)
    fn=bound_function(old.run,root_inputs=root_inputs,write_new=inner_write,finalize=finalize)
    result=fn(manifest,meter=meter)
    checks=[];identities=[];error=None
    try:
        directory=out/'current'
        if (directory/'current_arrays.npz').exists():
            metadata=load_json(directory/'current.json');parent=Path(metadata['parent_root'])
            reference=load_json(parent/'reference_current_hashes.json')
            if metadata['current']['aggregate_sha256']!=reference['aggregate_sha256'] or metadata['current']['model_visible_components']!=reference['model_visible_components']:
                raise ValueError('later current metadata components do not match original sealed root hashes')
            # Compare captured later current to every old pc row0 and every
            # newly available motion row0 using the existing38+38 decoder.
            for pid in ('F4-ABC','F4-ACB','F4-BAC'):
                checks.append(current_audit(directory,parent/'branches'/pid/'trace_source.npz'))
                identities.append({'program_id':pid,'realization':'r_pc'})
                trace=out/'branches'/pid/'trace_source.npz'
                if trace.exists():
                    checks.append(current_audit(directory,trace))
                    identities.append({'program_id':pid,'realization':'r_inv_motion'})
        else:error={'type':'CurrentArtifactMissing','message':'keep pc/motion pilot eligibility pending'}
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    available_pass=bool(checks) and error is None and all(c.get('pass') is True and c.get('unique_articulation_dofs')==38 and c.get('model_visible_robot_state_dimension')==76 for c in checks)
    expected=[{'program_id':pid,'realization':real} for pid in ('F4-ABC','F4-ACB','F4-BAC') for real in ('r_pc','r_inv_motion')]
    complete=len(checks)==6 and identities==expected
    components_pass=available_pass and complete
    if error is None and not available_pass:error={'type':'CurrentComponentAuditRejected','message':'returned false or wrong38/76 layout, not merely exception based'}
    if error is None and not complete:error={'type':'CurrentAuditMatrixIncomplete','message':'requires exactly3programs x(pc,motion), all6 trace inputs'}
    audit=seal(dict(current_component_checks=checks,error=error,current_component_validation_pass=components_pass,
        available_current_components_pass=available_pass,complete_program_realization_matrix=complete,checked_current_sources=identities,
        captured_later_not_originally_saved=True,formal_or_pilot_acceptance_issued=False,producer_Goal_Guard_still_required=True))
    write_new(out/'current_component_audit.json',audit)
    result=dict(result);result.pop('receipt_sha256',None)
    result.update(source_root_original_goal_pass=False,resource_only_source_acceptance=True,
        current_component_audit=audit,shared_current_reference_publication_required=True,pilot_cells_modified=False)
    if not components_pass:result['scientific_route_pass']=False;result['accepted_variant_trajectory_count']=0
    if components_pass and result.get('scientific_route_pass') is True and (out/'pipeline_publication_index.json').exists():
        index=checked(load_json(out/'pipeline_publication_index.json'));index.pop('receipt_sha256',None)
        index.update(current_component_audit_receipt_sha256=audit['receipt_sha256'],producer_Goal_Guard_still_required=True)
        write_new(out/'publication_index.json',seal(index))
    result=seal(result);write_new(out/'runtime_terminal.json',result);return result
