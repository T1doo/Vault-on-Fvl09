from goal_pilot48_v1.f2_inside_native_floor_v1.certificate import A,sha

APPROVAL=A/'goal_pilot48_v1/USER_F2_CONTACT_F3_UPRIGHT_APPROVAL_V1_20260907.md'
APPROVAL_SHA='5eeb6a2998656cec08657cbcbcb2379b544a53a7e0f139509559f2f61ef6fd5e'
IMPACT=A/'goal_pilot48_v1/f2_controlled_inside_runtime_v2/TRANSPORT_IMPACT.md'
IMPACT_SHA='7f48f389ac99b1e906d119a9df8e929947f715f6536835283809d5ac84d62b6a'
DESIGN='F2_SUPPORTED_DESCENT_BOX9_RULE_V1'
PHASE=A/'goal_pilot48_v1/F2_SUPPORTED_DESCENT_PHASE_CLARIFICATION_V1_20260907.md'
PHASE_SHA='56dd9511921aa60e9e1dd8f5f38ed8a61eb755b0c4b5b7fedade5b53ffd86db0'

def verify_approval():
    if sha(APPROVAL)!=APPROVAL_SHA or sha(IMPACT)!=IMPACT_SHA:raise ValueError('explicit supported-contact approval/impact hash changed')
    if sha(PHASE)!=PHASE_SHA:raise ValueError('main-thread approved-stage implementation clarification changed')
    return {'design_id':DESIGN,'approval_file':str(APPROVAL),'approval_sha256':APPROVAL_SHA,'impact_sha256':IMPACT_SHA,
      'phase_clarification_file':str(PHASE),'phase_clarification_sha256':PHASE_SHA,
      'scope':'final controlled descent and its required supported hold, before first slow-open; never carry/preinsert',
      'old_failed_audit_must_be_retained':True}
