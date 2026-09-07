"""Actual stage models; on has NO scale or inside-floor exemption."""
import numpy as np
from goal_pilot48_v1.f2_controlled_inside_runtime_v2.live_models import LiveModels as Base, released_config_and_world,MODELS
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,support_witness,native_can_screen

class LiveModels(Base):
    def __init__(self,scene,output,spec):
        super().__init__(scene,output);self.spec=spec;self.witness=None

    def install_carried(self,index):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import install_motiongens
        from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.certificate import negative_pairs
        from transforms import full_joint_state_to_solver_joint_state
        export,can,names,q=self.prepare();self.export,self.can=export,can
        full=install_motiongens(self.scene,self.cfg,export,witness=None);checks=self.query_current('full_'+str(index))
        self.phase='CARRIED_FULL_WORLD'
        if self.spec['relation']=='on':
            return self.save('on_full',{'pass':all(r['valid'] is True for r in checks.values()),'checks':checks,'audits':full,
              'new_scale_exception_admitted':False,'failure_requires_model_impact_review':True,'config':self.cfg,'world':export})
        self.witness=support_witness(export,can,self.spec['target_actor_pose'],self.base)
        if self.witness['support_name']!='table__0':raise ValueError('new support piece needs review')
        overlaps={}
        for name in MODELS:
            mg=getattr(self.scene.robot.left_planner,name)
            ordered=full_joint_state_to_solver_joint_state(q,names,list(mg.kinematics.joint_names))
            spheres=mg.kinematics.get_state(mg.tensor_args.to_device(ordered).reshape(1,-1)).get_link_spheres().detach().cpu().numpy()[0]
            kin=mg.kinematics.kinematics_config;reverse={v:k for k,v in kin.link_name_to_idx_map.items()}
            links=[reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
            overlaps[name]=negative_pairs(spheres,links,export)
            self.save('beside_full_spheres_'+name,{'spheres':spheres.tolist(),'links':links,'negative_pairs':overlaps[name]})
            if any(r['link']!='attached_can' or r['obstacle']!='table__0' for r in overlaps[name]):
                raise ValueError('beside negative pair outside can/table support; no expansion')
            if checks[name]['valid'] is not True and 'INVALID_START_STATE_WORLD_COLLISION' not in str(checks[name]['status']):
                raise ValueError('unrelated actual full-model failure')
        binding=self.binding(export,can,names,q,self.spec['target_actor_pose'])
        self.save('beside_admission',{'actual_binding':binding,'actual_native_target_witness':self.witness,'full_checks':checks,'negative_pairs':overlaps})
        audits=install_motiongens(self.scene,self.cfg,export,witness=self.witness)
        pair=self.query_current('beside_table_pair_'+str(index))
        return self.save('beside_pair',{'pass':all(r['valid'] is True for r in pair.values()),'checks':pair,'audits':audits,
          'binding':binding,'only_attached_can_table_pair_filtered':True,'robot_uses_fullworld':True})

    def screen(self,control,index):
        from controlled_multi_future.family_runners_v3_3 import _pose
        from .native import NativeWorld
        poses=self.native_can_actor_poses(control)
        if np.max(abs(matrix(poses[0])-matrix(_pose(self.scene.can))))>1e-4:raise ValueError('native path not bound to current grasp')
        native=NativeWorld(self.export,self.can,self.base).screen(poses,table_support=self.spec['relation']=='beside')
        table=None
        if self.spec['relation']=='beside':
            table=native_can_screen(self.scene.robot.left_planner.motion_gen.kinematics,control['position'],self.native,self.base,self.witness,require_supported=index==1)
        return {'pass':native['pass'] and (table is None or table['pass']),'native_all_world_samples':native,'table_native_support':table}

    def install_released(self):
        from controlled_multi_future.family_runners_v3_3 import _arm_gripper_open
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import install_motiongens
        if self.phase!='CARRIED_FULL_WORLD' or not _arm_gripper_open(self.scene,'left'):raise ValueError('actual full-open stage required')
        export,can,names,q=self.capture();cfg,world=released_config_and_world(self.cfg,export,can,names,q)
        audits=install_motiongens(self.scene,cfg,world,witness=None);self.cfg=cfg;self.phase='RELEASED_FULL_WORLD'
        checks=self.query_current('released_full')
        return self.save('released_full',{'pass':all(r['valid'] is True for r in checks.values()),'checks':checks,'audits':audits,
          'config':cfg,'world':world,'actual_qpos':q.tolist(),'joint_names':list(names),'actual_can':can,
          'actual_binding':self.binding(world,can,names,q),'attached_can_present':False,'all_support_checks_restored':True,
          'predicted_can_or_open_joint_state_used':False})
