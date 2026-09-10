"""New native F1 integration. Importing this file does not import the simulator.

Old nonformal receipts retain their original labels. This adapter is callable only
inside a separately authorized GPU child; CPU tests do not construct native scenes.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import numpy as np


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
        if self.realization == 'r_inv_path':
            offset = float(self.rules['r_inv_path']['safe_horizontal_y_offset_m'])
            targets = change_path_targets(targets, offset)
            extra = {**extra, 'formal_path_offset_y_m': offset}
        return targets, extra


def native_adapter(*, spec, realization, output_root, source_sha):
    # These imports are lazy; constructor source integrity is checked by native base.
    from controlled_multi_future.real_sapien_adapter_f1_batch_v1 import RoboTwinRealSapienF1BatchPilotAdapterV1
    from controlled_multi_future.family_runners_v3_3 import F1ControllerV3_3, _wait_and_record
    from controlled_multi_future.real_sapien_adapter_v1_1 import _dual_entity_values

    class Controller(F1ControllerV3_3):
        def __init__(self):
            super().__init__()
            self.legacy = VariantLegacy(self.legacy, realization, spec['variant_rules'])

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
            if realization == 'r_inv_motion':
                frames = spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames']
                if type(frames) is not int or not 0 < frames <= 250:
                    raise ValueError('bounded integer hold required')
                _wait_and_record(scene, frames)
            result = super().execute_frozen_suffix_spec(scene, program, execution_spec, replay, realization_spec)
            result.setdefault('provenance', {})['formal_current_capture_path'] = str(scene._formal_current_capture_path)
            result['provenance'].update(formal_root_id=spec['root_id'], formal_spec_sha256=spec['spec_sha256'])
            return result

    from controlled_multi_future.real_sapien_adapter_v1_2 import RoboTwinSceneContextV1_2
    from native_f1_factory import context_class
    Context = context_class(RoboTwinSceneContextV1_2)

    class Adapter(RoboTwinRealSapienF1BatchPilotAdapterV1):
        def build_programs(self, scene):
            from controlled_multi_future.schemas import validate_exactly_three_programs
            programs=deepcopy(spec['programs']);validate_exactly_three_programs(programs)
            return programs

        def scene(self, planned_root_slot_spec, *, phase, program=None):
            from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
            return _PinnedSapienRenderDeviceContextV1(Context(family='F1', planned_spec=planned_root_slot_spec, phase=phase, program=program, output_root=self.output_root,
                sealed_implementation_source_sha256=self._sealed_implementation_source_sha256, sealed_source_binding=self._sealed_source_binding))

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
                (destination / 'anchor.json').write_text(json.dumps(anchor, sort_keys=True))
                (destination / 'capture.json').write_text(json.dumps({'current_hashes': current, 'spec_sha256': spec['spec_sha256'], 'camera_config': self._camera_configuration(scene, rgb), 'scene_instance_id': scene._cmf_scene_instance_id, 'capture_source': 'native_original_t0', 'render_device_binding': scene._cmf_render_device_binding_v1, 'npz_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, sort_keys=True))
            with np.load(path, allow_pickle=False) as persisted:
                if any(not np.array_equal(persisted[k], v) for k, v in arrays.items()):
                    raise RuntimeError('current write/readback mismatch')
            return current

    adapter = Adapter(family='F1', output_root=Path(output_root), expected_implementation_source_sha256=source_sha)
    adapter.controller_v3_3 = Controller()
    return adapter


def run_native_cohort(*, spec, realization, output, source_sha):
    from native_f1_orchestrator import FormalF1RecoverableOrchestrator
    from controlled_multi_future.canonical_artifact import canonical_hash_json
    output = Path(output)
    pointer = output / 'cohort_pointer.json'
    previous = json.loads(pointer.read_text()) if pointer.exists() else None
    attempt = previous['attempt'] + 1 if previous else 1
    if attempt > 2:
        raise ValueError('native F1 finite recovery invocation exhausted')
    if previous and (previous['spec_sha256'] != spec['spec_sha256'] or previous['source_sha256'] != source_sha):
        raise ValueError('recovery source or spec changed')
    attempt_output = output if attempt == 1 else output / f'recovery_{attempt}'
    root_output = attempt_output / 'root'
    reuse = {}
    if previous:
        old_root = output / previous['root_relative']
        for program in spec['programs']:
            branch = old_root / 'branches' / program['program_id']
            if (branch / 'receipt.json').exists() and json.loads((branch / 'receipt.json').read_text()).get('status') == 'accepted':
                reuse[program['program_id']] = branch
    adapter = native_adapter(spec=spec, realization=realization, output_root=attempt_output / 'scene_instances', source_sha=source_sha)
    planned = deepcopy(spec)
    planned['slot_id'] = spec['root_id']
    planned['candidate_display_order'] = [p['program_id'] for p in spec['programs']]
    planned['scene_layout_sha256'] = canonical_hash_json(spec['scene_layout'])
    orchestrator = FormalF1RecoverableOrchestrator(adapter, implementation_version='formal_f1_native_entry_20260910')
    orchestrator.reuse_cells = reuse
    if previous and (old_root / 'canonical_prefix_artifact').exists():
        orchestrator.reuse_prefix_dir = old_root / 'canonical_prefix_artifact'
    output.mkdir(parents=True, exist_ok=True)
    payload = {'root_relative':str(root_output.relative_to(output)), 'attempt':attempt,'spec_sha256':spec['spec_sha256'],'source_sha256':source_sha,'reused_programs':sorted(reuse),'status':'STARTED'}
    temporary=pointer.with_suffix('.tmp'); temporary.write_text(json.dumps(payload)); temporary.replace(pointer)
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
        temporary=pointer.with_suffix('.tmp'); temporary.write_text(json.dumps(payload)); temporary.replace(pointer)
