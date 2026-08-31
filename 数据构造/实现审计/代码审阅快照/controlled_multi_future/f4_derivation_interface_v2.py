"""Closure-V1 F4 planner target derivation interface validator.

Normalizes the historical A-role special case (which had no top-level pass)
and rejects scalar/sentinel/non-finite/non-pose targets before any IK query.
"""
from __future__ import annotations
import hashlib,json
from typing import Any,Mapping
import numpy as np
from .current_hasher import hash_json
SCHEMA_VERSION="cmf_f4_derivation_interface_v2"
def _target_hash(targets):
 normalized=[]
 for i,item in enumerate(targets):
  if not isinstance(item,Mapping):raise ValueError(f"target {i} is not mapping")
  sid=item.get("segment_id");pose=np.asarray(item.get("pose"),dtype=np.float64)
  if not isinstance(sid,str) or not sid or pose.shape!=(7,) or not np.all(np.isfinite(pose)):raise ValueError(f"target {i} must be finite shape-(7,)")
  if float(np.linalg.norm(pose[3:]))<=1e-12:raise ValueError(f"target {i} quaternion invalid")
  normalized.append({"segment_id":sid,"pose":pose.tolist()})
 return hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest(),normalized
def validate_f4_derivation_interface_v2(derived:Mapping[str,Any],*,role:str,selected_candidate:Mapping[str,Any]):
 if not isinstance(derived,Mapping) or role not in ("A","B","C"):raise ValueError("F4 derivation mapping/role invalid")
 if derived.get("role")!=role or derived.get("selected_candidate_id")!=selected_candidate.get("candidate_id"):raise ValueError("F4 derivation identity mismatch")
 targets=derived.get("targets")
 if not isinstance(targets,list) or len(targets)<7:raise ValueError("F4 derivation targets missing")
 target_hash,normalized=_target_hash(targets);ids=[x["segment_id"] for x in normalized]
 structure=ids[0]==f"{role}_pregrasp" and ids[1]==f"{role}_grasp" and any(x==f"{role}_release" for x in ids) and ids[-1]==f"{role}_neutral" and all(x.startswith(role+"_") for x in ids)
 if role=="A":
  gate=derived.get("preplanner_gate");source_pass=isinstance(gate,Mapping) and gate.get("pass") is True and gate.get("candidate_contract_target_pose_sha256")==gate.get("applied_planner_target_pose_sha256")
 else:
  payload=dict(derived);digest=payload.pop("receipt_sha256",None);source_pass=derived.get("pass") is True and isinstance(digest,str) and hash_json(payload)==digest and derived.get("target_pose_sha256")==target_hash
 checks={"mapping_not_scalar_or_sentinel":True,"finite_shape7_all":True,"segment_structure":structure,"source_derivation_pass":source_pass,"candidate_application_hash_bound":isinstance(selected_candidate.get("candidate_application_sha256"),str),"target_hash_recomputed":True}
 result={"schema_version":SCHEMA_VERSION,"role":role,"selected_candidate_id":selected_candidate.get("candidate_id"),"selected_candidate_application_sha256":selected_candidate.get("candidate_application_sha256"),"targets":normalized,"target_pose_sha256":target_hash,"checks":checks,"pass":all(checks.values())}
 result["receipt_sha256"]=hash_json(result)
 if not result["pass"]:raise ValueError(f"F4 {role} derivation interface v2 failed: {checks}")
 return result
__all__=["validate_f4_derivation_interface_v2"]
