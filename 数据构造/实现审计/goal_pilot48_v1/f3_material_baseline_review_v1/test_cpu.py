import unittest
from .policy import verify_loader_route,validate_values,EXPECTED

class Tests(unittest.TestCase):
    def test_actual_factory_and_builder_source_route(self):
        verify_loader_route()
    def test_reviewed_default_passes_without_writing_material(self):
        self.assertTrue(validate_values([EXPECTED]*5,EXPECTED))
    def test_scene_default_is_not_mesh_material(self):
        self.assertFalse(validate_values([[.5,.5,0.]],EXPECTED))
        self.assertFalse(validate_values([],EXPECTED))
    def test_changed_global_or_nan_rejected(self):
        with self.assertRaises(ValueError):validate_values([EXPECTED],[.5,.5,0.])
        self.assertFalse(validate_values([[float('nan'),EXPECTED[1],EXPECTED[2]]],EXPECTED))
