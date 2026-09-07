"""Fast CPU depth-sorted mesh diagnostic, not original camera RGB."""
import os,sys,time,math,subprocess
from pathlib import Path
import numpy as np
import cv2
from . import render as old
from realization_utf8_io_v1 import write_new
CODE=Path(__file__).parent/'attempt4';OUT=old.W/'Robotwin2/datasets/diagnostic_video_reconstruction_v4'

def panel(triangles,colors,center,width_m,height_m,elev,azim,path):
    w,h=608,740;canvas=np.full((h,w,3),(245,247,250),np.uint8)
    az,el=np.radians([azim,elev]);z=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    x=np.array([-np.sin(az),np.cos(az),0]);y=np.cross(z,x);scale=min(w/width_m,h/height_m)
    delta=triangles-center;depth=delta.mean(1)@z
    coords=np.stack((w/2+(delta@x)*scale,h/2-(delta@y)*scale),axis=-1)
    visible=(coords.max(1)[:,0]>=0)&(coords.min(1)[:,0]<w)&(coords.max(1)[:,1]>=0)&(coords.min(1)[:,1]<h)
    indices=np.flatnonzero(visible);indices=indices[np.argsort(depth[indices])]
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);length=np.linalg.norm(normals,axis=1)
    lighting=np.array([.3,-.4,.866]);shade=.58+.42*np.abs(normals@lighting/np.maximum(length,1e-12))
    shaded=np.clip(colors*shade[:,None],0,255).astype(np.uint8)
    for i in indices:
        cv2.fillConvexPoly(canvas,np.rint(coords[i]).astype(np.int32),tuple(int(v) for v in shaded[i]),lineType=cv2.LINE_AA)
    if len(path)>1:
        q=path-center;points=np.rint(np.stack((w/2+q@x*scale,h/2-q@y*scale),axis=-1)).astype(np.int32)
        cv2.polylines(canvas,[points],False,(65,65,190),2,cv2.LINE_AA)
    cv2.rectangle(canvas,(0,0),(w-1,h-1),(185,195,205),2)
    return canvas

def render(family):
    began=time.monotonic();g=old.geometry(family);OUT.mkdir(parents=True,exist_ok=True);video=OUT/(family+'_current_diagnostic_1080p_3views.mp4')
    if video.exists():raise FileExistsError(video)
    with np.load(g['trace'],allow_pickle=False) as z:
        arrays={k:z[k].copy() for k in ['joint_qpos','realized_left_gripper_joint_qpos','realized_right_gripper_joint_qpos','object_pose','eef_pose','timestamp','planner_goal_source']}
        roleposes={k:z['role_object_pose__'+role].copy() for k,role in g['roles'].items()}
    n=len(arrays['joint_qpos']);duration=float(arrays['timestamp'][-1]-arrays['timestamp'][0]);fps=12
    selected=np.unique(np.rint(np.linspace(0,n-1,max(2,math.ceil(duration*fps)))).astype(int)).tolist();indices=selected+[n-1]*(fps*2)
    robots,meshfiles=old.robot_meshes();optimization=[]
    for m in robots:
        v,f=m['vertices'],m['faces'];used,inv=np.unique(f.reshape(-1),return_inverse=True)
        nf=inv.reshape(f.shape)
        if not np.array_equal(v[f],v[used][nf]):raise ValueError('triangle geometry changed')
        optimization.append({'link':m['link'],'original_vertices':len(v),'used_vertices':len(used),'exact_triangles_equal':True});m['vertices']=v[used];m['faces']=nf
    B=old.matrix(g['base']);world=[];palette={'table':(174,199,219),'box':(202,143,84),'scale':(120,159,181),'stand':(146,169,136),'pad':(115,145,223)}
    for s in g['world']:
        if s['role'] in palette:world.append({'vertices':np.asarray(s['vertices']),'faces':np.asarray(s['faces'],dtype=int),'T':B@old.matrix(s['solver_pose']),
          'local':old.matrix(s['shape_local_pose']),'role':s['role'],'color':palette[s['role']]})
    parts=[{'vertices':np.asarray(s['vertices']),'faces':np.asarray(s['faces'],dtype=int),'T':old.matrix(s['shape_local_pose'])} for s in g['obj']]
    fk_errors=[]
    for i in (0,n-1):
        q=old.named_state(arrays,i);T=B@np.linalg.inv(old.root_transform('fl_base_link',q))@old.root_transform('fl_link6',q)
        fk_errors.append(float(np.max(np.abs(T-old.matrix(arrays['eef_pose'][i])))))
    if max(fk_errors)>1e-4:raise ValueError('URDF FK does not reproduce measured EEF frame')
    command=[str(old.FFMPEG),'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','bgr24','-s','1920x1080','-r',str(fps),'-i','-',
      '-an','-c:v','libx264','-preset','veryfast','-crf','19','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    child=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    start=CODE/(family+'_PROCESS_START_004.json');write_new(start,old.seal({'family':family,'python_namespace_pid':os.getpid(),'ffmpeg_namespace_pid':child.pid,
      'CPU_only':True,'output_namespace':str(OUT),'monotonic_start':began,'triangle_compaction':optimization}))
    print(family,'CPU_RASTER_START',os.getpid(),child.pid,flush=True)
    try:
        for fi,index in enumerate(indices):
            if time.monotonic()-began>280:raise TimeoutError('280s CPU raster deadline')
            q=old.named_state(arrays,index);R=B@np.linalg.inv(old.root_transform('fl_base_link',q));tri=[];color=[]
            for m in world:
                T=old.matrix(roleposes[m['role']][index])@m['local'] if m['role'] in roleposes else m['T']
                v=m['vertices']@T[:3,:3].T+T[:3,3];f=v[m['faces']];tri.append(f);color.extend([m['color']]*len(f))
            for m in robots:
                T=R@old.root_transform(m['link'],q);v=m['vertices']@T[:3,:3].T+T[:3,3];f=v[m['faces']];tri.append(f)
                color.extend([(153,121,40) if m['link'].startswith('fl') else (155,153,147)]*len(f))
            T=old.matrix(arrays['object_pose'][index])
            for m in parts:
                M=T@m['T'];v=m['vertices']@M[:3,:3].T+M[:3,3];f=v[m['faces']];tri.append(f);color.extend([(27,190,247)]*len(f))
            triangles=np.concatenate(tri);colors=np.asarray(color,dtype=float);frame=np.full((1080,1920,3),248,np.uint8)
            path=arrays['object_pose'][:index+1:5,:3]
            config=[(np.array([-.03,-.13,.98]),1.30,1.02,25,-63),
              (g['focus'],.48 if family=='F2' else .27,.59 if family=='F2' else .35,22,-63),
              (g['focus'],.48 if family=='F2' else .27,.59 if family=='F2' else .35,15,5)]
            for j,view in enumerate(config):
                left=24+j*632;frame[234:974,left:left+608]=panel(triangles,colors,*view,path)
                cv2.putText(frame,['DIAGNOSTIC OVERVIEW','DIAGNOSTIC CLOSE-UP','DIAGNOSTIC SIDE'][j],(left+40,214),cv2.FONT_HERSHEY_SIMPLEX,.78,(55,65,75),2,cv2.LINE_AA)
            lines=[(f'{family}: MEASURED TRACE - 1080p THREE-VIEW DIAGNOSTIC',(36,48),1.05,(35,52,69)),
              ('RECONSTRUCTED FROM TRACE / NOT NEW ROLLOUT / NOT ORIGINAL CAMERA RGB',(36,90),.77,(52,52,174)),
              (g['failure'],(36,140),.87,(45,45,180)),(g['detail'],(36,174),.65,(70,80,90))]
            for text,xy,size,c in lines:cv2.putText(frame,text,xy,cv2.FONT_HERSHEY_SIMPLEX,size,c,2,cv2.LINE_AA)
            elapsed=arrays['timestamp'][index]-arrays['timestamp'][0];phase=str(arrays['planner_goal_source'][index,0]) or 'measured hold/settle'
            cv2.putText(frame,f'Measured {elapsed:.3f}s | row {index}/{n-1} | {phase}',(36,1010),cv2.FONT_HERSHEY_SIMPLEX,.75,(35,52,69),2,cv2.LINE_AA)
            cv2.putText(frame,'Teal robot FK / Gold measured object / Red executed path. Native meshes + robot convex envelopes. No unexecuted targets.',(36,1047),cv2.FONT_HERSHEY_SIMPLEX,.62,(75,85,95),1,cv2.LINE_AA)
            child.stdin.write(frame.tobytes())
            if fi==len(selected)-1:cv2.imwrite(str(OUT/(family+'_final_frame_1080p.png')),frame)
            if fi%24==0:print(family,'FRAME',fi,'of',len(indices),'elapsed',round(time.monotonic()-began,1),flush=True)
        child.stdin.close();rc=child.wait(timeout=20)
        if rc:raise RuntimeError(child.stderr.read().decode('utf-8')[:1000])
    except BaseException as e:
        if child.poll() is None:child.kill()
        child.wait(timeout=10)
        write_new(CODE/(family+'_CPU_FAILURE_004.json'),old.seal({'family':family,'pass':False,'error':{'type':type(e).__name__,'message':str(e)},'ffmpeg_namespace_pid':child.pid,
          'ffmpeg_reaped':child.poll() is not None,'elapsed_seconds':time.monotonic()-began}));raise
    files=list(dict.fromkeys([*g['files'],*meshfiles,old.URDF,old.A/'f3_model_replay_v1/kinematics_cpu.py',Path(old.__file__),Path(__file__),old.FFMPEG,start]))
    receipt=old.seal({'schema_version':'diagnostic_cpu_raster_video_v4','family':family,'video_path':str(video),'video_sha256':old.sha(video),'width':1920,'height':1080,
      'fps':fps,'frames':len(indices),'duration_seconds':len(indices)/fps,'source_rows':n,'source_duration_seconds':duration,'source_frequency_hz':250,
      'view_types':['diagnostic_overview','diagnostic_close_up','diagnostic_side'],'original_camera_RGB':False,'six_real_cameras_delivered':False,
      'new_rollout':False,'GPU_used':False,'simulator_scene_created':False,'unexecuted_goals_drawn':False,'failure_label':g['failure'],
      'rasterization':'CPU OpenCV orthographic projection with depth-sorted mesh triangles; diagnostic approximation',
      'robot_geometry':'exact convex-envelope triangles of source URDF collision meshes','object_world_geometry':'source native pieces at measured poses',
      'source_files':{str(p):old.sha(p) for p in files},'sampled_source_row_indices':selected,'final_hold_frames':24,
      'initial_final_FK_max_matrix_error':fk_errors,'ffmpeg_namespace_pid':child.pid,'ffmpeg_reaped':child.poll() is not None,
      'elapsed_seconds':time.monotonic()-began,'not_accepted_trajectory_or_scientific_evidence':True})
    write_new(CODE/(family+'_VIDEO_RECEIPT_004.json'),receipt);print(family,'VIDEO_DONE',round(receipt['elapsed_seconds'],2),str(video),flush=True)
if __name__=='__main__':render(sys.argv[1])
