"""S0: explicit accepted pilot input lock, no recursive test-data discovery."""
from .common import *
from goal_pilot48_v1.no_training_audit_plan_v1.inventory import accepted_rows
def run():
    table=ROOT/'pilot_cells.json';doc=read(table);accepted,structure=accepted_rows(doc)
    if len(accepted)!=24:raise ValueError('this bounded audit is frozen to current24; new cohort needs new lock')
    sources=[*OUT.glob('*.py'),P/'controlled_multi_future/raw_writer.py',P/'controlled_multi_future/schemas.py',P/'controlled_multi_future/probes/runtime_trace.py',
      W/'Robotwin2/tmp/cmf_f1_parent_317387b/数据构造/实现审计/代码审阅快照/controlled_multi_future/probes/runtime_trace.py',
      A/'realization_current_layout_audit_v1.py',ROOT/'no_training_audit_plan_v1/inventory.py',ROOT/'pilot_matrix_audit_v1/audit.py',
      P/'controlled_multi_future/current_hasher.py',P/'controlled_multi_future/canonical_artifact.py',A/'realization_utf8_io_v1.py']
    files={str(table):sha(table)};rows=[]
    for i,(cell,path) in enumerate(accepted):
        e=cell['evidence'];m=read(path/'raw/manifest.json')
        if m['formal_data'] is not False or m['provenance']['synthetic'] is not False:raise ValueError('formal/synthetic input forbidden')
        current=Path(e['current_initial_state_audit']['current_directory'])
        receipt=path/'receipt.json';receipt_kind='original_finalized'
        required=[path/'trace_source.npz',path/'raw/raw_streams.npz',path/'raw/manifest.json',path/'raw/manifest.sha256.json',path/'video/trajectory.mp4',current/'current.json',current/'current_arrays.npz']
        if not receipt.exists():
            publication=A/'REALIZATION_UTF8_FAILURE_RESOLUTION_PUBLICATION_V1_20260906.json';p=checked(publication)
            receipt=Path(p['derived_branch_path']);branch=read(receipt)
            if e.get('receipt_is_trace_reconstructed') is not True or Path(branch['raw_directory'])!=path/'raw' or sha(receipt)!=p['derived_branch_file_sha256'] or branch['status']!='accepted':raise ValueError('missing final receipt without exact approved resolution')
            required.extend([publication,path/'receipt.provisional.json',Path(p['reconciliation_path'])]);receipt_kind='approved_append_only_derived_final_original_provisional_preserved'
        required.append(receipt)
        binding={str(p):sha(p) for p in required}
        if binding[str(path/'trace_source.npz')]!=e['trace_sha256'] or binding[str(path/'raw/raw_streams.npz')]!=e['raw_id'] or binding[str(path/'video/trajectory.mp4')]!=e['video_sha256']:raise ValueError('accepted disk identity changed')
        files.update(binding);rows.append({'index':i,'cell':cell,'paths':{'rollout':str(path),'current':str(current),'final_receipt':str(receipt)},'receipt_kind':receipt_kind,'files':binding})
    reports=[ROOT/'reuse18/audit.json',ROOT/'reuse18/resolution_audit.json',ROOT/'f4_b_pilot_acceptance_v2/FINAL_AUDIT_001.json',ROOT/'pilot_registration_v1/F4_B_ADOPTION_001.json']
    files.update({str(p):sha(p) for p in reports})
    value=seal({'schema_version':'no_training_S0_input_lock_v1','accepted_count':24,'target_count':48,'structure':structure,'cells':rows,'input_files':files,
      'source_files':{str(p):sha(p) for p in sources},'per_cell_timeout_seconds':180,'serial_CPU_only':True,'formal_test_accessed':False,
      'S0_input_lock_complete':True,'S1_executed':False,'suite_complete':False,'scientific_gate_proven':False})
    write(OUT/'INPUT_LOCK_001.json',value);print('S0_INPUT_LOCK_COMPLETE cells=24',flush=True);return value
if __name__=='__main__':run()
