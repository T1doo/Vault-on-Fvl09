"""Single adopted +4mm on release recipe; all old source stays untouched."""
import copy,types
from goal_pilot48_v1.f2_on_beside_runtime_v1 import runtime as old,spec as oldspec
from goal_pilot48_v1.f2_on_beside_runtime_v1.spec import A,load,sha,digest
PROPOSAL=A/'goal_pilot48_v1/f2_on_release_failure_review_v1/SINGLE_REVISION_PROPOSAL_001.json'
PROPOSAL_SHA='c938f2c9f1e11d29a7283b3a586510d833cb7ec9af2eae64b5ff7e68b3046716'
def proposal():
    if sha(PROPOSAL)!=PROPOSAL_SHA:raise ValueError('unique adopted recipe evidence changed')
    p=load(PROPOSAL)
    if p['offset_world_z_m']!=.004 or not p['native_and_attached_target_CPU_pass'] or not p['no_scale_pair_exception']:raise ValueError('different on recipe')
    return p
def revise(spec):
    oldspec.validate(spec)
    if spec['relation']!='on':raise ValueError('on-only revision')
    proposal();out=copy.deepcopy(spec);out.pop('receipt_sha256');out['targets'][1]['pose'][2]+=.004
    out['on_release_revision1']={'offset_world_z_m':.004,'proposal_file_sha256':PROPOSAL_SHA,'only_release_waypoint_changed':True,
      'extra_preopen_drop_m':.004,'nominal_metadata_target_unchanged':True,'collision_model_and_gates_unchanged':True}
    out['receipt_sha256']=digest(out);return out
def validate(spec):
    p=copy.deepcopy(spec);h=p.pop('receipt_sha256',None)
    if digest(p)!=h:raise ValueError('revised spec selfhash')
    revision=p.pop('on_release_revision1');p['targets'][1]['pose'][2]-=.004;p['receipt_sha256']=digest(p)
    expected=revise(p)
    if expected!=spec:raise ValueError('only exact release+4mm revision allowed')
    return True
def build_targets(scene,relation):return revise(oldspec.build_targets(scene,relation))
def run(*args,**kwargs):
    ns=dict(old.run.__globals__);ns.update(build_targets=build_targets,validate=validate)
    fn=types.FunctionType(old.run.__code__,ns,old.run.__name__,old.run.__defaults__,old.run.__closure__)
    fn.__kwdefaults__=old.run.__kwdefaults__
    return fn(*args,**kwargs)
