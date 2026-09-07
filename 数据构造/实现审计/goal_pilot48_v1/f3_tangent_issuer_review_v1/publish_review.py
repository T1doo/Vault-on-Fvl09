import unittest,json,hashlib
from pathlib import Path
from . import test_builder,test_dispatcher
from goal_pilot48_v1.runtime import issue_tangent_micro as issuer
from realization_utf8_io_v1 import write_new
def main():
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_builder,test_dispatcher)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise ValueError('pure issuer tests failed')
    p=Path(issuer.__file__);t=Path(test_builder.__file__)
    value={'schema_version':'p48_f3_tangent_pure_issuer_CPU_review_v1','pass':True,'tests_run':result.testsRun,
        'issuer_file_sha256':issuer.sha(p),'test_file_sha256':issuer.sha(t),'current_CPU_receipt':issuer.EXPECTED_CPU_RECEIPT,
        'inherited_job':'p48_f3_micro_006','caps':issuer.CAPS,'state_check_cap_separate':6,
        'reservation_created':False,'manifest_written':False,'GPU_executed':False,
        'actual_source_dependency_build_test_pass':True,'old_CPU_AUDIT_not_used_as_current_source_seal':True}
    value['dispatcher_test_file_sha256']=issuer.sha(Path(test_dispatcher.__file__))
    value['supersedes_CPU_REVIEW_file_sha256']=issuer.sha(Path(__file__).parent/'CPU_REVIEW.json')
    value['actual_generic_dispatcher_local2_meter3_rejected']=True
    value['job_kind_preserves_F3_MICRO_accounting_branch']=True
    value['receipt_sha256']=issuer.digest(value);write_new(Path(__file__).parent/'CPU_REVIEW_V1_1.json',value);print(value['receipt_sha256'])
if __name__=='__main__':main()
