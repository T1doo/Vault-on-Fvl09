"""Draft planned slots only. Does not construct a simulator or authorize dispatch."""
import argparse,collections,hashlib,json
PROGRAMS={'F1':['red','green','blue'],'F2':['inside','on','beside'],'F3':['VVHH','VHVH','VHHV'],'F4':['ABC','ACB','BAC']}
REALIZATIONS=['r_pc','r_inv_path','r_inv_motion']
SPLIT=[('train','clear'),('train','medium'),('train','medium'),('train','medium'),('train','crowded'),('validation','medium'),('validation','medium'),('test','clear'),('test','medium'),('test','crowded')]
def generate():
    slots=[]
    for f,programs in PROGRAMS.items():
        for i in range(14):
            reserve=i>=10
            # Physical translation is distinct, bounded, and only proposed; not a measured current hash.
            parameters={'group_translation_xy_m':[round(0.002*(i+1),4),round(0.001*((i%3)-1),4)],'asset_size_multiplier':1.0,'appearance_rotation':i%3,'projected_spacing_width_ratio':{'clear':2.2,'medium':1.75,'crowded':1.35}.get(SPLIT[i][1] if not reserve else '',None)}
            slots.append({'root_slot_id':f'{f}_{i+1:06d}' if not reserve else f'{f}_reserve_{i-9:02d}','family':f,'seed':2026091000+int(f[1])*100+i,'generator_version':'formal_batch_draft_v1','split':SPLIT[i][0] if not reserve else 'inherit_failed_slot','difficulty':SPLIT[i][1] if not reserve else 'inherit_failed_slot','reserve_rank':i-9 if reserve else None,'status':'reserve_pending_activation' if reserve else 'planned_pending_feasibility','scene_parameters_proposed':parameters,'program_templates':programs,'realizations':REALIZATIONS,'expected_cells':[{'intent':p,'realization':r} for p in programs for r in REALIZATIONS],'current_sha256':None,'anchor_sha256':None,'candidate_sha256':None,'prefix_sha256':None,'physics_verified':False,'split_near_duplicate_gate':'reject cross-split scene similarity before freeze; no promotion from pilot'})
    return {'version':'formal_batch_draft_v1','execution_authorized':False,'allowed_physical_gpu_indices':list(range(8)),'family_order':list(PROGRAMS),'slots':slots,'first_wave':['F1_000001','F1_000002'],'physics_entry_status':'NOT_IMPLEMENTED_PENDING_ADAPTER_EXTENSION'}
def validate(p):
    slots=p['slots'];assert len(slots)==56 and len({s['root_slot_id'] for s in slots})==56
    signatures=set()
    for s in slots:
        assert s['program_templates']==PROGRAMS[s['family']]
        assert set(s['realizations'])==set(REALIZATIONS)
        assert {(x['intent'],x['realization']) for x in s['expected_cells']}=={(a,b) for a in PROGRAMS[s['family']] for b in REALIZATIONS} and len(s['expected_cells'])==9
        assert all(s[k] is None for k in ['current_sha256','anchor_sha256','candidate_sha256','prefix_sha256'])
        signature=(s['family'],json.dumps(s['scene_parameters_proposed'],sort_keys=True));assert signature not in signatures;signatures.add(signature)
    for f in PROGRAMS:
        primary=[s for s in slots if s['family']==f and s['reserve_rank'] is None]
        assert collections.Counter((s['split'],s['difficulty']) for s in primary)==collections.Counter(SPLIT)
        assert [s['reserve_rank'] for s in slots if s['family']==f and s['reserve_rank'] is not None]==[1,2,3,4]
    return {'pass':True,'primary':40,'reserve':16,'formal_target':360,'physical_scene_or_current_uniqueness_verified':False}
if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--output');p.add_argument('--check');a=p.parse_args();v=json.loads(Path(a.check).read_text()) if a.check else generate();result=validate(v)
    if a.output:Path(a.output).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result))
