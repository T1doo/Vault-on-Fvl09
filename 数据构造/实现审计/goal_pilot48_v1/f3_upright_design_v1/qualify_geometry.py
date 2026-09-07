"""Bounded CPU A-first/B-only-if-needed comparison; does not freeze a winner."""
import json,sys
from pathlib import Path
import numpy as np
from .geometry import Geometry,A
sys.path[:0]=[str(A),str(A/'代码审阅快照')]
from realization_utf8_io_v1 import write_new
def candidate(g,name,station):
    actual=[-.18,-.20,.75+station,2**-.5,0.,0.,2**-.5]
    touches={f:g.first_touch(actual,f) for f in ('fl_link7','fl_link8')}
    support=[{'opening':q,'hits':g.support_clear(actual,q)} for q in (.045,.038125,.03125,.024375,.0175)]
    return {'candidate':name,'station_local_y_m':station,'desired_actual_flange_world_pose':actual,'approach_direction_world':[0,1,0],
        'contact_depth_from_flange_m':.14,'first_native_contacts':touches,'support_closure_samples':support,
        'palm_bottle_hits':[p for p in g.pairs(actual,.0175) if p['hand']=='fl_link6'],
        'all_open_clear':all(v['open_clear'] for v in touches.values()),'both_sides_reachable':all(v.get('contact_reachable') for v in touches.values()),
        'physical_stability_not_proven':True}
def main():
    g=Geometry();a=candidate(g,'A_neck_flange',.220)
    # A requires first actual side contact to be neck, not cap/shoulder interception.
    bands=[v.get('contact_local_y_minmax_m') for v in a['first_native_contacts'].values()]
    a['neck_first_contact_necessary_pass']=all(b is not None and b[0]>=.215 and b[1]<=.222 for b in bands)
    rows=[a]
    if not a['neck_first_contact_necessary_pass']:rows.append(candidate(g,'B_upper_straight_body',.170))
    write_new(Path(__file__).parent/'candidate_geometry_audit.json',{'candidates':rows,'GPU':False,'Scene_created':False,'no_design_frozen_yet':True})
    for r in rows:print(json.dumps({k:v for k,v in r.items() if k not in ('support_closure_samples','palm_bottle_hits')}))
if __name__=='__main__':main()
