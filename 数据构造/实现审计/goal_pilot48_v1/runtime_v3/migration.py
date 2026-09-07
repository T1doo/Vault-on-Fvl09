"""Read-only mapping; same Goal ledger, no reserve/publication."""
import hashlib
from pathlib import Path
from goal_pilot48_v1.runtime_v2.migration import bindings as v2_bindings
RUNTIME=Path(__file__).resolve().parent
ROOT=RUNTIME.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bindings(parent):
    value=v2_bindings(parent)
    for p in RUNTIME.glob('*.py'):value['source_files'][str(p)]=sha(p)
    for role,name in (('guard','guarded_launcher.py'),('runner','job_runner.py')):
        value[role+'_script_path']=str(RUNTIME/name);value[role+'_script_sha256']=sha(RUNTIME/name)
    return value
