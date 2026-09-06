"""CPU trace-only load-transfer diagnostic, no simulator imports."""
import json, sys, hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计')
D=Path(sys.argv[1])
sys.path.insert(0,str(A))
from realization_utf8_io_v1 import write_new
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rot(p): return R.from_quat(np.asarray(p)[..., [4,5,6,3]])
def main():
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:
        t={k:z[k] for k in z.files}
    poses=t['object_pose']; eef=t['eef_pose']; er=rot(eef); br=rot(poses)
    rel=er.inv().apply(poses[:,:3]-eef[:,:3]); relrot=er.inv()*br
    base=json.loads((D/'goal_terminal.json').read_text())['runtime_result']['result']['post_lift']['lift_execution_receipt']['start_trace_row']
    drift=np.linalg.norm(rel-rel[base],axis=1)
    angle=(relrot[base].inv()*relrot).magnitude()
    shapes=json.loads((D/'postclose_attached_model.json').read_text())['native_bottle_shapes']
    vertices=np.concatenate([rot(s['shape_local_pose']).apply(s['vertices'])+np.asarray(s['shape_local_pose'][:3]) for s in shapes])
    center=(vertices.max(0)+vertices.min(0))/2
    centerworld=br.apply(np.broadcast_to(center,(len(poses),3)))+poses[:,:3]
    rows=[]
    for i in range(base-249,len(poses)):
        pairs=[p for p in json.loads(str(t['contact_pairs_json'][i])) if 'f3_main_bottle' in (p['body_a'],p['body_b'])]
        groups={}
        for p in pairs:
            other=p['body_b'] if p['body_a']=='f3_main_bottle' else p['body_a']
            points=[v for v in p['point_evidence'] if v['impulse_norm']>1e-9 or v['signed_separation_m']<=0]
            for v in points:
                local=br[i].inv().apply(np.asarray(v['position'])-poses[i,:3])
                groups.setdefault(other,[]).append({
                    'position_world':v['position'],'position_bottle_local':local.tolist(),
                    'normal_world':v['normal'],'impulse_vector_recorded':v['impulse_vector'],
                    'impulse_norm':v['impulse_norm'],'separation_m':v['signed_separation_m']})
        stats={}
        for other, pts in groups.items():
            imp=np.array([p['impulse_norm'] for p in pts]); w=imp/(imp.sum() or 1)
            stats[other]={'physical_points':len(pts),'impulse_norm_sum':float(imp.sum()),
                'weighted_position_world':(w@np.array([p['position_world'] for p in pts])).tolist(),
                'weighted_position_bottle_local':(w@np.array([p['position_bottle_local'] for p in pts])).tolist(),
                'weighted_normal_world':(w@np.array([p['normal_world'] for p in pts])).tolist(),
                'points':pts}
        rows.append({'row':i,'time_since_lift_s':float(t['timestamp'][i]-t['timestamp'][base]),
            'bottle_rise_m':float(poses[i,2]-poses[base,2]),
            'eef_rise_m':float(eef[i,2]-eef[base,2]),
            'relative_translation_m':float(drift[i]),'relative_rotation_rad':float(angle[i]),
            'bottle_geometry_center_world':centerworld[i].tolist(),
            'gripper_joint_qpos':t['realized_left_gripper_joint_qpos'][i].tolist(),
            'gripper_drive_target':t['left_gripper_joint_drive_target'][i].tolist(),
            'bottle_velocity':t['object_component_linear_velocity'][i].tolist(),
            'bottle_angular_velocity':t['object_component_angular_velocity'][i].tolist(),
            'contacts':stats})
    def first(pred):
        return next((r['row'] for r in rows if r['row']>base and pred(r)),None)
    out={'schema_version':'p48_f3_slip_trace_audit_v1','source_trace_sha256':sha(D/'physical_trace.npz'),
        'source_terminal_sha256':sha(D/'goal_terminal.json'),'base_row':base,
        'actual_COM_recorded':False,'geometry_center_not_COM':center.tolist(),
        'geometry_bounds_actor_local':[vertices.min(0).tolist(),vertices.max(0).tolist()],
        'first_no_physical_pad_contact_row':first(lambda r:'f3_original_pad' not in r['contacts']),
        'first_drift_1mm_row':first(lambda r:r['relative_translation_m']>.001),
        'first_drift_5mm_row':first(lambda r:r['relative_translation_m']>.005),
        'first_orientation_0_05rad_row':first(lambda r:r['relative_rotation_rad']>.05),
        'rows':rows,'gpu_execution':False,'thresholds_modified':False,
        'impulse_sign_caveat':'Recorded per-point vectors retained; not interpreted as signed force on bottle without body-order API convention validation.'}
    out['receipt_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write_new(Path(__file__).parent/(D.name+'.json'),out)
    print({k:v for k,v in out.items() if k!='rows'})
    for i in (base,base+10,base+60,base+111,len(poses)-1):
        r=next(r for r in rows if r['row']==i)
        print({k:v for k,v in r.items() if k!='contacts'})
        print({k:{a:b for a,b in v.items() if a!='points'} for k,v in r['contacts'].items()})
if __name__=='__main__':main()

