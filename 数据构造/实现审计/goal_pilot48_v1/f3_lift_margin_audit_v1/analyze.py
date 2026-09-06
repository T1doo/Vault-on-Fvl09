"""Independent 004 rise-window/contact audit; no threshold changes or GPU."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_micro_004')
sys.path[:0]=[str(A),str(A/'代码审阅快照'),str(A/'new_recipe_prereqs_v1')]
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    terminal=json.loads((D/'goal_terminal.json').read_text());gate=terminal['runtime_result']['result']['post_lift'];s=gate['lift_execution_receipt']['start_trace_row'];e=gate['lift_execution_receipt']['end_trace_row']
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:
        t={k:z[k] for k in z.files}
    poses=t['object_pose'];eef=t['eef_pose'];mass=json.loads((D/'actual_mass_properties.json').read_text());curve=[]
    for i in range(e+1,e+51):curve.append({'row':i,'rise_m':float(poses[i,2]-poses[s,2]),'eef_rise_m':float(eef[i,2]-eef[s,2])})
    contact=[]
    for i in (s,e,e+1,e+50):
        p=poses[i];com=R.from_quat(p[[4,5,6,3]]).apply(mass['cmass_local_pose'][:3])+p[:3];groups={}
        for pair in json.loads(str(t['contact_pairs_json'][i])):
            if 'f3_main_bottle' not in (pair['body_a'],pair['body_b']):continue
            other=pair['body_b'] if pair['body_a']=='f3_main_bottle' else pair['body_a']
            if other not in ('fl_link7','fl_link8'):continue
            for v in pair['point_evidence']:
                if v['impulse_norm']>1e-9:groups.setdefault(other,[]).append(v)
        fingers={}
        for name,points in groups.items():
            w=np.array([x['impulse_norm'] for x in points]);w/=w.sum();xyz=w@np.array([x['position'] for x in points]);fingers[name]={'weighted_contact_world':xyz.tolist(),'contact_z_minus_COM_z_m':float(xyz[2]-com[2]),'points':len(points),'normal_world':(w@np.array([x['normal'] for x in points])).tolist()}
        contact.append({'row':i,'COMworld':com.tolist(),'fingers':fingers,'finger_qpos':t['realized_left_gripper_joint_qpos'][i].tolist()})
    rise=np.array([r['rise_m'] for r in curve]);goal=eef[s].copy();goal[2]+=.027
    from goal_mapping import cpu_views,roundtrip
    model=json.loads((D/'initial_model_application.json').read_text())
    base=json.loads((Path('/nfs_share/lijunhui/Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json')).read_text())['solver_base_binding']['base_link_world_pose']
    robot,planner=cpu_views(base);mapping=roundtrip(robot,planner,goal)
    out={'schema_version':'p48_f3_004_lift_margin_audit_v1','bindings':{str(p):sha(p) for p in [D/'goal_terminal.json',D/'physical_trace.npz',D/'actual_mass_properties.json']},
        'postclose_baseline_row_unchanged':s,'lift_end_row':e,'confirmation_curve':curve,'contacts':contact,
        'minimum_row':curve[int(rise.argmin())]['row'],'minimum_rise_m':float(rise.min()),'maximum_rise_m':float(rise.max()),
        'last_minus_first_confirmation_rise_m':float(rise[-1]-rise[0]),'negative_differences_count':int((np.diff(rise)<0).sum()),
        'worst_single_frame_decrease_m':float(np.diff(rise).min()),'original_gate_accepted':False,
        'threshold_20mm_unchanged':True,'proposed_actual_goal27mm_from_saved_postclose':goal.tolist(),'original_entry_roundtrip':mapping,
        'new_target_IK_reachability_verified':False,'new_target_native_whole_arm_path_verified':False,
        'requires_fresh_native_lift_escape_on_actual27mm_plan_before_execution':True,
        'unique_revision3_proposal':'25->27mm diagnostic lift only; same recipe/route/close/physics/Gates; then2fresh successes',
        'no_new_GPU_scene_or_physical':True}
    out['receipt_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();write_new(O/'analysis.json',out)
    print(json.dumps({k:v for k,v in out.items() if k not in ('bindings','confirmation_curve','contacts')}));print(json.dumps(contact))
if __name__=='__main__':main()
