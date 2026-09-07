"""Private ModuleType binding of the immutable V1.3 realization pipeline."""
import ast
from copy import deepcopy
import hashlib
import importlib
from pathlib import Path
from types import ModuleType
from ..f4_b_root_runtime_v1.entry import private_functions
from ..f4_b_runtime_v1.adapter import make_adapter as B_adapter
from ..f4_b_runtime_v1.binding import seal
from ..runtime.issue_f4_b_stage_a import sha,read,A,W,digest
from realization_utf8_io_v1 import write_new

PIPE=A/'realization_batch_runtime_v1_3/pipeline.py'
RETIME=A/'realization_batch_runtime_v1_3/retiming.py'
PIPE_SHA='c02e55f4f9436d7f5920b0b4eef9a8f684069b2d0c628e496d3a0d3acc016a34'
RETIME_SHA='b5b2601701bb689ba31454df04530c5854de1a379885d3ed7dc854fe97e52adb'

def build_pipeline(bound,source_sha):
    if sha(PIPE)!=PIPE_SHA or sha(RETIME)!=RETIME_SHA:raise ValueError('frozen realization source changed')
    def source_branch(cell):
        if sha(cell['source_branch'])!=cell['source_branch_file_sha256']:raise ValueError('B parent branch changed')
        return read(cell['source_branch'])
    def make_adapter(cell,output):
        if cell['family']!='F4' or cell['variant']!='r_inv_motion':raise ValueError('only F4-B motion, no path/F1/F4-A')
        parent=Path(cell['parent_root']).resolve()
        if cell['parent_root_id']!=bound['planned_spec']['slot_id'] or not parent.parent.name.startswith('p48_f4_b_root_'):
            raise ValueError('motion factory cannot substitute historical F4-A parent')
        if not Path(cell['source_suffix']).resolve().is_relative_to(parent) or not Path(cell['source_branch']).resolve().is_relative_to(parent):
            raise ValueError('motion controls/branch are not inside the same B root')
        return B_adapter(output_root=output,source_sha256=source_sha,planned_spec=bound['planned_spec'],full_program_specs=bound['full_program_specs'])
    retime=ModuleType('cmf_B_motion_private_retime')
    retime.__dict__.update(seal=seal)
    tree=ast.parse(RETIME.read_text(encoding='utf-8'));tree.body=[n for n in tree.body if not(isinstance(n,ast.ImportFrom) and n.module=='catalog')]
    exec(compile(tree,str(RETIME)+'#B-private','exec'),retime.__dict__)
    module=ModuleType('cmf_B_motion_private_pipeline')
    module.__dict__.update(W=W,A=A,SOURCE_SHA=source_sha,read=read,sha=sha,canonical=digest,seal=seal,make_adapter=make_adapter,source_branch=source_branch,retime=retime.retime)
    for name,entry in [('raw_writer','write_raw_attempt'),('frozen_suffix_artifact_v1','write_frozen_suffix_artifact')]:
        mod=importlib.import_module('controlled_multi_future.'+name)
        module.__dict__[entry]=private_functions(mod,{'canonical_write_json':lambda p,v,**kw:write_new(p,v)})[entry]
    class Rewrite(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            if node.module in ('catalog','retiming'):return None
            if node.module in ('controlled_multi_future.raw_writer','controlled_multi_future.frozen_suffix_artifact_v1'):
                node.names=[n for n in node.names if n.name not in ('write_raw_attempt','write_frozen_suffix_artifact')]
                if not node.names:return None
            return node
    tree=ast.fix_missing_locations(Rewrite().visit(ast.parse(PIPE.read_text(encoding='utf-8'))))
    exec(compile(tree,str(PIPE)+'#B-private','exec'),module.__dict__)
    if module.collect_cell.__globals__ is not module.__dict__:raise ValueError('collector instance-hook globals disconnected')
    return module
