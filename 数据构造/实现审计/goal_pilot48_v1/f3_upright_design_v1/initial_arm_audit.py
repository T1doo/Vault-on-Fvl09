"""Known initial-state native16-arm-link check; not fabricated target IK."""
import json,sys
from pathlib import Path
import numpy as np
from .geometry import Geometry,A,D,matrix,collision
from kinematics_cpu import link_world,JOINTS
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def main():
    g=Geometry();trace=D/'p48_f3_one_sided_micro_001/physical_trace.npz'
    with np.load(trace,allow_pickle=False) as z:q=z['joint_qpos'][0]
    names=json.loads(g.model_path.read_text(encoding='utf-8'))['actual_joint_names'];named=dict(zip(names,q))
    base=json.loads((D/'f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json').read_text(encoding='utf-8'))['solver_base_binding']['base_link_world_pose']
    robot=[]
    for side in ('fl','fr'):
        for i in range(1,9):
            name=side+'_link'+str(i)
            for shape,local in g.arm_shapes[i]:robot.append((shape,link_world(name,named,base)@local,name))
    self_hits=[];world_hits=[];checked=0
    for i,(a,Ta,na) in enumerate(robot):
        for b,Tb,nb in robot[i+1:]:
            if JOINTS.get(na) is not None and JOINTS[na].find('parent').get('link')==nb:continue
            if JOINTS.get(nb) is not None and JOINTS[nb].find('parent').get('link')==na:continue
            checked+=1
            if collision(a,Ta,b,Tb):self_hits.append([na,nb])
        for b,Tb,name,role in g.world:
            if collision(a,Ta,b,Tb):world_hits.append([na,name])
        for b,Tb,name in g.bottles:
            if collision(a,Ta,b,g.B@Tb):world_hits.append([na,name])
    value={'self_hits':self_hits,'world_hits':world_hits,'checked_nonadjacent_arm_pairs':checked,'initial_known_joint_state':q.tolist(),
        'pass':not self_hits and not world_hits,'coverage':'16 links fl/fr1..8, nonadjacent pairs, table/pad/upright bottle; base/wheels not captured',
        'target_full_arm_IK_states_available':False,'target_or_path_native_pass_claimed':False,'GPU':False}
    write_new(Path(__file__).parent/'initial_arm_audit.json',value);print(json.dumps({k:v for k,v in value.items() if k!='initial_known_joint_state'}))
if __name__=='__main__':main()
