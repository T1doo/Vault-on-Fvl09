from goal_pilot48_v1.f2_controlled_inside_runtime_v2.spec import prefix_lineage,REFERENCE,A,sha,digest
from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.runtime import build_prefix_spec

CAPS={'solver_problems':5,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}

def build_spec():
    parent=build_prefix_spec();lineage=prefix_lineage()
    return {'schema_version':'f2_inside_one_fresh_replay_qualification_v1','binding':parent['binding'],'planned':parent['planned'],
      'prefix_lineage':lineage,'resource_caps':CAPS,'high_level_state_check_cap':10,
      'prefix_operation':'actual_canonical_replay_zero_new_solver','scene_phase':'f2_inside_noncollection_qualification',
      'physical_verifier':'f2_inside_native_envelope_piecewise_floor_v1','old_gravity_drop_allowed':False,
      'whole_root_qualification_complete':False,'new_accepted_roots':0,'new_raw_trajectories':0}
