"""Freeze exactly CPU-selected B; never create a scene or run IK."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from .geometry import A,D,Geometry,matrix,pose
sys.path[:0]=[str(A),str(A/'代码审阅快照'),str(A/'new_recipe_prereqs_v1')]
from goal_mapping import cpu_views,roundtrip
from realization_utf8_io_v1 import write_new
O=Path(__file__).parent;G=O.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seal(v):return {**v,'receipt_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()}
def main():
    approval=G/'USER_F2_CONTACT_F3_UPRIGHT_APPROVAL_V1_20260907.md'
    if 'F3_UPRIGHT_SAME_ASSET_QUALIFICATION_V1' not in approval.read_text(encoding='utf-8'):raise ValueError('upright design approval absent')
    audit=json.loads((O/'candidate_geometry_audit.json').read_text(encoding='utf-8'));a,b=audit['candidates']
    if a['candidate']!='A_neck_flange' or a['neck_first_contact_necessary_pass']:raise ValueError('A must be transparently rejected before B selection')
    if b['candidate']!='B_upper_straight_body' or not b['all_open_clear'] or not b['both_sides_reachable'] or b['palm_bottle_hits'] or any(r['hits'] for r in b['support_closure_samples']):raise ValueError('B necessary hand geometry failed')
    if not all(v['bottle_shapes_at_touch']==['bottle__4'] for v in b['first_native_contacts'].values()):raise ValueError('B not same continuous body section')
    if not json.loads((O/'initial_arm_audit.json').read_text(encoding='utf-8'))['pass']:raise ValueError('known initial native arm state blocked')
    geometry=Geometry();grasp=np.array(b['desired_actual_flange_world_pose']);pre=grasp.copy();pre[1]-=.12
    base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))['solver_base_binding']['base_link_world_pose'];robot,planner=cpu_views(base)
    mappings={'grasp':roundtrip(robot,planner,grasp),'pregrasp':roundtrip(robot,planner,pre)}
    mass_path=D/'p48_f3_one_sided_micro_001/actual_mass_properties.json';mass=json.loads(mass_path.read_text(encoding='utf-8'))
    local=np.concatenate([np.asarray(s['vertices']) for s in geometry.bottle_shapes]);world=local@geometry.B[:3,:3].T+geometry.B[:3,3]
    if abs(world[:,2].min()-.75)>1e-12:raise ValueError('native base not analytically aligned with original pad')
    spec=seal({'schema_version':'cmf_f3_upright_same_asset_qualification_design_v1','design_id':'F3_UPRIGHT_SAME_ASSET_QUALIFICATION_V1',
        'selected_design':'B_upper_straight_body','selection_rule':'A first contact strikes cap, not neck bearing; B only CPU-selected before GPU',
        'slot_id':'f3-upright13-B-qualification-v1','family':'F3','seed':2026090713,
        'asset_id':13,'asset_name':'001_bottle','scale':[.132,.132,.132],'bottle_actor_pose':geometry.bottle_pose,
        'pad_actor_pose':[-.18,-.06,.745,1,0,0,0],'pad_top_m':.75,
        'nominal_grasp_world_pose':grasp.tolist(),'nominal_pregrasp_world_pose':pre.tolist(),
        'grasp_in_bottle_frame':pose(np.linalg.inv(geometry.B)@matrix(grasp)),
        'pregrasp_in_bottle_frame':pose(np.linalg.inv(geometry.B)@matrix(pre)),
        'target_derivation':'fixed bottle-relative grasp/pregrasp applied to one accepted actual post-settle bottle pose; no candidate search',
        'close_normalized':.5,'hold_frames':250,'lift_m':.025,'postlift_confirmation_frames':50,
        'minimum_actual_rise_m':.020,'maximum_relative_translation_m':.005,'maximum_relative_orientation_rad':.05,
        'canonical_settle_steps':60,'primary_frequency_hz':250,'event_programs':['VVHH','VHVH','VHHV'],'shared_V_amplitude_m':.055,'shared_V_points':7,'event_hold_frames':50,
        'expected_mass_properties':mass,'mass_source_set_value':.01,'friction_unchanged':{'static':.5,'dynamic':.5},
        'actual_contact_height_above_COM_candidate_m':[v['contact_local_y_minmax_m'][0]-mass['cmass_local_pose'][1] for v in b['first_native_contacts'].values()],
        'nominal_native_bottle_bounds_world':[world.min(0).tolist(),world.max(0).tolist()],
        'nominal_pose_mapping_audit':mappings,
        'qualification_cap':{'solver_problems':6,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0,'gpu_lease_seconds':1080,'child_timeout_seconds':900},
        'conditional_confirmation_cap':{'solver_problems':17,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0,'gpu_lease_seconds':1980,'child_timeout_seconds':1800},
        'total_round_cap':{'solver_problems':23,'fresh_scenes':2,'action_scenes':2,'collection_attempts':0,'gpu_lease_seconds':3060},
        'old_stability_revision_limit_not_reset':True,'physical_failure_may_not_switch_to_A_or_third_scene':True,
        'upright_standing_actual_stability_verified':False,'target_IK_or_full_arm_path_verified':False,'CPU_geometry_selected_not_physical_qualified':True,
        'execution_ready':False,'remaining_runtime_work':'fresh scene standing/mass gate, counted3IK and actual full-arm native planned-control screens, micro binding, conditional sharedV integration',
        'source_bindings':{str(p):sha(p) for p in [approval,O/'candidate_geometry_audit.json',O/'initial_arm_audit.json',mass_path,geometry.capture_path,geometry.model_path,G/'f3_next_design_impact_review_v1/base_support_diagnostic.json']}})
    write_new(O/'design_spec.json',spec);print(spec['receipt_sha256']);print('B contact heights aboveCOM',spec['actual_contact_height_above_COM_candidate_m'])
if __name__=='__main__':main()
