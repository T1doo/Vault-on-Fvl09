"""One deterministic 4mm release-waypoint proposal, no solve or rollout."""
import numpy as np
from .analyze import A,P,D,OUT,load,sha,digest,matrix,pose,negative_pairs,NativeWorld

def run():
    review=load(OUT/'ANALYSIS_001.json');model=load(D/'model_014_on_full.json');spec=load(D/'suffix_spec.json')
    for p,h in review['source_files'].items():
        if sha(p)!=h:raise ValueError('original review source changed '+p)
    if not review['all_target_buffered_negative_pairs_are_scale']:raise ValueError('not the observed support-padding conflict')
    kin=model['config']['kinematics'];offset=kin['collision_sphere_buffer']
    if offset!=.004:raise ValueError('only the actual original4mm buffer-derived proposal')
    B=matrix(review['actual_base_world_pose']);old=matrix(review['analytical_solver_goal'])
    new=old.copy();new[:3,3]+=B[:3,:3].T@np.array([0,0,offset])
    entries=kin['collision_spheres']['attached_can']
    spheres=np.asarray([[*(new[:3,:3]@np.asarray(s['center'])+new[:3,3]),s['radius']+offset] for s in entries])
    negatives=negative_pairs(spheres,['attached_can']*len(spheres),model['world'])
    can=load(D.parents[1]/'p48_f2_u_route_001/live_capture.json')['can_shapes']
    implied=np.asarray(review['solver_implied_actual_actor_pose']);raised=implied.copy();raised[2]+=offset
    native=NativeWorld(model['world'],can,review['actual_base_world_pose']).screen([raised.tolist()],table_support=False)
    goal=list(spec['targets'][1]['pose']);goal[2]+=offset
    result={'schema_version':'f2_on_one_release_waypoint_padding_clearance_proposal_v1','proposal_only':True,'execution_authorized_by_this_artifact':False,
      'parent_job':'p48_f2_on_beside_qualification_001','parent_review_receipt_sha256':review['receipt_sha256'],
      'evidence_based_single_revision':'raise_only_on_release_waypoint_by_existing_collision_buffer_world_z',
      'offset_world_z_m':offset,'offset_derivation':'exact existing saved cfg collision_sphere_buffer, not parameter search',
      'original_release_goal':spec['targets'][1]['pose'],'proposed_release_goal':goal,
      'metadata_support_target_actor_unchanged':spec['target_actor_pose'],'proposed_preopen_actor_pose':raised.tolist(),
      'preplace_retreat_rest_goals_unchanged':True,'all_189_attached_spheres_and_4mm_buffer_unchanged':True,
      'all_50_world_shapes_unchanged':True,'remaining_target_attached_world_negative_pairs':negatives,
      'native_target_check':native,'actual_robot_target_IK_checked':False,'actual_path_checked':False,
      'same_original_metadata_footprint_height_support_exclusivity_rest_gates':True,
      'same_original_100_settle_75_rest':True,'no_scale_pair_exception':True,'no_collision_tolerance_change':True,
      'planned_native_bottom_minus_scale0_top_m':review['native_checks']['actual_grasp_solver_implied_target']['bounds_world_m']['lower'][2]+offset-max(s['world_upper'][2] for s in review['scale_piece_world_bounds'] if s['name']=='scale__0'),
      'normal_on_release_drop_increases_by_m':offset,'physical_support_and_release_success_pending':True,
      'native_and_attached_target_CPU_pass':not negatives and native['pass'],'new_solver_problems':0,'new_scenes':0,
      'beside_not_attempted_and_requires_new_manifest':True,
      'sources':{str(p):sha(p) for p in (OUT/'ANALYSIS_001.json',D/'model_014_on_full.json',D/'suffix_spec.json',__file__)}}
    result['receipt_sha256']=digest(result);return result

if __name__=='__main__':
    from realization_utf8_io_v1 import write_new
    r=run();write_new(OUT/'SINGLE_REVISION_PROPOSAL_001.json',r)
    print({'CPU_pass':r['native_and_attached_target_CPU_pass'],'remaining_negative_pairs':r['remaining_target_attached_world_negative_pairs'],'preopen_native_floor_gap_m':r['planned_native_bottom_minus_scale0_top_m']})
