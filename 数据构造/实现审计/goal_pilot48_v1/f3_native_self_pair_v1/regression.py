import json,sys
from pathlib import Path
import numpy as np
from .checker import A,D,check_controls,inspect_q,model
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def main():
    results=[]
    for run in ('004','005'):
        d=D/('p48_f3_micro_'+run);plan=json.loads((d/'pregrasp.plan.json').read_text());names=json.loads((d/'initial_model_application.json').read_text())
        with np.load(d/'pregrasp.controls.npz',allow_pickle=False) as z:positions=z['position']
        q=plan['segment_receipts'][0]['start_qpos'];all_names=['q'+str(i) for i in range(len(q))]
        indices=(6,14,18,22,26,30)
        for i,j in enumerate(indices):all_names[j]='fl_joint'+str(i+1)
        controls=check_controls(positions,['fl_joint'+str(i+1) for i in range(6)],all_names,q)
        with np.load(d/'physical_trace.npz',allow_pickle=False) as z:actual=z['joint_qpos'];eef=z['eef_pose']
        models=model();rows=[]
        for i in range(max(0,len(actual)-400),len(actual)):
            state={'fl_joint'+str(k+1):float(actual[i,j]) for k,j in enumerate(indices)};rows.append({'trace_row':i,**inspect_q(state,models)})
        results.append({'run':run,'planned_control_native_pair':controls,'actual_tail_native_pair':rows})
        print(run,'plannedhits',sum(r['intersects'] for r in controls['rows']),'actualhits',sum(r['intersects'] for r in rows),flush=True)
    write_new(Path(__file__).parent/'regression.json',{'results':results,'new_GPU':False})
if __name__=='__main__':main()
