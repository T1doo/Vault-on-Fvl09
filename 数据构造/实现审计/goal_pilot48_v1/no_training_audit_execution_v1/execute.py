"""24 serial CPU subprocesses, finite timeout and append-only checkpoints."""
import subprocess,sys,time
from .common import *
def run():
    lock=checked(OUT/'INPUT_LOCK_001.json');rows=[]
    for row in lock['cells']:
        i=row['index'];path=OUT/'cells'/('%02d.json'%i)
        if path.exists():raise FileExistsError('do not overwrite or silently retry prior cell '+str(i))
        try:
            child=subprocess.run([sys.executable,'-m','goal_pilot48_v1.no_training_audit_execution_v1.cell',str(i)],timeout=180,check=False)
            if path.exists():result=checked(path)
            else:
                result=seal({'cell_index':i,'pass':False,'error':{'type':'ChildExitWithoutReceipt','exit_code':child.returncode},'suite_complete':False});write(path,result)
        except subprocess.TimeoutExpired:
            result=seal({'cell_index':i,'pass':False,'error':{'type':'CPUCellTimeout','timeout_seconds':180},'suite_complete':False});write(path,result)
            print('S1_CELL',i,'TIMEOUT',flush=True)
        rows.append({'cell_index':i,'pass':result['pass'],'receipt_sha256':result['receipt_sha256'],'path':str(path)})
        snapshot=seal({'schema_version':'no_training_S1_partial_progress_v1','input_lock_receipt_sha256':lock['receipt_sha256'],
          'checked':len(rows),'passed':sum(r['pass'] for r in rows),'failed':sum(not r['pass'] for r in rows),'target_existing':24,'target_goal':48,
          'cells':rows,'suite_complete':False,'scientific_stage1_proven':False,'S2_S3_S4_executed':False})
        write(OUT/'progress'/('%02d.json'%len(rows)),snapshot)
    write(OUT/'S1_EXISTING24_PARTIAL_001.json',snapshot)
if __name__=='__main__':run()
