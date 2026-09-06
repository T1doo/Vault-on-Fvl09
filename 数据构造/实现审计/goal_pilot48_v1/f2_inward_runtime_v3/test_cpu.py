import copy,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .contract import A,P,W,build_contract,parent_contract,validate_contract,manifest_lineage,proposal,digest
from . import runtime,runner_bridge
from goal_pilot48_v1.f2_inward_runtime_v1.test_cpu import StateTests
from goal_pilot48_v1.f2_inward_runtime_v1.test_issuer import result as sample_result,events as sample_events

class RouteTests(unittest.TestCase):
    def test_only_U_changes_not_qualified_layout_D_seed_or_Gates(self):
        old=parent_contract();new=build_contract();p=proposal()
        self.assertEqual(old['binding'],new['binding']);self.assertEqual(old['planned'],new['planned'])
        for k in ('C','D_new','N'):self.assertEqual(old['inward_goals'][k],new['inward_goals'][k])
        np.testing.assert_array_equal(np.asarray(old['inward_goals']['U_new'])[[0,1,3,4,5,6]],np.asarray(new['inward_goals']['U_new'])[[0,1,3,4,5,6]])
        self.assertEqual(new['inward_goals']['U_new'],p['new_U_reported_goal']);self.assertEqual(p['exact_pair_count'],15664)
        self.assertTrue(p['native_geometry_pass']);self.assertFalse(p['physical_Gates_changed'])
        self.assertTrue(validate_contract(new))

    def test_old_U_or_changed_D_rejected(self):
        old=parent_contract()
        with self.assertRaises(ValueError):validate_contract(old)
        c=build_contract();c['inward_goals']['D_new'][2]+=.001
        with self.assertRaises(ValueError):validate_contract(c)

    def test_private_live_derivation_uses_new_height(self):
        c=build_contract()
        Pose=lambda p,q:types.SimpleNamespace(p=np.asarray(p),q=np.asarray(q))
        entity=types.SimpleNamespace(q=None)
        entity.set_qpos=lambda q:setattr(entity,'q',np.array(q))
        entity.set_qvel=lambda q:None;entity.get_qpos=lambda:entity.q
        can=types.SimpleNamespace(pose=Pose(c['sealed_prefix_end_actor_pose'][:3],c['sealed_prefix_end_actor_pose'][3:]))
        can.set_pose=lambda p:setattr(can,'pose',p)
        robot=types.SimpleNamespace(left_entity=entity,left_original_pose=c['neutral_eef_pose'],get_left_ee_pose=lambda:c['sealed_prefix_end_eef_pose'])
        scene=types.SimpleNamespace(robot=robot,can=can,table_z_bias=0.)
        meta=json.loads((P/'assets/objects/071_can/model_data0.json').read_text(encoding='utf-8'))
        helpers=types.SimpleNamespace(_actor_local_geometry_bounds=lambda x:(np.asarray(meta['center'])*.05,np.asarray(meta['extents'])*.025),
          _entity=lambda x:x,_pose=lambda x:np.r_[x.pose.p,x.pose.q])
        from semantic_target import derive_live_targets as old_derive
        with patch.dict(sys.modules,{'sapien':types.SimpleNamespace(Pose=Pose),'controlled_multi_future.family_runners_v3_3':helpers}):
            # A negative control proves old .08m geometry is actually reached
            # and rejected; the new helper fixes only this private derivation.
            with self.assertRaises(ValueError):old_derive(scene,c)
            targets,binding=runtime.live_target_helper()(scene,c)
        self.assertEqual(targets[1]['pose'],c['inward_goals']['U_new'])
        self.assertEqual(binding['targets_sha256'],c['beside_targets_sha256'])

    def test_actual_entry_new_route_and_missing_manifest_negative(self):
        observed={}
        def adapter(**kw):observed.update(kw);raise ImportError('CPU sentinel before scene')
        fake={'controlled_multi_future.f2_asset_bound_runtime_v3':types.SimpleNamespace(RoboTwinRealSapienF2AssetBoundAdapterV3=adapter),
              'controlled_multi_future.real_sapien_adapter_high_level_v1':types.SimpleNamespace(_PinnedSapienRenderDeviceContextV1=object)}
        for good in (True,False):
            with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='f2_U_cpu_') as tmp:
                out=Path(tmp)/'job';m={'jobs':[{'output_namespace':str(out)}],'manifest_sha256':'cpu','implementation_source_sha256':'cpu'}
                if good:m.update(manifest_lineage())
                with patch.dict(sys.modules,fake):r=runtime.run(m)
                self.assertEqual(r['fresh_scene_attempts'],0);self.assertFalse(r['pass'])
                self.assertEqual(r['error']['type'],'ImportError' if good else 'ValueError')
                if good:
                    receipt=json.loads((out/'runtime_route_revision1_lineage.json').read_text(encoding='utf-8'))
                    self.assertTrue(receipt['all_three_endpoints_require_fresh_model_checks'])
                    self.assertEqual(receipt['goals']['U_new'],proposal()['new_U_reported_goal'])

    def test_no_shared_globals_patch_and_three_fresh_IK_remain(self):
        from goal_pilot48_v1.f2_inward_runtime_v1 import runtime as parent
        old=parent.build_contract;one=runtime.load_private_runtime({})
        self.assertIs(parent.build_contract,old);self.assertIsNot(parent.dependencies,one.dependencies)
        text=(A/'goal_pilot48_v1/f2_inward_runtime_v1/runtime.py').read_text(encoding='utf-8')
        self.assertIn("for key in ('C', 'U_new', 'D_new'):",text)
        self.assertIn("endpoints = all",text)

    def test_meter_bridge_missing_charge_stops(self):
        for good in (True,False):
            with tempfile.TemporaryDirectory(dir=W/'Robotwin2/tmp',prefix='f2_U_bridge_cpu_') as tmp:
                out=Path(tmp)/'job';out.mkdir();meter=Path(tmp)/'job_meter';meter.mkdir();rows=sample_events()
                if not good:rows.pop()
                (meter/'events.jsonl').write_text('\n'.join(json.dumps(x) for x in rows)+'\n',encoding='utf-8')
                r={**sample_result(),'pass':True,'receipt_sha256':'cpu-parent'}
                with patch.object(runner_bridge,'execute',return_value=r):value=runner_bridge.run({'jobs':[{'output_namespace':str(out)}]})
                self.assertEqual(value['pass'],good)

if __name__=='__main__':unittest.main()
