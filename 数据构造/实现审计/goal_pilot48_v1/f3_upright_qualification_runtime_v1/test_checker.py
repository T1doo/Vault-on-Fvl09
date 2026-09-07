"""Finite CPU collision fixtures, not captured physical-success evidence."""
import unittest,copy
import numpy as np
import transforms3d as t3d
from .native import Checker,fk_all,T,hash_value,pad_escape_token
from types import SimpleNamespace
def pose(m):return np.r_[m[:3,3],t3d.quaternions.mat2quat(m[:3,:3])].tolist()
def fixture():
    f=fk_all({});records=[]
    def shape(body,robot):return {'name':body+'__0','body':body,'robot':robot,'kind':'PhysxCollisionShapeSphere','radius':.01,'local_pose':[100,0,0,1,0,0,0],'body_world_pose':[0,0,100,1,0,0,0],'groups':[0,0,0,0]}
    for body in [side+'_link'+str(i) for side in ('fl','fr') for i in range(1,9)]+['fl_base_link','fl_wheel_link']:records.append(shape(body,True))
    for body in ('table','f3_original_pad','f3_main_bottle','ground'):records.append(shape(body,False))
    names=['fl_joint'+str(i) for i in range(1,7)];d={'shapes':records,'coverage':[],'inventory_complete':True,'base_pose':pose(f('fl_base_link')),'joint_names':names,'actual_qpos':[0.]*6}
    return d
def locate(d,body,point):
    s=next(x for x in d['shapes'] if x['body']==body);s['groups']=[1,1,0,0]
    if s['robot']:
        m=fk_all({})(body);local=np.linalg.inv(m)@np.r_[point,1.];s['local_pose']=[*local[:3],1,0,0,0]
    else:s['local_pose']=[0,0,0,1,0,0,0];s['body_world_pose']=[*point,1,0,0,0]
    return s
def checker(d):d['geometry_sha256']=hash_value(d['shapes']);return Checker(d)
class Tests(unittest.TestCase):
    def test_nonadjacent_self_hit(self):
        d=fixture();point=[0,0,2];locate(d,'fl_link3',point);locate(d,'fl_link5',point);r=checker(d).check(np.zeros((2,6)),d['joint_names']);self.assertFalse(r['pass']);self.assertEqual(r['checked_samples'],1)
    def test_base_and_wheel_are_checked(self):
        for body in ('fl_base_link','fl_wheel_link'):
            d=fixture();locate(d,'fl_link3',[0,0,2]);locate(d,body,[0,0,2]);self.assertFalse(checker(d).check(np.zeros((1,6)),d['joint_names'])['pass'])
    def test_ground_halfspace_blocks_below_not_above(self):
        d=fixture();locate(d,'fl_link3',[0,0,2]);s=locate(d,'ground',[0,0,1]);s.update(kind='PhysxCollisionShapePlane',body_world_pose=[0,0,1,2**-.5,0,-2**-.5,0]);self.assertTrue(checker(d).check(np.zeros((1,6)),d['joint_names'])['pass'])
        s['body_world_pose'][2]=3;self.assertFalse(checker(d).check(np.zeros((1,6)),d['joint_names'])['pass'])
    def test_carried_allows_only_fingers_not_palm(self):
        for body,allowed in [('fl_link7',True),('fl_link8',True),('fl_link6',False)]:
            d=fixture();locate(d,body,[0,0,2]);locate(d,'f3_main_bottle',[0,0,2]);r=checker(d).check(np.zeros((1,6)),d['joint_names'],carried=True);self.assertEqual(r['pass'],allowed)
    def test_pad_exception_requires_validated_binding_and_not_table(self):
        d=fixture();locate(d,'f3_main_bottle',[0,0,2]);locate(d,'f3_original_pad',[0,0,2]);c=checker(d)
        with self.assertRaises(ValueError):c.check(np.zeros((1,6)),d['joint_names'],carried=True,allow_pad_escape=True)
        token={'geometry_sha256':d['geometry_sha256'],'validated_model_eligibility':True}
        self.assertTrue(c.check(np.zeros((1,6)),d['joint_names'],carried=True,allow_pad_escape=token)['pass'])
        locate(d,'table',[0,0,2]);c=checker(d);token['geometry_sha256']=d['geometry_sha256'];self.assertFalse(c.check(np.zeros((1,6)),d['joint_names'],carried=True,allow_pad_escape=token)['pass'])
    def test_empty_nonfinite_missing_coverage_hash_rejected(self):
        d=fixture();c=checker(d)
        for q in (np.zeros((0,6)),np.full((1,6),np.nan)):
            with self.assertRaises(ValueError):c.check(q,d['joint_names'])
        d['shapes']=[s for s in d['shapes'] if s['body']!='fl_wheel_link']
        with self.assertRaises(ValueError):checker(d)
        d=fixture();c=checker(d);d['geometry_sha256']='f'*64
        with self.assertRaises(ValueError):Checker(d)
    def test_complete_control_samples_traversed(self):
        d=fixture();r=checker(d).check(np.zeros((5,6)),d['joint_names']);self.assertTrue(r['pass']);self.assertEqual(r['checked_samples'],5)
    def test_uncertified_phase_cannot_mint_pad_token(self):
        with self.assertRaises(ValueError):pad_escape_token(SimpleNamespace(),{'geometry_sha256':'x'})
if __name__=='__main__':unittest.main()
