"""Real program evidence read-only; all simulated motion is CPU fixture only."""
import unittest
from .test_cpu import Tests as RuntimeTests
from . import runtime as r
from goal_pilot48_v1.runtime import issue_f4_b_isolation as issuer

class IssuerTests(unittest.TestCase):
    def test_real_programs_bind_all_five_original_physical_specs(self):
        fields,_=issuer.evidence_bindings();stage_a,scene,current,sources=r.prerequisites(fields)
        self.assertEqual(len(sources),3);self.assertEqual(scene['seed'],2026090604)
        for stage in r.STAGES:
            source=sources[r.PROGRAM[stage]]
            spec=r.physical_spec(source['terminal'],stage_a=stage_a,program_id=r.PROGRAM[stage],
                slot_id=source['physical_micro_slot_id'],planner_reset_nonce=source['spec']['planner_reset_nonce'],isolation_stage=stage)
            self.assertEqual(spec['legacy_scene_spec'],scene)
            self.assertEqual(spec['planner_query_limit'],22 if stage in r.STAGES[:3] else 32)
    def test_isolation_evidence_shape_accepted_by_real_root_prerequisites(self):
        from goal_pilot48_v1.f4_b_runtime_v1.stages import root_prerequisites
        fields,_=issuer.evidence_bindings();stage_a,scene,_,sources=r.prerequisites(fields)
        # In-memory format fixtures only; no physical success is written.
        isolation=r.seal(dict(status='B_ALL_FIVE_ISOLATION_PASS',b_scene_spec_sha256=scene['planned_scope_spec_sha256'],
            b_payload_sha256=r.payload()['receipt_sha256'],rows=[dict(stage=s,physical_pass=True,scene_receipt_sha256='1'*64) for s in r.STAGES],CPU_FIXTURE=True))
        template=r.seal(dict(status='B_FULL_PROGRAM_TEMPLATE_PASS',b_scene_spec_sha256=scene['planned_scope_spec_sha256'],
            b_payload_sha256=r.payload()['receipt_sha256'],isolation_receipt_sha256=isolation['receipt_sha256'],
            rows=[dict(program_id=p,physical_pass=True,scene_receipt_sha256='2'*64) for p in sources],
            same_current_pass=True,same_anchor_pass=True,final_state_equivalence={'equivalent':True},CPU_FIXTURE=True))
        bound=root_prerequisites(stage_a=stage_a,planner_envelopes=sources,isolation=isolation,template=template)
        self.assertEqual(bound['planned_spec'],scene)
        self.assertEqual(set(bound['full_program_specs']),set(sources))
    def test_pure_manifest_exact_scope_and_no_ledger_write(self):
        ledger=issuer.ROOT/'budget_ledger.jsonl';before=ledger.read_bytes();job='p48_f4_b_isolation_cpu_test'
        m=issuer.build_manifest(job,dict(kind='RESERVE',job_id=job,reserved=dict(issuer.CAPS),event_sha256='CPU_fixture_not_reserved'))
        self.assertEqual(before,ledger.read_bytes());self.assertEqual(m['jobs'][0]['resource_caps'],r.CAPS)
        self.assertEqual(m['jobs'][0]['timeout_seconds'],3600);self.assertEqual(m['reserved']['gpu_lease_seconds'],3780)
        self.assertTrue(m['physical_execution_authorized']);self.assertFalse(m['pilot_input_authorized'])
        self.assertFalse((issuer.ROOT/'jobs'/(job+'.json')).exists())

if __name__=='__main__':unittest.main(verbosity=2)
