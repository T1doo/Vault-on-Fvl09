# F2 controlled inside runtime v2 — CPU implementation, GPU pending

**Current blocker:** the original complete held-transport Gate is now restored
and rejects can/box contact while held, including genuine box9 supported
descent. The contact-rule adaptation is a pending proposal in
`TRANSPORT_IMPACT.md`, not enabled code or authorization. No rows are dropped.
Public qualification issuance is fail-closed until an explicit narrow
decision is separately recorded; the geometry approval alone does not unlock it.

This is a suffix implementation, not a root issuer or collection entry. It
consumes a caller-owned fresh scene after exact replay of the qualified
`p48_f2_prefix_clearance_001` canonical artifact. No prefix planning is repeated.
The caller must own Guard, scene/action/collection meters, current and initial
anchor capture/equivalence, the actual canonical replay receipt, failure/raw
publication and scene cleanup. `root_execution_ready=false` is intentional:
on/beside and the same-current three-relation root have not been qualified.

## Exact finite execution graph

1. Validate the saved real prefix lineage and fresh original replay physical
   Gate. Build a fresh native-shape certificate, derive the actual reported
   EEF-to-can transform and map the one approved relative box contact pose to
   this scene. Recompute native geometry; require only `box__9` support.
2. Install actual carried/full world. Plan and execute one original extra
   12 cm lift. Refit from actual post-lift can and install full world again;
   plan and execute the original 30 mm preinsert.
3. Refit from actual preinsert. Save both full-model state checks and every
   negative actual fitted sphere/world pair. Only attached_can/box__9 may be
   excepted; all other 14 box pieces, all robot/full world queries and self
   collision remain. Plan one descent. Every actual 250 Hz plan sample is
   checked against native can/box geometry before execution, without sample
   thinning. All non-box9 intersections reject; box9 contact must clear under
   the previously approved 0.1 mm numerical band. Final target must satisfy
   the approved native-floor verifier. This is not a continuous-sweep proof.
4. Execute descent; retain original 50 support frames and original physical
   support checks plus actual floor shape evidence. Open .2/.4/.6/.8/1.0,
   with 10 frames each. Before full opening apply original ReleaseSafetyV10
   plus actual floor contact. Never release after a failed support Gate.
5. Record exactly 250 settle frames. Build released/full world from actual
   can pose and measured named joint positions; no projected/snapped can or
   commanded-open qpos substitution. Plan/execute retreat then neutral.
   Wait original 75 rest frames; retain original 250-frame/final physical
   Gate and additionally check actual post-retreat/rest native geometry and
   last 10 actual floor contacts (not stale settle-end geometry).

Worst case: **5 MotionGen goals, 0 independent IK, 1 containing fresh scene,
1 action attempt, 0 collections**. The suffix creates no additional scene;
the one includes canonical replay, which is physical and must be metered even
though it makes zero new solver calls. Model constructions may perform at
most **10 high-level single/batch state checks**: initial2 + postlift2 +
prefloor-full2 + prefloor-pair2 + released2. These are not IK/trajectory
problems. The fixed waits total 425 frames; trajectory and gripper internal
steps are saved from real execution, not guessed. No retries, alternative
poses, height scans or fallback grasp exist. Guard timeout/lease must be
frozen by the later issuer; this module has no independent launch authority.

## CPU evidence and pending work

`test_cpu` uses actual saved prefix terminal geometry for target construction.
Its sequence backend and entry/model-failure fixtures are explicitly CPU-only,
not successful physical insertions. `test_live_models` exercises real shared
pair checker methods with CPU torch and actual native contact geometry. Use
`python -m unittest goal_pilot48_v1.f2_controlled_inside_runtime_v2.test_all -v`.

Still pending: live CuRobo five-goal solvability/collision/FK conformance,
support/release physics, whole-scene wrapper and dynamic metering/cleanup,
same-current on/beside and atomic three-relation acceptance. The original
Stage-0 and all failed receipts remain immutable. There is no gravity-drop,
new physical fixture, collision-mesh mutation, inside threshold expansion,
training/formal/Stage-1 scientific acceptance in this implementation.
