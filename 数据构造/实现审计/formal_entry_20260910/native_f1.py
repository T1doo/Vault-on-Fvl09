"""New native F1 integration. Importing this file does not import the simulator.

Old nonformal receipts retain their original labels. This adapter is callable only
inside a separately authorized GPU child; CPU tests do not construct native scenes.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import numpy as np


def _canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    ).hexdigest()


def build_motion_baseline_planner_source(*, binding, spec, program_id, baseline_manifest):
    """Build a verifiable provenance envelope for timing-only control reuse.

    The motion realization deliberately invokes no live planner.  Its collision
    provenance therefore comes only from the sealed r_pc execution spec; the
    receiver must re-load that artifact and verify this envelope instead of
    trusting a free-form source string.
    """
    if not isinstance(binding, dict) or not isinstance(baseline_manifest, dict):
        raise ValueError('motion baseline planner source requires structured binding and artifact')
    item = (binding.get('programs') or {}).get(program_id)
    execution_spec = baseline_manifest.get('execution_spec')
    if not isinstance(item, dict) or not isinstance(execution_spec, dict):
        raise ValueError('motion baseline planner source lacks bound execution spec')
    queries = execution_spec.get('planner_query_receipts')
    targets = execution_spec.get('targets')
    if not isinstance(queries, list) or not queries or not isinstance(targets, list) or not targets:
        raise ValueError('motion baseline planner source lacks historical planner receipts or targets')
    if len(queries) < len(targets):
        raise ValueError('historical planner receipt count does not cover frozen suffix targets')
    if any(
        not isinstance(q, dict)
        or q.get('status') not in ('Success', 'success')
        or not isinstance(q.get('query_id'), int)
        or not isinstance(q.get('source'), str)
        or not q.get('source')
        for q in queries
    ):
        raise ValueError('historical planner receipts are incomplete or non-successful')
    artifact_sha = baseline_manifest.get('artifact_sha256')
    prefix_sha = baseline_manifest.get('prefix_artifact_sha256')
    execution_sha = baseline_manifest.get('execution_spec_sha256')
    if not all(isinstance(x, str) and x for x in (artifact_sha, prefix_sha, execution_sha)):
        raise ValueError('baseline artifact lacks immutable identity hashes')
    historical_sources = sorted({q['source'] for q in queries})
    description = (
        f"sealed r_pc artifact {artifact_sha} historical official CuRobo per-segment "
        f"receipts ({len(queries)}); no new planner invoked"
    )
    return {
        'schema': 'f1_motion_baseline_planner_source_v1',
        'kind': 'sealed_r_pc_artifact_historical_planner_evidence',
        'baseline_root_id': baseline_manifest.get('root_slot_id'),
        'baseline_program_id': baseline_manifest.get('program_id'),
        'baseline_realization': 'r_pc',
        'baseline_artifact_sha256': artifact_sha,
        'baseline_manifest_artifact_sha256': item.get('manifest_artifact_sha256'),
        'baseline_manifest_file_sha256': item.get('manifest_file_sha256'),
        'baseline_arrays_file_sha256': item.get('arrays_file_sha256'),
        'baseline_execution_spec_sha256': execution_sha,
        'baseline_prefix_artifact_sha256': prefix_sha,
        'historical_planner_receipt_count': len(queries),
        'historical_planner_receipts_sha256': _canonical_hash(queries),
        'historical_planner_receipt_scope': 'execution_spec.planner_query_receipts for all frozen baseline suffix targets',
        'historical_planner_sources': historical_sources,
        'collision_model_scope': 'official CuRobo planner success/failure per frozen segment in the sealed r_pc artifact',
        'planner_invoked': False,
        'live_planner_query_count': 0,
        'quantitative_collision_clearance_available': False,
        'description': description,
    }


def validate_motion_baseline_planner_source(source, *, binding, spec, program_id, baseline_manifest):
    """Validate the structured provenance envelope at the family-gate boundary."""
    if not isinstance(source, dict):
        raise ValueError('motion planner source envelope is missing')
    expected = build_motion_baseline_planner_source(
        binding=binding, spec=spec, program_id=program_id, baseline_manifest=baseline_manifest
    )
    for key, value in expected.items():
        if source.get(key) != value:
            raise ValueError(f'motion planner source binding mismatch: {key}')
    if source.get('planner_invoked') is not False or source.get('live_planner_query_count') != 0:
        raise ValueError('motion planner source falsely claims a live planner call')
    if source.get('quantitative_collision_clearance_available') is not False:
        raise ValueError('motion planner source overclaims quantitative clearance')
    if source.get('description') != expected['description']:
        raise ValueError('motion planner source description is not generated from the artifact')
    return True


def audit_motion_start_qpos(*, baseline_start_qpos, actual_qpos, arm_qpos_indices, tolerance_rad=1e-5):
    """Apply the branch's selected-arm start rule to a saved hold state."""
    baseline = np.asarray(baseline_start_qpos, dtype=np.float64).reshape(-1)
    actual = np.asarray(actual_qpos, dtype=np.float64).reshape(-1)
    indices = [int(index) for index in arm_qpos_indices]
    if baseline.shape != actual.shape or baseline.ndim != 1:
        raise ValueError('motion start qpos shapes differ')
    if not indices or len(set(indices)) != len(indices) or any(index < 0 or index >= len(baseline) for index in indices):
        raise ValueError('motion start qpos arm index mapping is invalid')
    all_error = float(np.max(np.abs(actual - baseline)))
    arm_error = float(np.max(np.abs(actual[indices] - baseline[indices])))
    return {
        'baseline_start_qpos_sha256': hashlib.sha256(np.ascontiguousarray(baseline).tobytes()).hexdigest(),
        'actual_start_qpos_sha256': hashlib.sha256(np.ascontiguousarray(actual).tobytes()).hexdigest(),
        'arm_qpos_indices': indices,
        'all_qpos_max_error_rad': all_error,
        'selected_arm_max_error_rad': arm_error,
        'tolerance_rad': float(tolerance_rad),
        'all_qpos_pass': all_error <= float(tolerance_rad),
        'selected_arm_pass': arm_error <= float(tolerance_rad),
        'pass': arm_error <= float(tolerance_rad),
        'mapping_source': 'runtime _execute_cached_segment arm_joint_names resolved against active_joints; indices persisted in segment receipts',
    }


def change_path_targets(targets, offset):
    result = deepcopy(targets)
    matches = [x for x in result if x['segment_id'] == 'safe_horizontal']
    if len(matches) != 1 or not 0 < abs(offset) <= .05:
        raise ValueError('one safe_horizontal target and bounded nonzero offset required')
    pose = np.asarray(matches[0]['pose'], dtype=float).copy()
    pose[1] += offset
    matches[0]['pose'] = pose
    return result


class VariantLegacy:
    def __init__(self, original, realization, rules):
        self.original, self.realization, self.rules = original, realization, rules

    def __getattr__(self, key):
        return getattr(self.original, key)

    def build_targets(self, *args, **kwargs):
        targets, extra = self.original.build_targets(*args, **kwargs)
        baseline=next(np.asarray(t['pose'],float).copy() for t in targets if t['segment_id']=='safe_horizontal')
        extra={**extra,'formal_path_baseline_pose':baseline.tolist(),'formal_path_prescribed_offset_y_m':float(self.rules['r_inv_path']['safe_horizontal_y_offset_m']) if self.realization=='r_inv_path' else 0.0}
        if self.realization == 'r_inv_path':
            offset = float(self.rules['r_inv_path']['safe_horizontal_y_offset_m'])
            targets = change_path_targets(targets, offset)
            extra = {**extra, 'formal_path_offset_y_m': offset}
        return targets, extra



def execute_with_stage_capture(controller,scene,program,execution_spec,replay,realization_spec,spec):
    """Same mature native primitive, instrumented through isolated function globals."""
    import types
    from controlled_multi_future.family_runners_v3_3 import F1ControllerV3_3
    from controlled_multi_future.probes.runtime_trace import _gripper_joint_qpos
    from f1_disk_verifier import frozen_contract
    c=frozen_contract(spec);native=F1ControllerV3_3.execute_frozen_suffix_spec;env=dict(native.__globals__)
    if list(scene.robot.left_gripper_scale)!=[c['release']['closed_master_m'],c['release']['open_master_m']]:raise ValueError('actual robot gripper calibration differs from frozen formal contract')
    stages={'executing_arm':'left','sample_rate_hz':250,'program_id':program['program_id'],'realization_id':realization_spec['realization'],'subject_actor_name':'formal_f1_'+program['target_role'],'robot_link_names':sorted({link.get_name() for entity in (scene.robot.left_entity,scene.robot.right_entity) for link in entity.get_links()}),'prefix_acceptance_end_row':len(scene.trace)-1,'gripper_link_names':list(scene.selected_gripper_links()),'gripper_scale_m':list(scene.robot.left_gripper_scale),'stages':[]}
    scene._formal_f1_stages=stages
    def record(name,callback):
        item={'name':name,'start_row':len(scene.trace)-1};stages['stages'].append(item)
        try:return callback()
        finally:item['end_row']=len(scene.trace)-1
    original_segment=env['_execute_cached_segment'];original_action=env['_must_action'];original_wait=env['_wait_and_record'];original_stable=env['_stable_and_support']
    env['_execute_cached_segment']=lambda current,frozen,controls,index:record(frozen['targets'][index]['segment_id'],lambda:original_segment(current,frozen,controls,index))
    def action(current,value,label):
        if label==program['target_role']+'_close_gripper':name='gripper_close'
        elif label==program['target_role']+'_release':name='gripper_open'
        else:raise ValueError('unregistered F1 action phase')
        return record(name,lambda:original_action(current,value,label))
    env['_must_action']=action;waits=[]
    def wait(current,frames):
        if len(waits)>=2:raise ValueError('unregistered extra hold')
        name=('release_settle','rest_settle')[len(waits)];waits.append(name)
        return record(name,lambda:original_wait(current,frames))
    env['_wait_and_record']=wait
    env['_stable_and_support']=lambda current,actor,support,frames=None:original_stable(current,actor,support,frames=c['terminal']['stable_window_frames'])
    env['_arm_gripper_open']=lambda current,arm:((_gripper_joint_qpos(current.robot,arm)[0]-c['release']['closed_master_m'])/(c['release']['open_master_m']-c['release']['closed_master_m']))>c['release']['actual_open_fraction_gt']
    env['PROVISIONAL_RUNTIME_THRESHOLDS']={'non_target_displacement_m':c['non_task']['position_m'],'stable_linear_speed_mps':c['terminal']['object_linear_m_s'],'eef_stationary_angular_speed_rps':c['terminal']['object_angular_rad_s'],'rest_position_error_m':c['terminal']['eef_position_m'],'orientation_error':c['terminal']['eef_orientation_rad'],'eef_stationary_linear_speed_mps':c['terminal']['eef_linear_m_s']}
    count=c['motion']['additional_frames'] if realization_spec['realization']=='r_inv_motion' else 0
    motion_receipt = None
    if realization_spec['realization']=='r_inv_motion' and getattr(scene, '_cmf_f1_motion_hold_execution_applied', False):
        raise ValueError('r_inv_motion post-prefix hold applied more than once')
    scene._cmf_f1_motion_hold_active = realization_spec['realization']=='r_inv_motion'
    before_hold = len(getattr(scene, 'trace', []))
    record('post_prefix_hold',lambda:original_wait(scene,count))
    if realization_spec['realization']=='r_inv_motion':
        scene._cmf_f1_motion_hold_execution_applied = True
        motion_receipt = {
            'state_before':'S_prefix',
            'state_after':'S_motion_start',
            'frames':int(count),
            'trace_rows_added':int(len(getattr(scene, 'trace', []))-before_hold),
            'applied_once':True,
            'planner_and_execution_boundary_shared':True,
        }
    try:
        result=types.FunctionType(native.__code__,env)(controller,scene,program,execution_spec,replay,realization_spec)
    except BaseException:
        from family_entry import write
        write(Path(scene._formal_current_capture_path).parent/'partial_stage_evidence.json',stages)
        raise
    result['provenance']['formal_f1_stages']=stages
    result['provenance']['formal_f1_contract']=c
    if isinstance(execution_spec.get('motion_control_source'), dict):
        result['provenance']['motion_control_source'] = deepcopy(execution_spec['motion_control_source'])
    if motion_receipt is not None:
        result['motion_hold_boundary']=motion_receipt
        result['provenance']['motion_hold_boundary']=motion_receipt
    return result


def legacy_comparison_view(value,compatibility,kind):
    """Explicit audit-only source alias; original observations/anchors stay unchanged.

    Only approved implementation provenance is normalized for the inherited
    artifact comparator. Model hashes, numeric state, physics and all other
    source fields are untouched. The actual new capture is persisted separately.
    """
    if compatibility is None:return value
    from controlled_multi_future.current_hasher import hash_json
    if compatibility.get('status')!='CPU_REVIEWED_APPLICABLE' or compatibility.get('scientific_contract_unchanged') is not True:raise ValueError('source comparison needs explicit compatible approval')
    old,new=compatibility['old_source_sha256'],compatibility['new_source_sha256']
    result=deepcopy(value)
    if kind=='anchor':
        config=result['physics_config']
        if config['implementation_source_sha256'] not in (old,new):raise ValueError('undeclared anchor implementation source')
        config['implementation_source_sha256']=old
        result['anchor_sha256']=hash_json({k:v for k,v in result.items() if k!='anchor_sha256'})
    elif kind=='current':
        config=result['reconstruction_spec_audit']['simulation_configuration']
        if config['implementation_source_sha256'] not in (old,new):raise ValueError('undeclared current implementation source')
        config['implementation_source_sha256']=old
        result['reconstruction_spec_components']['simulation_configuration_sha256']=hash_json(config)
        result['reconstruction_spec_aggregate_sha256']=hash_json(result['reconstruction_spec_components'])
        result['aggregate_sha256']=hash_json({'model_visible':result['model_visible_aggregate_sha256'],'reconstruction_spec':result['reconstruction_spec_aggregate_sha256']})
        result['audit_full_aggregate_sha256']=hash_json({'same_current':result['aggregate_sha256'],'hidden_physical_state':result['hidden_physical_aggregate_sha256']})
    else:raise ValueError('unsupported comparison view')
    return result

def _bound_workspace_path(value):
    """Resolve a recovery binding without allowing path escape or symlinks."""
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("motion baseline binding path must be absolute")
    resolved = path.resolve()
    workspace = Path("/nfs_share/lijunhui").resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError("motion baseline binding path leaves the workspace")
    for item in (path, *path.parents):
        try:
            if item.is_relative_to(workspace) and item.is_symlink():
                raise ValueError("motion baseline binding may not traverse symlinks")
        except AttributeError:
            # Python 3.10 has Path.is_relative_to; this branch is defensive for
            # the small CPU helpers that may be imported by older fixtures.
            if str(item).startswith(str(workspace)) and item.is_symlink():
                raise ValueError("motion baseline binding may not traverse symlinks")
    return resolved


def _load_motion_baseline_controls(*, binding, spec, program_id):
    """Load a sealed r_pc suffix; motion never falls back to live planning.

    The returned controls are the validated arrays from the baseline artifact,
    not a resampled or re-planned trajectory.  This helper is intentionally
    CPU-only and is also used by the recovery preflight tests.
    """
    if not isinstance(binding, dict) or binding.get("schema") != "f1_motion_baseline_binding_v1":
        raise ValueError("r_inv_motion requires a versioned baseline binding")
    if binding.get("status") != "CPU_REVIEWED_APPLICABLE":
        raise ValueError("motion baseline binding is not CPU-reviewed applicable")
    if binding.get("root_id") != spec.get("root_id") or binding.get("spec_sha256") != spec.get("spec_sha256"):
        raise ValueError("motion baseline binding root/spec mismatch")
    item = (binding.get("programs") or {}).get(program_id)
    if not isinstance(item, dict):
        raise ValueError(f"motion baseline binding lacks {program_id}")
    required = (
        "artifact_dir",
        "manifest_file_sha256",
        "manifest_artifact_sha256",
        "arrays_file_sha256",
        "program_id",
        "root_id",
        "realization",
    )
    if any(key not in item for key in required):
        raise ValueError(f"motion baseline binding for {program_id} is incomplete")
    if item["program_id"] != program_id or item["root_id"] != spec.get("root_id") or item["realization"] != "r_pc":
        raise ValueError(f"motion baseline binding identity mismatch for {program_id}")
    artifact_dir = _bound_workspace_path(item["artifact_dir"])
    manifest_path = artifact_dir / "frozen_suffix_artifact.json"
    arrays_path = artifact_dir / "suffix_controls.npz"
    if not manifest_path.is_file() or not arrays_path.is_file():
        raise ValueError(f"motion baseline artifact is incomplete for {program_id}")
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != item["manifest_file_sha256"]:
        raise ValueError(f"motion baseline manifest changed for {program_id}")
    if hashlib.sha256(arrays_path.read_bytes()).hexdigest() != item["arrays_file_sha256"]:
        raise ValueError(f"motion baseline arrays changed for {program_id}")
    from controlled_multi_future.frozen_suffix_artifact_v1 import load_frozen_suffix_artifact
    manifest, arrays, controls = load_frozen_suffix_artifact(artifact_dir)
    if manifest.get("artifact_sha256") != item["manifest_artifact_sha256"]:
        raise ValueError(f"motion baseline artifact hash changed for {program_id}")
    if manifest.get("root_slot_id") != spec.get("root_id") or manifest.get("family") != "F1" or manifest.get("program_id") != program_id:
        raise ValueError(f"motion baseline artifact identity mismatch for {program_id}")
    expected_prefix = item.get("prefix_artifact_sha256")
    if expected_prefix is not None and manifest.get("prefix_artifact_sha256") != expected_prefix:
        raise ValueError(f"motion baseline prefix binding mismatch for {program_id}")
    if len(controls) != len(manifest.get("execution_spec", {}).get("targets", [])):
        raise ValueError(f"motion baseline controls/targets mismatch for {program_id}")
    return manifest, arrays, controls


def native_adapter(*, spec, realization, output_root, source_sha, recovery_context=None):
    # These imports are lazy; constructor source integrity is checked by native base.
    from f1_disk_verifier import frozen_contract
    frozen_contract(spec)
    from file_source_pin import inventory,bundle_hash
    source_bundle=bundle_hash(inventory())
    from controlled_multi_future.real_sapien_adapter_f1_batch_v1 import RoboTwinRealSapienF1BatchPilotAdapterV1
    from controlled_multi_future.family_runners_v3_3 import F1ControllerV3_3, _wait_and_record
    from controlled_multi_future.real_sapien_adapter_v1_1 import _dual_entity_values

    motion_baseline_binding = (recovery_context or {}).get("motion_baseline_binding")

    class Controller(F1ControllerV3_3):
        def __init__(self):
            super().__init__()
            self.legacy = VariantLegacy(self.legacy, realization, spec['variant_rules'])

        def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
            if realization == 'r_inv_motion':
                from f1_disk_verifier import frozen_contract
                if getattr(scene, '_cmf_f1_motion_hold_planning_applied', False):
                    raise RuntimeError('r_inv_motion planner hold applied more than once')
                if motion_baseline_binding is None:
                    raise ValueError('r_inv_motion requires a sealed r_pc baseline; live suffix planning is forbidden')
                frames = frozen_contract(spec)['motion']['additional_frames']
                before = len(getattr(scene, 'trace', []))
                scene._cmf_f1_motion_hold_active = True
                _wait_and_record(scene, frames)
                scene._cmf_f1_motion_hold_planning_applied = True
                scene._cmf_f1_motion_hold_planning_receipt = {
                    'state_before': 'S_prefix',
                    'state_after': 'S_motion_start',
                    'frames': int(frames),
                    'trace_rows_added': int(len(getattr(scene, 'trace', [])) - before),
                    'applied_once': True,
                }
                baseline_manifest, baseline_arrays, baseline_controls = _load_motion_baseline_controls(
                    binding=motion_baseline_binding,
                    spec=spec,
                    program_id=program['program_id'],
                )
                planner_source = build_motion_baseline_planner_source(
                    binding=motion_baseline_binding,
                    spec=spec,
                    program_id=program['program_id'],
                    baseline_manifest=baseline_manifest,
                )
                baseline_qpos = np.asarray(baseline_arrays['actual_prefix_end_qpos'], dtype=np.float64).reshape(-1)
                actual_qpos = np.asarray(scene.robot.left_entity.get_qpos(), dtype=np.float64).reshape(-1)
                if actual_qpos.shape != baseline_qpos.shape:
                    raise ValueError('motion hold start qpos shape differs from sealed baseline')
                start_error = float(np.max(np.abs(actual_qpos - baseline_qpos)))
                if start_error > 1e-3:
                    raise ValueError(f'motion hold changed suffix start qpos beyond safety tolerance: {start_error:.9g} rad')
                execution_spec = deepcopy(baseline_manifest['execution_spec'])
                execution_spec['motion_control_source'] = {
                    'schema': 'f1_motion_baseline_control_source_v1',
                    'kind': 'sealed_r_pc_suffix_artifact',
                    'baseline_root_id': baseline_manifest['root_slot_id'],
                    'baseline_program_id': baseline_manifest['program_id'],
                    'baseline_realization': 'r_pc',
                    'baseline_artifact_sha256': baseline_manifest['artifact_sha256'],
                    'baseline_manifest_file_sha256': motion_baseline_binding['programs'][program['program_id']]['manifest_file_sha256'],
                    'baseline_manifest_artifact_sha256': motion_baseline_binding['programs'][program['program_id']]['manifest_artifact_sha256'],
                    'baseline_arrays_file_sha256': motion_baseline_binding['programs'][program['program_id']]['arrays_file_sha256'],
                    'baseline_execution_spec_sha256': baseline_manifest['execution_spec_sha256'],
                    'baseline_prefix_artifact_sha256': baseline_manifest['prefix_artifact_sha256'],
                    'control_count': len(baseline_controls),
                    'hold_start_max_qpos_error_rad': start_error,
                    'planner_invoked': False,
                    'planner_collision_source': planner_source,
                }
                scene._cmf_suffix_preflight_partial_receipt = {
                    'schema_version': 'cmf_f1_motion_baseline_replay_preflight_v1',
                    'program_id': program['program_id'],
                    'realization': 'r_inv_motion',
                    'baseline_artifact_sha256': baseline_manifest['artifact_sha256'],
                    'baseline_execution_spec_sha256': baseline_manifest['execution_spec_sha256'],
                    'baseline_controls_reused_exactly': True,
                    'planner_invoked': False,
                    'planner_query_count': 0,
                    'hold_start_max_qpos_error_rad': start_error,
                }
                return {
                    'planner_solvable': True,
                    'planner_query_count': 0,
                    'failure_type': None,
                    'evidence': {
                        'planner_invoked': False,
                        'planner_query_receipts': [],
                        'baseline_control_replay': execution_spec['motion_control_source'],
                        'planner_collision_check_source': planner_source['description'],
                        'planner_collision_source': planner_source,
                        'quantitative_collision_clearance_available': False,
                        'actual_prefix_end_qpos_sha256': baseline_manifest['actual_prefix_end_qpos_sha256'],
                        'hold_start_max_qpos_error_rad': start_error,
                        'hold_start_safe': True,
                    },
                    'actual_prefix_end_qpos_sha256': baseline_manifest['actual_prefix_end_qpos_sha256'],
                    'execution_spec': execution_spec,
                    '_execution_controls': baseline_controls,
                    '_actual_prefix_end_qpos': baseline_qpos,
                }
            result = super().plan_suffix_from_actual_prefix_end_state(scene, program, replay)
            planning_receipt = getattr(
                scene, '_cmf_f1_motion_hold_planning_receipt', None
            )
            if planning_receipt is not None:
                result['motion_hold_boundary_planning'] = planning_receipt
                result.setdefault('evidence', {})['motion_hold_boundary_planning'] = planning_receipt
            return result

        def audit_task_physical_feasibility(self, scene, program):
            from controlled_multi_future.family_runners_v3_1 import BaseFamilyRunnerV3_1, _pose
            from controlled_multi_future.runtime_v2_contracts import PLASTICBOX_BASE3_CAVITY
            base=BaseFamilyRunnerV3_1.audit_task_physical_feasibility(self.legacy.original,scene,program)
            by={r['role']:r for r in spec['roles']}
            actors={name:_pose(actor) for name,actor in scene.role_actors.items()}
            checks={'all_frozen_roles_created':set(actors)==set(by),'target_role':program.get('target_role') in ('red','green','blue'),
                'source_cube_size':all(np.array_equal(np.asarray(by[r]['size']),np.array([.044]*3)) for r in ('red','green','blue')),
                'cavity_larger_than_cube':bool(np.all(np.asarray(PLASTICBOX_BASE3_CAVITY['upper_m'])-np.asarray(PLASTICBOX_BASE3_CAVITY['lower_m'])>.044))}
            for a in ('red','green','blue'):
                for b in ('red','green','blue'):
                    if a>=b:continue
                    gap=np.abs(actors[a][:2]-actors[b][:2])-(np.asarray(by[a]['size'])[:2]+np.asarray(by[b]['size'])[:2])/2
                    checks[a+':'+b+':surface_clearance']=float(np.max(gap))>=.005
            passed=base['task_feasible'] and all(checks.values())
            return {'task_feasible':passed,'physical_feasible':passed,'planner_solvable':None,'failure_type':None if passed else 'formal_f1_geometry','evidence':{'checks':checks,'old_exact_four_role_rule_replaced_with_all_frozen_roles':True,'pairwise_surface_clearance_min_m':.005,'grasp_and_full_robot_clearance':'separate native planner qualification'}}

        def execute_frozen_suffix_spec(self, scene, program, execution_spec, replay, realization_spec):
            result=execute_with_stage_capture(self,scene,program,execution_spec,replay,realization_spec,spec)
            result.setdefault('provenance', {})['formal_current_capture_path'] = str(scene._formal_current_capture_path)
            result['provenance'].update(formal_root_id=spec['root_id'], formal_spec_sha256=spec['spec_sha256'],source_bundle_sha256=source_bundle)
            return result

    from controlled_multi_future.real_sapien_adapter_v1_2 import RoboTwinSceneContextV1_2
    from native_f1_factory import context_class
    Context = context_class(RoboTwinSceneContextV1_2)

    class Adapter(RoboTwinRealSapienF1BatchPilotAdapterV1):
        def build_programs(self, scene):
            from controlled_multi_future.schemas import validate_exactly_three_programs
            programs=deepcopy(spec['programs']);validate_exactly_three_programs(programs)
            return programs

        def validate_family_suffix_gate(self, receipts):
            result = dict(super().validate_family_suffix_gate(receipts))
            if realization != 'r_inv_motion':
                return result
            validation = []
            for item in receipts:
                program_id = item.get('program_id') if isinstance(item, dict) else None
                try:
                    baseline_manifest, _, _ = _load_motion_baseline_controls(
                        binding=motion_baseline_binding,
                        spec=spec,
                        program_id=program_id,
                    )
                    evidence = item.get('evidence') or {}
                    validate_motion_baseline_planner_source(
                        evidence.get('planner_collision_source'),
                        binding=motion_baseline_binding,
                        spec=spec,
                        program_id=program_id,
                        baseline_manifest=baseline_manifest,
                    )
                    if item.get('planner_query_count') != 0 or evidence.get('planner_invoked') is not False or evidence.get('planner_query_receipts') != []:
                        raise ValueError('motion receipt claims a live planner call')
                    validation.append({'program_id': program_id, 'pass': True})
                except BaseException as exc:
                    validation.append({'program_id': program_id, 'pass': False, 'error': str(exc)})
            valid = len(validation) == 3 and all(item['pass'] for item in validation)
            result.setdefault('evidence_checks', {})['motion_baseline_source_binding'] = valid
            result.setdefault('checks', {})['motion_baseline_source_binding'] = valid
            result['motion_baseline_source_validation'] = validation
            result['evidence_complete'] = all(result['evidence_checks'].values())
            result['pass'] = all(result['checks'].values())
            return result

        def scene(self, planned_root_slot_spec, *, phase, program=None):
            from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
            return _PinnedSapienRenderDeviceContextV1(Context(family='F1', planned_spec=planned_root_slot_spec, phase=phase, program=program, output_root=self.output_root,
                sealed_implementation_source_sha256=self._sealed_implementation_source_sha256, sealed_source_binding=self._sealed_source_binding))

        def capture_anchor(self,scene):
            actual=super().capture_anchor(scene)
            return legacy_comparison_view(actual,getattr(self,'_source_compatibility',None),'anchor')

        def _entity_payloads(self, scene):
            from controlled_multi_future.real_sapien_adapter_v1_2 import _dynamic_component, _entity, _pose, _rigid_velocity, _runtime_sleep_state, _procedural, _asset_hash_v1_2, procedural_asset_spec_sha256, ROLE_ASSETS_V1_2
            output = {}
            by_role = {r['role']:r for r in spec['roles']}
            for role, actor in scene.role_actors.items():
                r = by_role[role]
                if r['asset'] == 'primitive_box':
                    asset_spec = {'modelname':'procedural_box','model_id':None,'static_or_dynamic':'dynamic' if r['dynamic'] else 'static','collision_mode':'box',
                        'procedural_creation':_procedural(creation_api='create_box',half_size=(np.asarray(r['size'])/2).tolist(),color=r['color'],collision_enabled=True,visual_only=False,is_static=not r['dynamic'])}
                else:
                    asset_spec = ROLE_ASSETS_V1_2['F1']['common_box']
                dynamic = _dynamic_component(actor)
                linear,lm = _rigid_velocity(actor,'linear_velocity'); angular,am = _rigid_velocity(actor,'angular_velocity')
                config = getattr(actor,'config',None) or {}
                scale = np.asarray(config.get('scale',[1,1,1])).reshape(-1)
                if len(scale)==1: scale=np.repeat(scale,3)
                output[role] = {'role':role,'actor_name':_entity(actor).get_name(),'modelname':asset_spec['modelname'],'model_id':asset_spec['model_id'],
                    'visual_asset_hash':_asset_hash_v1_2(asset_spec,'visual'),'collision_asset_hash':_asset_hash_v1_2(asset_spec,'collision'),
                    'procedural_asset_spec_sha256':procedural_asset_spec_sha256(asset_spec),'procedural_creation':deepcopy(asset_spec.get('procedural_creation')),
                    'scale':scale.tolist(),'static_or_dynamic':asset_spec['static_or_dynamic'],'mass':float(dynamic.mass) if dynamic is not None else 0.,
                    'mass_source':'runtime_rigid_component' if dynamic is not None else 'not_applicable_non_dynamic','friction':{'static':.5,'dynamic':.5,'source':'scene_default_declared_config'},
                    'collision_mode':asset_spec['collision_mode'],'pose':_pose(actor),'linear_velocity':linear.tolist(),'angular_velocity':angular.tolist(),
                    'sleep_state':_runtime_sleep_state(dynamic),'velocity_source':{'linear_measured':lm,'angular_measured':am}}
            return output
        def capture_current(self, scene):
            # Native capture explicitly synchronizes and takes pictures. No physics step
            # occurs between that capture and retrieving the same camera buffers below.
            before = (len(getattr(scene,'trace',[])), int(getattr(scene,'_trace_step_index',0)))
            current = super().capture_current(scene)
            rgb = scene.cameras.get_rgb()
            arrays = {name: np.asarray(rgb[name]['rgb']).copy() for name in spec.get('cameras', {}).get('required', ('head_camera', 'left_camera', 'right_camera'))}
            for name, value in arrays.items():
                if value.dtype != np.uint8 or value.ndim != 3 or value.shape[2] != 3 or value.shape[:2] != (spec['cameras']['height'],spec['cameras']['width']):
                    raise ValueError(f'RGB capture invalid: {name}')
            arrays['robot_qpos'] = _dual_entity_values(scene.robot, 'get_qpos')
            arrays['robot_qvel'] = _dual_entity_values(scene.robot, 'get_qvel')
            anchor = super().capture_anchor(scene)
            if (len(getattr(scene,'trace',[])), int(getattr(scene,'_trace_step_index',0))) != before:
                raise RuntimeError('t0 capture advanced control time')
            destination = Path(self.output_root) / 'observations' / scene._cmf_scene_instance_id
            destination.mkdir(parents=True, exist_ok=True)
            path = destination / 'current.npz'
            scene._formal_current_capture_path = destination / 'capture.json'
            # Repeated capture within one scene cannot overwrite a previous t0.
            if path.exists():
                with np.load(path, allow_pickle=False) as old:
                    if set(old.files) != set(arrays) or any(not np.array_equal(old[k], v) for k, v in arrays.items()):
                        raise RuntimeError('second capture differs from persisted t0')
            else:
                np.savez_compressed(path, **arrays)
                (destination / 'anchor.json').write_text(
                    json.dumps(anchor, sort_keys=True), encoding='utf-8'
                )
                (destination / 'capture.json').write_text(
                    json.dumps({'current_hashes': current, 'root_id':spec['root_id'], 'spec_sha256': spec['spec_sha256'], 'source_bundle_sha256':source_bundle, 'camera_config': self._camera_configuration(scene, rgb), 'scene_instance_id': scene._cmf_scene_instance_id, 'capture_source': 'native_original_t0', 'render_device_binding': scene._cmf_render_device_binding_v1, 'npz_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, sort_keys=True),
                    encoding='utf-8',
                )
            with np.load(path, allow_pickle=False) as persisted:
                if any(not np.array_equal(persisted[k], v) for k, v in arrays.items()):
                    raise RuntimeError('current write/readback mismatch')
            compatibility=getattr(self,'_source_compatibility',None)
            if compatibility is not None:
                from family_entry import write,digest
                comparison=legacy_comparison_view(current,compatibility,'current')
                write(destination/'source_comparison_view.json',{'original_capture_sha256':hashlib.sha256((destination/'capture.json').read_bytes()).hexdigest(),'compatibility_payload_sha256':digest(compatibility),'view_current':comparison,'original_current':current,'view_anchor':legacy_comparison_view(anchor,compatibility,'anchor'),'original_anchor_file_sha256':hashlib.sha256((destination/'anchor.json').read_bytes()).hexdigest(),'normalization_only':'implementation_source_sha256 and dependent comparison hashes; originals unchanged'})
                return comparison
            return current

    adapter = Adapter(family='F1', output_root=Path(output_root), expected_implementation_source_sha256=source_sha)
    adapter.controller_v3_3 = Controller()
    return adapter


def run_native_cohort(*, spec, realization, output, source_sha,source_compatibility=None,recovery_context=None):
    from native_f1_orchestrator import FormalF1RecoverableOrchestrator
    from controlled_multi_future.canonical_artifact import canonical_hash_json
    output = Path(output)
    pointer = output / 'cohort_pointer.json'
    previous = json.loads(pointer.read_text(encoding='utf-8')) if pointer.exists() else None
    attempt = previous['attempt'] + 1 if previous else 1
    max_attempts = 4 if isinstance(recovery_context, dict) and recovery_context.get('mode') == 'motion_only' and recovery_context.get('allow_cohort_attempt4') is True else 3 if isinstance(recovery_context, dict) and recovery_context.get('mode') == 'motion_only' else 2
    if attempt > max_attempts:
        raise ValueError('native F1 finite recovery invocation exhausted')
    if previous and previous['spec_sha256'] != spec['spec_sha256']:raise ValueError('recovery spec changed')
    if previous and previous['source_sha256'] != source_sha:
        if not source_compatibility or source_compatibility.get('old_source_sha256')!=previous['source_sha256'] or source_compatibility.get('new_source_sha256')!=source_sha:raise ValueError('recovery source changed without validated compatibility')
    attempt_output = output if attempt == 1 else output / f'recovery_{attempt}'
    root_output = attempt_output / 'root'
    reuse = {}
    if previous:
        old_root = output / previous['root_relative']
        for program in spec['programs']:
            branch = old_root / 'branches' / program['program_id']
            if (branch / 'receipt.json').exists() and json.loads((branch / 'receipt.json').read_text(encoding='utf-8')).get('status') == 'accepted':
                reuse[program['program_id']] = branch
    adapter_kwargs = {
        'spec': spec,
        'realization': realization,
        'output_root': attempt_output / 'scene_instances',
        'source_sha': source_sha,
    }
    if recovery_context is not None:
        adapter_kwargs['recovery_context'] = recovery_context
    adapter = native_adapter(**adapter_kwargs)
    adapter._source_compatibility=source_compatibility
    planned = deepcopy(spec)
    planned['slot_id'] = spec['root_id']
    planned['candidate_display_order'] = [p['program_id'] for p in spec['programs']]
    planned['scene_layout_sha256'] = canonical_hash_json(spec['scene_layout'])
    orchestrator = FormalF1RecoverableOrchestrator(adapter, implementation_version='formal_f1_native_entry_20260910')
    orchestrator.reuse_cells = reuse
    orchestrator.source_compatibility=source_compatibility
    def independent_cell_gate(branch_dir,program):
        from family_entry import finalize_native_cell,write
        result=finalize_native_cell(spec=spec,output=output.parent,program_id=program['program_id'],realization=realization)
        if result['pass']:
            first=output.parent/'first_verified_cell.json'
            if not first.exists():write(first,{**result,'independent_cell_local_path':str(branch_dir/'independent_cell_local.json'),'independent_cell_local_sha256':hashlib.sha256((branch_dir/'independent_cell_local.json').read_bytes()).hexdigest()})
        return result
    orchestrator.independent_cell_gate=independent_cell_gate
    explicit_prefix = (recovery_context or {}).get('canonical_prefix_artifact_dir') if isinstance(recovery_context, dict) else None
    if explicit_prefix is not None:
        explicit_prefix = _bound_workspace_path(explicit_prefix)
        if not (explicit_prefix / 'canonical_prefix_artifact.json').is_file() or not (explicit_prefix / 'prefix_arrays.npz').is_file():
            raise ValueError('explicit recovery canonical prefix artifact is incomplete')
        orchestrator.reuse_prefix_dir = explicit_prefix
    elif previous and (old_root / 'canonical_prefix_artifact').exists():
        orchestrator.reuse_prefix_dir = old_root / 'canonical_prefix_artifact'
    output.mkdir(parents=True, exist_ok=True)
    payload = {'root_relative':str(root_output.relative_to(output)), 'attempt':attempt,'spec_sha256':spec['spec_sha256'],'source_sha256':source_sha,'reused_programs':sorted(reuse),'status':'STARTED','previous_pointer':previous}
    temporary=pointer.with_suffix('.tmp'); temporary.write_text(json.dumps(payload), encoding='utf-8'); temporary.replace(pointer)
    try:
        result = orchestrator.run_nonformal_root(output_dir=root_output, planned_root_slot_spec=planned,
            realization_spec_by_program={p['program_id']: {'realization': realization, 'variant_rules': spec['variant_rules'], 'formal_data': False, 'entry_spec_sha256': spec['spec_sha256']} for p in spec['programs']},
            stage0_data=False, stage0_authorized=False, development_video_required=False)
        payload['status']=result['status']
        return result
    finally:
        import time
        payload['ended_wall']=time.time()
        if payload['status']=='STARTED': payload['status']='EXCEPTION'
        temporary=pointer.with_suffix('.tmp'); temporary.write_text(json.dumps(payload), encoding='utf-8'); temporary.replace(pointer)
