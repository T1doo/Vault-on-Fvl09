import json,hashlib,zipfile,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];VAULT=BASE.parents[2]; OLD=VAULT/'数据构造/实现审计/f2_f3_redesign_execution_v2'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(n,d): (BASE/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
# Bounded cross-directory reconciliation of exactly the reported F1-red item.
audit=VAULT/'数据构造/实现审计/REALIZATION_NINE_FINAL_AUDIT_V1_20260906.json';co=next(x for x in json.loads(audit.read_text())['cohorts'] if x['cohort']=='F1_A_path');rp=Path(co['root_receipt_path']);root=json.loads(rp.read_text());b=next(x for x in root['branch_receipts'] if x['program_id']=='F1-red')
checks={'aggregate_root_file_hash':sha(rp)==co['root_receipt_file_sha256'],'aggregate_accepted':root['root_finalization']['accepted'] is True,'parent_root':b['root_id']==co['parent_root_id'],'trace_hash':sha(b['trace_source']['path'])==b['trace_source']['sha256'],'video_hash':sha(b['development_video_receipt']['path'])==b['development_video_receipt']['file_sha256'],'provisional_hash':sha(b['receipt_recovery']['original_partial_receipt_path'])==b['receipt_recovery']['original_partial_receipt_file_sha256']}
checks['raw_bindings']=all(sha(p)==h for p,h in co['raw_video_file_bindings'].items() if 'cmf_realization_recovery_v1_2/F1_A_path/branches/F1-red/' in p)
write('F1_SOURCE_LINK.json',{'checks':checks,'pass':all(checks.values()),'aggregate_audit':str(audit),'aggregate_root':str(rp),'aggregate_root_sha256':sha(rp),'trace':b['trace_source'],'receipt_recovery':b['receipt_recovery'],'interpretation':'cross-directory final acceptance covers this trace; original local root receipt remains absent; no new scientific promotion'})
idx=json.loads((OLD/'P4_UNIFIED_48_REFERENCE_INDEX.json').read_text());groups={}
for family in ['F1','F2','F3','F4']:
 rows=[e for e in idx['entries'] if e['family']==family];paths=[];trace_paths=[];times=[]
 for e in rows:
  if family in ['F2','F3']:
   src=e['source'];trace_paths.append(Path(src['trace']['path'])); paths.extend(Path(src[k]['path']) for k in ['trace','cell_receipt','independent_cell_finalizer','root_receipt','prefix_artifact']);paths.extend(Path(v['path']) for v in src['current_bundle']['files'].values());c=json.loads(Path(src['cell_receipt']['path']).read_text());times.append(c['elapsed_seconds'])
  else:
   src=e['source'];paths.extend(Path(v['path']) for v in src['files'].values() if v.get('path'));trace_paths.append(Path(src['files']['trace']['path']));roll=Path(e['source_profile']['rollout_id']);paths.extend(p for p in (roll/'raw').rglob('*') if p.is_file())
   receipt=Path(src['files']['branch_receipt']['path'])
   try:c=json.loads(receipt.read_text())
   except json.JSONDecodeError:c={} # preserved truncated provisional; aggregate evidence checked above
   t=c.get('elapsed_seconds')
   if isinstance(t,(int,float)):times.append(t)
 unique=set(paths);sizes=[p.stat().st_size for p in trace_paths]; unpack=[]
 for p in trace_paths:
  with zipfile.ZipFile(p) as z:unpack.append(sum(f.file_size for f in z.infolist()))
 groups[family]={'cells':len(rows),'unique_files':len(unique),'unique_bytes':sum(p.stat().st_size for p in unique),'referenced_bytes':sum(p.stat().st_size for p in paths),'trace_bytes_mean':statistics.mean(sizes),'trace_bytes_max':max(sizes),'uncompressed_trace_peak_bytes':max(unpack),'cell_elapsed_seconds_observed':times,'timing_scope':'cell receipt elapsed; excludes outer setup/cleanup and is not full GPU lease','trace_paths':[str(x) for x in trace_paths]}
write('STORAGE_INVENTORY.json',groups)
print(json.dumps({'F1_link':checks,'storage':{k:{a:v for a,v in d.items() if a not in ['trace_paths','cell_elapsed_seconds_observed']} for k,d in groups.items()}},ensure_ascii=False))
