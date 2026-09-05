import hashlib,json,os,uuid
from pathlib import Path

WORKSPACE=Path('/nfs_share/lijunhui')
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def seal(value):return {**value,'receipt_sha256':canonical(value)}
def load(path):
    d=json.loads(Path(path).read_text());v=dict(d);h=v.pop('receipt_sha256',None)
    if h!=canonical(v):raise ValueError('receipt hash mismatch')
    return d
def write_new(path,value):
    path=Path(path).resolve()
    if not path.is_relative_to(WORKSPACE):raise ValueError('outside workspace')
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.parent/(path.name+'.tmp.'+uuid.uuid4().hex)
    try:
        with temp.open('x') as f:
            json.dump(value,f,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
        os.link(temp,path)  # exclusive publication; never replace an old receipt
    finally:
        if temp.exists():temp.unlink()

def publish_identical_or_new(path,value,writer=write_new):
    path=Path(path)
    if path.exists():
        if json.loads(path.read_text())!=value:raise ValueError('immutable publication differs')
    else:writer(path,value)
