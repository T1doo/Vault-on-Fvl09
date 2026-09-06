"""One new planner-only scene, three IK problems, at most four route calls.

This module has CPU tests only until a separately signed Guard invokes run().
No robot control executor, scene step, physical grasp, or collector is invoked.
"""
import copy
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path
import numpy as np
import yaml
from .contract import A, P, build_contract, digest
from .state_machine import Budget, open_named_qpos, run_route
from .collision import matrix, pose, support_witness, make_pair_checker, audit_checker, native_can_screen

def dependencies():
    sys.path.insert(0, str(A / 'f2_f3_model_bridge_v1_1'))
    sys.path.insert(1, str(A / 'f2_endpoint_constraint_runtime_v1_1'))
    sys.path.insert(2, str(A))
    spec = importlib.util.spec_from_file_location('inward_parent_panel_v1_1', A / 'f2_endpoint_constraint_runtime_v1_1/panel.py')
    panel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(panel)
    return panel

def prepare_carried_config(scene, can):
    import torch
    from curobo.geom.types import Mesh
    from curobo.geom.sphere_fit import SphereFitType
    from model_apply import runtime_joint_state
    from transforms import full_joint_state_to_solver_joint_state
    planner = scene.robot.left_planner
    names, q = runtime_joint_state(scene)
    cfg = yaml.safe_load(Path(planner.yml_path).read_text(encoding='utf-8'))['robot_cfg']
    start = full_joint_state_to_solver_joint_state(q, names, list(planner.motion_gen.kinematics.joint_names))
    tensor = planner.motion_gen.tensor_args.to_device(start).reshape(1, -1)
    ee = planner.motion_gen.kinematics.get_state(tensor).ee_pose
    ep = ee.position.detach().cpu().numpy().reshape(-1)
    eq = ee.quaternion.detach().cpu().numpy().reshape(-1)
    E_inv = np.linalg.inv(matrix([*ep, *eq]))
    np.random.seed(1531)
    torch.manual_seed(1531)
    spheres, vertices = [], []
    for shape in can:
        mesh = Mesh(name=shape['name'], pose=shape['solver_pose'], vertices=shape['vertices'], faces=shape['faces'])
        fitted = mesh.get_bounding_spheres(max(8, 128 // len(can)), .001, pre_transform_pose=ee.inverse(), tensor_args=planner.motion_gen.tensor_args, fit_type=SphereFitType.VOXEL_VOLUME_SAMPLE_SURFACE)
        spheres.extend({'center': [float(x) for x in s.position], 'radius': float(s.radius)} for s in fitted)
        T = E_inv @ matrix(shape['solver_pose'])
        vertices.extend(np.asarray(shape['vertices']) @ T[:3, :3].T + T[:3, 3])
    if not spheres:
        raise ValueError('missing native carried can')
    kin = cfg['kinematics']
    kin['lock_joints'] = {n: float(q[names.index(n)]) for n in kin['lock_joints']}
    kin['link_names'] = ['fl_link6', 'fl_link7', 'fl_link8']
    base_spheres = yaml.safe_load(Path(kin['collision_spheres']).read_text(encoding='utf-8'))['collision_spheres'] if isinstance(kin['collision_spheres'], str) else copy.deepcopy(kin['collision_spheres'])
    base_spheres['attached_can'] = spheres
    kin['collision_spheres'] = base_spheres
    kin['collision_link_names'] = list(kin['collision_link_names']) + ['attached_can']
    kin['extra_links'] = dict(kin.get('extra_links') or {})
    kin['extra_links']['attached_can'] = {'parent_link_name': 'fl_link6', 'link_name': 'attached_can', 'fixed_transform': [0, 0, 0, 1, 0, 0, 0], 'joint_type': 'FIXED', 'joint_name': 'attached_can_fixed'}
    for name in ('fl_link6', 'fl_link7', 'fl_link8'):
        kin['self_collision_ignore'].setdefault(name, []).append('attached_can')
    return cfg, start, names, q, np.asarray(vertices), E_inv

def build_ik(scene, cfg, export, witness):
    from curobo.wrap.reacher.ik_solver import IKSolver, IKSolverConfig
    from curobo.geom.sdf.world import CollisionCheckerType
    from geometry import make_world
    from ik_config import profile_config
    args = scene.robot.left_planner.motion_gen.tensor_args
    robot, checker, subset = make_pair_checker(cfg, export, witness, args)
    spec = profile_config('K2')
    kw = {**copy.deepcopy(spec['kwargs']), **copy.deepcopy(spec['configs']), 'world_coll_checker': checker, 'tensor_args': args, 'collision_checker_type': CollisionCheckerType.MESH}
    solver = IKSolver(IKSolverConfig.load_from_robot_config(robot, make_world(export), **kw))
    return solver, {'profile': spec, 'actual_checker': audit_checker(solver, checker, export, subset), 'actual_locks': audit_locks(solver, cfg)}

def audit_locks(solver, cfg):
    """Check instantiated full-model locks, not only input configuration."""
    expected = cfg['kinematics']['lock_joints']
    rows = []
    rollouts = list(solver.get_all_rollout_instances())
    if hasattr(solver, 'rollout_fn'):
        rollouts.insert(0, solver.rollout_fn)
    for rollout in rollouts:
        locked = rollout.kinematics.kinematics_config.lock_jointstate
        actual = dict(zip(locked.joint_names, locked.position.detach().cpu().numpy().reshape(-1)))
        if set(actual) != set(expected) or any(abs(float(actual[n]) - float(v)) > 1e-7 for n, v in expected.items()):
            raise ValueError('actual locked-joint state differs from configured carry/release state')
        for name in ('robot_self_collision_constraint', 'primitive_collision_constraint'):
            term = getattr(rollout, name, None)
            if term is not None and not bool(term.enabled):
                raise ValueError('full-constraint term unexpectedly disabled: ' + name)
        rows.append({n: float(v) for n, v in actual.items()})
    if not rows:
        raise ValueError('no actual rollout lock evidence')
    return rows

def install_motiongens(scene, cfg, export, witness=None):
    from curobo.wrap.reacher.motion_gen import MotionGen, MotionGenConfig
    from curobo.geom.sdf.world import CollisionCheckerType
    from geometry import make_world
    from model_apply import verify_actual_world_cache
    planner = scene.robot.left_planner
    args = planner.motion_gen.tensor_args
    audits = {}
    for name in ('motion_gen', 'motion_gen_batch'):
        kwargs = {'interpolation_dt': .004, 'num_trajopt_seeds': 1, 'use_cuda_graph': False, 'tensor_args': args, 'collision_checker_type': CollisionCheckerType.MESH}
        if name == 'motion_gen_batch':
            kwargs['num_graph_seeds'] = 1
        if witness is not None:
            robot, checker, subset = make_pair_checker(cfg, export, witness, args)
            kwargs['world_coll_checker'] = checker
        else:
            robot = copy.deepcopy(cfg)
            kwargs['collision_cache'] = {'mesh': len(export['shapes']), 'obb': 1}
        mg = MotionGen(MotionGenConfig.load_from_robot_config(robot, make_world(export), **kwargs))
        setattr(planner, name, mg)
        audits[name] = {'checker': audit_checker(mg, checker, export, subset) if witness is not None else verify_actual_world_cache(mg, export), 'actual_locks': audit_locks(mg, cfg)}
        mg.reset(reset_seed=True)
    return audits

def run_scene(scene, c, out, budget):
    parent = dependencies()
    from realization_utf8_io_v1 import write_new
    from transforms import reported_eef_goal_to_solver_goal, full_joint_state_to_solver_joint_state
    from model_apply import link_conformance
    from curobo.types.math import Pose
    from curobo.types.state import JointState
    from controlled_multi_future.family_runners_v3_1 import _plan_arm, _merge_arm_terminal_qpos
    if scene.robot.communication_flag:
        raise ValueError('worker path not audited')
    _, live_binding = parent.derive_live_targets(scene, c)
    export, can = parent.world_and_can(scene, scene.robot.left_planner)
    base = scene.robot.left_planner._cmf_solver_base_world_pose
    witness = support_witness(export, can, c['beside_template_actor_pose'], base)
    write_new(out / 'world_geometry.json', export)
    write_new(out / 'support_witness.json', witness)
    write_new(out / 'live_binding.json', live_binding)
    cfg, start, names, full, native, E_inv = prepare_carried_config(scene, can)
    write_new(out / 'carried_robot_config.json', cfg)
    write_new(out / 'live_capture.json', {'joint_names': names, 'qpos': full.tolist(), 'base': base, 'can_shapes': can, 'native_flange_vertices': native.tolist()})
    solver, audit = build_ik(scene, cfg, export, witness)
    conformance = link_conformance(scene, scene.robot.left_planner, solver, solver.tensor_args.to_device(start).reshape(1, -1))
    if any(r['position_error_m'] > .005 or r['orientation_error_rad'] > .05 for r in conformance):
        raise ValueError('actual held link FK mismatch')
    audit['link_FK'] = conformance
    write_new(out / 'IK_model_audit.json', audit)
    solver.reset_seed()
    dummy = Pose.from_list(reported_eef_goal_to_solver_goal(scene.robot, scene.robot.left_planner, c['inward_goals']['C']).tolist())
    seed = solver.tensor_args.to_device(start).reshape(1, 1, -1)
    bank = solver.get_seed(32, dummy, False, seed_config=seed).reshape(1, 32, -1).clone()
    with (out / 'seed_bank.npz').open('xb') as f:
        np.savez_compressed(f, bank=bank.detach().cpu().numpy())
    problems = []
    for key in ('C', 'U_new', 'D_new'):
        ordinal = budget.reserve('ik')
        goal = reported_eef_goal_to_solver_goal(scene.robot, scene.robot.left_planner, c['inward_goals'][key])
        write_new(out / 'IK' / (key + '.start.json'), {'ordinal': ordinal, 'reported_goal': c['inward_goals'][key], 'solver_goal': goal.tolist(), 'seeds': 32, 'iterations': 100})
        result, error = None, None
        try:
            r = solver.solve_single(Pose.from_list(goal.tolist()), retract_config=solver.tensor_args.to_device(start).reshape(1, -1), seed_config=bank.clone(), return_seeds=32, num_seeds=32, use_nn_seed=False)
            rows = parent.cross_validate({'K2': solver}, r.solution, goal)
            for row in rows:
                if row['full_valid']:
                    row['native_can_screen'] = native_can_screen(solver.kinematics, [row['qpos']], native, base, witness, require_supported=key == 'D_new')
                    row['full_valid'] = row['native_can_screen']['pass']
            result = {'solutions': rows, 'reported_success': r.success.detach().cpu().numpy().tolist(), 'full_valid_solution_found': any(x['full_valid'] for x in rows)}
        except BaseException as exc:
            error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        receipt = {'ordinal': ordinal, 'goal': key, 'result': result, 'error': error, 'IK_problem_calls': 1}
        write_new(out / 'IK' / (key + '.done.json'), receipt)
        problems.append(receipt)
        if error is not None:
            raise RuntimeError('IK infrastructure failure: ' + error['message'])
    endpoints = all(p['result']['full_valid_solution_found'] for p in problems)
    if not endpoints:
        return {'pass': False, 'status': 'FIXED_ENDPOINT_GATE_FAILED', 'problems': problems, 'route': None}
    write_new(out / 'carry_motiongen_audit.json', install_motiongens(scene, cfg, export, witness))
    controls = []
    scene.planner_query_limit = 4
    def plan(goal, q, ordinal):
        write_new(out / 'route' / (str(ordinal) + '.start.json'), {'ordinal': ordinal, 'qpos': q.tolist(), 'goal': goal})
        try:
            control = _plan_arm(scene, goal, last_qpos=q, source='F2_inward_' + str(ordinal), arm='left')
        except BaseException as exc:
            write_new(out / 'route' / (str(ordinal) + '.done.json'), {'ordinal': ordinal, 'error': {'type': type(exc).__name__, 'message': str(exc)}, 'executed': False})
            raise
        controls.append(control)
        write_new(out / 'route' / (str(ordinal) + '.done.json'), {'ordinal': ordinal, 'status': control.get('status'), 'query': control.get('_cmf_planner_query'), 'executed': False})
        if control.get('status') == 'Success':
            with (out / 'route' / (str(ordinal) + '.controls.npz')).open('xb') as f:
                np.savez_compressed(f, position=np.asarray(control['position']), velocity=np.asarray(control['velocity']))
        return control
    def screen(control, index):
        if index < 2:
            return native_can_screen(scene.robot.left_planner.motion_gen.kinematics, control['position'], native, base, witness, require_supported=index == 1)
        return {'pass': True, 'released_can_static_in_full_world': True, 'robot_world_constraints_in_planner': True, 'physical_success': False}
    def release(q):
        mapping = [(joint.get_name(), mult, off) for joint, mult, off in scene.robot.left_gripper]
        opened, changes = open_named_qpos(q, names, mapping, scene.robot.left_gripper_scale)
        released_cfg = copy.deepcopy(cfg)
        kin = released_cfg['kinematics']
        kin['collision_link_names'].remove('attached_can')
        kin['collision_spheres'].pop('attached_can')
        kin['extra_links'].pop('attached_can')
        for ignored in kin['self_collision_ignore'].values():
            if 'attached_can' in ignored:
                ignored.remove('attached_can')
        kin['lock_joints'].update(changes)
        actual_q = full_joint_state_to_solver_joint_state(q, names, list(scene.robot.left_planner.motion_gen.kinematics.joint_names))
        st = scene.robot.left_planner.motion_gen.kinematics.get_state(scene.robot.left_planner.motion_gen.tensor_args.to_device(actual_q).reshape(1, -1))
        E_D = matrix([*st.ee_position.detach().cpu().numpy().reshape(-1), *st.ee_quaternion.detach().cpu().numpy().reshape(-1)])
        # Preserve the planned terminal attachment transform exactly. Do not
        # teleport the object to the nominal target to hide solver residual.
        static = []
        for s in can:
            n = copy.deepcopy(s)
            T = E_D @ E_inv @ matrix(s['solver_pose'])
            n['solver_pose'] = pose(T)
            n['name'] = 'released_' + s['name']
            n['role'] = 'released_can'
            n['source_capture_metadata'] = {k: n.pop(k) for k in ('actor_world_pose', 'geometry_sha256', 'body_global_aabb_max_error_m', 'body_global_aabb_source') if k in n}
            n['actor_world_pose'] = pose(matrix(base) @ T @ np.linalg.inv(matrix(s['shape_local_pose'])))
            n['projection_provenance'] = 'planned_D_flange_times_original_attachment'
            n['geometry_sha256'] = digest(n)
            static.append(n)
        released_world = {**export, 'shapes': export['shapes'] + static}
        released_world['geometry_sha256'] = digest(released_world['shapes'])
        audits = install_motiongens(scene, released_cfg, released_world)
        checks = []
        for name in ('motion_gen', 'motion_gen_batch'):
            mg = getattr(scene.robot.left_planner, name)
            from model_apply import query_state
            checks.append(query_state(mg, opened, names)[0])
        # query_state's valid status is inspected explicitly, not truthiness
        # of a nonempty diagnostic dictionary.
        ok = all(x['valid'] for x in checks)
        receipt = {'pass': ok, 'attached_can_present': False, 'released_can_present': True, 'open_named_joints': changes,
                   'qpos_before': q.tolist(), 'qpos_after': opened.tolist(), 'actual_terminal_attachment_continuity': True,
                   'can_pose_was_not_snapped_to_nominal_target': True, 'model_audits': audits, 'start_checks': checks,
                   'physical_release_executed': False}
        write_new(out / 'released_world.json', released_world)
        write_new(out / 'released_robot_config.json', released_cfg)
        write_new(out / 'release_transition.json', receipt)
        return opened, receipt
    route = run_route(full, c['inward_goals'], endpoints_pass=endpoints, budget=budget, plan=plan,
                      merge=lambda q, p: _merge_arm_terminal_qpos(scene, q, p, arm='left'), screen=screen, release=release)
    return {'pass': route['pass'], 'status': route['reason'], 'problems': problems, 'route': route}

def run(manifest):
    """Guard calls this once. No authority is inferred or signed here."""
    sys.path.insert(0, str(A))
    from realization_utf8_io_v1 import write_new
    out = Path(manifest['jobs'][0]['output_namespace'])
    out.mkdir(parents=True, exist_ok=False)
    budget = Budget()
    scene = context = None
    scene_attempts = 0
    result = error = cleanup = None
    before = after = None
    began = time.monotonic()
    try:
        c = build_contract()
        # Constructors/import failures remain visible as infrastructure stops,
        # even when no scene was instantiated and no solver was dispatched.
        from controlled_multi_future.f2_asset_bound_runtime_v3 import RoboTwinRealSapienF2AssetBoundAdapterV3
        from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
        adapter = RoboTwinRealSapienF2AssetBoundAdapterV3(output_root=out / 'adapter', expected_implementation_source_sha256=manifest['implementation_source_sha256'], binding=c['binding'], planner_only=True)
        scene_attempts = 1
        context = _PinnedSapienRenderDeviceContextV1(adapter.scene(c['planned'], phase='F2_NEW_INWARD_PLANNER_ONLY', program=None))
        with context as handle:
            scene = handle.scene
            if not hasattr(scene, 'planner_query_count'):
                scene.planner_query_count = 0
            before = scene.planner_query_count
            try:
                result = run_scene(scene, c, out, budget)
            finally:
                after = getattr(scene, 'planner_query_count', None)
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        cleanup = None if context is None else context.cleanup_receipt
    ik_start = len(list((out / 'IK').glob('*.start.json')))
    ik_done = len(list((out / 'IK').glob('*.done.json')))
    route_start = len(list((out / 'route').glob('*.start.json')))
    route_done = len(list((out / 'route').glob('*.done.json')))
    known = (scene_attempts == 0 and budget.ik == budget.trajectory == 0) or (type(before) is int and type(after) is int and after - before == budget.trajectory)
    accounting = known and ik_start == ik_done == budget.ik and route_start == route_done == budget.trajectory
    safe = error is None and accounting and cleanup is not None and cleanup.get('cleanup_safety_pass') is True
    terminal = {'schema_version': 'f2_inward_planner_only_terminal_v1', 'manifest_sha256': manifest.get('manifest_sha256'),
                'result': result, 'error': error, 'cleanup': cleanup, 'fresh_scene_attempts': scene_attempts,
                'ik_problem_attempts': budget.ik, 'trajectory_queries': after - before if type(before) is int and type(after) is int else (0 if scene_attempts == 0 else None),
                'total_solver_problems': budget.ik + budget.trajectory if known else None,
                'IK_start_receipts': ik_start, 'IK_done_receipts': ik_done, 'route_start_receipts': route_start, 'route_done_receipts': route_done,
                'accounting_complete': accounting, 'physical_execution_count': 0, 'new_raw_trajectories': 0, 'new_roots': 0,
                'collection_calls': 0, 'pass': safe, 'scientific_route_pass': bool(result and result['pass']),
                'elapsed_seconds': time.monotonic() - began, 'status': 'DIAGNOSIS_COMPLETED_WITH_FINDINGS' if safe else 'INFRASTRUCTURE_STOP'}
    terminal['receipt_sha256'] = digest(terminal)
    write_new(out / 'job_terminal.json', terminal)
    return terminal
