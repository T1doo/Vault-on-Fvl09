"""Separate adversarial review of final F1 disk predicates; no native simulator calls."""
import unittest,json
import numpy as np
from test_f1_verifier_cell import TestF1VerifierCell
from f1_disk_verifier import verify_f1_disk
class IndependentVerifierReview(unittest.TestCase):
 @classmethod
 def setUpClass(cls):TestF1VerifierCell.setUpClass()
 @classmethod
 def tearDownClass(cls):TestF1VerifierCell.tearDownClass()
 def setUp(self):self.fixture=TestF1VerifierCell()
 def tearDown(self):self.fixture.doCleanups()
 def check(self,mutate):
  raw,arrays=self.fixture.mutated();mutate(arrays);np.savez_compressed(raw/'raw_streams.npz',**arrays)
  return verify_f1_disk(raw_dir=raw,spec=self.fixture.spec,program=self.fixture.spec['programs'][0])
 def test_subject_moving_with_zero_saved_speed_is_not_stable(self):
  def mutate(a):a['audit__role_object_pose__red'][-20,0]+=.002;a['audit__role_object_linear_velocity__red'][-50:]=0.
  self.assertFalse(self.check(mutate)['pass'])
 def test_eef_window_motion_cannot_hide_in_last_stationary_row(self):
  def mutate(a):a['stream__realized_eef'][-20,0]+=.002;a['audit__eef_linear_velocity'][-50:]=0.
  self.assertFalse(self.check(mutate)['pass'])
 def test_nonexecuting_arm_velocity_command_is_not_left_only(self):
  def mutate(a):a['stream__controller_effective_setpoint'][-30,18]=.2
  self.assertFalse(self.check(mutate)['pass'])
 def test_open_command_does_not_replace_measured_opening(self):
  def mutate(a):a['stream__gripper_command'][-50:,0]=1.;a['audit__realized_left_gripper_joint_qpos'][-50:,0]=-.01
  result=self.check(mutate);self.assertFalse(result['pass']);self.assertFalse(result['checks']['actual_gripper_open'])
if __name__=='__main__':unittest.main()
