import unittest,json,hashlib,sys,textwrap,ast
from pathlib import Path
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from .test_all import MODULES
from realization_utf8_io_v1 import write_new
def main():
    source=A/'代码审阅快照/controlled_multi_future/family_runners_v3_3.py'
    s=source.read_text(encoding='utf-8');a=s.index('        post_lift = len(scene.trace) - 1 - start',s.index('f3_prefix_lift_8cm'));b=s.index('\n    def plan_suffix_from_actual_prefix_end_state',a)
    expected=ast.parse('def original_tail(scene,start,post_close,post_close_transform,qualified,frozen_grasp,target_construction_audit,prefix_planner_reset):\n'+textwrap.indent(textwrap.dedent(s[a:b]),'    '))
    actual=ast.parse((O/'locked_tail.py').read_text(encoding='utf-8'));actual.body=[x for x in actual.body if isinstance(x,ast.FunctionDef)]
    if ast.dump(actual,include_attributes=False)!=ast.dump(expected,include_attributes=False):raise ValueError('locked original post8cm tail changed')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(MODULES))
    if not result.wasSuccessful():raise ValueError('CPU tests failed')
    paths=list(O.glob('*.py'))+[source,*list((O.parent/'f3_runtime_v5').glob('*.py')),O.parent/'f3_native_self_pair_v1/checker.py']
    value={'schema_version':'p48_f3_prefix_extension_v3_CPU_audit','pass':True,'tests_run':result.testsRun,
        'original_post8cm_tail_AST_equal':True,'source_bindings':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'max_single_queries':14,'stages_query_counts':{'fresh_V5_micro':3,'15mm_and40mm_extension':2,'clearance_and_center':2,'shared_V':7},
        'first_fresh_micro_must_already_pass':True,'second_fresh_micro_and_full_restore_before_V':True,
        'early_boundary_poses_from_actual_rows':True,'new_GPU':False,'manifest_created':False,'budget_reserved':False,
        'actual_prefix_physical_pass':False,'formal_or_training_authorized':False}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();write_new(O/'CPU_AUDIT.json',value);print(value['receipt_sha256'])
if __name__=='__main__':main()
