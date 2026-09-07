import copy,unittest
import numpy as np
from .cell import primary_converter,equal
from .common import P
from controlled_multi_future.raw_writer import validate_raw_streams

class Tests(unittest.TestCase):
    def source(self):return P/'controlled_multi_future/probes/runtime_trace.py'
    def rows(self):
        return [{'timestamp':i*.004,'initial_state':i==0,'effective_setpoint':np.ones(26)*i,'requested_command':np.ones(26)*i,
          'planner_goal_eef_pose':np.full(14,np.nan),'gripper_command':np.ones(2),'component_mask':np.ones(26,dtype=bool),
          'joint_qpos':np.ones(38)*i,'joint_qvel':np.zeros(38),'dual_eef':np.zeros(14),
          'planner_goal_active':[False,False],'planner_query_id':[-1,-1],'planner_goal_source':['','']} for i in range(3)]
    def test_original_primary_mapping_and_Nplus1_validator(self):
        streams,_=primary_converter(self.source())(self.rows());validate_raw_streams(streams)
        self.assertEqual(streams['controller_effective_setpoint'].shape,(2,26));self.assertEqual(streams['realized_qpos'].shape,(3,38))
        self.assertTrue(equal(streams['controller_effective_setpoint'][:,0],[1,2]));self.assertTrue(equal(streams['action_interval_start_timestamps'],[0,.004]))
    def test_original_alignment_rejects_one_frame_shift(self):
        streams,_=primary_converter(self.source())(self.rows());streams['action_interval_start_timestamps']=streams['action_interval_start_timestamps']+.004
        with self.assertRaises(ValueError):validate_raw_streams(streams)
    def test_nan_equality_only_for_original_missing_fields(self):
        self.assertTrue(equal(np.array([np.nan]),np.array([np.nan])));self.assertFalse(equal([1,2],[2,1]))
        rows=self.rows();rows[0]['initial_state']=False
        with self.assertRaises(ValueError):primary_converter(self.source())(rows)

if __name__=='__main__':unittest.main()
