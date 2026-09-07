"""Bounded read-only bottle13 native section survey for a non-executable proposal."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def main():
    path=D/'p48_f3_one_sided_micro_001/postclose_attached_model.json';data=json.loads(path.read_text(encoding='utf-8'));shapes=data['native_bottle_shapes'];rows=[]
    for station in (.05,.08,.11,.14,.17,.19,.20,.21,.22,.225,.23,.235,.24,.245):
        points=[]
        for s in shapes:
            v=np.asarray(s['vertices']);faces=np.asarray(s['faces'])
            assert s['shape_local_pose']==[0.,0.,0.,1.,0.,0.,0.]
            for triangle in v[faces]:
                for i,j in ((0,1),(1,2),(2,0)):
                    a,b=triangle[i],triangle[j]
                    if abs(a[1]-station)<1e-10:points.append(a)
                    if (a[1]-station)*(b[1]-station)<0:points.append(a+(b-a)*((station-a[1])/(b[1]-a[1])))
        p=np.array(points)
        rows.append({'local_y_m':station,'intersection_points':len(p),'x_width_m':float(np.ptp(p[:,0])) if len(p) else None,
            'z_width_m':float(np.ptp(p[:,2])) if len(p) else None,'max_radius_m':float(np.linalg.norm(p[:,[0,2]],axis=1).max()) if len(p) else None})
    masspath=D/'p48_f3_one_sided_micro_001/actual_mass_properties.json';mass=json.loads(masspath.read_text(encoding='utf-8'))
    value={'schema_version':'f3_next_design_native_bottle13_section_audit_v1','asset_id':13,'scale':[.132]*3,'native_meshes':len(shapes),
        'sections':rows,'actual_local_COM_m':mass['cmass_local_pose'][:3],'mass_kg_unchanged':mass['mass_kg'],
        'source_files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,masspath]},
        'GPU_executed':False,'grasp_proposal_frozen':False,'physical_feasibility_proven':False}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();write_new(O/'geometry_profile.json',value)
    print(json.dumps(rows));print('receipt',value['receipt_sha256'])
if __name__=='__main__':main()
