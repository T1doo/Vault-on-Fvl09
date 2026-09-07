"""CPU synthetic backend/negative fixtures; never a physical qualification."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import live_models as m


def admission():
    return m.sealed({'schema_version': 'f2_inside_box9_pair_admission_v1', 'binding': {'CPU_FIXTURE': True},
        'support_shape_ids': ['box__9'], 'native_target_geometry_pass': True,
        'full_checks': {n: {'valid': True} for n in m.MODELS},
        'overlaps': {n: [] for n in m.MODELS}})


class Checker:
    def __init__(self, names, value): self.names, self.value = names, value
    def get_obstacle_names(self): return self.names
    def get_sphere_distance(self, query_sphere, collision_query_buffer, return_loss=False):
        import torch
        return torch.full(query_sphere.shape[:-1], self.value, dtype=query_sphere.dtype)
    get_sphere_collision = get_sphere_distance
    get_swept_sphere_distance = get_sphere_distance
    get_swept_sphere_collision = get_sphere_distance


class Tests(unittest.TestCase):
    def test_only_one_floor_removed_immutable_other_world(self):
        world = {'shapes': [{'name': 'box__' + str(i), 'CPU_FIXTURE': i} for i in range(15)] + [{'name': 'table__0'}]}
        before = copy.deepcopy(world)
        reduced = m.reduced_floor_world(world)
        self.assertEqual(world, before)
        self.assertEqual(reduced['shapes'], [s for s in world['shapes'] if s['name'] != 'box__9'])
        bad = copy.deepcopy(world); bad['shapes'].pop(0)
        with self.assertRaises(ValueError): m.reduced_floor_world(bad)

    def test_all_four_actual_pair_methods_keep_robot_full(self):
        import torch
        names = sorted(m.WALLS | {'box__9', 'table__0', 'scale__0'})
        pair = m.InsideFloorWorld(Checker(names, 7.), Checker([n for n in names if n != 'box__9'], 3.),
            names=['fl_link7', 'attached_can', 'fl_link8'], admission=admission(), expected_binding={'CPU_FIXTURE': True}, buffer_factory=lambda q: object())
        for method in m.METHODS:
            got = getattr(pair, method)(torch.zeros((1, 2, 3, 4)), object())
            self.assertEqual(got.tolist(), [[[7., 3., 7.], [7., 3., 7.]]])
            self.assertEqual(pair.calls[method], 1)
        with self.assertRaises(RuntimeError): pair.enable_obstacle('box__9', False)
        with self.assertRaises(RuntimeError): pair.load_collision_model(None)

    def test_partition_rejects_wall_or_other_world_removal(self):
        full = sorted(m.WALLS | {'box__9', 'table__0'})
        for excluded in ({'box__9', 'box__0'}, {'box__9', 'table__0'}, {'box__0'}):
            with self.assertRaises(ValueError):
                m.InsideFloorWorld(Checker(full, 1.), Checker([n for n in full if n not in excluded], 0.),
                    names=['robot', 'attached_can'], admission=admission(), expected_binding={'CPU_FIXTURE': True}, buffer_factory=lambda q: None)

    def test_stale_binding_false_gate_or_other_negative_pair(self):
        with self.assertRaises(ValueError): m.validate_pair_admission(admission(), {'CPU_FIXTURE': False})
        for change in ('floor', 'robot', 'table', 'status', 'missing', 'false'):
            a = admission(); a.pop('receipt_sha256')
            if change in ('floor', 'robot', 'table'):
                a['overlaps']['motion_gen'] = [{'link': 'fl_link7' if change == 'robot' else 'attached_can',
                    'obstacle': 'table__0' if change == 'table' else 'box__7'}]
            elif change == 'status': a['full_checks']['motion_gen'] = {'valid': False, 'status': 'SELF_COLLISION'}
            elif change == 'missing': a['full_checks'].pop('motion_gen_batch')
            else: a['native_target_geometry_pass'] = False
            with self.assertRaises(ValueError): m.validate_pair_admission(m.sealed(a), {'CPU_FIXTURE': True})

    def test_released_actual_q_not_commanded_open_static_can_unchanged(self):
        cfg = {'kinematics': {'lock_joints': {'finger': .001}, 'collision_link_names': ['robot', 'attached_can'],
            'collision_spheres': {'robot': [1], 'attached_can': [2]}, 'extra_links': {'attached_can': {}},
            'self_collision_ignore': {'robot': ['attached_can', 'pad']}}}
        export = {'shapes': [{'name': 'box__9', 'solver_pose': [9]}]}
        can = [{'name': 'held_can__0', 'solver_pose': [7], 'actor_world_pose': [8]}]
        snapshot = copy.deepcopy((cfg, export, can))
        released, world = m.released_config_and_world(cfg, export, can, ['arm', 'finger'], [1.3, .04321])
        self.assertEqual(released['kinematics']['lock_joints'], {'finger': .04321})
        self.assertNotIn('attached_can', released['kinematics']['collision_link_names'])
        self.assertEqual(world['shapes'], export['shapes'] + can)
        self.assertEqual(released['kinematics']['self_collision_ignore']['robot'], ['pad'])
        self.assertEqual((cfg, export, can), snapshot)
        with self.assertRaises(ValueError): m.released_config_and_world(cfg, export, can, ['finger'], [float('nan')])

    def test_real_native_target_evidence_and_wrong_target(self):
        from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import reference_certificate, load, A
        c = reference_certificate()
        g = load(A / 'goal_pilot48_v1/f2_inside_native_floor_v1/saved_contact_geometry.json')
        self.assertTrue(m.validate_floor_evidence(c, g, g['can_world_pose'], g['box_world_pose'])['pass'])
        p = list(g['can_world_pose']); p[2] += .002
        with self.assertRaises(ValueError): m.validate_floor_evidence(c, g, p, g['box_world_pose'])
        bad = copy.deepcopy(g); bad.pop('receipt_sha256'); bad['floor_geometry_candidate_indices'] = [9, 7]
        with self.assertRaises(ValueError): m.validate_floor_evidence(c, m.sealed(bad), g['can_world_pose'], g['box_world_pose'])

    def test_release_requires_real_current_joint_and_pose(self):
        from goal_pilot48_v1.f2_inward_runtime_v1 import runtime
        instance = m.LiveModels.__new__(m.LiveModels)
        instance.phase = 'CARRIED_BOX9_ONLY'; instance.scene = SimpleNamespace(is_left_gripper_open=lambda: True)
        instance.capture = lambda: ({'shapes': []}, [{'actor_world_pose': [1, 2, 3, 1, 0, 0, 0]}], ['finger'], np.array([.04]))
        e = {'pass': True, 'full_open_executed': True, 'gripper_full_open': True, 'joint_names': ['finger'],
             'qpos': [.03], 'can_world_pose': [1, 2, 3, 1, 0, 0, 0], 'CPU_FIXTURE': True}
        with patch.object(runtime, 'install_motiongens') as install:
            with self.assertRaisesRegex(ValueError, 'actual current joint'): instance.install_actual_released_fullworld(m.sealed(e))
            e['qpos'] = [.04]; e['can_world_pose'][0] = 0
            with self.assertRaisesRegex(ValueError, 'stale or snapped'): instance.install_actual_released_fullworld(m.sealed(e))
            self.assertFalse(install.called)

    def test_actual_solver_attachment_mapping_not_reported_goal(self):
        import torch
        instance = m.LiveModels.__new__(m.LiveModels)
        instance.phase = 'CARRIED_FULL_WORLD'; instance.base = [10, 0, 0, 1, 0, 0, 0]
        instance.T_solver_eef_can = m.matrix([0, 0, .2, 1, 0, 0, 0])
        st = SimpleNamespace(ee_position=torch.tensor([[1., 2., 3.], [4., 5., 6.]]),
                             ee_quaternion=torch.tensor([[1., 0., 0., 0.]] * 2))
        mg = SimpleNamespace(tensor_args=SimpleNamespace(to_device=torch.tensor), kinematics=SimpleNamespace(get_state=lambda q: st))
        instance.scene = SimpleNamespace(robot=SimpleNamespace(left_planner=SimpleNamespace(motion_gen=mg)))
        result = instance.native_can_actor_poses({'position': [[0]*6, [1]*6]})
        np.testing.assert_allclose(np.asarray(result)[:, :3], [[11, 2, 3.2], [14, 5, 6.2]])
        instance.phase = 'RELEASED_FULL_WORLD'
        with self.assertRaises(ValueError): instance.native_can_actor_poses({'position': [[0]*6, [1]*6]})


if __name__ == '__main__': unittest.main()
