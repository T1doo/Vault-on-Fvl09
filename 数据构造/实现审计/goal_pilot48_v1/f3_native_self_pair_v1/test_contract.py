"""Fail closed on empty/malformed controls before native geometry construction."""
import unittest
from unittest.mock import patch
import numpy as np
from . import checker

class Tests(unittest.TestCase):
    def test_empty_controls_rejected_without_loading_geometry(self):
        names=['fl_joint'+str(i) for i in range(1,7)]
        with patch.object(checker,'model',side_effect=AssertionError('must reject before native load')):
            with self.assertRaisesRegex(ValueError,'at least one'):
                checker.check_controls(np.empty((0,6)),names,names,np.zeros(6))

    def test_malformed_controls_rejected_without_loading_geometry(self):
        names=['fl_joint'+str(i) for i in range(1,7)]
        with patch.object(checker,'model',side_effect=AssertionError('must reject before native load')):
            for controls in (np.empty((2,5)),np.empty((6,))):
                with self.assertRaisesRegex(ValueError,'correctly dimensioned'):
                    checker.check_controls(controls,names,names,np.zeros(6))

if __name__=='__main__':unittest.main()
