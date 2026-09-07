import copy,unittest
import numpy as np
import torch
from .policy import PairFilteredWorld,audit_lift_escape,METHODS

from .test_certificate import fixture as witness
from .certificate import SinglePlanLease
class Backend:
    def __init__(self,names,factor):self.names=names;self.factor=factor;self.last_loss=None
    def get_obstacle_names(self):return self.names
    def get_sphere_distance(self,query_sphere,collision_query_buffer,weight,activation_distance,return_loss=False,**kwargs):
        self.last_loss=return_loss;return query_sphere[...,0]*self.factor
    get_sphere_collision=get_sphere_distance
    get_swept_sphere_distance=get_sphere_distance
    get_swept_sphere_collision=get_sphere_distance
class Tests(unittest.TestCase):
    def make(self):
        self.full=Backend(['table__0','pad__0','fr_link1__0'],1);self.sub=Backend(['table__0','fr_link1__0'],2)
        return PairFilteredWorld(self.full,self.sub,sphere_link_names=['fl_link7','attached_bottle','fl_link1'],attached_link_name='attached_bottle',support_name='pad__0',witness=witness(),buffer_factory=lambda q:object(),lease=SinglePlanLease(witness()))
    def test_only_attached_pair_filtered_all_four_callbacks(self):
        c=self.make();q=torch.ones((1,2,3,4))
        for name in METHODS:self.assertEqual(getattr(c,name)(q,object(),1.,0.).tolist(),[[[1.,2.,1.],[1.,2.,1.]]])
        self.assertEqual(c.calls,{k:1 for k in METHODS})
    def test_distance_gradient_routes_to_correct_backend(self):
        c=self.make();q=torch.ones((1,1,3,4),requires_grad=True);c.get_sphere_distance(q,object(),1.,0.).sum().backward();self.assertEqual(q.grad[0,0,:,0].tolist(),[1.,2.,1.]);self.assertTrue(self.full.last_loss and self.sub.last_loss)
    def test_global_disable_forbidden(self):
        with self.assertRaises(RuntimeError):self.make().enable_obstacle('table__0',False)
    def test_world_update_cannot_silently_desync(self):
        with self.assertRaises(RuntimeError):self.make().load_collision_model({})
    def test_dropping_another_obstacle_rejected(self):
        c=self.make();self.sub.names=['fr_link1__0']
        with self.assertRaises(ValueError):PairFilteredWorld(self.full,self.sub,sphere_link_names=c.names,attached_link_name=c.attached,support_name='pad__0',witness=witness(),buffer_factory=lambda q:None,lease=SinglePlanLease(witness()))
    def test_no_bad_contact_witness(self):
        c=self.make();w=witness();w['hold']['forbidden_count']=1
        with self.assertRaises(ValueError):PairFilteredWorld(self.full,self.sub,sphere_link_names=c.names,attached_link_name=c.attached,support_name='pad__0',witness=w,buffer_factory=lambda q:None,lease=SinglePlanLease(witness()))
    def test_escape_requires_rise_and_no_dip(self):
        v=np.zeros((3,2,3));v[:,:,2]=np.array([.74995,.76,.775])[:,None];p=np.tile([0,0,.78,1,0,0,0],(3,1));p[:,2]+=[0,.01,.025]
        self.assertTrue(audit_lift_escape(v,p,support_plane_z=.75,witness=witness())['pass']);v[1,:,2]=.74
        self.assertFalse(audit_lift_escape(v,p,support_plane_z=.75,witness=witness())['pass'])
    def test_shape_change_fail_closed(self):
        with self.assertRaises(ValueError):self.make().get_sphere_distance(torch.ones((1,1,4,4)),object(),1.,0.)
    def test_expired_certificate_blocks_all_callbacks(self):
        c=self.make();c.lease.invalidate()
        for name in METHODS:
            with self.assertRaises(RuntimeError):getattr(c,name)(torch.ones((1,1,3,4)),object(),1.,0.)
if __name__=='__main__':unittest.main(verbosity=2)
