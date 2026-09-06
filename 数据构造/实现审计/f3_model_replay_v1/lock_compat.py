"""Local compatibility for locked JointState with absent velocity/acceleration."""
import copy

def update_locked_state(mg,locked,robot_config):
    from curobo.types.robot import RobotConfig
    cfg=copy.deepcopy(robot_config.get('robot_cfg',robot_config));cfg['kinematics']['lock_joints']=locked
    new=RobotConfig.from_dict(cfg,mg.tensor_args).kinematics.kinematics_config
    seen=set()
    for rollout in [mg.rollout_fn]+mg.get_all_rollout_instances():
        model=rollout.kinematics;target=model.kinematics_config
        if id(target) in seen:continue
        seen.add(id(target));model.update_kinematics_config(new)
        # Upstream KinematicsTensorConfig.copy_ discards JointState.copy_'s
        # returned clone when v/a are None; explicitly copy named positions.
        js=target.lock_jointstate
        if js is None:raise ValueError('locked joint metadata missing')
        import torch
        values=torch.as_tensor([locked[n] for n in js.joint_names],device=js.position.device,dtype=js.position.dtype).reshape_as(js.position)
        js.position.copy_(values)
    return {'updated_kinematics_config_instances':len(seen),'locked_positions':locked,'installed_library_files_changed':False}
