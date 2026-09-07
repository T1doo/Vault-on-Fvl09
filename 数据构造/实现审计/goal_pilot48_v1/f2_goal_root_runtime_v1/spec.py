"""New F2 root lineage; initial executable scope is prefix qualification only."""
import copy,hashlib,json
from pathlib import Path
from goal_pilot48_v1.f2_inward_runtime_v3.contract import A,P,W,digest,build_contract

def build_prefix_spec():
    c=build_contract();planned=copy.deepcopy(c['planned']);parent=planned.pop('planned_root_slot_spec_sha256')
    planned.update(slot_id='f2-goal-root-A-fixed-layout-v1-20260907',generator='f2_goal_root_runtime_v1',
      purpose='new_current_anchor_real_common_prefix_qualification',parent_planned_spec_sha256=parent,
      new_current_anchor_lineage_required=True,old_current_anchor_reuse_allowed=False)
    planned['planned_root_slot_spec_sha256']=digest(planned)
    return {'schema_version':'f2_goal_prefix_qualification_spec_v1','planned':planned,'binding':c['binding'],
      'qualified_beside_route_reference':'p48_f2_u_route_001','beside_approach_height_m':c['inward_contract']['approach_height_m'],
      'all_three_programs':['F2-inside','F2-on','F2-beside'],'old_inside_success_inherited':False,
      'root_acceptance_authorized_by_this_spec':False,'prefix_only':True,
      'resource_caps':{'solver_problems':3,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0},
      'prefix_ops':['pregrasp','grasp','close0','actual_postclose_model','lift12cm','original_settle_and_physical_gate'],
      'qualification_recipe_selection_is_not_completed_prefix':True}

def validate_prefix_spec(spec):
    expected=build_prefix_spec()
    if spec!=expected:raise ValueError('new F2 prefix spec mismatch')
    return True
