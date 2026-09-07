"""CPU per-pixel barycentric orthographic depth test, no painter-order guess."""
import numpy as np
import cv2

def raster(coords,depths,colors,w,h):
    image=np.full((h,w,3),(245,247,250),np.uint8);z=np.full((h,w),-np.inf)
    for i in np.argsort(depths.mean(1))[::-1]:
        t=coords[i];xmin=max(0,int(np.floor(t[:,0].min())));xmax=min(w-1,int(np.ceil(t[:,0].max())))
        ymin=max(0,int(np.floor(t[:,1].min())));ymax=min(h-1,int(np.ceil(t[:,1].max())))
        if xmin>xmax or ymin>ymax:continue
        a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:continue
        xx=np.arange(xmin,xmax+1,dtype=float)[None,:]+.5;yy=np.arange(ymin,ymax+1,dtype=float)[:,None]+.5
        u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        inside=(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)
        zz=u*depths[i,0]+v*depths[i,1]+(1-u-v)*depths[i,2]
        target=z[ymin:ymax+1,xmin:xmax+1];mask=inside&(zz>target)
        target[mask]=zz[mask];image[ymin:ymax+1,xmin:xmax+1][mask]=colors[i]
    return image,z

def panel(triangles,colors,center,width_m,height_m,elev,azim,path):
    w,h=608,740;az,el=np.radians([azim,elev]);z=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    x=np.array([-np.sin(az),np.cos(az),0]);y=np.cross(z,x);scale=min(w/width_m,h/height_m)
    delta=triangles-center;depth=delta@z
    coords=np.stack((w/2+delta@x*scale,h/2-delta@y*scale),axis=-1)
    visible=(coords.max(1)[:,0]>=0)&(coords.min(1)[:,0]<w)&(coords.max(1)[:,1]>=0)&(coords.min(1)[:,1]<h)
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);norm=np.linalg.norm(normals,axis=1)
    shade=.58+.42*np.abs(normals@np.array([.3,-.4,.866])/np.maximum(norm,1e-12));shaded=np.clip(colors*shade[:,None],0,255).astype(np.uint8)
    canvas,depthbuffer=raster(coords[visible],depth[visible],shaded[visible],w,h)
    # The diagnostic executed path is explicitly an overlay, not opaque scene geometry.
    if len(path)>1:
        q=path-center;points=np.rint(np.stack((w/2+q@x*scale,h/2-q@y*scale),axis=-1)).astype(np.int32)
        cv2.polylines(canvas,[points],False,(65,65,190),2,cv2.LINE_AA)
    cv2.rectangle(canvas,(0,0),(w-1,h-1),(185,195,205),2);return canvas
