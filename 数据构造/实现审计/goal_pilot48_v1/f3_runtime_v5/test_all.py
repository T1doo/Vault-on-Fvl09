import unittest
MODULES=['goal_pilot48_v1.f3_tangent_escape_v1.'+n for n in ('test_certificate','test_policy','test_fresh_input','test_live_restore','test_integrity')]+['goal_pilot48_v1.f3_runtime_v5.'+n for n in ('test_lifecycle','test_sequence','test_restore')]
def load_tests(loader,tests,pattern):return loader.loadTestsFromNames(MODULES)
if __name__=='__main__':unittest.main()
