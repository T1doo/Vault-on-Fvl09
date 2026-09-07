"""Original whole-held transport Gate; support adaptation is not authorized."""
from .spec import digest

def audit_transport(rows,*,descent_start_relative_row,verifier,can_actor_name,selected_gripper_body_names,allowed_gripper_assembly_body_names,named_facility_body_names):
    from controlled_multi_future.f2_suffix_routes_v3 import audit_f2_held_transport_contacts
    kwargs=dict(relation='inside',can_actor_name=can_actor_name,selected_gripper_body_names=selected_gripper_body_names,
      allowed_gripper_assembly_body_names=allowed_gripper_assembly_body_names,named_facility_body_names=named_facility_body_names)
    unmodified=audit_f2_held_transport_contacts(rows,**kwargs)
    result={'schema_version':'f2_original_inside_transport_pending_support_decision_v1','pass':unmodified['pass'],'original_unmodified_audit':unmodified,
      'floor_pair_projection_implemented':False,'floor_pair_projection_enabled':False,'supported_descent_contact_permission_pending':True,
      'descent_start_relative_row':descent_start_relative_row,'raw_rows_unchanged':True,'whole_box_whitelist':False}
    result['receipt_sha256']=digest(result);return result
