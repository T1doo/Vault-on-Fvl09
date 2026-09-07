import sys
import types
import unittest
from unittest.mock import patch
from . import runtime

class Tests(unittest.TestCase):
    def test_changes_shader_only_when_constructing_display_recorder(self):
        calls=[]
        fake=types.SimpleNamespace(render=types.SimpleNamespace(set_camera_shader_dir=lambda name:calls.append(name)))
        with patch.dict(sys.modules,{'sapien':fake}),patch.object(runtime.Recorder,'__init__',return_value=None):
            runtime.RasterRecorder(None,None)
        self.assertEqual(calls,['default'])
    def test_requires_explicit_versioned_shader_scope(self):
        with self.assertRaises(ValueError):runtime.run({},meter=None)

def load_tests(loader,tests,pattern):
    return unittest.TestSuite([tests,loader.loadTestsFromName('goal_pilot48_v1.hd_state_replay_v1.test_all')])
