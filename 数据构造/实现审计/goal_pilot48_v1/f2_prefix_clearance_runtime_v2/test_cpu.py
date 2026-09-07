import copy,json,os,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .certificate import capture_native_grasp,state_binding,choose_mode,verify_certificate,escape_gate,VERSION,digest,matrix
from .models import postclose_sequence,LiveBackend
from .pair_model import ClearancePairWorld
from . import runtime
from goal_pilot48_v1.f2_goal_root_runtime_v1.spec import A,W

def fixture():
    d=W/'Robotwin2/datasets/p48_f2_prefix_001';capture=json.loads((d/'prefix_open_model.json').read_text(encoding='utf-8'));shapes=capture['world']['shapes']
    table=next(s for s in shapes if s['name']=='table__0');B=matrix(table['actor_world_pose'])@matrix(table['shape_local_pose'])@np.linalg.inv(matrix(table['solver_pose']))
    import transforms3d as t3d
    base=np.r_[B[:3,3],t3d.quaternions.mat2quat(B[:3,:3])].tolist();rows=[]
    velocity_fields=[('role_actor_linear_velocities','role_object_linear_velocity__main_can'),('role_actor_angular_velocities','role_object_angular_velocity__main_can'),
      ('role_actor_linear_velocity_measured','role_object_linear_velocity_measured__main_can'),('role_actor_angular_velocity_measured','role_object_angular_velocity_measured__main_can'),
      ('role_actor_component_linear_velocities','role_object_component_linear_velocity__main_can'),('role_actor_component_angular_velocities','role_object_component_angular_velocity__main_can'),
      ('role_actor_component_linear_velocity_measured','role_object_component_linear_velocity_measured__main_can'),('role_actor_component_angular_velocity_measured','role_object_component_angular_velocity_measured__main_can')]
    with np.load(d/'partial_prefix_trace.npz',allow_pickle=False) as z:
        data={k:np.array(z[k]) for k in ['eef_pose','role_object_pose__main_can','selected_contact_actor_name','contact_pairs_json','joint_qpos','planner_queries_json',*[key for _,key in velocity_fields]]}
        for i in range(len(data['eef_pose'])-50,len(data['eef_pose'])):
            row={'eef':data['eef_pose'][i],'role_actor_poses':{'main_can':data['role_object_pose__main_can'][i]},'selected_contact_actor_name':str(data['selected_contact_actor_name'][i]),
              'contact_pairs':json.loads(str(data['contact_pairs_json'][i]))}
            for field,key in velocity_fields:row[field]={'main_can':data[key][i].copy()}
            rows.append(row)
        q=data['joint_qpos'][-1].copy();plans=json.loads(data['planner_queries_json'].item());grasp=list(plans[-1]['goal_eef_pose'])
    lift=list(grasp);lift[2]+=.12;targets=[{'pose':grasp,'segment_id':'pregrasp'},{'pose':grasp,'segment_id':'grasp'},{'pose':lift,'segment_id':'lift12'}]
    scene=types.SimpleNamespace(trace=rows,_cmf_scene_instance_id='CPU_REPLAY_PREFIX001',_cmf_goal_prefix_output=str(W/'Robotwin2/tmp/CPU_clearance_unused'),planner_query_count=2,
      selected_gripper_links=lambda:['fl_link7','fl_link8'],robot=types.SimpleNamespace(left_entity=types.SimpleNamespace(get_qpos=lambda:q)))
    can=copy.deepcopy([s for s in shapes if s['role']=='held_can'])
    for s in can:
        T=np.linalg.inv(B)@matrix(rows[-1]['role_actor_poses']['main_can'])@matrix(s['shape_local_pose']);s['solver_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist();s['actor_world_pose']=rows[-1]['role_actor_poses']['main_can'].tolist()
    export={'shapes':[s for s in shapes if s['role']!='held_can']}
    with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'CPU_FIXTURE_NO_GPU'}):
        binding=state_binding(scene,{},export,can,targets)
    witness=capture_native_grasp(scene,export,can,base,binding)
    return scene,export,can,base,targets,witness,binding

def evidence(witness,binding,valid=False):
    checks={name:{'valid':valid,'status':None if valid else 'MotionGenStatus.INVALID_START_STATE_WORLD_COLLISION','model_instance_id':i} for i,name in enumerate(('motion_gen','motion_gen_batch'))}
    overlaps={}
    for name,row in checks.items():
        v={'sphere_source':'CURRENT_FRESHLY_FITTED_MODEL_KINEMATICS','binding':binding,'model_instance_id':row['model_instance_id'],
           'negative_pairs':[{'link':'attached_can','obstacle':'table__0','clearance_m':-.004}]}
        v['receipt_sha256']=digest(v);overlaps[name]=v
    return {'native':witness,'full_checks':checks,'overlaps':overlaps}

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=fixture()
    def test_real_saved_state_positive_gap_no_fake_table_contact(self):
        w=self.data[5];self.assertTrue(w['pass']);self.assertGreater(w['native_gap_m'],.0001);self.assertEqual(w['actual_table_contact_frames'],0);self.assertIsNone(w['positive_gap_upper_bound'])
        self.assertTrue(all(v['component_linear_measured'] for v in w['velocity_evidence']))
        self.assertTrue(all(not v['primary_linear_measured'] for v in w['velocity_evidence']))
    def test_full_valid_never_uses_pair(self):
        _,_,_,_,_,w,b=self.data;e=evidence(w,b,True);self.assertEqual(choose_mode(w,e['full_checks'],{},b),'FULL_WORLD')
    def test_inactive_command_nan_not_physical_binding(self):
        scene,export,can,base,targets,w,b=copy.deepcopy(self.data)
        for row in scene.trace:row['inactive_planner_goal']=np.full(7,np.nan)
        with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'CPU_FIXTURE_NO_GPU'}):
            actual=state_binding(scene,{},export,can,targets)
        self.assertEqual(actual,b)
        self.assertEqual(capture_native_grasp(scene,export,can,base,b)['receipt_sha256'],w['receipt_sha256'])
        scene.trace[-1]['eef'][0]+=.001
        with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'CPU_FIXTURE_NO_GPU'}):
            self.assertNotEqual(state_binding(scene,{},export,can,targets),b)
    def test_pair_only_fresh_exclusive_negative_pairs(self):
        *_,w,b=self.data;e=evidence(w,b)
        self.assertEqual(choose_mode(w,e['full_checks'],e['overlaps'],b),'F2_CAN_TABLE_PADDING_UPWARD_ONLY')
        bad=copy.deepcopy(e);bad['overlaps']['motion_gen']['negative_pairs'].append({'link':'fl_link7','obstacle':'table__0'})
        x=bad['overlaps']['motion_gen'];x['receipt_sha256']=digest({k:v for k,v in x.items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):choose_mode(w,bad['full_checks'],bad['overlaps'],b)
    def test_tampered_stale_certificate_or_overlap_rejected(self):
        *_,w,b=self.data
        with self.assertRaises(ValueError):verify_certificate({**w,'pass':False},b)
        for key,value in [('scene_instance_id','stale'),('model_cfg_sha256','bad'),('world_sha256','bad'),('joint_qpos_sha256','bad')]:
            with self.assertRaises(ValueError):verify_certificate(w,{**b,key:value})
        e=evidence(w,b);e['overlaps']['motion_gen']['model_instance_id']=99
        with self.assertRaises(ValueError):choose_mode(w,e['full_checks'],e['overlaps'],b)
    def test_original_OR_selected_semantics_and_missing_velocity(self):
        scene,export,can,base,targets,w,b=copy.deepcopy(self.data)
        for r in scene.trace:r['contact_pairs']=[p for p in r['contact_pairs'] if 'fl_link8' not in (p['body_a'],p['body_b'])]
        self.assertTrue(capture_native_grasp(scene,export,can,base,b)['pass'])
        scene.trace[-1]['role_actor_component_linear_velocity_measured']['main_can']=False
        self.assertFalse(capture_native_grasp(scene,export,can,base,b)['pass'])
    def test_model_disagreement_and_self_failure_rejected(self):
        *_,w,b=self.data;e=evidence(w,b)
        e['full_checks']['motion_gen']['valid']=True
        with self.assertRaises(ValueError):choose_mode(w,e['full_checks'],e['overlaps'],b)
        e=evidence(w,b);e['full_checks']['motion_gen']['status']='SELF_COLLISION'
        with self.assertRaises(ValueError):choose_mode(w,e['full_checks'],e['overlaps'],b)
    def test_actual_plan_native_shape_start_and_no_descent(self):
        w=self.data[5];v=np.asarray(w['native_world_vertices']);good=np.array([v,v+[0,0,.06],v+[0,0,.12]])
        self.assertTrue(escape_gate(good,w)['pass'])
        with self.assertRaises(ValueError):escape_gate(np.array([0]),w)
        bad=good.copy();bad[1,:,2]-=.07;self.assertFalse(escape_gate(bad,w)['pass'])
        bad=good.copy();bad[0,:,0]+=.01;self.assertFalse(escape_gate(bad,w)['pass'])
    def test_sequence_full_pair_and_failure_before_plan(self):
        *_,w,b=self.data
        class Backend:
            def __init__(self,valid=False,pair=True,screen=True):self.e=evidence(w,b,valid);self.calls=[];self.pair=pair;self.screen=screen
            def prepare_full(self):self.calls.append('full');return self.e
            def current_binding(self):return b
            def record_mode(self,*a):pass
            def install_pair(self,e):self.calls.append('pair');return {k:{'valid':self.pair} for k in ('motion_gen','motion_gen_batch')}
            def plan_lift(self,t):self.calls.append('plan');return {'pass':True,'controls':[{}],'segment_receipts':[{}]}
            def screen_actual_plan(self,*a):self.calls.append('screen');return {'pass':self.screen}
        p={'controls':[{},{}],'segment_receipts':[{},{}]};targets=[{}, {}, {}]
        backend=Backend(True);self.assertEqual(len(postclose_sequence(backend,p,targets)['controls']),3);self.assertNotIn('pair',backend.calls)
        backend=Backend();postclose_sequence(backend,p,targets);self.assertEqual(backend.calls,['full','pair','plan','screen'])
        backend=Backend(pair=False)
        with self.assertRaises(RuntimeError):postclose_sequence(backend,p,targets)
        self.assertNotIn('plan',backend.calls)
    def test_parent_sources_and_runner_globals_unchanged(self):
        from goal_pilot48_v1.f2_goal_root_runtime_v1 import prefix_runner as old
        before=old.build_prefix_spec;fn=runtime.private_entry();self.assertIs(old.build_prefix_spec,before)
        self.assertIsNot(fn.__globals__,old.run.__globals__)

if __name__=='__main__':unittest.main()
