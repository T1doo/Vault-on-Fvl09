"""Instance-level collection request accounting for active and F1 parent adapters.

Install before the orchestrator or realization collector can call adapter.scene.
No global source-class patch and no GPU imports are used. An attempt is consumed
before the original scene factory is entered, including factory/setup failures.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import functools
import re
import sys

_DISPATCH = ContextVar('cmf_collection_factory_dispatch_v1', default=None)

def collection_key(planned, phase, program, profile):
    if not isinstance(phase, str):
        raise ValueError('scene phase must be explicit')
    if not phase.startswith('strict_prefix_branch'):
        return None
    if not phase.startswith('strict_prefix_branch:') or not phase.split(':', 1)[1]:
        raise ValueError('malformed strict-prefix collection phase')
    pid = phase.split(':', 1)[1]
    if not isinstance(program, dict) or program.get('program_id') != pid:
        raise ValueError('collection phase/program mismatch')
    slot = planned.get('slot_id')
    family = planned.get('family')
    if not slot or family not in ('F1', 'F2', 'F3', 'F4'):
        raise ValueError('collection root/family missing')
    return (slot, family, pid, profile)

class AttemptContext:
    """Forward the original handle and cleanup receipt without changing type IDs."""
    def __init__(self, original, meter, record):
        self.original = original
        self.meter = meter
        self.record = record

    def __getattr__(self, name):
        return getattr(self.original, name)

    def __enter__(self):
        if self.record['state'] != 'factory_returned':
            raise RuntimeError('one collection context may enter only once')
        self.record['state'] = 'entering'
        self.meter.event('COLLECTION_CONTEXT_ENTER', **self.record)
        try:
            handle = self.original.__enter__()
        except BaseException as exc:
            self.record['state'] = 'failed_enter'
            self.meter.event('COLLECTION_CONTEXT_ENTER_FAILED', **self.record, error_type=type(exc).__name__, error=str(exc))
            raise
        self.record['state'] = 'entered'
        self.meter.event('COLLECTION_CONTEXT_ENTERED', **self.record, scene_instance_id=getattr(handle, 'scene_instance_id', None))
        return handle

    def __exit__(self, exc_type, exc, tb):
        if self.record['state'] != 'entered':
            raise RuntimeError('collection context exit without completed entry')
        try:
            suppress = self.original.__exit__(exc_type, exc, tb)
        except BaseException as cleanup_error:
            self.record['state'] = 'failed_exit'
            self.meter.event('COLLECTION_CONTEXT_EXIT_FAILED', **self.record, error_type=type(cleanup_error).__name__, error=str(cleanup_error))
            raise
        self.record['state'] = 'exited'
        self.meter.event('COLLECTION_CONTEXT_EXITED', **self.record,
                         body_error_type=None if exc_type is None else exc_type.__name__,
                         body_error_suppressed=bool(suppress))
        return suppress

class CollectionHook:
    def __init__(self, adapter, meter, *, source_profile_sha256):
        if not re.fullmatch('[0-9a-f]{64}', source_profile_sha256):
            raise ValueError('exact source profile hash required')
        actual = getattr(adapter, '_sealed_implementation_source_sha256', None)
        if actual != source_profile_sha256:
            raise ValueError('adapter source profile differs from manifest')
        if '_cmf_collection_hook_v1' in vars(adapter):
            raise ValueError('adapter already instrumented')
        self.adapter, self.meter, self.profile = adapter, meter, source_profile_sha256
        self.original = adapter.scene
        self.had_override = 'scene' in vars(adapter)
        self.old_override = vars(adapter).get('scene')
        self.records = []
        self.closed = False

        @functools.wraps(self.original)
        def factory(planned_root_slot_spec, *, phase, program=None):
            key = collection_key(planned_root_slot_spec, phase, program, self.profile)
            if key is None:
                return self.original(planned_root_slot_spec, phase=phase, program=program)
            outer = _DISPATCH.get()
            if outer is not None:
                # Wrapper/super delegation is not a new collection. A nested
                # different root/program is not assumed free: fail closed.
                if outer != key:
                    raise RuntimeError('nested factory changed collection identity')
                return self.original(planned_root_slot_spec, phase=phase, program=program)
            fields = dict(zip(('slot_id', 'family', 'program_id', 'source_profile_sha256'), key))
            fields['phase'] = phase
            fields['adapter_class'] = type(adapter).__module__ + '.' + type(adapter).__name__
            # CHARGE persists before context construction. Do not refund on
            # factory error, missing current, prefix failure or absent raw.
            meter.charge('collection_attempts', 1, **fields)
            record = {**fields, 'collection_attempt_ordinal': meter.counts['collection_attempts'], 'state': 'factory_entered'}
            self.records.append(record)
            token = _DISPATCH.set(key)
            try:
                context = self.original(planned_root_slot_spec, phase=phase, program=program)
            except BaseException as exc:
                record['state'] = 'failed_factory'
                meter.event('COLLECTION_FACTORY_FAILED', **record, error_type=type(exc).__name__, error=str(exc))
                raise
            finally:
                _DISPATCH.reset(token)
            record['state'] = 'factory_returned'
            meter.event('COLLECTION_FACTORY_RETURNED', **record)
            return AttemptContext(context, meter, record)

        self.factory = factory
        adapter.scene = factory
        adapter._cmf_collection_hook_v1 = self

    def close(self):
        if self.closed:
            return
        if vars(self.adapter).get('scene') is not self.factory or vars(self.adapter).get('_cmf_collection_hook_v1') is not self:
            raise RuntimeError('collection hook was replaced; cannot silently restore')
        active = [r for r in self.records if r['state'] in ('entering', 'entered')]
        if active:
            raise RuntimeError('collection context remains active during hook cleanup')
        for r in self.records:
            if r['state'] == 'factory_returned':
                self.meter.event('COLLECTION_CONTEXT_NEVER_ENTERED', **r)
        if self.had_override:
            self.adapter.scene = self.old_override
        else:
            delattr(self.adapter, 'scene')
        delattr(self.adapter, '_cmf_collection_hook_v1')
        self.closed = True

@contextmanager
def instrument_adapter(adapter, meter, *, source_profile_sha256):
    hook = CollectionHook(adapter, meter, source_profile_sha256=source_profile_sha256)
    try:
        yield adapter
    finally:
        hook.close()

@contextmanager
def instrument_collector_factory(pipeline_module, meter, *, profile_for_cell):
    """Versioned wrapper for pipeline's imported make_adapter binding.

    Patching catalog.make_adapter alone is insufficient: pipeline imported it
    by value. Restore the exact original binding after all collect_cell calls.
    """
    original = pipeline_module.make_adapter
    hooks = []
    @functools.wraps(original)
    def make_adapter(cell, output):
        adapter = original(cell, output)
        hooks.append(CollectionHook(adapter, meter, source_profile_sha256=profile_for_cell(cell)))
        return adapter
    pipeline_module.make_adapter = make_adapter
    try:
        yield
    finally:
        if pipeline_module.make_adapter is not make_adapter:
            raise RuntimeError('collector factory binding changed while instrumented')
        pipeline_module.make_adapter = original
        for hook in reversed(hooks):
            hook.close()
