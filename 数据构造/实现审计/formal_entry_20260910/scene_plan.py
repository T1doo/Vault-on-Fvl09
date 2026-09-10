"""Strict CPU scene resolution and deterministic barrier-based reserve allocation."""
import argparse,copy,fcntl,hashlib,itertools,json,math,os
from pathlib import Path
import numpy as np
VERSION='formal_scene_v2'
REALIZATIONS=('r_pc','r_inv_path','r_inv_motion')
SPLITS=(('train','clear'),('train','medium'),('train','medium'),('train','medium'),('train','crowded'),('validation','medium'),('validation','medium'),('test','clear'),('test','medium'),('test','crowded'))
FAMILIES=('F1','F2','F3','F4')
PROGRAMS={'F1':('F1-red','F1-green','F1-blue'),'F2':('inside','on','beside'),'F3':('VVHH','VHVH','VHHV'),'F4':('F4-ABC','F4-ACB','F4-BAC')}
RATIOS={'clear':2.2,'medium':1.75,'crowded':1.35}
SLOT_KEYS={'root_id','family','rank','reserve_rank','seed','split','difficulty','generator_version','parameters','realizations','current_sha256','candidate_sha256','prefix_sha256'}
PARAM_KEYS={'translation_xy_m','scale_multiplier','permutation','distractor_band_y_m'}

def hash_json(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def finite(value):
 if isinstance(value,dict):
  for v in value.values():finite(v)
 elif isinstance(value,(list,tuple)):
  for v in value:finite(v)
 elif isinstance(value,float):require(math.isfinite(value),'nonfinite value')
def number(x):return type(x) in (int,float) and math.isfinite(x)
def validate_slot(s):
 require(type(s) is dict and set(s)==SLOT_KEYS,'slot schema')
 require(s['family'] in FAMILIES and type(s['root_id']) is str and s['root_id'].startswith(s['family']+'_'),'root identity')
 require(type(s['rank']) is int and 1<=s['rank']<=14,'rank')
 require(type(s['seed']) is int and s['seed']>0,'seed')
 require(s['generator_version']==VERSION,'generator version')
 require(type(s['realizations']) is list and len(s['realizations'])==3 and set(s['realizations'])==set(REALIZATIONS),'realizations must be three unique values')
 require(all(s[k] is None for k in ['current_sha256','candidate_sha256','prefix_sha256']),'unobserved hashes must be null')
 p=s['parameters'];require(type(p) is dict and set(p)==PARAM_KEYS,'unknown/missing parameter')
 require(type(p['translation_xy_m']) is list and len(p['translation_xy_m'])==2 and all(number(x) and abs(x)<=.05 for x in p['translation_xy_m']),'translation range/finite')
 require(number(p['scale_multiplier']) and p['scale_multiplier']==1.,'only source size multiplier 1 is qualified for proposal')
 require(type(p['permutation']) is int and 0<=p['permutation']<3,'permutation')
 require(number(p['distractor_band_y_m']) and .1<=p['distractor_band_y_m']<=.45,'distractor band')
 if s['reserve_rank'] is None:require((s['split'],s['difficulty']) in SPLITS,'split difficulty')
 else:require(type(s['reserve_rank']) is int and 1<=s['reserve_rank']<=4 and s['split']==s['difficulty']=='inherit_failed_slot','inactive reserve')
 finite(s);return s

def generate():
 slots=[]
 for f in FAMILIES:
  for i in range(14):
   split,diff=SPLITS[i] if i<10 else ('inherit_failed_slot','inherit_failed_slot')
   band={'train':.15,'validation':.28,'test':.41}.get(split,.15)
   translation=([round(.002*(i%5),4),0.] if split=='train' else [round(-.045+.002*(i%5),4),.025] if split=='validation' else [round(.043+.001*(i%5),4),-.025] if split=='test' else [round(.001*(i-10),4),.0])
   slots.append({'root_id':f'{f}_{i+1:06d}','family':f,'rank':i+1,'reserve_rank':None if i<10 else i-9,'seed':2026091000+100*int(f[1])+i,'split':split,'difficulty':diff,'generator_version':VERSION,'parameters':{'translation_xy_m':translation,'scale_multiplier':1.,'permutation':i%3,'distractor_band_y_m':band},'realizations':list(REALIZATIONS),'current_sha256':None,'candidate_sha256':None,'prefix_sha256':None})
 return {'schema':VERSION,'allowed_physical_gpu_indices':list(range(8)),'execution_authorized':False,'slots':slots,'reserve_policy':'barrier_terminal_batch_then_failed_primary_rank; terminal order ignored','near_duplicate_threshold_m':.035}

def role(name,xyz,size=(.044,.044,.044),asset='primitive_box',color=(.5,.5,.5),dynamic=True,q=(1,0,0,0)):
 return {'role':name,'asset':asset,'pose':[float(x) for x in xyz]+list(q),'size':list(size),'color':list(color),'dynamic':dynamic,'material_source':'source-profile default friction .5/restitution0; no physical override','mass_source':'source asset or AuditScene._box original; freeze before qualification','material':{'static_friction':.5,'dynamic_friction':.5,'restitution':0.0},'density_policy':'unchanged_source_factory'}
def camera():
 return {'required':['front_camera','head_camera','left_camera','right_camera'],'width':320,'height':240,'head':{'K':[[358.6421814,0,160],[0,358.6421814,120],[0,0,1]],'extrinsic_cv':[[1,0,0,.032],[0,-.8,-.6,.45],[0,.6,-.8,1.35]]},'wrist_binding':'native robot camera source; verify at t0','original_source':'P4 capture_metadata head calibration'}
def projected(r,cam):
 # world AABB projection: primitive boxes exact, source asset visual extent conservative.
 p=np.asarray(r['pose'][:3])+np.asarray(r.get('bbox_center_offset_world',[0,0,0]));size=np.asarray(r['size']);corners=np.array([p+size*np.array(c)/2 for c in itertools.product([-1,1],repeat=3)])
 E=np.asarray(cam['head']['extrinsic_cv']);K=np.asarray(cam['head']['K']);cv=corners@E[:,:3].T+E[:,3];require(bool((cv[:,2]>0).all()),'geometry behind camera');uv=cv@K.T;uv=uv[:,:2]/uv[:,2:];return [float(uv[:,0].min()),float(uv[:,1].min()),float(uv[:,0].max()),float(uv[:,1].max())]
def pair_ratio(a,b,cam):
 aa,bb=projected(a,cam),projected(b,cam);return abs((aa[0]+aa[2]-bb[0]-bb[2])/2)/max(aa[2]-aa[0],bb[2]-bb[0])
def place_neighbor(a,name,ratio,cam):
 b=copy.deepcopy(a);b['role']=name;b['color']=[.55,.55,.55]
 lo,hi=0.,.4
 for _ in range(60):
  d=(lo+hi)/2;b['pose'][0]=a['pose'][0]+d
  if pair_ratio(a,b,cam)<ratio:lo=d
  else:hi=d
 b['pose'][0]=a['pose'][0]+(lo+hi)/2;return b

def bind_assets(roles):
 base=Path('/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets/objects');result={}
 for asset in sorted({r['asset'] for r in roles if ':model' in r['asset']}):
  name,mid=asset.split(':model');directory=base/name;paths=[directory/f'model_data{mid}.json',directory/'points_info.json',directory/'collision'/f'base{mid}.glb',directory/'visual'/f'base{mid}.glb']
  require(all(p.is_file() for p in paths),'missing frozen asset files: '+asset)
  result[asset]={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 return result

def validate_resolved(spec):
 require(type(spec) is dict and spec.get('schema')==VERSION,'resolved schema')
 finite(spec);require(spec.get('spec_sha256')==hash_json({k:v for k,v in spec.items() if k!='spec_sha256'}),'resolved spec hash')
 require(spec.get('family') in FAMILIES,'resolved family');require(spec.get('realizations')==list(REALIZATIONS),'resolved realizations')
 require(spec['programs']==program_templates(spec['family']),'resolved program semantics')
 if spec['family']=='F1':
  from f1_disk_verifier import frozen_contract
  frozen_contract(spec)
 roles=spec['roles'];expected_roles={'F1':{'red','green','blue','common_box','similar_1','similar_2','background'},'F2':{'main_can','box','scale','stand','similar_1','similar_2','background'},'F3':{'bottle','original_pad','similar_1','similar_2','background','central_marker'},'F4':{'A','B','C','common_x','slot_A','slot_B','slot_C','common_tray','similar_1','similar_2'}}
 require({r['role'] for r in roles}==expected_roles[spec['family']],'resolved semantic role set')
 require(len({r['role'] for r in roles})==len(roles),'duplicate role')
 for r in roles:
  require(len(r['pose'])==7 and all(number(v) for v in r['pose']),'role pose');require(-.55<=r['pose'][0]<=.50 and -.40<=r['pose'][1]<=.50 and .70<=r['pose'][2]<=1.50,'role outside frozen workspace');require(len(r['size'])==3 and all(number(v) and 0<v<1 for v in r['size']),'role size')
  require(abs(sum(v*v for v in r['pose'][3:])-1)<1e-4,'quaternion');require(type(r['dynamic']) is bool,'dynamic type');require(r['material']=={'static_friction':.5,'dynamic_friction':.5,'restitution':0.0},'material outside unchanged native profile');require(r['density_policy']=='unchanged_source_factory','density policy')
 require(spec.get('asset_bindings')==bind_assets(roles),'incomplete/changed asset binding')
 require(spec['cameras']['required']==['front_camera','head_camera','left_camera','right_camera'] and spec['cameras']['width']==320 and spec['cameras']['height']==240,'camera contract')
 require(all(number(v) and 0<v<=.05 for v in spec['terminal_tolerances'].values()),'terminal tolerance range')
 for asset,files in spec['asset_bindings'].items():
  for path,expected in files.items():
   p=Path(path);require(p.resolve().is_relative_to('/nfs_share/lijunhui') and p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,'frozen asset changed')
 return spec

def program_templates(f):
 programs=[]
 for name in PROGRAMS[f]:
  if f=='F1':steps=[{'op':'pick','object':name[3:]},{'op':'place','object':name[3:],'relation':'inside','reference':'common_box'}]
  elif f=='F2':steps=[{'op':'pick','object':'main_can'},{'op':'place','object':'main_can','relation':name,'reference':{'inside':'box','on':'scale','beside':'stand'}[name]}]
  elif f=='F3':steps=[{'op':'oscillate','axis':a,'frame':'table'} for a in name]
  else:steps=[{'op':'place','object':'common_x','reference':'common_tray'}]+[{'op':'place','object':a,'reference':'slot_'+a} for a in name[3:]]
  programs.append({'program_id':name,'steps':steps,'target_role':name[3:] if f=='F1' else None})
 return programs

def resolve(slot,activation=None):
 s=copy.deepcopy(validate_slot(slot));
 if s['reserve_rank'] is not None:
  require(activation is not None and activation['reserve_root_id']==s['root_id'],'reserve requires bound activation')
  require(activation['reserve_seed']==s['seed'],'reserve seed binding')
  require((activation['split'],activation['difficulty']) in SPLITS,'activation split')
  s['split']=activation['split'];s['difficulty']=activation['difficulty'];s['parameters']['distractor_band_y_m']={'train':.15,'validation':.28,'test':.41}[s['split']]
  jitter=.001*s['reserve_rank'];s['parameters']['translation_xy_m']=[.012+jitter,0.] if s['split']=='train' else [-.047+jitter,.025] if s['split']=='validation' else [.046+jitter,-.025]
 f=s['family'];p=s['parameters'];dx,dy=p['translation_xy_m'];perm=p['permutation'];cam=camera();ratio=RATIOS[s['difficulty']];roles=[];targets={}
 if f=='F1':
  a=role('red',[-.23+dx,.02+dy,.762],color=(1,0,0));b=place_neighbor(a,'green',ratio,cam);c=place_neighbor(b,'blue',ratio,cam)
  points=[a['pose'][:3],b['pose'][:3],c['pose'][:3]]
  for j,n in enumerate(['red','green','blue']):roles.append(role(n,points[(j+perm)%3],color=tuple(int(j==k) for k in range(3))))
  roles.append(role('common_box',[-.08+dx,-.16+dy,.78],(.20,.16,.08),'062_plasticbox:model3',dynamic=False,q=(.5,.5,.5,.5)));targets={'common_box':{'relation':'inside','asset_geometry':'062_plasticbox:model3 interior from source model'}};pair=('red','green') if perm==0 else (['red','green','blue'][(-perm)%3],['red','green','blue'][(1-perm)%3])
 elif f=='F2':
  main=role('main_can',[-.22+dx,.02+dy,.755],(.07115,.07119,.09647),'071_can:model0',q=(.7071067811865476,.7071067811865476,0,0));main['bbox_center_offset_world']=[0,0,.048];roles.append(main)
  positions=[[-.30+dx,-.18+dy],[-.06+dx,-.18+dy],[.18+dx,-.18+dy]]
  for j,n in enumerate(['box','scale','stand']):
   x,y=positions[(j+perm)%3];size={'box':(.24,.24,.10),'scale':(.08,.12,.01),'stand':(.10,.10,.07)}[n];z={'box':.805,'scale':.755,'stand':.790}[n]
   roles.append(role(n,[x,y,z],size,'open_box_five_parts' if n=='box' else 'primitive_box',dynamic=False))
   if n=='box':targets['inside']={'reference':'box','support':'box_bottom','lower':[x-.11,y-.11,.760],'upper':[x+.11,y+.11,.855]}
   if n=='scale':targets['on']={'reference':'scale','support':'scale','center':[x,y,.760],'half_xy':[.04,.06]}
   if n=='stand':targets['beside']={'reference':'stand','support':'table','target':[x,y+.16,.740],'annulus':[.105,.205],'forbid_reference_top':True}
  roles.append(place_neighbor(main,'similar_1',ratio,cam));pair=('main_can','similar_1')
 elif f=='F3':
  main=role('bottle',[-.18+dx,-.06+dy,.750],(.06907,.06907,.21593),'114_bottle:model1',q=(.7071067811865476,.7071067811865476,0,0));main['bbox_center_offset_world']=[0,0,.108];roles.append(main);roles.append(role('original_pad',[-.18+dx,-.06+dy,.745],(.15,.15,.01),dynamic=False));roles.append(place_neighbor(main,'similar_1',ratio,cam));pair=('bottle','similar_1')
  targets={'central':{'position_m':[dx,-.05+dy,1.05],'orientation_policy':'preserve_actual_grasp','axis_frame':'table','V':[0,0,1],'H':[1,0,0],'amplitude_m':.047,'downward_assembly_clearance_required_m':.010,'computed_work_height_status':'must validate source grasp transform lower envelope before freeze'},'rest':{'source':'pre_action_origin_eef','position_tolerance_m':.03,'orientation_tolerance_rad':.02}}
 else:
  a=role('A',[-.20+dx,.06+dy,.762],color=(1,0,0));b=place_neighbor(a,'B',ratio,cam);c=place_neighbor(b,'C',ratio,cam);roles.extend([a,b,c]);roles.append(role('common_x',[-.31+dx,.06+dy,.762],color=(1,1,0)));pair=('A','B')
  for j,n in enumerate('ABC'):
   pose=[-.18+j*.15+dx,-.17+dy,.742];roles.append(role('slot_'+n,pose,(.07,.07,.004),'visual_box',dynamic=False));targets[n]={'object':n,'slot':'slot_'+n,'pose':pose}
  roles.append(role('common_tray',[.23+dx,.02+dy,.76],(.16,.16,.05),'008_tray:model0',dynamic=False,q=(.706527,.706483,-.0291356,-.0291767)));targets['X']={'object':'common_x','reference':'common_tray'}
 # All roles are explicit; split bands move real distractor geometry, not ID fields.
 if f in ('F1','F4'):
  roles.append(role('similar_1',[-.34,p['distractor_band_y_m'],.762]));
 if f in ('F2','F3'):
  d2=copy.deepcopy(main);d2['role']='similar_2';d2['pose'][0]=.24;d2['pose'][1]=p['distractor_band_y_m'];roles.append(d2)
 else:roles.append(role('similar_2',[.24,p['distractor_band_y_m'],.762],asset='primitive_box'))
 if f=='F3':roles.append(role('central_marker',[dx,-.05+dy,.95],(.03,.03,.03),'visual_box',dynamic=False))
 if f!='F4':roles.append(role('background',[-.42,.31,.765],(.04,.04,.05),dynamic=False))
 programs=program_templates(f)
 spec={'schema':VERSION,'root_id':s['root_id'],'family':f,'seed':s['seed'],'split':s['split'],'difficulty':s['difficulty'],'roles':roles,'targets':targets,'cameras':cam,'programs':programs,'realizations':list(REALIZATIONS),'variant_rules':{'r_pc':{'cohort':'prefix_controlled','time_scale':1.5 if f=='F3' else 1.0},'r_inv_path':{'cohort':'trajectory_invariance','postprefix_detour_m':.04 if f=='F2' else .03,'safe_horizontal_y_offset_m':.015},'r_inv_motion':{'cohort':'trajectory_invariance','time_scale':1.5 if f=='F3' else 1.0,'post_prefix_hold_frames':35 if f in ('F1','F4') else 0,'hold_frames_by_stage':{'after_transport':35,'at_support':40} if f=='F2' else {'event_negative':25,'event_positive':30,'event_return':25} if f=='F3' else {'post_prefix':35},'label_independent':True}},'difficulty_measurement':{'camera':'head_camera','pair':list(pair),'method':'horizontal projected AABB center distance / larger projected width','target_ratio':ratio,'computed_ratio':pair_ratio(next(r for r in roles if r['role']==pair[0]),next(r for r in roles if r['role']==pair[1]),cam),'render_occlusion_and_grasp_clearance':'PHYSICS_PENDING'},'physics_verified':False}
 if f=='F1':spec['scene_layout']={'object_xyz_by_role':{r['role']:r['pose'][:3] for r in roles if r['role'] in ['red','green','blue']},'common_box_pose_wxyz':next(r['pose'] for r in roles if r['role']=='common_box')}
 if f=='F2':spec['control_profile']={'route_mode':'side_then_geometry_target','lift_clearance_m':.12,'support_point_source':'source071_can collision lower localY point; native transform required'}
 spec['asset_bindings']=bind_assets(roles)
 spec['projection_evidence']={r['role']:{'bbox_xyxy':projected(r,cam),'measurement':'CPU AABB projection, not rendered visibility'} for r in roles}
 spec['terminal_tolerances']={'object_position_m':.03,'object_orientation_rad':.02,'eef_position_m':.03,'eef_orientation_rad':.02,'joint_position_rad':.03,'joint_speed_rad_s':.01,'gripper_fraction':.01,'non_task_position_m':.003,'non_task_orientation_rad':.02,'non_task_linear_speed_m_s':.02,'non_task_angular_speed_rad_s':.05}
 if f=='F1':
  from f1_disk_verifier import contract_for_f1
  spec['f1_verifier_contract']=contract_for_f1(spec)
 finite(spec);spec['spec_sha256']=hash_json(spec);return spec

def physical_signature(spec):
 fields=('role','asset','pose','size','color','dynamic','material','density_policy')
 return hash_json({'roles':[{k:r[k] for k in fields} for r in sorted(spec['roles'],key=lambda r:r['role'])],'asset_content':sorted(sorted(files.values()) for files in spec.get('asset_bindings',{}).values()),'camera':{k:spec['cameras'][k] for k in ('required','width','height','head')}})
def near_duplicate(a,b):
 if a['family']!=b['family']:return False
 # Task geometry decides split similarity; moving background alone cannot evade it.
 ignore={'similar_1','similar_2','background','central_marker'}
 aa={r['role']:r for r in a['roles'] if r['role'] not in ignore};bb={r['role']:r for r in b['roles'] if r['role'] not in ignore}
 if set(aa)!=set(bb):return False
 return all(aa[k]['asset']==bb[k]['asset'] and aa[k]['color']==bb[k]['color'] and np.linalg.norm(np.array(aa[k]['pose'][:3])-bb[k]['pose'][:3])<=.035 for k in aa)

def validate_plan(p):
 require(set(p)=={'schema','allowed_physical_gpu_indices','execution_authorized','slots','reserve_policy','near_duplicate_threshold_m'},'plan schema')
 require(p['schema']==VERSION and p['execution_authorized'] is False and p['allowed_physical_gpu_indices']==list(range(8)),'plan boundary')
 require(p['near_duplicate_threshold_m']==.035 and p['reserve_policy']=='barrier_terminal_batch_then_failed_primary_rank; terminal order ignored','frozen policy changed')
 slots=p['slots'];require(len(slots)==56,'56 slots');require(len({s['root_id'] for s in slots})==56 and len({s['seed'] for s in slots})==56,'duplicate root/seed')
 for s in slots:
  validate_slot(s);require(s['root_id']==f"{s['family']}_{s['rank']:06d}",'root/rank binding');require(s['reserve_rank']==(None if s['rank']<=10 else s['rank']-10),'reserve/rank binding')
 specs=[]
 from collections import Counter
 for f in FAMILIES:
  ss=[s for s in slots if s['family']==f];require(sorted(s['rank'] for s in ss)==list(range(1,15)),'family ranks');require(len(ss)==14,'family slot count');pr=[s for s in ss if s['reserve_rank'] is None];require(Counter((s['split'],s['difficulty']) for s in pr)==Counter(SPLITS),'split quotas');require(sorted(s['reserve_rank'] for s in ss if s['reserve_rank'] is not None)==[1,2,3,4],'reserve ranks')
  specs.extend(resolve(s) for s in pr)
 require(len({physical_signature(s) for s in specs})==40,'duplicate actual physical configuration')
 for a,b in itertools.combinations(specs,2):require(not(a['split']!=b['split'] and near_duplicate(a,b)),'cross-split near duplicate')
 f2=[s for s in specs if s['family']=='F2'];balance={}
 for n in ['box','scale','stand']:
  c=Counter(sorted([r for r in s['roles'] if r['role'] in ['box','scale','stand']],key=lambda r:r['pose'][0]).index(next(r for r in s['roles'] if r['role']==n)) for s in f2);require(sorted(c.values())==[3,3,4],'F2 position balance');balance[n]=dict(c)
 return {'pass':True,'primary':40,'reserve':16,'formal_cells':360,'F2_position_counts':balance,'physics_verified':False}

def activate_reserves(plan,path,terminals,wave='first'):
 """Persist a complete frozen wave barrier; allocate by origin primary rank.

 First barrier is primary1..2; remaining barrier primary3..10. Recovery
 barriers use all previously activated unresolved replacements in that wave.
 No partial-completion dispatch is allowed to claim a reserve.
 """
 validate_plan(plan);require(wave in ('first','remaining'),'wave identity');require(bool(terminals),'empty barrier')
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.with_suffix('.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  old=json.loads(path.read_text()) if path.exists() else {'plan_hash':hash_json(plan),'records':[],'barriers':[]}
  require(old['plan_hash']==hash_json(plan),'activation plan changed')
  by={s['root_id']:s for s in plan['slots']};require(set(terminals)<=set(by),'unknown terminal root')
  require(all(x in ('FAILED','PASSED') for x in terminals.values()),'wait for terminal barrier')
  family=by[next(iter(terminals))]['family'];require(all(by[x]['family']==family for x in terminals),'one family per wave')
  bid=hash_json({'family':family,'wave':wave,'terminals':terminals})
  if any(x['id']==bid for x in old['barriers']):return old
  if wave=='remaining':
   first=[x for x in old['barriers'] if x['family']==family and x['wave']=='first']
   require(bool(first) and not first[-1]['replacement_ids'],'first wave must close before remaining')
  prior=[x for x in old['barriers'] if x['family']==family and x['wave']==wave]
  if not prior:
   expected={s['root_id'] for s in plan['slots'] if s['family']==family and s['reserve_rank'] is None and ((s['rank']<=2)==(wave=='first'))}
  else:expected=set(prior[-1]['replacement_ids'])
  require(bool(expected) and set(terminals)==expected,'incomplete/future/conflicting terminal barrier')
  records=copy.deepcopy(old['records']); replacements=[]
  def origin(rid):
   if by[rid]['reserve_rank'] is None:return by[rid]
   return by[next(r['primary_root_id'] for r in records if r['reserve_root_id']==rid)]
  for rid in sorted(terminals,key=lambda x:origin(x)['rank']):
   if terminals[rid]!='FAILED':continue
   primary=origin(rid);used={r['reserve_root_id'] for r in records}
   available=sorted([s for s in plan['slots'] if s['family']==family and s['reserve_rank'] is not None and s['root_id'] not in used],key=lambda s:s['reserve_rank']);require(bool(available),'reserve exhausted')
   r=available[0];rec={'failed_root_id':rid,'primary_root_id':primary['root_id'],'reserve_root_id':r['root_id'],'reserve_seed':r['seed'],'rank':r['reserve_rank'],'split':primary['split'],'difficulty':primary['difficulty'],'failed_terminal':'FAILED'}
   rec['resolved_spec']=resolve(r,rec);records.append(rec);replacements.append(r['root_id'])
  new={'plan_hash':old['plan_hash'],'records':records,'barriers':old['barriers']+[{'id':bid,'family':family,'wave':wave,'terminals':terminals,'replacement_ids':replacements}]}
  temp=path.with_suffix('.partial')
  with temp.open('w') as f:json.dump(new,f,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(temp,path);return new

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--check',type=Path);a=p.parse_args();v=json.loads(a.check.read_text()) if a.check else generate();print(json.dumps(validate_plan(v)))
 if a.output:a.output.mkdir(exist_ok=True);(a.output/'PLANNED_SLOTS_V2.json').write_text(json.dumps(v,indent=2));(a.output/'RESOLVED_PRIMARY_SCENES.json').write_text(json.dumps([resolve(s) for s in v['slots'] if s['reserve_rank'] is None],indent=2))
