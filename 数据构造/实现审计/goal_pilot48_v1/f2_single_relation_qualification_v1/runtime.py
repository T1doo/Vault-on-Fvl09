"""One fresh original prefix replay; no reused old scene or consumed job."""
import types,gc
from pathlib import Path
from goal_pilot48_v1.f2_on_beside_qualification_v1 import runtime as base
from .spec import build_spec,digest

def suffix_callable(relation):
    if relation=='on':
        from goal_pilot48_v1.f2_on_release_revision_v1.runtime import run
    else:
        from goal_pilot48_v1.f2_on_beside_runtime_v1.runtime import run
    return run
def run(manifest):
    from realization_utf8_io_v1 import write_new
    out=Path(manifest['jobs'][0]['output_namespace']);out.mkdir(parents=True,exist_ok=False)
    relation=manifest['qualification_relation'];local=base.LocalCounts();branch=None;error=None;known=False
    try:
        spec=build_spec(relation)
        if digest(spec)!=manifest.get('single_relation_qualification_spec_sha256'):raise ValueError('single relation spec binding')
        write_new(out/'qualification_spec.json',spec);artifact,arrays=base.load_reference()
        if artifact['reference_current_sha256']!=spec['prefix_lineage']['current']['aggregate_sha256']:raise ValueError('canonical/current mismatch')
        ns=dict(base.run_one.__globals__);ns['suffix_run']=suffix_callable(relation)
        run_one=types.FunctionType(base.run_one.__code__,ns,base.run_one.__name__,base.run_one.__defaults__,base.run_one.__closure__)
        with local:
            try:branch=run_one(manifest,spec,relation,out/relation,artifact,arrays,local)
            finally:local.retire_completed();gc.collect()
    except BaseException as exc:error=base.failure(exc,'single_relation')
    try:counts=local.snapshot();known=True
    except BaseException as exc:counts={};error=error or base.failure(exc,'counts')
    safe=known and error is None and branch is not None and branch['pass'] and counts.get('trajectory_queries',5)<=4 and counts.get('fresh_scene_attempts',2)<=1
    value={'schema_version':'f2_single_relation_qualification_terminal_v1','manifest_sha256':manifest.get('manifest_sha256'),**counts,
      'relation':relation,'branch':branch,'error':error,'pass':bool(safe),'accounting_complete':known,
      'scientific_route_pass':bool(safe and branch['scientific_route_pass'] and counts['trajectory_queries']==4 and counts['fresh_scene_attempts']==1 and counts['action_scenes_observed']==1),
      'qualification_only':True,'whole_root_qualification_complete':False,'new_raw_trajectories':0,'new_accepted_roots':0,
      'high_level_state_checks':None if branch is None else branch['high_level_state_checks'],'high_level_state_check_cap':6 if relation=='on' else 10,
      'inside_contact_permission_used':False,'original_Gates_and_model_retained':True}
    value['receipt_sha256']=digest(value);write_new(out/'job_terminal.json',value);return value
