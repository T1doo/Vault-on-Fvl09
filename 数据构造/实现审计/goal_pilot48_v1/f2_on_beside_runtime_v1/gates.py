"""Execute the unchanged original on/beside held and final statements.

No copied numerical thresholds, private global changes, or inside acceptance.
Extraction is anchored on exact AST assignments and fails closed on drift.
"""
import ast
from pathlib import Path
from goal_pilot48_v1.f2_inward_runtime_v3.contract import P

SOURCE=P/'controlled_multi_future/family_runners_v3_3.py'

def original_blocks():
    from controlled_multi_future import family_runners_v3_3 as original
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='F2ControllerV3_3')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='execute_frozen_suffix_spec')
    def assignment(name):
        matches=[i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
        if len(matches)!=1:raise ValueError('original verifier AST drift: '+name)
        return matches[0]
    held=fn.body[assignment('held_transport_rows'):assignment('transport_contact_gate')+1]
    final=fn.body[assignment('can_pose'):assignment('checks')+1]
    return dict(original.__dict__),held,final

def held(scene,spec,start,windows):
    ns,nodes,_=original_blocks();ns.update(scene=scene,spec=spec,held_transport_start_row=start,held_segment_trace_windows=windows,release_index=1)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE)+':original_held_subset','exec'),ns)
    return ns['transport_contact_gate']

def final(scene,spec,transport):
    if spec['relation'] not in ('on','beside'):raise ValueError('inside Gate excluded')
    ns,_,nodes=original_blocks();ns.update(scene=scene,spec=spec,transport_contact_gate=transport)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE)+':original_final_subset','exec'),ns)
    checks=ns['checks']
    return {'pass':all(checks.values()),'checks':checks,'exclusive_relations':ns['exclusive'],
      'on_scale_full_obb_footprint':ns['on_footprint'],'on_scale_bottom_height_error_m':ns['on_bottom_height_error'],
      'final_can_actor_origin_pose':ns['can_pose'].tolist(),'original_verifier_statements_unchanged':True}
