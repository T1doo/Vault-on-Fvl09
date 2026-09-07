"""A first independently completed fresh micro is mandatory before second+V."""
import json,hashlib
from pathlib import Path
def checked(path,key):
    value=json.loads(Path(path).read_text(encoding='utf-8'));body=dict(value);h=body.pop(key)
    if hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()!=h:raise ValueError('prior receipt hash mismatch')
    return value
def restored(result):
    c=result.get('full_world_restoration_checks')
    return isinstance(c,dict) and set(c)=={'motion_gen','motion_gen_batch'} and all(v.get('valid') is True for v in c.values())
def verify_values(prior,guard,parent_manifest,new_manifest):
    r=prior.get('runtime_result') or {};result=r.get('result') or {}
    if prior.get('pass') is not True or prior.get('accounting_complete') is not True or r.get('micro_pass') is not True or result.get('pass') is not True or not restored(result):raise ValueError('first fresh micro/full restoration not passed')
    if guard.get('task_owned_cleanup_pass') is not True or guard.get('child_exit_code')!=0:raise ValueError('first fresh micro cleanup failed')
    if prior['manifest_sha256']!=parent_manifest['manifest_sha256'] or prior['job_id']!=guard['run_id'] or prior['job_id']==new_manifest['run_id']:raise ValueError('first/second job identity mismatch')
    if parent_manifest['recipe_spec_path']!=new_manifest['recipe_spec_path'] or parent_manifest['route_spec_path']!=new_manifest['route_spec_path']:raise ValueError('second confirmation recipe/route differs')
    if r['proposal_id']!=new_manifest['expected_recipe_id']:raise ValueError('prior recipe ID differs')
    return {'prior_job_id':prior['job_id'],'prior_terminal_receipt_sha256':prior['receipt_sha256'],'first_fresh_micro_pass':True,'second_fresh_micro_still_required':True}
def load(manifest):
    paths={k:Path(manifest[k]) for k in ('prior_micro_terminal_path','prior_micro_guard_path','prior_micro_manifest_path')}
    for p in paths.values():
        if not p.resolve().is_relative_to('/nfs_share/lijunhui'):raise ValueError('prior input outside workspace')
        if manifest['input_files'].get(str(p))!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('prior input not hash-bound')
    return verify_values(checked(paths['prior_micro_terminal_path'],'receipt_sha256'),checked(paths['prior_micro_guard_path'],'receipt_sha256'),checked(paths['prior_micro_manifest_path'],'manifest_sha256'),manifest)
