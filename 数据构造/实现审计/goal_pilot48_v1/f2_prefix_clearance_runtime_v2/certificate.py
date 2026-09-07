"""F2-specific native/grasp clearance evidence; never a table-contact claim."""
import copy,os
import numpy as np
import transforms3d as t3d
from scipy.spatial import ConvexHull
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
from goal_pilot48_v1.f2_inward_runtime_v1.contract import digest

VERSION='f2_nonpenetrating_grasp_upward_clearance_certificate_v1'
EPS=1e-4

def physical_row(row):
    """Bind measured state, not inactive planner command fields (legal NaNs)."""
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    keys=('eef','role_actor_poses','selected_contact_actor_name','contact_pairs',
      'role_actor_linear_velocities','role_actor_angular_velocities',
      'role_actor_linear_velocity_measured','role_actor_angular_velocity_measured',
      'role_actor_component_linear_velocities','role_actor_component_angular_velocities',
      'role_actor_component_linear_velocity_measured','role_actor_component_angular_velocity_measured')
    return canonical_jsonable({key:row[key] for key in keys})

def state_binding(scene,cfg,export,can,targets):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    return {'scene_instance_id':scene._cmf_scene_instance_id,'job_namespace':scene._cmf_goal_prefix_output,
      'gpu_uuid':os.environ.get('CUDA_VISIBLE_DEVICES'),'trace_last_index':len(scene.trace)-1,
      'trace_last_row_sha256':digest(physical_row(scene.trace[-1])),
      'joint_qpos_sha256':digest(np.asarray(scene.robot.left_entity.get_qpos()).tolist()),
      'model_cfg_sha256':digest(cfg),'world_sha256':digest(export['shapes']),'can_sha256':digest(can),
      'lift_target_sha256':digest(targets[2]),'lift_target_pose':targets[2]['pose'],'grasp_target_pose':targets[1]['pose'],
      'planner_query_before_lift':int(scene.planner_query_count),'single_lift_plan_limit':1}

def verify_certificate(value,expected_binding):
    payload=copy.deepcopy(value);claimed=payload.pop('receipt_sha256',None)
    if digest(payload)!=claimed or value.get('schema_version')!=VERSION:raise ValueError('F2 certificate selfhash/schema')
    if value.get('binding')!=expected_binding:raise ValueError('stale scene/joint/world/config/target certificate')
    b=value['binding']
    if not b['scene_instance_id'] or not b['job_namespace'] or not b['gpu_uuid'] or b['planner_query_before_lift']!=2 or b['single_lift_plan_limit']!=1:raise ValueError('F2 single-plan scope invalid')
    if not np.allclose(np.asarray(b['lift_target_pose'])-b['grasp_target_pose'],[0,0,.12,0,0,0,0],rtol=0,atol=1e-12):raise ValueError('original12cm lift changed')
    return True

def capture_native_grasp(scene,export,can,base,binding):
    from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
    from controlled_multi_future.runtime_v2_contracts import PROVISIONAL_RUNTIME_THRESHOLDS as thresholds
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    def vertices(shape):
        T=matrix(base)@matrix(shape['solver_pose']);return np.asarray(shape['vertices'])@T[:3,:3].T+T[:3,3]
    tables=[s for s in export['shapes'] if s['role']=='table']
    table=max(tables,key=lambda s:np.ptp(vertices(s),axis=0)[:2].prod())
    if table['name']!='table__0':raise ValueError('F2 reviewed tabletop identity changed')
    tv=vertices(table);z=float(tv[:,2].max());hull=ConvexHull(tv[abs(tv[:,2]-z)<1e-5,:2])
    native=np.concatenate([vertices(s) for s in can]);gap=float(native[:,2].min()-z)
    inside=bool(np.all(native[:,:2]@hull.equations[:,:2].T+hull.equations[:,2]<=1e-6))
    rows=scene.trace[-50:];actor=can[0]['actor_name'];selected=set(scene.selected_gripper_links())
    from controlled_multi_future.high_level_physical_runner_v1 import _complete_contact_signal
    complete=True;identity=True;physical=[];table_contact=[];relative=[];linear=[];angular=[];velocity=[]
    for row in rows:
        identity &= row.get('selected_contact_actor_name')==actor
        complete &= _complete_contact_signal(row)
        selected_hit=False;table_hit=False
        for pair in row['contact_pairs']:
            names={pair['body_a'],pair['body_b']}
            if actor not in names:continue
            if not (names&selected or 'table' in names):continue
            result=classify_contact_pair_physical_hit_v8(pair);complete &= result['evidence_complete']
            if names&selected:selected_hit |= result['physical_hit_for_gate']
            if 'table' in names:table_hit |= result['physical_hit_for_gate']
        physical.append(selected_hit);table_contact.append(table_hit)
        relative.append(np.linalg.inv(matrix(row['eef']))@matrix(row['role_actor_poses']['main_can']))
        linear.append(float(np.linalg.norm(row['role_actor_linear_velocities']['main_can'])))
        angular.append(float(np.linalg.norm(row['role_actor_angular_velocities']['main_can'])))
        velocity.append({'primary_linear_measured':bool(row['role_actor_linear_velocity_measured']['main_can']),
          'primary_angular_measured':bool(row['role_actor_angular_velocity_measured']['main_can']),
          'component_linear_measured':bool(row['role_actor_component_linear_velocity_measured']['main_can']),
          'component_angular_measured':bool(row['role_actor_component_angular_velocity_measured']['main_can']),
          'component_linear':np.asarray(row['role_actor_component_linear_velocities']['main_can']).tolist(),
          'component_angular':np.asarray(row['role_actor_component_angular_velocities']['main_can']).tolist()})
    if len(rows)!=50:raise ValueError('F2 model eligibility requires the recorded50-frame postclose window')
    translation=max(float(np.linalg.norm(r[:3,3]-relative[0][:3,3])) for r in relative)
    q0=t3d.quaternions.mat2quat(relative[0][:3,:3]);rotation=max(float(2*np.arccos(np.clip(abs(np.dot(q0,t3d.quaternions.mat2quat(r[:3,:3]))),0,1))) for r in relative)
    checks={'native_not_penetrating':gap>=-EPS,'footprint_inside_actual_table':inside,'actual_grasp_identity_complete':bool(identity and complete),
      'physical_selected_contact_fraction':float(np.mean(physical))>=thresholds['motion_min_contact_fraction'],
      'grasp_translation_stable':translation<=.005,'grasp_rotation_stable':rotation<=.05,
      'linear_stable':max(linear)<=thresholds['stable_linear_speed_mps'],'angular_stable':max(angular)<=thresholds['eef_stationary_angular_speed_rps'],
      'native_component_velocity_evidence_complete':all(v['component_linear_measured'] and v['component_angular_measured'] and np.isfinite(v['component_linear']+v['component_angular']).all() for v in velocity)}
    result={'schema_version':VERSION,'checks':checks,'pass':all(checks.values()),'table_shape_name':table['name'],'table_top_z_m':z,
      'native_gap_m':gap,'native_min_z_m':float(native[:,2].min()),'positive_gap_upper_bound':None,'negative_numeric_bound_m':-EPS,
      'actual_table_contact_frames':sum(table_contact),'table_contact_required':False,'selected_physical_contact_frames':sum(physical),
      'grasp_translation_drift_m':translation,'grasp_rotation_drift_rad':rotation,'rows_sha256':digest([physical_row(row) for row in rows]),
      'binding':binding,'selected_links':sorted(selected),'selected_contact_semantics':'OR over original selected assembly links, unchanged fraction threshold, stricter actual V8 physical evidence; not F3 both-finger rule',
      'primary_velocity_semantics':'unchanged original pose-derived velocity stability; native component velocities additionally recorded, not substituted',
      'velocity_evidence':velocity,
      'world_geometry_sha256':digest(export['shapes']),'can_geometry_sha256':digest(can),'native_vertex_sha256':digest(native.tolist()),
      'native_world_vertices':native.tolist(),
      'physical_Gates_changed':False,'F3_witness_used':False}
    result['receipt_sha256']=digest(result);return result

def negative_pairs(spheres,links,export):
    """All negative sphere/world pairs, not just one minimum per obstacle."""
    import trimesh
    spheres=np.asarray(spheres);valid=spheres[:,3]>0;rows=[]
    if len(links)!=len(spheres) or not np.isfinite(spheres).all():raise ValueError('actual sphere/link layout invalid')
    for shape in export['shapes']:
        mesh=trimesh.Trimesh(vertices=shape['vertices'],faces=shape['faces'],process=True);mesh.apply_transform(matrix(shape['solver_pose']))
        distance=-trimesh.proximity.signed_distance(mesh,spheres[valid,:3])-spheres[valid,3]
        for local in np.flatnonzero(distance<0):
            index=int(np.flatnonzero(valid)[local]);rows.append({'sphere_index':index,'link':links[index],'obstacle':shape['name'],'clearance_m':float(distance[local])})
    return rows

def choose_mode(witness,full_checks,actual_overlaps,expected_binding):
    verify_certificate(witness,expected_binding)
    if set(full_checks)!={'motion_gen','motion_gen_batch'}:raise ValueError('both actual full models required')
    if not witness['pass']:raise ValueError('fresh native/grasp model eligibility failed')
    valid=[full_checks[k]['valid'] is True for k in ('motion_gen','motion_gen_batch')]
    if all(valid):return 'FULL_WORLD'
    if any(valid):raise ValueError('single/batch full-model disagreement')
    for name,row in full_checks.items():
        if 'INVALID_START_STATE_WORLD_COLLISION' not in str(row['status']):raise ValueError('not a pure full-world start rejection')
        audit=actual_overlaps[name]
        if audit['sphere_source']!='CURRENT_FRESHLY_FITTED_MODEL_KINEMATICS' or not audit['negative_pairs']:raise ValueError('fresh actual overlap evidence missing')
        payload=copy.deepcopy(audit);claimed=payload.pop('receipt_sha256',None)
        if digest(payload)!=claimed or audit.get('binding')!=expected_binding or audit.get('model_instance_id')!=row.get('model_instance_id'):raise ValueError('actual full-model overlap binding changed')
        if any(p['link']!='attached_can' or p['obstacle']!='table__0' for p in audit['negative_pairs']):raise ValueError('negative pair outside F2 can/table scope')
    return 'F2_CAN_TABLE_PADDING_UPWARD_ONLY'

def escape_gate(world_vertices,witness):
    v=np.asarray(world_vertices)
    if v.ndim!=3 or len(v)<2 or v.shape[-1]!=3 or not np.isfinite(v).all():raise ValueError('missing actual native plan samples')
    bottom=v[:,:,2].min(axis=1)
    checks={'not_deeper_than_actual_start':bool(bottom.min()>=witness['native_min_z_m']-EPS),
      'start_native_pose_bound':bool(v[0].shape==np.asarray(witness['native_world_vertices']).shape and np.max(abs(v[0]-witness['native_world_vertices']))<=EPS),
      'non_descending':bool(np.all(np.diff(bottom)>=-EPS)),'end_off_table':bool(bottom[-1]>witness['table_top_z_m']+EPS)}
    return {'pass':all(checks.values()),'checks':checks,'samples':len(v),'minimum_z_m':float(bottom.min()),'last_z_m':float(bottom[-1]),'physical_success':False}
