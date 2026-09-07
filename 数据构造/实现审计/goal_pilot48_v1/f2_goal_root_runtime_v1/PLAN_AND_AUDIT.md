# F2 new-layout root: staged implementation audit v1

Only prefix qualification is implemented here. There is NO complete-root
dispatcher, no suffix collection entry, no new job/authorization or GPU run.
Five CPU tests pass. Actual model sequence/physical success remains pending.

## Why an existing root must not be run unchanged

`F2TopContactRootControllerV1` overrides its common grasp/lift prefix but inherits
`F2AssetBoundControllerV3` suffix planning. Its inside branch still uses the old
10cm gravity-drop route. Its beside branch still uses six targets, hubs and80mm
approach. Neither is the now-required controller. Changing only binding/goals
would not install controlled insertion or the verified carry/release model chain.

The new prefix controller explicitly refuses suffix planning/execution. It keeps
the candidate provisional, using the parent's planner_only mode for its original
purpose: real canonical-prefix qualification followed by a stop before physical
suffix/root acceptance. It does not fabricate selected=True or old micro success.

## Executable first stage

New planned slot: `f2-goal-root-A-fixed-layout-v1-20260907`.
Same repaired layout and deterministic seed; new current, anchor and real prefix.
No restoration of the old held qpos and no reuse of old current/anchor/raw.

Finite scope:3 MotionGen problems /1 fresh scene /1 action scene /0 collection.
Official contact8/rotation0/pregrasp90mm/close0/lift120mm remain unchanged.

1. Capture current/anchor/provisional programs before action. Save current RGB
   and unique38-DOF state once in this qualification namespace.
2. Fresh actual-open locked joints + full audited world including static can.
   Plan pregrasp/grasp (two queries); execute and apply original preclose Gate.
3. Close0. Build fresh actual-postclose attachment, native can/table support
   witness and F2-specific tabletop partition. Plan original120mm lift (one query).
4. Before execution, screen actual returned native can geometry for no deeper
   penetration, non-descending lower envelope, final off-table state and existing
   footprint/world checks. Never disable robot/table collisions.
5. Execute lift, rebuild full world WITHOUT the support exception, and recheck
   actual single/batch start states. Apply original settling, selected-contact,
   grasp-transform5mm/0.05rad and prefix physical acceptance Gates unchanged.
6. On pass, publish a new canonical prefix artifact using the existing canonical
   builder. On failure preserve partial trace/structured Gate/cleanup evidence.
   Prefix success is not complete F2 root success.

The original physical method is AST-copied to private globals. Only its planning
schedule changes from three pre-close plans to2+actual-postclose1, plus fullworld
restoration after lift. No source file or imported global is modified. CPU tests
execute that private method and prove preclose failure cannot close or lift.

## Postclose conflict checked before GPU

`postclose_cpu_audit.json` uses F2's historical real postclose row1044 and the
current repaired-layout geometry, NOT F3 witness data and NOT a new physical run.
Native can bottom is0.544µm below the tabletop (within unchanged numeric band).
Full buffered attached-can/table overlap is4.9614mm. The pair-filtered model
retains all robot/table collisions and has minimum world gap31.8653mm, no self
overlap. A31-pose geometrical straight120mm rise does not deepen support contact
and ends off-table. This confirms the anticipated padding conflict and model
applicability on saved evidence; it does not prove the future actual plan.

The fresh run recomputes every witness from its own actual state, checks its own
returned controls, restores fullworld and keeps the original physical Gates.
It may safely fail those checks. CPU evidence does not justify skipping them.

## Remaining stages and budget boundaries

| Stage | Minimum task solver problems | Scenes/actions/collections |
|---|---:|---|
| Fresh common-prefix qualification | 3 | 1 /1 /0 |
| Three-relation suffix qualification using that exact prefix replay | inside5 + on4 + beside4 =13 | at least3 /3 /0 |
| Complete unmodified strict-prefix root lifecycle after new controller integration | prefix3 + suffix13 =16 | 11 /7 /3 |

These latter rows are source-derived LOWER BOUNDS, NOT signed budgets or ready
jobs. Additional actual model/endpoint checks must be counted separately before
issuing the corresponding new stage. Root lifecycle11 scenes is pristine1 +
task feasibility3 + canonical prefix1 + suffix preflight3 + collection branches3.
Never count those prerequisite scenes as collected raw trajectories.

### Required inside integration

Reuse the original controlled insertion suffix geometry from the actual common
prefix transform, not the full standalone8-query executor that would grasp again.
Retain high carry/preinsert30mm/controlled descend, original50-frame continuous
box support and stability check, five open targets0.2/0.4/0.6/0.8/1.0 with10-frame
holds,250-frame release settling, retreat/neutral,75-frame rest and strict-inside
V10 verifier. New layout requires fresh inside qualification; old inside5/5 is
historical only. Box-floor supporting contact needs its own audited pair-specific
model and strict cavity/native wall checks; do not reuse the can/table exception
by globally dropping the box or its walls.

### Required on/beside integration

On retains actual scale functional-point geometry and its release/rest verifier;
scale support needs a correctly audited carried/released model transition.
Beside must use the now-verified47.9469mm four-target route, not the inherited
80mm/six-target route. All suffix goals must be rederived from the NEW actual
prefix-end transform and current geometry, not copied from historical held-state
diagnosis. Preserve open-lock/static-can transition, original physical tracking,
contact, release and semantic verifiers.

### Collection integration

Only after the above passes should a new full-root controller be enabled and
accepted r_pc branches generated. It must use runtime_v2's live collection meter
and instrument actual strict_prefix_branch requests before scene creation.
F2 is the active source profile, but actual action/collection coverage must still
be checked. No old accepted root/current, no partial success promotion and no
formal/training authorization are inferred here.

## Prefix entry hardening completed before first issuance

Expanded CPU suite is14/14: five controller/model tests, seven actual run()
lifecycle/publication/meter tests, two pure-issuer tests. The lifecycle suite
covers capture_current/anchor/RGB failures before action, setup/save/publication
failures, earliest-error preservation across cleanup failure, and a real original
canonical artifact load/validate roundtrip under forced C locale with Unicode.

`artifact_io.py` keeps the original validator, writes NPZ exclusively, uses the
reviewed explicit-UTF8 exclusive atomic JSON writer, and reloads the artifact.
`runner_bridge.py` requires runtime_v2's supplied live Meter and independently
matches MotionGen/IK/scene/action/collection event partitions. Only actual prefix
physical success plus a published, validated artifact maps to scientific_route_pass.
Clean negative prefix evidence is not an accepted prefix/root.

Pure issuer: `runtime.issue_f2_prefix.build_manifest(job_id, reservation)`;
no reserve/write is performed by that function. It migrates to frozen runtime_v2
Guard/runner, binds14-test preflight, and caps3solver/1scene/1action/0collection,
1800s child/1980s lease. The main scheduler must provide the actual reservation.
