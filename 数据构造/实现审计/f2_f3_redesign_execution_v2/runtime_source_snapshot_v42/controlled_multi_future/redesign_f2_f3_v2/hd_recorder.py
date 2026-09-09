"""Independent native-resolution debug cameras; never resize model RGB."""
import math,os,hashlib,time
from pathlib import Path
import numpy as np
WIDTH=960;HEIGHT=720;FPS=25;STRIDE=10;MAX_VIEWS=24;MAX_FRAMES=602
FONT=Path('/nfs_share/lijunhui/Robotwin2/env/lib/python3.10/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf')
def inventory(manager):
    static=list(zip(manager.static_camera_name,manager.static_camera_list));head=next((c for n,c in static if n=='head_camera'),None)
    pairs=[('head',head),('left_wrist',getattr(manager,'left_camera',None)),('right_wrist',getattr(manager,'right_camera',None))]
    if any(c is None for _,c in pairs):raise ValueError('required model head/left/right camera absent')
    pairs += [(label,getattr(manager,attr,None)) for label,attr in [('observer','observer_camera'),('world1','world_camera1'),('world2','world_camera2')]]
    pairs += [('static_'+str(i)+'_'+str(n),c) for i,(n,c) in enumerate(static)]
    seen=set();out=[]
    for label,camera in pairs:
        if camera is None or id(camera) in seen:continue
        seen.add(id(camera));out.append((label,camera))
    if len(out)>MAX_VIEWS:raise ValueError('debug view finite memory budget exceeded; no views silently omitted')
    return out
def intrinsic(source):
    K=np.asarray(source.get_intrinsic_matrix(),float).copy();sx=WIDTH/source.get_width();sy=HEIGHT/source.get_height();K[0]*=sx;K[1]*=sy;return K
def page_layout(count):return [list(range(i,min(i+6,count))) for i in range(0,count,6)]
def state(source):return {'width':source.get_width(),'height':source.get_height(),'K':np.asarray(source.get_intrinsic_matrix()).tolist(),'near':float(source.get_near()),'far':float(source.get_far())}
class Recorder:
    def __init__(self,scene,directory,writer_factory=None):
        import imageio.v2 as imageio
        import imageio_ffmpeg
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False)
        self.video_fps=FPS;self.sample_stride_steps=STRIDE;self.closed=False;self.frame_count=0;self.sampled_step_indices=[];self.clones=[];self.writers=[];self.sources=[];self.last=None;self.render_seconds=0.
        self.manager=scene.cameras;self.original_static=list(self.manager.static_camera_list);self.original_names=list(self.manager.static_camera_name)
        self.original_wrist=(self.manager.left_camera,self.manager.right_camera)
        self.sources=inventory(self.manager);self.source_states=[state(c) for _,c in self.sources];self.pages=page_layout(len(self.sources))
        factory=writer_factory or imageio.get_writer
        if writer_factory is None and not Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve().is_relative_to('/nfs_share/lijunhui'):raise ValueError('ffmpeg executable outside workspace')
        try:
            for i,(label,source) in enumerate(self.sources):
                K=intrinsic(source);near=float(source.get_near());far=float(source.get_far())
                clone=scene.scene.add_camera('audit_HD_'+str(i)+'_'+label,WIDTH,HEIGHT,2*math.atan(HEIGHT/(2*K[1,1])),near,far)
                clone.set_perspective_parameters(near,far,float(K[0,0]),float(K[1,1]),float(K[0,2]),float(K[1,2]),float(K[0,1]))
                clone.set_local_pose(source.get_local_pose());self.clones.append(clone)
                if clone.get_width()!=WIDTH or clone.get_height()!=HEIGHT:raise ValueError('debug camera is not native960x720')
            for i,_ in enumerate(self.pages):
                path=self.directory/f'upright_hd_views_page{i+1:02d}.partial.mp4'
                self.writers.append(factory(str(path),format='FFMPEG',mode='I',fps=FPS,codec='libx264',macro_block_size=2,ffmpeg_log_level='error',ffmpeg_params=['-crf','20','-preset','veryfast','-threads','2','-movflags','+faststart']))
        except BaseException:
            self.abort(scene);raise
    def unchanged(self):
        if list(self.manager.static_camera_list)!=self.original_static or list(self.manager.static_camera_name)!=self.original_names or (self.manager.left_camera,self.manager.right_camera)!=self.original_wrist:raise ValueError('model camera registry changed')
        if [state(c) for _,c in self.sources]!=self.source_states:raise ValueError('source/model camera configuration changed')
    def capture(self,scene,*,step_index,force=False):
        if self.closed:raise RuntimeError('HD recorder closed')
        step_index=int(step_index)
        if (not force and step_index%STRIDE) or self.last==step_index:return False
        if self.last is not None and step_index<self.last:raise ValueError('HD trace step moved backwards')
        if self.frame_count>=MAX_FRAMES:raise RuntimeError('HD finite frame cap reached')
        self.unchanged();start=time.monotonic();scene._update_render()
        for clone,(_,source) in zip(self.clones,self.sources):clone.entity.set_pose(source.entity.get_pose());clone.set_local_pose(source.get_local_pose())
        scene.scene.update_render();frames=[]
        for clone,(_,source) in zip(self.clones,self.sources):
            if not np.allclose(clone.get_model_matrix(),source.get_model_matrix(),atol=1e-6,rtol=0):raise ValueError('HD cloned camera extrinsic differs')
            clone.take_picture();rgba=np.asarray(clone.get_picture('Color'))
            if rgba.shape!=(HEIGHT,WIDTH,4) or not np.isfinite(rgba).all():raise ValueError('native HD pixel shape/data invalid')
            frames.append(np.ascontiguousarray((np.clip(rgba[:,:,:3],0,1)*255).astype(np.uint8)))
        from PIL import Image,ImageDraw,ImageFont
        font=ImageFont.truetype(str(FONT),28)
        for writer,page in zip(self.writers,self.pages):
            canvas=np.zeros((2*HEIGHT,3*WIDTH,3),dtype=np.uint8)
            for slot,idx in enumerate(page):r,c=divmod(slot,3);canvas[r*HEIGHT:(r+1)*HEIGHT,c*WIDTH:(c+1)*WIDTH]=frames[idx]
            image=Image.fromarray(canvas);draw=ImageDraw.Draw(image)
            for slot,idx in enumerate(page):
                r,c=divmod(slot,3);x=c*WIDTH;y=r*HEIGHT;draw.rectangle((x,y,x+WIDTH,y+42),fill=(0,0,0));draw.text((x+12,y+4),f'{self.sources[idx][0]} | native 960x720 | step {step_index}',font=font,fill=(255,255,255))
            writer.append_data(np.asarray(image))
        self.render_seconds+=time.monotonic()-start;self.last=step_index;self.sampled_step_indices.append(step_index);self.frame_count+=1;return True
    def remove_clones(self,scene):
        errors=[]
        for camera in self.clones:
            try:scene.scene.remove_camera(camera)
            except BaseException as exc:errors.append(str(exc))
        self.clones=[]
        if errors:raise RuntimeError('HD camera cleanup failed: '+repr(errors))
    def abort(self,scene):
        for writer in self.writers:
            try:writer.close()
            except BaseException:pass
        self.closed=True;self.remove_clones(scene)
    def close(self,scene,*,terminal_status):
        if self.closed:return self.receipt
        final=max(0,int(getattr(scene,'_step_index',1))-1);error=None
        try:self.capture(scene,step_index=final,force=True)
        except BaseException as exc:error=exc
        finally:
            for writer in self.writers:
                try:writer.close()
                except BaseException as exc:error=error or exc
            self.closed=True
            try:self.remove_clones(scene)
            except BaseException as exc:error=error or exc
        if error:raise error
        self.unchanged();pages=[]
        for i,page in enumerate(self.pages):
            partial=self.directory/f'upright_hd_views_page{i+1:02d}.partial.mp4';path=self.directory/f'upright_hd_views_page{i+1:02d}.mp4'
            if path.exists() or not partial.is_file() or self.frame_count<1:raise ValueError('missing or conflicting HD video output')
            os.replace(partial,path);pages.append({'path':str(path),'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'labels':[self.sources[j][0] for j in page],'width':3*WIDTH,'height':2*HEIGHT,'frame_count':self.frame_count})
        self.receipt={'schema_version':'cmf_live_native_HD_multiview_v2','pages':pages,'views':[{'label':label,'source_configuration':config} for (label,_),config in zip(self.sources,self.source_states)],
            'native_camera_resolution':[WIDTH,HEIGHT],'mosaic_resolution':[3*WIDTH,2*HEIGHT],'video_fps':FPS,'sample_stride_steps':STRIDE,'sampled_step_indices':self.sampled_step_indices,
            'includes_initial_frame':0 in self.sampled_step_indices,'includes_final_frame':final in self.sampled_step_indices,'frame_count':self.frame_count,'render_and_encode_seconds':self.render_seconds,
            'model_camera_configuration_unchanged':True,'reconstruction':False,'RGB_upscaled':False,'settle_frames_recorded':False,'post_settle_initial_only':self.frame_count==1,'terminal_context_status':terminal_status}
        return self.receipt
