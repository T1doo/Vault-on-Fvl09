"""Pure versioned native-HD display renderer issuance; no budget writes."""
from .issue_hd_state_render import build_manifest as original,ROOT,W,CAPS,sha,digest
from pathlib import Path

def build_manifest(job_id,reservation,item):
    m=original(job_id,reservation,item);m.pop('manifest_sha256')
    folder=ROOT/'hd_state_replay_v2'
    for path in [*folder.glob('*.py'),Path(__file__).resolve()]:
        m['source_files'][str(path)]=sha(path)
    shader=W/'Robotwin2/env/lib/python3.10/site-packages/sapien/vulkan_shader/default'
    files=[p for p in shader.rglob('*') if p.is_file()]
    if not files:raise ValueError('installed default raster shader absent')
    for path in files:
        if not path.resolve().is_relative_to(W):raise ValueError('shader outside workspace')
        m['input_files'][str(path)]=sha(path)
    m.update(display_shader='default_native_raster',original_raytraced_pixels_claimed=False,
             primary_state_camera_and_resolution_changed=False)
    m['jobs'][0].update(runtime_module='goal_pilot48_v1.hd_state_replay_v2.runtime',
                       runtime_file=str(folder/'runtime.py'),test_module='goal_pilot48_v1.hd_state_replay_v2.test_all')
    m['manifest_sha256']=digest(m);return m
