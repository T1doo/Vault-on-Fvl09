import unittest
from types import SimpleNamespace
import numpy as np
from live_mass_properties import capture_mass_properties
class Body:
    def get_mass(self): return .01
    def get_inertia(self): return [1e-5,2e-5,3e-5]
    def get_cmass_local_pose(self):return SimpleNamespace(p=np.array([0,.11,0]),q=np.array([1,0,0,0]))
class Entity:
    def get_components(self):return [Body()]
    def get_pose(self):return SimpleNamespace(p=np.array([1,2,3]),q=np.array([1,0,0,0]))
    def get_name(self):return 'bottle'
class Tests(unittest.TestCase):
    def test_actor_wrapper(self):
        x=capture_mass_properties(SimpleNamespace(actor=Entity()))
        self.assertEqual(x['com_world'],[1,2.11,3]);self.assertFalse(x['proxy_COM_used'])
    def test_component_ambiguity_rejected(self):
        e=Entity();e.get_components=lambda:[Body(),Body()]
        with self.assertRaises(ValueError):capture_mass_properties(e)
    def test_bad_mass_rejected(self):
        b=Body();b.get_mass=lambda:0
        e=Entity();e.get_components=lambda:[b]
        with self.assertRaises(ValueError):capture_mass_properties(e)
if __name__=='__main__':unittest.main()
