"""Supplement pair-presence with measured contact geometry; zero impulse is not no support for sleeping bodies."""
import json
from pathlib import Path
import numpy as np
from reconcile import tail_contacts,sha,write
B=Path(__file__).parent
rows=[]
for file in sorted(B.glob('F2-*_cells.json')):
 for cell in json.loads(file.read_text()):
  print('CONTACT',cell['cell'],flush=True);frames=tail_contacts(cell['trace']);stats={}
  for name in ['f2_redesign_box_bottom','f2_redesign_scale','f2_redesign_stand','table']:
   points=[];impulses=[];seen=0
   for frame in frames:
    pairs=[p for p in frame if {p.get('body_a'),p.get('body_b')}=={'f2_redesign_can',name}]
    seen+=bool(pairs)
    for pair in pairs:
     impulses.append(float(pair.get('impulse_norm_sum',0)))
     points.extend(pair.get('point_evidence',[]))
   seps=[p['signed_separation_m'] for p in points if p.get('signed_separation_available')]
   zs=[p['position'][2] for p in points if 'position' in p];norms=[abs(p['normal'][2]) for p in points if 'normal' in p]
   stats[name]={'pair_presence_fraction':seen/len(frames),'min_signed_separation_m':min(seps) if seps else None,'max_signed_separation_m':max(seps) if seps else None,'point_z_range':[min(zs),max(zs)] if zs else None,'max_abs_normal_z':max(norms) if norms else None,'max_reported_pair_impulse':max(impulses) if impulses else None}
  rows.append({'cell':cell['cell'],'trace_sha256':sha(cell['trace']),'last_window_frames':50,'contact_geometry':stats});write(B/'CONTACT_DETAILS.json',{'cells':rows,'note':'Pair presence alone can include positive-separation contact-offset neighbours. Support conclusions use geometry, persistence, release and rest together; no new impulse cutoff or sleep assumption is introduced.'})
