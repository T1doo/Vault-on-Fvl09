"""Exercise actual execute() with CPU callbacks, including every pre-close stop."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
import numpy as np
from . import micro
class Tests(unittest.TestCase):
    def case(self,fail_plan=None,fail_window=None,fail_native=False):
        route=json.loads((Path(__file__).parent/'route_spec.json').read_text())
        proposal=json.loads((Path(__file__).parent.parent/'f3_contact_height_revision_v2/recipe.json').read_text())
        proposal['_route_pregrasp_pose']=route['intermediate_actual_pregrasp_pose'];calls=[]
        actor=SimpleNamespace(get_name=lambda:'bottle');scene=SimpleNamespace(robot=SimpleNamespace(left_planner=SimpleNamespace(motion_gen=SimpleNamespace(kinematics=SimpleNamespace(joint_names=["fl_joint1"])))),planner_query_count=0,trace=[{}],bottle=actor,pad=actor,selected_gripper_links=lambda:['fl_link7','fl_link8'])
        scene.close_gripper=lambda *a,**k:calls.append('close')
        def plan(s,req,**kw):
            stage=req[0]['segment_id'].removeprefix('f3_micro_');calls.append('plan:'+stage);s.planner_query_count+=1
            return {'pass':stage!=fail_plan,'controls':[{'position':np.zeros((1,6)),'velocity':np.zeros((1,6))}], 'segment_receipts':[{'end_qpos':np.zeros(38)}]}
        def execute(s,*args):s.trace.append({});calls.append('execute');return {'start_trace_row':0,'end_trace_row':len(s.trace)-1}
        def window(s,r,target,*args):return {'pass':target['segment_id']!='f3_micro_'+str(fail_window)}
        patches={'bind_actual_solver_base':lambda *a:None,'capture_scene_collision_geometry':lambda *a:{},'rebuild_actual_motiongens':lambda *a:(None,None,{},{}),'refresh_open_model':lambda *a:None,'actual_flange_goal_to_reported_command':lambda *a:a[-1], 'online_window':window,'attach_closed_bottle_model':lambda *a:calls.append('attach'),'native_plan_gate':lambda *a:{'pass':True},'audit_micro_lift_trace':lambda *a,**k:{'pass':True}}
        with patch('goal_pilot48_v1.f3_native_self_pair_v1.checker.check_controls',return_value={'pass':not fail_native}), patch.object(micro,'runtime_joint_state',return_value=(['fl_joint1'],[0.])), tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as d,ExitStack() as stack:
            for k,v in patches.items():stack.enter_context(patch.object(micro,k,v))
            prefix='controlled_multi_future.family_runners_v3_1.'
            for k,v in {'_plan_chain':plan,'_planner_reset':lambda *a,**k:None,'_arm_eef_pose':lambda *a:proposal['desired_actual_flange_world_pose'],'_must_action':lambda *a:None,'_arm_tag':lambda a:a,'_wait_and_record':lambda *a:None,'_entity':lambda a:a}.items():stack.enter_context(patch(prefix+k,v))
            stack.enter_context(patch('controlled_multi_future.high_level_physical_runner_v1._execute_planned_segment',execute))
            result=micro.execute(scene,proposal,Path(d))
        return scene,calls,result
    def test_success_exactly_three_queries(self):
        s,c,r=self.case();self.assertEqual(s.planner_query_count,3);self.assertTrue(r['pass']);self.assertEqual([x for x in c if x.startswith('plan:')],['plan:pregrasp','plan:grasp','plan:lift25'])
    def test_every_preclose_planner_failure_stops(self):
        for i,stage in enumerate(('pregrasp','grasp')):
            s,c,r=self.case(fail_plan=stage);self.assertEqual(s.planner_query_count,i+1);self.assertNotIn('close',c);self.assertFalse(r['pass'])
    def test_every_preclose_window_failure_stops(self):
        for i,stage in enumerate(('pregrasp','grasp')):
            s,c,r=self.case(fail_window=stage);self.assertEqual(s.planner_query_count,i+1);self.assertNotIn('close',c);self.assertFalse(r['pass'])
    def test_lift_planner_failure_no_fourth_query(self):
        s,c,r=self.case(fail_plan='lift25');self.assertEqual(s.planner_query_count,3);self.assertFalse(r['pass'])
    def test_native_failure_before_first_control(self):
        s,c,r=self.case(fail_native=True);self.assertEqual(s.planner_query_count,1);self.assertNotIn('execute',c);self.assertNotIn('close',c);self.assertEqual(r['earliest_failed_stage'],'pregrasp_native_self_pair_gate')
if __name__=='__main__':unittest.main()
