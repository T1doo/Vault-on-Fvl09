import json,hashlib,sys,unittest
from pathlib import Path
import numpy as np
from .geometry import Geometry,A
from . import test_cpu
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
O=Path(__file__).parent
def main():
    s=json.loads((O/'design_spec.json').read_text(encoding='utf-8'));g=Geometry();pre=np.array(s['nominal_pregrasp_world_pose']);goal=np.array(s['nominal_grasp_world_pose']);rows=[]
    for fraction in np.linspace(0,1,13):
        p=pre.copy();p[:3]=(1-fraction)*pre[:3]+fraction*goal[:3]
        rows.append({'fraction':float(fraction),'hand_bottle_hits':g.pairs(p,.045),'hand_support_hits':g.support_clear(p,.045)})
    if any(r['hand_bottle_hits'] or r['hand_support_hits'] for r in rows):raise ValueError('selected B open-hand nominal approach blocked')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_cpu))
    if not result.wasSuccessful():raise ValueError('CPU interface tests failed')
    paths=[*O.glob('*.py'),O/'design_spec.json',O/'candidate_geometry_audit.json',O/'initial_arm_audit.json']
    value={'schema_version':'f3_upright_B_selected_CPU_audit_v1','pass':True,'selected_design':'B_upper_straight_body','design_receipt':s['receipt_sha256'],
        'source_bindings':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'open_hand_approach_samples':rows,'CPU_tests_passed':result.testsRun,
        'known_initial_arm_nonadjacent_pairs_checked':106,'target_full_arm_IK_or_path_verified':False,'physical_standing_verified':False,
        'new_GPU':False,'new_scene_or_physical_attempts':0,'job_manifest_or_reservation_created':False,
        'execution_ready':False,'scope':'unique geometry/seed/pose choice and CPU scene/qualification interfaces; live ports still require implementation and preflight'}
    value['receipt_sha256']=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest();write_new(O/'CPU_AUDIT.json',value);print(value['receipt_sha256'])
if __name__=='__main__':main()
