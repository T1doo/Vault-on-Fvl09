# Collection attempt accounting review v1

Status: CPU implemented/tested only. Not installed in the running Goal dispatcher.
No frozen source, running job, ledger or existing manifest was changed.

## Actual entry points

- Active `root_orchestrator_v1_2.py:1561` calls inherited `_scene_call` for each
  `strict_prefix_branch:{program_id}`. Its parent v1.1 `_scene_call:447` invokes
  `adapter.scene(...)`, before entering the returned context or branch callback.
- `realization_batch_runtime_v1_3/pipeline.py:99` likewise calls
  `adapter.scene(..., phase='strict_prefix_branch:'+program['program_id'])`.
  Same-current, anchor, prefix, planning, action, verifier and raw publication all
  occur later. Failure at any of those stages must not refund the attempt.
- `RoboTwinSceneContextV1_2` only creates/setup the real scene inside `__enter__`.
  Charging before the original adapter factory therefore precedes scene creation.
- Pristine, task feasibility, canonical prefix and suffix preflight are not raw
  collection attempts. They still consume their independently metered scene,
  action and solver resources. An accepted new r_pc root normally consumes three
  collection attempts, not one per prerequisite and not one per written file.
- Older non-strict root v1.1 uses `rollout:{program_id}`. The supplied hook does
  NOT claim coverage of that different entry. A new runner must reject unsupported
  collector versions, not silently treat their collections as zero.

`audit_sources.py` reports exact current source hashes and AST dispatch line
numbers without loading simulator classes.

## Hook and counting rule

`helper.CollectionHook` wraps the concrete adapter instance's `scene` method.
It preserves the adapter class and passes the original context handle unchanged.
The strict-branch factory request charges `collection_attempts` once before the
original factory. Cap exhaustion prevents entry into that factory.

Factory failure, setup failure, same-current failure before any action, prefix
failure, solver failure, verifier failure and publication failure retain the
charge. A requested context that is never entered also remains an attempted
collection, with a separate event. Preparatory failure before the collector has
requested a strict-branch context is zero *scene-request collection attempts*,
but must remain a separately logged infrastructure failure; it is not success.

Nested wrapper/super factory delegation with the same root/program/profile uses
a ContextVar to avoid double charging. A nested changed identity is rejected.
Sequential calls for the same root/program are distinct attempts and each charge.
One returned context cannot enter twice. Original cleanup_receipt and handle
identity are preserved. Uninstall while a context is active fails closed.

## Minimal integration in a new version

1. Expose the existing live Meter object to the new family runtime (for example
   a new dispatcher passes `run(manifest, meter=...)`). Do not create a second
   independent meter or patch the currently running dispatcher.
2. Root path: construct and source-validate its actual adapter, then wrap the
   whole orchestrator call with `instrument_adapter(adapter, meter,
   source_profile_sha256=manifest_profile)`.
3. Realization path: wrap its calls using
   `instrument_collector_factory(pipeline, meter, profile_for_cell=...)`.
   The hook patches the pipeline's imported `make_adapter` binding, not just
   `catalog.make_adapter`, because the pipeline imported that function by value.
4. Bind this helper plus new dispatcher/runtime/source-profile map into a NEW
   manifest version. Reserve collection attempts independently of scene/action
   counts. Old F1/F4 completed outputs and Goal jobs remain untouched.
5. Before closing Meter, verify each requested strict branch has one CHARGE and
   one lifecycle outcome, no context remains entered, and all branch requests in
   the orchestrator/cell ledger match the collection charge ledger. Raw count and
   accepted count may be less than attempts and must be reported separately.
6. Test live integration on the next genuinely authorized remaining collection,
   not a rerun of accepted cells for accounting tests.

## Source-profile boundary and additional gap

F1 historical A/B adapters live under `cmf_parent_f1_9873`, source
`9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72`.
Other current families use active source
`3ec56ec08c39b15615538e5bde48e485d535ae10e7e1f7962254f146d32943f7`.
Patching only an active adapter base class misses F1; instance wrapping avoids
that class-identity problem without changing reconstruction-source hashes.

Additional audited risk: the frozen Meter patches the ACTIVE DenseTraceMixin,
while the old F1 namespace creates its own DenseTraceMixin-derived scene class.
Those are different Python classes. Fresh-scene Base_Task hooks are shared, but
this does not prove old-F1 dense-action coverage. A new F1 dispatcher must also
instrument the actual instance's dense-action method or the exact namespaced
class and deduplicate action-scene charges against Base_Task.move. The collection
helper does not claim to solve that separate action counter gap.

## CPU tests

Ten tests pass: pre-factory charge, class/handle/cleanup preservation, factory and
setup failures, pre-action current failure, prerequisite exclusion, repeated
attempts, nested delegation, pre-factory cap rejection, source-profile mismatch,
factory restoration, never-entered and double-enter protection.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计 /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest goal_pilot48_v1.collection_meter_review_v1.test_cpu -v
```

No CUDA imports or GPU operations occur in this helper/test suite.
