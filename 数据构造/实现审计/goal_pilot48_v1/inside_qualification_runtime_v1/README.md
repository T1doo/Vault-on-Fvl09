# One-scene inside qualification shell — not issued

`runtime.run(manifest)` creates exactly one fresh scene, captures real current
and initial anchor, uses the original same-current and anchor-equivalence
functions, loads and physically replays clearance001's canonical prefix,
checks its physical Gate, calls the versioned inside suffix, saves failure or
success trace, and obtains the scene-context cleanup receipt. It does not
restore held state, call prefix planning, freeze a candidate universe, write
training raw or accept a root. Actual anchor hashes are kept even when the
original equivalence function accepts different hashes.

`local_counts` independently observes actual setup and action call entries;
it counts an attempted first replay action even if no new trace row was
appended. Hooks are process-local, ownership-checked and restored. The bridge
compares those counts and the local planner counter against every live V3
meter charge, requiring only MotionGen methods and zero IK/collection. Scene
construction failure and cleanup failure remain failures, not empty success.

The reviewed envelope is five new MotionGen goals, one fresh scene and one
action attempt (including physical replay), zero collections, ten high-level
model state checks, proposed child timeout1800/lease1980 seconds. No resource
has been reserved by these modules.

`runtime/issue_inside_qualification.py::build_manifest` unconditionally fails
closed while supported held-contact permission is pending. `build_preview`
is pure CPU-only validation: it hashes/validates the real parent terminal,
Guard cleanup and all inherited plus new dependencies, but returns
`CPU_ONLY_NONISSUED_PREVIEW`, no reservation, and GPU authorization=false.
It is not valid for Guard issuance. Automatic Goal continuation cannot unlock
the explicit contact decision. No caller should sign this pending preview.

Run CPU tests with `python -m unittest
goal_pilot48_v1.inside_qualification_runtime_v1.test_all -v`. The suite includes
the prior prefix tests, inside geometry/model/state tests, real shell with
explicit CPU fake scenes, live replay-meter instrumentation, and nonissuing
preview/blocked-issuer tests. CPU fixture success does not mean that the
currently blocked supported-inside physical rule has passed.
