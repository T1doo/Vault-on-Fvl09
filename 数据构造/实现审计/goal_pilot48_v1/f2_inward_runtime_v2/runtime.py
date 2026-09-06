"""Private module globals preserve the GPU-verified v1 mechanics unchanged."""
import hashlib
import importlib.util
from pathlib import Path
from .contract import A, build_contract, manifest_lineage

PARENT = A / 'goal_pilot48_v1/f2_inward_runtime_v1/runtime.py'
PARENT_SHA = 'b660f4145c767fa13509a1a7a134caf0f125e52c1fa7701c4227a638bb801654'

def load_private_runtime(manifest):
    if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA:
        raise ValueError('GPU-verified parent mechanics changed')
    # Do not register this module in sys.modules. Relative imports point to
    # immutable v1 helpers, but every function owns this private globals dict.
    spec = importlib.util.spec_from_file_location('goal_pilot48_v1.f2_inward_runtime_v1._revision1_private_runtime', PARENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def bound_contract():
        c = build_contract()
        expected = manifest_lineage(c)
        if any(manifest.get(k) != v for k, v in expected.items()):
            raise ValueError('manifest does not bind exact revision1 lineage')
        from realization_utf8_io_v1 import write_new
        output = Path(manifest['jobs'][0]['output_namespace'])
        write_new(output / 'runtime_revision1_lineage.json', {'schema_version': 'f2_private_runtime_revision1_lineage_v2',
                  'lineage': expected, 'planned': c['planned'], 'binding': c['binding'], 'goals': c['inward_goals'],
                  'mechanics_source_path': str(PARENT), 'mechanics_source_sha256': PARENT_SHA,
                  'shared_import_globals_modified': False, 'GPU_revision1_qualification_pending_at_entry': True})
        return c
    module.build_contract = bound_contract
    return module

def run(manifest):
    return load_private_runtime(manifest).run(manifest)
