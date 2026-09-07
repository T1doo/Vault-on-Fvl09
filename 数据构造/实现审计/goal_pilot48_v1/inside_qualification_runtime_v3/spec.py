from goal_pilot48_v1.inside_qualification_runtime_v2.spec import build_spec as old_spec
from goal_pilot48_v1.f2_inside_carry_waypoint_revision_v1.analyze import A,load,sha,digest
REVIEW=A/'goal_pilot48_v1/f2_inside_carry_waypoint_revision_v1/CPU_REVIEW.json'

def checked_review():
    r=load(REVIEW);p=dict(r);h=p.pop('receipt_sha256')
    if digest(p)!=h:raise ValueError('carry review selfhash mismatch')
    for table in ('files','analysis_source_files'):
        for path,value in r[table].items():
            if sha(path)!=value:raise ValueError('carry review source/evidence changed')
    if not r['native_continuous_straight_carry']['pass'] or not r['actual_fitted_buffered_sphere_straight_carry']['pass']:raise ValueError('carry geometric prerequisite failed')
    return r

def build_spec():
    r=checked_review();s=old_spec();s.update(schema_version='f2_inside_carry_revision1_fresh_qualification_v3',
      carry_waypoint_revision=1,carry_rule='preserve_actual_prefix_EEF_z_and_orientation_move_can_xy_to_final_inside_xy',
      failed_parent_job='p48_f2_inside_qualification_001',CPU_carry_review_sha256=sha(REVIEW),CPU_carry_receipt_sha256=r['receipt_sha256'],
      additional_lift_height_m=0,final_inside_and_remaining_four_targets_changed=False)
    return s
