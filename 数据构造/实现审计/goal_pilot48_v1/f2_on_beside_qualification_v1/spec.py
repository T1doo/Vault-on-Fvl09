from goal_pilot48_v1.f2_on_beside_runtime_v1.spec import lineage,REFERENCE,digest,sha
from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.runtime import build_prefix_spec
CAPS={'solver_problems':8,'fresh_scenes':2,'action_scenes':2,'collection_attempts':0}
RELATIONS=('on','beside')
def build_spec():
    parent=build_prefix_spec()
    return {'schema_version':'f2_on_beside_fresh_qualification_v1','binding':parent['binding'],'planned':parent['planned'],
      'prefix_lineage':lineage(),'relations':list(RELATIONS),'stop_on_first_required_failure':True,
      'resource_caps':CAPS,'per_relation_solver_cap':4,'high_level_state_checks':{'on':6,'beside':10},
      'prefix_operation':'actual_canonical_replay_zero_new_solver','whole_root_qualification_complete':False,
      'inside_contact_permission_used':False,'original_on_beside_verifiers_unchanged':True,
      'new_accepted_roots':0,'new_raw_trajectories':0}
