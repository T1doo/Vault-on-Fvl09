"""Frozen Gate preflight aggregation for lifecycle, sequence and native inputs."""
import unittest
from . import test_lifecycle, test_sequence
from ..f3_native_self_pair_v1 import test_contract

def load_tests(loader, tests, pattern):
    return unittest.TestSuite(loader.loadTestsFromModule(m)
                             for m in (test_lifecycle, test_sequence, test_contract))
