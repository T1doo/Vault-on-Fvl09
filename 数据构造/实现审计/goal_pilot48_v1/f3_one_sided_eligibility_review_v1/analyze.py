"""Expose every current V1 certificate predicate without modifying V1 or data."""
import ast,inspect,copy,json,sys,hashlib
from pathlib import Path
import numpy as np
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent
D=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_tangent_micro_001')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from goal_pilot48_v1.f3_tangent_escape_v1 import certificate as old
from realization_utf8_io_v1 import write_new
def main():
    path=D/'tangent_certificate_candidate.json';c=json.loads(path.read_text(encoding='utf-8'));tree=ast.parse(inspect.getsource(old.validate))
    class Explain(ast.NodeTransformer):
        changed=0
        def visit_Return(self,node):
            v=node.value
            if isinstance(v,ast.Call) and isinstance(v.func,ast.Name) and v.func.id=='bool' and isinstance(v.args[0],ast.BoolOp):
                self.changed+=1
                return ast.Return(value=ast.Dict(keys=[ast.Constant(ast.unparse(x)) for x in v.args[0].values],values=[ast.Call(func=ast.Name(id='bool',ctx=ast.Load()),args=[x],keywords=[]) for x in v.args[0].values]))
            return node
    x=Explain();tree=x.visit(tree);assert x.changed==1
    namespace=dict(old.__dict__);exec(compile(ast.fix_missing_locations(tree),str(Path(__file__)),'exec'),namespace);checks=namespace['validate'](c)
    if not isinstance(checks,dict):raise ValueError('failure before conjunction; inspect early identity/hash checks')
    gaps=np.asarray(c['native_gap_per_hold_frame_m']);steps=c['hold_step_indices'];bad=np.flatnonzero(gaps>.0001)
    value={'schema_version':'p48_f3_tangent_V1_predicate_failure_audit','old_V1_pass':old.validate(c),
        'predicates':checks,'failed_predicates':[k for k,v in checks.items() if not v],
        'source_certificate_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_validator_sha256':hashlib.sha256(Path(old.__file__).read_bytes()).hexdigest(),
        'certificate_receipt':c['certificate_sha256'],'native_gap_min_m':float(gaps.min()),'native_gap_max_m':float(gaps.max()),
        'positive_upper_bound_exceedances':[{'hold_index':int(i),'trace_step':steps[int(i)],'native_gap_m':float(gaps[i])} for i in bad],
        'negative_lower_bound_pass':bool((gaps>=-.0001).all()),'all_other_original_predicates_pass':all(v for k,v in checks.items() if k!='(np.abs(g) <= 0.0001).all()'),
        'old_supported_witness':c['old_supported_witness'],'full_model_checks':c['full_model_checks'],
        'current_model_eligibility_revision':1,'proposed_model_eligibility_revision':2,'stability_recipe_revision_unchanged':3,'route_revision_unchanged':2,
        'new_schema_not_implemented_or_executed':True,'original_files_modified':False,'GPU_executed':False}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
    write_new(O/'analysis.json',value);print(json.dumps({k:v for k,v in value.items() if k not in ('predicates','old_supported_witness','full_model_checks','positive_upper_bound_exceedances')}));print('upper_count',len(bad),'first',int(bad[0]),'last',int(bad[-1]))
if __name__=='__main__':main()
