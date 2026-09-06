"""Composable B stage bindings. No scene opening, job signing, or gate fabrication."""
from copy import deepcopy
from types import FunctionType
from .binding import payload, runtime_spec, validate_runtime, checked, PROGRAMS

def planner_spec(program_id, *, slot_id, planner_reset_nonce):
    from controlled_multi_future.f4_program_planner_integration_v2 import build_f4_program_planner_spec_v2
    b = payload()
    return build_f4_program_planner_spec_v2(b['source'], b['slot'], program_id=program_id,
        slot_id=slot_id, planner_reset_nonce=planner_reset_nonce)

def bound_function(function, **overrides):
    """Private globals copy: never monkeypatch the imported production module."""
    globals_copy = dict(function.__globals__); globals_copy.update(overrides)
    result = FunctionType(function.__code__, globals_copy, function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result

def source_stage_a_runner(adapter):
    """Return original runner bound to exact B validator, without opening a scene.

    Caller supplies durable UTF-8 writer/meter/Guard before execution. This
    interface alone does not produce the B source qualification envelope.
    """
    from types import MethodType
    from controlled_multi_future.high_level_planner_runner_v1 import HighLevelPlannerRunnerV1
    if validate_runtime(adapter.planned_spec)['purpose'] != 'f4_stage_a_planner':
        raise ValueError('source qualification requires a Stage-A adapter')
    runner = HighLevelPlannerRunnerV1(adapter)
    runner.run = MethodType(bound_function(HighLevelPlannerRunnerV1.run,
        validate_f4_runtime_spec_v1=validate_runtime), runner)
    return runner

def physical_spec(terminal, *, stage_a, program_id, slot_id, planner_reset_nonce,
                  isolation_receipt_sha256=None, isolation_stage=None):
    b = payload(); scene_spec = runtime_spec('f4_stage_b_planner', stage_a=stage_a)
    def exact_runtime(candidate_id, *, purpose, stage_a_terminal):
        if candidate_id != b['slot']['candidate_id'] or purpose != 'f4_stage_b_planner' or stage_a_terminal != stage_a:
            raise ValueError('physical builder attempted a different B runtime binding')
        return deepcopy(scene_spec)
    if isolation_stage is None:
        from controlled_multi_future.f4_full_program_physical_v1 import build_f4_full_program_physical_spec_v1 as original
        kwargs = dict(program_id=program_id, slot_id=slot_id, planner_reset_nonce=planner_reset_nonce,
                      isolation_gate_receipt_sha256=isolation_receipt_sha256)
    else:
        from controlled_multi_future.f4_bounded_physical_micro_v1 import build_f4_bounded_physical_micro_spec_v1 as original, STAGES
        if STAGES[isolation_stage]['program_id'] != program_id:
            raise ValueError('isolation program mismatch')
        kwargs = dict(stage=isolation_stage, slot_id=slot_id, planner_reset_nonce=planner_reset_nonce)
    # The legacy helper name remains in the original code object, but receives
    # the real B evidence supplied above, never a synthetic passing terminal.
    function = bound_function(original, build_f4_runtime_spec_v1=exact_runtime,
        _f4_synthetic_stage_a_terminal=lambda: deepcopy(stage_a))
    return function(b['source'], b['slot'], terminal, **kwargs)

def root_prerequisites(*, stage_a, planner_envelopes, isolation, template):
    """Validate B provenance before constructing the reusable full specs."""
    spec = runtime_spec('f4_stage_b_planner', stage_a=stage_a)
    if set(planner_envelopes) != set(PROGRAMS):
        raise ValueError('all three exact B program sources required')
    for row, status in ((isolation, 'B_ALL_FIVE_ISOLATION_PASS'), (template, 'B_FULL_PROGRAM_TEMPLATE_PASS')):
        checked(row)
        if (row.get('status') != status or row.get('b_scene_spec_sha256') != spec['planned_scope_spec_sha256'] or
            row.get('b_payload_sha256') != spec['b_payload_sha256']):
            raise ValueError('B qualification receipt cannot be replaced by A')
    if template.get('isolation_receipt_sha256') != isolation['receipt_sha256']:
        raise ValueError('B template isolation lineage mismatch')
    isolation_rows = isolation.get('rows', [])
    if (len(isolation_rows) != 5 or {r.get('stage') for r in isolation_rows} !=
        {'A_ONLY','B_ONLY','C_ONLY','AB_NONINTERFERENCE','AC_NONINTERFERENCE'} or
        not all(r.get('physical_pass') is True and r.get('scene_receipt_sha256') for r in isolation_rows)):
        raise ValueError('five actual isolation receipts required')
    template_rows = template.get('rows', [])
    if (len(template_rows) != 3 or {r.get('program_id') for r in template_rows} != set(PROGRAMS) or
        not all(r.get('physical_pass') is True and r.get('scene_receipt_sha256') for r in template_rows) or
        template.get('same_current_pass') is not True or template.get('same_anchor_pass') is not True or
        template.get('final_state_equivalence', {}).get('equivalent') is not True):
        raise ValueError('three real template programs and equivalence required')
    full = {}
    for pid, envelope in planner_envelopes.items():
        prior = envelope['spec']; terminal = envelope['terminal']
        expected = planner_spec(pid, slot_id=prior['slot_id'], planner_reset_nonce=prior['planner_reset_nonce'])
        if prior != expected:
            raise ValueError('planner source spec is not exact B')
        full[pid] = physical_spec(terminal, stage_a=stage_a, program_id=pid,
            slot_id=prior['slot_id'], planner_reset_nonce=prior['planner_reset_nonce'],
            isolation_receipt_sha256=isolation['receipt_sha256'])
    return dict(planned_spec=spec, full_program_specs=full,
                qualification_evidence=dict(isolation=deepcopy(isolation), template=deepcopy(template)))
