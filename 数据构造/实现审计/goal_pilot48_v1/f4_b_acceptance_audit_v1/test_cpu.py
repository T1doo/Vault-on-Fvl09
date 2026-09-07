"""Current persistence/eligibility negative controls; CPU data fixtures only."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from controlled_multi_future.current_hasher import hash_array
from realization_current_layout_audit_v1 import audit as storage_audit
from .pristine_current_hook import persist_pristine_current,validate_arrays
from .current_recovery import historical_rule_evidence,audit_later_current

class Tests(unittest.TestCase):
    def fixture(self):
        q=np.arange(38,dtype=np.float64);v=np.zeros(38);g=np.zeros(4)
        arrays=dict(head_rgb=np.zeros((2,3,3),dtype=np.uint8),left_wrist_rgb=np.ones((2,2,3),dtype=np.uint8),right_wrist_rgb=np.full((2,2,3),2,dtype=np.uint8),
            robot_qpos=np.concatenate((q,q)),robot_qvel=np.concatenate((v,v)),gripper_joint_qpos=g)
        current={'aggregate_sha256':'CPU_FIXTURE','model_visible_components':dict(head_rgb_sha256=hash_array(arrays['head_rgb']),
            wrist_rgb_sha256={'left':hash_array(arrays['left_wrist_rgb']),'right':hash_array(arrays['right_wrist_rgb'])},
            robot_state_sha256=hash_array(np.concatenate((q,v))),gripper_actual_state_sha256=hash_array(g))}
        return arrays,current,q,v
    def test_hook_persists_once_pristine_and_matches_existing_lossless_audit(self):
        arrays,current,q,v=self.fixture();adapter=SimpleNamespace(capture_current=lambda scene:deepcopy(current));original=adapter.capture_current
        scene=SimpleNamespace(_cmf_scene_context_v1_2=SimpleNamespace(phase='pristine'))
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            root=Path(directory)
            with patch('goal_pilot48_v1.f4_b_acceptance_audit_v1.pristine_current_hook.build_arrays',return_value=arrays):
                with persist_pristine_current(adapter,root_directory=root) as state:
                    adapter.capture_current(scene);self.assertTrue(state['persisted'])
                    scene._cmf_scene_context_v1_2.phase='strict_prefix_branch:F4-ABC';adapter.capture_current(scene)
                    with (root/'CPU_trace.npz').open('xb') as f:np.savez_compressed(f,joint_qpos=q[None,:],joint_qvel=v[None,:])
                    audit=storage_audit(root/'current',root/'CPU_trace.npz')
                    self.assertEqual(audit['unique_articulation_dofs'],38);self.assertEqual(audit['model_visible_robot_state_dimension'],76);self.assertTrue(audit['pass'])
            self.assertIs(adapter.capture_current,original)
    def test_wrong_RGB_or_duplicate_state_copy_rejected(self):
        for key in ('head_rgb','left_wrist_rgb','right_wrist_rgb','robot_qpos'):
            arrays,current,_,_=self.fixture();arrays[key].flat[-1]+=1
            with self.assertRaises(ValueError):validate_arrays(arrays,current)
    def test_no_pristine_phase_does_not_silently_capture_branch(self):
        arrays,current,_,_=self.fixture();adapter=SimpleNamespace(capture_current=lambda scene:current)
        scene=SimpleNamespace(_cmf_scene_context_v1_2=SimpleNamespace(phase='strict_prefix_branch:F4-ABC'))
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            with persist_pristine_current(adapter,root_directory=directory) as state:adapter.capture_current(scene)
            self.assertFalse(state['persisted']);self.assertFalse((Path(directory)/'current').exists())
    def test_reuse18_explicitly_links_older_pc_to_later_real_variant_current(self):
        proof=historical_rule_evidence();rows=proof['rows']
        self.assertEqual(len(rows),6);self.assertEqual(sum(r['realization']=='r_pc' for r in rows),3)
        self.assertEqual(len({r['shared_current_directory'] for r in rows}),1)
        self.assertIn('F4_A_path/current',rows[0]['shared_current_directory'])
    def test_A_current_cannot_recover_B(self):
        with self.assertRaises(ValueError):audit_later_current(root_job='/nfs_share/lijunhui/Robotwin2/datasets/p48_f4_b_root_001',
            current_directory='/nfs_share/lijunhui/Robotwin2/datasets/cmf_realization_unattempted8_v1_3/F4_A_path/current',
            producer_branch='unused',producer_goal='unused',producer_guard='unused')

if __name__=='__main__':unittest.main(verbosity=2)
