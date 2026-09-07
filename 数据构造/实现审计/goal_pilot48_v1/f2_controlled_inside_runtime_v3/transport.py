"""Native-certified audit projection, immutable raw rows and old rejection."""
import copy
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.spec import digest
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.gates import physical_rows
from .approval import verify_approval

def row_commitment(rows):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    fields=('contact_pairs','selected_gripper_contact','selected_contact_actor_name','role_actor_poses','actor_pose_frame')
    return digest(canonical_jsonable([{key:r.get(key) for key in fields} for r in rows]))

def audit_transport(rows,*,descent_start_relative_row,supported_stage_end_relative_row,held_window_start_trace_row,verifier,can_actor_name,selected_gripper_body_names,allowed_gripper_assembly_body_names,named_facility_body_names):
    from controlled_multi_future.f2_suffix_routes_v3 import audit_f2_held_transport_contacts
    from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
    from goal_pilot48_v1.f2_inside_native_floor_v1.contact import verify_floor_contact_row
    approval=verify_approval();rows=list(rows);raw_hash=row_commitment(rows)
    if type(held_window_start_trace_row) is not int or held_window_start_trace_row<0:raise ValueError('actual held-window trace origin required')
    if descent_start_relative_row is not None and (type(descent_start_relative_row) is not int or not 0<=descent_start_relative_row<len(rows)):raise ValueError('descent boundary outside retained complete held window')
    if descent_start_relative_row is not None and (type(supported_stage_end_relative_row) is not int or not descent_start_relative_row<=supported_stage_end_relative_row<len(rows)):raise ValueError('supported-stage end outside retained window')
    kwargs=dict(relation='inside',can_actor_name=can_actor_name,selected_gripper_body_names=selected_gripper_body_names,
      allowed_gripper_assembly_body_names=allowed_gripper_assembly_body_names,named_facility_body_names=named_facility_body_names)
    original=audit_f2_held_transport_contacts(rows,**kwargs)
    continuous=all(r.get('selected_gripper_contact') is True and r.get('selected_contact_actor_name')==can_actor_name for r in rows)
    grippers=set(selected_gripper_body_names);projected=[];allowed=[];proofs={}
    for i,row in enumerate(physical_rows(rows)):
        pairs=row.get('contact_pairs',[]);kept=[];proof=None
        physical_grasp=any(can_actor_name in {p.get('body_a'),p.get('body_b')} and bool({p.get('body_a'),p.get('body_b')}&grippers)
          and classify_contact_pair_physical_hit_v8(p)['evidence_complete'] is True and classify_contact_pair_physical_hit_v8(p)['physical_hit_for_gate'] is True for p in pairs)
        for j,pair in enumerate(pairs):
            box_pair={pair.get('body_a'),pair.get('body_b')}=={can_actor_name,verifier.c['box_actor_name']}
            eligible=continuous and physical_grasp and box_pair and descent_start_relative_row is not None and descent_start_relative_row<i<=supported_stage_end_relative_row
            if eligible:
                if proof is None:
                    try:proof=verify_floor_contact_row(row,verifier)
                    except (ValueError,KeyError,TypeError) as e:proof={'pass':False,'error':{'type':type(e).__name__,'message':str(e)}}
                bi=0 if pair['body_a']==verifier.c['box_actor_name'] else 1;identities=pair.get('shape_identities',[])
                eligible=proof['pass'] is True and len(identities)==2 and identities[bi].get('body_collision_shape_index')==9 and classify_contact_pair_physical_hit_v8(pair)['physical_hit_for_gate'] is True
            if eligible:
                proofs[str(i)]=proof
                allowed.append({'relative_row':i,'absolute_trace_row':held_window_start_trace_row+i,'original_pair_index':j,'original_pair_sha256':digest(pair),
                  'shape_identities':copy.deepcopy(pair['shape_identities']),'native_row_proof_sha256':proof['receipt_sha256'],'box_shape_index':9})
            else:kept.append(pair)
        projected.append({**row,'contact_pairs':kept})
    adapted=audit_f2_held_transport_contacts(projected,**kwargs)
    if row_commitment(rows)!=raw_hash:raise RuntimeError('original raw evidence mutated')
    result={'schema_version':'f2_supported_descent_box9_transport_gate_v1','approval':approval,'pass':bool(adapted['pass']),
      'original_unmodified_audit':original,'original_audit_on_explicit_projection':adapted,'projected_pair_receipts':allowed,'native_row_proofs':proofs,
      'original_physical_rows_sha256':raw_hash,'projected_physical_rows_sha256':row_commitment(projected),
      'descent_start_relative_row':descent_start_relative_row,'supported_stage_end_relative_row':supported_stage_end_relative_row,'boundary_start_row_excluded_as_preinsert_state':True,
      'held_window_start_trace_row':held_window_start_trace_row,
      'descent_boundary_trace_row':None if descent_start_relative_row is None else held_window_start_trace_row+descent_start_relative_row,
      'supported_stage_end_trace_row':None if supported_stage_end_relative_row is None else held_window_start_trace_row+supported_stage_end_relative_row,
      'all_original_rows_retained':True,'original_row_count':len(rows),'projected_row_count':len(projected),'whole_box_whitelist':False,
      'continuous_original_selected_grasp_identity':continuous,'numeric_thresholds_changed':False}
    result['receipt_sha256']=digest(result);return result

def validate_projection(receipt,rows,**kwargs):
    candidate=copy.deepcopy(receipt);claimed=candidate.pop('receipt_sha256',None)
    if digest(candidate)!=claimed:raise ValueError('projection selfhash changed')
    if audit_transport(rows,**kwargs)!=receipt:raise ValueError('projection does not reproduce from original rows/phase/native evidence')
    return True
