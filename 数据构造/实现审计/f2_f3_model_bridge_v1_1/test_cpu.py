import ast,copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import yaml
from transforms import *
from geometry import capture_actor_geometry,exact_shape_pairs,matrix

class BridgeTests(unittest.TestCase):
    def test_original_C_U_D_chain(self):
        old=Path(__file__).resolve().parent.parent/'f2_bounded_transit_runtime_v1'
        sys.path.append(str(old))
        from transit import build_transit_spec
        cfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/config.yml').read_text())
        pcfg=yaml.safe_load((P/'assets/embodiments/aloha-agilex/curobo_left.yml').read_text())
        robot=SimpleNamespace(left_gripper_bias=cfg['gripper_bias'],left_inv_delta_matrix=np.linalg.inv(cfg['delta_matrix']),communication_flag=False)
        robot._trans_from_gripper_to_endlink=lambda target,arm_tag:TOOL(robot,target,arm_tag)
        planner=planner_view(cfg['robot_pose'][0],pcfg['planner']['frame_bias'],'aloha-agilex/curobo_left.yml')
        planner.plan_path=lambda q,pose,constraint_pose,arms_tag:GOAL(planner,q,pose,constraint_pose,arms_tag)
        robot.left_planner=planner
        for goal in [build_transit_spec()['poses'][k] for k in ('C','U','D')]:
            np.testing.assert_array_equal(reported_eef_goal_to_solver_goal(robot,planner,goal),ORIGINAL_LEFT_CALL(robot,goal,last_qpos=np.zeros(38)))

    def test_obstacles_never_receive_tool_offset(self):
        planner=planner_view([0,0,0,1,0,0,0],[0,0,0],'aloha-agilex/config')
        robot=SimpleNamespace(left_gripper_bias=.10,left_inv_delta_matrix=np.eye(3))
        p=[.2,.1,.9,1,0,0,0]
        self.assertGreater(np.linalg.norm(reported_eef_goal_to_solver_goal(robot,planner,p)[:3]-world_obstacle_to_solver_frame(planner,p)[:3]),.019)
        planner._cmf_solver_base_world_pose=[.1,.2,.3,1,0,0,0]
        np.testing.assert_allclose(world_obstacle_to_solver_frame(planner,planner._cmf_solver_base_world_pose),[0,0,0,1,0,0,0],atol=1e-12)

    def test_named_joint_mapping_and_missing_rejection(self):
        np.testing.assert_array_equal(full_joint_state_to_solver_joint_state([.3,.1,.2],['c','a','b'],['a','b']),np.array([.1,.2],dtype=np.float32))
        with self.assertRaises(ValueError):full_joint_state_to_solver_joint_state([0],['a'],['absent'])
        with self.assertRaises(ValueError):full_joint_state_to_solver_joint_state([0,1],['a','a'],['a'])

    def test_shape_world_pose_updates_do_not_reuse_changed_cached_vertices(self):
        shape=type('PhysxCollisionShapeBox',(),{})()
        shape.get_half_size=lambda:np.array([.02,.03,.04]);shape.get_local_pose=lambda:Pose([.01,0,0],[1,0,0,0])
        shape.get_contact_offset=lambda:.002;shape.get_rest_offset=lambda:0.;shape.get_collision_groups=lambda:[1,1,0,0]
        actor=SimpleNamespace(position=np.array([.2,.1,.9]),get_name=lambda:'box')
        actor.get_pose=lambda:Pose(actor.position,[1,0,0,0]);actor.get_collision_shapes=lambda:[shape]
        actor.compute_global_aabb_tight=lambda:np.stack((actor.position+[.01,0,0]-shape.get_half_size(),actor.position+[.01,0,0]+shape.get_half_size()))
        planner=planner_view([0,0,0,1,0,0,0],[0,0,0],'aloha-agilex/config')
        a=capture_actor_geometry(actor,'box',planner)[0];actor.position[0]+=.1;b=capture_actor_geometry(actor,'box',planner)[0]
        self.assertEqual(a['vertices'],b['vertices']);self.assertNotEqual(a['solver_pose'],b['solver_pose'])
        self.assertLess(a['body_global_aabb_max_error_m'],1e-12)
        pairs=exact_shape_pairs([a],[b]);self.assertFalse(pairs[0]['mesh_intersection']);self.assertGreater(pairs[0]['surface_distance_m'],.059)
        c=copy.deepcopy(a);c['name']='overlap';pairs=exact_shape_pairs([a],[c]);self.assertTrue(pairs[0]['mesh_intersection'])
        actor.get_collision_shapes=lambda:[shape,shape,shape]
        many=capture_actor_geometry(actor,'box',planner)
        self.assertEqual([s['name'] for s in many],['box__0','box__1','box__2'])

    def test_recorded_multishape_geometry_has_unique_derived_keys(self):
        import json
        path=Path('/nfs_share/lijunhui/Robotwin2/datasets/f3_model_conformance_v1/f3-final-pose-v3-r3063/initial_geometry.json')
        if not path.exists():self.skipTest('recorded capture not available')
        data=json.loads(path.read_text());counts={};names=[]
        for shape in data['shapes']:
            role=shape['role'];i=counts.get(role,0);counts[role]=i+1;names.append(role+'__'+str(i))
        self.assertEqual(len(names),len(set(names)));self.assertEqual(counts['table'],5);self.assertEqual(counts['bottle'],7)

    def test_non_action_driver_has_no_physical_or_trajectory_dispatch(self):
        path=Path(__file__).with_name('f3_conformance.py');tree=ast.parse(path.read_text())
        forbidden={'step','take_dense_action','left_plan_path','left_move_to_pose','_plan_chain','close_gripper','_must_action'}
        calls={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        self.assertFalse(calls&forbidden)

if __name__=='__main__':unittest.main(verbosity=2)
