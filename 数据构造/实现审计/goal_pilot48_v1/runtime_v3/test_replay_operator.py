"""Execute the REAL replay_effective_setpoint_step Python body on CPU joints."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from controlled_multi_future.probes.runtime_trace import DenseTraceMixin
from .meter import Meter

class Joint:
    def __init__(self):self.target=None;self.velocity=None
    def set_drive_target(self,value):self.target=value
    def set_drive_velocity_target(self,value):self.velocity=value

class Robot:
    def __init__(self):
        self.position={'left':np.zeros(6),'right':np.zeros(6)};self.velocity={'left':np.zeros(6),'right':np.zeros(6)}
        self.left_gripper=[(Joint(),),(Joint(),)];self.right_gripper=[(Joint(),),(Joint(),)]
        self.left_entity=object();self.right_entity=self.left_entity;self.qf_calls=0
    def set_arm_joints(self,q,v,arm):self.position[arm]=q.copy();self.velocity[arm]=v.copy()
    def _entity_qf(self,entity):self.qf_calls+=1

class CPUScene(DenseTraceMixin):
    def __init__(self):
        self.robot=Robot();self.trace=[];self.steps=0
        self._requested_position={};self._requested_velocity={};self._requested_gripper=[1.,1.]
        self.scene=SimpleNamespace(step=self.step)
    def step(self):self.steps+=1
    def _record(self):
        # Reconstruct from the drive APIs written by the original operator;
        # do not copy the expected effective_setpoint input into trace.
        robot=self.robot
        action=np.concatenate((robot.position['left'],robot.position['right'],robot.velocity['left'],robot.velocity['right'],[robot.left_gripper_val,robot.right_gripper_val]))
        self.trace.append({'effective_setpoint':action})

def command(scene):
    action=np.arange(26,dtype=np.float64)/100
    scene.replay_effective_setpoint_step(action,requested_command=action,component_mask=np.ones(26,dtype=bool),
        left_gripper_joint_drive_target=np.array([.01,.02]),right_gripper_joint_drive_target=np.array([.03,.04]),
        left_gripper_joint_drive_velocity_target=np.array([.001,.002]),right_gripper_joint_drive_velocity_target=np.array([.003,.004]))
    return action

class Tests(unittest.TestCase):
    def test_real_operator_drives_steps_records_and_charges_once_per_scene(self):
        original=DenseTraceMixin.replay_effective_setpoint_step
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            meter=Meter(directory,dict(solver_problems=0,fresh_scenes=2,action_scenes=2,collection_attempts=0))
            meter.install_replay_hook(DenseTraceMixin)
            try:
                for ordinal in (1,2):
                    scene=CPUScene();meter.scene_ids[id(scene)]=ordinal
                    expected=command(scene);command(scene)
                    self.assertEqual(scene.steps,2);self.assertEqual(len(scene.trace),2)
                    np.testing.assert_array_equal(scene.trace[-1]['effective_setpoint'],expected)
                    self.assertEqual(scene.robot.left_gripper[0][0].target,.01)
                    self.assertEqual(scene.robot.right_gripper[1][0].velocity,.004)
                    self.assertEqual(meter.counts['action_scenes'],ordinal)
            finally:meter.close()
        self.assertIs(DenseTraceMixin.replay_effective_setpoint_step,original)
    def test_replay_and_other_action_entry_share_scene_dedup(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            meter=Meter(directory,dict(solver_problems=0,fresh_scenes=1,action_scenes=1,collection_attempts=0))
            scene=CPUScene();meter.scene_ids[id(scene)]=1
            meter.charge('action_scenes',scene_ordinal=1);meter.active_actions.add((id(scene),1))
            meter.install_replay_hook(DenseTraceMixin)
            try:command(scene);self.assertEqual(meter.counts['action_scenes'],1)
            finally:meter.close()
    def test_unknown_scene_refused_before_real_drive(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            meter=Meter(directory,dict(solver_problems=0,fresh_scenes=1,action_scenes=1,collection_attempts=0));scene=CPUScene()
            meter.install_replay_hook(DenseTraceMixin)
            try:
                with self.assertRaises(RuntimeError):command(scene)
                self.assertEqual(scene.steps,0);self.assertEqual(meter.counts['action_scenes'],0)
            finally:meter.close()

if __name__=='__main__':unittest.main(verbosity=2)
