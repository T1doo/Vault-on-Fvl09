"""CPU Agg/ffmpeg reconstruction of measured states, never a simulator rollout."""
import json,sys,time,hashlib,math,subprocess
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.spatial import ConvexHull
import trimesh
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计';P=W/'Robotwin2/project/RoboTwin'
OUT=W/'Robotwin2/datasets/diagnostic_video_reconstruction_v1';CODE=Path(__file__).parent
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import TREE,origin,root_transform,named_state,URDF
from goal_pilot48_v1.f2_inward_runtime_v1.collision import matrix,pose
from realization_utf8_io_v1 import write_new
FFMPEG=W/'Robotwin2/env/bin/ffmpeg'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def seal(v):return {**v,'receipt_sha256':hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()}

def geometry(family):
    if family=='F2':
        d=W/'Robotwin2/datasets/p48_f2_inside_carry_revision1_002';source=d/'model_010_carried_full.json';m=read(source)
        trace=d/'qualification_trace.npz';world=m['world']['shapes'];obj=m['can'];base=m['base'];roles={'box':'box','scale':'scale','stand':'stand'}
        result=d/'inside_result.json';failure='PREINSERT PLAN FAILED - not executed';detail='Held can reached carry waypoint; no insertion / no release'
        files=[source,trace,result,d/'goal_terminal.json'];objname='CAN';focus=[-.30,-.18,.87]
    elif family=='F3':
        d=W/'Robotwin2/datasets/p48_f3_one_sided_micro_001';source=d/'postclose_attached_model.json';m=read(source)
        worldpath=W/'Robotwin2/datasets/f3_remaining_model_scene_v1_1/remaining_scene/f3-final-pose-v3-r3063/initial_geometry.json'
        world=read(worldpath)['shapes'];obj=m['native_bottle_shapes'];s=obj[0]
        base=pose(matrix(s['actor_world_pose'])@matrix(s['shape_local_pose'])@np.linalg.inv(matrix(s['solver_pose'])))
        trace=d/'physical_trace.npz';roles={'pad':'original_pad'};result=d/'goal_terminal.json'
        failure='POST-LIFT GRASP-STABILITY GATE FAILED';detail='Measured grip drift: 6.06 mm / 3.30 deg; shared V not executed'
        files=[source,worldpath,trace,result,d/'scene_binding.json'];objname='BOTTLE';focus=[-.185,-.06,.82]
    else:raise ValueError('exactly F2 or F3')
    return dict(d=d,source=source,trace=trace,world=world,obj=obj,base=base,roles=roles,failure=failure,detail=detail,files=files,objname=objname,focus=np.asarray(focus))

def robot_meshes():
    meshes=[];files=[]
    for side in ('fl','fr'):
        for name in [side+'_base_link']+[side+'_link'+str(i) for i in range(1,9)]:
            link=TREE.find("link[@name='"+name+"']")
            if link is None:continue
            for node in link.findall('collision'):
                g=node.find('geometry');mesh=g.find('mesh');box=g.find('box')
                if mesh is not None:
                    path=P/'assets/embodiments/aloha-agilex/meshes'/Path(mesh.get('filename')).name
                    if not path.exists():raise FileNotFoundError(path)
                    loaded=trimesh.load(path,force='mesh',process=False);v=np.asarray(loaded.vertices);files.append(path)
                    v=v*np.fromstring(mesh.get('scale','1 1 1'),sep=' ')
                elif box is not None:v=np.asarray(trimesh.creation.box(extents=np.fromstring(box.get('size'),sep=' ')).vertices)
                else:raise ValueError('unsupported robot collision geometry '+name)
                T=origin(node);v=v@T[:3,:3].T+T[:3,3]
                # A collision-mesh convex envelope is an explicit diagnostic
                # drawing approximation, not rendered RGB or new contact truth.
                faces=ConvexHull(v).simplices
                meshes.append({'link':name,'vertices':v,'faces':faces,'color':'#147D92' if side=='fl' else '#7D8790','alpha':.85})
    return meshes,files

def render(family):
    began=time.monotonic();g=geometry(family);OUT.mkdir(parents=True,exist_ok=True);video=OUT/(family+'_current_diagnostic_1080p_3views.mp4')
    if video.exists():raise FileExistsError('one video per family; never overwrite '+str(video))
    with np.load(g['trace'],allow_pickle=False) as z:
        arrays={k:z[k].copy() for k in ['joint_qpos','realized_left_gripper_joint_qpos','realized_right_gripper_joint_qpos','object_pose','eef_pose','timestamp','planner_goal_source']}
        roleposes={k:z['role_object_pose__'+role].copy() for k,role in g['roles'].items()}
    n=len(arrays['joint_qpos']);duration=float(arrays['timestamp'][-1]-arrays['timestamp'][0]);fps=12
    selected=np.unique(np.rint(np.linspace(0,n-1,max(2,math.ceil(duration*fps)))).astype(int)).tolist();indices=selected+[n-1]*(fps*2)
    robot,robotfiles=robot_meshes();B=matrix(g['base']);world=[]
    colors={'table':'#D5C5A7','box':'#5080CB','scale':'#C08065','stand':'#667566','pad':'#DB765E'}
    for s in g['world']:
        if s['role'] not in colors:continue
        v=np.asarray(s['vertices']);faces=np.asarray(s['faces'],dtype=int)
        world.append({'vertices':v,'faces':faces,'T':B@matrix(s['solver_pose']),'local':matrix(s['shape_local_pose']),
          'role':s['role'],'color':colors[s['role']],'alpha':.33 if s['role']=='box' else .42 if s['role']=='table' else .68})
    object_parts=[{'vertices':np.asarray(s['vertices']),'faces':np.asarray(s['faces'],dtype=int),'T':matrix(s['shape_local_pose'])} for s in g['obj']]
    fig=plt.figure(figsize=(16,9),dpi=120,facecolor='#F7F9FC');axes=[];groups=[]
    views=[('DIAGNOSTIC OVERVIEW',25,-63),('DIAGNOSTIC CLOSE-UP',20,-63),('DIAGNOSTIC SIDE VIEW',15,5)]
    for j,(title,elev,azim) in enumerate(views):
        ax=fig.add_subplot(1,3,j+1,projection='3d');axes.append(ax);ax.set_proj_type('ortho');ax.view_init(elev=elev,azim=azim)
        ax.set_facecolor('#F7F9FC');ax.set_title(title,fontsize=14,pad=10);ax.set_xlabel('world X [m]');ax.set_ylabel('world Y [m]');ax.set_zlabel('Z [m]')
        if j==0:lims=([-.62,.50],[-.58,.32],[.67,1.38])
        else:
            span=np.array([.43,.43,.56]) if family=='F2' else np.array([.27,.27,.33]);c=g['focus'];lims=[(c[k]-span[k]/2,c[k]+span[k]/2) for k in range(3)]
        ax.set_xlim(lims[0]);ax.set_ylim(lims[1]);ax.set_zlim(lims[2]);ax.set_box_aspect([b-a for a,b in lims]);ax.tick_params(labelsize=8)
        artists=[]
        for item in world+robot:
            art=Poly3DCollection([],facecolors=item['color'],edgecolors='none',alpha=item['alpha']);ax.add_collection3d(art);artists.append(art)
        obj=Poly3DCollection([],facecolors='#F0B323',edgecolors='#6E4B12',linewidths=.2,alpha=1.);ax.add_collection3d(obj)
        line,=ax.plot([],[],[],color='#C84448',linewidth=2.,alpha=.9);groups.append((artists,obj,line))
    fig.subplots_adjust(left=.02,right=.98,bottom=.15,top=.78,wspace=.12)
    fig.text(.5,.955,f'{family}  |  REAL MEASURED STATES - 3-VIEW CPU RECONSTRUCTION',ha='center',fontsize=21,weight='bold',color='#193044')
    fig.text(.5,.915,'RECONSTRUCTED FROM TRACE / NOT NEW ROLLOUT / NOT ORIGINAL CAMERA RGB',ha='center',fontsize=14,color='#AB3035',weight='bold')
    fig.text(.5,.86,g['failure'],ha='center',fontsize=18,weight='bold',color='#AB3035')
    fig.text(.5,.822,g['detail'],ha='center',fontsize=12,color='#354655')
    progress=fig.text(.5,.09,'',ha='center',fontsize=14,color='#193044')
    fig.text(.5,.045,'Teal: measured robot FK | Gold: measured object | Red line: executed object path | No unexecuted target drawn',ha='center',fontsize=11,color='#45535D')
    fig.text(.5,.020,'Robot collision envelopes / native object-world meshes. 250 Hz source sampled at 12 fps; final state held 2 s.',ha='center',fontsize=10,color='#677680')
    command=[str(FFMPEG),'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(fps),'-i','-',
      '-an','-c:v','libx264','-preset','veryfast','-crf','19','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    child=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE);error=None
    try:
        for frame,index in enumerate(indices):
            if time.monotonic()-began>280:raise TimeoutError('280s inner render deadline')
            q=named_state(arrays,index);base_root=B@np.linalg.inv(root_transform('fl_base_link',q))
            transforms={item['link']:base_root@root_transform(item['link'],q) for item in robot}
            triangles=[]
            for item in world:
                T=matrix(roleposes[item['role']][index])@item['local'] if item['role'] in roleposes else item['T']
                v=item['vertices']@T[:3,:3].T+T[:3,3];triangles.append(v[item['faces']])
            for item in robot:
                T=transforms[item['link']];v=item['vertices']@T[:3,:3].T+T[:3,3];triangles.append(v[item['faces']])
            op=[];T=matrix(arrays['object_pose'][index])
            for item in object_parts:
                M=T@item['T'];v=item['vertices']@M[:3,:3].T+M[:3,3];op.extend(v[item['faces']])
            path=arrays['object_pose'][:index+1:10,:3]
            for artists,obj,line in groups:
                for art,verts in zip(artists,triangles):art.set_verts(verts)
                obj.set_verts(op);line.set_data(path[:,0],path[:,1]);line.set_3d_properties(path[:,2])
            elapsed=arrays['timestamp'][index]-arrays['timestamp'][0];phase=str(arrays['planner_goal_source'][index,0]) or 'measured hold / settle'
            progress.set_text(f'Measured time {elapsed:.3f} s | trace row {index}/{n-1} | {phase}'+(' | FINAL OBSERVED STATE' if index==n-1 else ''))
            fig.canvas.draw();rgba=np.asarray(fig.canvas.buffer_rgba());child.stdin.write(np.ascontiguousarray(rgba[:,:,:3]).tobytes())
            if index==n-1 and frame==len(selected)-1:fig.savefig(OUT/(family+'_final_frame_1080p.png'),dpi=120)
        child.stdin.close();rc=child.wait(timeout=20)
        if rc:raise RuntimeError(child.stderr.read().decode('utf-8')[:1000])
    except BaseException as exc:
        error={'type':type(exc).__name__,'message':str(exc)};child.kill();child.wait(timeout=10);raise
    finally:plt.close(fig)
    files=list(dict.fromkeys([*g['files'],*robotfiles,URDF,A/'f3_model_replay_v1/kinematics_cpu.py',Path(__file__),FFMPEG]))
    receipt=seal({'schema_version':'diagnostic_trace_reconstruction_video_v1','family':family,'video_path':str(video),'video_sha256':sha(video),
      'width':1920,'height':1080,'fps':fps,'frames':len(indices),'source_state_rows':n,'source_frequency_hz':250,'source_duration_seconds':duration,
      'three_views':['diagnostic_overview','diagnostic_close_up','diagnostic_side'],'actual_camera_RGB':False,'measured_trace_reconstruction':True,
      'new_rollout':False,'GPU_used':False,'simulator_scene_created':False,'unexecuted_goals_drawn':False,'failure_label':g['failure'],
      'robot_display_geometry':'URDF_collision_mesh_convex_envelopes','object_world_display_geometry':'saved_native_meshes_at_measured_poses',
      'source_files':{str(p):sha(p) for p in files},'sampled_source_row_indices':selected,'final_hold_frames':fps*2,'elapsed_seconds':time.monotonic()-began,
      'not_accepted_trajectory_or_scientific_evidence':True,'error':error})
    write_new(CODE/(family+'_VIDEO_RECEIPT_001.json'),receipt);print(family,'VIDEO_DONE',round(receipt['elapsed_seconds'],2),str(video),flush=True)
    return receipt
if __name__=='__main__':render(sys.argv[1])
