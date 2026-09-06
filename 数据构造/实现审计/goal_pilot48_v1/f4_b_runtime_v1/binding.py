"""CPU-only, single B payload binding; no execution authority or fabricated gates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from controlled_multi_future.canonical_artifact import canonical_hash_json as digest
from controlled_multi_future.planner_qualification_manifests_v2_3 import build_f4_program_panel_manifest_v1_1
from controlled_multi_future.f4_stage_b_geometry_contract_v2 import audit_f4_stage_b_candidate_geometry_v2
from controlled_multi_future.f4_post_stage0_layout_v1 import LAYOUT

AUDIT = Path(__file__).resolve().parents[2]
PROPOSAL = AUDIT / 'F4_PILOT_B_NEW_LAYOUT_CPU_PROPOSAL_V1_20260906.json'
PROPOSAL_RECEIPT = '39c1f6238014b0959f43d4d4748391dd79b7c1528703c5609f0039a428984e0f'
SEED = 2026090604
ROOT_ID = 'f4-pilot-B-layout-v1-20260906'
PROGRAMS = ('F4-ABC', 'F4-ACB', 'F4-BAC')

def seal(value, key='receipt_sha256'):
    result = deepcopy(value)
    result.pop(key, None)
    result[key] = digest(result)
    return result

def checked(value, key='receipt_sha256'):
    if not isinstance(value, dict):
        raise ValueError('mapping evidence required: ' + key)
    result = deepcopy(value)
    claimed = result.pop(key, None)
    if claimed != digest(result):
        raise ValueError('self-hash mismatch: ' + key)
    return deepcopy(value)

def payload():
    proposal = checked(json.loads(PROPOSAL.read_text(encoding='utf-8')))
    if proposal['receipt_sha256'] != PROPOSAL_RECEIPT:
        raise ValueError('single B proposal changed')
    panel = build_f4_program_panel_manifest_v1_1()
    source, slot = deepcopy(panel['source_candidate']), deepcopy(panel['candidates'][0])
    if (source['candidate_sha256'] != proposal['parent_A_source_candidate_sha256'] or
            slot['candidate_sha256'] != proposal['parent_A_slot_candidate_sha256']):
        raise ValueError('parent A lineage changed')
    old_source, old_slot = source['candidate_sha256'], slot['candidate_sha256']
    for role in ('A', 'B', 'C'):
        for field, old in (('new_source_layout', source['source_layout']), ('new_slot_poses', slot['slot_poses'])):
            expected = deepcopy(old[role]); expected[0] -= .01
            if proposal[field][role] != expected:
                raise ValueError('B must be exactly one fixed minus-1cm translation')
    source.update(candidate_id=ROOT_ID + '-source', source_layout=proposal['new_source_layout'],
                  source_layout_sha256=digest(proposal['new_source_layout']),
                  parent_candidate_sha256=old_source,
                  f1_15_of_15_execution_claim_applies_to_candidate=False)
    source['A_pregrasp_xyz_m'] = [source['source_layout']['A'][i] + source['grasp_policy']['pregrasp_offset_world_m'][i] for i in range(3)]
    half = source['block_half_extents_m'][0]
    xs = [pose[0] for pose in source['source_layout'].values()]
    source['minimum_pairwise_block_surface_clearance_m'] = min(abs(a-b)-2*half for i,a in enumerate(xs) for b in xs[i+1:])
    source = seal(source, 'candidate_sha256')
    geometry = audit_f4_stage_b_candidate_geometry_v2(source_layout=source['source_layout'],
        slot_poses=proposal['new_slot_poses'], corridor_policy=slot['corridor_policy'], arm=source['arm'])
    if not geometry['construction_valid']:
        raise ValueError('B geometry does not pass unchanged construction gate')
    slot.update(candidate_id=ROOT_ID + '-slots', source_grasp_candidate_id=source['candidate_id'],
                source_grasp_candidate_sha256=source['candidate_sha256'], slot_poses=proposal['new_slot_poses'],
                slot_poses_sha256=digest(proposal['new_slot_poses']), parent_candidate_sha256=old_slot,
                program_state_transition_audit=geometry,
                program_state_transition_audit_sha256=geometry['geometry_contract_sha256'])
    for field in ('construction_valid', 'construction_failure_codes', 'minimum_terminal_clearance_m', 'minimum_swept_clearance_m'):
        slot[field] = geometry[field]
    slot = seal(slot, 'candidate_sha256')
    layout = deepcopy(LAYOUT)
    layout.update(layout_version=ROOT_ID, object_poses=deepcopy(source['source_layout']),
                  slot_poses=deepcopy(slot['slot_poses']),
                  stage_a_source_grasp_candidate_sha256=source['candidate_sha256'],
                  stage_b_slot_corridor_candidate_sha256=slot['candidate_sha256'],
                  stage_b_corridor_policy=slot['corridor_policy'],
                  stage_a_slot_placeholders_fixed_not_searched=False)
    return seal(dict(schema_version='cmf_f4_b_payload_v1', source=source, slot=slot,
        scene_layout=layout, seed=SEED, root_id=ROOT_ID, proposal_receipt_sha256=PROPOSAL_RECEIPT,
        parent_scene_family='F4_A_B_correlated_pilot_family', qualification_status='pending_real_B_evidence',
        GPU_authorized=False, formal_data=False))

def validate_stage_a(receipt):
    row = checked(receipt)
    b = payload()
    required = {'rendered_visibility', 'A_pregrasp_grasp_lift_planner',
                'B_pregrasp_grasp_lift_planner', 'C_pregrasp_grasp_lift_planner', 'all_roles_return_one_neutral'}
    if (row.get('schema_version') != 'cmf_f4_b_source_stage_a_evidence_v1' or
        row.get('source_candidate_sha256') != b['source']['candidate_sha256'] or
        row.get('payload_sha256') != b['receipt_sha256'] or row.get('scene_seed') != SEED or
        not row.get('scene_instance_id') or row.get('physical_execution_count') != 0 or
        set(row.get('checks', {})) != required or not all(row['checks'].values()) or
        row.get('status') != 'B_SOURCE_STAGE_A_PASS' or
        not isinstance(row.get('planner_query_count'), int) or not 0 < row['planner_query_count'] <= 48):
        raise ValueError('fresh exact B Stage-A qualification required; A/synthetic forbidden')
    return row

def runtime_spec(purpose='f4_stage_a_planner', *, stage_a=None):
    if purpose not in ('f4_stage_a_planner', 'f4_stage_b_planner'):
        raise ValueError('unsupported B runtime purpose')
    if purpose == 'f4_stage_a_planner' and stage_a is not None:
        raise ValueError('Stage-A input cannot contain success evidence')
    if purpose == 'f4_stage_b_planner':
        stage_a = validate_stage_a(stage_a)
    b = payload()
    return seal(dict(schema_version='cmf_f4_b_runtime_spec_v1', implementation_version='f4_b_runtime_v1',
        slot_id=ROOT_ID, family='F4', arm=b['source']['arm'], seed=SEED,
        generator='fixed_B_minus_1cm_scene_v1', purpose=purpose,
        f4_source_grasp_candidate_v1=b['source'], f4_source_grasp_candidate_sha256=b['source']['candidate_sha256'],
        f4_stage_b_candidate_v1=b['slot'], f4_stage_b_candidate_sha256=b['slot']['candidate_sha256'],
        scene_layout=b['scene_layout'], scene_layout_sha256=digest(b['scene_layout']),
        b_payload_sha256=b['receipt_sha256'], f4_b_source_stage_a_evidence=stage_a,
        automatic_retry=False, recovery_attempts=0, formal_data=False, stage0_data=False,
        stage1_authorized=False), 'planned_scope_spec_sha256')

def validate_runtime(value):
    row = checked(value, 'planned_scope_spec_sha256')
    expected = runtime_spec(row['purpose'], stage_a=row.get('f4_b_source_stage_a_evidence'))
    if row != expected:
        raise ValueError('B runtime payload/seed/layout changed')
    return expected
