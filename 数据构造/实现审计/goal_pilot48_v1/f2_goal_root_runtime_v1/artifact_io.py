"""Original prefix validator, exclusive NPZ and explicit UTF8 atomic JSON."""
import os
from pathlib import Path
import numpy as np

def write_prefix_artifact(output_dir,manifest,arrays):
    from controlled_multi_future.canonical_prefix_artifact_v1 import validate_canonical_prefix_artifact,file_sha256,load_canonical_prefix_artifact
    from realization_utf8_io_v1 import write_new
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=False)
    validated,normalized=validate_canonical_prefix_artifact(manifest,arrays)
    path=out/'prefix_arrays.npz'
    with path.open('xb') as f:
        np.savez_compressed(f,**normalized);f.flush();os.fsync(f.fileno())
    complete=dict(validated);complete['prefix_arrays_npz_sha256']=file_sha256(path)
    write_new(out/'canonical_prefix_artifact.json',complete)
    loaded,_=load_canonical_prefix_artifact(out)
    if loaded!=complete:raise ValueError('prefix artifact disk roundtrip mismatch')
    return complete
