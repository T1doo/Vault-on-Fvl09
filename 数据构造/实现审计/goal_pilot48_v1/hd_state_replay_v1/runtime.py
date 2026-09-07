"""Native-HD camera replay of saved states; no task actions or physics stepping."""
import json
import hashlib
import types
from pathlib import Path
import numpy as np
from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.recorder import Recorder as OriginalRecorder
from realization_utf8_io_v1 import write_new

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def sample_indices(count):
    if type(count) is not int or count<2:raise ValueError('at least two measured states required')
    return sorted(set([*range(0,count,10),count-1]))

def load_trace(path):
    with np.load(path,allow_pickle=False) as saved:
        q=saved['joint_qpos'].copy();t=saved['timestamp'].copy()
        roles={k.removeprefix('role_object_pose__'):saved[k].copy() for k in saved.files if k.startswith('role_object_pose__')}
    if q.ndim!=2 or q.shape[1]!=38 or len(q)!=len(t) or not roles:
        raise ValueError('unsupported measured articulation/role layout')
    if not np.isfinite(q).all() or not np.isfinite(t).all() or not np.allclose(np.diff(t),.004,atol=1e-9,rtol=0):
        raise ValueError('invalid measured states or timebase')
    if any(v.shape!=(len(q),7) or not np.isfinite(v).all() for v in roles.values()):
        raise ValueError('invalid measured role poses')
    return q,t,roles

def restore(scene,q,roles,index,pose_factory):
    if scene.robot.left_entity is not scene.robot.right_entity:
        raise ValueError('expected the recorded shared38-DOF articulation')
    entity=scene.robot.left_entity
    if len(entity.get_qpos())!=38:raise ValueError('render articulation differs from measured states')
    if set(scene.role_actors)!=set(roles):raise ValueError('render actor roles differ from saved scene')
    entity.set_qpos(q[index])
    for role,values in roles.items():
        actor=scene.role_actors[role]
        native=actor.actor if hasattr(actor,'actor') else actor
        native.set_pose(pose_factory(values[index]))
    if not np.allclose(entity.get_qpos(),q[index],atol=1e-6,rtol=0):
        raise ValueError('measured joint restoration failed')
    for role,values in roles.items():
        actor=scene.role_actors[role];native=actor.actor if hasattr(actor,'actor') else actor
        actual=native.get_pose();p=np.r_[actual.p,actual.q]
        target=values[index]
        if not np.allclose(p[:3],target[:3],atol=1e-6,rtol=0) or abs(float(np.dot(p[3:],target[3:])))<1-1e-6:
            raise ValueError('measured actor restoration failed '+role)

def run(manifest,*,meter):
    job=manifest['jobs'][0];out=Path(job['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    item=manifest['render_item'];trace=Path(item['trace_path']);specpath=Path(item['planned_spec_path'])
    before=dict(meter.counts);ctx=None;recorder=None;error=None;video=None;rendered=0
    try:
        if sha(trace)!=item['trace_sha256'] or sha(specpath)!=item['planned_spec_sha256']:
            raise ValueError('render source changed')
        q,t,roles=load_trace(trace);indices=sample_indices(len(q))
        if len(indices)>job['max_video_frames']:raise ValueError('frozen frame budget exceeded')
        from controlled_multi_future.real_sapien_adapter_v1_2 import RoboTwinSceneContextV1_2
        from controlled_multi_future.real_sapien_adapter_high_level_v1 import _PinnedSapienRenderDeviceContextV1
        import sapien
        spec=json.loads(specpath.read_text(encoding='utf-8'))
        ctx=_PinnedSapienRenderDeviceContextV1(RoboTwinSceneContextV1_2(
            family=item['family'],planned_spec=spec,phase='HD_SAVED_STATE_RENDER_ONLY',program=None,
            output_root=out/'scene',sealed_implementation_source_sha256=manifest['implementation_source_sha256'],
            sealed_source_binding='render-only source states; no new collection acceptance'))
        # Versioned render-only frame cap, retaining the original native HD capture.
        class Recorder(OriginalRecorder):pass
        env=dict(OriginalRecorder.capture.__globals__);env['MAX_FRAMES']=job['max_video_frames']
        Recorder.capture=types.FunctionType(OriginalRecorder.capture.__code__,env)
        with ctx as handle:
            scene=handle.scene
            original_step=scene.scene.step
            def prohibited_step(*a,**k):raise RuntimeError('physics stepping prohibited during saved-state video replay')
            scene.scene.step=prohibited_step
            try:
                restore(scene,q,roles,0,lambda p:sapien.Pose(p[:3],p[3:]))
                import imageio.v2 as imageio
                import imageio_ffmpeg
                from PIL import Image,ImageDraw,ImageFont
                from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.recorder import FONT
                if not Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve().is_relative_to('/nfs_share/lijunhui'):
                    raise ValueError('encoder outside workspace')
                font=ImageFont.truetype(str(FONT),24)
                def writer_factory(path,**kwargs):
                    writer=imageio.get_writer(path,**kwargs)
                    def append(data):
                        image=Image.fromarray(data);draw=ImageDraw.Draw(image)
                        draw.rectangle((0,image.height-34,image.width,image.height),fill=(0,0,0))
                        draw.text((12,image.height-31),'SAVED-STATE RE-RENDER | '+item['label']+' | NOT A NEW ROLLOUT',font=font,fill=(255,255,255))
                        writer.append_data(np.asarray(image))
                    return types.SimpleNamespace(append_data=append,close=writer.close)
                recorder=Recorder(scene,out/'video_hd',writer_factory=writer_factory)
                for index in indices:
                    restore(scene,q,roles,index,lambda p:sapien.Pose(p[:3],p[3:]))
                    scene._step_index=index+1
                    recorder.capture(scene,step_index=index,force=True)
                    rendered+=1
                video=recorder.close(scene,terminal_status='SAVED_STATE_RENDER_COMPLETE_NOT_NEW_ROLLOUT')
                video={**video,'schema_version':'cmf_hd_saved_state_multiview_video_v1','reconstruction':True,'original_camera_RGB':False,'new_rollout':False}
            finally:
                try:
                    if recorder is not None and not recorder.closed:recorder.abort(scene)
                finally:scene.scene.step=original_step
        if sha(trace)!=item['trace_sha256']:raise ValueError('source trace changed during replay')
    except BaseException as exc:
        import traceback
        error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    counts={k:meter.counts[k]-before[k] for k in before}
    cleanup=None if ctx is None else ctx.cleanup_receipt
    known=counts['solver_problems']==0 and counts['action_scenes']==0 and counts['collection_attempts']==0 and counts['fresh_scenes']<=1
    passed=error is None and video is not None and cleanup is not None and cleanup.get('cleanup_safety_pass') is True and known
    result={'schema_version':'cmf_native_HD_saved_state_render_v1','pass':passed,'scientific_route_pass':False,
        'render_pass':passed,'accounting_complete':known,'scene_attempts':counts['fresh_scenes'],'collection_attempts':0,
        'error':error,'cleanup':cleanup,'video':video,'rendered_frames':rendered,'item':item,
        'saved_state_reconstruction':True,'original_camera_RGB':False,'new_physical_rollout':False,
        'primary_data_modified':False,'rendering_source_profile':manifest['implementation_source_sha256'],
        'no_task_physics_steps':True,'source_check_is_not_new_family_acceptance':True}
    payload=json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    result['receipt_sha256']=hashlib.sha256(payload.encode('utf-8')).hexdigest()
    write_new(out/'render_terminal.json',result)
    return result
