import unittest
MODULES=['goal_pilot48_v1.f3_upright_qualification_runtime_v1.'+name for name in ('test_checker','test_native','test_runtime','test_scope')]
def load_tests(loader,tests,pattern):return loader.loadTestsFromNames(MODULES)
if __name__=='__main__':unittest.main()
