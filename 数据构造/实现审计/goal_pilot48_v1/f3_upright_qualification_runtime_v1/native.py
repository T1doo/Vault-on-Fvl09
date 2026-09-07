"""Fresh complete visible collision inventory and native-derived planned-state checks."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
import transforms3d as t3d
import mplib
from mplib.collision_detection import fcl
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计')
sys.path.insert(0,str(A/'f3_model_replay_v1'))
from kinematics_cpu import TREE,JOINTS,origin
LINK_NAMES={node.get('name') for node in TREE.findall('link')}
def T(p):return t3d.affines.compose(p[:3],t3d.quaternions.quat2mat(p[3:]),[1,1,1])
def p7(x):
    p=x.get_pose() if hasattr(x,'get_pose') else x.get_entity_pose();return np.r_[p.p,p.q].astype(float).tolist()
def hash_value(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
def fk_all(q):
    cache={}
    def pose(name):
        if name not in LINK_NAMES:raise ValueError('unknown URDF link '+name)
        if name in cache:return cache[name]
        if name not in JOINTS:cache[name]=np.eye(4);return cache[name]
        j=JOINTS[name];motion=np.eye(4);a=j.find('axis');axis=np.fromstring(a.get('xyz','1 0 0') if a is not None else '1 0 0',sep=' ')
        if j.get('type') in ('revolute','continuous'):motion[:3,:3]=t3d.axangles.axangle2mat(axis,float(q.get(j.get('name'),0)))
        elif j.get('type')=='prismatic':motion[:3,3]=axis*float(q.get(j.get('name'),0))
        cache[name]=pose(j.find('parent').get('link'))@origin(j)@motion;return cache[name]
    return pose
def enabled(a,b):
    x,y=a['groups'],b['groups'];return bool((x[0]&y[1] or x[1]&y[0]) and not(x[2]&y[2] and (x[3]&65535)==(y[3]&65535)))
def adjacent(a,b):
    return (a in JOINTS and JOINTS[a].find('parent').get('link')==b) or (b in JOINTS and JOINTS[b].find('parent').get('link')==a)
def capture_shape(shape,name,index,robot,world):
    local=shape.get_local_pose();r={'name':name+'__'+str(index),'body':name,'robot':robot,'kind':type(shape).__name__,
        'local_pose':np.r_[local.p,local.q].astype(float).tolist(),'body_world_pose':world,'groups':list(shape.get_collision_groups())}
    k=r['kind']
    if k in ('PhysxCollisionShapeConvexMesh','PhysxCollisionShapeTriangleMesh'):
        r.update(vertices=(np.asarray(shape.get_vertices(),float)*np.asarray(shape.get_scale(),float)).tolist(),faces=np.asarray(shape.get_triangles(),dtype=int).tolist())
    elif k=='PhysxCollisionShapeBox':r['half_size']=np.asarray(shape.get_half_size(),float).tolist()
    elif k=='PhysxCollisionShapeSphere':r['radius']=float(shape.get_radius())
    elif k in ('PhysxCollisionShapeCylinder','PhysxCollisionShapeCapsule'):
        r.update(radius=float(shape.get_radius()),half_length=float(shape.get_half_length()),native_axis='X',axis_source='locked sapien.wrapper.urdf_loader cylinder/capsule URDF-Z to native-X rotation')
    elif k=='PhysxCollisionShapePlane':r['normal']=[1.,0.,0.]
    else:raise ValueError('uncovered visible native shape '+k+' on '+name)
    hash_value(r)  # Reject nonfinite geometry instead of passing a NaN AABB comparison.
    if 'radius' in r and r['radius']<=0:raise ValueError('nonpositive native radius')
    if 'half_length' in r and r['half_length']<0:raise ValueError('negative native half length')
    if 'half_size' in r and (len(r['half_size'])!=3 or any(x<=0 for x in r['half_size'])):raise ValueError('invalid native box')
    if 'vertices' in r:
        v=np.asarray(r['vertices']);f=np.asarray(r['faces'])
        if v.ndim!=2 or v.shape[1]!=3 or len(v)==0 or f.ndim!=2 or f.shape[1]!=3 or len(f)==0 or f.min()<0 or f.max()>=len(v):raise ValueError('invalid native mesh arrays')
    return r
def bounds(shape,world):
    k=shape['kind'];R=world[:3,:3];p=world[:3,3]
    if k.endswith('Mesh'):
        v=np.asarray(shape['vertices'])@R.T+p;return np.array([v.min(0),v.max(0)])
    if k=='PhysxCollisionShapePlane':return np.array([[-np.inf]*3,[np.inf]*3])
    if k=='PhysxCollisionShapeBox':e=np.abs(R)@shape['half_size']
    elif k=='PhysxCollisionShapeSphere':e=np.ones(3)*shape['radius']
    else:
        axis=R[:,0];e=np.abs(axis)*shape['half_length']+shape['radius']*(np.ones(3) if k.endswith('Capsule') else np.sqrt(np.maximum(0,1-axis*axis)))
    return np.array([p-e,p+e])
def geometry(shape):
    k=shape['kind'];extra=np.eye(4)
    if k.endswith('Mesh'):
        g=fcl.BVHModel();v=np.asarray(shape['vertices']);f=np.asarray(shape['faces'],np.int32);g.begin_model(len(f),len(v));g.add_sub_model(v,f);g.end_model()
    elif k=='PhysxCollisionShapeBox':g=fcl.Box(*(2*np.asarray(shape['half_size'])))
    elif k=='PhysxCollisionShapeSphere':g=fcl.Sphere(shape['radius'])
    elif k in ('PhysxCollisionShapeCylinder','PhysxCollisionShapeCapsule'):
        g=(fcl.Cylinder if k.endswith('Cylinder') else fcl.Capsule)(shape['radius'],2*shape['half_length']);extra[:3,:3]=t3d.euler.euler2mat(0,np.pi/2,0)
    elif k=='PhysxCollisionShapePlane':g=fcl.Halfspace(np.array([1.,0,0]),0.)
    else:raise ValueError('unsupported frozen shape')
    return g,extra
def capture(scene,base_pose,names,qpos):
    links={}
    for articulation in scene.scene.get_all_articulations():
        for link in articulation.get_links():
            name=link.get_name()
            if name in links and links[name] is not link:raise ValueError('ambiguous duplicate articulation link '+name)
            links[name]=link
    if not all(n in links for n in ('fl_base_link','fl_link3','fl_link5','fl_link7','fl_link8')):raise ValueError('missing executing arm native links')
    records=[];coverage=[];f=fk_all(dict(zip(names,qpos)));B=T(base_pose)@np.linalg.inv(f('fl_base_link'))
    bodies=[(name,link,True) for name,link in links.items()]
    for ordinal,actor in enumerate(scene.scene.get_all_actors()):
        for component in actor.get_components():
            if hasattr(component,'get_collision_shapes'):bodies.append((actor.get_name() or 'unnamed_world_actor_'+str(ordinal),component,False))
    for name,body,robot in bodies:
        world=p7(body);shapes=body.get_collision_shapes()
        if robot:
            node=TREE.find("link[@name='"+name+"']")
            if node is None:raise ValueError('robot link absent from locked URDF '+name)
            if node.findall('collision') and not shapes:raise ValueError('native geometry absent for declared robot collision '+name)
            expected=B@f(name)
            if np.max(np.abs(expected-T(world)))>1e-5:raise ValueError('full-link FK does not match actual '+name)
        group=[capture_shape(s,name,i,robot,world) for i,s in enumerate(shapes)]
        finite=[bounds(s,T(world)@T(s['local_pose'])) for s in group if s['kind']!='PhysxCollisionShapePlane']
        err=None
        if finite:
            predicted=np.array([np.min([b[0] for b in finite],0),np.max([b[1] for b in finite],0)])
            actual=np.asarray(body.compute_global_aabb_tight(),float);err=float(np.max(np.abs(predicted-actual)))
            primitive=any(s['kind'] in ('PhysxCollisionShapeCylinder','PhysxCollisionShapeCapsule','PhysxCollisionShapeSphere') for s in group)
            enclosed=bool(np.all(actual[0]>=predicted[0]-1e-4) and np.all(actual[1]<=predicted[1]+1e-4))
            if (primitive and not enclosed) or (not primitive and err>1e-4):raise ValueError('native primitive/mesh AABB axis or scale mismatch '+name)
        records.extend(group);coverage.append({'body':name,'robot':robot,'shapes':len(group),'aabb_error_m':err,'primitive_representation':'native-parameter enclosing solid; mesh/box use exact vertices/half-size'})
    if not any('wheel' in s['body'] for s in records) or not any(s['body']=='fl_base_link' for s in records):raise ValueError('base/wheel coverage absent')
    if not all(any(s['body']==n for s in records) for n in ('table','f3_original_pad','f3_main_bottle','ground')):raise ValueError('mandatory native world body absent')
    return {'shapes':records,'coverage':coverage,'inventory_complete':True,'base_pose':base_pose,'joint_names':names,'actual_qpos':np.asarray(qpos).tolist(),'geometry_sha256':hash_value(records),
        'coverage_rule':'all visible rigid bodies and all articulation collision shapes; moving left arm checked against all remaining robot/base/wheels/world; fixed-fixed baseline support is not planned motion'}
class Checker:
    def __init__(self,snapshot):
        names={s['body'] for s in snapshot['shapes']};required={'table','f3_original_pad','f3_main_bottle','ground','fl_base_link'}|{side+'_link'+str(i) for side in ('fl','fr') for i in range(1,9)}
        if snapshot.get('inventory_complete') is not True or not required.issubset(names) or not any('wheel' in n for n in names):raise ValueError('incomplete full visible native coverage')
        if snapshot['geometry_sha256']!=hash_value(snapshot['shapes']):raise ValueError('native inventory hash changed')
        self.data=snapshot;self.shapes=snapshot['shapes'];self.compiled=[geometry(s) for s in self.shapes]
        self.actual=dict(zip(snapshot['joint_names'],snapshot['actual_qpos']));f=fk_all(self.actual);self.B=T(snapshot['base_pose'])@np.linalg.inv(f('fl_base_link'))
        self.bottle=next(s for s in self.shapes if s['body']=='f3_main_bottle');self.grasp=np.linalg.inv(self.B@f('fl_link6'))@T(self.bottle['body_world_pose'])
    def check(self,positions,joint_names,*,carried=False,allow_pad_escape=False):
        values=np.asarray(positions,float)
        if values.ndim!=2 or len(values)==0 or values.shape[1]!=len(joint_names) or not np.isfinite(values).all():raise ValueError('empty/nonfinite native check positions')
        if set(joint_names)!={f'fl_joint{i}' for i in range(1,7)}:raise ValueError('exact left-arm named positions required')
        if allow_pad_escape is not False and (not isinstance(allow_pad_escape,dict) or allow_pad_escape.get('geometry_sha256')!=self.data['geometry_sha256'] or allow_pad_escape.get('validated_model_eligibility') is not True):raise ValueError('uncertified native pad exception')
        rows=[]
        for index,q in enumerate(values):
            named={**self.actual,**dict(zip(joint_names,q))};fk=fk_all(named);objects=[];boxes=[];moving=[];worlds=[]
            for s,(g,extra) in zip(self.shapes,self.compiled):
                move=s['robot'] and s['body'] in {f'fl_link{i}' for i in range(1,9)}
                if s['robot']:world=self.B@fk(s['body'])
                elif carried and s['body']=='f3_main_bottle':world=self.B@fk('fl_link6')@self.grasp;move=True
                else:world=T(s['body_world_pose'])
                world=world@T(s['local_pose']);actual=world@extra
                objects.append(fcl.CollisionObject(g,mplib.Pose(actual[:3,3],t3d.quaternions.mat2quat(actual[:3,:3]))));boxes.append(bounds(s,world));moving.append(move);worlds.append(world)
            hits=[]
            for i,a in enumerate(self.shapes):
                for j in range(i+1,len(self.shapes)):
                    b=self.shapes[j]
                    if not(moving[i] or moving[j]) or a['body']==b['body'] or not enabled(a,b):continue
                    if a['robot'] and b['robot'] and adjacent(a['body'],b['body']):continue
                    pair={a['body'],b['body']}
                    if carried and 'f3_main_bottle' in pair and pair&{'fl_link7','fl_link8'}:continue
                    if carried and isinstance(allow_pad_escape,dict) and pair=={'f3_main_bottle','f3_original_pad'}:continue
                    if np.any(boxes[i][1]<boxes[j][0]) or np.any(boxes[j][1]<boxes[i][0]):continue
                    if a['kind']=='PhysxCollisionShapePlane' or b['kind']=='PhysxCollisionShapePlane':
                        pi,mi=(i,j) if a['kind']=='PhysxCollisionShapePlane' else (j,i)
                        n=worlds[pi][:3,0];local_n=worlds[mi][:3,:3].T@n;s=self.shapes[mi];k=s['kind']
                        offset=float(n@(worlds[mi][:3,3]-worlds[pi][:3,3]))
                        if k.endswith('Mesh'):distance=offset+float(np.min(np.asarray(s['vertices'])@local_n))
                        elif k=='PhysxCollisionShapeBox':distance=offset-float(np.abs(local_n)@s['half_size'])
                        elif k=='PhysxCollisionShapeSphere':distance=offset-s['radius']
                        elif k in ('PhysxCollisionShapeCylinder','PhysxCollisionShapeCapsule'):distance=offset-abs(local_n[0])*s['half_length']-s['radius']*(1. if k.endswith('Capsule') else float(np.linalg.norm(local_n[1:])))
                        else:raise ValueError('unsupported moving plane geometry')
                        hit=distance<=0
                    else:hit=fcl.collide(objects[i],objects[j]).is_collision()
                    if hit:hits.append([a['name'],b['name']])
            rows.append({'sample_index':index,'hits':hits})
            if hits:break
        return {'pass':len(rows)==len(values) and not any(r['hits'] for r in rows),'rows':rows,'requested_samples':len(values),'checked_samples':len(rows),
            'geometry_sha256':self.data['geometry_sha256'],'full_visible_native_inventory':True,'discrete_not_continuous_proof':True,'carried':carried,'pad_escape_requires_separate_native_gate':bool(allow_pad_escape)}
def pad_escape_token(scene,snapshot):
    branch=getattr(scene,'_cmf_escape_model_branch',None)
    if branch=='old_supported':
        from support_pair_collision_v1.policy import verify_support_witness
        if not verify_support_witness(scene._cmf_fresh_support_witness):raise ValueError('old support witness invalid')
    elif branch=='one_sided_unloading':
        from goal_pilot48_v1.f3_one_sided_escape_v2.certificate import validate
        if not validate(scene._cmf_escape_certificate):raise ValueError('one-sided certificate invalid')
        scene._cmf_tangent_lease.check()
        if scene._cmf_tangent_lease.state!='planning':raise ValueError('pad exception outside one bound lift plan')
    else:raise ValueError('no certified pad escape mode')
    return {'geometry_sha256':snapshot['geometry_sha256'],'validated_model_eligibility':True,'requires_original_native_escape_gate':True}
