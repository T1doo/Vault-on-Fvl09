"""Literal saved attachment sphere/pad overlap, not a CUDA checker run."""
import json,sys,hashlib
from pathlib import Path
import numpy as np,trimesh
from scipy.spatial.transform import Rotation as R
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_micro_006')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def main():
    mp=D/'postclose_attached_model.json';m=json.loads(mp.read_text(encoding='utf-8'));k=m['robot_config']['kinematics']
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:e=z['eef_pose'][-1];p=z['role_object_pose__original_pad'][-1]
    spheres=k['collision_spheres']['attached_bottle'];c=R.from_quat(e[[4,5,6,3]]).apply([s['center'] for s in spheres])+e[:3];buffer=k['collision_sphere_buffer'];rad=np.array([s['radius'] for s in spheres])+buffer
    sp=D.parent/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json';s=next(s for s in json.loads(sp.read_text(encoding='utf-8'))['shapes'] if s['role']=='pad')
    assert s['shape_local_pose']==[0.,0.,0.,1.,0.,0.,0.]
    v=R.from_quat(p[[4,5,6,3]]).apply(s['vertices'])+p[:3];mesh=trimesh.Trimesh(vertices=v,faces=s['faces'],process=True);gap=-trimesh.proximity.signed_distance(mesh,c)-rad
    out={'schema_version':'p48_f3_006_literal_saved_attachment_pad_overlap_v1','sphere_buffer_m_unchanged':buffer,
        'negative_spheres':int((gap<0).sum()),'minimum_clearance_m':float(gap.min()),
        'without_buffer_diagnostic_only_negative_count':int((gap+buffer<0).sum()),
        'overlaps':[{'sphere_index':int(i),'clearance_m':float(gap[i])} for i in np.flatnonzero(gap<0)],
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [mp,sp,D/'physical_trace.npz']},
        'full_GPU_model_validity_not_measured':True,'world_from_flange_uses_actual_saved_EEF':True,'new_GPU':False}
    out['receipt_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();write_new(O/'sphere_overlap.json',out);print(json.dumps(out))
if __name__=='__main__':main()
