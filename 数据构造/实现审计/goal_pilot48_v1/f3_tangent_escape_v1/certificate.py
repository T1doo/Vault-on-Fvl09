"""Independent tangent-unloading model certificate; old supported gate unchanged."""
import hashlib,json,copy
import numpy as np
SCHEMA='stable_grasp_native_tangent_unloading_escape_v1'
def seal(value):
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    value=canonical_jsonable(value)
    return {**value,'certificate_sha256':hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()}
def validate(c):
    try:
        payload=dict(c);h=payload.pop('certificate_sha256')
        if seal(payload)['certificate_sha256']!=h:return False
        hold=c['hold'];g=np.asarray(c['native_gap_per_hold_frame_m'],dtype=float);pairs=c['overlap_pairs']
        steps=np.asarray(c['hold_step_indices'],dtype=float);times=np.asarray(c['hold_timestamps'],dtype=float)
        from support_pair_collision_v1.policy import verify_support_witness
        old=c['old_supported_witness']
        poses=np.asarray([c['actual_actor_pose'],c['actual_eef_pose']],dtype=float)
        if old['hold']!=hold or old['pairs']!=pairs or verify_support_witness(old):return False
        return bool(c['schema_version']==SCHEMA and c['old_supported_hold_pass'] is False and
            isinstance(c['scene_id'],str) and c['scene_id'] and isinstance(c['plan_id'],str) and c['plan_id'] and
            isinstance(c['job_namespace'],str) and c['job_namespace'] and poses.shape==(2,7) and np.isfinite(poses).all() and
            len(c['actual_joint_names'])==len(c['actual_qpos'])>0 and len(set(c['actual_joint_names']))==len(c['actual_joint_names']) and np.isfinite(c['actual_qpos']).all() and
            all(isinstance(c[k],str) and len(c[k])==64 and all(x in '0123456789abcdef' for x in c[k]) for k in ('trace_window_sha256','world_sha256','robot_config_sha256','native_geometry_sha256')) and
            steps.shape==(250,) and times.shape==(250,) and np.isfinite(steps).all() and np.isfinite(times).all() and (np.diff(steps)==1).all() and np.allclose(np.diff(times),.004,rtol=0,atol=1e-9) and
            c['pad_actor_name']==hold['support_actor_name'] and c['pad_shape_name']=='pad__0' and
            hold['frames']==250 and hold['all_both_fingers'] is True and hold['all_selected_contact'] is True and hold['all_signal_complete'] is True and
            hold['forbidden_count']==0 and 0<hold['support_contact_frames']<250 and c['table_contact_frames']==0 and c['other_support_contact_frames']==0 and
            0<=hold['max_relative_translation_drift_m']<=.005 and 0<=hold['max_relative_orientation_drift_rad']<=.05 and
            g.shape==(250,) and np.isfinite(g).all() and (np.abs(g)<=.0001).all() and
            len(pairs)>0 and all(p['link']=='attached_bottle' and p['obstacle']=='pad__0' and np.isfinite(p['clearance_m']) and p['clearance_m']<0 for p in pairs) and
            set(c['full_model_checks'])=={'motion_gen','motion_gen_batch'} and all(v['valid'] is False and v['status']=='MotionGenStatus.INVALID_START_STATE_WORLD_COLLISION' for v in c['full_model_checks'].values()) and
            c['target_delta_world_m']==[0.,0.,.025] and c['target_orientation_unchanged'] is True)
    except (KeyError,ValueError,TypeError):return False

class SinglePlanLease:
    """One scene, one frozen plan; shared across single/batch checker instances."""
    def __init__(self,certificate):
        if not validate(certificate):raise ValueError('invalid tangent certificate, never old supported witness')
        self.certificate=copy.deepcopy(certificate);self.state='conformance';self.plan_calls=0
    def check(self):
        if self.state not in ('conformance','planning') or not validate(self.certificate):raise RuntimeError('tangent certificate invalidated')
    def begin_plan(self,scene_id,plan_id,world_sha256):
        self.check();c=self.certificate
        if self.state!='conformance' or self.plan_calls or (scene_id,plan_id,world_sha256)!=(c['scene_id'],c['plan_id'],c['world_sha256']):
            raise RuntimeError('tangent certificate scene/plan/world mismatch or reuse')
        self.plan_calls=1;self.state='planning'
    def invalidate(self):self.state='expired'
