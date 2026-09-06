import types
import unittest
from .helper import CollectionHook, instrument_adapter, instrument_collector_factory

CURRENT = '3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7'
F1 = '9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72'

class Meter:
    def __init__(self, cap=9):
        self.cap = cap
        self.counts = {'collection_attempts': 0, 'action_scenes': 0, 'fresh_scenes': 0}
        self.events = []
    def event(self, kind, **fields):
        self.events.append({'kind': kind, **fields})
    def charge(self, key, amount=1, **fields):
        if self.counts[key] + amount > self.cap:
            raise RuntimeError('cap exceeded before original factory')
        self.counts[key] += amount
        self.event('CHARGE', resource=key, amount=amount, **fields)

class Context:
    def __init__(self, *, fail_enter=False):
        self.fail_enter = fail_enter
        self.enter_count = 0
        self.exit_count = 0
        self.cleanup_receipt = None
        self.handle = types.SimpleNamespace(scene_instance_id='cpu-scene', scene=object())
    def __enter__(self):
        self.enter_count += 1
        if self.fail_enter:
            self.cleanup_receipt = {'cleanup_safety_pass': True}
            raise RuntimeError('setup failed before action')
        return self.handle
    def __exit__(self, *args):
        self.exit_count += 1
        self.cleanup_receipt = {'cleanup_safety_pass': True}
        return False

class Adapter:
    def __init__(self, source=CURRENT, *, fail_factory=False, fail_enter=False):
        self._sealed_implementation_source_sha256 = source
        self.calls = 0
        self.fail_factory = fail_factory
        self.fail_enter = fail_enter
    def scene(self, planned_root_slot_spec, *, phase, program=None):
        self.calls += 1
        if self.fail_factory:
            raise ValueError('context constructor failed')
        return Context(fail_enter=self.fail_enter)

def branch(adapter, slot='root-a'):
    return adapter.scene({'slot_id': slot, 'family': 'F4'}, phase='strict_prefix_branch:F4-ABC', program={'program_id': 'F4-ABC'})

class CollectionTests(unittest.TestCase):
    def test_charge_precedes_factory_and_preserves_adapter_type_handle_cleanup(self):
        adapter = Adapter()
        meter = Meter()
        with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
            self.assertIs(type(adapter), Adapter)
            context = branch(adapter)
            self.assertEqual(meter.counts['collection_attempts'], 1)
            self.assertEqual(context.original.enter_count, 0)
            with context as h:
                self.assertIs(h, context.original.handle)
            self.assertTrue(context.cleanup_receipt['cleanup_safety_pass'])
        self.assertNotIn('scene', vars(adapter))

    def test_factory_and_setup_failures_still_count_without_action(self):
        for kw in ({'fail_factory': True}, {'fail_enter': True}):
            meter = Meter(); adapter = Adapter(**kw)
            with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
                with self.assertRaises((ValueError, RuntimeError)):
                    with branch(adapter): pass
            self.assertEqual(meter.counts['collection_attempts'], 1)
            self.assertEqual(meter.counts['action_scenes'], 0)

    def test_failed_current_before_motion_counts_once(self):
        meter = Meter(); adapter = Adapter()
        with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
            with self.assertRaisesRegex(ValueError, 'same-current'):
                with branch(adapter): raise ValueError('same-current mismatch')
        self.assertEqual(meter.counts['collection_attempts'], 1)
        self.assertEqual(meter.counts['action_scenes'], 0)

    def test_prerequisites_never_charge_collection(self):
        meter = Meter(); adapter = Adapter()
        with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
            for phase in ('pristine', 'task_physical_feasibility:F4-ABC', 'canonical_prefix_reference', 'suffix_preflight:F4-ABC'):
                with adapter.scene({'slot_id': 'x', 'family': 'F4'}, phase=phase, program={'program_id': 'F4-ABC'}): pass
        self.assertEqual(meter.counts['collection_attempts'], 0)

    def test_same_root_new_attempt_is_not_deduplicated(self):
        meter = Meter(); adapter = Adapter()
        with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
            for _ in range(2):
                with branch(adapter): pass
        self.assertEqual(meter.counts['collection_attempts'], 2)

    def test_nested_factory_delegation_counts_once(self):
        meter = Meter(); inner = Adapter()
        outer = Adapter()
        outer.scene = inner.scene
        with instrument_adapter(inner, meter, source_profile_sha256=CURRENT):
            # Bind to the currently wrapped inner factory, as a proxy would.
            outer.scene = inner.scene
            with instrument_adapter(outer, meter, source_profile_sha256=CURRENT):
                with branch(outer): pass
        self.assertEqual(meter.counts['collection_attempts'], 1)
        self.assertEqual(inner.calls, 1)

    def test_cap_stops_before_original_factory(self):
        meter = Meter(cap=0); adapter = Adapter()
        with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
            with self.assertRaises(RuntimeError): branch(adapter)
        self.assertEqual(adapter.calls, 0)

    def test_source_profile_not_collapsed_and_double_hook_rejected(self):
        adapter = Adapter(source=F1); meter = Meter()
        with self.assertRaises(ValueError): CollectionHook(adapter, meter, source_profile_sha256=CURRENT)
        with instrument_adapter(adapter, meter, source_profile_sha256=F1):
            with self.assertRaises(ValueError): CollectionHook(adapter, meter, source_profile_sha256=F1)
            with branch(adapter): pass
        charge = next(x for x in meter.events if x['kind'] == 'CHARGE')
        self.assertEqual(charge['source_profile_sha256'], F1)

    def test_pipeline_imported_factory_restored(self):
        meter = Meter()
        original = lambda cell, output: Adapter(source=cell['source'])
        pipeline = types.SimpleNamespace(make_adapter=original)
        with instrument_collector_factory(pipeline, meter, profile_for_cell=lambda c: c['source']):
            for source in (CURRENT, F1):
                adapter = pipeline.make_adapter({'source': source}, None)
                with branch(adapter): pass
        self.assertIs(pipeline.make_adapter, original)
        self.assertEqual(meter.counts['collection_attempts'], 2)

    def test_unentered_context_retained_as_attempt_and_cannot_reenter(self):
        meter = Meter(); adapter = Adapter()
        with instrument_adapter(adapter, meter, source_profile_sha256=CURRENT):
            branch(adapter)
            context = branch(adapter)
            with context: pass
            with self.assertRaises(RuntimeError): context.__enter__()
        self.assertEqual(meter.counts['collection_attempts'], 2)
        self.assertTrue(any(x['kind'] == 'COLLECTION_CONTEXT_NEVER_ENTERED' for x in meter.events))

if __name__ == '__main__': unittest.main()
