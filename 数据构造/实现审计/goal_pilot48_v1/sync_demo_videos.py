"""Copy verified accepted pilot MP4s to the videos-only Vault directory."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VAULT = ROOT.parents[2]
DEST = VAULT/'数据构造/演示视频'
DATA = Path('/nfs_share/lijunhui/Robotwin2/datasets')
KINDS = {'r_pc':'01_标准轨迹', 'r_inv_path':'02_路径变化', 'r_inv_motion':'03_节奏变化'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sync():
    document = json.loads((ROOT/'pilot_cells.json').read_text(encoding='utf-8'))
    planned = []
    for cell in document['cells']:
        if cell['status'] not in ('accepted_existing', 'accepted_new'):
            continue
        evidence = cell['evidence']
        if evidence.get('video_integrity_pass') is not True:
            raise ValueError('video not verified')
        family, pilot, program = cell['family'], cell['pilot'], cell['program_id']
        if family not in ('F1','F2','F3','F4') or pilot not in ('A','B'):
            raise ValueError('unknown pilot identity')
        if Path(program).name != program or program in ('.','..'):
            raise ValueError('invalid program filename')
        source = (Path(evidence['rollout_id'])/'video/trajectory.mp4').resolve()
        if not source.is_relative_to(DATA) or sha(source) != evidence['video_sha256']:
            raise ValueError('source MP4 mismatch')
        destination = DEST/family/f'根组{pilot}'/KINDS[cell['realization']]/f'{program}.mp4'
        if destination.exists() and sha(destination) != evidence['video_sha256']:
            raise FileExistsError('different video already exists; never overwrite')
        planned.append((source,destination,evidence['video_sha256']))
    if len({str(d) for _,d,_ in planned}) != len(planned):
        raise ValueError('duplicate destination')
    copied = 0
    for source,destination,expected in planned:
        if not destination.exists():
            destination.parent.mkdir(parents=True,exist_ok=True)
            with source.open('rb') as src, destination.open('xb') as dst:
                shutil.copyfileobj(src,dst)
            copied += 1
        if sha(destination) != expected:
            raise ValueError('copied MP4 mismatch')
    if any(p.is_file() and p.suffix.lower() != '.mp4' for p in DEST.rglob('*')):
        raise ValueError('videos-only directory contains another file type')
    return {'copied':copied,'verified':len(planned),'bytes':sum(d.stat().st_size for _,d,_ in planned),'directory':str(DEST)}

if __name__ == '__main__':
    print(json.dumps(sync(),ensure_ascii=False))
