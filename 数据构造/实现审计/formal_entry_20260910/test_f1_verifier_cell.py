"""Actual native save/local verifier/export paths; only simulator adapter is synthetic."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,'/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
from scene_plan import generate,resolve
from fixture_f1_backend import make_backend,physical_contact
from native_f1 import run_native_cohort,_load_motion_baseline_controls
from f1_disk_verifier import verify_f1_disk,verify_variant_pair
from family_entry import validate_saved_cell
BASE=Path('/nfs_share/lijunhui/Robotwin2/tmp')


class TestF1VerifierCell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(dir=BASE);cls.output=Path(cls.temporary.name);cls.spec=resolve(generate()['slots'][0])
        with patch('native_f1.native_adapter',make_backend):
            for r in cls.spec['realizations']:
                receipt=run_native_cohort(spec=cls.spec,realization=r,output=cls.output/r,source_sha='explicit_fixture')
                if receipt['status']!='accepted':raise AssertionError(receipt.get('error',receipt['status']))
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def mutated(self,realization='r_pc'):
        td=tempfile.TemporaryDirectory(dir=BASE);self.addCleanup(td.cleanup);root=Path(td.name)/'root'
        shutil.copytree(self.output/realization/'root',root)
        raw=root/'branches/F1-red/raw'
        with np.load(raw/'raw_streams.npz',allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
        return raw,arrays
    def test_formal_threshold_and_real_release_support(self):
        raw,a=self.mutated();self.assertTrue(verify_f1_disk(raw_dir=raw,spec=self.spec,program=self.spec['programs'][0])['pass'])
        for kind in ('six_mm','closed_qpos','attached','pair_without_support','wrong_rest','above_box'):
            with self.subTest(kind=kind):
                raw,a=self.mutated()
                if kind=='six_mm':a['audit__role_object_pose__green'][10,0]+=.006
                elif kind=='closed_qpos':a['audit__realized_left_gripper_joint_qpos'][-50:]=-.01
                elif kind=='wrong_rest':a['stream__realized_eef'][-1,0]+=.5
                elif kind=='above_box':a['audit__role_object_pose__red'][-1,2]=1.5
                else:
                    rows=[json.loads(str(x)) for x in a['audit__contact_pairs_json']]
                    for row in rows[-50:]:
                        if kind=='attached':row.append(physical_contact('formal_f1_red','fixture_finger',[0,0,.8],impulse=.01))
                        else:
                            for p in row:
                                p['impulse_norm_sum']=0.;p['point_evidence'][0].update(signed_separation_m=.01,impulse_norm=0.)
                    a['audit__contact_pairs_json']=np.array([json.dumps(x) for x in rows])
                np.savez_compressed(raw/'raw_streams.npz',**a)
                result=verify_f1_disk(raw_dir=raw,spec=self.spec,program=self.spec['programs'][0]);self.assertFalse(result['pass'])
                expected={'six_mm':'unchanged:green','closed_qpos':'actual_gripper_open','attached':'released_from_robot','pair_without_support':'continuous_box_support_contact','wrong_rest':'rest_position','above_box':'true_inside'}[kind]
                self.assertFalse(result['checks'][expected],result)
    def test_longer_trace_or_unrelated_path_is_not_variant(self):
        baseline=self.output/'r_pc/root/branches/F1-red/raw'
        raw,a=self.mutated('r_inv_motion');manifest=json.loads((raw/'manifest.json').read_text());stages=manifest['provenance']['formal_f1_stages']['stages']
        hold=stages[0];delta=hold['end_row']-hold['start_row'];hold['end_row']=hold['start_row'];stages[1]['start_row']-=delta
        (raw/'manifest.json').write_text(json.dumps(manifest))
        self.assertFalse(verify_f1_disk(raw_dir=raw,spec=self.spec,program=self.spec['programs'][0])['checks']['registered_hold_length'])
        self.assertFalse(verify_variant_pair(baseline_dir=baseline,variant_dir=raw,spec=self.spec,realization='r_inv_motion')['pass'])
        raw,a=self.mutated('r_inv_path');manifest=json.loads((raw/'manifest.json').read_text());by={x['name']:x for x in manifest['provenance']['formal_f1_stages']['stages']}
        a['stream__realized_eef'][:,1]=0.;a['stream__realized_eef'][by['retreat']['end_row'],1]=.1
        np.savez_compressed(raw/'raw_streams.npz',**a)
        self.assertFalse(verify_variant_pair(baseline_dir=baseline,variant_dir=raw,spec=self.spec,realization='r_inv_path')['pass'])

    def test_motion_pair_requires_exact_baseline_non_hold_controls(self):
        baseline=self.output/'r_pc/root/branches/F1-red/raw'
        variant=self.output/'r_inv_motion/root/branches/F1-red/raw'
        self.assertTrue(verify_variant_pair(baseline_dir=baseline,variant_dir=variant,spec=self.spec,realization='r_inv_motion')['pass'])
        raw,a=self.mutated('r_inv_motion')
        manifest=json.loads((raw/'manifest.json').read_text(encoding='utf-8'))
        stages={x['name']:x for x in manifest['provenance']['formal_f1_stages']['stages']}
        row=stages['target_lift']['start_row']
        a['stream__controller_effective_setpoint'][row,0]+=np.float64(1e-6)
        np.savez_compressed(raw/'raw_streams.npz',**a)
        self.assertFalse(verify_variant_pair(baseline_dir=baseline,variant_dir=raw,spec=self.spec,realization='r_inv_motion')['pass'])

    def test_motion_baseline_binding_loads_sealed_controls_only(self):
        with tempfile.TemporaryDirectory(dir=BASE) as td,patch('native_f1.native_adapter',make_backend):
            root=Path(td)
            run_native_cohort(spec=self.spec,realization='r_pc',output=root/'r_pc',source_sha='fixture')
            programs={}
            for program in self.spec['programs']:
                artifact=root/'r_pc/root/suffix_artifacts'/program['program_id']
                manifest=json.loads((artifact/'frozen_suffix_artifact.json').read_text(encoding='utf-8'))
                programs[program['program_id']]={
                    'artifact_dir':str(artifact),
                    'manifest_file_sha256':hashlib.sha256((artifact/'frozen_suffix_artifact.json').read_bytes()).hexdigest(),
                    'manifest_artifact_sha256':manifest['artifact_sha256'],
                    'arrays_file_sha256':hashlib.sha256((artifact/'suffix_controls.npz').read_bytes()).hexdigest(),
                    'program_id':program['program_id'],'root_id':self.spec['root_id'],'realization':'r_pc',
                    'prefix_artifact_sha256':manifest['prefix_artifact_sha256'],
                }
            binding={'schema':'f1_motion_baseline_binding_v1','status':'CPU_REVIEWED_APPLICABLE','root_id':self.spec['root_id'],'spec_sha256':self.spec['spec_sha256'],'programs':programs}
            manifest,arrays,controls=_load_motion_baseline_controls(binding=binding,spec=self.spec,program_id='F1-red')
            self.assertEqual(manifest['program_id'],'F1-red');self.assertEqual(len(controls),len(manifest['execution_spec']['targets']));self.assertEqual(arrays['segment_000_position'].dtype,np.float32)
            bad=json.loads(json.dumps(binding));bad['programs']['F1-red']['manifest_file_sha256']='0'*64
            with self.assertRaises(ValueError):_load_motion_baseline_controls(binding=bad,spec=self.spec,program_id='F1-red')

    def test_verify_variant_pair_reads_utf8_under_ascii_locale(self):
        baseline=self.output/'r_pc/root/branches/F1-red/raw';variant=self.output/'r_inv_motion/root/branches/F1-red/raw'
        td=tempfile.TemporaryDirectory(dir=BASE);self.addCleanup(td.cleanup);root=Path(td.name)
        b=root/'baseline';v=root/'variant';shutil.copytree(baseline,b);shutil.copytree(variant,v)
        for folder in (b,v):
            path=folder/'manifest.json';payload=json.loads(path.read_text(encoding='utf-8'));payload['utf8_diagnostic']='中文回执';path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        spec_path=root/'spec.json';spec_path.write_text(json.dumps(self.spec,ensure_ascii=False),encoding='utf-8')
        code="""import json,sys
sys.path.insert(0, sys.argv[3])
from f1_disk_verifier import verify_variant_pair
spec=json.loads(open(sys.argv[2], encoding='utf-8').read())
result=verify_variant_pair(baseline_dir=sys.argv[4], variant_dir=sys.argv[5], spec=spec, realization='r_inv_motion')
raise SystemExit(0 if result.get('pass') is True else 1)
"""
        env=dict(os.environ,LC_ALL='C',LANG='C',PYTHONUTF8='0',PYTHONCOERCECLOCALE='0')
        result=subprocess.run([sys.executable,'-c',code,'utf8',str(spec_path),str(Path(__file__).parent),str(b),str(v)],env=env,cwd=str(Path(__file__).parent),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_no_provisional_fallback_and_local_receipt_binding(self):
        spec=dict(self.spec);del spec['f1_verifier_contract']
        raw=self.output/'r_pc/root/branches/F1-red/raw';self.assertFalse(verify_f1_disk(raw_dir=raw,spec=spec,program=spec['programs'][0])['pass'])
        marker=json.loads((self.output/'first_verified_cell.json').read_text());self.assertEqual(marker['program_id'],'F1-red')
        self.assertTrue(validate_saved_cell(self.spec,self.output,'F1-red','r_pc')['pass'])
        self.assertTrue(marker['independent_cell_local_sha256']);self.assertTrue(marker['manifest_sha256']);self.assertTrue(marker['raw_sha256'])
    def test_after_first_saved_cell_missing_rgb_stops_later_execution(self):
        adapters=[]
        def boundary(**kwargs):
            adapter=make_backend(**kwargs);original=adapter.execute_frozen_suffix_spec
            def execute(*a,**k):
                result=original(*a,**k);capture=Path(result['provenance']['formal_current_capture_path']);(capture.parent/'current.npz').unlink();return result
            adapter.execute_frozen_suffix_spec=execute;adapters.append(adapter);return adapter
        with tempfile.TemporaryDirectory(dir=BASE) as td,patch('native_f1.native_adapter',boundary):
            root=Path(td);receipt=run_native_cohort(spec=self.spec,realization='r_pc',output=root/'r_pc',source_sha='fixture')
            self.assertNotEqual(receipt['status'],'accepted');self.assertEqual(adapters[0].suffix_execution_count,1)
            first=root/'r_pc/root/branches/F1-red';self.assertTrue((first/'raw/raw_streams.npz').exists());self.assertFalse(json.loads((first/'independent_cell_local.json').read_text())['pass'])
            self.assertFalse((root/'r_pc/root/branches/F1-green').exists());self.assertFalse((root/'first_verified_cell.json').exists())
    def test_actual_saved_physical_failure_is_classified_separately(self):
        def boundary(**kwargs):
            adapter=make_backend(**kwargs);original=adapter.execute_frozen_suffix_spec
            def execute(*a,**k):
                result=original(*a,**k);result['audit_streams']['role_object_pose__green'][10,0]+=.006;return result
            adapter.execute_frozen_suffix_spec=execute;return adapter
        with tempfile.TemporaryDirectory(dir=BASE) as td,patch('native_f1.native_adapter',boundary):
            root=Path(td);receipt=run_native_cohort(spec=self.spec,realization='r_pc',output=root/'r_pc',source_sha='fixture')
            branch=receipt['branch_receipts'][0]
            self.assertEqual(branch['status'],'failed_independent_cell');self.assertEqual(branch['independent_cell_gate']['failure_class'],'PHYSICAL_FAILURE')
            self.assertFalse((root/'r_pc/root/branches/F1-green').exists())
    def test_approved_legacy_comparison_is_provenance_only(self):
        from native_f1 import legacy_comparison_view
        from copy import deepcopy
        old,new='a'*64,'b'*64
        approval={'status':'CPU_REVIEWED_APPLICABLE','scientific_contract_unchanged':True,'old_source_sha256':old,'new_source_sha256':new}
        current={'reconstruction_spec_audit':{'simulation_configuration':{'implementation_source_sha256':new,'gravity':[0,0,-9.8]}},'reconstruction_spec_components':{'simulation_configuration_sha256':'new','scene_spec_sha256':'same-scene'},'model_visible_aggregate_sha256':'actual-new-pixels-hash','hidden_physical_aggregate_sha256':'actual-new-state-hash'}
        original=deepcopy(current);view=legacy_comparison_view(current,approval,'current')
        self.assertEqual(current,original);self.assertEqual(view['reconstruction_spec_audit']['simulation_configuration']['implementation_source_sha256'],old)
        self.assertEqual(view['model_visible_aggregate_sha256'],current['model_visible_aggregate_sha256']);self.assertEqual(view['hidden_physical_aggregate_sha256'],current['hidden_physical_aggregate_sha256'])
        anchor={'physics_config':{'implementation_source_sha256':new,'friction':.9},'robot_qpos':[.03]*38}
        v=legacy_comparison_view(anchor,approval,'anchor');self.assertEqual(v['robot_qpos'],anchor['robot_qpos']);self.assertEqual(v['physics_config']['friction'],.9);self.assertEqual(anchor['physics_config']['implementation_source_sha256'],new)
        with self.assertRaises(ValueError):legacy_comparison_view(current,{**approval,'scientific_contract_unchanged':False},'current')
    def test_root_recheck_is_read_only(self):
        from family_entry import finalize_structure
        files=list(self.output.rglob('*.json'));before={p:p.read_bytes() for p in files}
        result=finalize_structure(spec=self.spec,output=self.output,write_receipt=False)
        self.assertTrue(result['pass']);self.assertEqual(set(files),set(self.output.rglob('*.json')))
        self.assertTrue(all(p.read_bytes()==v for p,v in before.items()))
    def test_capture_write_failure_stops_before_any_prefix(self):
        adapters=[]
        def boundary(**kwargs):a=make_backend(**kwargs);adapters.append(a);return a
        with tempfile.TemporaryDirectory(dir=BASE) as td,patch('native_f1.native_adapter',boundary),patch('numpy.savez_compressed',side_effect=OSError('explicit fixture disk failure')):
            receipt=run_native_cohort(spec=self.spec,realization='r_pc',output=Path(td)/'r_pc',source_sha='fixture')
            self.assertNotEqual(receipt['status'],'accepted');self.assertEqual(adapters[0].prefix_generation_count,0);self.assertEqual(adapters[0].suffix_execution_count,0)

if __name__=='__main__':unittest.main()
