"""F2-only geometric support exception. No F3 hold witness is accepted.

The attached-can view excludes only the identified horizontal table-top mesh.
Every returned carry solution/path is separately screened with native vertices.
This is a planner-only model, not physical release or continuous-sweep proof.
"""
import copy
import sys
from types import SimpleNamespace
import numpy as np
import transforms3d as t3d
from scipy.spatial import ConvexHull
from .contract import A, digest
sys.path.insert(0, str(A))
from support_pair_collision_v1.policy import PairFilteredWorld, METHODS

def matrix(pose):
    p = np.asarray(pose, dtype=float)
    out = np.eye(4)
    out[:3, :3] = t3d.quaternions.quat2mat(p[3:])
    out[:3, 3] = p[:3]
    return out

def pose(T):
    return np.r_[T[:3, 3], t3d.quaternions.mat2quat(T[:3, :3])].tolist()

def world_vertices(shape, base):
    T = matrix(base) @ matrix(shape['solver_pose'])
    return np.asarray(shape['vertices']) @ T[:3, :3].T + T[:3, 3]

def support_witness(export, can_shapes, target_actor, base):
    tables = [s for s in export['shapes'] if s['role'] == 'table']
    if len(tables) < 2:
        raise ValueError('table geometry incomplete')
    top = max(tables, key=lambda s: np.ptp(world_vertices(s, base), axis=0)[:2].prod())
    v = world_vertices(top, base)
    z = float(v[:, 2].max())
    topxy = v[np.abs(v[:, 2] - z) < 1e-5, :2]
    hull = ConvexHull(topxy)
    native = []
    for s in can_shapes:
        T = matrix(target_actor) @ matrix(s['shape_local_pose'])
        native.append(np.asarray(s['vertices']) @ T[:3, :3].T + T[:3, 3])
    native = np.concatenate(native)
    gap = float(native[:, 2].min() - z)
    within = bool(np.all(native[:, :2] @ hull.equations[:, :2].T + hull.equations[:, 2] <= 1e-6))
    w = {'schema_version': 'f2_native_supported_target_planner_witness_v1', 'support_name': top['name'], 'support_plane_z_m': z,
         'table_top_halfspaces_xy': hull.equations.tolist(), 'native_target_bottom_gap_m': gap, 'target_native_footprint_inside': within,
         'numeric_geometry_tolerance_m': 1e-4, 'pass': within and abs(gap) <= 1e-4, 'physical_support_observed': False,
         'world_geometry_sha256': digest(export['shapes']), 'can_geometry_sha256': digest(can_shapes),
         'native_screen_required_for_every_returned_carry_solution_and_path': True}
    w['receipt_sha256'] = digest(w)
    if not w['pass']:
        raise ValueError('new target has no native supported-table witness')
    return w

class F2PairWorld(PairFilteredWorld):
    def __init__(self, full, reduced, *, names, witness, buffer_factory):
        w = dict(witness)
        h = w.pop('receipt_sha256')
        if digest(w) != h or w.get('schema_version') != 'f2_native_supported_target_planner_witness_v1' or not w['pass'] or w['physical_support_observed'] is not False:
            raise ValueError('invalid F2 geometric witness')
        original = {n for n in full.get_obstacle_names() if n}
        filtered = {n for n in reduced.get_obstacle_names() if n}
        support = w['support_name']
        if support not in original or filtered != original - {support}:
            raise ValueError('only the identified tabletop may differ')
        if 'attached_can' not in names or all(n == 'attached_can' for n in names):
            raise ValueError('invalid robot/carried-can sphere partition')
        self.full = full
        self.without_support = reduced
        self.names = list(names)
        self.attached = 'attached_can'
        self.buffer_factory = buffer_factory
        self.buffers = {}
        self.calls = {name: 0 for name in METHODS}
        self.support_pair_policy_version = 'F2_NATIVE_SUPPORT_PLANNER_ONLY_V1_GPU_VALIDATION_PENDING'

def make_pair_checker(robot_cfg, export, witness, tensor_args):
    from curobo.types.robot import RobotConfig
    from curobo.geom.sdf.world import WorldCollisionConfig, CollisionCheckerType, CollisionQueryBuffer
    from curobo.geom.sdf.utils import create_collision_checker
    sys.path.insert(0, str(A / 'f2_f3_model_bridge_v1_1'))
    from geometry import make_world
    cfg = RobotConfig.from_dict(copy.deepcopy(robot_cfg), tensor_args)
    kin = cfg.kinematics.kinematics_config
    reverse = {v: k for k, v in kin.link_name_to_idx_map.items()}
    names = [reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
    subset = {**export, 'shapes': [s for s in export['shapes'] if s['name'] != witness['support_name']]}
    subset['geometry_sha256'] = digest(subset['shapes'])
    def build(e):
        return create_collision_checker(WorldCollisionConfig(tensor_args=tensor_args, world_model=make_world(e), checker_type=CollisionCheckerType.MESH, cache={'mesh': len(e['shapes']), 'obb': 1}))
    full, reduced = build(export), build(subset)
    checker = F2PairWorld(full, reduced, names=names, witness=witness,
                          buffer_factory=lambda q: CollisionQueryBuffer.initialize_from_shape(q.shape, tensor_args, reduced.collision_types))
    return cfg, checker, subset

def audit_checker(solver, checker, export, subset):
    sys.path.insert(0, str(A / 'f2_f3_model_bridge_v1_1'))
    from model_apply import verify_actual_world_cache
    if solver.world_coll_checker is not checker:
        raise ValueError('solver did not retain actual pair checker')
    callbacks = []
    rollouts = solver.get_all_rollout_instances()
    if hasattr(solver, 'rollout_fn'):
        rollouts = [solver.rollout_fn] + rollouts
    for rollout in rollouts:
        for name in ('primitive_collision_cost', 'primitive_collision_constraint'):
            cost = getattr(rollout, name, None)
            if cost is None:
                continue
            for field in ('coll_check_fn', 'sweep_check_fn'):
                if getattr(getattr(cost, field), '__self__', None) is not checker:
                    raise ValueError('cached callback bypasses F2 pair checker')
                callbacks.append(name + '.' + field)
    return {'full': verify_actual_world_cache(SimpleNamespace(world_coll_checker=checker.full), export),
            'can_except_tabletop': verify_actual_world_cache(SimpleNamespace(world_coll_checker=checker.without_support), subset),
            'callback_count': len(callbacks), 'all_robot_tabletop_checks_retained': True}

def native_can_screen(model, positions, can_link_vertices, base, witness, *, require_supported=False):
    q = model.tensor_args.to_device(np.asarray(positions, dtype=np.float32))
    state = model.get_state(q)
    ep = state.ee_position.detach().cpu().numpy()
    eq = state.ee_quaternion.detach().cpu().numpy()
    B = matrix(base)
    vertices = np.asarray(can_link_vertices)
    hs = np.asarray(witness['table_top_halfspaces_xy'])
    rows = []
    for p, r in zip(ep, eq):
        T = B @ matrix([*p, *r])
        v = vertices @ T[:3, :3].T + T[:3, 3]
        gap = float(v[:, 2].min() - witness['support_plane_z_m'])
        inside = bool(np.all(v[:, :2] @ hs[:, :2].T + hs[:, 2] <= 1e-6))
        # Conservative: carried native geometry must remain above and within
        # the identified support top. No full tabletop collision disabling.
        rows.append({'bottom_gap_m': gap, 'footprint_inside': inside, 'pass': gap >= -1e-4 and inside})
    good = bool(rows) and all(r['pass'] for r in rows)
    if require_supported:
        good = good and abs(rows[-1]['bottom_gap_m']) <= 1e-4
    return {'pass': good, 'samples': len(rows), 'minimum_gap_m': min((r['bottom_gap_m'] for r in rows), default=None),
            'last_gap_m': rows[-1]['bottom_gap_m'] if rows else None, 'all_footprints_inside': all(r['footprint_inside'] for r in rows),
            'supported_endpoint_required': require_supported, 'discrete_only': True, 'physical_success': False}
