"""Existing-trace solver replay with ZERO fresh simulator scenes."""
import copy,json,sys,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import transforms3d as t3d
from kinematics_cpu import W,P,named_state,link_world,collision_description,verify_recorded_fk
A=W/'Vault-on-Fvl09/数据构造/实现审计';B=A/'f2_f3_model_bridge_v1_1'
sys.path.insert(1,str(B));sys.path.insert(2,str(A))
from geometry import matrix,digest,make_world,exact_shape_pairs,closest_pairs
from model_apply import query_state,verify_actual_world_cache
from lock_compat import update_locked_state
from realization_utf8_io_v1 import write_new,load_json

def native_bottle_shapes(model_id,scale):
    """Same native cooking API as ActorBuilder; does not build an entity/scene."""
    import sapien.core as sapien
    from sapien.wrapper.actor_builder import preprocess_mesh_file
    p=P/'assets/objects/001_bottle/collision'/('base'+str(model_id)+'.glb')
    material=sapien.physx.PhysxMaterial(.5,.5,0.)
    shapes=sapien.physx.PhysxCollisionShapeConvexMesh.load_multiple(preprocess_mesh_file(str(p)),scale,material)
    result=[]
    for i,s in enumerate(shapes):
        vertices=np.asarray(s.get_vertices(),dtype=float)*np.asarray(s.get_scale(),dtype=float)
        result.append({'name':'bottle__'+str(i),'role':'bottle','actor_name':'f3_main_bottle','kind':type(s).__name__,
            'vertices':vertices.tolist(),'faces':np.asarray(s.get_triangles(),dtype=int).tolist(),'shape_local_pose':[0,0,0,1,0,0,0],
            'contact_offset':float(s.get_contact_offset()),'rest_offset':float(s.get_rest_offset()),'collision_groups':[1,1,0,0],
            'geometry_origin':'same ActorBuilder native load_multiple API without constructing Scene','source_file':str(p),'source_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    return result

def states_for(index):
    base=W/'Robotwin2/datasets/cmf_f3_micro_authorized_v1_1'/str(index)/'physical'
    rec=load_json(base/'scene_receipt.json')['result'];pre=rec['windows'][0]['end_inclusive'];failure=rec['windows'][1]['first_failure']['row_index'];end=rec['windows'][1]['end_inclusive']
    with np.load(base/'physical_trace.npz',allow_pickle=False) as z:
        fields={k:z[k] for k in ('joint_qpos','realized_left_gripper_joint_qpos','realized_right_gripper_joint_qpos','object_pose','controller_effective_setpoint','dual_eef_pose')}
    moved=np.flatnonzero(np.linalg.norm(fields['object_pose'][:,:3]-fields['object_pose'][0,:3],axis=1)>1e-6);before=max(0,int(moved[0])-1)
    rows=[{'label':label,'trace_row':i,'named_qpos':named_state(fields,i),'bottle_pose':fields['object_pose'][i].tolist()} for label,i in [('initial_clear',0),('pregrasp_endpoint',pre),('first_failure',failure),('before_bottle_motion',before)]]
    q=named_state(fields,0)
    for i in range(6):q['fl_joint'+str(i+1)]=float(fields['controller_effective_setpoint'][end,i])
    rows.append({'label':'planned_grasp_endpoint','trace_row':None,'named_qpos':q,'bottle_pose':fields['object_pose'][0].tolist()})
    return rows

def export_state(saved,bottles,state,base_pose):
    Tbase=matrix(base_pose);out=[];counts={}
    for original in saved['shapes']:
        role=original['role']
        if role=='bottle':continue
        s=copy.deepcopy(original);s.pop('geometry_sha256',None)
        if role.startswith('fr_link'):actor=link_world(role,state['named_qpos'],base_pose)
        else:actor=matrix(s['actor_world_pose'])
        index=counts.get(role,0);counts[role]=index+1;s['name']=role+'__'+str(index)
        T=np.linalg.inv(Tbase)@actor@matrix(s['shape_local_pose']);s['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();s['geometry_sha256']=digest(s);out.append(s)
    for original in bottles:
        s=copy.deepcopy(original);s.pop('geometry_sha256',None);T=np.linalg.inv(Tbase)@matrix(state['bottle_pose'])@matrix(s['shape_local_pose'])
        s['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();s['actor_world_pose']=state['bottle_pose'];s['geometry_sha256']=digest(s);out.append(s)
    return {'schema_version':'cmf_trace_geometry_replay_no_scene_v1','shapes':out,'geometry_sha256':digest(out)}

def hand_shapes(saved,state,base_pose):
    out=[]
    for index in (6,7,8):
        left='fl_link'+str(index);right='fr_link'+str(index)
        assert collision_description(left)==collision_description(right)
        for original in saved['shapes']:
            if original['role']!=right:continue
            s=copy.deepcopy(original);s['name']=s['name'].replace('fr_','fl_');s['role']=left;s['actor_name']=left
            T=np.linalg.inv(matrix(base_pose))@link_world(left,state['named_qpos'],base_pose)@matrix(s['shape_local_pose'])
            s['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();s['geometry_origin']='measured identical right collision geometry, URDF-proven left transform';out.append(s)
    return out

def make_models(cfg,export,old=False):
    from curobo.geom.types import WorldConfig,Cuboid
    from curobo.geom.sdf.world import CollisionCheckerType
    from curobo.wrap.reacher.motion_gen import MotionGenConfig,MotionGen
    world=WorldConfig(cuboid=[Cuboid(name='table',dims=[.7,2,.04],pose=[-.65,0,.74,1,0,0,0])]) if old else make_world(export)
    models={}
    for name in ('motion_gen','motion_gen_batch'):
        kwargs={'interpolation_dt':.004,'num_trajopt_seeds':1,'use_cuda_graph':False,'collision_checker_type':CollisionCheckerType.PRIMITIVE if old else CollisionCheckerType.MESH}
        if not old:kwargs['collision_cache']={'mesh':len(export['shapes']),'obb':1}
        if name=='motion_gen_batch':kwargs['num_graph_seeds']=1
        models[name]=MotionGen(MotionGenConfig.load_from_robot_config(copy.deepcopy(cfg['robot_cfg']),world,**kwargs))
    return models

def run(output):
    import yaml
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    saved=load_json(W/'Robotwin2/datasets/f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json')
    base=load_json(W/'Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json')['solver_base_binding']['base_link_world_pose']
    native13=native_bottle_shapes(13,[s for s in saved['shapes'] if s['role']=='bottle'][0]['shape_scale'])
    old13=[s for s in saved['shapes'] if s['role']=='bottle']
    assert len(native13)==len(old13)
    for actual,previous in zip(native13,old13):
        assert np.array_equal(actual['vertices'],previous['vertices']) and np.array_equal(actual['faces'],previous['faces'])
    binding5=load_json(W/'Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/scene_receipt.json')['scene_binding']
    native5=native_bottle_shapes(5,binding5['runtime_asset']['scale'])
    write_new(output/'native_geometry_equivalence.json',{'asset13_matches_actual_capture_exactly':True,'asset13_shapes':len(native13),'asset5_shapes':len(native5),'new_sapien_scenes':0,'asset5_runtime_binding':binding5['runtime_asset']})
    cfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/curobo_left.yml').read_text());cfg['robot_cfg']['kinematics']['link_names']=['fl_link6','fl_link7','fl_link8']
    old_models=make_models(cfg,None,True);results=[];checks=0
    for index,recipe,bottles in [(0,'f3-final-pose-v3-r3063',native13),(2,'f3-final-pose-v3-r1401',native5)]:
        states=states_for(index);derived=copy.deepcopy(cfg);derived['robot_cfg']['kinematics']['lock_joints']={n:states[0]['named_qpos'][n] for n in cfg['robot_cfg']['kinematics']['lock_joints']}
        models=make_models(derived,export_state(saved,bottles,states[0],base));rows=[]
        for state in states:
            export=export_state(saved,bottles,state,base);world=make_world(export);names=list(state['named_qpos']);q=[state['named_qpos'][n] for n in names];locked={n:state['named_qpos'][n] for n in derived['robot_cfg']['kinematics']['lock_joints']}
            row={'state':state,'models':{},'geometry_sha256':export['geometry_sha256']}
            for name,mg in models.items():
                mg.update_world(world);sync=update_locked_state(mg,locked,derived);cache=verify_actual_world_cache(mg,export)
                checks+=1;write_new(output/'check_ledger'/(str(checks)+'.start.json'),{'recipe':recipe,'state':state['label'],'model':name,'kind':'old'})
                old_result,_=query_state(old_models[name],q,names);write_new(output/'check_ledger'/(str(checks)+'.done.json'),old_result)
                checks+=1;write_new(output/'check_ledger'/(str(checks)+'.start.json'),{'recipe':recipe,'state':state['label'],'model':name,'kind':'new'})
                new_result,tensor=query_state(mg,q,names);write_new(output/'check_ledger'/(str(checks)+'.done.json'),new_result)
                returned=dict(zip(new_result['full_model_joint_names'],new_result['full_model_qpos']));assert all(abs(returned[n]-v)<1e-6 for n,v in locked.items())
                poses=mg.kinematics.get_link_poses(tensor,['fl_link6','fl_link7','fl_link8']);positions=poses.position.cpu().numpy()[0];quats=poses.quaternion.cpu().numpy()[0];errors=[]
                for i,link in enumerate(['fl_link6','fl_link7','fl_link8']):
                    T=np.linalg.inv(matrix(base))@link_world(link,state['named_qpos'],base)
                    expected_q=t3d.quaternions.mat2quat(T[:3,:3]);actual_q=quats[i]/np.linalg.norm(quats[i])
                    angle=2*np.arccos(np.clip(abs(np.dot(expected_q,actual_q)),0,1))
                    errors.append({'link':link,'position_error_m':float(np.linalg.norm(T[:3,3]-positions[i])),'orientation_error_rad':float(angle),'rotation_matrix_error':float(np.max(np.abs(T[:3,:3]-t3d.quaternions.quat2mat(quats[i]))))})
                row['models'][name]={'old':old_result,'new':new_result,'lock_sync':sync,'actual_cache_audit':cache,'FK_conformance':errors,'nearest_sphere_world_pairs':closest_pairs(mg.kinematics,tensor,export)}
            pairs=exact_shape_pairs(hand_shapes(saved,state,base),[s for s in export['shapes'] if s['role'] in ('table','pad','bottle')]);row['exact_shape_pairs']=pairs
            row['geometry_violation']=any(p['definite_open_grasp_geometry_violation'] and p['physical_collision_filter_enabled'] for p in pairs)
            write_new(output/recipe/(state['label']+'.geometry.json'),export);write_new(output/recipe/(state['label']+'.json'),row);rows.append(row)
            print(recipe,state['label'],{k:v['new']['valid'] for k,v in row['models'].items()},row['geometry_violation'],flush=True)
        endpoint=rows[-1];conformance=all(p['position_error_m']<.005 and p['orientation_error_rad']<.05 for r in rows for v in r['models'].values() for p in v['FK_conformance'])
        clear=all(r['models'][n]['new']['valid'] for r in rows[:2] for n in models)
        decision='EXACT_ENDPOINT_GEOMETRY_INVALID_NO_PHYSICAL' if endpoint['geometry_violation'] else 'ENDPOINT_VALID_MICRO_PREREQUISITES_PENDING' if clear and conformance and all(v['new']['valid'] for v in endpoint['models'].values()) else 'MODEL_CONFORMANCE_OR_CONTACT_REVIEW_REQUIRED'
        result={'recipe_id':recipe,'decision':decision,'model_FK_conformance':conformance,'known_clear_not_blanket_rejected':clear,'states':rows,'physical_attempts':0};write_new(output/recipe/'result.json',result);results.append(result)
    return {'model_results':results,'constraint_API_calls':checks,'fresh_sapien_scenes':0,'trajectory_queries':0,'physical_attempts':0,'new_roots':0,'new_raw_trajectories':0,'pass':True}
