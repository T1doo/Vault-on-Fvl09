"""Complete project runtime byte pin checked before native imports and after jobs."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
LIVE=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin')
WORKSPACE=Path('/nfs_share/lijunhui')


def runtime_paths():
    paths=set(p for p in HERE.glob('*.py') if not p.name.startswith('test_'))
    for root in (LIVE/'controlled_multi_future',LIVE/'envs'):
        paths.update(root.rglob('*.py'))
    for p in paths:
        if not p.resolve().is_relative_to(WORKSPACE) or any(q.is_symlink() for q in [p,*p.parents] if q.is_relative_to(WORKSPACE)):
            raise ValueError('source pin path leaves workspace or follows symlink')
    return paths


def inventory():
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(runtime_paths())}


def bundle_hash(files):
    return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def validate(authorization):
    supplied=authorization.get('source_files')
    if not isinstance(supplied,dict) or set(supplied)!={str(p) for p in runtime_paths()}:
        raise ValueError('authorization must pin all new runtime, live cmf and envs Python files')
    if authorization.get('source_bundle_sha256')!=bundle_hash(supplied):
        raise ValueError('source bundle hash mismatch')
    for path,sha in supplied.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha:
            raise ValueError('frozen source changed: '+path)
    return True
