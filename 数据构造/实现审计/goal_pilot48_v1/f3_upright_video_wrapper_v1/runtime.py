"""Live existing-head MP4 wrapper; no physics, camera configuration or cap changes."""
import sys,types,hashlib
from pathlib import Path
from goal_pilot48_v1.f3_upright_qualification_runtime_v1 import runtime as base
from realization_utf8_io_v1 import write_new
from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
class VideoContext:
    def __init__(self,inner,path):self.inner=inner;self.path=Path(path)
    @property
    def cleanup_receipt(self):return self.inner.cleanup_receipt
    def __enter__(self):
        handle=self.inner.__enter__()
        try:
            started=handle.scene.start_development_video_capture(self.path)
            if started.get('started') is not True:raise RuntimeError('existing-head video did not start')
            write_new(self.path.parent/'capture_start.json',{**started,'coverage':'after canonical60 settle; initial frame and subsequent dense trace steps','settle_frames_recorded':False,'reconstruction':False})
        except BaseException:
            self.inner.__exit__(*sys.exc_info());raise
        return handle
    def __exit__(self,*args):return self.inner.__exit__(*args)
def run(manifest,*,meter):
    if manifest.get('video_capture_required') is not True:raise ValueError('explicit required-video manifest field absent')
    out=Path(manifest['jobs'][0]['output_namespace']);path=out/'video/upright_qualification.mp4'
    def make(spec,directory,counts):
        adapter,inner=base.make(spec,directory,counts);return adapter,VideoContext(inner,path)
    env=dict(base.__dict__);env['make']=make
    result=types.FunctionType(base.run.__code__,env)(manifest,meter=meter)
    receipt=(result.get('cleanup') or {}).get('development_video_receipt');validation=None;error=None
    try:
        validation=validate_development_trajectory_mp4_receipt_v1(receipt,expected_path=path)
        if not validation['pass']:raise ValueError('required live MP4 integrity/endpoints failed')
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc)}
    video_ok=error is None
    value={**result,'schema_version':'f3_upright_first_qualification_live_video_v1','physical_qualification_pass':result.get('qualified') is True,
        'base_qualification_terminal_sha256':hashlib.sha256((out/'qualification_terminal.json').read_bytes()).hexdigest(),
        'development_video_receipt':receipt,'video_validation':validation,'video_error':error,'video_required':True,
        'video_reconstruction':False,'video_covers_canonical_settle':False,'robot_action_scenes_observed':result.get('action_scenes_observed',0),
        'pass':result.get('pass') is True and video_ok,'qualified':result.get('qualified') is True and video_ok,
        'micro_pass':result.get('micro_pass') is True and video_ok,'scientific_route_pass':result.get('scientific_route_pass') is True and video_ok}
    value.pop('receipt_sha256',None);value['receipt_sha256']=base.hash_value(value);write_new(out/'video_qualification_terminal.json',value);return value
