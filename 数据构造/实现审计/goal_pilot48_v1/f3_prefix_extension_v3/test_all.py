import unittest
MODULES=['goal_pilot48_v1.f3_prefix_extension_v3.'+name for name in ('test_order','test_contract','test_lifecycle')]
def load_tests(loader,tests,pattern):return loader.loadTestsFromNames(MODULES)
if __name__=='__main__':unittest.main()
