"""One uniform box scale derived before any proposed geometry evaluation."""
import itertools
import numpy as np
from goal_pilot48_v1.f2_inside_preinsert_failure_review_v1.analyze import context,hand_parts,root_transform,matrix,pose
from .geometry import minimum_interval_feasible_scale,first_vertical_contact,ray_height

FLOORS={4,5,7,9,12,13,14}
def body_vertices(shape):
    T=matrix(shape['shape_local_pose']);return np.asarray(shape['vertices'])@T[:3,:3].T+T[:3,3]
def world_vertices(shape,base):
    T=matrix(base)@matrix(shape['solver_pose']);return np.asarray(shape['vertices'])@T[:3,:3].T+T[:3,3]

def derive():
    c=context();cert=c['certificate'];m=c['model'];B=matrix(c['box']);R=B[:3,:3];C=matrix(c['can']);K=R.T@C[:3,:3];center=np.asarray(cert['can_native_center_m']);half=np.asarray(cert['can_native_half_extents_m'])
    lower=np.asarray(cert['unchanged_strict_lower_m']);upper=np.asarray(cert['unchanged_strict_upper_m']);mid=(lower+upper)/2;rawlo=lower-.005;rawhi=upper+.005;rawhalf=(rawhi-rawlo)/2
    corners=np.asarray([half*np.asarray(sign) for sign in itertools.product((-1,1),repeat=3)])@K.T
    can_H=float(np.ptp(corners[:,1]));floor_shapes=[s for s in cert['box_shapes'] if int(s['name'].split('__')[1]) in FLOORS];box_all=np.concatenate([body_vertices(s) for s in cert['box_shapes']]);floor_all=np.concatenate([body_vertices(s) for s in floor_shapes]);floor_max=float(floor_all[:,1].max());rim_max=float(box_all[:,1].max())
    height_scale=(can_H+.005)/(rawhi[1]-floor_max)
    can_parts=[]
    for s in cert['can_shapes']:can_parts.append((s['name'],(body_vertices(s)-center)@K.T,s['faces']))
    # Reorder box coordinates X,Y,Z to X,Z,Y for the vertical-ray helper.
    floor_at_center=max(ray_height(body_vertices(s)[:,[0,2,1]],s['faces'],mid[[0,2]],highest=True) for s in floor_shapes if _ray_possible(body_vertices(s)[:,[0,2,1]],mid[[0,2]]))
    can_bottom_center=min(ray_height(v[:,[0,2,1]],f,[0.,0.],highest=False) for _,v,f in can_parts if _ray_possible(v[:,[0,2,1]],[0.,0.]))
    hand_bounds=[];A=np.linalg.inv(np.asarray(m['T_solver_eef_can']));intervals=[];mandatory=[1.,height_scale]
    for axis in (0,2):mandatory.append((max(abs(corners[:,axis]))+.005)/rawhalf[axis])
    def bound(label,lo,hi,*,always=False):
        side=max((max(abs(lo[axis]),abs(hi[axis]))+.005)/rawhalf[axis] for axis in (0,2))
        entry=(lo[1]-can_bottom_center)/(rim_max-floor_at_center)
        hand_bounds.append({'label':label,'relative_box_lower':lo.tolist(),'relative_box_upper':hi.tolist(),'side_fit_sufficient_scale':float(side),
          'below_rim_entry_scale_lower_bound':float(entry),'whole_piece_fit_is_sufficient_not_acceptance_rule':True})
        if always:mandatory.append(side)
        elif entry<side:intervals.append((float(entry),float(side),label))
    for link,s,T in hand_parts(c,np.eye(4)):
        T=A@T;v=(np.asarray(s['vertices'])@T[:3,:3].T+T[:3,3]-center)@K.T;bound('native_'+link,v.min(0),v.max(0))
    for link in ('fl_link6','fl_link7','fl_link8','attached_can'):
        T=A if link=='attached_can' else A@np.linalg.inv(c['rootE'])@root_transform(link,c['named'])
        for i,sphere in enumerate(c['kin']['collision_spheres'][link]):
            p=K@(T[:3,:3]@np.asarray(sphere['center'])+T[:3,3]-center);radius=sphere['radius']+c['kin']['collision_sphere_buffer'];bound(link+'_sphere_'+str(i),p-radius,p+radius,always=link=='attached_can')
    factor,active=minimum_interval_feasible_scale(max(mandatory),intervals)
    # A single X compensation keeps the original right edge, no position grid.
    old_world=box_all@R.T+B[:3,3];scaled_relative=(box_all*factor)@R.T;newB=B.copy();newB[0,3]=old_world[:,0].max()-scaled_relative[:,0].max()
    table=next(s for s in m['world']['shapes'] if s['name']=='table__0');tv=world_vertices(table,m['base']);newB[2,3]=tv[:,2].max()-scaled_relative[:,2].min()
    newbox=[(s['name'],(body_vertices(s)*factor)@R.T+newB[:3,3],s['faces']) for s in cert['box_shapes']]
    targetcenter=newB[:3,3]+R@np.array([factor*mid[0],0.,factor*mid[2]]);target=C.copy();target[:3,3]=targetcenter-C[:3,:3]@center
    moving=[]
    for s in cert['can_shapes']:moving.append((s['name'],body_vertices(s)@target[:3,:3].T+target[:3,3],s['faces']))
    floorworld=[s for s in newbox if int(s[0].split('__')[1]) in FLOORS];contact=first_vertical_contact(moving,floorworld);target[2,3]+=contact['vertical_translation_m']
    finalcenter=target[:3,:3]@center+target[:3,3];bc=R.T@(finalcenter-newB[:3,3]);finalcorners=corners+bc
    newlower=rawlo*factor+.005;newupper=rawhi*factor-.005
    can_checks={'X_sides':bool(finalcorners[:,0].min()>=newlower[0] and finalcorners[:,0].max()<=newupper[0]),
      'Z_sides':bool(finalcorners[:,2].min()>=newlower[2] and finalcorners[:,2].max()<=newupper[2]),'top':bool(finalcorners[:,1].max()<=newupper[1])}
    bbox=np.concatenate([v for _,v,_ in newbox]);others={}
    for role in ('scale','stand'):
        v=np.concatenate([world_vertices(s,m['base']) for s in m['world']['shapes'] if s['role']==role]);sep=np.maximum(v.min(0)-bbox.max(0),bbox.min(0)-v.max(0));others[role]={'aabb_disjoint':bool(sep.max()>0),'axis_gaps':sep.tolist()}
    return dict(context=c,box_pieces=newbox,box_pose=newB,can_target=target,can_parts=can_parts,
      report={'uniform_factor':factor,'old_asset_scale':.1,'new_asset_scale':.1*factor,'scale_candidates_evaluated':1,
        'height_sufficient_bound_factor':float(height_scale),'mandatory_sufficient_bound_factor':float(max(mandatory)),
        'hand_below_rim_interval_constraints':hand_bounds,'active_interval_bounds':active,'native_upright_envelope_height_m':can_H,
        'old_raw_cavity_top_m':float(rawhi[1]),'old_highest_native_floor_m':floor_max,'new_box_actor_pose':pose(newB),
        'box_translation_world_m':(newB[:3,3]-B[:3,3]).tolist(),'old_right_edge_m':float(old_world[:,0].max()),'new_box_world_bounds':[bbox.min(0).tolist(),bbox.max(0).tolist()],
        'table_xy_footprint_pass':bool(np.all(bbox.min(0)[:2]>=tv.min(0)[:2]) and np.all(bbox.max(0)[:2]<=tv.max(0)[:2])),
        'other_facility_separation':others,'can_actor_target':pose(target),'native_vertical_contact_construction':contact,'can_five_boundaries':can_checks,
        'actual_top_margin_beyond_unchanged5mm_m':float(newupper[1]-finalcorners[:,1].max()),
        'scientific_verifier_or_Gate_changed':False,'new_current_and_three_relation_qualification_required':True,'physical_or_IK_qualification_proven':False})

def _ray_possible(v,xy):
    return bool(np.all(np.asarray(xy)>=v[:,:2].min(0)-1e-12) and np.all(np.asarray(xy)<=v[:,:2].max(0)+1e-12))

if __name__=='__main__':
    r=derive()['report'];print({k:v for k,v in r.items() if k!='hand_below_rim_interval_constraints'})
