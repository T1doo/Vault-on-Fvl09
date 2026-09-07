"""Parent visually approved depth-buffer preview -> one CPU movie per family."""
import os,sys,time,subprocess
from pathlib import Path
import cv2,numpy as np
from . import preview_v5 as preview,render_v4 as source
from realization_utf8_io_v1 import write_new
def render(family):
    began=time.monotonic();ns=preview.context(family);out=preview.OUT;code=preview.CODE
    video=out/(family+'_current_diagnostic_1080p_3views.mp4')
    if video.exists():raise FileExistsError(video)
    command=[str(source.old.FFMPEG),'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','bgr24','-s','1920x1080','-r','12','-i','-',
      '-an','-c:v','libx264','-preset','veryfast','-crf','19','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    child=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE);start=code/(family+'_PROCESS_START_005.json')
    write_new(start,source.old.seal({'family':family,'python_namespace_pid':os.getpid(),'ffmpeg_namespace_pid':child.pid,'CPU_only':True,
      'output_namespace':str(out),'per_movie_timeout_seconds':300,'inner_deadline_seconds':280,'monotonic_start':began}))
    print(family,'ZBUFFER_VIDEO_START',os.getpid(),child.pid,flush=True)
    screenshots={};selected=ns['selected'];samples={selected[0]:'initial',selected[len(selected)//2]:'middle',selected[-1]:'final'}
    try:
        for ordinal,index in enumerate(ns['indices']):
            if time.monotonic()-began>280:raise TimeoutError('280s zbuffer render deadline')
            image=preview.frame(ns,index);child.stdin.write(image.tobytes())
            if index in samples and samples[index] not in screenshots:
                name=samples[index];p=out/(family+'_'+name+'_frame_zbuffer_1080p.png')
                if p.exists():
                    if not np.array_equal(cv2.imread(str(p)),image):raise ValueError('existing approved preview differs')
                else:cv2.imwrite(str(p),image)
                screenshots[name]={'source_row':index,'path':str(p),'sha256':source.old.sha(p)}
            if ordinal%24==0:print(family,'FRAME',ordinal,'of',len(ns['indices']),'elapsed',round(time.monotonic()-began,1),flush=True)
        child.stdin.close();rc=child.wait(timeout=20)
        if rc:raise RuntimeError(child.stderr.read().decode('utf-8')[:1000])
    except BaseException as exc:
        if child.poll() is None:child.kill()
        child.wait(timeout=10)
        write_new(code/(family+'_CPU_FAILURE_005.json'),source.old.seal({'family':family,'pass':False,'error':{'type':type(exc).__name__,'message':str(exc)},
          'ffmpeg_namespace_pid':child.pid,'ffmpeg_reaped':child.poll() is not None,'elapsed_seconds':time.monotonic()-began}));raise
    files=list(dict.fromkeys([*ns['g']['files'],*ns['meshfiles'],source.old.URDF,source.old.A/'f3_model_replay_v1/kinematics_cpu.py',
      Path(source.old.__file__),Path(source.__file__),Path(preview.__file__),Path(__file__).with_name('zbuffer.py'),Path(__file__),source.old.FFMPEG,start]))
    receipt=source.old.seal({'schema_version':'diagnostic_cpu_zbuffer_video_v5','family':family,'video_path':str(video),'video_sha256':source.old.sha(video),
      'width':1920,'height':1080,'fps':12,'frames':len(ns['indices']),'duration_seconds':len(ns['indices'])/12,'source_rows':ns['n'],
      'source_frequency_hz':250,'source_duration_seconds':ns['duration'],'sampled_source_row_indices':selected,'final_hold_frames':24,'screenshots':screenshots,
      'view_types':['diagnostic_overview','diagnostic_close_up','diagnostic_side'],'original_camera_RGB':False,'six_real_cameras_delivered':False,
      'new_rollout':False,'GPU_used':False,'simulator_scene_created':False,'unexecuted_goals_drawn':False,'failure_label':ns['g']['failure'],
      'rasterization':'orthographic per-pixel barycentric z-buffer, not centroid painter ordering','near_view_focus_world':ns['g']['focus'].tolist(),
      'robot_geometry':'URDF collision mesh convex envelopes','object_world_geometry':'native pieces at measured actor poses',
      'initial_final_FK_max_matrix_error':ns['fk_errors'],'ffmpeg_namespace_pid':child.pid,'ffmpeg_reaped':child.poll() is not None,
      'elapsed_seconds':time.monotonic()-began,'source_files':{str(p):source.old.sha(p) for p in files},'not_accepted_trajectory_or_scientific_evidence':True})
    write_new(code/(family+'_VIDEO_RECEIPT_005.json'),receipt);print(family,'ZBUFFER_VIDEO_DONE',round(receipt['elapsed_seconds'],2),str(video),flush=True)
if __name__=='__main__':render(sys.argv[1])
