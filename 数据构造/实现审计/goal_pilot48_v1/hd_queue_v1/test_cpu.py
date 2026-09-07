import unittest
from unittest.mock import patch
from types import SimpleNamespace
from . import queue

class Tests(unittest.TestCase):
    def test_finite_safe_job_names(self):
        self.assertEqual(queue.job_name({'label':'F4_B_r_inv_motion_F4-ABC'}),'p48_hd_render_queue_f4_b_r_inv_motion_f4_abc_001')
        for label in ('../bad','x'*200):
            with self.assertRaises(ValueError):queue.job_name({'label':label})
    def test_unexpected_staging_never_absorbed(self):
        with patch.object(queue.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch.object(queue,'git') as git:
            with self.assertRaises(RuntimeError):queue.publish_issuance('CPU')
            git.assert_not_called()
