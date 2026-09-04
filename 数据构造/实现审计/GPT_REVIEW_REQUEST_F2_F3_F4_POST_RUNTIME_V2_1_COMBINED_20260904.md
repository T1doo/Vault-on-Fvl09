# Combined narrow review: F2, F3 and F4 after Runtime V2.1

Please review the three independent items below. This document and every
referenced proposal currently authorize no GPU execution. Stage 0 rerun,
Stage 1, formal 360, training, H-reveal, compression and pi0.5 remain false.

Current unified status:

NOT_READY_F1_R_INV_INCOMPLETE_F2_ROUTE_GATE_INFRASTRUCTURE_FAILED_F3_SHARED_V_PHYSICAL_FAILED_F4_ROOT_AWAITING_EXTERNAL_APPROVAL

Development data currently accepted: 5 roots / 15 trajectories, all from F1
r_pc. Stage-1-authorized trajectories remain 0/48. Formal remains 0/40 roots
and 0/360 trajectories.

## Decision A — F2 short-TMPDIR Run3

Run2 launched a child but failed before any planner query because Warp NVRTC
rejected a 137-byte TMPDIR. The scientific route Gate therefore has no result.
GPU, cache, lease and processes were cleanly released.

The unapproved Run3 proposal changes no scientific or runtime semantics. A
future approved manifest may change only run_id, guard_directory,
cache_directory and output_namespace. The proposed cache root is
/nfs_share/lijunhui/Robotwin2/cache/f2; its derived TMPDIR is 82 bytes and all
nine cache paths are at most 95 bytes under a frozen 100-byte prelaunch cap.

The exact retained scope is inside 5 + beside 6 = 11 planner queries, two
fresh scenes, and zero physical/branch/raw/video/root/formal outputs.

Proposal:

- manifest SHA: f279c87521013dadf25442314123575eed1b3c209f238a21038db2fb36b56867
- file SHA: 82e0527ccf5cd945694b726034c6d0028ff0300ae480e62d002046675346c2fc
- approved and all execution authorities: false

CPU review:

- receipt: 94b40454abc12397b6a05dbff7602b3ceffc90a683a1c75331ca6aba9dde62de
- file SHA: 6d6df67245d1353b03a3fe7690e8e0eb60582251a57e5de197f7801b75276863

Return APPROVE_ONE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3 if and only
if this one path-only recovery may be issued. Otherwise return
REVISE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3 with exact deficiencies.
Approval must still be followed by an exact approved manifest, read-only
auditor V1.2, CPU preflight, publication, fresh GPU snapshot and Guard.

## Decision B — F3 pre-close Gate design

F3 V2.1 solved planner qualification: all three new candidates passed Stage A
and B. Runtime accounting was exactly 58 queries / 10 scenes. Physical
shared-V failed 0/4 because all four candidates lost bottle contact.

Trace audit identifies the root cause as collision-model mismatch, not gripper
or action routing. CuRobo accepted paths that produced SAPIEN arm self
collisions and table/pad collisions before close. A CPU-only pre-close Gate
now checks realized selected-arm qpos/EEF, V8-classified contacts and premature
bottle displacement. It rejects all four sealed traces before close and passes
20/20 tests.

Replay receipt:

- receipt: d2a42d743ca126aab42f54009d2153b97c346efbe31ce82dccf2c3ed5607a24a
- file SHA: bd1414caa51b423ea64f8f6d27a79d256e119680aeb180b7058b3bfa549504db

Unapproved proposal:

- manifest SHA: 1ef3f9b543b4f93cdbccf5948d3022c1116456d04a8dd0d5bf12cdf1c6115b1e
- file SHA: 6d54c7156661090cd75953985dd85f38ddaf84eaeff72ea8ef5da6ab7a6e52dd
- four candidate slots deliberately remain pending
- future cap: 52 planner queries / 12 scenes / 4 physical attempts
- physical scope ends at conditional 25 mm micro-lift
- shared-V/suffix/root/raw/formal are all zero

Older-protocol bottle13 + left-arm evidence had contact fraction 1.0 and is an
audit lead only. It is not automatically a current candidate.

Because exact candidates are not yet frozen, do not approve GPU execution.
Return APPROVE_F3_PRECLOSE_GATE_DESIGN_CPU_CANDIDATE_FREEZE_ONLY_V1 together
with an exact deterministic candidate-freeze rule and whether a second review
of the frozen candidates is required. Otherwise return
REVISE_F3_PRECLOSE_GATE_V1 with exact code, field or test deficiencies.

## Decision C — one F4 development root

F4 Runtime V2.1 completed the requested CPU hardening. Finalizer tests are
18/18; environment, lineage, executable identity and POST_CHILD tests are
21/21, 5/5, 3/3 and 11/11. The proposal preserves r01, ABC/ACB/BAC,
right-prefix/left-suffix, the existing planners/verifiers and all caps.

Proposal:

- manifest SHA: ea27ac315516b2006a96bd92594e125473970d111d2ef12434be9fecc11893e5
- file SHA: 751ff914161456a70dd2975ada2de5f8b4aa7f70edcad2abd8291708e44d8612
- approved/GPU/planner/scene/physical/root: all false

CPU review:

- receipt: f1efa1fa8e093a2ca900171cab9cd72d1fb1f44f5ffbca2fff398aa58a1db166
- file SHA: 0ff6f2a68ca25f0686e1673f8951b000e31d2a84ce6a5690666477cb238bb51a

If the hardening is sufficient, return
APPROVE_ONE_F4_INFRASTRUCTURE_CORRECTED_ROOT_V2. This may authorize only one
nonformal r_pc development root, at most three trajectories and zero formal
data. Otherwise return REVISE with exact deficiencies.

## Machine packet

NEXT_EXTERNAL_REVIEW_PACKET_F2_F3_F4_POST_RUNTIME_V2_1_V1.json

- receipt: 2b8e15957d3aabc97c662a6416e4255a5caa8e748eb4187d3a5cc0e2e77921c3
- unified readiness receipt:
  2eb967588a226bb9e24360946c13a9cd08a0a575e84bfd469938ad1e0f447362

Please return three separate decisions. Do not merge F2, F3 and F4 authority:
one family failing or requiring revision must not silently alter another
family's decision.
