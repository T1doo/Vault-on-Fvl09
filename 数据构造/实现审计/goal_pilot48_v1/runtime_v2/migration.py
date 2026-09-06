"""Read-only source/entry mapping for a future issuer, not a reservation."""
import hashlib
from pathlib import Path
RUNTIME=Path(__file__).resolve().parent
ROOT=RUNTIME.parent
W=Path('/nfs_share/lijunhui')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bindings(parent_manifest):
    sources=dict(parent_manifest['source_files']);inputs=dict(parent_manifest['input_files'])
    for table in (sources,inputs):
        for p,h in table.items():
            if not Path(p).resolve().is_relative_to(W) or sha(p)!=h:raise ValueError('changed parent dependency '+p)
    for folder in (RUNTIME,ROOT/'collection_meter_review_v1'):
        for p in folder.glob('*.py'):sources[str(p)]=sha(p)
    writer=ROOT.parent/'realization_utf8_io_v1.py'
    if str(writer) in sources and sources[str(writer)]!=sha(writer):raise ValueError('UTF8 helper changed from parent')
    sources[str(writer)]=sha(writer)
    entries={}
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        entries[role+'_script_path']=str(RUNTIME/name);entries[role+'_script_sha256']=sha(RUNTIME/name)
    return dict(source_files=sources,input_files=inputs,**entries)
