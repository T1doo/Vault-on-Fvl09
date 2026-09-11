"""Unified CPU describe / separately authorized native collection and copy entry."""
import argparse,json
from pathlib import Path
import scene_plan, family_entry, file_source_pin

def finish_copy(spec,output,result,destination):
 if result.get('pass') is not True:raise ValueError('failed root cannot publish')
 output=Path(output);destination=Path(destination)
 if spec['family']=='F1':
  from f1_portable_export import seal_source,copy_root
  return copy_root(seal_source(output,spec,result),destination)
 if spec['family']=='F4':
  from formal_export import seal_native_source,copy_sealed_root
  from family_entry import cohort_root
  cells=[]
  for p in spec['programs']:
   for r in spec['realizations']:
    root=cohort_root(output,r);branch=root/'branches'/p['program_id'];raw=branch/'raw/raw_streams.npz';manifest=json.loads((raw.parent/'manifest.json').read_text(encoding='utf-8'));capture=Path(manifest['provenance']['formal_current_capture_path'])
    cells.append({'program_id':p['program_id'],'realization_id':r,'raw_path':str(raw),'capture_path':str(capture),'current_arrays_path':str(capture.parent/'current.npz'),'anchor_path':str(capture.parent/'anchor.json'),'prefix_artifact_path':str(root/'canonical_prefix_artifact/prefix_arrays.npz'),'branch_receipt_path':str(branch/'receipt.json'),'root_receipt_path':str(root/'root_receipt.json'),'source_result_path':str(output/'f4_native_result.json')})
  index=output/'source_seal/source_index.json'
  if not index.is_file():index=seal_native_source(str(output),spec,cells,result)
  return copy_sealed_root(str(index),str(destination))
 return result.get('copy') # F2/F3 native runner already seals after independent finalizer.

def copy_only(spec,output,authorization):
 """Disk-only acceptance recheck and copy recovery; never creates a native scene."""
 file_source_pin.validate(authorization);scene_plan.validate_resolved(spec)
 if authorization.get('spec_sha256')!=spec['spec_sha256']:raise ValueError('copy recovery spec mismatch')
 if spec['family']!='F1':raise ValueError('this bounded copy recovery is F1 only')
 output=Path(output)
 previous=json.loads((output/'independent_structure.json').read_text(encoding='utf-8'))
 if previous.get('pass') is not True:raise ValueError('root collection was not independently accepted')
 compatibility=None
 binding=authorization.get('source_compatibility_receipt')
 if binding:
  import hashlib
  raw=Path(binding['path']).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('source compatibility receipt bytes changed')
  compatibility=json.loads(raw)
 actual=family_entry.finalize_structure(spec=spec,output=output,write_receipt=False,source_compatibility=compatibility)
 import hashlib
 audit={'root_id':spec['root_id'],'spec_sha256':spec['spec_sha256'],'original_report_sha256':hashlib.sha256((output/'independent_structure.json').read_bytes()).hexdigest(),'recomputed':actual,'original_report_unchanged':True,'source_bundle_sha256':authorization['source_bundle_sha256'],'source_compatibility_receipt':binding,'GPU_started':False}
 audit_hash=hashlib.sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest();audit_path=output/'copy_revalidations'/(audit_hash+'.json');family_entry.write(audit_path,audit)
 if actual.get('pass') is not True:raise ValueError('saved root no longer independently passes')
 result=dict(previous);result['copy']=finish_copy(spec,output,previous,authorization['copy_destination'])
 file_source_pin.validate(authorization)
 family_entry.write(output/'execution_result.json',result)
 family_entry.write(output/'copy_recovery_result.json',{'pass':True,'root_id':spec['root_id'],'GPU_started':False,'physical_execution_count':0,'copy':result['copy'],'revalidation_audit':{'path':str(audit_path),'sha256':hashlib.sha256(audit_path.read_bytes()).hexdigest()}})
 return result


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--authorization',type=Path);p.add_argument('--output',type=Path);p.add_argument('--describe',action='store_true');p.add_argument('--copy-only',action='store_true');p.add_argument('--collect-only',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args(argv)
 spec=json.loads(a.spec.read_text(encoding='utf-8'));scene_plan.validate_resolved(spec)
 if a.describe:
  if spec['family']=='F1':budget=family_entry.get_call_budget(spec)
  elif spec['family']=='F4':
   from native_f4 import call_budget
   budget=call_budget()
  else:
   from native_f2f3 import call_budget
   budget=call_budget(spec['family'])
  print(json.dumps({'root_id':spec['root_id'],'matrix':family_entry.planned_cells(spec),'calls':budget,'execution_authorized':False}));return
 if a.authorization is None or a.output is None:p.error('--authorization and --output required')
 auth=json.loads(a.authorization.read_text(encoding='utf-8'));file_source_pin.validate(auth)
 if a.copy_only:
  result=copy_only(spec,a.output,auth);print(json.dumps(result));return result
 if a.resume:auth={**auth,'resume':True}
 if auth.get('gpu_execution_authorized') is not True:raise PermissionError('current CPU package is not GPU authorization')
 if not auth.get('copy_destination'):raise ValueError('root copy destination must be fixed before action')
 limits=auth['job_limits']
 if not 0<limits['timeout_seconds']+limits['cleanup_grace_seconds']<=limits['gpu_reservation_seconds']:raise ValueError('timeout exceeds lease reservation')
 result=family_entry.run_family_root(spec=spec,output=a.output,authorization=auth)
 if result['pass'] and not a.collect_only:result['copy']=finish_copy(spec,a.output,result,auth['copy_destination'])
 file_source_pin.validate(auth)
 from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json
 atomic_write_json(a.output/'execution_result.json',result)
 print(json.dumps(result));return result
if __name__=='__main__':
 result=main()
 raise SystemExit(1 if isinstance(result,dict) and result.get('pass') is not True else 0)
