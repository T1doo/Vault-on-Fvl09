# F2 inward endpoint revision1 runtime v2

CPU ready, GPU revision1 qualification pending. No GPU/Goal reservation/issuer
or common runtime change was made by this subtask.

Only the frozen `f2_inward_failure_review_v1/proposal_revision1.json` with SHA
`1060352374547715c7d2b88eab97d3d56061a16c891d45cf1ea69d9bcbe7a3b1`
is accepted. New layout is `f2_goal_inward_endpoint_revision1`; new planned slot
is `f2-goal-inward-endpoint-revision1-planner-only-20260907`. Seed stays fixed:
the registered change is layout, not an additional seed search.

`contract.build_contract()` applies the same derived translation to stand,
all beside coordinates and selected target. It regenerates layout payload,
binding, planned spec and geometry target hashes. All three relation programs
share that new binding/current requirement. No old inside success is adopted.
C/N, orientation/z, grasp transform, assets, 80mm U-D, seedbank/iterations,
carry/release mechanics and physical verifiers remain unchanged.

`runtime.py` loads the already GPU-checked v1 runtime source with exact SHA
`b660f4145c767fa13509a1a7a134caf0f125e52c1fa7701c4227a638bb801654`
into a private module namespace that is NOT inserted into `sys.modules`. Only
its private `build_contract` binding changes. No shared imported function or
module globals are temporarily patched. Original v1 callers continue to build
the old layout. Every v1 state-machine/IK/route/cleanup function executes using
the private globals and unchanged source. The new lineage receipt is written
before adapter/scene construction.

Main-thread issuer integration:

```python
from goal_pilot48_v1.f2_inward_runtime_v2.dependencies import additional_bindings
extra = additional_bindings()
# Retain and verify inward001's complete dependency maps first.
m['source_files'].update(extra['additional_source_files'])
m['input_files'].update(extra['additional_input_files'])
m.update(extra['manifest_fields'])
job.update(runtime_module=extra['runtime_module'],
           runtime_file=extra['runtime_file'],
           test_module=extra['test_module'])
```

Four top-level `f2_revision1_*` hashes are mandatory. Missing/old hashes are
rejected inside the actual run lifecycle before scene creation, with a failed
terminal rather than fallback to old goals. The caller still must issue a NEW
Goal job ID/reservation/output namespace and rehash/publish its manifest.

Budget remains 3 IK plus conditional 4 trajectory = 7 solver, 1 scene,
0 action, 0 collection, no accepted root/raw. New bridge uses the exact v1
meter reconciliation for IK/trajectory partitions and all other counters.

CPU preflight: 12 tests pass, including the actual run entry constructing the
new binding before a fake adapter constructor stops it, missing manifest
lineage rejection, private-globals isolation, old goal rejection, complete
meter counter bridge, and all six original state-machine tests.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计:/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest goal_pilot48_v1.f2_inward_runtime_v2.test_cpu -v
```

As always, pin native caches inside Robotwin2 before the command. Actual GPU
cache/lock/constraint checks and Guard/UUID/pre-post/cleanup remain mandatory.
