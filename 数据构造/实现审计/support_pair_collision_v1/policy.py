"""Proposal-only support-pair split checker. Never disables the robot's pad."""
import inspect
import numpy as np

METHODS=('get_sphere_distance','get_sphere_collision','get_swept_sphere_distance','get_swept_sphere_collision')
def verify_support_witness(w):
    h=w['hold']
    return bool(w['only_attached_bottle_support_pairs_overlap'] and h['frames']==250 and h['all_selected_contact'] and h['all_both_fingers'] and h['all_signal_complete'] and h['forbidden_count']==0 and h['support_contact_frames']==250 and h['max_relative_translation_drift_m']<=.005 and h['max_relative_orientation_drift_rad']<=.05)

class PairFilteredWorld:
    """Pass as world_coll_checker BEFORE constructing MotionGen/IKSolver.

    PrimitiveCollisionCost caches bound methods at construction; changing a
    checker afterwards does not update those cached callbacks. Both unswept
    and swept methods must therefore be provided by this object initially.
    """
    def __init__(self,full,without_support,*,sphere_link_names,attached_link_name,support_name,witness,buffer_factory):
        if not verify_support_witness(witness):raise ValueError('no verified legal supported-grasp witness')
        if attached_link_name!='attached_bottle' or support_name!='pad__0':raise ValueError('only recorded bottle-pad pair reviewed')
        original={n for n in full.get_obstacle_names() if n};filtered={n for n in without_support.get_obstacle_names() if n}
        if support_name not in original or filtered!=original-{support_name}:raise ValueError('other world obstacle was removed')
        if not sphere_link_names or attached_link_name not in sphere_link_names or all(n==attached_link_name for n in sphere_link_names):raise ValueError('invalid sphere/link partition')
        self.full=full;self.without_support=without_support;self.names=list(sphere_link_names);self.attached=attached_link_name;self.buffer_factory=buffer_factory;self.buffers={};self.calls={name:0 for name in METHODS}
        self.support_pair_policy_version='PROPOSAL_CPU_TESTED_NOT_GPU_VALIDATED_V1'
    def __getattr__(self,name):return getattr(self.full,name)
    def load_collision_model(self,*a,**kw):raise RuntimeError('rebuild both checked views for a new world; no one-sided world update')
    def enable_obstacle(self,*a,**kw):raise RuntimeError('global obstacle toggles are prohibited in this scoped checker')
    def _query(self,name,query_sphere,collision_query_buffer,*args,**kwargs):
        import torch
        if query_sphere.shape[-2]!=len(self.names) or query_sphere.shape[-1]!=4:raise ValueError('sphere partition shape changed')
        original=getattr(self.full,name);subset=getattr(self.without_support,name)
        binding=inspect.signature(original).bind(query_sphere,collision_query_buffer,*args,**kwargs);values=dict(binding.arguments)
        for p in inspect.signature(original).parameters.values():
            if p.kind==inspect.Parameter.VAR_KEYWORD:values.update(values.pop(p.name,{}))
        # CuRobo documents return_loss=True when results are subsequently
        # weighted/masked. Binary collision methods do not support that mode.
        if name.endswith('distance'):values['return_loss']=True
        elif values.get('return_loss',False):raise ValueError('binary collision has no differentiable return_loss')
        primary=original(**values)
        key=(name,id(collision_query_buffer),tuple(query_sphere.shape),str(query_sphere.device),str(query_sphere.dtype))
        if key not in self.buffers:self.buffers[key]=self.buffer_factory(query_sphere)
        values['collision_query_buffer']=self.buffers[key];secondary=subset(**values)
        if tuple(primary.shape)!=tuple(query_sphere.shape[:-1]) or primary.shape!=secondary.shape:raise ValueError('expected per-sphere collision outputs, not preaggregated cost')
        mask=torch.tensor([n==self.attached for n in self.names],device=query_sphere.device,dtype=torch.bool)
        self.calls[name]+=1
        return torch.where(mask,secondary,primary)
    def get_sphere_distance(self,*a,**kw):return self._query('get_sphere_distance',*a,**kw)
    def get_sphere_collision(self,*a,**kw):return self._query('get_sphere_collision',*a,**kw)
    def get_swept_sphere_distance(self,*a,**kw):return self._query('get_swept_sphere_distance',*a,**kw)
    def get_swept_sphere_collision(self,*a,**kw):return self._query('get_swept_sphere_collision',*a,**kw)

def audit_lift_escape(native_world_vertices,actor_world_poses,*,support_plane_z,witness):
    """Mandatory post-plan discrete 250Hz geometry screen, before execution.

    Does not prove continuous collision freedom or physical grasp stability.
    The existing full-window physical/postlift gates must still be applied.
    """
    if not verify_support_witness(witness):raise ValueError('support witness missing')
    v=np.asarray(native_world_vertices,dtype=float);poses=np.asarray(actor_world_poses,dtype=float)
    if v.ndim!=3 or v.shape[-1]!=3 or len(v)<2 or poses.shape!=(len(v),7) or not np.isfinite(v).all() or not np.isfinite(poses).all():raise ValueError('missing/invalid dense native geometry or actor poses')
    height=v[:,:,2].min(axis=1);eps=1e-4
    checks={'native_support_penetration_not_deeper':bool(height.min()>=height[0]-eps),'native_lower_envelope_not_descending':bool(np.all(np.diff(height)>=-eps)),
        'final_native_geometry_above_support':bool(height[-1]>support_plane_z),'planned_actor_origin_rise_at_least_original_20mm':bool(poses[-1,2]-poses[0,2]>=.020)}
    return {'checks':checks,'pass':all(checks.values()),'sample_count':len(v),'numerical_geometry_tolerance_m':eps,'continuous_sweep_proven':False,'physical_grasp_proven':False,'physics_thresholds_unchanged':True}
