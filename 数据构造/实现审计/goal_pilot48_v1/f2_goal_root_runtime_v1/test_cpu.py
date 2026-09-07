import types,unittest
from .spec import build_prefix_spec,validate_prefix_spec,build_contract
from .prefix_controller import compile_prefix_method,make_controller

class PrefixTests(unittest.TestCase):
    def test_new_current_lineage_and_prefix_budget(self):
        s=build_prefix_spec();c=build_contract();self.assertTrue(validate_prefix_spec(s))
        self.assertEqual(s['binding'],c['binding'])
        self.assertNotEqual(s['planned']['slot_id'],c['planned']['slot_id'])
        self.assertFalse(s['old_inside_success_inherited'])
        self.assertEqual(s['resource_caps'],{'solver_problems':3,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0})

    def test_provisional_prefix_controller_cannot_be_root_collector(self):
        controller=make_controller(build_prefix_spec()['binding'])
        self.assertTrue(controller.planner_only)
        self.assertFalse(controller.binding['selected'])
        with self.assertRaises(RuntimeError):controller.plan_suffix_from_actual_prefix_end_state(None)
        with self.assertRaises(RuntimeError):controller.execute_frozen_suffix_spec(None)

    def run_fake(self,tracking=True):
        from controlled_multi_future import f2_top_contact_root_runtime_v1 as parent
        log=[]
        def preplan(scene,targets):
            log.append('plan_pregrasp_grasp');self.assertEqual(len(targets),3)
            return {'pass':True,'controls':[{},{}],'segment_receipts':[{},{}]}
        def postplan(scene,planned,targets):
            log.append('actual_postclose_plan_lift');self.assertIn('close',log)
            return {'pass':True,'controls':[{},{},{}],'segment_receipts':[{},{},{}]}
        method,source=compile_prefix_method(parent,preplan,postplan,lambda s:log.append('restore_fullworld'))
        self.assertIn('translation_drift <= 0.005',source);self.assertIn('orientation_drift <= 0.05',source)
        scene=types.SimpleNamespace(trace=[{}],can=object(),close_gripper=lambda *a,**kw:'close')
        selfobj=types.SimpleNamespace(_bind_scene=lambda s:None,canonical_prefix_contract=lambda p:{},
          initialize_prefix_replay_trace=lambda s:None,recipe={'recipe_sha256':'cpu'})
        def execute(scene,controls,targets,index,arm):log.append('execute'+str(index));scene.trace.append({});return {}
        def tracking_gate(rows):log.append('tracking');return {'pass':tracking}
        ns=method.__globals__;pose=[0,0,.8,1,0,0,0]
        ns.update(generate_official_raw_pose_receipt_v1=lambda *a,**kw:{},freeze_f2_final_grasp_pose_v2=lambda *a,**kw:{'final_goal_poses':{'grasp':pose,'pregrasp':[0,0,.89,1,0,0,0]}},
          _planner_reset=lambda *a,**kw:{},_execute_planned_segment=execute,audit_f2_preclose_tracking_gate_v1=tracking_gate,
          _must_action=lambda s,a,label:log.append(a),_arm_tag=lambda a:a,_arm_eef_pose=lambda *a:pose,_pose=lambda a:pose,
          _entity=lambda a:types.SimpleNamespace(get_name=lambda:'can'),_settle_prefix_with_replay_operator=lambda *a:log.append('settle'),
          _prefix_physical_acceptance=lambda *a,**kw:{'pass':True},_prefix_reference_result=lambda *a,**kw:kw)
        try:r=method(selfobj,scene,{},capture_anchor=lambda s:{})
        except RuntimeError:
            if tracking:raise
            return log,scene
        return log,r

    def test_actual_private_method_orders_postclose_plan_after_close(self):
        log,_=self.run_fake()
        self.assertEqual(log,['plan_pregrasp_grasp','execute0','execute1','tracking','close','actual_postclose_plan_lift','execute2','restore_fullworld','settle'])

    def test_original_preclose_gate_stops_close_and_lift(self):
        log,scene=self.run_fake(False)
        self.assertNotIn('close',log);self.assertNotIn('actual_postclose_plan_lift',log)
        self.assertEqual(scene._cmf_prefix_failure_receipt['failure'],'PRECONTACT_ARM_TRACKING_FAILURE')

    def test_native_escape_rejects_deeper_or_still_supported(self):
        import numpy as np
        from .prefix_models import native_escape_checks
        good=np.array([[[0,0,.74]],[[0,0,.80]],[[0,0,.86]]])
        self.assertTrue(native_escape_checks(good,.74)['pass'])
        bad=good.copy();bad[1,0,2]=.739
        self.assertFalse(native_escape_checks(bad,.74)['pass'])
        self.assertFalse(native_escape_checks(np.array([[[0,0,.74]],[[0,0,.74]]]),.74)['pass'])

if __name__=='__main__':unittest.main()
