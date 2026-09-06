"""Guard preflight covers both real run lifecycle and four-query sequencing."""
import unittest
from . import test_lifecycle, test_sequence

def load_tests(loader, tests, pattern):
    return unittest.TestSuite([loader.loadTestsFromModule(test_lifecycle),
                               loader.loadTestsFromModule(test_sequence)])
