"""Single measured frame only; no video/encoder until parent visual review."""
import ast,copy,time
from pathlib import Path
import numpy as np
import cv2
from . import render_v4 as source
from .zbuffer import panel
from realization_utf8_io_v1 import write_new
OUT=source.old.W/'Robotwin2/datasets/diagnostic_video_reconstruction_v5';CODE=Path(__file__).parent/'attempt5'

def context(family):
    tree=ast.parse(Path(source.__file__).read_text(encoding='utf-8'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render')
    start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets))
    setup=copy.deepcopy(fn);setup.body=setup.body[:start]+[ast.parse('return locals()').body[0]]
    ns=dict(source.__dict__);ns.update(OUT=OUT,CODE=CODE,panel=panel)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[setup],type_ignores=[])),str(source.__file__)+':CPU_singleframe_setup','exec'),ns)
    result=ns['render'](family);ns.update(result)
    if family=='F3':
        local=np.concatenate([m['vertices']@m['T'][:3,:3].T+m['T'][:3,3] for m in ns['parts']])
        center=(local.min(0)+local.max(0))/2;T=source.old.matrix(ns['arrays']['object_pose'][-1])
        ns['g']['focus']=T[:3,:3]@center+T[:3,3]
    loop=next(n for n in ast.walk(fn) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and any(isinstance(v,ast.Name) and v.id=='fi' for v in n.target.elts))
    end=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='write')
    ns['frame_code']=compile(ast.Module(body=loop.body[:end],type_ignores=[]),str(source.__file__)+':same_measurements_zbuffer','exec')
    return ns
def frame(ns,index):
    ns['index']=index;ns['fi']=0;exec(ns['frame_code'],ns);return ns['frame']
def preview(family):
    began=time.monotonic();ns=context(family);index=ns['n']-1;value=frame(ns,index)
    path=OUT/(family+'_final_frame_zbuffer_1080p.png')
    if path.exists():raise FileExistsError(path)
    cv2.imwrite(str(path),value)
    receipt=source.old.seal({'family':family,'single_frame_only':True,'source_row':index,'width':1920,'height':1080,
      'view_types':['diagnostic_overview','diagnostic_close_up','diagnostic_side'],'not_original_cameras':True,'GPU_used':False,'new_rollout':False,
      'occlusion':'per_pixel_barycentric_depth_buffer','near_view_focus_world':ns['g']['focus'].tolist(),
      'output_path':str(path),'output_sha256':source.old.sha(path),'elapsed_seconds':time.monotonic()-began,
      'sources':{str(p):source.old.sha(p) for p in (Path(__file__),Path(source.__file__),Path(__file__).with_name('zbuffer.py'),ns['g']['trace'])}})
    write_new(CODE/(family+'_PREVIEW_005.json'),receipt);print(family,'SINGLE_FRAME_DONE',round(receipt['elapsed_seconds'],3),str(path),flush=True)
if __name__=='__main__':
    import sys
    preview(sys.argv[1])
