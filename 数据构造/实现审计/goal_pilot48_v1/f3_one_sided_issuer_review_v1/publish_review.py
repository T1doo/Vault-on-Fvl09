import unittest,json
from pathlib import Path
from . import test_builder,test_dispatcher
from goal_pilot48_v1.runtime import issue_one_sided_micro as issuer
from realization_utf8_io_v1 import write_new
def main():
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_builder,test_dispatcher)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise ValueError('pure issuer tests failed')
    paths=[Path(issuer.__file__),Path(test_builder.__file__),Path(test_dispatcher.__file__)]
    d={'schema_version':'p48_f3_one_sided_pure_issuer_CPU_review_v1','pass':True,'tests_run':result.testsRun,
        'source_bindings':{str(p):issuer.sha(p) for p in paths},'current_CPU_receipt':issuer.EXPECTED_CPU_RECEIPT,
        'inherited_consumed_job':issuer.PARENT_JOB,'kind':'F3_MICRO','model_eligibility_revision':2,'stability_recipe_revision':3,'route_revision':2,
        'caps':issuer.CAPS,'high_level_state_check_cap_non_solver':6,'child_timeout_seconds':900,
        'reservation_created':False,'persistent_job_manifest_written':False,'GPU_executed':False,
        'real_generic_local2_meter3_rejected':True,'current25_source_and_CPU_inputs_hash_checked':True}
    d['receipt_sha256']=issuer.digest(d);write_new(Path(__file__).parent/'CPU_REVIEW.json',d);print(d['receipt_sha256'])
if __name__=='__main__':main()
