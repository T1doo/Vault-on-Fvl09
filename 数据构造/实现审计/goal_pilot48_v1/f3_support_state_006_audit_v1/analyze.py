"""Read-only exact last250 hold classification using unchanged contact gate."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');O=Path(__file__).parent;D=Path('/nfs_share/lijunhui/Robotwin2/datasets/p48_f3_micro_006')
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from controlled_multi_future.f3_physical_contact_signal_v8 import classify_contact_pair_physical_hit_v8
from goal_pilot48_v1.runtime.support_witness import hold_witness
from realization_utf8_io_v1 import write_new
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    with np.load(D/'physical_trace.npz',allow_pickle=False) as z:t={k:z[k] for k in z.files}
    model=json.loads((D/'postclose_attached_model.json').read_text());shapes=model['native_bottle_shapes']
    vertices=np.concatenate([R.from_quat(np.array(s['shape_local_pose'])[[4,5,6,3]]).apply(s['vertices'])+s['shape_local_pose'][:3] for s in shapes])
    rows=[];summary=[]
    for i in range(len(t['object_pose'])-250,len(t['object_pose'])):
        pose=t['object_pose'][i];pairs=json.loads(str(t['contact_pairs_json'][i]));rows.append({'eef':t['eef_pose'][i],'actor_pose':pose,'contact_pairs':pairs})
        contacts=[]
        for p in pairs:
            c=classify_contact_pair_physical_hit_v8(p)
            if 'f3_main_bottle' in (p['body_a'],p['body_b']) and c['physical_hit_for_gate']:
                contacts.append({'bodies':[p['body_a'],p['body_b']],'impulse_norm_sum':p['impulse_norm_sum'],'minimum_separation_m':min(p['point_separations'])})
        world=R.from_quat(pose[[4,5,6,3]]).apply(vertices)+pose[:3]
        summary.append({'row':i,'bottle_pose':pose.tolist(),'native_bottle_min_z_m':float(world[:,2].min()),'contacts':contacts})
    witness=hold_witness(rows,selected_links=['fl_link7','fl_link8'],bottle_name='f3_main_bottle',pad_name='f3_original_pad')
    counts={name:sum(any(name in c['bodies'] for c in r['contacts']) for r in summary) for name in ['table','f3_original_pad','fl_link7','fl_link8']}
    out={'schema_version':'p48_f3_006_supported_state_cpu_audit_v1','trace_sha256':sha(D/'physical_trace.npz'),
        'postclose_model_sha256':sha(D/'postclose_attached_model.json'),'hold_witness':witness,'physical_contact_frame_counts':counts,
        'rows':summary,'all250_off_support':counts['table']==counts['f3_original_pad']==0,'full_GPU_model_valid_not_verified_by_CPU':True,
        'no_source_Gate_or_physical_modification':True,'new_GPU':False}
    out['receipt_sha256']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();write_new(O/'analysis.json',out)
    print({k:v for k,v in out.items() if k!='rows'});print('minZrange',min(r['native_bottle_min_z_m'] for r in summary),max(r['native_bottle_min_z_m'] for r in summary))
    print('firstlast',summary[0],summary[-1])
if __name__=='__main__':main()
