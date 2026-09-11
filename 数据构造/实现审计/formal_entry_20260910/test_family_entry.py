"""CPU tests; native factory is not invoked. Fixtures are never physical evidence."""
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from native_f1 import VariantLegacy, change_path_targets
from family_entry import planned_cells, validate_native_f1, run_root


def fixture_authorization(spec):
    from file_source_pin import inventory,bundle_hash
    files=inventory()
    return {'gpu_execution_authorized':True,'spec_sha256':spec['spec_sha256'],'implementation_source_sha256':'explicit_cpu_fixture_only','source_files':files,'source_bundle_sha256':bundle_hash(files)}


def fixture_spec():
    return {'root_id': 'F1-fixture', 'family': 'F1', 'spec_sha256': 'fixture-only',
            'programs': [{'program_id': f'F1-{r}', 'target_role': r} for r in ('red','green','blue')],
            'realizations': ['r_pc','r_inv_path','r_inv_motion'],
            'variant_rules': {'r_inv_path': {'safe_horizontal_y_offset_m': .03}, 'r_inv_motion': {'post_prefix_hold_frames': 35}},
            'scene_layout': {'object_xyz_by_role': {r: [0,0,.762] for r in ('red','green','blue')}, 'common_box_pose_wxyz': [0,0,.78,1,0,0,0]}}


class TestEntry(unittest.TestCase):
    def test_nine_unique_and_pc_only(self):
        cells = planned_cells(fixture_spec())
        self.assertEqual(len({x['cell_key'] for x in cells}), 9)
        self.assertEqual(sum(x['strict_prefix_cohort'] == 'r_pc' for x in cells), 3)

    def test_bad_program_or_variant(self):
        spec = fixture_spec()
        spec['programs'][1] = spec['programs'][0]
        with self.assertRaises(ValueError): planned_cells(spec)
        spec = fixture_spec(); spec['variant_rules']['r_inv_motion']['post_prefix_hold_frames'] = 0
        with self.assertRaises(ValueError): validate_native_f1(spec)

    def test_variant_changes_target_before_planner_without_mutating_baseline(self):
        targets = [{'segment_id':'safe_horizontal', 'pose': [0,0,1.02,1,0,0,0]}, {'segment_id':'release','pose':[0,0,.8,1,0,0,0]}]
        class Legacy:
            def build_targets(self, *args, **kwargs): return targets, {}
        path, extra = VariantLegacy(Legacy(), 'r_inv_path', fixture_spec()['variant_rules']).build_targets(None)
        self.assertAlmostEqual(path[0]['pose'][1], .03)
        self.assertEqual(targets[0]['pose'][1], 0)
        np.testing.assert_equal(path[1]['pose'], targets[1]['pose'])
        self.assertEqual(extra['formal_path_offset_y_m'], .03)

    def test_native_scene_context_consumes_actual_layout_without_entering_simulator(self):
        import sys
        sys.path.insert(0, '/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        from native_f1 import native_adapter
        from scene_plan import generate,resolve
        spec = resolve(generate()['slots'][0])
        adapter = native_adapter(spec=spec, realization='r_inv_path', output_root=Path(__file__).parent / 'unused_cpu_boundary', source_sha=None)
        context = adapter.scene(spec, phase='pristine').inner
        self.assertEqual(context.planned_spec['scene_layout'], spec['scene_layout'])
        self.assertEqual(type(adapter.controller_v3_3.legacy).__name__, 'VariantLegacy')
        self.assertIsNone(context._scene)
        second = adapter.scene(spec, phase='pristine').inner
        self.assertNotEqual(context.scene_instance_id, second.scene_instance_id)

    def test_generic_factory_consumes_geometry_and_distractors(self):
        from native_f1_factory import create_roles
        from types import SimpleNamespace
        calls = []
        class Actor:
            def set_name(self, name): self.name = name
        def box(scene, pose, size, **kwargs):
            calls.append(('box', pose, np.asarray(size).tolist(), kwargs)); return Actor()
        def asset(scene, pose, name, **kwargs):
            calls.append(('asset', pose, name, kwargs)); return Actor()
        roles = [{'role': r, 'asset':'primitive_box','pose':[i*.1,0,.762,1,0,0,0],'size':[.044,.044,.044],'color':[1,0,0],'dynamic':True} for i,r in enumerate(('red','green','blue','similar_1'))]
        roles.append({'role':'common_box','asset':'062_plasticbox:model3','pose':[0,0,.78,1,0,0,0],'size':[.2,.16,.08],'color':[1,1,1],'dynamic':False})
        scene = SimpleNamespace()
        create_roles(scene, {'roles':roles}, box=box, asset=asset, pose=lambda p,q: p+q)
        self.assertEqual(set(scene.role_actors), {'red','green','blue','similar_1','common_box'})
        self.assertEqual(calls[3][1][:3],[.30000000000000004,0,.762])
        self.assertEqual(calls[3][2],[.022,.022,.022])

    def test_disk_export_sources_and_answer_separation(self):
        from family_entry import export_native_cell
        import hashlib
        spec=fixture_spec()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            root=Path(td); current=root/'r_pc/scene_instances/observations/f1-strict_prefix_branch_F1-red-v1_2-000001'
            current.mkdir(parents=True)
            arrays={k:np.full((2,3,3),i,dtype=np.uint8) for i,k in enumerate(('head_camera','left_camera','right_camera'))}
            arrays.update(robot_qpos=np.arange(38,dtype=float),robot_qvel=np.zeros(38))
            np.savez_compressed(current/'current.npz',**arrays)
            (current/'capture.json').write_text(json.dumps({'spec_sha256':spec['spec_sha256'],'npz_sha256':hashlib.sha256((current/'current.npz').read_bytes()).hexdigest()}))
            raw=root/'r_pc/root/branches/F1-red/raw'; raw.mkdir(parents=True)
            np.savez_compressed(raw/'raw_streams.npz',stream__controller_effective_setpoint=np.ones((4,26)),stream__realized_qpos=np.tile(np.arange(38),(5,1)),stream__realized_qvel=np.zeros((5,38)))
            value=export_native_cell(spec=spec,output=root,program_id='F1-red',realization='r_pc')
            self.assertEqual(value['inputs']['state'].shape,(76,))
            self.assertNotIn('program_id',value['inputs'])
            self.assertEqual(value['supervision']['program_id'],'F1-red')
            self.assertEqual(value['inputs']['future'].shape,(4,26))
            arrays['robot_qpos'][0] += 1
            np.savez_compressed(current/'current.npz',**arrays)
            with self.assertRaises(ValueError): export_native_cell(spec=spec,output=root,program_id='F1-red',realization='r_pc')

    def test_actual_orchestrator_fixture_reuses_passed_cell_after_failure(self):
        import sys, importlib.util, hashlib
        sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        module_path=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
        loader=importlib.util.spec_from_file_location('explicit_synthetic_backend_fixture',module_path)
        fixture=importlib.util.module_from_spec(loader);loader.loader.exec_module(fixture)
        from native_f1_orchestrator import FormalF1RecoverableOrchestrator
        from controlled_multi_future.families import F1ObjectSelection
        kwargs={'planned_root_slot_spec':{'slot_id':'fixture-root','family':'F1','seed':17,'origin':'explicit_synthetic_fixture'},'realization_spec_by_program':{p['program_id']:{'realization':'r_pc','formal_data':False,'stage0_data':False} for p in F1ObjectSelection().checked_provisional_programs()}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            first=Path(td)/'first'; second=Path(td)/'second'
            failing=fixture.StrictPrefixSyntheticAdapter(verifier_error_program='F1-green')
            result=FormalF1RecoverableOrchestrator(failing).run_nonformal_root(output_dir=first,**kwargs)
            self.assertNotEqual(result['status'],'accepted')
            self.assertEqual(failing.suffix_execution_count,2)
            self.assertFalse((first/'branches/F1-blue').exists())
            old_raw=first/'branches/F1-red/raw/raw_streams.npz'; old_sha=hashlib.sha256(old_raw.read_bytes()).hexdigest()
            healthy=fixture.StrictPrefixSyntheticAdapter()
            runner=FormalF1RecoverableOrchestrator(healthy); runner.reuse_cells={'F1-red':first/'branches/F1-red'};runner.reuse_prefix_dir=first/'canonical_prefix_artifact'
            resumed=runner.run_nonformal_root(output_dir=second,**kwargs)
            self.assertEqual(resumed['status'],'accepted',resumed.get('error'))
            self.assertEqual(healthy.suffix_execution_count,2)
            self.assertEqual(hashlib.sha256((second/'branches/F1-red/raw/raw_streams.npz').read_bytes()).hexdigest(),old_sha)
            self.assertEqual(hashlib.sha256(old_raw.read_bytes()).hexdigest(),old_sha)
            self.assertEqual(resumed['reused_branches'][0]['program_id'],'F1-red')

    def test_recovery_prefix_replays_sealed_artifact_without_planner(self):
        import sys, importlib.util, hashlib
        from unittest.mock import patch
        sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        module_path=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
        loader=importlib.util.spec_from_file_location('recovery_prefix_fixture',module_path)
        fixture=importlib.util.module_from_spec(loader);loader.loader.exec_module(fixture)
        from native_f1_orchestrator import FormalF1RecoverableOrchestrator
        from controlled_multi_future.families import F1ObjectSelection
        kwargs={'planned_root_slot_spec':{'slot_id':'fixture-root','family':'F1','seed':17,'origin':'explicit_synthetic_fixture'},'realization_spec_by_program':{p['program_id']:{'realization':'r_pc','formal_data':False,'stage0_data':False} for p in F1ObjectSelection().checked_provisional_programs()}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            first=Path(td)/'first';second=Path(td)/'second'
            source=fixture.StrictPrefixSyntheticAdapter()
            FormalF1RecoverableOrchestrator(source).run_nonformal_root(output_dir=first,**kwargs)
            healthy=fixture.StrictPrefixSyntheticAdapter();runner=FormalF1RecoverableOrchestrator(healthy)
            runner.reuse_prefix_dir=first/'canonical_prefix_artifact'
            with patch.object(healthy,'plan_and_execute_canonical_prefix',side_effect=AssertionError('recovery must not re-plan prefix')):
                resumed=runner.run_nonformal_root(output_dir=second,**kwargs)
            self.assertEqual(resumed['status'],'accepted',resumed.get('error'))
            self.assertEqual(healthy.prefix_generation_count,0)
            self.assertTrue(resumed['canonical_prefix_reuse']['planner_called'] is False)
            self.assertEqual(resumed['canonical_prefix_generation_count'],0)
            comparison=json.loads((second/'recovery_prefix_binding_comparison.json').read_text())
            self.assertTrue(comparison['actions']['planner_called'] is False)
            self.assertTrue(comparison['actions']['byte_identical'])
            self.assertTrue(comparison['current']['aggregate_equal'])
            self.assertTrue(comparison['anchor']['equivalence']['equivalent'])

    def test_recovery_prefix_current_difference_is_reported_separately(self):
        import sys, importlib.util
        from unittest.mock import patch
        sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        module_path=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
        loader=importlib.util.spec_from_file_location('recovery_current_fixture',module_path)
        fixture=importlib.util.module_from_spec(loader);loader.loader.exec_module(fixture)
        from native_f1_orchestrator import FormalF1RecoverableOrchestrator
        from controlled_multi_future.families import F1ObjectSelection
        from controlled_multi_future.current_hasher import build_current_hashes
        kwargs={'planned_root_slot_spec':{'slot_id':'fixture-root','family':'F1','seed':17,'origin':'explicit_synthetic_fixture'},'realization_spec_by_program':{p['program_id']:{'realization':'r_pc','formal_data':False,'stage0_data':False} for p in F1ObjectSelection().checked_provisional_programs()}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            first=Path(td)/'first';second=Path(td)/'second'
            source=fixture.StrictPrefixSyntheticAdapter();FormalF1RecoverableOrchestrator(source).run_nonformal_root(output_dir=first,**kwargs)
            class Drift(fixture.StrictPrefixSyntheticAdapter):
                def capture_current(self, scene):
                    return build_current_hashes(head_rgb=np.zeros((2,2,3),dtype=np.uint8),wrist_rgb={'left':np.zeros((1,1,3),dtype=np.uint8),'right':np.zeros((1,1,3),dtype=np.uint8)},robot_state=np.zeros(14),gripper_actual_state=np.zeros(4),object_role_layout={'red':[0,0,0]},camera_config_version='camera-v1',scene_seed=18,generator_version='strict-prefix-test-v1')
            runner=FormalF1RecoverableOrchestrator(Drift());runner.reuse_prefix_dir=first/'canonical_prefix_artifact'
            resumed=runner.run_nonformal_root(output_dir=second,**kwargs)
            self.assertNotEqual(resumed['status'],'accepted')
            comparison=json.loads((second/'recovery_prefix_binding_comparison.json').read_text())
            self.assertFalse(comparison['current']['aggregate_equal'])
            self.assertEqual(comparison['failure'],'current_mismatch')
            self.assertTrue(comparison['actions']['planner_called'] is False)

    def test_motion_hold_uses_explicit_prefix_and_motion_start_states(self):
        import sys
        from unittest.mock import patch
        sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        from native_f1 import execute_with_stage_capture
        from scene_plan import generate,resolve
        spec=resolve(generate()['slots'][0])
        class Scene:
            def __init__(self): self.trace=[]
        scene=Scene()
        class Link:
            def get_name(self): return 'fixture_link'
        class Entity:
            def get_links(self): return [Link()]
        class Robot:
            left_gripper_scale=[-.01,.045]
            left_entity=Entity();right_entity=Entity()
        scene.robot=Robot(); scene.selected_gripper_links=lambda: ['fixture_finger']; scene._formal_current_capture_path=Path('/nfs_share/lijunhui/Robotwin2/tmp')/'native_motion_cpu_capture.json'
        scene._formal_current_capture_path.parent.mkdir(parents=True,exist_ok=True)
        def dummy_segment(*args, **kwargs): return None
        def dummy_action(*args, **kwargs): return None
        def dummy_wait(current, frames): current.trace.extend([{}]*int(frames))
        def dummy_stable(*args, **kwargs): return ([], [], [])
        def dummy_open(*args, **kwargs): return True
        def fake_native(self, current, program, execution_spec, replay, realization_spec): return {'provenance':{}}
        fake_native.__globals__.update(
            _execute_cached_segment=dummy_segment,
            _must_action=dummy_action,
            _wait_and_record=dummy_wait,
            _stable_and_support=dummy_stable,
            _arm_gripper_open=dummy_open,
            PROVISIONAL_RUNTIME_THRESHOLDS={},
        )
        with patch('controlled_multi_future.family_runners_v3_3.F1ControllerV3_3.execute_frozen_suffix_spec',new=fake_native):
            # execute_with_stage_capture obtains the mature primitive's globals
            # and applies the motion boundary before invoking that primitive.
            result=execute_with_stage_capture(object(),scene,{'program_id':'F1-red','target_role':'red'}, {}, {}, {'realization':'r_inv_motion'}, spec)
        self.assertEqual(result['motion_hold_boundary']['state_before'],'S_prefix')
        self.assertEqual(result['motion_hold_boundary']['state_after'],'S_motion_start')
        self.assertEqual(result['motion_hold_boundary']['frames'],35)
        self.assertTrue(result['motion_hold_boundary']['planner_and_execution_boundary_shared'])

    def test_real_cli_pipeline_missing_original_rgb_rejects_fixture(self):
        import sys,importlib.util,contextlib,io
        from unittest.mock import patch
        from family_entry import main
        sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        path=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/tests/controlled_multi_future/test_root_orchestrator_v1_2.py')
        loader=importlib.util.spec_from_file_location('cli_explicit_synthetic_backend',path);fixture=importlib.util.module_from_spec(loader);loader.loader.exec_module(fixture)
        adapters=[]
        def boundary(**kwargs):
            adapter=fixture.StrictPrefixSyntheticAdapter();adapters.append(adapter);return adapter
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            directory=Path(td)
            from scene_plan import generate,resolve
            spec=resolve(generate()['slots'][0])
            (directory/'spec.json').write_text(json.dumps(spec));(directory/'authorization.json').write_text(json.dumps(fixture_authorization(spec)))
            with patch('native_f1.native_adapter',boundary),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(RuntimeError):
                main(['--spec',str(directory/'spec.json'),'--authorization',str(directory/'authorization.json'),'--output',str(directory/'root')])
            self.assertEqual(len(adapters),1)
            self.assertEqual(sum(a.suffix_execution_count for a in adapters),1)
            local=json.loads((directory/'root/r_pc/root/branches/F1-red/independent_cell_local.json').read_text())
            self.assertFalse(local['pass'])
            self.assertFalse((directory/'root/r_pc/root/branches/F1-green').exists())
            self.assertFalse((directory/'root/independent_structure.json').exists())

    def test_positive_whole_cli_nine_fixture_keeps_research_ineligible(self):
        import sys,contextlib,io
        from unittest.mock import patch
        sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
        from family_entry import main
        from fixture_f1_backend import make_backend
        from scene_plan import generate,resolve
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            directory=Path(td);spec=resolve(generate()['slots'][0])
            (directory/'spec.json').write_text(json.dumps(spec));(directory/'auth.json').write_text(json.dumps(fixture_authorization(spec)))
            with patch('native_f1.native_adapter',make_backend),contextlib.redirect_stdout(io.StringIO()):
                code=main(['--spec',str(directory/'spec.json'),'--authorization',str(directory/'auth.json'),'--output',str(directory/'root')])
            final=json.loads((directory/'root/independent_structure.json').read_text())
            self.assertEqual(code,0,{k:v for k,v in final['checks'].items() if not v})
            self.assertTrue(final['pass']);self.assertFalse(final['research_eligible']);self.assertFalse(final['native_physical_evidence'])
            self.assertTrue(final['independent_semantic_recomputed']);self.assertTrue(final['model_export_verified']);self.assertEqual(len(final['cells']),9)
            from f1_portable_export import seal_source,copy_root
            import portable_v2
            index=seal_source(directory/'root',spec,final)
            copied=copy_root(index,directory/'copied_root')
            self.assertTrue(copied['synthetic']);self.assertFalse(copied['formal_eligible'])
            original_open=io.open
            def blocked_source(file,*args,**kwargs):
                if isinstance(file,(str,Path)) and Path(file).resolve().is_relative_to((directory/'root').resolve()):
                    raise PermissionError('fixture original source disabled')
                return original_open(file,*args,**kwargs)
            with patch('io.open',blocked_source):
                for relative in copied['relative_cell_paths']:
                    payload=portable_v2.read(directory/'copied_root'/relative)
                    self.assertEqual(payload['inputs']['state'].shape,(76,))
                    self.assertEqual(payload['inputs']['future'].shape[1],26)


    def test_first_failure_saved_and_stops(self):
        calls = []
        def failed(**kwargs):
            calls.append(kwargs['realization'])
            raise RuntimeError('fixture injected scene-entry failure')
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            with self.assertRaises(RuntimeError): run_root(spec=fixture_spec(), output=Path(td)/'root', source_sha='source', cohort_runner=failed)
            checkpoint = json.loads((Path(td)/'root/checkpoint.json').read_text())
            self.assertEqual(checkpoint['status'], 'FAILED')
            self.assertEqual(calls, ['r_pc'])
            with self.assertRaises(RuntimeError): run_root(spec=fixture_spec(), output=Path(td)/'root', source_sha='source', resume=True, cohort_runner=failed)
            self.assertEqual(len(calls), 2)

    def test_resume_rejects_changed_spec(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as td:
            def fail(**kwargs): raise RuntimeError('fixture')
            with self.assertRaises(RuntimeError): run_root(spec=fixture_spec(), output=Path(td)/'root', source_sha='a', cohort_runner=fail)
            with self.assertRaises(ValueError): run_root(spec=fixture_spec(), output=Path(td)/'root', source_sha='b', resume=True, cohort_runner=fail)

if __name__ == '__main__': unittest.main()
