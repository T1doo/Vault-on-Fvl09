"""HD multiview render-only wrapper around immutable first qualification."""
import types,sys,hashlib
from pathlib import Path
from goal_pilot48_v1.f3_upright_qualification_runtime_v1 import runtime as base
from realization_utf8_io_v1 import write_new
from .recorder import Recorder
class Context:
    def __init__(self,inner,out):self.inner=inner;self.out=Path(out)
    @property
    def cleanup_receipt(self):return self.inner.cleanup_receipt
    def __enter__(self):
        handle=self.inner.__enter__();scene=handle.scene;recorder=None
        try:
            if hasattr(scene,'_cmf_stage0_video_recorder') or hasattr(scene,'_cmf_development_video_recorder'):raise ValueError('another recorder already active')
            recorder=Recorder(scene,self.out/'video_hd');recorder.capture(scene,step_index=0,force=True)
            scene._cmf_development_video_recorder=recorder;scene._cmf_development_video_receipt=None
        except BaseException as primary:
            info=sys.exc_info();errors=[]
            try:
                if recorder is not None and not recorder.closed:recorder.abort(scene)
            except BaseException as cleanup:errors.append({'phase':'recorder_abort','type':type(cleanup).__name__,'message':str(cleanup)})
            finally:
                try:self.inner.__exit__(*info)
                except BaseException as cleanup:errors.append({'phase':'inner_scene_exit','type':type(cleanup).__name__,'message':str(cleanup)})
            try:write_new(self.out/'HD_start_failure.json',{'primary':{'type':type(primary).__name__,'message':str(primary)},'cleanup_errors':errors,'inner_exit_attempted':True})
            except BaseException:pass  # Preserve the original error even if audit storage fails.
            raise
        return handle
    def __exit__(self,*args):return self.inner.__exit__(*args)
def validate(receipt):
    if not isinstance(receipt,dict) or receipt.get('schema_version')!='cmf_live_native_HD_multiview_v2' or not receipt.get('pages'):return False
    if not receipt.get('includes_initial_frame') or not receipt.get('includes_final_frame') or receipt.get('RGB_upscaled') is not False:return False
    labels=[v['label'] for v in receipt['views']];page_labels=[l for p in receipt['pages'] for l in p['labels']]
    if sorted(labels)!=sorted(page_labels) or not {'head','left_wrist','right_wrist'}.issubset(labels):return False
    if not all(Path(p['path']).is_file() and hashlib.sha256(Path(p['path']).read_bytes()).hexdigest()==p['file_sha256'] and p['frame_count']>=1 for p in receipt['pages']):return False
    import imageio.v2 as imageio
    try:
        for page in receipt['pages']:
            reader=imageio.get_reader(page['path'],format='FFMPEG')
            try:
                frame=reader.get_data(0)
                if frame.shape!=(1440,2880,3):return False
            finally:reader.close()
    except BaseException:return False
    return True
def run(manifest,*,meter):
    if manifest.get('video_capture_required') is not True or manifest.get('video_mode')!='native_HD_all_existing_views_v2':raise ValueError('exact HD multiview requirement missing')
    out=Path(manifest['jobs'][0]['output_namespace'])
    def make(spec,directory,counts):
        adapter,inner=base.make(spec,directory,counts);return adapter,Context(inner,out)
    env=dict(base.__dict__);env['make']=make;result=types.FunctionType(base.run.__code__,env)(manifest,meter=meter)
    receipt=(result.get('cleanup') or {}).get('development_video_receipt');ok=validate(receipt)
    value={**result,'schema_version':'f3_upright_first_qualification_HD_multiview_v2','physical_qualification_pass':result.get('qualified') is True,
        'base_terminal_sha256':hashlib.sha256((out/'qualification_terminal.json').read_bytes()).hexdigest(),'HD_video_receipt':receipt,'HD_video_pass':ok,
        'video_capture_required':True,'pass':result.get('pass') is True and ok,'qualified':result.get('qualified') is True and ok,'micro_pass':result.get('micro_pass') is True and ok,'scientific_route_pass':result.get('scientific_route_pass') is True and ok,
        'physical_actions_Gates_caps_model_cameras_unchanged':True,'new_camera_type':'audit-only native-resolution independently rendered clones'}
    value.pop('receipt_sha256',None);value['receipt_sha256']=base.hash_value(value);write_new(out/'HD_video_qualification_terminal.json',value);return value
