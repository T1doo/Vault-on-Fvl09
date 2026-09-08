"""CPU audit helpers only; not installed into the frozen collector."""
import copy,itertools,json
from pathlib import Path
import numpy as np

def classify(point,*,box_lower,box_upper,scale_center,scale_half_xy,height_tolerance,reference_xy,annulus,beside_z,reference_top_contact):
 p=np.asarray(point,float)
 inside=bool(np.all(p>=box_lower) and np.all(p<=box_upper))
 on=bool(np.all(abs(p[:2]-scale_center[:2])<=scale_half_xy) and abs(p[2]-scale_center[2])<=height_tolerance)
 if annulus is None:
  beside=False if reference_top_contact else None
 else:
  r=np.linalg.norm(p[:2]-reference_xy);beside=bool(annulus[0]<=r<=annulus[1] and abs(p[2]-beside_z)<=height_tolerance and not reference_top_contact)
 vals={'inside':inside,'on':on,'beside':beside}
 return {'predicates':vals,'exclusive':None if beside is None else sum(vals.values())==1}

def model_inputs(sample):
 # No implicit projection of target or oracle-bearing dictionaries.
 if set(sample)!={'inputs','supervision','audit'}:raise ValueError('three separate envelopes required')
 if set(sample['inputs'])!={'rgb','state','future','candidate_set'}:raise ValueError('model input whitelist violated')
 for name in ('rgb','state','future','candidate_set'):
  if sample['inputs'][name] is None:raise ValueError('missing real '+name)
 s=np.asarray(sample['inputs']['state']);f=np.asarray(sample['inputs']['future']);rgb=np.asarray(sample['inputs']['rgb'])
 if s.shape!=(76,) or f.ndim!=2 or f.shape[1]!=26 or not np.isfinite(s).all() or not np.isfinite(f).all():raise ValueError('shape/finite')
 if rgb.ndim not in (3,4) or rgb.shape[-1]!=3 or rgb.dtype!=np.uint8:raise ValueError('RGB provenance/shape')
 candidates=sample['inputs']['candidate_set']
 if not isinstance(candidates,list) or len(candidates)!=3:raise ValueError('three candidates required')
 for c in candidates:
  if not isinstance(c,dict) or set(c)!={'family','relation','object_ref'}:raise ValueError('candidate schema')
  if any(not isinstance(v,str) or not v for v in c.values()):raise ValueError('candidate values')
 if len({tuple(sorted(c.items())) for c in candidates})!=3:raise ValueError('duplicate candidates')
 # Validates structure only; real provenance is separately audited and never fabricated.
 return copy.deepcopy(sample['inputs'])

def run():
 args=dict(box_lower=np.array([-.29,-.29,.76]),box_upper=np.array([-.07,-.07,.86]),scale_center=np.array([-.02,-.18,.76]),scale_half_xy=np.array([.04,.06]),height_tolerance=.012,reference_xy=np.array([.08,-.18]),annulus=(.08,.20),beside_z=.75,reference_top_contact=False)
 high=classify([-.18,-.18,1.5],**args)
 top=classify([.08,-.18,.825],**{**args,'reference_top_contact':True})
 # Artificial overlapping regions to exercise exactly-one; not a real-scene result.
 overlap=classify([-.09,-.18,.78],**{**args,'scale_center':np.array([-.09,-.18,.78])})
 missing=classify([.20,-.18,.75],**{**args,'annulus':None})
 assert not high['predicates']['inside'];assert not top['predicates']['beside'];assert not overlap['exclusive'];assert missing['exclusive'] is None
 result={'schema':'boundary_negative_tests_v1','synthetic_only':True,'production_thresholds_changed':False,'annulus_numbers':'synthetic fixture only; never used to reaccept real data','checks':{'above_box_rejected':not high['predicates']['inside'],'reference_top_not_beside':not top['predicates']['beside'],'overlap_not_exclusive':not overlap['exclusive'],'missing_region_not_default_pass':missing['exclusive'] is None},'examples':{'above_box':high,'stand_top':top,'overlap':overlap,'missing_annulus':missing}}
 # Actual row0/future from every trace; missing real RGB deliberately blocks full export.
 results=[]
 for p in sorted(Path(__file__).parent.glob('*_cells.json')):
  for c in json.loads(p.read_text()):
   sample={'inputs':{'rgb':None,'state':c['row0']['joint_qpos']+c['row0']['joint_qvel'],'future':None,'candidate_set':None},'supervision':{'historical_label':c['cell'].split('/')[1]},'audit':{'trace':c['trace']}}
   with np.load(c['trace'],allow_pickle=False) as z:sample['inputs']['future']=z['controller_effective_setpoint'][1:]
   try:model_inputs(sample);raise AssertionError('must block missing RGB')
   except ValueError as e:results.append({'cell':c['cell'],'actual_state_76':len(sample['inputs']['state'])==76,'actual_future_26':sample['inputs']['future'].shape[1]==26,'full_export_blocked':True,'reason':str(e),'target_in_inputs':False})
 result['real_data_partial_export']=results;result['real_complete_rgb_state_future_candidate_exports']=0
 fixture={'inputs':{'rgb':np.zeros((1,1,3),dtype=np.uint8),'state':[0.0]*76,'future':[[0.0]*26],'candidate_set':[{'family':'F2','relation':r,'object_ref':'synthetic object'} for r in ['inside','on','beside']]},'supervision':{'target':'synthetic only'},'audit':{'path':'synthetic only'}}
 assert set(model_inputs(fixture))=={'rgb','state','future','candidate_set'}
 contaminated=copy.deepcopy(fixture);contaminated['inputs']['target']='answer'
 try:model_inputs(contaminated);raise AssertionError('target must be rejected')
 except ValueError:pass
 result['checks']['synthetic_envelope_separates_supervision_audit']=True
 result['checks']['target_in_inputs_rejected']=True
 result['unit_tests_pass']=all(result['checks'].values());Path(__file__).with_name('BOUNDARY_CHECKS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':run()
