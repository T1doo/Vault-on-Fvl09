"""Build display-only F2/F3 scene specifications from actual diagnostic evidence."""
import json
from pathlib import Path
from goal_pilot48_v1.hd_state_replay_v1.runtime import load_trace,sha
ROOT=Path(__file__).resolve().parent
DATA=Path('/nfs_share/lijunhui/Robotwin2/datasets')

def build():
    f2=DATA/'p48_f2_inside_carry_revision1_002'
    f3=DATA/'p48_f3_one_sided_micro_001'
    f2_source=f2/'qualification_spec.json';f3_source=f3/'scene_binding.json'
    second=json.loads(f2_source.read_text(encoding='utf-8'))
    third=json.loads(f3_source.read_text(encoding='utf-8'))
    if third['asset_model_id']!=13:raise ValueError('default F3 render scene would use a different asset')
    from controlled_multi_future.f2_official_asset_compatibility_matrix_v3 import validate_frozen_asset_layout_binding_v3
    validate_frozen_asset_layout_binding_v3(second['planned']['f2_asset_layout_binding_v3'])
    entries=[('F2',f2/'qualification_trace.npz',second['planned'],f2_source,'PREINSERT_IK_FAILED'),
             ('F3',f3/'physical_trace.npz',{'family':'F3','seed':third['scene_seed'],
               'purpose':'saved_state_render_only','source_scene_binding_receipt_sha256':third['receipt_sha256'],
               'default_asset13_confirmed':True,'formal_data':False},f3_source,'POSTLIFT_GRASP_GATE_FAILED')]
    result=[]
    for family,path,spec,source,status in entries:
        q,t,roles=load_trace(path)
        expected={'main_can','box','scale','stand'} if family=='F2' else {'bottle','original_pad','central_marker'}
        if set(roles)!=expected:raise ValueError('actual diagnostic role coverage mismatch')
        result.append({'family':family,'trace_path':str(path),'trace_sha256':sha(path),'states':len(q),
            'label':family+'_DIAGNOSTIC_'+status,'program_id':family+'_diagnostic','pilot':'diagnostic',
            'realization':'saved_state_diagnostic','root_id':path.parent.name,'raw_id':None,
            'display_only':True,'new_collection':False,'source_failure_status':status,
            'planned_spec':spec,'scene_source_path':str(source),'scene_source_sha256':sha(source)})
    return result

if __name__=='__main__':
    from realization_utf8_io_v1 import write_new
    directory=ROOT/'hd_diagnostic_input_specs_v1';directory.mkdir(exist_ok=True)
    items=build()
    for item in items:
        spec=item.pop('planned_spec');path=directory/(item['family']+'_scene.json')
        write_new(path,spec);item['planned_spec_path']=str(path);item['planned_spec_sha256']=sha(path)
    write_new(directory/'catalog.json',{'items':items,'not_accepted_pilot_inputs':True,'new_GPU_or_scene':False})
    print([(i['family'],i['states']) for i in items])
