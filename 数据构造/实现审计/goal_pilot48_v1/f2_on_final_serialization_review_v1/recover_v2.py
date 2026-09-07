"""Append-only source-complete revision; original recovery001 is untouched."""
from pathlib import Path
from . import recover as old
def run():
    original=old.run();saved=old.load(old.OUT/'RECOVERY_REVIEW_001.json')
    if original!=saved:raise ValueError('original recovery evidence/source drift')
    result=dict(original);result.pop('receipt_sha256')
    result.update(schema_version='f2_on_final_serialization_append_only_review_v2',
      parent_review_receipt_sha256=original['receipt_sha256'],
      gripper_predicate_source='Base_Task.is_left_gripper_open -> Robot.is_left_gripper_open -> left_gripper_val > 0.8',
      serialization_helper_source='f2_on_beside_runtime_v2.runtime.json_values',
      source_completion_only_no_predicate_or_result_changes=True)
    paths=[old.P/'envs/robot/robot.py',old.P/'envs/_base_task.py',Path(__file__),old.OUT/'RECOVERY_REVIEW_001.json']
    result['files']={**original['files'],**{str(p):old.sha(p) for p in paths}}
    result['receipt_sha256']=old.digest(result);return result
if __name__=='__main__':
    from realization_utf8_io_v1 import write_new
    r=run();write_new(old.OUT/'RECOVERY_REVIEW_002.json',r)
    print({'derived_final_predicates_pass':r['derived_final_predicates_pass'],'receipt_sha256':r['receipt_sha256']})
