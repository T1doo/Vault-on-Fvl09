import unittest
import numpy as np
from .zbuffer import raster
class Tests(unittest.TestCase):
    def test_intersecting_triangles_require_per_pixel_depth(self):
        xy=np.array([[[0,0],[10,0],[0,10]],[[0,0],[10,0],[0,10]]],dtype=float)
        depth=np.array([[0,2,0],[1,1,1]],dtype=float);colors=np.array([[0,200,0],[0,0,200]],dtype=np.uint8)
        a,z=raster(xy,depth,colors,11,11);b,_=raster(xy[::-1],depth[::-1],colors[::-1],11,11)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(a[1,1],[0,0,200]);np.testing.assert_array_equal(a[1,7],[0,200,0])
    def test_large_background_cannot_cover_near_object(self):
        xy=np.array([[[0,0],[10,0],[0,10]],[[1,1],[5,1],[1,5]]],float);d=np.array([[0,0,0],[2,2,2]],float);c=np.array([[100,100,100],[0,200,200]],np.uint8)
        image,z=raster(xy,d,c,11,11);np.testing.assert_array_equal(image[2,2],[0,200,200]);self.assertEqual(z[2,2],2)
if __name__=='__main__':unittest.main()
