"""Metadata-only inventory of explicitly accepted pilot cells; no H/model data."""
import hashlib,json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];W=Path('/nfs_share/lijunhui');A=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def seal(v):return {**v,'receipt_sha256':digest(v)}

def accepted_rows(document):
    from goal_pilot48_v1.pilot_matrix_audit_v1.audit import inspect_document
    structural=inspect_document(document)
    if not structural['pass']:raise ValueError('pilot matrix structural audit failed')
    rows=[]
    for cell in document['cells']:
        if cell['status'] not in ('accepted_existing','accepted_new'):continue
        path=Path(cell['evidence']['rollout_id']).resolve()
        if not path.is_relative_to(W/'Robotwin2/datasets'):raise ValueError('non-workspace pilot data')
        rows.append((cell,path))
    return rows,structural

def run():
    pilot=ROOT/'pilot_cells.json';document=read(pilot);cells,structure=accepted_rows(document);rows=[];inputs={str(pilot):sha(pilot)}
    for cell,path in cells:
        mp=path/'raw/manifest.json';m=read(mp);e=cell['evidence'];p=m['provenance']
        if m.get('formal_data') is not False or p.get('formal_data') is not False:raise ValueError('inventory excludes formal/test roots')
        if p['family']!=cell['family'] or p['program_id']!=cell['program_id'] or p['synthetic'] is not False:raise ValueError('accepted metadata identity drift')
        if m['action_count']!=e['actions'] or m['state_count']!=e['states'] or m['state_count']!=m['action_count']+1:raise ValueError('recorded action/state mismatch')
        if m['action_dim']!=26 or m['frequency_hz']!=250:raise ValueError('frozen primary stream changed')
        if m['raw_streams_npz_sha256']!=e['raw_id']:raise ValueError('registered raw identity differs from manifest')
        inputs[str(mp)]=sha(mp)
        rows.append({'family':cell['family'],'pilot':cell['pilot'],'program_id':cell['program_id'],'realization':cell['realization'],
          'root_id':e['root_id'],'rollout_id':str(path),'manifest_path':str(mp),'raw_id':e['raw_id'],
          'actions':m['action_count'],'states':m['state_count'],'frequency_hz':m['frequency_hz'],'action_dim':m['action_dim'],
          'metadata_manifest_link_verified_now':True,'raw_array_or_video_bytes_rehashed_now':False,
          'registered_raw_current_anchor_video_verifier_cleanup_pass':all(e.get(k) is True for k in ('raw_integrity_pass','raw_N_Nplus1_stream_contract_pass','raw_state0_equals_trace_state0','same_current_pass','anchor_equivalence_pass','video_integrity_pass','family_verifier_pass','cleanup_pass')),
          'stream_field_names':sorted(m['stream_field_metadata']),'audit_field_names':sorted(m['audit_field_metadata']),
          'provenance_field_names':sorted(p),'raw_contains_audit_only_fields_by_design':True,
          'model_input_export_audited_now':False})
    reports=[ROOT/'reuse18/audit.json',ROOT/'reuse18/resolution_audit.json',ROOT/'f4_b_pilot_acceptance_v2/FINAL_AUDIT_001.json',ROOT/'pilot_registration_v1/F4_B_ADOPTION_001.json']
    evidence=[]
    for path in reports:
        d=read(path);inputs[str(path)]=sha(path)
        evidence.append({'path':str(path),'file_sha256':sha(path),'receipt_sha256':d.get('receipt_sha256'),
          'schema_version':d.get('schema_version'),'recorded_pass':d.get('pass'),'limitations':d.get('limitations',[]),
          'contents_read_now':True,'full_underlying_audit_reexecuted_now':False})
    return seal({'schema_version':'pilot_no_training_audit_coverage_inventory_v1','scope':'accepted pilot metadata and existing audit evidence only',
      'accepted_cell_count':len(rows),'family_counts':dict(Counter(r['family'] for r in rows)),
      'group_counts':dict(Counter(r['family']+'/'+r['pilot'] for r in rows)),'registration_structure_rechecked':structure,
      'rows':rows,'existing_evidence':evidence,'input_files':inputs,
      'future_remaining_checks_status':'PLANNED_NOT_EXECUTED','no_training_suite_complete':False,'scientific_stage1_proven':False,
      'model_run':False,'H_views_generated':False,'formal_test_accessed':False,'raw_or_registration_modified':False})

if __name__=='__main__':
    from realization_utf8_io_v1 import write_new
    r=run();write_new(Path(__file__).parent/'INVENTORY_001.json',r)
    print({'accepted':r['accepted_cell_count'],'families':r['family_counts'],'metadata_only':True,'suite_complete':False})
