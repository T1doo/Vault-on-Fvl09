"""Original root entry with private UTF-8 writers and final receipt ordering."""
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import FunctionType,MethodType
from typing import Any,Mapping
from realization_utf8_io_v1 import write_new

A=Path(__file__).resolve().parents[2]
P=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin')

class RootWriter:
    def __init__(self,root):self.root=Path(root);self.pending={};self.ordinals={}
    def __call__(self,path,value,**kwargs):
        path=Path(path);value=deepcopy(value)
        if not path.resolve().is_relative_to(self.root.resolve()):raise ValueError('root writer path escaped namespace')
        if path.name=='receipt.json':
            n=self.ordinals.get(str(path),0);self.ordinals[str(path)]=n+1
            write_new(path.parent/'receipt_history'/f'{n:04d}.json',value);self.pending[path]=value;return
        if path==self.root/'root_receipt.json':
            for branch in value.get('branch_receipts',[]):
                self.pending[self.root/'branches'/branch['program_id']/'receipt.json']=deepcopy(branch)
            for target,payload in self.pending.items():write_new(target,payload)
            self.pending.clear()
        write_new(path,value)

def private_functions(module,overrides):
    ns=dict(vars(module));ns.update(overrides)
    for name,value in vars(module).items():
        if isinstance(value,FunctionType) and value.__module__==module.__name__:
            clone=FunctionType(value.__code__,ns,value.__name__,value.__defaults__,value.__closure__)
            clone.__kwdefaults__=value.__kwdefaults__;ns[name]=clone
    ns.update(overrides);return ns

def orchestrator(adapter,root,*,implementation_version):
    mod=importlib.import_module('controlled_multi_future.root_orchestrator_v1_2')
    writer=RootWriter(root)
    replacements={'canonical_write_json':writer,'_write_json':writer}
    for name,entry in [('canonical_prefix_artifact_v1','write_canonical_prefix_artifact'),
        ('frozen_suffix_artifact_v1','write_frozen_suffix_artifact'),('raw_writer','write_raw_attempt')]:
        m=importlib.import_module('controlled_multi_future.'+name)
        replacements[entry]=private_functions(m,{'canonical_write_json':writer})[entry]
    ns=private_functions(mod,replacements)
    original=mod.RealSapienStrictPrefixRootOrchestratorV1_2.run_nonformal_root
    run=FunctionType(original.__code__,ns,original.__name__,original.__defaults__,original.__closure__)
    run.__kwdefaults__=original.__kwdefaults__
    obj=mod.RealSapienStrictPrefixRootOrchestratorV1_2(adapter,implementation_version=implementation_version)
    obj.run_nonformal_root=MethodType(run,obj)
    return obj,writer

def disk_finalizer(result,job,output):
    """Extract only the unchanged disk-audit function closure, not old dispatcher."""
    path=A/'f4_development_root_runtime_v2_2/job_runner.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    names={'_canonical_jsonable','_read_mapping','_safe_raw_audit','_safe_video_audit','_phase_category',
        '_suffix_accounting','_minimal_failed_finalizer','finalize_f4_root_result'}
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(funcs)!=len(names):raise ValueError('frozen disk finalizer closure changed')
    from controlled_multi_future.canonical_artifact import canonical_hash_json
    ns=dict(Any=Any,Mapping=Mapping,Path=Path,Counter=Counter,json=json,
        canonical_hash=canonical_hash_json,file_sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),
        EXPECTED_PROGRAMS=['F4-ABC','F4-ACB','F4-BAC'])
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+funcs,type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(path)+'#private-disk-finalizer','exec'),ns)
    return ns['finalize_f4_root_result'](result,job,output=Path(output))
