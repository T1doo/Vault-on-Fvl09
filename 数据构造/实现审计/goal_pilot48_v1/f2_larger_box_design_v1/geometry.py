"""Pure analytic scale bounds and exact vertical surface-contact construction."""
import numpy as np

def minimum_interval_feasible_scale(lower,intervals):
    """Solve sufficient forbidden intervals, not a scale/pose search."""
    value=float(lower);active=[]
    for start,end,label in sorted(intervals):
        if start<=value<end:value=float(end);active.append(label)
    return float(np.nextafter(value,np.inf)),active

def vertical_triangles(vertices,faces):
    result=[]
    for index,tri in enumerate(np.asarray(vertices)[np.asarray(faces,dtype=int)]):
        xy=tri[:,:2];cross=np.cross(xy[1]-xy[0],xy[2]-xy[0])
        if abs(cross)<1e-12:continue
        plane=np.linalg.solve(np.c_[xy,np.ones(3)],tri[:,2])
        if cross<0:xy=xy[::-1]
        result.append((xy,plane,xy.min(0),xy.max(0),index))
    return result

def intersection_polygon(first,second):
    polygon=list(first)
    for a,b in zip(second,np.roll(second,-1,axis=0)):
        output=[]
        if not polygon:break
        for p,q in zip(polygon,[*polygon[1:],polygon[0]]):
            dp=float(np.cross(b-a,p-a));dq=float(np.cross(b-a,q-a));ip=dp>=-1e-12;iq=dq>=-1e-12
            if ip:output.append(p)
            if ip!=iq:output.append(p+(q-p)*(dp/(dp-dq)))
        polygon=output
    return np.asarray(polygon)

def first_vertical_contact(moving,floors):
    """Max floor-Z minus can-bottom-Z over exact triangle overlap polygons."""
    best=None;pair_count=0
    first=[(name,t) for name,v,f in moving for t in vertical_triangles(v,f)]
    second=[(name,t) for name,v,f in floors for t in vertical_triangles(v,f)]
    for cname,(xy,cp,lo,hi,ci) in first:
        for fname,(fx,fp,flo,fhi,fi) in second:
            if np.any(hi<flo) or np.any(fhi<lo):continue
            polygon=intersection_polygon(xy,fx)
            if len(polygon)==0:continue
            pair_count+=1;difference=np.c_[polygon,np.ones(len(polygon))]@(fp-cp);i=int(np.argmax(difference));delta=float(difference[i])
            if best is None or delta>best['vertical_translation_m']:
                point=polygon[i];best={'vertical_translation_m':delta,'can_shape':cname,'floor_shape':fname,'can_triangle':ci,'floor_triangle':fi,
                  'contact_xy_world':point.tolist(),'floor_surface_z_m':float(np.r_[point,1]@fp)}
    if best is None:raise ValueError('no native floor under the one candidate can footprint')
    return {**best,'triangle_overlap_polygons':pair_count,'height_trials':0}

def ray_height(vertices,faces,xy,*,highest):
    hits=[]
    for polygon,plane,lo,hi,index in vertical_triangles(vertices,faces):
        if np.any(np.asarray(xy)<lo) or np.any(np.asarray(xy)>hi):continue
        if all(np.cross(b-a,np.asarray(xy)-a)>=-1e-12 for a,b in zip(polygon,np.roll(polygon,-1,axis=0))):hits.append(float(np.r_[xy,1]@plane))
    if not hits:raise ValueError('native vertical ray has no intersection')
    return max(hits) if highest else min(hits)
