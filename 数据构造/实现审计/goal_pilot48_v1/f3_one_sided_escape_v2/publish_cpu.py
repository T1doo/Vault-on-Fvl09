"""Durable CPU test/source audit, explicitly not GPU conformance."""
import json,unittest,time,hashlib,sys
from pathlib import Path
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;G=O.parent
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
from goal_pilot48_v1.f3_runtime_v6.test_all import MODULES
def main():
    start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(MODULES))
    if not result.wasSuccessful():raise RuntimeError('CPU suite failed; no publication')
    paths=list(O.glob('*.py'))+list((G/'f3_runtime_v6').glob('*.py'))+[A/'support_pair_collision_v1/policy.py',A/'support_pair_collision_v1/factory.py',G/'runtime/support_witness.py',G/'f3_native_self_pair_v1/checker.py',G/'f3_tangent_escape_v1/certificate.py',G/'f3_runtime_v5/micro.py']
    r={'schema_version':'p48_f3_one_sided_escape_CPU_implementation_audit_v2','pass':True,'tests_run':result.testsRun,'elapsed_seconds':time.monotonic()-start,
        'source_bindings':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'old_supported_gate_or_006_changed':False,'new_model_eligibility_schema_not_physical_acceptance':True,
        'actual_GPU_model_and_kernel_conformance_verified':False,'new_scenes':0,'new_GPU_jobs':0,'budget_reserved':False,
        'expected_micro_query_cap':3,'expected_model_start_check_calls':6,'GPU_kernel_launch_count':'not_profiled_not_run',
        'real006_saved_inputs_test':'raw16/250 preserved; GPU status and factories explicitly mocked, not actual GPU evidence'}
    r['supersedes_CPU_AUDIT_file_sha256']=hashlib.sha256((G/'f3_tangent_escape_v1/CPU_AUDIT_V1_1.json').read_bytes()).hexdigest()
    r['factory_and_actual_state_binding_hardening']=True
    r['model_eligibility_revision']=2;r['stability_recipe_revision_unchanged']=3;r['pregrasp_route_revision_unchanged']=2
    r['native_negative_epsilon_m_unchanged']=.0001;r['arbitrary_positive_gap_upper_bound_removed']=True
    r['supersedes_initial_V2_CPU_audit_sha256']=hashlib.sha256((O/'CPU_AUDIT_V2.json').read_bytes()).hexdigest()
    r['generic_dispatcher_local_meter_mismatch_rejected']=True
    r['receipt_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();write_new(O/'CPU_AUDIT_V2_1.json',r);print(r['receipt_sha256'])
if __name__=='__main__':main()
