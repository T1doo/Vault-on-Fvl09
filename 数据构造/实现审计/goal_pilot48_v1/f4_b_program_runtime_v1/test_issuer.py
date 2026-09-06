"""Uses real saved Stage-A evidence read-only, plus CPU-only planner fixtures."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from .test_cpu import Tests as RuntimeTests
from goal_pilot48_v1.runtime import issue_f4_b_program as issuer
from .runtime import prerequisites

class IssuerTests(unittest.TestCase):
    def test_stage_a_b_purpose_does_not_change_current_reconstruction_metadata(self):
        from goal_pilot48_v1.f4_b_runtime_v1.binding import runtime_spec
        from goal_pilot48_v1.f4_b_runtime_v1.adapter import make_adapter
        from .runtime import SOURCE_SHA
        fields,_=issuer.evidence_bindings();evidence,b_spec,current=prerequisites(fields)
        a_spec=runtime_spec();observed=current['reconstruction_spec_audit'];configs=[];generators=[]
        self.assertNotEqual(a_spec['planned_scope_spec_sha256'],b_spec['planned_scope_spec_sha256'])
        self.assertEqual(a_spec['scene_layout'],b_spec['scene_layout'])
        for spec in (a_spec,b_spec):
            adapter=make_adapter(output_root=issuer.W/'Robotwin2/tmp/f4_metadata_cpu_no_scene',source_sha256=SOURCE_SHA,planned_spec=spec)
            scene=SimpleNamespace(_cmf_setup_kwargs={'seed':spec['seed']},_cmf_planned_root_slot_spec=spec,
                scene=SimpleNamespace(get_timestep=lambda:observed['simulation_configuration']['simulator_timestep_seconds']),
                _cmf_canonical_settle_steps=60,_cmf_sealed_implementation_source_sha256=SOURCE_SHA,
                _cmf_sealed_source_binding=adapter._sealed_source_binding)
            adapter._mark_v1_3_context(scene)
            configs.append(adapter._simulation_configuration(scene));generators.append(scene._cmf_generator_version)
        self.assertEqual(configs[0],configs[1]);self.assertEqual(configs[0],observed['simulation_configuration'])
        self.assertEqual(generators,[observed['generator_version']]*2)
        self.assertEqual(observed['scene_seed'],2026090604)
    def test_real_completed_source_evidence_compatible(self):
        fields,paths=issuer.evidence_bindings()
        evidence,spec,current=prerequisites(fields)
        self.assertEqual(evidence['receipt_sha256'],issuer.EVIDENCE_RECEIPT)
        self.assertEqual(evidence['goal_problem_accounting']['solver_problems'],135)
        self.assertEqual(spec['seed'],2026090604);self.assertEqual(len(current['aggregate_sha256']),64)
        self.assertTrue(all(p.is_file() for p in paths.values()))
    def test_pure_manifest_build_preserves_ledger_and_full_parent_hashes(self):
        job='p48_f4_b_program_cpu_test';ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes()
        m=issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=dict(issuer.CAPS),event_sha256='CPU_fixture_no_reservation'))
        self.assertEqual(before,ledger.read_bytes())
        self.assertEqual(m['jobs'][0]['planner_reset_nonce_base'],202609070400)
        self.assertEqual(m['jobs'][0]['resource_caps'],dict(solver_problems=450,fresh_scenes=3,action_scenes=0,collection_attempts=0))
        self.assertEqual(m['jobs'][0]['timeout_seconds'],1800);self.assertEqual(m['reserved']['gpu_lease_seconds'],1980)
        self.assertFalse(m['physical_execution_authorized']);self.assertFalse(m['pilot_input_authorized'])
        parent=issuer.read(issuer.ROOT/'jobs'/('p48_f4_b_stage_a_001.json'))
        for field in ('source_files','input_files'):
            for path,sha in parent[field].items():self.assertEqual(m[field][path],sha)
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())
    def test_namespace_reserved_and_no_mutators(self):
        job='p48_f4_b_program_cpu_test'
        with self.assertRaises(ValueError):issuer.build_manifest(job,{})
        exists=Path.exists;target=issuer.W/'Robotwin2/datasets'/(job+'_meter')
        with patch.object(Path,'exists',lambda p:p==target or exists(p)):
            with self.assertRaises(FileExistsError):issuer.assert_fresh(job)
        tree=ast.parse(Path(issuer.__file__).read_text(encoding='utf-8'))
        forbidden={'reserve','write_new','Popen','exec_command'}
        self.assertFalse({n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}&forbidden)

if __name__=='__main__':unittest.main(verbosity=2)
