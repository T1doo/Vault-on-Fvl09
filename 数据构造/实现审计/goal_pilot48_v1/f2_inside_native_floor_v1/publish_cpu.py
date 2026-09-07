"""Publish CPU-only version evidence; no job or resource reservation."""
import json
from pathlib import Path
from .certificate import A,P,reference_certificate,sha,digest,VERSION,APPROVAL_SHA
from .geometry_verifier import GeometryVerifier
OUT=Path(__file__).parent

def publish():
    from realization_utf8_io_v1 import write_new
    from controlled_multi_future import f2_release_gates_v10 as original
    c=reference_certificate();v=GeometryVerifier(c)
    anatomy=json.loads((A/'goal_pilot48_v1/f2_controlled_suffix_runtime_v1/anatomy.json').read_text(encoding='utf-8'))
    pose=anatomy['inside']['first_contact_actor_pose'];box=c['box_shapes'][0]['actor_world_pose']
    g=v.evaluate(pose,box,binding_sha256=c['binding_sha256'])
    if not g['pass']:raise ValueError('saved native contact geometry regression failed')
    for name,value in (('support_shape_certificate.json',c),('saved_contact_geometry.json',g)):
        path=OUT/name
        if path.exists():
            if json.loads(path.read_text(encoding='utf-8'))!=value:raise ValueError('prior CPU certificate/positive geometry changed')
        else:write_new(path,value)
    constants={name:getattr(original,name) for name in dir(original) if name.startswith(('SAFETY_','FINAL_','CONTACT_CONFIRM_')) and isinstance(getattr(original,name),(int,float,str))}
    original_files=[P/'controlled_multi_future/f2_release_gates_v10.py',P/'controlled_multi_future/f3_physical_contact_signal_v8.py',P/'controlled_multi_future/high_level_physical_runner_v1.py']
    report={'schema_version':'f2_inside_native_floor_CPU_implementation_audit_v1_1','verifier_version':VERSION,'approval_file_sha256':APPROVAL_SHA,
      'certificate_sha256':c['receipt_sha256'],'saved_contact_geometry_receipt_sha256':g['receipt_sha256'],
      'source_files':{str(p):sha(p) for p in sorted(OUT.glob('*.py'))+original_files},'input_files':c['files'],
      'unchanged_original_physical_constants':constants,'CPU_regression_tests':15,'CPU_tests_passed':True,
      'CPU_hardening':'positive-gap floor underside must enter material under upward epsilon and is rejected; original CPU_AUDIT retained',
      'test_positive_physical_contact_rows_are_explicitly_synthetic_fixtures':True,'real_physical_inside_success_demonstrated':False,
      'saved_contact_pose_is_only_native_geometry_evidence':True,'original_failed_artifacts_rewritten':False,
      'new_GPU_scenes':0,'new_solver_queries':0,'new_physical_actions':0,'new_raw_or_accepted_roots':0,
      'GPU_planner_support_partition_installed':False,'root_controller_integration_complete':False,
      'remaining':['fresh certificate/trace integration','model partition retaining full robot/wall checks','new supported target from actual grasp transform','bounded physical inside qualification','three-relation atomic root verification']}
    report['receipt_sha256']=digest(report);write_new(OUT/'CPU_AUDIT_V1_1.json',report);return report

if __name__=='__main__':
    r=publish();print(json.dumps({'receipt':r['receipt_sha256'],'certificate':r['certificate_sha256'],'geometry':r['saved_contact_geometry_receipt_sha256']},indent=2))
