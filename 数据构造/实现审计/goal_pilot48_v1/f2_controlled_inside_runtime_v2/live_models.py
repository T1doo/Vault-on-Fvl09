"""Live F2 models. Construction is GPU-only under the caller's Goal Guard.

Import and pure contracts are CPU-safe. This module does not execute actions,
issue work, or relax physical Gates. Only attached_can/box__9 is filterable.
"""
import copy
from pathlib import Path
import numpy as np
import yaml
from goal_pilot48_v1.f2_inward_runtime_v1.contract import digest
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix, pose
from support_pair_collision_v1.policy import PairFilteredWorld, METHODS

MODELS = ('motion_gen', 'motion_gen_batch')
FLOOR = 'box__9'
WALLS = {'box__' + str(i) for i in (0, 1, 2, 3, 6, 8, 10, 11)}


def sealed(value):
    result = copy.deepcopy(value)
    result['receipt_sha256'] = digest(result)
    return result


def verify_seal(value):
    payload = copy.deepcopy(value)
    claimed = payload.pop('receipt_sha256', None)
    if claimed != digest(payload):
        raise ValueError('model evidence self-hash mismatch')


def reduced_floor_world(export):
    names = [s['name'] for s in export['shapes']]
    if len(set(names)) != len(names) or not WALLS.issubset(names):
        raise ValueError('missing/duplicate eight box wall registry')
    if {n for n in names if n.startswith('box__')} != {'box__' + str(i) for i in range(15)}:
        raise ValueError('all fifteen native box pieces required')
    result = copy.deepcopy(export)
    result['shapes'] = [s for s in result['shapes'] if s['name'] != FLOOR]
    result['geometry_sha256'] = digest(result['shapes'])
    return result


def validate_floor_evidence(certificate, geometry, target_actor_pose, box_pose):
    from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import validate_certificate
    from goal_pilot48_v1.f2_inside_native_floor_v1.geometry_verifier import GeometryVerifier
    validate_certificate(certificate)
    verify_seal(geometry)
    actual = GeometryVerifier(certificate).evaluate(
        target_actor_pose, box_pose, binding_sha256=certificate['binding_sha256'])
    if actual != geometry:
        raise ValueError('floor evidence differs from actual target geometry')
    if actual['pass'] is not True or actual['floor_geometry_candidate_indices'] != [9]:
        raise ValueError('only the independently verified box__9 support target admitted')
    if actual['wall_intersection_indices'] or actual['floor_penetration_indices']:
        raise ValueError('native floor/wall penetration')
    return actual


def validate_pair_admission(admission, expected_binding):
    verify_seal(admission)
    if admission.get('schema_version') != 'f2_inside_box9_pair_admission_v1' or admission.get('binding') != expected_binding:
        raise ValueError('stale/wrong actual model/goal binding')
    if admission.get('support_shape_ids') != [FLOOR] or admission.get('native_target_geometry_pass') is not True:
        raise ValueError('unsupported floor partition')
    if set(admission.get('full_checks', {})) != set(MODELS) or set(admission.get('overlaps', {})) != set(MODELS):
        raise ValueError('both actual models and all negative pairs required')
    for name in MODELS:
        check = admission['full_checks'][name]
        if check.get('valid') is not True and 'INVALID_START_STATE_WORLD_COLLISION' not in str(check.get('status')):
            raise ValueError('unrelated full model failure cannot use floor exception')
        for row in admission['overlaps'][name]:
            if row['link'] != 'attached_can' or row['obstacle'] != FLOOR:
                raise ValueError('negative pair outside attached_can/box__9; no scope expansion')


class InsideFloorWorld(PairFilteredWorld):
    def __init__(self, full, reduced, *, names, admission, expected_binding, buffer_factory):
        validate_pair_admission(admission, expected_binding)
        original = {n for n in full.get_obstacle_names() if n}
        filtered = {n for n in reduced.get_obstacle_names() if n}
        if not WALLS.issubset(original) or FLOOR not in original or filtered != original - {FLOOR}:
            raise ValueError('robot full-world or eight-wall partition incomplete')
        if 'attached_can' not in names or all(n == 'attached_can' for n in names):
            raise ValueError('invalid actual robot/carried sphere partition')
        self.full, self.without_support = full, reduced
        self.names, self.attached = list(names), 'attached_can'
        self.buffer_factory, self.buffers = buffer_factory, {}
        self.calls = {name: 0 for name in METHODS}
        self.support_pair_policy_version = 'F2_INSIDE_NATIVE_BOX9_ONLY_V1'


def released_config_and_world(cfg, export, can, names, qpos):
    """Actual capture only; no planned object projection or gripper teleport."""
    names = list(names)
    qpos = np.asarray(qpos, dtype=float)
    if len(set(names)) != len(names) or qpos.shape != (len(names),) or not np.isfinite(qpos).all():
        raise ValueError('invalid actual full joint state')
    out = copy.deepcopy(cfg)
    kin = out['kinematics']
    kin['lock_joints'] = {n: float(qpos[names.index(n)]) for n in kin['lock_joints']}
    kin['collision_link_names'] = [n for n in kin['collision_link_names'] if n != 'attached_can']
    if isinstance(kin['collision_spheres'], dict):
        kin['collision_spheres'].pop('attached_can', None)
    kin.get('extra_links', {}).pop('attached_can', None)
    for key, values in kin.get('self_collision_ignore', {}).items():
        kin['self_collision_ignore'][key] = [n for n in values if n != 'attached_can']
    if not can or any(s['name'] in {w['name'] for w in export['shapes']} for s in can):
        raise ValueError('missing/duplicate actual static can geometry')
    world = copy.deepcopy(export)
    world['shapes'] += copy.deepcopy(can)
    world['geometry_sha256'] = digest(world['shapes'])
    return out, world


class LiveModels:
    def __init__(self, scene, output):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import dependencies
        self.scene, self.output, self.parent = scene, Path(output), dependencies()
        self.serial, self.phase = 0, 'UNINITIALIZED'
        self.cfg = self.native = self.base = None

    def save(self, label, data):
        from realization_utf8_io_v1 import write_new
        self.serial += 1
        value = sealed(data)
        write_new(self.output / ('model_%03d_%s.json' % (self.serial, label)), value)
        return value

    def capture(self):
        from model_apply import runtime_joint_state
        export, can = self.parent.world_and_can(self.scene, self.scene.robot.left_planner)
        names, q = runtime_joint_state(self.scene)
        return export, can, names, np.asarray(q)

    def binding(self, export, can, names, q, target=None):
        return {'world_sha256': digest(export), 'can_sha256': digest(can), 'config_sha256': digest(self.cfg),
                'joint_state_sha256': digest({'names': list(names), 'qpos': q.tolist()}),
                'target_actor_pose_sha256': digest(target), 'scene_identity': id(self.scene),
                'asset_binding_sha256': self.scene._cmf_f2_asset_binding_v3['binding_sha256']}

    def prepare(self):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import prepare_carried_config
        export, can, names, q = self.capture()
        self.cfg, _, _, _, self.native, E_inv = prepare_carried_config(self.scene, can)
        self.base = list(self.scene.robot.left_planner._cmf_solver_base_world_pose)
        self.T_solver_eef_can = E_inv @ np.linalg.inv(matrix(self.base)) @ matrix(can[0]['actor_world_pose'])
        return export, can, names, q

    def query_current(self, label):
        from model_apply import query_state, runtime_joint_state
        names, q = runtime_joint_state(self.scene)
        checks = {}
        for name in MODELS:
            self.save(label + '_' + name + '_start', {'model': name, 'high_level_constraint_call': 1})
            try:
                checks[name] = query_state(getattr(self.scene.robot.left_planner, name), q, names)[0]
                self.save(label + '_' + name + '_done', {'model': name, 'result': checks[name], 'error': None})
            except BaseException as exc:
                self.save(label + '_' + name + '_done', {'model': name, 'error': {'type': type(exc).__name__, 'message': str(exc)}})
                raise
        return checks

    def install_carried_fullworld(self):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import install_motiongens
        export, can, names, q = self.prepare()
        audits = install_motiongens(self.scene, self.cfg, export, witness=None)
        self.phase = 'CARRIED_FULL_WORLD'
        checks = self.query_current('carried_full')
        return self.save('carried_full', {'pass': all(c['valid'] is True for c in checks.values()), 'checks': checks,
            'audits': audits, 'config': self.cfg, 'world': export, 'can': can, 'binding': self.binding(export, can, names, q),
            'all_world_checks_retained': True, 'native_flange_vertices': self.native.tolist(), 'base': self.base,
            'T_solver_eef_can': self.T_solver_eef_can.tolist()})

    def install_floor_only(self, certificate, target_geometry, target_actor_pose):
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import install_motiongens
        from goal_pilot48_v1.f2_prefix_clearance_runtime_v2.certificate import negative_pairs
        from model_apply import runtime_joint_state
        from transforms import full_joint_state_to_solver_joint_state
        export, can, names, q = self.prepare()
        box = next(s for s in export['shapes'] if s['name'] == FLOOR)
        if certificate['binding_sha256'] != self.scene._cmf_f2_asset_binding_v3['binding_sha256']:
            raise ValueError('live layout differs from native-floor certificate')
        validate_floor_evidence(certificate, target_geometry, target_actor_pose, box['actor_world_pose'])
        from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import local_signature
        for actual, expected in ((can, certificate['can_shapes']), ([s for s in export['shapes'] if s['role'] == 'box'], certificate['box_shapes'])):
            if [local_signature(s) for s in actual] != [local_signature(s) for s in expected]:
                raise ValueError('live native geometry differs from target certificate')
        full_audits = install_motiongens(self.scene, self.cfg, export, witness=None)
        checks = self.query_current('floor_full_first')
        overlaps = {}
        for name in MODELS:
            mg = getattr(self.scene.robot.left_planner, name)
            active = full_joint_state_to_solver_joint_state(q, names, list(mg.kinematics.joint_names))
            st = mg.kinematics.get_state(mg.tensor_args.to_device(active).reshape(1, -1))
            spheres = st.get_link_spheres().detach().cpu().numpy()[0]
            kin = mg.kinematics.kinematics_config
            reverse = {v: k for k, v in kin.link_name_to_idx_map.items()}
            links = [reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
            overlaps[name] = negative_pairs(spheres, links, export)
            self.save('floor_actual_spheres_' + name, {'spheres': spheres.tolist(), 'links': links,
                'negative_pairs': overlaps[name], 'actual_model_instance_id': id(mg)})
        binding = self.binding(export, can, names, q, target_actor_pose)
        admission = sealed({'schema_version': 'f2_inside_box9_pair_admission_v1', 'binding': binding,
            'support_shape_ids': [FLOOR], 'native_target_geometry_pass': True, 'target_geometry': target_geometry,
            'certificate_sha256': certificate['receipt_sha256'], 'full_checks': checks, 'overlaps': overlaps})
        self.save('floor_admission', {'admission': admission, 'full_model_audits': full_audits})
        validate_pair_admission(admission, binding)
        audits = self._install_pair(export, admission, binding)
        self.phase = 'CARRIED_BOX9_ONLY'
        checks = self.query_current('floor_pair')
        return self.save('floor_pair', {'pass': all(c['valid'] is True for c in checks.values()),
            'checks': checks, 'audits': audits, 'admission': admission, 'config': self.cfg, 'binding': binding,
            'robot_full_world': True, 'eight_walls_retained_for_can': True})

    def _install_pair(self, export, admission, binding):
        from curobo.types.robot import RobotConfig
        from curobo.geom.sdf.world import WorldCollisionConfig, CollisionCheckerType, CollisionQueryBuffer
        from curobo.geom.sdf.utils import create_collision_checker
        from curobo.wrap.reacher.motion_gen import MotionGen, MotionGenConfig
        from geometry import make_world
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import audit_locks
        from goal_pilot48_v1.f2_inward_runtime_v1.collision import audit_checker
        planner = self.scene.robot.left_planner
        args, audits = planner.motion_gen.tensor_args, {}
        subset = reduced_floor_world(export)
        for name in MODELS:
            cfg = RobotConfig.from_dict(copy.deepcopy(self.cfg), args)
            kin = cfg.kinematics.kinematics_config
            reverse = {v: k for k, v in kin.link_name_to_idx_map.items()}
            names = [reverse[int(i)] for i in kin.link_sphere_idx_map.detach().cpu().numpy().reshape(-1)]
            def checker(world):
                return create_collision_checker(WorldCollisionConfig(tensor_args=args, world_model=make_world(world),
                    checker_type=CollisionCheckerType.MESH, cache={'mesh': len(world['shapes']), 'obb': 1}))
            full, reduced = checker(export), checker(subset)
            pair = InsideFloorWorld(full, reduced, names=names, admission=admission, expected_binding=binding,
                buffer_factory=lambda query, reduced=reduced: CollisionQueryBuffer.initialize_from_shape(query.shape, args, reduced.collision_types))
            kwargs = dict(interpolation_dt=.004, num_trajopt_seeds=1, use_cuda_graph=False, tensor_args=args,
                          collision_checker_type=CollisionCheckerType.MESH, world_coll_checker=pair)
            if name == 'motion_gen_batch':
                kwargs['num_graph_seeds'] = 1
            mg = MotionGen(MotionGenConfig.load_from_robot_config(cfg, make_world(export), **kwargs))
            setattr(planner, name, mg)
            audits[name] = {'checker': audit_checker(mg, pair, export, subset), 'locks': audit_locks(mg, self.cfg)}
            mg.reset(reset_seed=True)
        return audits

    def native_can_actor_poses(self, control):
        if self.phase not in ('CARRIED_FULL_WORLD', 'CARRIED_BOX9_ONLY'):
            raise ValueError('native carried screening requested after release/before model')
        mg = self.scene.robot.left_planner.motion_gen
        q = np.asarray(control['position'], dtype=np.float32)
        if q.ndim != 2 or len(q) < 2 or not np.isfinite(q).all():
            raise ValueError('incomplete native planned samples')
        st = mg.kinematics.get_state(mg.tensor_args.to_device(q))
        pp, qq = st.ee_position.detach().cpu().numpy(), st.ee_quaternion.detach().cpu().numpy()
        return [pose(matrix(self.base) @ matrix([*p, *r]) @ self.T_solver_eef_can) for p, r in zip(pp, qq)]

    def install_actual_released_fullworld(self, release_evidence):
        from controlled_multi_future.family_runners_v3_1 import _arm_gripper_open
        from goal_pilot48_v1.f2_inward_runtime_v1.runtime import install_motiongens
        verify_seal(release_evidence)
        if self.phase != 'CARRIED_BOX9_ONLY' or not all(release_evidence.get(k) is True for k in ('pass', 'full_open_executed', 'gripper_full_open')):
            raise ValueError('real successful controlled release required')
        if not _arm_gripper_open(self.scene, 'left'):
            raise ValueError('actual scene gripper not open under original predicate')
        export, can, names, q = self.capture()
        if release_evidence.get('joint_names') != list(names) or not np.array_equal(release_evidence.get('qpos'), q):
            raise ValueError('release evidence is not actual current joint state')
        if release_evidence.get('can_world_pose') != can[0]['actor_world_pose']:
            raise ValueError('release actor pose stale or snapped to nominal goal')
        cfg, world = released_config_and_world(self.cfg, export, can, names, q)
        audits = install_motiongens(self.scene, cfg, world, witness=None)
        self.cfg, self.phase = cfg, 'RELEASED_FULL_WORLD'
        checks = self.query_current('released_full')
        return self.save('released_full', {'pass': all(c['valid'] is True for c in checks.values()),
            'checks': checks, 'audits': audits, 'config': cfg, 'world': world, 'actual_qpos': q.tolist(),
            'joint_names': list(names), 'release_evidence': release_evidence, 'attached_can_present': False,
            'binding': self.binding(world, can, names, q),
            'can_static_actual_capture': True, 'all_floor_and_wall_checks_restored': True,
            'no_predicted_open_joint_substitution': True, 'can_pose_not_snapped_to_goal': True})
