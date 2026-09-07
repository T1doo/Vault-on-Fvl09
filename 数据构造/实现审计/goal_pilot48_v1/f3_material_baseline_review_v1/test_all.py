import unittest

def load_tests(loader,tests,pattern):
    return loader.loadTestsFromNames([
        'goal_pilot48_v1.f3_material_baseline_review_v1.test_cpu',
        'goal_pilot48_v1.f3_material_baseline_review_v1.test_runtime',
        'goal_pilot48_v1.f3_upright_trace_recovery_v1.test_all'])
