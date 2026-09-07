"""CPU rendering retry3: compact exact triangles, explicit PIPE and process audit."""
import os,sys,time,types,subprocess
from pathlib import Path
import numpy as np
from . import render as old
from realization_utf8_io_v1 import write_new
CODE=Path(__file__).parent/'attempt3';OUT=old.W/'Robotwin2/datasets/diagnostic_video_reconstruction_v3'
def render(family):
    began=time.monotonic();children=[];optimization=[]
    def meshes():
        items,files=old.robot_meshes()
        for m in items:
            ov=m['vertices'];of=m['faces'];used,inverse=np.unique(of.reshape(-1),return_inverse=True);v=ov[used];faces=inverse.reshape(of.shape)
            if not np.array_equal(ov[of],v[faces]):raise ValueError('drawing triangles changed')
            optimization.append({'link':m['link'],'original_vertices':len(ov),'used_vertices':len(v),'triangles_unchanged':True})
            m['vertices']=v;m['faces']=faces
        return items,files
    def geometry(family):
        g=old.geometry(family);g['files'] += [Path(__file__),CODE/(family+'_PROCESS_START_003.json')];return g
    def popen(*args,**kwargs):
        c=subprocess.Popen(*args,**kwargs);children.append(c)
        write_new(CODE/(family+'_PROCESS_START_003.json'),old.seal({'family':family,'python_pid':os.getpid(),'ffmpeg_pid':c.pid,
          'monotonic_start':began,'CPU_only':True,'output_namespace':str(OUT),'mesh_optimization':optimization,
          'OPENBLAS_NUM_THREADS':os.environ.get('OPENBLAS_NUM_THREADS'),'OMP_NUM_THREADS':os.environ.get('OMP_NUM_THREADS')}))
        print(family,'CPU_RENDER_START python',os.getpid(),'ffmpeg',c.pid,flush=True);return c
    ns=dict(old.render.__globals__);ns.update(OUT=OUT,CODE=CODE,robot_meshes=meshes,geometry=geometry,subprocess=types.SimpleNamespace(Popen=popen,PIPE=subprocess.PIPE))
    fn=types.FunctionType(old.render.__code__,ns,old.render.__name__,old.render.__defaults__,old.render.__closure__)
    try:
        result=fn(family)
        write_new(CODE/(family+'_CPU_COMPLETION_003.json'),old.seal({'family':family,'pass':True,'video_receipt_sha256':result['receipt_sha256'],
          'owned_ffmpeg_pid':children[0].pid,'owned_ffmpeg_reaped':children[0].poll() is not None,'elapsed_seconds':time.monotonic()-began,
          'new_rollout':False,'GPU_used':False,'three_diagnostic_views_not_six_real_cameras':True}))
    except BaseException as exc:
        for c in children:
            if c.poll() is None:c.kill()
            c.wait(timeout=10)
        write_new(CODE/(family+'_CPU_FAILURE_003.json'),old.seal({'family':family,'pass':False,'error':{'type':type(exc).__name__,'message':str(exc)},
          'owned_ffmpeg_pids':[c.pid for c in children],'all_owned_ffmpeg_reaped':all(c.poll() is not None for c in children),'elapsed_seconds':time.monotonic()-began}))
        raise
if __name__=='__main__':render(sys.argv[1])
