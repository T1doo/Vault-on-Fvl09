"""Compare contact line against measured actor-local COM; CPU, one NPZ load/run."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent
D=Path('/nfs_share/lijunhui/Robotwin2/datasets')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    mp=D/'p48_f3_micro_002/actual_mass_properties.json';mass=json.loads(mp.read_text());rows=[]
    for run,summary in [('001',O.parent/'f3_slip_audit_v1/analysis.json'),('002',O/'p48_f3_micro_002.json')]:
        d=json.loads(summary.read_text());base=d['base_row'];record=next(x for x in d['rows'] if x['row']==base)
        tr=D/('p48_f3_micro_'+run)/'physical_trace.npz'
        with np.load(tr,allow_pickle=False) as z:
            p=z['object_pose'];eff=z['estimated_left_gripper_joint_drive_effort'];v=z['realized_left_gripper_joint_qvel']
        rot=R.from_quat(p[base,[4,5,6,3]]);com=rot.apply(mass['cmass_local_pose'][:3])+p[base,:3]
        contacts=record['contacts'];a=np.array(contacts['fl_link7']['weighted_position_world']);b=np.array(contacts['fl_link8']['weighted_position_world']);mid=(a+b)/2
        rows.append({'run':run,'trace_sha256':sha(tr),'base_row':base,'COMworld':com.tolist(),
            'COM_source':'002 measured local COM; same native asset/scale reused for001 comparison',
            'actual_COM_minus_contact_midpoint_m':(com-mid).tolist(),
            'contact_midpoint_world':mid.tolist(),'contact_station_local_y':[contacts[k]['weighted_position_bottle_local'][1] for k in ('fl_link7','fl_link8')],
            'estimated_drive_effort_at_base':eff[base].tolist(),'estimated_drive_effort_at_end':eff[-1].tolist(),
            'estimated_drive_effort_not_measured_contact_force':True,
            'hold250_max_abs_joint_speed':np.max(np.abs(v[base-249:base+1]),axis=0).tolist(),
            'world_rotation_vector_base_to_end':(R.from_quat(p[-1,[4,5,6,3]])*rot.inv()).as_rotvec().tolist()})
    out={'schema_version':'p48_f3_second_slip_comparison_v1','rows':rows,'actual_mass_properties_sha256':sha(mp),
        'actual_mass_properties':mass,'metadata_clarification':{'p48_f3_micro_002.json.actual_COM_recorded':'False is inherited pose-only analyzer field; actual COM was recorded and independently included here. It does not invalidate pose/contact calculations.'},
        'unique_revision2_proposal':{'parent':'f3-r3063-com-station-plus13p1mm-v1','delta_world_z_m':.010,
            'apply_to':['grasp','pregrasp'],'other_parameters_changed':False,'CPU_geometry_passed':False,'GPU_run':False}}
    out['receipt_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write_new(O/'comparison.json',out);print(out['receipt_sha256'])
if __name__=='__main__':main()
