"""One exact preflight covers physical lifecycle, issuance and HD display."""
import unittest

def load_tests(loader, tests, pattern):
    from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.test_all import Tests
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(Tests))
    suite.addTests(loader.loadTestsFromName('goal_pilot48_v1.f3_upright_qualification_runtime_v1.test_all'))
    suite.addTests(loader.loadTestsFromName('goal_pilot48_v1.runtime.test_upright_issuer'))
    return suite
