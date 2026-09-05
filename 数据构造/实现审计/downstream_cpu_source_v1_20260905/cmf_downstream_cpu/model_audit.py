"""Read-only same-evidence F3 collision-model and F2 target audit; no solver calls."""
import ast,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import yaml
from .io import sha,seal,write_new

W=Path('/nfs_share/lijunhui');P=W/'Robotwin2/project/RoboTwin';A=W/'Vault-on-Fvl09/数据构造/实现审计'
def read(p):return json.loads(Path(p).read_text())

def audit():
    model_dir=P/'assets/embodiments/aloha-agilex';cfg_path=model_dir/'curobo_left.yml';config_path=model_dir/'config.yml'
    cfg=yaml.safe_load(cfg_path.read_text());robot=yaml.safe_load(config_path.read_text());kin=cfg['robot_cfg']['kinematics']
    sphere_path=Path(kin['collision_spheres']);spheres=yaml.safe_load(sphere_path.read_text())['collision_spheres']
    urdf_path=Path(kin['urdf_path']);urdf=ET.parse(urdf_path).getroot();joints={j.attrib['name']:j for j in urdf.findall('joint')}
    planner_path=P/'envs/robot/planner.py';source=planner_path.read_text();tree=ast.parse(source)
    world=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='world_config' for t in n.targets))
    cuboid=world.values[0];world_names=[ast.literal_eval(k) for k in cuboid.keys]
    updates=[]
    for folder in (P/'controlled_multi_future',P/'envs/robot'):
        for p in folder.rglob('*.py'):
            if 'update_world(' in p.read_text():updates.append(str(p))
    traces=[];Q=[6,14,18,22,26,30]
    root=W/'Robotwin2/datasets/cmf_f3_micro_authorized_v1_1'
    for index in (0,2):
        receipt_path=root/str(index)/'physical/scene_receipt.json';receipt=read(receipt_path);path=receipt_path.parent/'physical_trace.npz'
        if sha(path)!=receipt['trace']['sha256']:raise ValueError('sealed F3 trace changed')
        with np.load(path,allow_pickle=False) as z:
            q=z['joint_qpos'];commands=z['controller_effective_setpoint'];eef=z['eef_pose'];obj=z['object_pose'];step=z['step_index']
        stages=[]
        for window in receipt['result']['windows']:
            start,end=window['start_exclusive'],window['end_inclusive'];errors=np.max(np.abs(q[start+1:end+1,Q]-commands[start+1:end+1,:6]),axis=1)
            above=np.flatnonzero(errors>.10);first=window['first_failure']
            stages.append({'stage':window['stage'],'window_start':start,'window_end':end,'stage_gate_pass':window['pass'],'first_gate_failure':first,
              'endpoint_measurements':window['endpoint_receipt']['measurements'],'maximum_bottle_displacement_m':window['maximum_bottle_displacement_m'],
              'command_vs_realized_qpos_max_rad':float(errors.max()),'first_command_tracking_error_gt_existing_0p10_rad_diagnostic_only':None if not len(above) else int(start+1+above[0]),
              'first_failure_qpos':None if first is None else q[first['row_index'],Q].tolist(),
              'first_failure_eef_pose':None if first is None else eef[first['row_index']].tolist(),
              'first_failure_bottle_pose':None if first is None else obj[first['row_index']].tolist()})
        traces.append({'candidate_index':index,'trace_path':str(path),'trace_sha256':sha(path),'recipe_sha256':receipt['recipe_sha256'],
            'full_qpos_width':int(q.shape[1]),'action_width':int(commands.shape[1]),'step_indices_contiguous':bool(np.all(np.diff(step)==1)),'stages':stages})
    sections=[
      {'order':1,'topic':'joint-name/qpos order','configured_arm_names':robot['arm_joints_name'][0],'planner_cspace_names':kin['cspace']['joint_names'],
       'six_arm_names_match':robot['arm_joints_name'][0]==kin['cspace']['joint_names'][:6],'URDF_names_exist':all(n in joints for n in robot['arm_joints_name'][0]),
       'trace_selected_indices':Q,'limitation':'Uses source-validated 38-D index mapping; current trace lacks serialized full joint-name enumeration.'},
      {'order':2,'topic':'base/world frame','robot_pose_config':robot['robot_pose'],'planner_frame_bias':cfg['planner']['frame_bias'],
       'aloha_left_extra_z_rotation_rad':-.02,'source_transform':'Rz(-0.02) @ T(frame_bias) @ inverse(robot_origin) @ world_goal',
       'limitation':'Static mapping checked; no new runtime base-pose capture or simulator FK execution.'},
      {'order':3,'topic':'EEF/tool frame','planner_ee_link':kin['ee_link'],'robot_move_group':robot['move_group'][0],
       'names_match':kin['ee_link']==robot['move_group'][0],'gripper_bias':robot['gripper_bias'],'reported_ee_translation_offset_m':robot['gripper_bias']-.12,
       'global_trans_matrix':robot['global_trans_matrix'],'delta_matrix':robot['delta_matrix']},
      {'order':4,'topic':'collision sphere/mesh coverage','sphere_counts':{k:len(v) for k,v in spheres.items()},'collision_link_names':kin['collision_link_names'],
       'mesh_link_names':kin['mesh_link_names'],'sphere_buffer_m':kin['collision_sphere_buffer'],'exact_mesh_envelope_coverage_proven':False},
      {'order':5,'topic':'self collision ignore pairs','pairs':kin['self_collision_ignore'],
       'old_fl_link4_fl_link6_pair_ignored':('fl_link6' in kin['self_collision_ignore'].get('fl_link4',[]) or 'fl_link4' in kin['self_collision_ignore'].get('fl_link6',[])),
       'no_new_self_collision_ignore_change':True},
      {'order':6,'topic':'table/pad world geometry','planner_world_obstacles':world_names,'planner_table_dims':[.7,2.,.04],
       'physics_table_source_dimensions':{'length':1.2,'width':.7,'thickness':.05},'planner_table_pose_expression':ast.get_source_segment(source,world),
       'pad_in_planner_world':False,'bottle_in_planner_world':False,'controlled_source_update_world_calls':updates,
       'finding':'The active CuRobo world initializer contains only table; the witnessed pad and bottle interactions are not represented as world objects in this path.',
       'limitation':'Table extents are in different frames; do not claim a numerical world-space discrepancy without transform reconciliation.'},
      {'order':7,'topic':'opposite arm coverage','right_arm_links_in_left_collision_model':[x for x in kin['collision_link_names'] if x.startswith('fr_')],
       'dual_arm_physics':robot['dual_arm'],'causal_for_current_two_failures_proven':False},
      {'order':8,'topic':'commanded/realized divergence on same failed traces','trace_audits':traces,
       'full_window_gate_is_post_segment_review_not_per_step_emergency_stop':True}]
    f2root=W/'Robotwin2/datasets/cmf_f2_bounded_transit_v1';terminal=read(f2root/'job_terminal.json');matrix=[]
    for scene in terminal['scene_receipts']:
        for test in (scene['result'] or {}).get('tests',[]):
            first=next((s for s in test['segment_receipts'] if s['planner_status']!='Success'),None)
            seg=first or test['segment_receipts'][-1]
            matrix.append({'test_id':test['test_id'],'pass':test['pass'],'target_pose':seg['goal_eef_pose'],'starting_qpos':test['segment_receipts'][0]['start_qpos'],
                'first_failed_segment':None if first is None else first['segment_id'],'MotionGen':seg['planner_query_receipt'].get('motiongen_result_side_channel'),
                'query_before':test['before'],'query_after':test['after'],'query_delta':test['delta'],'cleanup_pass':scene['cleanup']['cleanup_safety_pass']})
    child={j.find('child').attrib['link']:j for j in urdf.findall('joint')};link=kin['ee_link'];segments=[]
    while link!=kin['base_link']:
        joint=child[link];origin=joint.find('origin');v=np.array([float(x) for x in origin.attrib.get('xyz','0 0 0').split()]);segments.append(float(np.linalg.norm(v)));link=joint.find('parent').attrib['link']
    poses=read(A/'F2_BOUNDED_TRANSIT_SPEC_20260905_V1.json')['poses'];distances={}
    for name,p in poses.items():
        v=np.array([p[1]+.65,-p[0],p[2]])+np.array(cfg['planner']['frame_bias']);distances[name]=float(np.linalg.norm(v))
    evidence_files=[cfg_path,config_path,sphere_path,urdf_path,planner_path,P/'envs/robot/robot.py',P/'envs/_base_task.py',f2root/'job_terminal.json']
    return seal({'schema_version':'cmf_same_evidence_model_target_cpu_audit_v1','F3_ordered_sections':sections,'F2_failure_matrix':matrix,
       'F2_target_distance_from_configured_planner_base_m':distances,'URDF_translation_length_sum_loose_upper_bound_m':sum(segments),
       'F2_geometric_infeasibility_proven':False,'F2_findings':'D0 passes; U/D and all three transit first goals fail IK. Prioritize fixed placement/grasp-transform workspace analysis, not another arbitrary hub sweep.',
       'source_files':{str(p):sha(p) for p in evidence_files},'new_GPU_calls':0,'new_planner_queries':0,'new_scene_creations':0,
       'candidate_substitution':False,'threshold_changes':False,'actual_model_repair_or_physical_validation_performed':False})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=audit();write_new(a.output,result)
    print(json.dumps({'receipt_sha256':result['receipt_sha256'],'F3_sections':8,'F2_matrix_rows':len(result['F2_failure_matrix']),'GPU_used':False}))
