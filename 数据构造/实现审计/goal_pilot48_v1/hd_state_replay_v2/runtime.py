"""Display-only raster shader for new HD clones; saved state/cameras unchanged."""
import types
from pathlib import Path
from goal_pilot48_v1.hd_state_replay_v1 import runtime as original
from goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.recorder import Recorder
from realization_utf8_io_v1 import write_new

class RasterRecorder(Recorder):
    def __init__(self,*args,**kwargs):
        import sapien
        # Only cameras subsequently created by this display recorder use this
        # shader. Existing observation cameras and physics are not replaced.
        sapien.render.set_camera_shader_dir('default')
        super().__init__(*args,**kwargs)

def run(manifest,*,meter):
    if manifest.get('display_shader')!='default_native_raster':
        raise ValueError('explicit display-shader declaration required')
    env=dict(original.__dict__);env['OriginalRecorder']=RasterRecorder
    result=types.FunctionType(original.run.__code__,env)(manifest,meter=meter)
    result.pop('receipt_sha256',None)
    result.update(schema_version='cmf_native_HD_saved_state_raster_render_v2',
                  display_shader='default_native_raster',
                  raytraced_original_pixels_reproduced=False,
                  native_resolution_and_camera_intrinsics_unchanged=True)
    import hashlib,json
    result['receipt_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
    write_new(Path(manifest['jobs'][0]['output_namespace'])/'raster_render_terminal.json',result)
    return result
