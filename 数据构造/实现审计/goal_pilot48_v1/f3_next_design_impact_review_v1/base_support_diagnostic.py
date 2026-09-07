"""Native base-layer diagnostic only; tolerance layers are not scene trials."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_one_sided_micro_001')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def main():
    source=D/'postclose_attached_model.json';mass=D/'actual_mass_properties.json'
    vertices=np.concatenate([np.asarray(s['vertices']) for s in json.loads(source.read_text(encoding='utf-8'))['native_bottle_shapes']])
    com=np.array(json.loads(mass.read_text(encoding='utf-8'))['cmass_local_pose'])[[0,2]];rows=[]
    for thickness in (1e-6,1e-5,1e-4,1e-3):
        points=np.unique(vertices[vertices[:,1]<=vertices[:,1].min()+thickness][:,[0,2]],axis=0)
        row={'diagnostic_layer_thickness_m':thickness,'vertices':len(points),'width_xz_m':np.ptp(points,axis=0).tolist(),
            'exact_coplanar_support_proven':False}
        if len(points)>=3:
            hull=ConvexHull(points);margin=-(hull.equations[:,:2]@com+hull.equations[:,2]);row.update(projected_COM_in_layer_hull=bool((margin>=0).all()),minimum_layer_hull_margin_m=float(margin.min()))
        rows.append(row)
    value={'schema_version':'f3_upright_base_native_layer_diagnostic_v1','layers':rows,'upright_physical_stability_verified':False,
        'source_files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,mass]},'GPU_executed':False,'physical_or_scene_attempts':0}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();write_new(O/'base_support_diagnostic.json',value);print(value['receipt_sha256'])
if __name__=='__main__':main()
