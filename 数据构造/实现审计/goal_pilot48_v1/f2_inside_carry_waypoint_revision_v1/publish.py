"""Immutable CPU evidence generator, no solver/scene/resource reservation."""
import json
from pathlib import Path
from .analyze import analyze,digest,sha

def publish():
    root=Path(__file__).parent;r=analyze();r.pop('receipt_sha256')
    r['analysis_source_files']={str(root/'analyze.py'):sha(root/'analyze.py')};r['receipt_sha256']=digest(r)
    with (root/'CPU_REVIEW.json').open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    return {'receipt_sha256':r['receipt_sha256'],'native':r['native_continuous_straight_carry']['minimum_separating_axis_gap_m'],
      'sphere_buffer':r['actual_fitted_buffered_sphere_straight_carry']['minimum_separating_axis_gap_m'],'sphere_pass':r['actual_fitted_buffered_sphere_straight_carry']['pass']}

if __name__=='__main__':print(publish())
