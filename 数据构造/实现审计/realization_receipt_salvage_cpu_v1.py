"""Read-only trace reconciliation; does not recreate or execute a GPU scene."""
import ast,copy,importlib,inspect,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
W=Path('/nfs_share/lijunhui');A=W/'Vault-on-Fvl09/数据构造/实现审计'
sys.path.insert(0,str(A));sys.path.insert(0,str(A/'realization_batch_runtime_v1_2'))
from catalog import read,sha,seal,build_catalog,source_branch
from realization_parent_f1_bridge_cpu_v1 import load_parent_adapter,NAME

def read_complete_fields(path):
    text=Path(path).read_text(encoding='utf-8');decoder=json.JSONDecoder();pos=1;fields={};key=None
    if not text.startswith('{'):raise ValueError('not a JSON object prefix')
    while True:
        while pos<len(text) and text[pos] in ' \n\r\t,':pos+=1
        if pos<len(text) and text[pos]=='}':return fields,None
        try:
            key,pos=decoder.raw_decode(text,pos)
            while text[pos].isspace():pos+=1
            if text[pos]!=':':raise ValueError('missing colon')
            pos+=1
            while pos<len(text) and text[pos].isspace():pos+=1
            value,pos=decoder.raw_decode(text,pos);fields[key]=value
        except (ValueError,IndexError):return fields,key

class RecordedActor:
    def __init__(self,name,pose):self.name=name;self.pose=np.asarray(pose)
    def get_name(self):return self.name
    def get_pose(self):return SimpleNamespace(p=self.pose[:3],q=self.pose[3:])

def original_verifier_tail():
    load_parent_adapter(W/'Robotwin2/tmp/salvage_no_scene')
    module=importlib.import_module(NAME+'.family_runners_v3_3')
    source=inspect.getsource(module);tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='F1ControllerV3_3')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='execute_frozen_suffix_spec')
    start=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='inside')
    end=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='semantic')
    statements=copy.deepcopy(fn.body[start:end+1]);names=['scene','actor','non_targets','baseline','stages','spec','execution_receipts','role']
    wrapper=ast.FunctionDef(name='recompute_verifier_only',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in names],kwonlyargs=[],kw_defaults=[],defaults=[]),
        body=statements+[ast.Return(value=ast.Name(id='semantic',ctx=ast.Load()))],decorator_list=[])
    compiled=ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[]));namespace=dict(vars(module))
    exec(compile(compiled,str(Path(module.__file__).resolve()),'exec'),namespace)
    return namespace['recompute_verifier_only'],seal({'source_file':str(Path(module.__file__).resolve()),'source_file_sha256':sha(module.__file__),
        'class':'F1ControllerV3_3','method':fn.name,'extracted_verifier_statement_start_line':fn.body[start].lineno,
        'extracted_verifier_statement_end_line':fn.body[end].end_lineno,'predicate_ast_unchanged':True,'physical_execution_statements_excluded':True})

def recompute(branch_dir,program,*,cpu_negative_fixture=None):
    directory=Path(branch_dir);role=program['target_role'];verify,source=original_verifier_tail()
    artifact=read(directory/'variant_suffix_artifact/frozen_suffix_artifact.json') if (directory/'variant_suffix_artifact').exists() else read(directory.parent.parent/'suffix_artifacts'/program['program_id']/'frozen_suffix_artifact.json')
    with np.load(directory/'trace_source.npz',allow_pickle=False) as z:
        steps=z['step_index'];assert np.array_equal(steps,np.arange(len(steps)))
        queries=json.loads(str(z['planner_queries_json'].item()));by={q['source']:q for q in queries}
        stage_indices={'prefix_boundary':by['target_pregrasp']['start_step'],'after_grasp':by['target_lift_mid']['start_step'],
            'after_transport':by['release']['end_step'],'after_release':by['retreat']['start_step'],'after_rest':len(steps)-1}
        poses={r:z['role_object_pose__'+r] for r in ('red','green','blue','common_box')}
        non_targets={r:RecordedActor('f1_'+r+'_block',poses[r][-1]) for r in ('red','green','blue') if r!=role}
        stages={label:{r:poses[r][index,:3].copy() for r in non_targets} for label,index in stage_indices.items()}
        actor=RecordedActor('f1_'+role+'_block',poses[role][-1]);box=RecordedActor('f1_common_plasticbox',poses['common_box'][-1])
        linear=z['role_object_linear_velocity__'+role][-50:];angular=z['role_object_angular_velocity__'+role][-50:]
        eeflin=z['eef_linear_velocity'][-50:];eefang=z['eef_angular_velocity'][-50:];contacts=z['contact_pairs_json'][-50:]
        rows=[{'role_actor_linear_velocities':{role:lv},'role_actor_angular_velocities':{role:av},'eef_linear_velocity':el,'eef_angular_velocity':ea,'contact_pairs':json.loads(str(c))} for lv,av,el,ea,c in zip(linear,angular,eeflin,eefang,contacts)]
        if cpu_negative_fixture=='missing_support':
            for row in rows:row['contact_pairs']=[]
        elif cpu_negative_fixture=='outside_cavity':actor.pose=actor.pose.copy();actor.pose[0]+=.3
        elif cpu_negative_fixture is not None:raise ValueError('unknown CPU fixture')
        # Exact Base_Task delegation -> Robot.is_left_gripper_open predicate.
        gripper=float(z['gripper_command'][-1,0]);eef=z['dual_eef_pose'][-1,:7]
        scene=SimpleNamespace(trace=rows,trace_role_actors={role:actor},box=box,robot=SimpleNamespace(get_left_ee_pose=lambda:eef),is_left_gripper_open=lambda:gripper>.8)
        receipts=[{'segment_id':t['segment_id'],'source':'trace-query interval derived; not original ephemeral execution receipt'} for t in artifact['execution_spec']['targets']]
        semantic=verify(scene,actor,non_targets,stages['prefix_boundary'],stages,artifact['execution_spec'],receipts,role)
    return semantic,source,stage_indices

def run_checks():
    checks=[]
    for cohort in build_catalog()['cohorts'][:2]:
        for cell in cohort['cells']:
            directory=Path(cell['parent_root'])/'branches'/cell['program']['program_id'];semantic,source,stages=recompute(directory,cell['program'])
            original=source_branch(cell)['verifier']['family_semantic_verifier']
            assert semantic['checks']==original['checks'],cell['cell_id']
            assert semantic['pass']==original['pass']
            checks.append({'cell_id':cell['cell_id'],'all_nine_original_predicates_equal':True})
    target=W/'Robotwin2/datasets/cmf_realization_recovery_v1_2/F1_A_path/branches/F1-red'
    cell=build_catalog()['cohorts'][0]['cells'][0];semantic,source,stages=recompute(target,cell['program'])
    fields,incomplete=read_complete_fields(target/'receipt.provisional.json')
    from controlled_multi_future.raw_writer import verify_raw_artifact_integrity
    from controlled_multi_future.development_video_capture_v1 import validate_development_trajectory_mp4_receipt_v1
    raw=verify_raw_artifact_integrity(target/'raw');video=validate_development_trajectory_mp4_receipt_v1(fields['development_video_receipt'])
    assert raw['pass'] and video['pass'];manifest=raw['manifest'];query_count=manifest['provenance']['new_planner_queries']
    assert query_count==11 and len(manifest['provenance']['planner_queries'])==11
    from controlled_multi_future.frozen_suffix_artifact_v1 import load_frozen_suffix_artifact
    from pipeline import variations_from_trace
    _,_,controls=load_frozen_suffix_artifact(target/'variant_suffix_artifact')
    with np.load(target/'trace_source.npz',allow_pickle=False) as z:
        queries=json.loads(str(z['planner_queries_json'].item()));ids=z['planner_query_id'];active=z['planner_goal_active'];effective=z['controller_effective_setpoint']
        control_checks=[]
        for q,c in zip(queries,controls):
            indices=np.flatnonzero((ids[:,0]==q['query_id'])&active[:,0])
            good=np.array_equal(effective[indices,:6],c['position']) and np.array_equal(effective[indices,12:18],c['velocity'])
            assert good,q['source'];control_checks.append({'segment_id':q['source'],'recorded_effective_position_velocity_equal_frozen_controls':True,'steps':len(indices)})
        recorded_scene=SimpleNamespace(planner_queries=queries,trace=[{'eef':e,'timestamp':t,'planner_query_id':i,'planner_goal_active':a} for e,t,i,a in zip(z['eef_pose'],z['timestamp'],ids,active)])
        variation=variations_from_trace(cell,{'semantic_verifier':semantic},recorded_scene,[])
        assert variation['pass']
    negative={}
    for fault in ('missing_support','outside_cavity'):
        bad,_,_=recompute(target,cell['program'],cpu_negative_fixture=fault)
        assert bad['pass'] is False;negative[fault]='correctly_rejected'
    return seal({'schema_version':'cmf_realization_trace_reconciliation_cpu_v1','original_six_branch_regressions':checks,'original_predicate_source':source,
        'target_directory':str(target),'target_trace_sha256':sha(target/'trace_source.npz'),'raw_integrity_pass':raw['pass'],'video_integrity_pass':video['pass'],
        'observed_raw_trajectory_count':1,'observed_raw_action_count':manifest['action_count'],'reconciled_planner_queries':query_count,
        'accounting_basis':'saved live raw provenance count plus eleven matching executable query receipts; old failed job terminal remains unchanged',
        'complete_partial_receipt_fields':list(fields),'incomplete_field':incomplete,'scene_cleanup_pass':fields['cleanup']['cleanup_safety_pass'],
        'anchor_equivalence':fields['anchor_equivalence'],'recomputed_family_semantic_verifier':semantic,'stage_trace_indices':stages,
        'recomputed_realized_variation':variation,'control_stream_reconciliation':control_checks,'negative_cpu_fixtures':negative,
        'cpu_derived_not_original_ephemeral_receipt':True,'new_gpu_scenes':0,'new_raw_rollouts':0,'acceptance_registration_created':False})

if __name__=='__main__':
    from controlled_multi_future.canonical_artifact import canonical_jsonable
    print(json.dumps(canonical_jsonable(run_checks()),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
