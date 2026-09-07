import unittest
import types
import numpy as np
from .runtime import restore,sample_indices
from .catalog import verify_f1_scene_source

class Tests(unittest.TestCase):
    def test_samples_include_exact_initial_and_final(self):
        self.assertEqual(sample_indices(22),[0,10,20,21])
        self.assertEqual(sample_indices(21),[0,10,20])
    def test_real_f1_construction_ast_matches_parent(self):
        self.assertEqual(len(verify_f1_scene_source()),2)
    def test_state_restore_never_steps_or_commands_actions(self):
        class Entity:
            q=np.zeros(38)
            def get_qpos(self):return self.q
            def set_qpos(self,q):self.q=q.copy()
        class Actor:
            def set_pose(self,p):self.pose=p
            def get_pose(self):return types.SimpleNamespace(p=self.pose[:3],q=self.pose[3:])
        entity=Entity();actor=Actor();scene=types.SimpleNamespace(robot=types.SimpleNamespace(left_entity=entity,right_entity=entity),role_actors={'red':actor})
        q=np.ones((2,38));poses={'red':np.array([[0,0,1,1,0,0,0],[1,0,1,1,0,0,0]])}
        restore(scene,q,poses,1,lambda p:p.copy())
        self.assertTrue(np.array_equal(entity.q,q[1]));self.assertEqual(actor.pose[0],1)
        with self.assertRaises(ValueError):restore(scene,q,{},0,lambda p:p)

def load_tests(loader,tests,pattern):
    from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.test_all import Tests as HDTests
    return unittest.TestSuite([tests,loader.loadTestsFromTestCase(HDTests)])
