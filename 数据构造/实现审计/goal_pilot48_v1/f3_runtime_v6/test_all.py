import unittest
MODULES=['goal_pilot48_v1.f3_one_sided_escape_v2.'+n for n in ('test_certificate','test_policy','test_fresh_input','test_live_restore','test_integrity','test_one_sided')]+['goal_pilot48_v1.f3_runtime_v6.'+n for n in ('test_lifecycle','test_sequence','test_restore','test_dispatcher')]
def load_tests(loader,tests,pattern):return loader.loadTestsFromNames(MODULES)
if __name__=='__main__':unittest.main()
