"""Clarify source-capture metadata versus projected world pose; no model rerun."""
import json,sys,hashlib,copy
from pathlib import Path
import numpy as np
import transforms3d as t3d
A=Path('/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计');sys.path.insert(0,str(A/'f2_f3_model_bridge_v1_1'));sys.path.insert(1,str(A))
from geometry import matrix,digest
from realization_utf8_io_v1 import write_new
def main():
    path=A/'F3_POSTCLOSE_REPLAY_INPUT_V1_20260906.json';d=json.loads(path.read_text(encoding='utf-8'));B=matrix(d['world_base_pose']);rows=[]
    for old in d['world_export']['shapes']:
        T=B@matrix(old['solver_pose'])@np.linalg.inv(matrix(old['shape_local_pose']))
        row={k:copy.deepcopy(old[k]) for k in ('name','role','kind','vertices','faces','solver_pose','shape_local_pose','collision_groups','contact_offset','rest_offset')}
        row['actor_world_pose']=np.r_[T[:3,3],t3d.quaternions.mat2quat(T[:3,:3])].tolist()
        row['source_capture_metadata']={k:copy.deepcopy(v) for k,v in old.items() if k not in ('vertices','faces','solver_pose')}
        row['projection_provenance']='original replay solver_pose unchanged; actor pose derived from actual base and local shape; prior per-shape hash is a source-capture stamp, not projected self-hash'
        row['geometry_sha256']=digest(row)
        for k in ('name','vertices','faces','solver_pose'):assert row[k]==old[k]
        rows.append(row)
    out={'schema_version':'cmf_support_model_projection_metadata_overlay_v1','source_file':str(path),'source_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'original_bytes_changed':False,
        'solver_relevant_fields_byte_value_equivalent':True,'GPU_validation_or_plan_rerun':False,'world_export':{'shapes':rows,'geometry_sha256':digest(rows)},
        'reason':'prepare projected solver poses but retained historical actor pose/per-shape hash metadata; separate those source fields explicitly without altering geometry used by successful GPU run'}
    write_new(A/'SUPPORT_MODEL_PROJECTION_METADATA_OVERLAY_V1_20260906.json',out);print('14 projected shape metadata records separated from source captures; model fields unchanged')
if __name__=='__main__':main()
