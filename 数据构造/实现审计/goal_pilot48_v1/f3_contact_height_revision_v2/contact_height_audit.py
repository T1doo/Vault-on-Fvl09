"""Quantify candidate inner-face heights against COM in the exact CPU world."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;A=O.parents[1];D=Path('/nfs_share/lijunhui/Robotwin2/datasets')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    worldpath=D/'f3_zero_scene_solver_replay_v1/f3-final-pose-v3-r3063/planned_grasp_endpoint.geometry.json'
    world=json.loads(worldpath.read_text());shape=next(s for s in world['shapes'] if s['role']=='bottle')
    masspath=D/'p48_f3_micro_002/actual_mass_properties.json';m=json.loads(masspath.read_text())
    p=np.asarray(shape['actor_world_pose']);com=R.from_quat(p[[4,5,6,3]]).apply(m['cmass_local_pose'][:3])+p[:3]
    inn=json.loads((O/'inner.json').read_text());rows=[]
    for sample in inn['results'][0]['rows']:
        fingers={}
        for name,v in sample['fingers'].items():
            pts=np.array(v['contact_witness_points']);dz=pts[:,2]-com[2] if pts.size else np.array([])
            fingers[name]={'contact_point_count':len(dz),'above_COM_count':int(np.sum(dz>0)),
                'min_z_minus_COM_z_m':float(dz.min()) if len(dz) else None,
                'max_z_minus_COM_z_m':float(dz.max()) if len(dz) else None}
        rows.append({'closure_fraction':sample['closure_fraction'],'fingers':fingers,
            'both_inner_faces_have_above_COM_candidates':all(v['above_COM_count']>0 for v in fingers.values())})
    out={'schema_version':'p48_f3_revision2_contact_height_candidates_v1','source_bindings':{str(p):sha(p) for p in [worldpath,masspath,O/'recipe.json',O/'inner.json']},
        'COM_world_in_exact_CPU_geometry':com.tolist(),'rows':rows,
        'both_above_COM_candidates_exist':any(r['both_inner_faces_have_above_COM_candidates'] for r in rows),
        'actual_contact_height_verified':False,'sampled_interpenetrating_closure_not_physical_reachability_proof':True,
        'recipe_field_semantics':{'shift_rule':'inherited parent COM station XY translation only',
            'height_preserving_world_shift_m':'inherited parent station delta relative to original topdown, not revision2 total delta',
            'unique_revision_delta_world_m':'revision3 additional [0,0,.002] relative to +10mm height parent',
            'authoritative_execution_poses':['desired_actual_flange_world_pose','desired_pregrasp_world_pose']},
        'total_shift_from_original_topdown_world_m':[1.0825373844530342e-05,.013099995527147372,.012]}
    out['receipt_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    write_new(O/'contact_height_audit.json',out);print(json.dumps(out))
if __name__=='__main__':main()
