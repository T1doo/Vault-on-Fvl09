"""Two four-target suffixes, derived from the real replayed can/flange state."""
import copy
import json,hashlib
from pathlib import Path
import numpy as np
from goal_pilot48_v1.f2_inward_runtime_v3.contract import A,W,build_contract,proposal,digest
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,pose

REFERENCE=W/'Robotwin2/datasets/p48_f2_prefix_clearance_001'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def lineage():
    terminal=load(REFERENCE/'job_terminal.json');p=dict(terminal);h=p.pop('receipt_sha256')
    if digest(p)!=h or not all(terminal.get(k) is True for k in ('pass','prefix_physical_pass','scientific_route_pass')):
        raise ValueError('real accepted prefix required')
    files=['job_terminal.json','goal_terminal.json','prefix_result.json','reference_anchor.json','reference_current_hashes.json',
      'prefix_trace.npz','canonical_prefix_artifact/canonical_prefix_artifact.json','canonical_prefix_artifact/prefix_arrays.npz']
    return {'reference_job':'p48_f2_prefix_clearance_001','files':{str(REFERENCE/f):sha(REFERENCE/f) for f in files},
      'current':load(REFERENCE/'reference_current_hashes.json'),'anchor':load(REFERENCE/'reference_anchor.json'),
      'prefix_receipt_sha256':h,'old_held_state_not_used':True}

def make_targets(actual_eef,actual_can,target_actor,neutral,approach_height):
    values=[np.asarray(p,dtype=float) for p in (actual_eef,actual_can,target_actor,neutral)]
    if any(p.shape!=(7,) or not np.isfinite(p).all() or abs(np.linalg.norm(p[3:])-1)>1e-5 for p in values):
        raise ValueError('finite actual world poses required')
    E,C,D,N=map(matrix,values);grasp=np.linalg.inv(E)@C;release=D@np.linalg.inv(grasp)
    upper=release.copy();upper[2,3]+=approach_height
    return [{'segment_id':name,'pose':pose(T)} for name,T in zip(('preplace','release','retreat','rest'),(upper,release,upper,N))],grasp.tolist()

def build_targets(scene,relation):
    if relation not in ('on','beside'):raise ValueError('only original on/beside semantics')
    from controlled_multi_future.f2_asset_bound_runtime_v3 import _actor_pose_centered_on_support,_actor_local_geometry_bounds
    from controlled_multi_future.family_runners_v3_3 import _pose,_arm_eef_pose
    c=build_contract();binding=scene._cmf_f2_asset_binding_v3
    if binding!=c['binding']:raise ValueError('wrong actual prefix layout binding')
    if relation=='on':
        center,half=_actor_local_geometry_bounds(scene.can);point=np.asarray(scene.scale.get_functional_point(0))
        target=_actor_pose_centered_on_support(target_geometry_xy=point[:2],support_plane_z_m=float(point[2]),
          orientation_wxyz=binding['layout_payload']['main_object_orientation_wxyz'],local_geometry_center_m=center,half_extents_m=half)
        height=.10;source={'method':'unchanged_metadata_bounds_and_scale_functional_point','scale_point':point.tolist()}
    else:
        # Keep the selected native-supported D actor pose, not its historical
        # held-state EEF goal. The new grip determines the new EEF target.
        target=np.asarray(c['beside_template_actor_pose']);height=proposal()['new_approach_height_m']
        source={'method':'reviewed_revision1_native_supported_D_actor','route_proposal_sha256':c['inward_contract']['route_proposal_file_sha256']}
    actual_eef=np.asarray(_arm_eef_pose(scene,'left'));actual_can=np.asarray(_pose(scene.can));neutral=np.asarray(scene.robot.left_original_pose)
    targets,grasp=make_targets(actual_eef,actual_can,target,neutral,height)
    result={'schema_version':'f2_on_beside_actual_prefix_suffix_v1','relation':relation,'program_id':'F2-'+relation,
      'targets':targets,'target_actor_pose':target.tolist(),'actual_eef_to_can':grasp,'actual_start_eef':actual_eef.tolist(),
      'actual_start_can':actual_can.tolist(),'binding_sha256':binding['binding_sha256'],'prefix_lineage':lineage(),
      'approach_height_m':height,'target_source':source,'release_index':1,'settle_frames':100,'rest_frames':75,
      'suffix_solver_cap':4,'whole_root_budget':False,'original_final_metadata_verifier_unchanged':True,
      'old_physical_success_inherited':False}
    result['receipt_sha256']=digest(result);return result

def validate(spec):
    value=copy.deepcopy(spec);h=value.pop('receipt_sha256',None)
    if digest(value)!=h or spec['relation'] not in ('on','beside') or len(spec['targets'])!=4:
        raise ValueError('invalid suffix spec')
    if [spec[k] for k in ('release_index','settle_frames','rest_frames','suffix_solver_cap')]!=[1,100,75,4]:
        raise ValueError('on/beside windows or four-query cap changed')
    height=.10 if spec['relation']=='on' else proposal()['new_approach_height_m']
    if spec['approach_height_m']!=height or spec['prefix_lineage']!=lineage():raise ValueError('route/prefix source changed')
    expected,_=make_targets(spec['actual_start_eef'],spec['actual_start_can'],spec['target_actor_pose'],spec['targets'][-1]['pose'],height)
    for a,b in zip(expected,spec['targets']):
        if a['segment_id']!=b['segment_id'] or not np.allclose(matrix(a['pose']),matrix(b['pose']),atol=1e-12,rtol=0):
            raise ValueError('target no longer bound to actual grip')
    return True
