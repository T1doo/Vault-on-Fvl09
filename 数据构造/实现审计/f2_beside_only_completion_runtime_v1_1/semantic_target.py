"""Frozen candidate-2 geometry-centre target, never actor-origin XY overwrite."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from controlled_multi_future.geometry import pose_matrix, compose_pose, actor_target_to_eef_pose, world_axis_offset_pose
from controlled_multi_future.f2_asset_bound_runtime_v3 import _actor_pose_centered_on_support

AUDIT=Path("/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计")
PROJECT=Path("/nfs_share/lijunhui/Robotwin2/project/RoboTwin")
OLD_PATH=AUDIT/"f2_controlled_insertion_route_gate_run1_runtime_v1/job_runner.py"
OLD_SHA="376a782ada5ee95b3e45b09a0af5314516004a4c360f4e9a8e3fb9647f5ace26"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(d): return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
if sha(OLD_PATH)!=OLD_SHA: raise ValueError("old scientific runner changed")
spec=importlib.util.spec_from_file_location("f2_beside_parent_runner",OLD_PATH)
old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)


def corrected_contract():
    c=old.load_sealed_contract()
    # Runtime actor.config uses model_data centre/extents scaled by 0.05.
    p=PROJECT/"assets/objects/071_can/model_data0.json"
    if sha(p)!="78eb137b42da2d6fa0b9208717964838e01cf6c65c5c6b14ad7c988d6ff2acfb":
        raise ValueError("model data changed")
    data=json.loads(p.read_text())
    center=np.asarray(data["center"],dtype=float)*.05
    half=np.asarray(data["extents"],dtype=float)*.05/2
    orientation=c["binding"]["layout_payload"]["main_object_orientation_wxyz"]
    xy=np.asarray(c["beside_candidate_xy_m"])
    # Derive frozen table plane from the previously frozen supported actor pose.
    # Translation from candidate0 to candidate2 changes no orientation/support height.
    template=c["beside_template_actor_pose"].copy()
    rotation=pose_matrix([0,0,0,*orientation])[:3,:3]
    offset=rotation@center
    plane=float(template[2]+offset[2]-np.dot(np.abs(rotation[2]),half))
    if not np.isclose(plane,float(c["binding"]["layout_payload"]["table_plane_z_m"]),atol=1e-12,rtol=0): raise ValueError("independent frozen support plane mismatch")
    pose=_actor_pose_centered_on_support(target_geometry_xy=xy,support_plane_z_m=plane,
                  orientation_wxyz=orientation,local_geometry_center_m=center,half_extents_m=half)
    composed=compose_pose(pose,[*center,1,0,0,0])
    if not np.allclose(composed[:2],xy,atol=1e-12,rtol=0): raise ValueError("geometry centre mismatch")
    # Independent translation of candidate0 origin must match canonical recomputation.
    translated=template.copy()
    candidate0=np.asarray(c["binding"]["layout_payload"]["beside_candidate_xy_m"][0])
    translated[:2]+=xy-candidate0
    if not np.allclose(translated,pose,atol=1e-9,rtol=0): raise ValueError("historical translation mismatch")
    release=actor_target_to_eef_pose(c["sealed_prefix_end_eef_pose"],c["sealed_prefix_end_actor_pose"],pose)
    pre=world_axis_offset_pose(release,.08)
    hub=pre.copy(); hub[:2]=(c["sealed_prefix_end_eef_pose"][:2]+pre[:2])/2
    hub[2]=max(float(c["sealed_prefix_end_eef_pose"][2]),float(pre[2]))
    targets=[{"segment_id":n,"pose":p.tolist()} for n,p in zip(old.BESIDE_SEGMENTS,
              (hub,pre,release,pre,hub,c["neutral_eef_pose"]))]
    wrong=template.copy(); wrong[:2]=xy
    artifact={"schema_version":"cmf_f2_beside_geometry_center_target_v1",
        "candidate_index":2,"candidate_geometry_xy":xy.tolist(),
        "local_center_m":center.tolist(),"half_extents_m":half.tolist(),"orientation":list(orientation),
        "support_plane_z_m":plane,"corrected_actor_pose":pose.tolist(),
        "composed_geometry_center_pose":composed.tolist(),"rotated_local_center":offset.tolist(),
        "old_xy_overwrite_position_error_m":float(np.linalg.norm(wrong[:3]-pose[:3])),
        "translated_candidate0_matches":True,"six_targets":targets,
        "targets_sha256":canonical(targets),"model_data_sha256":sha(p)}
    artifact["receipt_sha256"]=canonical(artifact)
    c["beside_template_actor_pose"]=pose
    c["beside_targets"]=targets
    c["beside_targets_sha256"]=artifact["targets_sha256"]
    return c,artifact


def derive_live_targets(scene,contract):
    # Reuse the sealed state restoration and unchanged geometry/threshold checks.
    # Only replace the incorrect actor-origin XY overwrite.
    import ast
    frozen=float(contract["binding"]["layout_payload"]["table_plane_z_m"])
    if not np.isclose(0.74+float(scene.table_z_bias),frozen,atol=1e-12,rtol=0):
        raise ValueError("live/frozen support plane mismatch")
    tree=ast.parse(OLD_PATH.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_derive_live_targets")
    source=ast.get_source_segment(OLD_PATH.read_text(),node)
    needle="expected[:2] = candidate_xy"
    if source.count(needle)!=1: raise ValueError("unexpected old derivation shape")
    source=source.replace(needle,"# corrected contract already freezes the compensated actor origin")
    ns=dict(old.__dict__)
    exec(compile(source,str(OLD_PATH)+":corrected-beside", "exec"),ns)
    return ns["_derive_live_targets"](scene,contract,"beside")
