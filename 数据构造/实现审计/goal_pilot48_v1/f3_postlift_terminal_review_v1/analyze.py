"""Independent CPU drift/contact timeline for final-recipe failure and004."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');D=Path('/nfs_share/lijunhui/Robotwin2/datasets');O=Path(__file__).parent
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rotation(p):return R.from_quat(np.asarray(p)[..., [4,5,6,3]])
def audit(job):
    root=D/job;terminal=json.loads((root/'goal_terminal.json').read_text(encoding='utf-8'));gate=terminal['runtime_result']['result']['post_lift'];receipt=gate['lift_execution_receipt'];base=receipt['start_trace_row'];end=receipt['end_trace_row']
    with np.load(root/'physical_trace.npz',allow_pickle=False) as z:t={k:z[k] for k in z.files}
    actor=t['object_pose'];eef=t['eef_pose'];ar=rotation(actor);er=rotation(eef);rel=er.inv().apply(actor[:,:3]-eef[:,:3]);rr=er.inv()*ar
    drift=np.linalg.norm(rel-rel[base],axis=1);angles=(rr[base].inv()*rr).magnitude();rise=actor[:,2]-actor[base,2]
    mass=json.loads((root/'actual_mass_properties.json').read_text(encoding='utf-8'));com=ar.apply(np.broadcast_to(mass['cmass_local_pose'][:3],(len(actor),3)))+actor[:,:3]
    timelines=[]
    for i in range(base-249,end+51):
        groups={}
        for p in json.loads(str(t['contact_pairs_json'][i])):
            if 'f3_main_bottle' not in (p['body_a'],p['body_b']):continue
            if not classify_contact_pair_physical_hit_v8(p)['physical_hit_for_gate']:continue
            other=p['body_b'] if p['body_a']=='f3_main_bottle' else p['body_a'];groups.setdefault(other,[]).extend([v for v in p['point_evidence'] if v['impulse_norm']>0])
        contacts={}
        for name,pts in groups.items():
            w=np.array([v['impulse_norm'] for v in pts]);total=w.sum()
            if total<=0:contacts[name]={'physical_hit':True,'impulse_norm_sum':0};continue
            w/=total;point=w@np.array([v['position'] for v in pts]);normal=w@np.array([v['normal'] for v in pts])
            contacts[name]={'physical_hit':True,'points':len(pts),'impulse_norm_sum':float(total),'weighted_point_world':point.tolist(),
                'contact_z_minus_COM_z_m':float(point[2]-com[i,2]),'weighted_normal_world':normal.tolist()}
        timelines.append({'row':i,'time_from_lift_start_s':float(t['timestamp'][i]-t['timestamp'][base]),
            'phase':'supported_hold' if i<=base else 'lift' if i<=end else 'confirmation',
            'drift_m':float(drift[i]),'angular_drift_rad':float(angles[i]),'origin_rise_m':float(rise[i]),
            'eef_rise_m':float(eef[i,2]-eef[base,2]),'COM_rise_m':float(com[i,2]-com[base,2]),
            'qpos_fingers':t['realized_left_gripper_joint_qpos'][i].tolist(),'drive_targets':t['left_gripper_joint_drive_target'][i].tolist(),
            'actor_angular_velocity':t['object_component_angular_velocity'][i].tolist(),'contacts':contacts})
    hold_base=base-249;hold_d=np.linalg.norm(rel[hold_base:base+1]-rel[hold_base],axis=1);hold_r=(rr[hold_base].inv()*rr[hold_base:base+1]).magnitude()
    def first(v,threshold):
        hits=np.flatnonzero(v[base+1:end+51]>threshold);return None if len(hits)==0 else int(base+1+hits[0])
    confirm=rise[end+1:end+51]
    rowmap={r['row']:r for r in timelines};phase_stats={}
    for phase in ('supported_hold','lift','confirmation'):
        rows=[r for r in timelines if r['phase']==phase]
        phase_stats[phase]={'rows':len(rows),'contact_frame_counts':{n:sum(n in r['contacts'] for r in rows) for n in ('fl_link7','fl_link8','f3_original_pad','table')},
            'max_drift_m':max(r['drift_m'] for r in rows),'max_angular_drift_rad':max(r['angular_drift_rad'] for r in rows)}
    out={'job':job,'base_row':base,'lift_end_row':end,'trace_sha256':sha(root/'physical_trace.npz'),'terminal_receipt':terminal['receipt_sha256'],
        'original_gate':gate,'phase_stats':phase_stats,'supported_hold_relative_drift_m':float(hold_d.max()),'supported_hold_relative_angle_rad':float(hold_r.max()),
        'first_translation_above5mm_row':first(drift,.005),'first_angle_above0_05rad_row':first(angles,.05),
        'confirmation_rise_first_m':float(confirm[0]),'confirmation_rise_last_m':float(confirm[-1]),'confirmation_rise_min_m':float(confirm.min()),
        'confirmation_rise_negative_differences':int((np.diff(confirm)<0).sum()),'confirmation_drift_increase_m':float(drift[end+50]-drift[end+1]),
        'confirmation_angle_increase_rad':float(angles[end+50]-angles[end+1]),
        'world_rotation_vector_lift_start_to_final':(ar[end+50]*ar[base].inv()).as_rotvec().tolist(),
        'boundary_rows':[rowmap[i] for i in (base,end,end+1,end+30,end+50)],'timeline':timelines}
    assert abs(max(drift[base+1:end+51])-gate['maximum_relative_translation_drift_m'])<1e-12
    assert abs(max(angles[base+1:end+51])-gate['maximum_relative_orientation_drift_rad'])<1e-10
    return out
def main():
    results=[audit(j) for j in ('p48_f3_micro_004','p48_f3_one_sided_micro_001')]
    conf=json.loads((D/'p48_f3_one_sided_micro_001/escape_model_conformance.json').read_text(encoding='utf-8'))
    value={'schema_version':'p48_f3_final_recipe_postlift_terminal_review_v1','results':results,'actual_model_branch':conf['branch'],
        'new_one_sided_branch_GPU_validated_by_this_job':False,'stability_recipe_revision_limit':3,'fourth_recipe_authorized':False,
        'automatic_retry_or_failure_class_reset_authorized':False,'new_GPU':False,'old_data_modified':False}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();write_new(O/'analysis.json',value)
    for r in results:print(json.dumps({k:v for k,v in r.items() if k not in ('timeline','boundary_rows','original_gate')}))
    print('receipt',value['receipt_sha256'])
if __name__=='__main__':main()
