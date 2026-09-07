"""Original physical support numbers with approved native geometry provider."""
import numpy as np
from goal_pilot48_v1.f2_inside_native_floor_v1.physical_gates import opening_geometry,pre_release_floor_support,release_safety_gate,final_inside_gate
from .spec import digest

def physical_rows(rows):
    """Same original row adapter; completeness is calculated, not asserted."""
    from controlled_multi_future.high_level_physical_runner_v1 import _complete_contact_signal
    return [{**r,'contact_signal_complete':_complete_contact_signal(r)} for r in rows]

def support_gate(scene,binding,verifier):
    from controlled_multi_future.high_level_physical_runner_v1 import _pair_is_physical_hit_between
    from controlled_multi_future.runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS as t
    rows=scene.trace[-50:];c=verifier.c
    hit=lambda row,a,b:any(_pair_is_physical_hit_between(pair,{a},{b}) for pair in row.get('contact_pairs',[]))
    opening=opening_geometry(scene,binding,c)
    checks={'exact_50_frame_window':len(rows)==50,'continuous_box_support':bool(rows) and all(hit(r,c['can_actor_name'],c['box_actor_name']) for r in rows),
      'no_table_contact':bool(rows) and all(not hit(r,c['can_actor_name'],'table') for r in rows),
      'stable_before_open':bool(rows) and max(float(np.linalg.norm(r['actor_linear_velocity'])) for r in rows)<=t['stable_linear_speed_mps'] and max(float(np.linalg.norm(r['actor_angular_velocity'])) for r in rows)<=t['eef_stationary_angular_speed_rps'],
      'opening_projection_inside':opening['opening_projection_inside'] is True,
      'selected_contact_continuous':all(r.get('selected_gripper_contact') is True for r in rows)}
    original={'schema_version':'cmf_f2_controlled_insertion_support_gate_v2','checks':checks,'opening_geometry':opening,'pass':all(checks.values())};original['receipt_sha256']=digest(original)
    return pre_release_floor_support(physical_rows(rows),verifier,original_support_gate=original)
