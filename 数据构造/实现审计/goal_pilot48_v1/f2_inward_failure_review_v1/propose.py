"""One deterministic evidence-derived XY revision; no search or new IK."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import transforms3d as t3d
import yaml
from .analyze import W, A, D, OUT, load, sha, matrix
sys.path.insert(0, str(A / 'f2_f3_model_bridge_v1_1'))
from transforms import TOOL, planner_view, reported_eef_goal_to_solver_goal
from geometry import exact_shape_pairs
from kinematics_cpu import link_world, collision_description
from goal_pilot48_v1.f2_inward_runtime_v1.collision import support_witness

def derive(report):
    P = W / 'Robotwin2/project/RoboTwin'
    cfg = yaml.safe_load((P / 'assets/embodiments/aloha-agilex/config.yml').read_text(encoding='utf-8'))
    pcfg = yaml.safe_load((P / 'assets/embodiments/aloha-agilex/curobo_left.yml').read_text(encoding='utf-8'))
    robot = SimpleNamespace(left_gripper_bias=cfg['gripper_bias'], left_inv_delta_matrix=np.linalg.inv(cfg['delta_matrix']))
    planner = planner_view(cfg['robot_pose'][0], pcfg['planner']['frame_bias'], 'aloha-agilex/curobo_left.yml')
    selected = {}; residuals = {}; replay_errors = {}
    for key in ('C', 'U_new', 'D_new'):
        item = report['records'][key]
        acceptable = [r for r in item['solutions'] if r['recorded_K2'] and r['recorded_orientation_metric'] <= .05]
        if not acceptable: raise ValueError('no existing constraint/orientation-valid pose')
        best = min(acceptable, key=lambda r: (r['FK_position_error_m'], r['index']))
        goal = np.asarray(item['start']['reported_goal'])
        original = reported_eef_goal_to_solver_goal(robot, planner, goal)
        # The live SAPIEN Pose stores float32. The CPU extraction retains
        # float64; report this reconstruction discrepancy, never relabel it
        # byte-identical or alter the actual collector/verifier tolerances.
        replay_errors[key] = float(np.max(np.abs(original - item['start']['solver_goal'])))
        if replay_errors[key] > 1e-7: raise ValueError('saved goal transform outside float32 reconstruction precision')
        # Fixed coordinate Jacobian, not optimization: evaluate three unit
        # translations through the frozen analytical Robot/planner transform.
        J = np.column_stack([reported_eef_goal_to_solver_goal(robot, planner, goal + np.r_[np.eye(3)[i], np.zeros(4)])[:3] - original[:3] for i in range(3)])
        residual = np.linalg.solve(J, np.asarray(best['solver_FK_pose'])[:3] - np.asarray(item['start']['solver_goal'])[:3])
        selected[key] = best
        residuals[key] = residual
    # The more distant constraint+orientation-valid endpoint determines the
    # sole direction. Both existing U/D observations determine one magnitude.
    governing = max(('U_new', 'D_new'), key=lambda k: np.linalg.norm(residuals[k][:2]))
    direction = residuals[governing][:2] / np.linalg.norm(residuals[governing][:2])
    projection = {k: float(np.dot(residuals[k][:2], direction)) for k in ('U_new', 'D_new')}
    length = max(projection.values()) + .005  # one unchanged old position-tolerance margin
    delta = length * direction
    C = np.asarray(report['records']['C']['start']['reported_goal'])[:2]
    U = np.asarray(report['records']['U_new']['start']['reported_goal'])[:2]
    if np.linalg.norm(U + delta - C) >= np.linalg.norm(U - C): raise ValueError('revision does not move toward known feasible C region')
    return {'selected_existing_solution_indices': {k: v['index'] for k, v in selected.items()},
            'selected_existing_position_errors_m': {k: v['FK_position_error_m'] for k, v in selected.items()},
            'all_selected_K2_and_orientation_pass': True, 'governing_endpoint': governing,
            'CPU_float64_vs_saved_float32_goal_max_abs_errors': replay_errors,
            'reported_frame_FK_residuals_xyz_m': {k: v.tolist() for k, v in residuals.items()},
            'direction_xy': direction.tolist(), 'projected_endpoint_deficits_m': projection,
            'additional_margin_m': .005, 'margin_source': 'one original IK position tolerance; no Gate changed',
            'translation_xy_m': delta.tolist(), 'translation_length_m': float(length),
            'distance_to_known_C_before_m': float(np.linalg.norm(U-C)), 'distance_to_known_C_after_m': float(np.linalg.norm(U+delta-C)),
            'target_orientation_change': False, 'layout_candidates_searched': 0}

def geometry_check(proposal):
    capture = load(D / 'live_capture.json'); export = load(D / 'world_geometry.json')
    B = matrix(capture['base']); invB = np.linalg.inv(B)
    def move(shapes, actor):
        rows = []
        for shape in shapes:
            n = copy.deepcopy(shape); T = invB @ matrix(actor) @ matrix(shape['shape_local_pose'])
            n['solver_pose'] = np.r_[T[:3, 3], t3d.quaternions.mat2quat(T[:3, :3])].tolist()
            rows.append(n)
        return rows
    stand_source = [s for s in export['shapes'] if s['role'] == 'stand']
    stand = move(stand_source, proposal['new_stand_actor_pose'])
    finalcan = move(capture['can_shapes'], proposal['new_can_actor_pose'])
    line = load(A / 'F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json')['binding']['layout_payload']
    initialcan = move(capture['can_shapes'], [*line['main_object_pose_xyz'], *line['main_object_orientation_wxyz']])
    support = {'can': support_witness(export, capture['can_shapes'], proposal['new_can_actor_pose'], capture['base']),
               'stand': support_witness(export, stand_source, proposal['new_stand_actor_pose'], capture['base'])}
    objects = finalcan + initialcan + capture['can_shapes'] + [s for s in export['shapes'] if s['role'] in ('box', 'scale')]
    pairs = exact_shape_pairs(stand, objects)
    trace = W / 'Robotwin2/datasets/controlled_multi_future_f2_top_contact_root_v1/f2-top-contact-development-rpc-root-v1-run1/root/canonical_prefix_reference_trace.npz'
    with np.load(trace, allow_pickle=False) as z: initial = z['joint_qpos'][0]
    robot_rows = []
    for label, q in (('initial', initial), ('held', capture['qpos'])):
        named = dict(zip(capture['joint_names'], q)); shapes = []
        for prefix in ('fl', 'fr'):
            for index in range(1, 9):
                link = prefix + '_link' + str(index); right = 'fr_link' + str(index)
                if collision_description(link) != collision_description(right): raise ValueError('left/right collision reuse unsupported')
                for shape in export['shapes']:
                    if shape['role'] != right: continue
                    n = copy.deepcopy(shape); T = invB @ link_world(link, named, capture['base']) @ matrix(shape['shape_local_pose'])
                    n['solver_pose'] = np.r_[T[:3, 3], t3d.quaternions.mat2quat(T[:3, :3])].tolist(); n['name'] = link + '__' + shape['name'].rsplit('__', 1)[-1]
                    shapes.append(n)
        rp = exact_shape_pairs(stand, shapes); robot_rows.append({'state': label, 'pairs': rp}); pairs += rp
    metadata = load(W / 'Robotwin2/project/RoboTwin/assets/objects/071_can/model_data0.json')
    ext = abs(matrix(proposal['new_can_actor_pose'])[:3, :3]) @ (np.asarray(metadata['extents']) * .05 / 2)
    target = np.asarray(proposal['new_target_geometry_xy_m'])
    inside_false = bool(np.any(abs(target - line['inside_region_center_xy_m']) > ext[:2] + line['inside_region_half_xy_m']))
    on_false = bool(np.any(abs(target - line['on_region_center_xy_m']) > ext[:2] + line['on_region_half_xy_m']))
    collisions = [p for p in pairs if p['mesh_intersection'] and p['physical_collision_filter_enabled']]
    return {'pass': not collisions and inside_false and on_false and all(v['pass'] for v in support.values()), 'support': support,
            'forbidden_moving_stand_intersections': collisions, 'checked_exact_pairs': len(pairs),
            'inside_false': inside_false, 'on_false': on_false, 'beside_radial_relation_preserved_by_identical_pair_translation': True,
            'robot_states_checked': [r['state'] for r in robot_rows], 'GPU_IK_qualification': False, 'physical_stability_proven': False}

def build():
    report = load(OUT / 'analysis_v1_1.json'); evidence = derive(report)
    old = load(A / 'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json')['one_proposal']
    delta = np.asarray(evidence['translation_xy_m'])
    new = {'schema_version': 'f2_goal_inward_failure_revision1_cpu_proposal_v1',
           'parent_job_id': 'p48_f2_inward_001', 'parent_analysis_file_sha256': sha(OUT / 'analysis_v1_1.json'),
           'failure_class': 'endpoint_full_constraint_pose_not_solved', 'evidence_based_revision': 1,
           'new_layout_id': 'f2_goal_inward_endpoint_revision1', 'new_root_current_anchor_required': True,
           'derivation': evidence, 'new_target_geometry_xy_m': (np.asarray(old['new_target_geometry_xy_m']) + delta).tolist()}
    for key in ('new_stand_actor_pose', 'new_can_actor_pose', 'new_U_reported_goal', 'new_D_reported_goal'):
        value = np.asarray(old[key]).copy(); value[:2] += delta; new[key] = value.tolist()
    line = load(A / 'F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json')['binding']['layout_payload']
    new['all_beside_candidate_xy_m'] = [(np.asarray(v) + delta).tolist() for v in line['beside_candidate_xy_m']]
    new['geometry_audit'] = geometry_check(new)
    new.update(GPU_IK_verified=False, physical_execution_authorized_by_this_proposal=False,
               next_minimum_gate={'IK_problems': 3, 'conditional_route_queries': 4, 'scenes': 1, 'actions': 0, 'collections': 0},
               unchanged=['can/stand orientation and z', 'C held state and N', 'U-D 80mm', 'inside/on/beside relation definitions', 'original physical Gates', 'assets/grasp transform/seedbank/iterations'])
    return new

if __name__ == '__main__':
    result = build()
    from realization_utf8_io_v1 import write_new
    write_new(OUT / 'proposal_revision1.json', result)
    print(json.dumps({'derivation': result['derivation'], 'geometry': result['geometry_audit'], 'target': result['new_target_geometry_xy_m']}, ensure_ascii=False, indent=2))
