"""CPU replay of saved F2 endpoint solutions; no new IK/planner/scene."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
W = Path('/nfs_share/lijunhui')
A = W / 'Vault-on-Fvl09/数据构造/实现审计'
D = W / 'Robotwin2/datasets/p48_f2_inward_001'
OUT = Path(__file__).parent
sys.path.insert(0, str(A / 'f3_model_replay_v1'))
from kinematics_cpu import root_transform, link_world

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def matrix(p): return t3d.affines.compose(p[:3], t3d.quaternions.quat2mat(p[3:]), [1, 1, 1])

def sphere_geometry(cfg, named):
    rows = []
    base_inv = np.linalg.inv(root_transform('fl_base_link', named))
    for link in cfg['collision_link_names']:
        T = base_inv @ root_transform('fl_link6' if link == 'attached_can' else link, named)
        for sphere in cfg['collision_spheres'][link]:
            p = T[:3, :3] @ np.asarray(sphere['center']) + T[:3, 3]
            rows.append({'link': link, 'position': p, 'radius': float(sphere['radius']) + cfg['collision_sphere_buffer'],
                         'self_radius': float(sphere['radius']) + cfg['self_collision_buffer'].get(link, 0.)})
    return rows

def model_collision_audit(cfg, named, export, witness):
    import trimesh
    spheres = sphere_geometry(cfg, named)
    points = np.asarray([r['position'] for r in spheres])
    radius = np.asarray([r['radius'] for r in spheres])
    rows = []
    for shape in export['shapes']:
        mesh = trimesh.Trimesh(vertices=shape['vertices'], faces=shape['faces'], process=True)
        mesh.apply_transform(matrix(shape['solver_pose']))
        distances = -trimesh.proximity.signed_distance(mesh, points) - radius
        valid = np.ones(len(spheres), dtype=bool)
        if shape['name'] == witness['support_name']:
            valid = np.asarray([r['link'] != 'attached_can' for r in spheres])
        index = int(np.flatnonzero(valid)[np.argmin(distances[valid])])
        rows.append({'obstacle': shape['name'], 'role': shape['role'], 'link': spheres[index]['link'], 'buffered_clearance_m': float(distances[index])})
    self_rows = []
    ignore = cfg['self_collision_ignore']
    for i, first in enumerate(spheres):
        for second in spheres[i+1:]:
            a, b = first['link'], second['link']
            if a == b or b in ignore.get(a, []) or a in ignore.get(b, []): continue
            # Locked CuRobo generator subtracts the world sphere buffer again
            # for its self-collision thresholds (cuda_robot_generator.py:764).
            gap = float(np.linalg.norm(first['position'] - second['position']) - first['self_radius'] - second['self_radius'])
            if gap < 0:
                self_rows.append({'links': [a, b], 'buffered_clearance_m': gap})
    return {'world_nearest': sorted(rows, key=lambda x: x['buffered_clearance_m'])[:8],
            'self_buffered_overlaps': sorted(self_rows, key=lambda x: x['buffered_clearance_m'])[:12],
            'CPU_approximate_sphere_model_not_new_GPU_constraint_check': True,
            'self_uses_original_radius_plus_self_collision_buffer': True}

def analyze():
    capture = load(D / 'live_capture.json')
    base = capture['base']; B = matrix(base)
    cfg = load(D / 'carried_robot_config.json')['kinematics']
    named0 = dict(zip(capture['joint_names'], capture['qpos']))
    export = load(D / 'world_geometry.json'); witness = load(D / 'support_witness.json')
    records = {}; max_position_metric_error = 0.
    for key in ('C', 'U_new', 'D_new'):
        start = load(D / 'IK' / (key + '.start.json'))
        result = load(D / 'IK' / (key + '.done.json'))['result']
        rows = []
        for i, solution in enumerate(result['solutions']):
            named = dict(named0); named.update({f'fl_joint{j+1}': q for j, q in enumerate(solution['qpos'])})
            T = np.linalg.inv(root_transform('fl_base_link', named)) @ root_transform('fl_link6', named)
            goal = np.asarray(start['solver_goal'])
            error = T[:3, 3] - goal[:3]
            max_position_metric_error = max(max_position_metric_error, abs(float(np.linalg.norm(error)) - solution['FK_position_error_m']))
            world = B @ T
            rows.append({'index': i, 'qpos': solution['qpos'], 'recorded_full_valid': solution['full_valid'], 'recorded_K2': solution['constraint_checks']['K2'],
                         'solver_FK_pose': [*T[:3, 3], *t3d.quaternions.mat2quat(T[:3, :3])], 'world_FK_pose': [*world[:3, 3], *t3d.quaternions.mat2quat(world[:3, :3])],
                         'solver_FK_error_xyz_m': error.tolist(), 'FK_position_error_m': float(np.linalg.norm(error)),
                         'recorded_orientation_metric': solution['FK_rotation_metric_sin_half_angle'], 'joint_limit_min_margin_rad': solution['joint_limit_min_margin_rad']})
        best = min(rows, key=lambda x: x['FK_position_error_m'])
        named = dict(named0); named.update({f'fl_joint{j+1}': q for j, q in enumerate(best['qpos'])})
        # Also select a known-positive C solution for model interpretation.
        if key == 'C':
            best = min([r for r in rows if r['recorded_full_valid']], key=lambda x: x['FK_position_error_m'])
            named = dict(named0); named.update({f'fl_joint{j+1}': q for j, q in enumerate(best['qpos'])})
        records[key] = {'start': start, 'returned_count': len(rows), 'K2_pass_count': sum(r['recorded_K2'] for r in rows), 'full_valid_count': sum(r['recorded_full_valid'] for r in rows),
                        'within_position_tolerance_count': sum(r['FK_position_error_m'] <= .005 for r in rows),
                        'within_orientation_metric_count': sum(r['recorded_orientation_metric'] <= .05 for r in rows),
                        'minimum_joint_limit_margin_rad': min(r['joint_limit_min_margin_rad'] for r in rows), 'solutions': rows, 'selected_closest': best,
                        'selected_CPU_collision': model_collision_audit(cfg, named, export, witness)}
    if max_position_metric_error > 2e-6:
        raise ValueError('CPU URDF FK does not reproduce saved GPU FK error')
    result = {'schema_version': 'f2_inward_001_saved_IK_CPU_review_v1', 'records': records, 'maximum_CPU_vs_recorded_FK_metric_error_m': max_position_metric_error,
              'new_solver_problems': 0, 'new_scenes': 0, 'physical_execution': 0,
              'input_hashes': {str(p): sha(p) for p in [D / 'live_capture.json', D / 'carried_robot_config.json', D / 'world_geometry.json', D / 'support_witness.json', *sorted((D / 'IK').glob('*.json'))]}}
    return result

if __name__ == '__main__':
    r = analyze()
    sys.path.insert(0, str(A))
    from realization_utf8_io_v1 import write_new
    write_new(OUT / 'analysis_v1_1.json', r)
    print(json.dumps({k: {x:v[x] for x in ('K2_pass_count', 'full_valid_count', 'within_position_tolerance_count', 'minimum_joint_limit_margin_rad', 'selected_closest', 'selected_CPU_collision')} for k,v in r['records'].items()}, ensure_ascii=False, indent=2))
