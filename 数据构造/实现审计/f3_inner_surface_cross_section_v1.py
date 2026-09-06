"""Inner-facing triangle contact at one identical bottle Y cross-section."""
import copy,json,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
import trimesh
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';D=W/'Robotwin2/datasets'
sys.path.insert(0,str(A/'f3_model_replay_v1'));sys.path.insert(1,str(A))
from replay import hand_shapes,matrix,link_world
from realization_utf8_io_v1 import write_new
def mesh(s,T):
    m=trimesh.Trimesh(vertices=s['vertices'],faces=s['faces'],process=True);m.apply_transform(T);return m
def section_inner_points(m,y,direction):
    points=[]
    for tri,normal in zip(m.triangles,m.face_normals):
        if normal[0]*direction<.8:continue
        ends=[]
        for i,j in ((0,1),(1,2),(2,0)):
            a,b=tri[i],tri[j]
            if abs(a[1]-y)<1e-9:ends.append(a)
            if (a[1]-y)*(b[1]-y)<0:ends.append(a+(b-a)*((y-a[1])/(b[1]-a[1])))
        if len(ends)>=2:points.extend(ends+[np.mean(ends,axis=0)])
    return np.array(points)
def run():
    proposals=json.loads((A/'F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json').read_text(encoding='utf-8'))['proposals'];saved=json.loads((D/'f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'));base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))['solver_base_binding']['base_link_world_pose'];B=matrix(base);results=[]
    for prop in proposals:
        root=D/'f3_zero_scene_solver_replay_v1'/prop['parent_recipe_id'];state=json.loads((root/'planned_grasp_endpoint.json').read_text(encoding='utf-8'))['state'];world=json.loads((root/'planned_grasp_endpoint.geometry.json').read_text(encoding='utf-8'))['shapes'];bottles=[mesh(s,B@matrix(s['solver_pose'])) for s in world if s['role']=='bottle'];desired=matrix(prop['desired_actual_flange_world_pose']);old=link_world('fl_link6',state['named_qpos'],base);rows=[];station=None
        for fraction in (0.,.25,.5,.75,1.):
            st=copy.deepcopy(state)
            for k in ('fl_joint7','fl_joint8'):st['named_qpos'][k]=(1-fraction)*state['named_qpos'][k]+fraction*.0175
            fingers={s['role']:mesh(s,desired@np.linalg.inv(old)@B@matrix(s['solver_pose'])) for s in hand_shapes(saved,st,base) if s['role'] in ('fl_link7','fl_link8')}
            centers={k:m.bounds.mean(0) for k,m in fingers.items()}
            if station is None:station=float(np.mean([x[1] for x in centers.values()]))
            out={}
            for k,m in fingers.items():
                other='fl_link8' if k=='fl_link7' else 'fl_link7';direction=float(np.sign(centers[other][0]-centers[k][0]));points=section_inner_points(m,station,direction)
                if len(points):
                    signed=np.max(np.stack([trimesh.proximity.signed_distance(b,points) for b in bottles]),axis=0);contact=points[signed>=-1e-5]
                else:signed=np.array([]);contact=np.empty((0,3))
                out[k]={'closing_direction_x':direction,'inner_normal_alignment_min':.8,'sample_points':len(points),'max_signed_bottle_distance_m':None if not len(signed) else float(signed.max()),'contact_witness_points':contact.tolist(),'inner_surface_reaches_cross_section':len(contact)>0}
            rows.append({'closure_fraction':fraction,'same_table_y_cross_section_m':station,'fingers':out,'both_inner_faces_reach_same_section':all(r['inner_surface_reaches_cross_section'] for r in out.values())})
        results.append({'proposal_id':prop['proposal_id'],'rows':rows,'necessary_inner_surface_gate_pass':any(r['both_inner_faces_reach_same_section'] for r in rows),'sampled_necessary_condition_not_force_closure':True})
    value={'schema_version':'cmf_f3_topdown_inner_surface_same_section_v1','results':results,'IK_queries':0,'scenes':0,'physical_attempts':0};write_new(A/'F3_TOPDOWN_INNER_SURFACE_SAME_SECTION_V1_20260906.json',value);print(json.dumps([{k:r[k] for k in ('proposal_id','necessary_inner_surface_gate_pass')} for r in results]))
if __name__=='__main__':run()
