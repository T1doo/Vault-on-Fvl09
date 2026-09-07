import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from .recorder import inventory,intrinsic,page_layout,Recorder
from .runtime import Context
class Entity:
    def __init__(self):self.pose=np.eye(4)
    def get_pose(self):return self.pose.copy()
    def set_pose(self,p):self.pose=np.array(p)
class Camera:
    def __init__(self,w=320,h=240,source=True):self.w=w;self.h=h;self.K=np.array([[200.,0,w/2],[0,200,h/2],[0,0,1]]);self.entity=Entity();self.local=np.eye(4);self.source=source;self.picture_calls=0
    def get_width(self):return self.w
    def get_height(self):return self.h
    def get_intrinsic_matrix(self):return self.K.copy()
    def get_near(self):return .1
    def get_far(self):return 100.
    def get_local_pose(self):return self.local.copy()
    def set_local_pose(self,p):self.local=np.array(p)
    def get_model_matrix(self):return self.entity.pose@self.local
    def set_perspective_parameters(self,n,f,fx,fy,cx,cy,s):self.K=np.array([[fx,s,cx],[0,fy,cy],[0,0,1.]])
    def take_picture(self):self.picture_calls+=1
    def get_picture(self,name):
        if self.source:raise AssertionError('must not upscale/read old320 RGB')
        return np.ones((self.h,self.w,4),dtype=np.float32)*.25
def manager(extra=0):
    head=Camera();return SimpleNamespace(static_camera_list=[head]+[Camera() for _ in range(extra)],static_camera_name=['head_camera']+['extra_'+str(i) for i in range(extra)],left_camera=Camera(),right_camera=Camera(),observer_camera=Camera(),world_camera1=Camera(),world_camera2=Camera())
class Tests(unittest.TestCase):
    def test_all_six_views_and_same_internal_name_not_deduped(self):
        m=manager();m.world_camera1.name=m.world_camera2.name='world_camera1'
        self.assertEqual([n for n,_ in inventory(m)],['head','left_wrist','right_wrist','observer','world1','world2'])
    def test_extra_static_views_paginate_without_loss(self):
        views=inventory(manager(3));self.assertEqual(len(views),9);self.assertEqual(page_layout(len(views)),[list(range(6)),[6,7,8]])
    def test_native_intrinsics_are_scaled_not_RGB(self):
        c=Camera();k=c.K.copy();hd=intrinsic(c);self.assertEqual(hd[0,0],600);self.assertEqual(hd[1,1],600);self.assertTrue(np.array_equal(c.K,k))
    def test_actual_capture_uses_new_HD_pixels_and_original_pose(self):
        m=manager();created=[];removed=[];frames=[]
        def add(name,w,h,*args):c=Camera(w,h,False);created.append(c);return c
        renderer=SimpleNamespace(add_camera=add,update_render=lambda:None,remove_camera=lambda c:removed.append(c))
        scene=SimpleNamespace(cameras=m,scene=renderer,_update_render=lambda:None,_step_index=11)
        def writer(path,**kwargs):
            return SimpleNamespace(append_data=lambda data:frames.append(data.shape),close=lambda:Path(path).write_bytes(b'EXPLICIT_CPU_FAKE_ENCODING'))
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            r=Recorder(scene,Path(directory)/'hd',writer_factory=writer);r.capture(scene,step_index=0,force=True)
            m.left_camera.entity.pose[0,3]=.12;r.capture(scene,step_index=10);receipt=r.close(scene,terminal_status='CPU_FIXTURE')
            self.assertEqual(frames,[(1440,2880,3)]*2);self.assertEqual(len(removed),6);self.assertTrue(all(c.w==960 and c.h==720 for c in created));self.assertTrue(np.array_equal(created[1].entity.pose,m.left_camera.entity.pose));self.assertEqual(receipt['sampled_step_indices'],[0,10]);self.assertFalse(receipt['RGB_upscaled'])
            self.assertEqual(m.left_camera.picture_calls,0);self.assertEqual(m.left_camera.w,320)
    def test_abort_error_cannot_skip_inner_exit_or_mask_primary(self):
        calls=[];scene=SimpleNamespace()
        class Inner:
            cleanup_receipt={}
            def __enter__(self):return SimpleNamespace(scene=scene)
            def __exit__(self,*args):calls.append('inner_exit')
        class BadRecorder:
            closed=False
            def __init__(self,*a):pass
            def capture(self,*a,**k):raise ValueError('primary capture failure')
            def abort(self,*a):calls.append('abort');raise RuntimeError('abort cleanup failure')
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory,patch('goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.runtime.Recorder',BadRecorder):
            with self.assertRaisesRegex(ValueError,'primary capture failure'):Context(Inner(),Path(directory)).__enter__()
            audit=json.loads((Path(directory)/'HD_start_failure.json').read_text(encoding='utf-8'));self.assertEqual(calls,['abort','inner_exit']);self.assertEqual(audit['cleanup_errors'][0]['message'],'abort cleanup failure')
    def test_model_configuration_mutation_rejected(self):
        m=manager();r=Recorder.__new__(Recorder);r.manager=m;r.original_static=list(m.static_camera_list);r.original_names=list(m.static_camera_name);r.original_wrist=(m.left_camera,m.right_camera);r.sources=inventory(m)
        from .recorder import state
        r.source_states=[state(c) for _,c in r.sources];m.left_camera.K[0,0]+=1
        with self.assertRaises(ValueError):r.unchanged()
def load_tests(loader,tests,pattern):
    return unittest.TestSuite([loader.loadTestsFromName('goal_pilot48_v1.f3_upright_qualification_runtime_v1.test_all'),
        loader.loadTestsFromName('goal_pilot48_v1.runtime.test_upright_issuer'),tests])
if __name__=='__main__':unittest.main()
