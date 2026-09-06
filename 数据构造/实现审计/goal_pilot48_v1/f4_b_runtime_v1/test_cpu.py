"""In-memory fixtures only. Tests never publish passing GPU evidence."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest
from .binding import payload, runtime_spec, validate_runtime, validate_stage_a, seal, SEED, ROOT_ID
from .stages import planner_spec, physical_spec, bound_function

def fixture_stage_a():
    b = payload()
    return seal(dict(schema_version='cmf_f4_b_source_stage_a_evidence_v1',
        source_candidate_sha256=b['source']['candidate_sha256'], payload_sha256=b['receipt_sha256'],
        scene_seed=SEED, scene_instance_id='CPU_FIXTURE_NOT_REAL', physical_execution_count=0,
        planner_query_count=27, status='B_SOURCE_STAGE_A_PASS', checks={k:True for k in
        ('rendered_visibility','A_pregrasp_grasp_lift_planner','B_pregrasp_grasp_lift_planner',
         'C_pregrasp_grasp_lift_planner','all_roles_return_one_neutral')}))

class Tests(unittest.TestCase):
    def test_unique_payload_and_parent_separation(self):
        b = payload()
        self.assertEqual(b, payload()); self.assertEqual(b['seed'], SEED)
        self.assertNotEqual(b['source']['candidate_sha256'], b['source']['parent_candidate_sha256'])
        self.assertNotEqual(b['slot']['candidate_sha256'], b['slot']['parent_candidate_sha256'])
        self.assertEqual(b['source']['source_layout'], b['scene_layout']['object_poses'])
        self.assertEqual(b['slot']['slot_poses'], b['scene_layout']['slot_poses'])

    def test_runtime_exact_seed_no_legacy_rank_fallback(self):
        spec = runtime_spec(); self.assertEqual(validate_runtime(spec), spec)
        self.assertEqual(spec['seed'], 2026090604); self.assertEqual(spec['slot_id'], ROOT_ID)
        for key, value in [('seed',2026091401), ('slot_id','old_A')]:
            altered = deepcopy(spec); altered[key] = value; altered = seal(altered,'planned_scope_spec_sha256')
            with self.assertRaises(ValueError): validate_runtime(altered)
        altered = deepcopy(spec); altered['scene_layout']['object_poses']['A'][0] += .01
        with self.assertRaises(ValueError): validate_runtime(seal(altered,'planned_scope_spec_sha256'))

    def test_no_source_success_fabricated_by_builder(self):
        self.assertIsNone(runtime_spec()['f4_b_source_stage_a_evidence'])
        with self.assertRaises((ValueError,TypeError)): runtime_spec('f4_stage_b_planner')
        wrong = fixture_stage_a(); wrong['source_candidate_sha256'] = payload()['source']['parent_candidate_sha256']
        with self.assertRaises(ValueError): validate_stage_a(seal(wrong))

    def test_full_builder_preserves_exact_planner_gate(self):
        ps = planner_spec('F4-ABC', slot_id='B-ABC-planner-source', planner_reset_nonce=2026090701)
        terminal = seal(dict(spec_sha256=ps['spec_sha256'],candidate_sha256=ps['candidate_sha256'],
            program_id='F4-ABC',robot_kinematic_table_world_planner_pass=True,physical_execution_count=0))
        args = dict(stage_a=fixture_stage_a(), program_id='F4-ABC', slot_id=ps['slot_id'],
            planner_reset_nonce=ps['planner_reset_nonce'],isolation_receipt_sha256='1'*64)
        result = physical_spec(terminal, **args)
        self.assertEqual(result['legacy_scene_spec']['seed'],SEED)
        self.assertEqual(result['legacy_scene_spec']['scene_layout'],payload()['scene_layout'])
        wrong = deepcopy(terminal); wrong['candidate_sha256'] = payload()['slot']['parent_candidate_sha256']
        with self.assertRaises(ValueError): physical_spec(seal(wrong),**args)
        wrong = deepcopy(terminal); wrong['robot_kinematic_table_world_planner_pass'] = False
        with self.assertRaises(ValueError): physical_spec(seal(wrong),**args)

    def test_isolation_builder_keeps_B_scene(self):
        ps = planner_spec('F4-ABC', slot_id='B-ABC-planner-source', planner_reset_nonce=1)
        terminal = seal(dict(spec_sha256=ps['spec_sha256'],candidate_sha256=ps['candidate_sha256'],
            program_id='F4-ABC',robot_kinematic_table_world_planner_pass=True,physical_execution_count=0))
        result = physical_spec(terminal,stage_a=fixture_stage_a(),program_id='F4-ABC',slot_id='B-ABC',
            planner_reset_nonce=1,isolation_stage='A_ONLY')
        self.assertEqual(result['planner_query_limit'],22)
        self.assertEqual(result['legacy_scene_spec']['seed'],SEED)

    def test_namespace_clone_does_not_mutate_shared_globals(self):
        def original(): return SEED
        clone = bound_function(original, SEED=12)
        self.assertEqual(clone(),12); self.assertEqual(original(),SEED)

    def test_adapter_constructor_and_stage_a_runner_no_scene(self):
        from .adapter import make_adapter
        from .stages import source_stage_a_runner
        adapter = make_adapter(output_root=Path('/nfs_share/lijunhui/Robotwin2/tmp/f4_b_cpu_not_created'),
            source_sha256='3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7',
            planned_spec=runtime_spec())
        self.assertEqual(adapter.planned_spec['seed'],SEED)
        runner=source_stage_a_runner(adapter)
        self.assertIs(runner.adapter,adapter)
        self.assertFalse(adapter.output_root.exists())

    def test_real_scene_loader_consumes_bound_layout_without_scene_creation(self):
        path = Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/controlled_multi_future/probes/scene_inspection.py')
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='F4Scene')
        fn = next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='load_actors')
        class Actor:
            def set_name(self,name): self.name=name
        class Fake:
            def __init__(self): self._cmf_planned_root_slot_spec=runtime_spec();self.seen={}
            def _box(self,name,position,color): self.seen[name]=position;return Actor()
        poses=[]
        class Sapien:
            class Pose:
                def __init__(self,p,q=None): self.p=p;self.q=q
        def visual(scene,pose,*args,**kwargs): poses.append(pose.p);return Actor()
        ns=dict(sapien=Sapien,create_actor=lambda *a,**k:Actor(),create_visual_box=visual)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
        fake=Fake();ns['load_actors'](fake)
        self.assertEqual(fake.seen['f4_object_a'],payload()['source']['source_layout']['A'][:3])
        self.assertEqual(poses,[payload()['slot']['slot_poses'][r][:3] for r in ('A','B','C')])

if __name__=='__main__': unittest.main()
