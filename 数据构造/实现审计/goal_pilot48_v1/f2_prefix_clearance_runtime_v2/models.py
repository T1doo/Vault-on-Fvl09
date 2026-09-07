"""Live freshly fitted full-model-first F2 postclose implementation."""
import copy
import numpy as np
from goal_pilot48_v1.f2_goal_root_runtime_v1.prefix_models import imports,save
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix
from goal_pilot48_v1.f2_inward_runtime_v1.contract import digest
from .certificate import capture_native_grasp,negative_pairs,choose_mode,escape_gate,state_binding,verify_certificate

def query_models(scene,label):
    from model_apply import runtime_joint_state,query_state
    names,q=runtime_joint_state(scene);rows={};tensors={}
    if not hasattr(scene,'_f2_clearance_check_count'):scene._f2_clearance_check_count=0
    for name in ('motion_gen','motion_gen_batch'):
        scene._f2_clearance_check_count+=1;ordinal=scene._f2_clearance_check_count
        save(scene,f'clearance_check_{ordinal:02d}.start.json',{'stage':label,'model':name,'high_level_constraint_call':1})
        try:
            mg=getattr(scene.robot.left_planner,name)
            row,tensor=query_state(mg,q,names);row={**row,'model_instance_id':id(mg)};rows[name]=row;tensors[name]=tensor
            save(scene,f'clearance_check_{ordinal:02d}.done.json',{'stage':label,'model':name,'result':row,'error':None})
        except BaseException as e:
            save(scene,f'clearance_check_{ordinal:02d}.done.json',{'stage':label,'model':name,'error':{'type':type(e).__name__,'message':str(e)}});raise
    return rows,tensors

def snapshot_overlaps(scene,export,tensors,binding):
    result={}
    for name in ('motion_gen','motion_gen_batch'):
        mg=getattr(scene.robot.left_planner,name);state=mg.kinematics.get_state(tensors[name]);spheres=state.get_link_spheres().detach().cpu().numpy()[0]
        kin=mg.kinematics.kinematics_config;reverse={v:k for k,v in kin.link_name_to_idx_map.items()};links=[reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
        row={'sphere_source':'CURRENT_FRESHLY_FITTED_MODEL_KINEMATICS','sphere_array':spheres.tolist(),'sphere_links':links,
          'binding':binding,'model_instance_id':id(mg),
          'negative_pairs':negative_pairs(spheres,links,export),'solver_qpos':tensors[name].detach().cpu().numpy().tolist()}
        row['receipt_sha256']=digest(row);result[name]=row
    save(scene,'clearance_actual_sphere_overlap.json',result);return result

def postclose_sequence(backend,planned,targets):
    """CPU-testable branch ordering; backend supplies actual live model work."""
    evidence=backend.prepare_full()
    mode=choose_mode(evidence['native'],evidence['full_checks'],evidence['overlaps'],backend.current_binding())
    backend.record_mode(mode,evidence)
    if mode!='FULL_WORLD':
        checks=backend.install_pair(evidence)
        if set(checks)!={'motion_gen','motion_gen_batch'} or not all(v['valid'] for v in checks.values()):raise RuntimeError('F2 pair model did not make both actual starts valid')
    lift=backend.plan_lift(targets[2])
    if not lift['pass']:raise RuntimeError('F2 clearance lift planner failed')
    if not backend.screen_actual_plan(lift,evidence['native'])['pass']:raise RuntimeError('F2 actual native lift path failed before execution')
    return {**lift,'controls':planned['controls']+lift['controls'],'segment_receipts':planned['segment_receipts']+lift['segment_receipts']}

class LiveBackend:
    def __init__(self,scene,targets):self.scene=scene;self.targets=targets;self.plan_consumed=False
    def current_binding(self):
        parent,_,_=imports();export,can=parent.world_and_can(self.scene,self.scene.robot.left_planner)
        return state_binding(self.scene,self.cfg,export,can,self.targets)
    def prepare_full(self):
        scene=self.scene;parent,install,prepare=imports()
        self.export,self.can=parent.world_and_can(scene,scene.robot.left_planner);self.base=scene.robot.left_planner._cmf_solver_base_world_pose
        self.cfg,_,_,_,self.native,_=prepare(scene,self.can)
        audits=install(scene,self.cfg,self.export,witness=None)
        save(scene,'clearance_fresh_full_models.json',{'config':self.cfg,'world':self.export,'can':self.can,'audits':audits,'sphere_fit_is_from_this_scene':True})
        full,tensors=query_models(scene,'FULL_WORLD_FIRST')
        self.binding=state_binding(scene,self.cfg,self.export,self.can,self.targets)
        native=capture_native_grasp(scene,self.export,self.can,self.base,self.binding);self.native_certificate=native;save(scene,'clearance_native_grasp_certificate.json',native)
        overlaps=snapshot_overlaps(scene,self.export,tensors,self.binding)
        return {'native':native,'full_checks':full,'overlaps':overlaps}
    def record_mode(self,mode,evidence):save(self.scene,'clearance_mode.json',{'mode':mode,'native_certificate_sha256':evidence['native']['receipt_sha256'],'full_checks':evidence['full_checks']})
    def install_pair(self,evidence):
        from .pair_model import install
        certificate=copy.deepcopy(evidence['native']);certificate.pop('receipt_sha256');certificate.update(admitted_mode='F2_CAN_TABLE_PADDING_UPWARD_ONLY',
          full_checks=evidence['full_checks'],fresh_overlap_receipts={k:v['receipt_sha256'] for k,v in evidence['overlaps'].items()});certificate['receipt_sha256']=digest(certificate)
        save(self.scene,'clearance_pair_admission.json',certificate)
        audits=install(self.scene,self.cfg,self.export,certificate,self.current_binding());save(self.scene,'clearance_pair_models.json',audits)
        checks,_=query_models(self.scene,'PAIR_AFTER_FULL_REJECTION');return checks
    def plan_lift(self,target):
        from controlled_multi_future.family_runners_v3_1 import _plan_chain
        verify_certificate(self.native_certificate,self.current_binding())
        if self.plan_consumed or digest(target)!=self.binding['lift_target_sha256']:raise ValueError('single12cm plan lease already consumed or target changed')
        self.plan_consumed=True
        save(self.scene,'clearance_single_lift_plan_lease.json',{'binding':self.binding,'consumed':True,'planner_query_before':int(self.scene.planner_query_count)})
        return _plan_chain(self.scene,[target],query_limit=3,arm='left')
    def screen_actual_plan(self,lift,witness):
        from goal_pilot48_v1.f2_inward_runtime_v1.collision import native_can_screen
        mg=self.scene.robot.left_planner.motion_gen;q=mg.tensor_args.to_device(np.asarray(lift['controls'][0]['position'],dtype=np.float32));state=mg.kinematics.get_state(q)
        positions=state.ee_position.detach().cpu().numpy();quats=state.ee_quaternion.detach().cpu().numpy();B=matrix(self.base);samples=[]
        for p,r in zip(positions,quats):
            T=B@matrix([*p,*r]);samples.append(self.native@T[:3,:3].T+T[:3,3])
        check=escape_gate(samples,witness)
        from transforms import reported_eef_goal_to_solver_goal
        goal=reported_eef_goal_to_solver_goal(self.scene.robot,self.scene.robot.left_planner,self.targets[2]['pose'])
        position_error=float(np.linalg.norm(positions[-1]-goal[:3]));q=quats[-1]/np.linalg.norm(quats[-1]);g=goal[3:]/np.linalg.norm(goal[3:])
        angle=float(2*np.arccos(np.clip(abs(np.dot(q,g)),0,1)))
        check['planned_endpoint_position_error_m']=position_error;check['planned_endpoint_orientation_error_rad']=angle
        check['planned_endpoint_matches_original_12cm_goal']=position_error<=.005 and angle<=.05
        check['pass']=check['pass'] and check['planned_endpoint_matches_original_12cm_goal']
        # The original physical execution receipt and prefix Gates remain
        # unchanged; this is an additional plan-intent integrity check.
        check['original_12cm_target_bound']=digest(self.targets[2])==self.binding['lift_target_sha256']
        if not self.plan_consumed or self.scene.planner_query_count!=self.binding['planner_query_before_lift']+1:raise ValueError('lift single-plan counter/lease mismatch')
        # Footprint checks use the actual table hull, already frozen in the
        # fresh witness. No old absolute support-gap predicate is invoked.
        from scipy.spatial import ConvexHull
        table=next(s for s in self.export['shapes'] if s['name']=='table__0');T=B@matrix(table['solver_pose']);v=np.asarray(table['vertices'])@T[:3,:3].T+T[:3,3]
        hull=ConvexHull(v[abs(v[:,2]-v[:,2].max())<1e-5,:2]);points=np.asarray(samples)
        footprint=bool(np.all(points[:,:,:2]@hull.equations[:,:2].T+hull.equations[:,2]<=1e-6));check['all_native_footprints_inside']=footprint;check['pass']=check['pass'] and footprint
        save(self.scene,'clearance_actual_lift_native_gate.json',check);return check

def postclose_plan(scene,planned,targets):
    if scene.planner_query_count!=2 or len(planned['controls'])!=2 or len(targets)!=3:raise ValueError('F2 unchanged2+1 prefix budget')
    if not np.allclose(np.asarray(targets[2]['pose'])-np.asarray(targets[1]['pose']),[0,0,.12,0,0,0,0],atol=1e-12,rtol=0):raise ValueError('original12cm lift target changed')
    return postclose_sequence(LiveBackend(scene,targets),planned,targets)

def restore_fullworld(scene):
    parent,install,prepare=imports();export,can=parent.world_and_can(scene,scene.robot.left_planner);cfg,_,_,_,_,_=prepare(scene,can)
    audits=install(scene,cfg,export,witness=None);checks,_=query_models(scene,'POST_LIFT_FULL_WORLD_RESTORED')
    save(scene,'prefix_postlift_fullworld_restored.json',{'audits':audits,'checks':checks,'support_pair_exception_active':False})
    if not all(row['valid'] for row in checks.values()):raise RuntimeError('actual postlift fullworld model invalid before prefix acceptance')
