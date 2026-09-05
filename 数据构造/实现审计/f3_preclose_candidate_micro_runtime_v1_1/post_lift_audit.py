"""Predeclared CPU-only 20-mm/50-frame micro-lift diagnostic contract."""
import math
import numpy as np
from controlled_multi_future.geometry import relative_pose
from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8

CONTRACT={'minimum_actual_bottle_rise_m':.020,'post_lift_confirmation_frames':50,
 'maximum_relative_translation_drift_m':.005,'maximum_relative_orientation_drift_rad':.05}

def audit_micro_lift_trace(trace,*,baseline_row,lift_receipt,arm,selected_links,bottle_name,support_names):
    checks={'execution_receipt':False,'complete_window':False,'actual_rise':False,'continuous_selected_contact':False,
        'confirmation_off_support':False,'full_window_transform':False,'no_forbidden_arm_collisions':False,'signal_complete':False}
    result={'schema_version':'cmf_f3_post_lift_audit_v1_1','contract':dict(CONTRACT),'checks':checks,'pass':False,'lift_execution_receipt':lift_receipt}
    try:
        if arm not in ('left','right') or not selected_links or not support_names:raise ValueError('actor/arm identities')
        start=lift_receipt['start_trace_row'];end=lift_receipt['end_trace_row']
        if type(start) is not int or type(end) is not int or type(baseline_row) is not int or start!=baseline_row or start<0 or end<=start:raise ValueError('lift receipt rows')
        pos=float(lift_receipt['tracking_position_error_m']);ang=float(lift_receipt['tracking_orientation_error_rad'])
        checks['execution_receipt']=lift_receipt['planner_status']=='Success' and lift_receipt['segment_id']=='f3_micro_lift25' and math.isfinite(pos) and math.isfinite(ang) and 0<=pos<=.030 and 0<=ang<=.020
        if len(trace)!=end+51:raise ValueError('confirmation must contain exactly 50 rows')
        base=trace[start]
        def pose(row,key):
            p=np.asarray(row[key],dtype=float)
            if p.shape!=(7,) or not np.all(np.isfinite(p)) or np.linalg.norm(p[3:])==0:raise ValueError('invalid '+key)
            return p
        base_actor=pose(base,'actor_pose');base_transform=relative_pose(pose(base,'eef'),base_actor)
        step=int(base['step_index']);last_time=float(base['timestamp'])
        if not math.isfinite(last_time):raise ValueError('baseline timestamp')
        selected=set(selected_links);support=set(support_names);prefix='fl_' if arm=='left' else 'fr_'
        contact_ok=off_ok=collision_ok=complete=True;max_t=max_a=0.;rises=[];first_failure=None
        for i in range(start+1,len(trace)):
            row=trace[i]
            if type(row['step_index']) is not int or row['step_index']!=step+i-start:raise ValueError('missing/duplicate trace row')
            now=float(row['timestamp'])
            if not math.isfinite(now) or now<=last_time:raise ValueError('missing/nonmonotonic timestamp')
            last_time=now;actor=pose(row,'actor_pose');eef=pose(row,'eef')
            transform=relative_pose(eef,actor);td=float(np.linalg.norm(transform[:3]-base_transform[:3]));ad=float(quaternion_angular_error(transform[3:],base_transform[3:]))
            max_t=max(max_t,td);max_a=max(max_a,ad)
            if i>=end:rises.append(float(actor[2]-base_actor[2]))
            pairs=row['contact_pairs']
            if not isinstance(pairs,list):raise ValueError('contact list missing')
            selected_hit=False;support_hit=False;forbidden=False;row_complete=True
            for p in pairs:
                bodies={p['body_a'],p['body_b']}
                if not all(isinstance(x,str) and x for x in bodies):raise ValueError('body identity')
                signal=classify_contact_pair_physical_hit_v8(p)
                row_complete &= signal['evidence_complete'] is True
                if signal['physical_hit_for_gate'] is not True:continue
                arm_bodies={x for x in bodies if x.startswith(prefix)}
                if len(arm_bodies)==2 or (arm_bodies and bodies & support):forbidden=True
                if bottle_name in bodies:
                    selected_hit |= bool(bodies & selected);support_hit |= bool(bodies & support)
                    if arm_bodies and not arm_bodies.issubset(selected):forbidden=True
            contact_ok &= selected_hit;complete &= row_complete;collision_ok &= not forbidden
            if i>end:off_ok &= not support_hit
            if first_failure is None and (not selected_hit or not row_complete or forbidden or td>.005 or ad>.05 or (i>end and support_hit)):
                first_failure=i
        checks.update(complete_window=True,actual_rise=bool(rises) and min(rises)>=.020,
            continuous_selected_contact=bool(contact_ok),confirmation_off_support=bool(off_ok),
            full_window_transform=max_t<=.005 and max_a<=.05,no_forbidden_arm_collisions=bool(collision_ok),signal_complete=bool(complete))
        result.update(minimum_measured_rise_m=min(rises),maximum_relative_translation_drift_m=max_t,
            maximum_relative_orientation_drift_rad=max_a,first_failed_row=first_failure,
            lift_rows=end-start,confirmation_rows=50,pass_=all(checks.values()))
        result['pass']=result.pop('pass_')
    except (KeyError,ValueError,TypeError,IndexError) as exc:
        result['error']={'type':type(exc).__name__,'message':str(exc)}
    return result
