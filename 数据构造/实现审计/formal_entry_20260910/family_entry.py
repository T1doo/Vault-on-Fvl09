"""Nine-cell F1 native dispatch and disk structural finalization, CPU-safe import.

No CLI execution authorization is conferred by this module. Native execution must
be invoked by the external Guard in its authorized UUID-bound child.
"""
from pathlib import Path
import hashlib
import json
import os
from copy import deepcopy
import numpy as np
from native_f1 import run_native_cohort

REALIZATIONS = ('r_pc', 'r_inv_path', 'r_inv_motion')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    os.replace(temporary, path)



def cohort_root(output, realization):
    output=Path(output)
    pointer=output / realization / 'cohort_pointer.json'
    if not pointer.exists(): return output / realization / 'root'
    relative=Path(json.loads(pointer.read_text())['root_relative'])
    if relative.is_absolute() or '..' in relative.parts: raise ValueError('cohort pointer escapes root')
    return output / realization / relative


def planned_cells(spec):
    if spec['family'] not in ('F1', 'F2', 'F3', 'F4'):
        raise ValueError('unknown family')
    programs = [p['program_id'] for p in spec['programs']]
    if len(programs) != 3 or len(set(programs)) != 3 or tuple(spec['realizations']) != REALIZATIONS:
        raise ValueError('requires three unique programs and all three realizations')
    return [{'program_id': p, 'realization_id': r, 'cell_key': f'{p}:{r}', 'strict_prefix_cohort': 'r_pc' if r == 'r_pc' else None} for r in REALIZATIONS for p in programs]


def validate_native_f1(spec):
    planned_cells(spec)
    if spec['family'] != 'F1':
        raise ValueError('native family entry currently implemented for F1 only')
    if {p['program_id'] for p in spec['programs']} != {'F1-red', 'F1-green', 'F1-blue'}:
        raise ValueError('F1 identity mismatch')
    layout = spec['scene_layout']
    if set(layout['object_xyz_by_role']) != {'red', 'green', 'blue'}:
        raise ValueError('native scene layout lacks all roles')
    if len(layout['common_box_pose_wxyz']) != 7:
        raise ValueError('native box requires seven-pose')
    for p in spec['programs']:
        if p['target_role'] != p['program_id'].split('-')[1]:
            raise ValueError('program role mismatch')
    rules = spec['variant_rules']
    if not 0 < abs(rules['r_inv_path']['safe_horizontal_y_offset_m']) <= .05:
        raise ValueError('path variation outside frozen bounded range')
    hold = rules['r_inv_motion']['post_prefix_hold_frames']
    if type(hold) is not int or not 0 < hold <= 250:
        raise ValueError('motion variation requires bounded integer hold')


def _run_root(*, spec, output, source_sha, resume=False, cohort_runner=run_native_cohort):
    """Completed cohorts skip; failed cohort recovers only its missing cells.

    Requalification is charged, and accepted cells require exact regenerated
    current/prefix/control bindings. Unreconciled RUNNING jobs remain blocked.
    """
    validate_native_f1(spec)
    output = Path(output)
    checkpoint_path = output / 'checkpoint.json'
    fingerprint = digest(spec)
    if checkpoint_path.exists():
        if not resume:
            raise FileExistsError('root exists; explicit resume required')
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint['input_sha256'] != fingerprint or checkpoint['source_sha256'] != source_sha:
            raise ValueError('resume spec or source changed')
        if checkpoint['status'] == 'RUNNING':
            raise RuntimeError('interrupted job requires owned cleanup reconciliation before recovery')
    else:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError('unowned nonempty output')
        checkpoint = {'status': 'READY', 'input_sha256': fingerprint, 'source_sha256': source_sha, 'completed': {}, 'planned_cells': planned_cells(spec)}
        write(output / 'root_spec.json', spec)
        write(checkpoint_path, checkpoint)
    for realization in REALIZATIONS:
        receipt_path = cohort_root(output, realization) / 'root_receipt.json'
        if realization in checkpoint['completed']:
            if not receipt_path.exists() or hashlib.sha256(receipt_path.read_bytes()).hexdigest() != checkpoint['completed'][realization]:
                raise RuntimeError('resume receipt absent or changed')
            from native_raw_contract import validate_native_raw_contract as validate_raw_artifact_contract
            for program in spec['programs']:
                raw=receipt_path.parent / 'branches' / program['program_id'] / 'raw'
                if validate_raw_artifact_contract(raw)['pass'] is not True:
                    raise RuntimeError('completed cell changed before further dispatch')
            continue
        checkpoint.update(status='RUNNING', active_realization=realization)
        write(checkpoint_path, checkpoint)
        try:
            cohort_runner(spec=deepcopy(spec), realization=realization, output=output / realization, source_sha=source_sha)
            receipt_path = cohort_root(output, realization) / 'root_receipt.json'
            receipt = json.loads(receipt_path.read_text())
            if receipt.get('status') != 'accepted':
                raise RuntimeError(f'{realization} native cohort failed')
            checkpoint['completed'][realization] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            checkpoint.update(status='READY', active_realization=None)
            write(checkpoint_path, checkpoint)
        except BaseException as exc:
            checkpoint.update(status='FAILED', error_type=type(exc).__name__, error=str(exc))
            write(checkpoint_path, checkpoint)
            raise
    result = finalize_structure(spec=spec, output=output)
    checkpoint['status'] = 'STRUCTURE_READY' if result['pass'] else 'INCOMPLETE'
    write(checkpoint_path, checkpoint)
    return result


def finalize_structure(*, spec, output):
    """Recompute disk integrity, shapes, t0 equality and pc-prefix actual arrays.

    Family semantic functions recompute saved terminal geometry/state/contact
    independently. Synthetic fixture data can pass these checks but remains
    research-ineligible; no fixture is counted as a native physical run.
    """
    from native_raw_contract import validate_native_raw_contract as validate_raw_artifact_contract
    from controlled_multi_future.canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
    from controlled_multi_future.anchor import compare_anchors
    output = Path(output)
    checks, cells, actions, observations, realized = {}, [], {}, [], {}
    for realization in REALIZATIONS:
        root = cohort_root(output, realization)
        provisional=root/'provisional_programs.json'
        checks[realization+':frozen_candidates']=provisional.exists() and json.loads(provisional.read_text()).get('programs')==spec['programs']
        for program in spec['programs']:
            key = f"{program['program_id']}:{realization}"
            raw = root / 'branches' / program['program_id'] / 'raw'
            try:
                audit = validate_raw_artifact_contract(raw)
                checks[key + ':raw'] = audit['pass'] is True
                provenance=audit.get('manifest',{}).get('provenance',{})
                checks[key+':root_identity']=provenance.get('formal_root_id')==spec['root_id'] and provenance.get('formal_spec_sha256')==spec['spec_sha256'] and provenance.get('program_id')==program['program_id'] and provenance.get('realization_spec',{}).get('realization')==realization
                checks[key+':native_source']=provenance.get('synthetic') is False
                with np.load(raw / 'raw_streams.npz', allow_pickle=False) as data:
                    actions[key] = data['stream__controller_effective_setpoint'].copy()
                    realized[key] = data['stream__realized_eef'].copy()
                branch = json.loads((raw.parent / 'receipt.json').read_text())
                actual_sha = hashlib.sha256((raw / 'raw_streams.npz').read_bytes()).hexdigest()
                checks[key + ':source_bound_semantic'] = branch.get('program_id') == program['program_id'] and branch.get('verifier', {}).get('pass') is True and branch.get('raw_manifest', {}).get('raw_streams_npz_sha256') == actual_sha
                exported = export_native_cell(spec=spec, output=output, program_id=program['program_id'], realization=realization)
                if spec['family']=='F1':
                    from f1_disk_verifier import verify_f1_disk as semantic_verifier
                elif spec['family']=='F4':
                    from native_f4_disk_verifier import verify_f4_disk as semantic_verifier
                else:raise ValueError('native family verifier absent')
                semantic=semantic_verifier(raw_dir=raw,spec=spec,program=program)
                write(raw.parent / ('independent_'+spec['family'].lower()+'_semantics.json'),semantic)
                checks[key+':independent_semantics']=semantic['pass']
                checks[key + ':model_export'] = exported['inputs']['state'].shape == (76,) and set(exported) == {'inputs','supervision','audit'} and 'target' not in exported['inputs']
                cells.append({'cell_key': key, 'raw': str(raw.relative_to(output)), 'raw_sha256': hashlib.sha256((raw / 'raw_streams.npz').read_bytes()).hexdigest()})
            except (OSError, KeyError, ValueError) as exc:
                checks[key + ':raw'] = False
                cells.append({'cell_key': key, 'error': str(exc)})
        for capture in sorted((output / realization).glob('**/observations/*/capture.json')):
            meta = json.loads(capture.read_text())
            path = capture.parent / 'current.npz'
            checks[str(capture.relative_to(output))] = meta.get('spec_sha256') == spec['spec_sha256'] and hashlib.sha256(path.read_bytes()).hexdigest() == meta['npz_sha256']
            with np.load(path, allow_pickle=False) as data:
                arrays = {k: data[k].copy() for k in data.files}
            observations.append((arrays, json.loads((capture.parent / 'anchor.json').read_text())))
    checks['nine_unique_cells'] = len(cells) == 9 and len({c['cell_key'] for c in cells}) == 9
    checks['nine_distinct_raw_files'] = len({c.get('raw') for c in cells if 'raw' in c}) == 9
    checks['current_observations_present'] = len(observations) >= 9
    if observations:
        reference, anchor = observations[0]
        checks['all_current_arrays_identical'] = all(set(v) == set(reference) and all(v[k].dtype == reference[k].dtype and v[k].shape == reference[k].shape and v[k].tobytes() == reference[k].tobytes() for k in reference) for v, _ in observations)
        checks['all_anchors_equivalent'] = all(compare_anchors(anchor, a)['equivalent'] for _, a in observations)
    try:
        prefix_manifest, prefix = load_canonical_prefix_artifact(cohort_root(output, 'r_pc') / 'canonical_prefix_artifact')
        checks['pc_prefix_root_identity']=prefix_manifest['root_slot_id']==spec['root_id'] and prefix_manifest['family']==spec['family']
        expected = prefix['effective_setpoint_actions']
        checks['pc_actual_prefix'] = True
        fields={'effective_setpoint_actions':('stream__controller_effective_setpoint',0),'requested_commands':('stream__requested_command',0),'component_masks':('stream__component_masks',0),'left_gripper_joint_drive_targets':('audit__left_gripper_joint_drive_target',1),'right_gripper_joint_drive_targets':('audit__right_gripper_joint_drive_target',1),'left_gripper_joint_drive_velocity_targets':('audit__left_gripper_joint_drive_velocity_target',1),'right_gripper_joint_drive_velocity_targets':('audit__right_gripper_joint_drive_velocity_target',1)}
        for program in spec['programs']:
            with np.load(cohort_root(output,'r_pc')/'branches'/program['program_id']/'raw/raw_streams.npz',allow_pickle=False) as raw:
                for name,(field,start) in fields.items():
                    actual=raw[field][start:start+len(expected)]; reference=prefix[name]
                    exact=actual.shape==reference.shape and actual.dtype==reference.dtype and actual.tobytes()==reference.tobytes()
                    checks[f'pc_prefix:{program["program_id"]}:{name}']=exact
                    checks['pc_actual_prefix'] = checks['pc_actual_prefix'] and exact
    except (OSError, KeyError, ValueError):
        checks['pc_actual_prefix'] = False
    for p in spec['programs']:
        name = p['program_id']
        baseline = actions.get(f'{name}:r_pc')
        for realization in REALIZATIONS[1:]:
            variant = actions.get(f'{name}:{realization}')
            checks[f'{name}:{realization}:different_effective_actions'] = baseline is not None and variant is not None and not np.array_equal(baseline, variant)
        base_path = realized.get(f'{name}:r_pc')
        path = realized.get(f'{name}:r_inv_path')
        if base_path is not None and path is not None:
            a = base_path[np.linspace(0,len(base_path)-1,min(500,len(base_path)),dtype=int), :3]
            b = path[np.linspace(0,len(path)-1,min(500,len(path)),dtype=int), :3]
            deviation = max(max(float(np.min(np.linalg.norm(b-point,axis=1))) for point in a),max(float(np.min(np.linalg.norm(a-point,axis=1))) for point in b))
            checks[f'{name}:realized_path_difference'] = deviation > .001
        else:
            checks[f'{name}:realized_path_difference'] = False
        motion = actions.get(f'{name}:r_inv_motion')
        checks[f'{name}:realized_hold_duration_difference'] = baseline is not None and motion is not None and len(motion) >= len(baseline) + spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames']

    structural_pass=all(v for k,v in checks.items() if not k.endswith(':native_source'))
    result = {'schema': 'formal_nine_structure_v1', 'family': spec['family'], 'root_id': spec['root_id'], 'checks': checks, 'cells': cells, 'pass': structural_pass, 'native_physical_evidence': all(checks.get(c['cell_key']+':native_source') is True for c in cells), 'independent_semantic_recomputed': all(checks.get(c['cell_key']+':independent_semantics') is True for c in cells), 'model_export_verified': all(checks.get(c['cell_key']+':model_export') is True for c in cells), 'source_bound_semantic_verified': all(checks.get(c['cell_key']+':source_bound_semantic') is True for c in cells), 'research_eligible': all(checks.values()), 'full_stage1_scientific_supported': False, 'physical_execution_authorized': False, 'strict_prefix_cohort': 'r_pc', 'variant_pairing': 'within-program versus r_pc'}
    write(output / 'independent_structure.json', result)
    return result


def state38(value):
    value = np.asarray(value)
    if value.shape == (38,):
        return value.copy()
    if value.shape == (76,) and np.array_equal(value[:38], value[38:]):
        return value[:38].copy()
    raise ValueError('robot state is neither 38DOF nor byte-equivalent duplicated storage')


def export_native_cell(*, spec, output, program_id, realization):
    """Load actual capture and raw arrays; answers never enter the inputs mapping."""
    output = Path(output)
    root = cohort_root(output, realization)
    raw_path = root / 'branches' / program_id / 'raw' / 'raw_streams.npz'
    observations = output / realization / 'scene_instances' / 'observations'
    manifest = json.loads((raw_path.parent / 'manifest.json').read_text()) if (raw_path.parent / 'manifest.json').exists() else {}
    bound = manifest.get('provenance', {}).get('formal_current_capture_path')
    captures = [Path(bound)] if bound else list(observations.glob(f'{spec["family"].lower()}-strict_prefix_branch_{program_id}-v1_2-*/capture.json'))
    if bound and not Path(bound).resolve().is_relative_to(output.resolve()):
        raise ValueError('capture provenance leaves current root')
    if len(captures) != 1:
        raise ValueError('exactly one actual branch current capture required')
    capture_path = captures[0]
    meta = json.loads(capture_path.read_text())
    current_path = capture_path.parent / 'current.npz'
    if meta['spec_sha256'] != spec['spec_sha256'] or hashlib.sha256(current_path.read_bytes()).hexdigest() != meta['npz_sha256']:
        raise ValueError('capture identity/integrity mismatch')
    with np.load(current_path, allow_pickle=False) as data:
        rgb = {k: data[k].copy() for k in spec.get('cameras', {}).get('required', ('head_camera','left_camera','right_camera'))}
        qpos, qvel = state38(data['robot_qpos']), state38(data['robot_qvel'])
    if any(v.dtype != np.uint8 or v.ndim != 3 or v.shape[-1] != 3 or ('cameras' in spec and v.shape[:2] != (spec['cameras']['height'],spec['cameras']['width'])) for v in rgb.values()):
        raise ValueError('invalid original RGB')
    with np.load(raw_path, allow_pickle=False) as data:
        future = data['stream__controller_effective_setpoint'].copy()
        anchor_file=capture_path.parent/'anchor.json'
        if anchor_file.exists():
            anchor=json.loads(anchor_file.read_text())
            actors=anchor.get('actor_states',{});facilities=anchor.get('facility_poses',{})
            if set(actors)|set(facilities) != {r['role'] for r in spec.get('roles',[])}:
                raise ValueError('complete anchor roles missing')
            for role in spec.get('roles',[]):
                name=role['role'];pose=actors[name]['pose'] if name in actors else facilities[name]
                if not np.array_equal(np.asarray(pose),data['audit__role_object_pose__'+name][0]):
                    raise ValueError('anchor/raw role row0 mismatch')
        elif spec.get('roles'):
            raise ValueError('complete anchor absent')
        if not np.array_equal(qpos, state38(data['stream__realized_qpos'][0])) or not np.array_equal(qvel, state38(data['stream__realized_qvel'][0])):
            raise ValueError('current/raw row0 mismatch')
    if future.ndim != 2 or future.shape[1] != 26 or not len(future) or not np.isfinite(future).all():
        raise ValueError('invalid actual 26D future')
    return {'inputs': {'rgb': rgb, 'state': np.concatenate((qpos,qvel)), 'future': future, 'candidate_set': deepcopy(spec['programs'])},
            'supervision': {'program_id': program_id},
            'audit': {'spec_sha256':spec['spec_sha256'], 'capture_sha256':hashlib.sha256(capture_path.read_bytes()).hexdigest(), 'raw_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(), 'capture_source':'native_original_t0', 'realization_id':realization}}


def run_root(*, spec, output, source_sha, resume=False, cohort_runner=run_native_cohort):
    import fcntl
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    lock=output.parent / (output.name + '.formal_root.lock')
    with lock.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            return _run_root(spec=spec,output=output,source_sha=source_sha,resume=resume,cohort_runner=cohort_runner)
        finally:
            fcntl.flock(handle,fcntl.LOCK_UN)


def run_family_root(*, spec, output, authorization):
    if authorization.get('gpu_execution_authorized') is not True or authorization.get('spec_sha256') != spec['spec_sha256']:
        raise ValueError('requires separately authorized UUID-bound native worker and exact spec')
    from scene_plan import validate_resolved
    from file_source_pin import validate as validate_source_pin
    validate_resolved(spec)
    validate_source_pin(authorization)
    planned_cells(spec)
    if spec['family'] == 'F1':
        result=run_root(spec=spec,output=output,source_sha=authorization['implementation_source_sha256'],resume=authorization.get('resume',False))
        validate_source_pin(authorization);return result
    if spec['family'] in ('F2','F3'):
        from native_f2f3 import run_native_root
        result=run_native_root(spec,output,authorization)
        validate_source_pin(authorization);return result
    if spec['family'] == 'F4':
        from native_f4 import run_native_root
        result=run_native_root(spec,output,authorization)
        validate_source_pin(authorization);return result
    raise ValueError('unsupported family')


def get_call_budget(spec):
    if spec['family']!='F1':
        return {'family':spec['family'],'budget_owner':'native family module; no inherited F1 estimate'}
    return {'family':'F1','allowed_physical_gpu_indices':list(range(8)),
        'per_cohort_stages':{'pristine':{'fresh':1,'action':0,'collection':0,'solver_cap':0},'task_geometry':{'fresh':3,'action':0,'collection':0,'solver_cap':0},'canonical_prefix_reference':{'fresh':1,'action':1,'collection':0,'solver_cap':16},'suffix_preflight_with_prefix_replay':{'fresh':3,'action':3,'collection':0,'solver_cap':48},'cell_execution':{'fresh':3,'action':3,'collection':3,'solver_cap':0}},
        'base_nine_cells':{'fresh':33,'action':21,'collection':9,'solver_cap':192},
        'recovery_per_affected_cohort':{'fresh':'8 + missing_cells','action':'4 + missing_cells','collection':'missing_cells','solver_cap':64,'accepted_cell_reexecution':False},
        'max_cohort_invocations':2,'max_root_with_one_recovery_each_cohort':{'fresh':66,'action':42,'collection':18,'solver_cap':384},
        'gpu_reservation_seconds':None,'job_timeout_seconds':None,'first_wave_dispatch_cap':None,
        'gpu_timing_status':'external Guard contract required; no CPU estimate is measured GPU cost',
        'solver_cap_basis':'native prefix scene planner_query_limit=16; each suffix preflight cumulative planner_query_limit=16 incl target construction; task geometry and execution frozen control make no new planner queries',
        'authorization_granted':False}


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Formal nine-cell native family entry; authorization-bound GPU child only')
    parser.add_argument('--spec',required=True,type=Path)
    parser.add_argument('--authorization',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--describe',action='store_true')
    args=parser.parse_args(argv)
    spec=json.loads(args.spec.read_text())
    if args.describe:
        from scene_plan import validate_resolved
        validate_resolved(spec);print(json.dumps(get_call_budget(spec),sort_keys=True));return 0
    if args.authorization is None or args.output is None:parser.error('--authorization and --output required for native execution')
    authorization=json.loads(args.authorization.read_text())
    result=run_family_root(spec=spec,output=args.output,authorization=authorization)
    print(json.dumps({'root_id':spec['root_id'],'pass':result.get('pass'),'research_eligible':result.get('research_eligible',False),'native_physical_evidence':result.get('native_physical_evidence',False)},sort_keys=True))
    return 0 if result.get('pass') is True else 1

if __name__=='__main__':
    raise SystemExit(main())
