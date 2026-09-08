"""Evidence inventory and comparison with historical published results."""
import json,subprocess,hashlib
from pathlib import Path
from reconcile import sha,write,ROOTS,BASE,REPO,W
OUT=Path(__file__).parent;VAULT=W/'Vault-on-Fvl09';OLD=VAULT/'数据构造/实现审计/f2_f3_redesign_execution_v1'
legacy=json.loads((OLD/'hd_parallel_20260908_v1/HD_PARALLEL_RECEIPT.json').read_text()); hashes={c['source_trace']:c['source_trace_sha256_before'] for j in legacy['jobs'] for c in j['root_render_receipt']['cells']}
refs=[];search_dirs=set()
for file in OUT.glob('*_cells.json'):
 for c in json.loads(file.read_text()):
  refs.append({'cell':c['cell'],'original_hd_hash_matches_current':hashes[c['trace']]==c['trace_sha256_after'],'trace':c['trace'],'sha256':c['trace_sha256_after']});search_dirs.add(Path(c['trace']).parent.parent)
files=[]
for d in sorted(search_dirs):
 for p in d.rglob('*'):
  if p.is_symlink():continue
  if p.is_file():files.append(str(p))
artifacts=[p for p in files if any(k in Path(p).name.lower() for k in ['current','anchor','camera','rgb','rest','candidate']) or Path(p).suffix.lower() in ['.png','.jpg','.jpeg','.h5','.hdf5']]
protected=[]
for rel in ['STATE.json','budget_ledger.jsonl','CONTRACT.json','pilot_48_index.json','FINAL_COMPLETION_AUDIT.json','verification_profile.json']:
 p=OLD/rel;r=str(p.relative_to(VAULT));old=subprocess.check_output(['git','-C',str(VAULT),'show','1854cb2:'+r]); protected.append({'path':r,'sha256_current':sha(p),'unchanged_from_review_commit':sha(p)==hashlib.sha256(old).hexdigest()})
source=[]
for rel in ['controlled_multi_future/redesign_f2_f3_v1/pilot_f2_root_probe.py','controlled_multi_future/redesign_f2_f3_v1/pilot_f3_root_probe.py','controlled_multi_future/redesign_f2_f3_v1/f2_scene.py','controlled_multi_future/redesign_f2_f3_v1/scene.py','controlled_multi_future/redesign_f2_f3_v1/pilot_contract.py','controlled_multi_future/redesign_f2_f3_v1/strict_exit.py']:
 p=REPO/rel;s=OLD/'runtime_source_snapshot_v14'/rel;source.append({'path':str(p),'sha256':sha(p),'same_as_reviewed_snapshot_v14':sha(p)==sha(s)})
write(OUT/'PROVENANCE.json',{'trace_comparison_with_pre_review_hd_receipts':refs,'protected_historical_artifacts':protected,'live_sources':source,'original_evidence_search':{'searched_lineage_directories':[str(p) for p in sorted(search_dirs)],'file_count':len(files),'all_files':files,'candidate_rgb_anchor_rest_files':artifacts,'result':'No original RGB/current/full-anchor/rest numeric artifact found within final-root lineage; not a claim about every archive elsewhere.'},'cpu_only':True,'training_or_gpu_or_render_executed':False})
print('trace_hashes',len(refs),all(x['original_hd_hash_matches_current'] for x in refs),'historical_unchanged',all(x['unchanged_from_review_commit'] for x in protected),'source_unchanged',all(x['same_as_reviewed_snapshot_v14'] for x in source),'evidence_candidates',artifacts)
