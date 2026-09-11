"""F1 independent physical/stage verifier. Only frozen formal thresholds apply."""
import hashlib,json
from pathlib import Path
import numpy as np
STAGES=('post_prefix_hold','target_pregrasp','target_grasp','gripper_close','target_lift_mid','target_lift','carry_hub_low','carry_hub_high','safe_horizontal','preplace','release','gripper_open','release_settle','retreat','rest','rest_settle')


def contract_for_f1(spec):
    t=spec['terminal_tolerances']
    return {'version':'f1_formal_physical_v2','frame':'world/table-fixed; box geometry in actor local frame; wxyz quaternions',
        'threshold_source':'canonical D6.6-D6.7 Stage2 frozen spec; no provisional fallback',
        'non_task':{'phase':'all N+1 states relative to original t0','position_m':t['non_task_position_m'],'orientation_rad':t['non_task_orientation_rad']},
        'terminal':{'phase':'last stable_window_frames inside rest_settle after release/retreat','stable_window_frames':50,'object_linear_m_s':t['non_task_linear_speed_m_s'],'object_angular_rad_s':t['non_task_angular_speed_rad_s'],'eef_position_m':t['eef_position_m'],'eef_orientation_rad':t['eef_orientation_rad'],'eef_linear_m_s':.01,'eef_angular_rad_s':.05},
        'grasp_identity':{'phase':'gripper_close through target_lift','signal':'physical selected-finger/selected-actor contact; selected_contact_actor_name matches candidate'},
        'release':{'phase':'post release final stable window','closed_master_m':-.01,'open_master_m':.045,'actual_open_fraction_gt':.8,'source':'aloha-agilex/config.yml gripper_scale and existing open fraction; applied to measured master qpos','separation_rule':'no physical contact with any robot link'},
        'support':{'phase':'final stable window','physical_hit':'impulse>1e-10 or signed_separation<=0 with complete v2 shape/point evidence','normal_rule':'abs(world_z) dominant normal component','plane_rule':'point and subject bottom inside true cavity support band','geometry_source':'PLASTICBOX_BASE3_CAVITY support_surface_band_local_y_m'},
        'stages':list(STAGES),'sample_rate_hz':250,'executing_arm':'left',
        'path':{'stage':'safe_horizontal','offset_y_m':spec['variant_rules']['r_inv_path']['safe_horizontal_y_offset_m'],'minimum_realized_change_m':.001,'comparison':'same program baseline, prescribed transport endpoint only'},
        'motion':{'stage':'post_prefix_hold','additional_frames':spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames'],'comparison':'same constant effective command at registered post-prefix location; same frozen non-hold targets/controls'}}


def frozen_contract(spec):
    c=spec['f1_verifier_contract']
    if c!=contract_for_f1(spec):raise ValueError('formal F1 verifier contract differs from frozen applicable signal rules')
    return c


def pose_rates(poses,timestamps,start_state,end_state):
    """Rates at states start..end from each preceding saved pose, never API fallback."""
    from controlled_multi_future.geometry import quaternion_orientation_error
    poses=np.asarray(poses,float);timestamps=np.asarray(timestamps,float)
    if poses.ndim!=2 or poses.shape[1]!=7 or len(poses)!=len(timestamps) or not 1<=start_state<=end_state<len(poses):raise ValueError('invalid saved-pose velocity interval')
    dt=np.diff(timestamps[start_state-1:end_state+1])
    if not np.isfinite(dt).all() or np.any(dt<=0):raise ValueError('invalid physical timestamps')
    window=poses[start_state-1:end_state+1]
    linear=np.linalg.norm(np.diff(window[:,:3],axis=0),axis=1)/dt
    angular=np.array([quaternion_orientation_error(a[3:],b[3:]) for a,b in zip(window[:-1],window[1:])])/dt
    if not np.isfinite(linear).all() or not np.isfinite(angular).all():raise ValueError('nonfinite saved-pose velocity')
    return linear,angular


def load_stages(raw,manifest,spec,suffix,controls):
    c=frozen_contract(spec);e=manifest['provenance']['formal_f1_stages'];stages=e['stages'];n=len(raw['stream__controller_effective_setpoint'])
    if manifest['provenance']['formal_f1_contract']!=c:raise ValueError('collector declared different frozen F1 verifier contract')
    if [v['name'] for v in stages]!=c['stages']:raise ValueError('missing/reordered actual phase record')
    if e['executing_arm']!=c['executing_arm'] or e['sample_rate_hz']!=c['sample_rate_hz'] or e['program_id']!=manifest['provenance']['program_id']:raise ValueError('stage arm/rate/program changed')
    if e['realization_id']!=manifest['provenance']['realization_spec']['realization']:raise ValueError('stage realization changed')
    previous=e['prefix_acceptance_end_row']
    if type(previous)is not int or previous<1:raise ValueError('prefix boundary missing')
    by={};checks={}
    for stage in stages:
        start,end=stage['start_row'],stage['end_row']
        if type(start)is not int or type(end)is not int or start!=previous or not start<=end<=n:raise ValueError('phase rows not contiguous/in bounds')
        if end==start and stage['name']!='post_prefix_hold':raise ValueError('required phase never executed')
        by[stage['name']]=stage;previous=end
    if previous!=n:raise ValueError('unaccounted tail actions')
    timestamps=np.asarray(raw['stream__state_timestamps'])
    checks['250Hz']=len(timestamps)==n+1 and np.allclose(np.diff(timestamps),1/c['sample_rate_hz'],rtol=0,atol=1e-9)
    actual=np.asarray(raw['stream__controller_effective_setpoint']);requested=np.asarray(raw['stream__requested_command'])
    hold=by[c['motion']['stage']];a,b=hold['start_row'],hold['end_row']
    wanted=c['motion']['additional_frames'] if e['realization_id']=='r_inv_motion' else 0
    checks['registered_hold_length']=b-a==wanted
    checks['registered_hold_commands']=bool(np.array_equal(actual[a:b],np.repeat(actual[a-1:a],b-a,axis=0)) and np.array_equal(requested[a:b],np.repeat(requested[a-1:a],b-a,axis=0)))
    if b>a:
        hold_linear,hold_angular=pose_rates(raw['stream__realized_eef'][:,:7],timestamps,a+1,b)
        checks['hold_is_stationary']=bool(np.max(hold_linear)<=c['terminal']['eef_linear_m_s'] and np.max(hold_angular)<=c['terminal']['eef_angular_rad_s'])
    else:checks['hold_is_stationary']=True
    fixed_dimensions=list(range(6,12))+list(range(18,24))+[25]
    boundary=e['prefix_acceptance_end_row'];fixed=actual[:,fixed_dimensions]
    checks['right_arm_unchanged']=np.array_equal(fixed[boundary:],np.repeat(fixed[boundary-1:boundary],n-boundary,axis=0))
    for i,target in enumerate(suffix['execution_spec']['targets']):
        stage=by[target['segment_id']];a,b=stage['start_row'],stage['end_row'];position=controls[f'segment_{i:03d}_position'];velocity=controls[f'segment_{i:03d}_velocity']
        checks['actual_control:'+target['segment_id']]=np.array_equal(actual[a:b,:6],position.astype(actual.dtype)) and np.array_equal(actual[a:b,12:18],velocity.astype(actual.dtype))
    baseline=np.asarray(suffix['execution_spec']['formal_path_baseline_pose'],float).copy()
    expected_offset=c['path']['offset_y_m'] if e['realization_id']=='r_inv_path' else 0.0
    baseline[1]+=expected_offset
    goal=next(t['pose'] for t in suffix['execution_spec']['targets'] if t['segment_id']==c['path']['stage'])
    checks['prescribed_transport_target']=suffix['execution_spec']['formal_path_prescribed_offset_y_m']==expected_offset and np.array_equal(baseline,np.asarray(goal))
    checks['release_settle_length']=by['release_settle']['end_row']-by['release_settle']['start_row']==75
    checks['rest_settle_length']=by['rest_settle']['end_row']-by['rest_settle']['start_row']==75
    return e,by,checks


def physical_pair(pair):
    from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
    result=classify_contact_pair_physical_hit_v8(pair)
    return result['evidence_complete'],result['physical_hit_for_gate']


def supporting(pair,box_pose,subject_pose,half_size,band):
    from controlled_multi_future.geometry import obb_corners
    from scipy.spatial.transform import Rotation
    complete,hit=physical_pair(pair)
    if not complete or not hit:return False
    # geometry uses wxyz; scipy takes xyzw.
    r=Rotation.from_quat(np.r_[box_pose[4:],box_pose[3]]).as_matrix()
    corners=obb_corners(subject_pose,half_size)
    local=(corners-box_pose[:3])@r
    if not band[0]-1e-9<=float(local[:,1].min())<=band[1]+1e-9:return False
    for point in pair['point_evidence']:
        normal=np.asarray(point['normal'],float);position=np.asarray(point['position'],float)
        if normal.shape!=(3,) or position.shape!=(3,) or not np.isfinite(normal).all() or not np.isfinite(position).all():continue
        local_point=(position-box_pose[:3])@r
        if abs(normal[2])>0 and abs(normal[2])>=max(abs(normal[0]),abs(normal[1])) and band[0]-1e-9<=local_point[1]<=band[1]+1e-9:return True
    return False


def verify_f1_disk(*,raw_dir,spec,program):
    from controlled_multi_future.verifiers import verify_true_cavity_obb
    from controlled_multi_future.geometry import quaternion_orientation_error
    from controlled_multi_future.runtime_v2_contracts import PLASTICBOX_BASE3_CAVITY
    raw_dir=Path(raw_dir);checks={};evidence={}
    try:
        c=frozen_contract(spec);t=c['terminal'];role=program['target_role'];role_spec=next(r for r in spec['roles'] if r['role']==role)
        root=raw_dir.parent.parent.parent;folder=root/'suffix_artifacts'/program['program_id']
        suffix=json.loads((folder/'frozen_suffix_artifact.json').read_text(encoding='utf-8'));manifest=json.loads((raw_dir/'manifest.json').read_text(encoding='utf-8'))
        rest=np.asarray(suffix['execution_spec']['targets'][-1]['pose']);window=t['stable_window_frames']
        if suffix['execution_spec']['targets'][-1]['segment_id']!='rest':raise ValueError('frozen rest target missing')
        with np.load(raw_dir/'raw_streams.npz',allow_pickle=False) as z,np.load(folder/'suffix_controls.npz',allow_pickle=False) as controls:
            stages,by,stage_checks=load_stages(z,manifest,spec,suffix,controls);checks.update(stage_checks)
            mapping=manifest['provenance']['audit_role_mapping']
            checks['subject_identity']=mapping['target_role']==role and mapping['target_role_pose_field']=='role_object_pose__'+role and stages['subject_actor_name']=='formal_f1_'+role
            selected=z['audit__role_object_pose__'+role];box=z['audit__role_object_pose__common_box'];half=np.asarray(role_spec['size'])/2
            checks['true_inside']=verify_true_cavity_obb(selected[-1],half,box[-1],PLASTICBOX_BASE3_CAVITY)['pass_true_cavity_obb']
            checks['stable_window_present']=by['rest_settle']['end_row']-by['rest_settle']['start_row']>=window
            first_state,last_state=len(selected)-window,len(selected)-1
            object_linear,object_angular=pose_rates(selected,z['stream__state_timestamps'],first_state,last_state)
            checks['stable_linear']=np.max(object_linear)<=t['object_linear_m_s']
            checks['stable_angular']=np.max(object_angular)<=t['object_angular_rad_s']
            contacts=[json.loads(str(row)) for row in z['audit__contact_pairs_json'][-window:]];subject=stages['subject_actor_name'];robot_links=set(stages['robot_link_names'])
            fingers=set(stages['gripper_link_names'])
            if not fingers or not fingers<=robot_links or stages['gripper_scale_m']!=[c['release']['closed_master_m'],c['release']['open_master_m']]:raise ValueError('physical gripper identity/calibration evidence missing')
            ga,gb=by['gripper_close']['start_row'],by['target_lift']['end_row']
            checks['grasp_subject_contact_identity']=all(str(x)==subject for x in z['audit__selected_contact_actor_name'][ga+1:gb+1])
            grasp_pairs=[json.loads(str(row)) for row in z['audit__contact_pairs_json'][ga+1:gb+1]]
            checks['actual_selected_finger_grasp']=any(subject in (p['body_a'],p['body_b']) and bool({p['body_a'],p['body_b']}&fingers) and physical_pair(p)==(True,True) for row in grasp_pairs for p in row)
            if not robot_links:raise ValueError('actual robot-link registry missing')
            relevant=[p for rows in (contacts,grasp_pairs) for row in rows for p in row if subject in (p['body_a'],p['body_b']) and bool({p['body_a'],p['body_b']}&(robot_links|{'formal_f1_common_box'}))]
            checks['physical_contact_evidence_complete']=all(physical_pair(p)[0] for p in relevant)
            support_points=[point for row in contacts for pair in row if {pair['body_a'],pair['body_b']}=={subject,'formal_f1_common_box'} for point in pair['point_evidence']]
            checks['support_geometric_signals_available']=all(np.asarray(p.get(k),float).shape==(3,) and np.isfinite(np.asarray(p.get(k),float)).all() for p in support_points for k in ('normal','position'))
            support=[];detached=[]
            for i,pairs in enumerate(contacts):
                support.append(any({p['body_a'],p['body_b']}=={subject,'formal_f1_common_box'} and supporting(p,box[-window+i],selected[-window+i],half,PLASTICBOX_BASE3_CAVITY['support_surface_band_local_y_m']) for p in pairs))
                touching=[p for p in pairs if subject in (p['body_a'],p['body_b']) and bool({p['body_a'],p['body_b']}&robot_links)]
                detached.append(all(physical_pair(p)==(True,False) for p in touching))
            checks['continuous_box_support_contact']=bool(support) and all(support)
            checks['released_from_robot']=bool(detached) and all(detached)
            q=np.asarray(z['audit__realized_left_gripper_joint_qpos'][-window:,0]);fraction=(q-c['release']['closed_master_m'])/(c['release']['open_master_m']-c['release']['closed_master_m'])
            checks['actual_gripper_open']=bool(np.isfinite(fraction).all() and np.min(fraction)>c['release']['actual_open_fraction_gt'])
            eef=np.asarray(z['stream__realized_eef'])[:,:7];eef_window=eef[-window:]
            eef_linear,eef_angular=pose_rates(eef,z['stream__state_timestamps'],first_state,last_state)
            checks['rest_position']=float(np.max(np.linalg.norm(eef_window[:,:3]-rest[:3],axis=1)))<=t['eef_position_m']
            checks['rest_orientation']=max(quaternion_orientation_error(q[3:],rest[3:]) for q in eef_window)<=t['eef_orientation_rad']
            checks['eef_linear_stationary']=np.max(eef_linear)<=t['eef_linear_m_s']
            checks['eef_angular_stationary']=np.max(eef_angular)<=t['eef_angular_rad_s']
            for r in spec['roles']:
                if r['role']==role:continue
                poses=z['audit__role_object_pose__'+r['role']];delta=float(np.max(np.linalg.norm(poses[:,:3]-poses[0,:3],axis=-1)))
                checks['unchanged:'+r['role']]=delta<=c['non_task']['position_m'] and max(quaternion_orientation_error(p[3:],poses[0,3:]) for p in poses)<=c['non_task']['orientation_rad']
                evidence[r['role']+'_max_displacement_m']=delta
            evidence.update(velocity_source='independent difference of saved world pose/wxyz quaternion and state_timestamps; no stored zero-velocity fallback',object_linear_max_m_s=float(np.max(object_linear)),object_angular_max_rad_s=float(np.max(object_angular)),eef_linear_max_m_s=float(np.max(eef_linear)),eef_angular_max_rad_s=float(np.max(eef_angular)),actual_open_fraction_min=float(np.min(fraction)),stable_rows=[len(selected)-window,len(selected)-1],stage_ranges=by)
    except (KeyError,OSError,ValueError,TypeError,StopIteration,IndexError) as exc:
        return {'pass':False,'checks':{k:bool(v) for k,v in checks.items()},'error':str(exc),'runner_pass_used':False}
    return {'pass':all(checks.values()),'checks':{k:bool(v) for k,v in checks.items()},'runner_pass_used':False,'applied_contract':c,'evidence':evidence}


def verify_variant_pair(*,baseline_dir,variant_dir,spec,realization):
    c=frozen_contract(spec)
    def read(folder):
        folder=Path(folder);m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));e=m['provenance']['formal_f1_stages'];by={x['name']:x for x in e['stages']}
        with np.load(folder/'raw_streams.npz',allow_pickle=False) as z:return m,by,{k:z[k].copy() for k in ('stream__controller_effective_setpoint','stream__realized_eef')}
    try:
        bm,bs,b=read(baseline_dir);vm,vs,v=read(variant_dir);checks={'same_intent':bm['provenance']['program_id']==vm['provenance']['program_id'],'baseline_realization':bm['provenance']['realization_spec']['realization']=='r_pc','variant_realization':vm['provenance']['realization_spec']['realization']==realization}
        if realization=='r_inv_motion':
            source = vm.get('provenance', {}).get('motion_control_source')
            if vm.get('provenance', {}).get('synthetic') is not True:
                checks['motion_control_source_bound'] = isinstance(source, dict) and source.get('planner_invoked') is False and source.get('baseline_realization') == 'r_pc' and source.get('baseline_program_id') == bm.get('provenance', {}).get('program_id')
            checks['prescribed_extra_hold']=(vs['post_prefix_hold']['end_row']-vs['post_prefix_hold']['start_row'])-(bs['post_prefix_hold']['end_row']-bs['post_prefix_hold']['start_row'])==c['motion']['additional_frames']
            for name in STAGES[1:]:
                a,bend=bs[name]['start_row'],bs[name]['end_row'];x,y=vs[name]['start_row'],vs[name]['end_row']
                checks['same_non_hold_controls:'+name]=np.array_equal(b['stream__controller_effective_setpoint'][a:bend],v['stream__controller_effective_setpoint'][x:y])
        elif realization=='r_inv_path':
            name=c['path']['stage'];delta=float(v['stream__realized_eef'][vs[name]['end_row'],1]-b['stream__realized_eef'][bs[name]['end_row'],1])
            checks['prescribed_transport_changed']=delta*c['path']['offset_y_m']>0 and abs(delta)>=c['path']['minimum_realized_change_m']
        else:raise ValueError('not an invariance realization')
        return {'pass':all(checks.values()),'checks':checks,'applied_contract':c[('motion' if realization=='r_inv_motion' else 'path')]}
    except (KeyError,OSError,ValueError,TypeError,IndexError) as exc:return {'pass':False,'error':str(exc)}
