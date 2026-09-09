import importlib.util,json,sys,time
from pathlib import Path
package=Path(sys.argv[1]).resolve()
# Audit hook fails any attempt to read raw source or active/vault implementation.
blocked=['/nfs_share/lijunhui/Robotwin2/datasets/','/nfs_share/lijunhui/Robotwin2/project/','/nfs_share/lijunhui/Vault-on-Fvl09/']
def guard(event,args):
    if event=='open' and isinstance(args[0],(str,bytes)):
        p=str(Path(args[0]).absolute())
        if any(p.startswith(x) for x in blocked):raise PermissionError('original source fallback forbidden')
sys.addaudithook(guard)
spec=importlib.util.spec_from_file_location('portable_reader',package/'reader.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
t=time.monotonic();x=m.read(package)
assert set(x['inputs'])=={'rgb','state','future','candidate_set'}
assert x['inputs']['state'].shape==(76,)
print(json.dumps({'pass':True,'source_fallback_explicitly_denied':blocked,'package':str(package),'future_shape':list(x['inputs']['future'].shape),'rgb_shapes':{k:list(v.shape) for k,v in x['inputs']['rgb'].items()},'candidate_count':len(x['inputs']['candidate_set']),'elapsed_seconds':time.monotonic()-t}))
