import unittest,tempfile
from types import SimpleNamespace
from pathlib import Path
from meter import Meter
class Tests(unittest.TestCase):
    def test_batch_targets_not_seeds_and_nested_IK_not_double_counted(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as d:
            m=Meter(d,{'solver_problems':20,'fresh_scenes':2,'action_scenes':1,'collection_attempts':0})
            def ik(goal_pose,num_seeds=32):return 1
            wrapped_ik=m.solver(ik,kind='ik')
            def plan(goal_pose):return wrapped_ik(goal_pose)
            import numpy as np
            goal=SimpleNamespace(position=np.zeros((10,3)))
            m.solver(plan,kind='batch')(goal);self.assertEqual(m.counts['solver_problems'],10)
            wrapped_ik(SimpleNamespace(position=np.zeros((1,3))),num_seeds=32);self.assertEqual(m.counts['solver_problems'],11)
    def test_cap_before_dispatch_and_reset_cannot_erase(self):
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as d:
            m=Meter(d,{'solver_problems':1,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0});calls=[]
            def p(goal_pose):calls.append(1)
            f=m.solver(p,kind='plan');f(None)
            scene=SimpleNamespace(planner_query_count=0)
            with self.assertRaises(RuntimeError):f(None)
            self.assertEqual(len(calls),1);self.assertEqual(m.counts['solver_problems'],1)
if __name__=='__main__':unittest.main(verbosity=2)
