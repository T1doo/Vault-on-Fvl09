"""CPU contract construction. Never changes the archived parent contract."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

W = Path('/nfs_share/lijunhui')
A = W / 'Vault-on-Fvl09/数据构造/实现审计'
P = W / 'Robotwin2/project/RoboTwin'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def build_contract():
    sys.path.insert(0, str(A))
    from f2_inward_binding_and_route_state_v1 import build
    from semantic_target import corrected_contract
    c, _ = corrected_contract()
    c = copy.deepcopy(c)
    new = build()
    proposal = json.loads((A / 'F2_ENDPOINT_DIAGNOSIS_AND_ONE_LAYOUT_PROPOSAL_V1_20260906.json').read_text(encoding='utf-8'))['one_proposal']
    c['planned'] = new['planned']
    c['binding'] = new['binding']
    c['beside_candidate_xy_m'] = list(proposal['new_target_geometry_xy_m'])
    c['beside_template_actor_pose'] = np.asarray(proposal['new_can_actor_pose'], dtype=float)
    u = np.asarray(new['goals']['U_new'], dtype=float)
    d = np.asarray(new['goals']['D_new'], dtype=float)
    n = np.asarray(new['goals']['N'], dtype=float)
    hub = u.copy()
    hub[:2] = (c['sealed_prefix_end_eef_pose'][:2] + u[:2]) / 2
    hub[2] = max(float(c['sealed_prefix_end_eef_pose'][2]), float(u[2]))
    # Six geometry targets are required by the frozen live binding checker;
    # only four direct route targets are ever dispatched by this runtime.
    poses = [hub, u, d, u, hub, n]
    c['beside_targets'] = [dict(t, pose=p.tolist()) for t, p in zip(c['beside_targets'], poses)]
    c['beside_targets_sha256'] = digest(c['beside_targets'])
    c['inward_goals'] = copy.deepcopy(new['goals'])
    c['inward_contract'] = new
    validate_contract(c)
    return c

def validate_contract(c):
    n = c['inward_contract']
    if c['binding'] != n['binding'] or c['planned'] != n['planned']:
        raise ValueError('new planned/binding mismatch')
    if c['inward_goals'] != n['goals']:
        raise ValueError('dispatch goals differ from frozen inward goals')
    if c['binding']['layout_version'] != 'f2_beside_inward_layout_v1':
        raise ValueError('old layout')
    if c['planned']['new_current_anchor_lineage_required'] is not True:
        raise ValueError('new lineage missing')
    xy = c['binding']['layout_payload']['beside_candidate_xy_m'][2]
    if not np.allclose(c['beside_candidate_xy_m'], xy, rtol=0, atol=1e-12):
        raise ValueError('target coordinate mismatch')
    if digest(c['beside_targets']) != c['beside_targets_sha256']:
        raise ValueError('target hash mismatch')
    for index, goal in ((1, 'U_new'), (2, 'D_new'), (3, 'U_new'), (5, 'N')):
        if not np.allclose(c['beside_targets'][index]['pose'], n['goals'][goal], atol=1e-12, rtol=0):
            raise ValueError('old target under new binding')
    if [n[k] for k in ('IK_cap', 'trajectory_query_cap', 'scene_cap', 'physical_cap', 'raw_cap')] != [3, 4, 1, 0, 0]:
        raise ValueError('budget mismatch')
    return True
