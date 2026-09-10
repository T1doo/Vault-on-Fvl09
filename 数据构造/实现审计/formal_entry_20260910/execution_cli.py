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
    root=cohort_root(output,r);branch=root/'branches'/p['program_id'];raw=branch/'raw/raw_streams.npz';manifest=json.loads((raw.parent/'manifest.json').read_text());capture=Path(manifest['provenance']['formal_current_capture_path'])
    cells.append({'program_id':p['program_id'],'realization_id':r,'raw_path':str(raw),'capture_path':str(capture),'current_arrays_path':str(capture.parent/'current.npz'),'anchor_path':str(capture.parent/'anchor.json'),'prefix_artifact_path':str(root/'canonical_prefix_artifact/prefix_arrays.npz'),'branch_receipt_path':str(branch/'receipt.json'),'root_receipt_path':str(root/'root_receipt.json'),'source_result_path':str(output/'f4_native_result.json')})
  index=output/'source_seal/source_index.json'
  if not index.is_file():index=seal_native_source(str(output),spec,cells,result)
  return copy_sealed_root(str(index),str(destination))
 return result.get('copy') # F2/F3 native runner already seals after independent finalizer.

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--authorization',type=Path);p.add_argument('--output',type=Path);p.add_argument('--describe',action='store_true');a=p.parse_args(argv)
 spec=json.loads(a.spec.read_text());scene_plan.validate_resolved(spec)
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
 auth=json.loads(a.authorization.read_text());file_source_pin.validate(auth)
 if auth.get('gpu_execution_authorized') is not True:raise PermissionError('current CPU package is not GPU authorization')
 if not auth.get('copy_destination'):raise ValueError('root copy destination must be fixed before action')
 limits=auth['job_limits']
 if not 0<limits['timeout_seconds']+limits['cleanup_grace_seconds']<=limits['gpu_reservation_seconds']:raise ValueError('timeout exceeds lease reservation')
 result=family_entry.run_family_root(spec=spec,output=a.output,authorization=auth)
 if result['pass']:result['copy']=finish_copy(spec,a.output,result,auth['copy_destination'])
 file_source_pin.validate(auth)
 from controlled_multi_future.redesign_f2_f3_v2.canonical import atomic_write_json
 atomic_write_json(a.output/'execution_result.json',result)
 print(json.dumps(result));return result
if __name__=='__main__':
 result=main()
 raise SystemExit(1 if isinstance(result,dict) and result.get('pass') is not True else 0)
