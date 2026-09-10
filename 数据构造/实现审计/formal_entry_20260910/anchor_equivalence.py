"""Versioned F1 physical anchor equivalence; independent of file serialization.

No origin reads and no simulator imports. Single-file integrity remains a caller
SHA256 check. Tolerances reproduce the existing compare_anchors defaults.
"""
from copy import deepcopy
import hashlib,json
import numpy as np
VERSION='f1_physical_anchor_equivalence_v1'
CONTRACT={
 'version':VERSION,'schema_version':'physical_anchor_v2','phase':'fresh t0 before shared prefix',
 'frame':'world/table-fixed simulation world; wxyz quaternion orientation, normalized and sign-invariant at comparison',
 'binding_fields':['root_id','spec_sha256','source_bundle_sha256'],
 'required_fields':['schema_version','model_visible','robot_qpos','robot_qvel','robot_drive_target','gripper_joint_qpos','actor_states','facility_poses','physics_config','source_commit','metadata'],
 'actor_fields':['pose','linear_velocity','angular_velocity','sleep_state'],
 'units':{'robot_qpos':'native generalized coordinate: rad revolute / m prismatic','robot_drive_target':'same frozen native generalized coordinate as robot_qpos','robot_qvel':'rad/s revolute / m/s prismatic','gripper_joint_qpos':'m','pose_position':'m','pose_orientation_error':'rad','linear_velocity':'m/s','angular_velocity':'rad/s'},
 'tolerances':{'joint_coordinate_abs':1e-6,'joint_velocity_abs':1e-6,'position_norm_m':1e-6,'orientation_rad':1e-6,'linear_velocity_component_m_s':1e-6,'angular_velocity_component_rad_s':1e-6,'gripper_position_abs_m':1e-6},
 'exact_fields':['schema_version','model_visible','physics_config','source_commit','metadata','actor_roles','facility_roles','sleep_state'],
 'integrity_fields_not_scientific':['anchor_sha256'],
 'storage':'38 unique articulation entries; 76 accepted only if two 38-entry halves are exactly equal; gripper 4 entries',
 'source_compatibility':{'schema':'f1_source_compatibility_v1','default':'same source bundle required','exception':'exact reviewed old/new bundle pair, identical root/spec, old capture hash listed in accepted_cells; physical fields unchanged'},
 'reviewed_source_provenance_exceptions':['physics_config.implementation_source_sha256'],
 'tolerance_source':'controlled_multi_future.anchor.compare_anchors existing defaults (rtol=0); no new task-terminal tolerance applied'}

def contract():return deepcopy(CONTRACT)
def contract_hash():return hashlib.sha256(json.dumps(CONTRACT,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def validate_contract(value):
 if value!=CONTRACT:raise ValueError('unknown or modified frozen anchor equivalence contract')

def vector(value,size=None):
 x=np.asarray(value,dtype=np.float64)
 if x.ndim!=1 or (size is not None and x.shape!=(size,)) or not np.isfinite(x).all():raise ValueError('missing/invalid finite vector')
 return x

def joint(value):
 x=vector(value)
 if x.shape==(76,):
  if not np.array_equal(x[:38],x[38:]):raise ValueError('shared articulation storage differs')
  return x[:38]
 if x.shape!=(38,):raise ValueError('anchor must bind unique38DOF')
 return x

def pose(value):
 x=vector(value,7)
 if np.linalg.norm(x[3:])<=0:raise ValueError('zero anchor quaternion')
 return x

def angular_error(a,b):
 a=vector(a,4);b=vector(b,4);return float(2*np.arccos(np.clip(abs(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))),0,1)))

def validate_anchor(value,binding,rule=None):
 validate_contract(CONTRACT if rule is None else rule)
 if not isinstance(binding,dict) or any(not isinstance(binding.get(k),str) or not binding[k] for k in CONTRACT['binding_fields']):raise ValueError('missing anchor root/spec/source binding')
 for k in ['spec_sha256','source_bundle_sha256']:
  if len(binding[k])!=64 or any(c not in '0123456789abcdef' for c in binding[k]):raise ValueError('invalid anchor '+k)
 if not isinstance(value,dict) or not set(CONTRACT['required_fields'])<=set(value):raise ValueError('required anchor field missing')
 if set(value)-set(CONTRACT['required_fields'])-set(CONTRACT['integrity_fields_not_scientific']):raise ValueError('unknown anchor field outside frozen whitelist')
 if value['schema_version']!='physical_anchor_v2' or value['model_visible']is not False:raise ValueError('anchor schema/model visibility')
 for k in ['robot_qpos','robot_qvel','robot_drive_target']:joint(value[k])
 vector(value['gripper_joint_qpos'],4)
 if not isinstance(value['actor_states'],dict) or not value['actor_states'] or not isinstance(value['facility_poses'],dict):raise ValueError('anchor role state missing')
 for r,x in value['actor_states'].items():
  if not isinstance(r,str) or not r or not isinstance(x,dict) or set(CONTRACT['actor_fields'])!=set(x):raise ValueError('actor state fields missing')
  pose(x['pose']);vector(x['linear_velocity'],3);vector(x['angular_velocity'],3)
  if not isinstance(x['sleep_state'],(bool,str)):raise ValueError('actor sleep state unavailable')
 for r,x in value['facility_poses'].items():pose(x)
 try:json.dumps({k:value[k] for k in ['physics_config','metadata']},allow_nan=False)
 except (TypeError,ValueError) as exc:raise ValueError('nonfinite/invalid anchor metadata') from exc
 if not isinstance(value['physics_config'],dict) or not isinstance(value['metadata'],dict) or not isinstance(value['source_commit'],str) or not value['source_commit']:raise ValueError('anchor physics/source metadata missing')
 return value

def validate_source_compatibility(value,reference_binding,candidate_binding):
 required={'schema','status','root_id','spec_sha256','old_source_sha256','new_source_sha256','old_source_bundle_sha256','new_source_bundle_sha256','scientific_contract_unchanged','changed_files','affected_contracts','accepted_cells'}
 if not isinstance(value,dict) or not required<=set(value):raise ValueError('missing source compatibility receipt fields')
 if value['schema']!='f1_source_compatibility_v1' or value['status']!='CPU_REVIEWED_APPLICABLE' or value['scientific_contract_unchanged']is not True:raise ValueError('unreviewed source compatibility')
 for k in ['root_id','spec_sha256']:
  if reference_binding[k]!=candidate_binding[k] or value[k]!=reference_binding[k]:raise ValueError('compatibility root/spec mismatch')
 old=value['old_source_bundle_sha256'];new=value['new_source_bundle_sha256']
 if old==new or {reference_binding['source_bundle_sha256'],candidate_binding['source_bundle_sha256']}!={old,new}:raise ValueError('compatibility source pair mismatch')
 if not value['changed_files'] or not isinstance(value['affected_contracts'],dict) or any(not value['affected_contracts'].get(path) for path in value['changed_files']):raise ValueError('source change impact assessment missing')
 old_binding=reference_binding if reference_binding['source_bundle_sha256']==old else candidate_binding
 if not old_binding.get('capture_sha256') or old_binding['capture_sha256'] not in {c.get('capture_sha256') for c in value['accepted_cells']}:raise ValueError('old capture absent from compatibility evidence')
 return True

def compare_anchors(reference,candidate,*,reference_binding,candidate_binding,contract=None,compatibility=None):
 rule=CONTRACT if contract is None else contract;failures=[]
 try:
  validate_anchor(reference,reference_binding,rule);validate_anchor(candidate,candidate_binding,rule)
  for key in CONTRACT['binding_fields']:
   if reference_binding[key]!=candidate_binding[key]:
    if key=='source_bundle_sha256' and compatibility is not None:validate_source_compatibility(compatibility,reference_binding,candidate_binding)
    else:failures.append('binding:'+key)
  t=rule['tolerances']
  for key in ['schema_version','model_visible','physics_config','source_commit','metadata']:
   if reference[key]!=candidate[key]:
    if key=='physics_config' and compatibility is not None:
     validate_source_compatibility(compatibility,reference_binding,candidate_binding)
     left=dict(reference[key]);right=dict(candidate[key]);lv=left.pop('implementation_source_sha256',None);rv=right.pop('implementation_source_sha256',None)
     expected=lambda binding:compatibility['old_source_sha256'] if binding['source_bundle_sha256']==compatibility['old_source_bundle_sha256'] else compatibility['new_source_sha256']
     if left!=right or lv!=expected(reference_binding) or rv!=expected(candidate_binding):failures.append(key)
    else:failures.append(key)
  for key,tol in [('robot_qpos',t['joint_coordinate_abs']),('robot_drive_target',t['joint_coordinate_abs']),('robot_qvel',t['joint_velocity_abs'])]:
   if not np.allclose(joint(reference[key]),joint(candidate[key]),rtol=0,atol=tol):failures.append(key)
  if not np.allclose(vector(reference['gripper_joint_qpos'],4),vector(candidate['gripper_joint_qpos'],4),rtol=0,atol=t['gripper_position_abs_m']):failures.append('gripper_joint_qpos')
  def check_pose(a,b,label):
   a=pose(a);b=pose(b)
   if np.linalg.norm(a[:3]-b[:3])>t['position_norm_m']:failures.append(label+':position')
   if angular_error(a[3:],b[3:])>t['orientation_rad']:failures.append(label+':orientation')
  for field in ['actor_states','facility_poses']:
   if set(reference[field])!=set(candidate[field]):failures.append(field+':roles');continue
   for role,a in reference[field].items():
    b=candidate[field][role]
    if field=='facility_poses':check_pose(a,b,role);continue
    check_pose(a['pose'],b['pose'],role)
    for component,tol in [('linear_velocity',t['linear_velocity_component_m_s']),('angular_velocity',t['angular_velocity_component_rad_s'])]:
     if not np.allclose(vector(a[component],3),vector(b[component],3),rtol=0,atol=tol):failures.append(role+':'+component)
    if a['sleep_state']!=b['sleep_state']:failures.append(role+':sleep_state')
 except (TypeError,KeyError,ValueError) as exc:failures.append('invalid:'+str(exc))
 return {'equivalent':not failures,'failures':failures,'contract_version':VERSION,'contract_sha256':contract_hash(),'file_hash_equality_required':False}

def arrays_equal(reference,candidate):
 return set(reference)==set(candidate) and all(np.asarray(reference[k]).dtype==np.asarray(candidate[k]).dtype and np.asarray(reference[k]).shape==np.asarray(candidate[k]).shape and np.asarray(reference[k]).tobytes()==np.asarray(candidate[k]).tobytes() for k in reference)
