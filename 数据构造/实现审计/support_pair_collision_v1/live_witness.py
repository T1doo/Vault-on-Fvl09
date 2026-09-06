"""Fresh supported-hold certificate; no inherited success flag from another run."""
import numpy as np
from controlled_multi_future.geometry import relative_pose
from controlled_multi_future.anchor import quaternion_angular_error
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8

def hold_witness(rows,*,selected_links,bottle_name,pad_name):
    if len(rows)!=250:raise ValueError('exact250-frame hold required')
    selected=set(selected_links);support={'table',pad_name};contact=both=complete=True;forbidden=0;support_count=0;td=[];rd=[]
    initial=relative_pose(rows[0]['eef'],rows[0]['actor_pose'])
    for row in rows:
        touched=set();supported=False;bad=False
        for p in row['contact_pairs']:
            c=classify_contact_pair_physical_hit_v8(p);complete &= c['evidence_complete'] is True
            if not c['physical_hit_for_gate']:continue
            bodies={p['body_a'],p['body_b']};arm={b for b in bodies if b.startswith('fl_')}
            if bottle_name in bodies:touched|=bodies&selected;supported|=bool(bodies&support)
            if len(arm)==2 or (arm and bodies&support) or (bottle_name in bodies and arm and not arm.issubset(selected)):bad=True
        contact &= bool(touched);both &= touched==selected;forbidden+=int(bad);support_count+=int(supported)
        rel=relative_pose(row['eef'],row['actor_pose']);td.append(float(np.linalg.norm(rel[:3]-initial[:3])));rd.append(float(quaternion_angular_error(rel[3:],initial[3:])))
    return {'frames':250,'all_selected_contact':contact,'all_both_fingers':both,'all_signal_complete':complete,'forbidden_count':forbidden,'support_contact_frames':support_count,'max_relative_translation_drift_m':max(td),'max_relative_orientation_drift_rad':max(rd)}

def model_overlap_witness(mg,tensor,export):
    import trimesh
    from geometry import matrix
    spheres=mg.kinematics.get_state(tensor).get_link_spheres().detach().cpu().numpy()[0];cfg=mg.kinematics.kinematics_config
    reverse={v:k for k,v in cfg.link_name_to_idx_map.items()};links=[reverse[int(i)] for i in cfg.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)];valid=spheres[:,3]>0;indices=np.flatnonzero(valid);rows=[]
    for shape in export['shapes']:
        mesh=trimesh.Trimesh(vertices=shape['vertices'],faces=shape['faces'],process=True);mesh.apply_transform(matrix(shape['solver_pose']))
        clearance=-trimesh.proximity.signed_distance(mesh,spheres[valid,:3])-spheres[valid,3]
        for j in np.flatnonzero(clearance<0):rows.append({'link':links[indices[j]],'obstacle':shape['name'],'clearance_m':float(clearance[j])})
    return {'pairs':rows,'only_attached_bottle_support_pairs_overlap':all(p['link']=='attached_bottle' and p['obstacle']=='pad__0' for p in rows)}
