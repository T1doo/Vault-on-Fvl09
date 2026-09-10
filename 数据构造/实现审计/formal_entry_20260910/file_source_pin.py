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
    robot=LIVE/'assets/embodiments/aloha-agilex'
    paths.update(LIVE/'task_config'/name for name in ('demo_clean.yml','_embodiment_config.yml','_camera_config.yml'))
    paths.update(robot/name for name in ('config.yml','curobo_left.yml','curobo_right.yml','collision_aloha_left.yml','collision_aloha_right.yml','urdf/arx5_description_isaac.urdf','srdf/arx5_description_isaac.srdf'))
    import xml.etree.ElementTree as ET
    urdf=robot/'urdf/arx5_description_isaac.urdf'
    for mesh in ET.parse(urdf).getroot().iter('mesh'):
        name=mesh.attrib['filename']
        path=urdf.parent/name
        if not path.is_file():raise ValueError('robot mesh dependency missing: '+str(path))
        paths.add(path)
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


def native_implementation_hash():
    """Exact legacy adapter identity; distinct from complete source/config bundle."""
    digest=hashlib.sha256();root=LIVE/'controlled_multi_future'
    for path in sorted(root.rglob('*.py')):
        if not path.resolve().is_relative_to(WORKSPACE):raise ValueError('unsafe source')
        digest.update(path.relative_to(root).as_posix().encode('utf-8'));digest.update(b'\0')
        digest.update(path.read_bytes());digest.update(b'\0')
    return digest.hexdigest()
