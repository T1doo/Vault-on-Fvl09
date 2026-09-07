import unittest,copy
import numpy as np
from .native import bounds,geometry,T,capture_shape,enabled,adjacent,fk_all,LINK_NAMES
class Tests(unittest.TestCase):
    def test_native_primitive_axes_and_enclosing_bounds(self):
        for kind,length in [('PhysxCollisionShapeCylinder',.1),('PhysxCollisionShapeCapsule',.12)]:
            s={'kind':kind,'radius':.02,'half_length':.1};b=bounds(s,np.eye(4));self.assertTrue(np.allclose(b[1],[length,.02,.02]));g,extra=geometry(s);self.assertTrue(np.allclose(extra[:3,:3]@[0,0,1],[1,0,0]))
    def test_box_sphere_plane_supported(self):
        for s in [{'kind':'PhysxCollisionShapeBox','half_size':[.1,.2,.3]},{'kind':'PhysxCollisionShapeSphere','radius':.1},{'kind':'PhysxCollisionShapePlane'}]:
            self.assertIsNotNone(geometry(s)[0])
    def test_unknown_native_type_rejected(self):
        with self.assertRaises(ValueError):geometry({'kind':'Unknown'})
    def test_group_filter_matches_actual_contract(self):
        self.assertTrue(enabled({'groups':[1,1,0,0]},{'groups':[1,1,0,0]}));self.assertFalse(enabled({'groups':[1,1,4,3]},{'groups':[1,1,4,3]}))
    def test_adjacent_not_unrelated_self_pair(self):
        self.assertTrue(adjacent('fl_link3','fl_link4'));self.assertFalse(adjacent('fl_link3','fl_link5'))
    def test_FK_has_base_wheels_all_arm_links(self):
        f=fk_all({})
        for name in ('fl_base_link','fl_link3','fl_link5','fl_wheel_link','fr_link8','base_link'):
            self.assertIn(name,LINK_NAMES);self.assertEqual(f(name).shape,(4,4))
        with self.assertRaises(ValueError):f('does_not_exist')
if __name__=='__main__':unittest.main()
