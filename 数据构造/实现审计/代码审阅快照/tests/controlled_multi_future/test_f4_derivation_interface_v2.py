import unittest
from unittest.mock import Mock
from controlled_multi_future.f4_derivation_interface_v2 import validate_f4_derivation_interface_v2
from controlled_multi_future.f4_post_stage0_planner_only_v1 import _dispatch_endpoint_ik_planner
class TestF4DerivationInterfaceV2(unittest.TestCase):
 def _candidate(self):return {"candidate_id":"lower_carry_height","candidate_application_sha256":"a"*64}
 def _a(self):
  ids=["A_pregrasp","A_grasp","A_lift","A_lower_carry_mid","A_lower_preplace","A_release","A_neutral"];targets=[{"segment_id":x,"pose":[0,0,1,1,0,0,0]} for x in ids];return {"role":"A","selected_candidate_id":"lower_carry_height","targets":targets,"preplanner_gate":{"pass":True,"candidate_contract_target_pose_sha256":"b"*64,"applied_planner_target_pose_sha256":"b"*64}}
 def test_normalizes_a_special_case(self):self.assertTrue(validate_f4_derivation_interface_v2(self._a(),role="A",selected_candidate=self._candidate())["pass"])
 def test_rejects_scalar_and_nonfinite(self):
  for bad in (7,[0,0,float("nan"),1,0,0,0]):
   x=self._a();x["targets"][0]["pose"]=bad
   with self.assertRaises((ValueError,TypeError)):validate_f4_derivation_interface_v2(x,role="A",selected_candidate=self._candidate())
 def test_runner_dispatches_endpoint_planner(self):
  adapter=Mock();adapter.plan_suffix_from_actual_prefix_end_state.return_value={"planner_solvable":False};scene=object();program={"program_id":"F4-ABC"};replay={};self.assertEqual(_dispatch_endpoint_ik_planner(adapter,scene,program,replay),{"planner_solvable":False});adapter.plan_suffix_from_actual_prefix_end_state.assert_called_once_with(scene,program,replay)
if __name__=="__main__":unittest.main()
