"""Native scene subclasses: explicit formal spec, no root-name defaults.

Import only inside an authorized UUID-bound GPU worker. Never imported by CPU tests.
"""
import numpy as np
import sapien
from pathlib import Path
from envs.utils import create_box,create_visual_box
from controlled_multi_future.probes.scene_inspection import AuditScene
from controlled_multi_future.probes.runtime_trace import DenseTraceMixin
from controlled_multi_future.redesign_f2_f3_v2.factory import load_model_spec,build_actor
from controlled_multi_future.redesign_f2_f3_v2.scene import NativeAssetHandle
ASSETS=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets')
class FormalBase(DenseTraceMixin,AuditScene):
 def setup_demo(self,**kw):
  self.formal_spec=kw.pop('formal_scene_spec');kw.pop('scene_variant',None);kw.pop('f2_layout_id',None)
  from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
  from types import SimpleNamespace
  outer=self
  class SetupContext:
   def __enter__(self):
    super(FormalBase,outer).setup_demo(**kw)
    return SimpleNamespace(scene=outer)
   def __exit__(self,*args):return False # managed_scene owns the actual cleanup
  with _PinnedSapienRenderDeviceContextV1(SetupContext()):
   from native_f1_factory import bind_cameras
   bind_cameras(self,self.formal_spec['resolved_scene_spec'])
 def add_role(self,r,name=None):
  name=name or r['role'];p=r['pose'];q=sapien.Pose(p[:3],p[3:]);asset=r['asset']
  if asset in ('071_can:model0','114_bottle:model1'):
   model,mid=asset.split(':model');spec=load_model_spec(ASSETS,model,model_id=int(mid),asset_id=r['role']);actor=NativeAssetHandle(build_actor(self.scene,spec,q,convex=True,dynamic=r['dynamic'],name=name),spec)
  elif asset=='visual_box':
   actor=create_visual_box(self,q,tuple(np.array(r['size'])/2),color=tuple(r['color']),name=name)
  else:
   actor=create_box(self,q,tuple(np.array(r['size'])/2),color=tuple(r['color']),is_static=not r['dynamic'],name=name)
  return actor
class FormalF2Scene(FormalBase):
 family_id='F2'
 def load_actors(self):
  s=self.formal_spec;resolved=s['resolved_scene_spec'];by={r['role']:r for r in resolved['roles']};f=s['f2'];self.role_actors={}
  self.can=self.add_role(by['main_can'],'f2_redesign_can');self.role_actors['main_can']=self.can
  self.box_center=np.asarray(f['box_center_xyz']);x,y,z=self.box_center
  self.box_bottom=create_box(self,sapien.Pose([x,y,z]),(.12,.12,.005),is_static=True,name='f2_redesign_box_bottom');self.role_actors['box_bottom']=self.box_bottom
  for label,xyz,size in [('left',[x-.115,y,.805],(.005,.12,.05)),('right',[x+.115,y,.805],(.005,.12,.05)),('front',[x,y-.115,.805],(.12,.005,.05)),('back',[x,y+.115,.805],(.12,.005,.05))]:
   a=create_box(self,sapien.Pose(xyz),size,is_static=True,name='f2_redesign_box_'+label+'_wall');setattr(self,'box_'+label,a);self.role_actors['box_'+label]=a
  self.scale=self.add_role(by['scale'],'f2_redesign_scale');self.stand=self.add_role(by['stand'],'f2_redesign_stand');self.role_actors.update(scale=self.scale,stand=self.stand)
  self.scale_center=np.asarray(f['scale_center_xyz']);self.stand_center=np.asarray(f['stand_center_xyz']);self.beside_target_xy=np.asarray(f['beside_target_xy'])
  for r in resolved['roles']:
   if r['role'] not in ('main_can','box','scale','stand'):self.role_actors[r['role']]=self.add_role(r)
  self.role_actors.update(table=self.table,wall=self.wall)
class FormalF3Scene(FormalBase):
 family_id='F3'
 def load_actors(self):
  by={r['role']:r for r in self.formal_spec['resolved_scene_spec']['roles']};self.bottle=self.add_role(by['bottle'],'f3_redesign_bottle');self.pad=self.add_role(by['original_pad'],'f3_redesign_support_pad');self.role_actors={'bottle':self.bottle,'original_pad':self.pad}
  for r in by.values():
   if r['role'] not in ('bottle','original_pad'):self.role_actors[r['role']]=self.add_role(r)
  self.role_actors.update(table=self.table,wall=self.wall)
