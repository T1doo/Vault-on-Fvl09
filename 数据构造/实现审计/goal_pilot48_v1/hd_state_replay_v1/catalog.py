import ast
import json
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
W=Path('/nfs_share/lijunhui')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify_f1_scene_source():
    live=W/'Robotwin2/project/RoboTwin/controlled_multi_future/probes/scene_inspection.py'
    old=W/'Robotwin2/tmp/cmf_f1_parent_317387b/数据构造/实现审计/代码审阅快照/controlled_multi_future/probes/scene_inspection.py'
    trees=[ast.parse(p.read_text(encoding='utf-8')) for p in (live,old)]
    for name in ('F1Scene','AuditScene','_args'):
        nodes=[next(n for n in tree.body if getattr(n,'name',None)==name) for tree in trees]
        if ast.dump(nodes[0])!=ast.dump(nodes[1]):raise ValueError('F1 display scene construction changed')
    return {str(p):sha(p) for p in (live,old)}

def catalog():
    document=json.loads((ROOT/'pilot_cells.json').read_text(encoding='utf-8'))
    cells=[c for c in document['cells'] if c['family'] in ('F1','F4') and c['status'] in ('accepted_existing','accepted_new')]
    roots={}
    for c in cells:
        if c['realization']=='r_pc':
            roots[(c['family'],c['pilot'])]=Path(c['evidence']['rollout_id']).parents[1]
    result=[]
    for c in cells:
        e=c['evidence'];trace=Path(e['rollout_id'])/'trace_source.npz';planned=roots[(c['family'],c['pilot'])]/'planned_root_slot_spec.json'
        if not trace.resolve().is_relative_to(W/'Robotwin2/datasets') or sha(trace)!=e['trace_sha256']:
            raise ValueError('accepted trace mismatch')
        result.append({'family':c['family'],'pilot':c['pilot'],'program_id':c['program_id'],'realization':c['realization'],
                       'label':'_'.join(c[k] for k in ('family','pilot','realization','program_id')),
                       'trace_path':str(trace),'trace_sha256':e['trace_sha256'],
                       'planned_spec_path':str(planned),'planned_spec_sha256':sha(planned),
                       'states':e['states'],'raw_id':e['raw_id'],'root_id':e['root_id'],
                       'display_only':True,'new_collection':False})
    return result
