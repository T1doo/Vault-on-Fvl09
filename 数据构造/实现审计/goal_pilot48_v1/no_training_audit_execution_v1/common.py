import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(__file__).parent;W=Path('/nfs_share/lijunhui');A=ROOT.parent;P=W/'Robotwin2/project/RoboTwin'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def seal(v):return {**v,'receipt_sha256':digest(v)}
def write(p,v):
    from realization_utf8_io_v1 import write_new
    write_new(Path(p),v)
def checked(p):
    v=read(p);c=dict(v);h=c.pop('receipt_sha256')
    if digest(c)!=h:raise ValueError('receipt hash mismatch '+str(p))
    return v
