"""URDF geometry replay; no SAPIEN Scene and no renderer construction."""
import copy,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import transforms3d as t3d
W=Path('/nfs_share/lijunhui');P=W/'Robotwin2/project/RoboTwin'
URDF=P/'assets/embodiments/aloha-agilex/urdf/arx5_description_isaac.urdf'
TREE=ET.parse(URDF).getroot();JOINTS={j.find('child').get('link'):j for j in TREE.findall('joint')}
LEFT=[6,14,18,22,26,30];RIGHT=[7,15,19,23,27,31]

def origin(node):
    o=node.find('origin')
    xyz=np.fromstring(o.get('xyz','0 0 0') if o is not None else '0 0 0',sep=' ')
    angles=np.fromstring(o.get('rpy','0 0 0') if o is not None else '0 0 0',sep=' ')
    return t3d.affines.compose(xyz,t3d.euler.euler2mat(*angles),[1,1,1])

def root_transform(link,q):
    if link not in JOINTS:return np.eye(4)
    j=JOINTS[link];axis=j.find('axis');v=np.fromstring(axis.get('xyz','1 0 0') if axis is not None else '1 0 0',sep=' ');M=np.eye(4)
    if j.get('type') in ('revolute','continuous'):M[:3,:3]=t3d.axangles.axangle2mat(v,float(q.get(j.get('name'),0)))
    elif j.get('type')=='prismatic':M[:3,3]=v*float(q.get(j.get('name'),0))
    return root_transform(j.find('parent').get('link'),q)@origin(j)@M

def link_world(link,q,base_pose):
    B=t3d.affines.compose(base_pose[:3],t3d.quaternions.quat2mat(base_pose[3:]),[1,1,1])
    return B@np.linalg.inv(root_transform('fl_base_link',q))@root_transform(link,q)

def named_state(trace,row):
    q={f'fl_joint{i+1}':float(trace['joint_qpos'][row,j]) for i,j in enumerate(LEFT)}
    q.update({f'fr_joint{i+1}':float(trace['joint_qpos'][row,j]) for i,j in enumerate(RIGHT)})
    for side,prefix in [('left','fl'),('right','fr')]:
        values=trace['realized_'+side+'_gripper_joint_qpos'][row]
        q[prefix+'_joint7']=float(values[0]);q[prefix+'_joint8']=float(values[1])
    return q

def collision_description(link):
    node=TREE.find("link[@name='"+link+"']")
    def normalized(n):return (n.tag,tuple(sorted(n.attrib.items())),tuple(normalized(c) for c in n))
    return [normalized(c) for c in node.findall('collision')]

def verify_recorded_fk():
    f=W/'Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json'
    base=json.loads(f.read_text())['solver_base_binding']['base_link_world_pose'];rows=[]
    for i in (6,7,8):assert collision_description('fl_link'+str(i))==collision_description('fr_link'+str(i))
    for idx in (0,2):
        p=W/'Robotwin2/datasets/cmf_f3_micro_authorized_v1_1'/str(idx)/'physical/physical_trace.npz'
        pos=rot=0.
        with np.load(p,allow_pickle=False) as trace:
            for row in range(len(trace['joint_qpos'])):
                q=named_state(trace,row)
                for prefix,start in [('fl',0),('fr',7)]:
                    T=link_world(prefix+'_link6',q,base);observed=trace['dual_eef_pose'][row,start:start+7]
                    pos=max(pos,float(np.linalg.norm(T[:3,3]-observed[:3])))
                    rot=max(rot,float(np.max(np.abs(T[:3,:3]-t3d.quaternions.quat2mat(observed[3:])))))
            count=len(trace['joint_qpos'])
        assert pos<1e-5 and rot<1e-5
        rows.append({'trace_path':str(p),'states_checked':count,'max_position_error_m':pos,'max_rotation_matrix_error':rot})
    return {'pass':True,'both_arm_URDF_FK_matches_all_recorded_states':rows,'left_right_collision_definitions_equal_for_links_6_7_8':True,'new_scenes':0}

if __name__=='__main__':print(json.dumps(verify_recorded_fk(),sort_keys=True,indent=2))
