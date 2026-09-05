"""Frozen transport-only retiming with rounded grid and execution durations."""
import copy,math
import numpy as np
from catalog import seal
from controlled_multi_future.canonical_prefix_artifact_v1 import array_sha256

def retime(control,segment_id,factor=1.10,frequency=250):
    if factor!=1.10 or frequency!=250:raise ValueError('unregistered retiming')
    q=np.asarray(control['position']);v=np.asarray(control['velocity'])
    if q.ndim!=2 or q.shape!=v.shape or len(q)<2 or not np.isfinite(q).all() or not np.isfinite(v).all():raise ValueError('control arrays')
    n=len(q);m=math.ceil((n-1)*factor)+1;grid_scale=(m-1)/(n-1);execution_scale=m/n
    from scipy.interpolate import CubicHermiteSpline
    u=np.linspace(0.,1.,m)
    # One cohort-wide monotone C1 warp: preserve endpoint velocity instead of
    # assuming the real plans have exactly zero boundary velocities.
    warp=u+(grid_scale-1.)*u*(1.-u)*(1.-2.*u)
    rate=(1.+(grid_scale-1.)*(1.-6.*u+6.*u*u))/grid_scale
    if np.any(np.diff(warp)<=0) or np.any(rate<=0):raise ValueError('nonmonotone time warp')
    spline=CubicHermiteSpline(np.arange(n)/frequency,q,v,axis=0)
    tau=warp*(n-1)/frequency
    newq=spline(tau).astype(q.dtype);newv=(spline.derivative()(tau)*rate[:,None]).astype(v.dtype)
    newq[0]=q[0];newq[-1]=q[-1];newv[0]=v[0];newv[-1]=v[-1]
    out=copy.deepcopy(control);out['position']=newq;out['velocity']=newv
    for key in ('dt','interpolation_dt'):
        if key in out and not np.isclose(float(out[key]),1/frequency,rtol=0,atol=1e-9):raise ValueError('control dt mismatch')
    if 'time' in out:out['time']=np.arange(m,dtype=np.float64)/frequency
    if 'duration' in out:out['duration']=(m-1)/frequency
    if 'length' in out:out['length']=m
    receipt=seal({'schema_version':'cmf_realization_retime_v1','segment_id':segment_id,'nominal_factor':factor,'actual_control_grid_scale':grid_scale,
       'actual_execution_interval_scale':execution_scale,'old_samples':n,'new_samples':m,'frequency_hz':frequency,'dt':1/frequency,
       'old_control_grid_duration_s':(n-1)/frequency,'new_control_grid_duration_s':(m-1)/frequency,'old_execution_duration_s':n/frequency,'new_execution_duration_s':m/frequency,
       'original_position_sha256':array_sha256(q),'original_velocity_sha256':array_sha256(v),'position_sha256':array_sha256(newq),'velocity_sha256':array_sha256(newv),
       'position_endpoints_equal':bool(np.array_equal(newq[[0,-1]],q[[0,-1]])),'velocity_endpoints_equal':bool(np.array_equal(newv[[0,-1]],v[[0,-1]])),
       'time_warp':'monotone_C1_endpoint_rate_one_v1','velocity_rule':'Hermite derivative times actual dtau/dt',
       'new_solver_queries':0,'resamples_existing_raw':False})
    out['_cmf_planner_query']=copy.deepcopy(out.get('_cmf_planner_query',{}));out['_cmf_planner_query']['realization_control_transform']=receipt
    return out,receipt
