"""Explicit injected entry ordering; GPU/runtime ports remain main-owned work."""
from .scene import initial_gate,derive_targets
def qualify_existing_scene(scene,spec,ports,*,confirmation=False,prior_pass=None):
    """All ports must be supplied by a counted, guarded live runner; no defaults."""
    if confirmation and (not prior_pass or prior_pass.get('qualified') is not True or prior_pass.get('spec_receipt')!=spec['receipt_sha256']):raise ValueError('same-design first fresh pass required')
    snapshot=ports.snapshot(scene);standing=initial_gate(snapshot,spec)
    if not standing['pass']:return {'qualified':False,'stage':'initial_standing_or_identity','standing':standing,'solver_problems':0}
    ports.capture_current_anchor_initialize_trace(scene)
    targets=derive_targets(spec,snapshot['bottle_pose']);ik=[]
    for label in ('current','pregrasp','grasp'):
        result=ports.single_full_constraint_IK(scene,label,targets)
        if result.get('solver_problems')!=1:raise ValueError('single IK exact accounting required')
        ik.append(result)
        if result.get('pass') is not True:return {'qualified':False,'stage':label+'_IK','IK':ik,'solver_problems':len(ik)}
    # Must include actual full-arm native pre-execution controls and old Gates.
    micro=ports.micro_three_plans(scene,targets,spec)
    used=micro.get('solver_problems')
    if type(used)is not int or not 0<=used<=3:raise ValueError('micro bounded exact problem accounting required')
    if micro.get('pass') is not True:return {'qualified':False,'stage':'physical_micro','IK':ik,'micro':micro,'solver_problems':3+used}
    restored=micro.get('full_world_restoration_checks')
    if used!=3 or micro.get('post_lift',{}).get('pass') is not True or micro.get('native_full_arm_controls_pass') is not True or not isinstance(restored,dict) or set(restored)!={'motion_gen','motion_gen_batch'} or not all(v.get('valid') is True for v in restored.values()):raise ValueError('micro success missing full native/old Gate/restoration evidence')
    ports.record_micro_pass(scene,spec,micro)
    result={'qualified':True,'spec_receipt':spec['receipt_sha256'],'IK':ik,'micro':micro,'solver_problems':6,'fresh_confirmations':2 if confirmation else 1}
    if confirmation:
        prefix=ports.original_prefix_extension_eleven_plans(scene,spec)
        used=prefix.get('solver_problems')
        if type(used)is not int or not 0<=used<=11 or (prefix.get('pass') is True and used!=11):raise ValueError('original prefix extension bounded accounting required')
        result.update(prefix=prefix,qualified=prefix.get('pass') is True,solver_problems=6+used)
    return result
