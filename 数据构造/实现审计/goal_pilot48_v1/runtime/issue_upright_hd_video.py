"""Pure HD display wrapper binding; does not cancel/reserve/launch jobs."""
from pathlib import Path
from .issue_upright_qualification import build_manifest as first, ROOT, W, CAPS, sha, checked, digest

PRIOR = ROOT/'jobs/p48_f3_upright_qualification_001.json'

def build_manifest(job_id, reservation):
    m = first(job_id, reservation)
    m.pop('manifest_sha256')
    prior = checked(PRIOR, 'manifest_sha256')
    old_job = prior['jobs'][0]
    if any(p.exists() for p in (Path(old_job['output_namespace']), Path(prior['guard_directory']),
                                W/'Robotwin2/cache/p48'/old_job['job_id'],
                                W/'Robotwin2/datasets'/(old_job['job_id']+'_meter'))):
        raise ValueError('prior qualification may have launched; no unlaunched replacement')
    folder = ROOT/'f3_upright_hd_video_wrapper_v2'
    for required in ('runtime.py', 'test_all.py'):
        if not (folder/required).is_file():
            raise ValueError('HD video runtime not delivered')
    for path in folder.glob('*.py'):
        m['source_files'][str(path)] = sha(path)
    m['source_files'][str(Path(__file__).resolve())] = sha(Path(__file__))
    preflight = ROOT/'runtime/test_upright_hd_preflight.py'
    m['source_files'][str(preflight)] = sha(preflight)
    for path in (PRIOR, W/'Robotwin2/project/RoboTwin/envs/camera/camera.py'):
        m['input_files'][str(path)] = sha(path)
    for relative in ('sapien/pysapien/render.pyi', 'sapien/wrapper/scene.py',
                     'matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf'):
        path = W/'Robotwin2/env/lib/python3.10/site-packages'/relative
        m['input_files'][str(path)] = sha(path)
    m.update(video_capture_required=True, video_mode='native_HD_all_existing_views_v2', video_native_pane_resolution=[960,720],
             prior_issued_unlaunched_job=old_job['job_id'],
             prior_manifest_sha256=prior['manifest_sha256'],
             model_visible_camera_configuration_changed=False,
             display_only_camera_rendering=True)
    m['jobs'][0].update(runtime_module='goal_pilot48_v1.f3_upright_hd_video_wrapper_v2.runtime',
                       runtime_file=str(folder/'runtime.py'),
                       test_module='goal_pilot48_v1.runtime.test_upright_hd_preflight')
    m['manifest_sha256'] = digest(m)
    return m
