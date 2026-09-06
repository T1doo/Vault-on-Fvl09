"""One-time Goal checkpoint creation and explicit already-audited18-cell reuse."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from budget import ROOT,KEYS,read,digest,atomic,append
def checked(p):
    d=read(p);v=dict(d);h=v.pop('receipt_sha256');assert digest(v)==h;return d
def main():
    if (ROOT/'STATE.json').exists():raise FileExistsError('Goal checkpoint already exists; never reset budget')
    contract=checked(ROOT/'CONTRACT.json');audit=checked(ROOT/'reuse18/audit.json');resolution=checked(ROOT/'reuse18/resolution_audit.json')
    assert audit['pass'] and audit['eligible_existing_cells']==18 and resolution['pass']
    rows=audit['rows'];groups={}
    for r in rows:groups.setdefault(r['root_id'],[]).append(r)
    registration=[];cells=[];programs={'F1':['F1-red','F1-green','F1-blue'],'F2':['F2-inside','F2-on','F2-beside'],'F3':['F3-VVHH','F3-VHVH','F3-VHHV'],'F4':['F4-ABC','F4-ACB','F4-BAC']}
    mapping={}
    for root,rs in groups.items():
        family=rs[0]['program_id'].split('-')[0];pilot='B' if any(r['realization']=='r_inv_motion' for r in rs) else 'A';mapping[(family,pilot)]=(root,rs)
        for r in rs:registration.append({**r,'family':family,'pilot':pilot,'pilot_input_accepted':True,'acceptance_basis':'ISSUED_UNDER_USER_GOAL; independent existing raw/trace/video/current/resolution audit','new_collection':False})
    for family,ids in programs.items():
        for pilot in ('A','B'):
            for pid in ids:
                for realization in ('r_pc','r_inv_path' if pilot=='A' else 'r_inv_motion'):
                    match=[r for r in registration if r['family']==family and r['pilot']==pilot and r['program_id']==pid and r['realization']==realization]
                    assert len(match)<=1
                    cells.append({'family':family,'pilot':pilot,'program_id':pid,'realization':realization,'status':'accepted_existing' if match else 'pending','evidence':match[0] if match else None})
    assert len(cells)==48 and sum(c['status']=='accepted_existing' for c in cells)==18
    event={'kind':'GOAL_INITIALIZED','job_id':None,'unix_time':__import__('time').time(),'previous_event_sha256':None,'contract_receipt_sha256':contract['receipt_sha256'],'baseline_consumption_excluded_but_history_retained':True};event['event_sha256']=digest(event)
    append(ROOT/'budget_ledger.jsonl',event);(ROOT/'attempts.jsonl').touch(exist_ok=False)
    caps=contract['caps'];atomic(ROOT/'STATE.json',{'goal_id':contract['goal_id'],'status':'ACTIVE','last_turn_classification':'progress','source_profiles':{'active':'3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7','F1_parent':'9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72'},
        'families':{'F1':'PILOT_A_B_INPUTS_ACCEPTED_EXISTING','F2':'NEW_INWARD_PLANNER_RUNTIME_CPU_READY','F3':'SUPPORT_AWARE_PHYSICAL_CONFIRMATION_READY','F4':'A_ACCEPTED_B_RUNTIME_CPU_READY'},
        'pilot_input_accepted':18,'pilot_input_target':48,'running':None,'next_task':'F3 support-aware physical micro, first fresh scene','budget':{'caps':caps,'used':{k:0 for k in KEYS},'reserved':{k:0 for k in KEYS},'remaining':caps,'active_reservations':{},'terminal_jobs':[]},'last_budget_event_sha256':event['event_sha256'],
        'completion':{'FOUR_FAMILY_COLLECTION_PASS':False,'PILOT_INPUT_48_OF_48_ACCEPTED':False,'COLLECTOR_CONTINUOUS_RUN_VERIFIED':False,'FORMAL_PROTOCOL_DRAFT_READY':False},'model_experiments_completed':False,'stage1_scientific_complete':False,'formal_collection_authorized':False})
    atomic(ROOT/'pilot_cells.json',{'schema_version':'goal_pilot48_cells_v1','contract_receipt_sha256':contract['receipt_sha256'],'independent_audit_receipt_sha256':audit['receipt_sha256'],'resolution_audit_receipt_sha256':resolution['receipt_sha256'],'accepted':18,'cells':cells,'scientific_stage1_completion_claimed':False})
    print('Goal initialized without resetting historical artifacts;18/48 pilot input cells explicitly registered')
if __name__=='__main__':main()
