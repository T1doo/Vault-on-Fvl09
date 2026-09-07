from goal_pilot48_v1.f2_on_beside_qualification_v1.spec import build_spec as parent,digest,sha,REFERENCE
from goal_pilot48_v1.f2_on_release_revision_v1.runtime import proposal,PROPOSAL_SHA
CAPS={'solver_problems':4,'fresh_scenes':1,'action_scenes':1,'collection_attempts':0}
def build_spec(relation):
    if relation not in ('on','beside'):raise ValueError('single on/beside qualification only')
    s=parent();s.update(schema_version='f2_single_relation_fresh_qualification_v1',relations=[relation],resource_caps=CAPS,
      high_level_state_checks={relation:6 if relation=='on' else 10},parent_consumed_job='p48_f2_on_beside_qualification_001',
      parent_relation_status='FAILED_RELEASE_IK' if relation=='on' else 'UNATTEMPTED',no_retry_or_height_scan=True)
    if relation=='on':proposal();s['release_revision1_proposal_file_sha256']=PROPOSAL_SHA
    return s
