# F2 runtime v3: fixed-layout endpoint-route revision1

Only U height and derived geometry hub/route targets change. D, C, N, stand,
layout payload, binding, planned slot, scene seed and the three relation programs
remain exactly equal to v2. The layout-revision counter must NOT increment.

The frozen evidence proposal is
`f2_u_waypoint_revision_v1/proposal.json`, SHA
`f97bb48c4051b38ed20a5b9e10e15b4ea10ee608bd6697009e4e03e7ba951415`.
It is a finite residual-plane approximation, not an established reachable pose.

Private v1 execution globals remain in use; no shared module is patched. One
necessary private geometry change additionally replaces the old hardcoded
`preplace = world_axis_offset_pose(release, 0.08)` inside the frozen live-target
derivation with the proposal height. The original compensated actor-origin
correction and every other geometry/physical check are retained. The private
panel module alone receives this helper. Without it, updating only the contract
would correctly fail the live target check. Tests cover that negative control.

All three fresh C/U/D IK calls remain required. Prior D success is preserved as
evidence but never used to skip this scene's endpoint checks. Only when all three
pass can the four original carry/release route calls run. No physical/raw work.
Budget:7 solver /1scene /0action /0collection, unchanged original IK settings,
native screening and physical Gates.

Main issuer should retain/validate every revision1 job dependency, merge
`dependencies.additional_bindings()`, update the returned manifest_fields and
dispatch to `goal_pilot48_v1.f2_inward_runtime_v3.runner_bridge`. The three new
`f2_route_revision1_*` fields bind dispatch targets and the route proposal;
the existing four layout-revision lineage fields remain as parent references.
Issue a new job/output namespace; do not overwrite consumed manifests.

CPU tests cover actual run entry, missing manifest/old U/changed D rejection,
exact layout and seed preservation, private globals, real live derivation,
complete meter reconciliation and the six inherited state-machine tests.
An initial fake-scene test lacked an import-only Pose fixture; it was corrected
locally before testing the actual old-helper rejection/new-helper pass. No GPU
or scene was created by that CPU test failure.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计:/nfs_share/lijunhui/Robotwin2/project/RoboTwin /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest goal_pilot48_v1.f2_inward_runtime_v3.test_cpu -v
```

Pin native caches inside Robotwin2 as required. Actual v3 GPU qualification,
route planning, Guard/UUID/pre-post/cleanup remain pending. No reserve/issuer,
GPU job, common source or prior version was changed by this subtask.
