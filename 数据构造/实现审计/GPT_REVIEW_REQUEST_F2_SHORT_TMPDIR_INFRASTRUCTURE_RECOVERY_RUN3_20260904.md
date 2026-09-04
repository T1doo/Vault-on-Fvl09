# GPT Review Request — One F2 short-TMPDIR infrastructure recovery Run3

## Exact decision requested

Please return exactly one of:

- `APPROVE_ONE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3`
- `REVISE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3`
- `REJECT_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3`

No approved manifest exists yet. This review request and its proposal authorize
nothing by themselves.

## Why a new approval is required

The already authorized Run2 successor reached Guard start, initialized the GPU
context, and launched child PID 3634762. It then failed during the first scene's
CuRobo planner construction, before any planner query, because Warp NVRTC
rejected the Guard-derived 137-byte `TMPDIR`:

```text
NVRTC_ERROR_COMPILATION / error code 6
name of directory for temporary files is too long
```

Run2 is therefore sealed as
`FAILED_INFRASTRUCTURE_BEFORE_PLANNER_WITH_EVIDENCE`, not as an F2 route
result. Planner/physical/branch/raw/video/root/formal counts are all zero, but
the child/GPU dispatch occurred, so the one-shot authorization is consumed.
There is no local authority to issue or run dispatch 3.

Authoritative terminal publication:

- receipt SHA-256:
  `bc28ef29817dd522d15a5379aba914f46445b11b494eb41c361cbb6c98ff8ff7`
- file SHA-256:
  `c486c0489c0830e8280a0d6919be4a35855d72adb523ce4a3cae6d7d1b2a08d9`

## Proposed minimal correction

Use the unchanged F2 Guard, runner, active implementation, assets, sealed
prefix evidence, candidate, inside five-target chain, beside index-2 six-target
chain, verifier boundary, and budgets. A future approved manifest may change
only these four operational fields:

1. `run_id`;
2. `guard_directory`;
3. `cache_directory`;
4. `jobs[0].output_namespace`.

The proposed cache root is:

```text
/nfs_share/lijunhui/Robotwin2/cache/f2
```

With the unchanged job ID, Guard deterministically derives:

```text
/nfs_share/lijunhui/Robotwin2/cache/f2/f2-controlled-insertion-route-gate-run1/tmp
```

This is exactly 82 UTF-8 bytes/characters. All nine Guard-derived cache paths
are 82–95 bytes; the proposal adds a fail-closed prelaunch maximum of 100
bytes. The future cache, Guard, and output paths are currently absent.

## Exact retained budget and stop rule

```yaml
job_id: f2-controlled-insertion-route-gate-run1
family: F2
mode: F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1
inside_planner_queries: 5
beside_planner_queries: 6
aggregate_planner_queries: 11
fresh_planner_scenes: 2
physical: 0
branch: 0
raw: 0
video: 0
accepted_root: 0
formal: 0
timeout_seconds: 14400
automatic_retry: false
fallback: false
target_search: false
automatic_root_transition: false
additional_dispatch_after_run3: false
```

GPU0–7 remain eligible only through a new complete live snapshot, exact UUID
binding, one job per independently fresh-idle card, Guard lease, and mandatory
post-run cleanup/release checks.

## Runner exit semantics

For minimality, the proposal does not modify the existing runner. Its known
transport behavior can return child exit 0 after publishing
`job_terminal.pass=false`. The already reviewed safety boundary remains:

- `job_terminal.pass`, complete 5/5 and 6/6 receipts, and the read-only auditor
  define scientific success;
- Guard `completed` or child exit 0 alone never does;
- after approval, an exact-binding auditor V1.2 must be issued and CPU-tested
  before GPU execution.

If changing runner failure-exit semantics is required, please return `REVISE`;
that would be a new runtime revision rather than this path-only correction.

## Machine-reviewable proposal package

- `PROPOSED_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3_MANIFEST_V1.json`
  - manifest SHA-256:
    `f279c87521013dadf25442314123575eed1b3c209f238a21038db2fb36b56867`
  - file SHA-256:
    `82e0527ccf5cd945694b726034c6d0028ff0300ae480e62d002046675346c2fc`
  - `approved/GPU/planner/scene/physical/root=false`
- `F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3_CPU_REVIEW_V1.json`
  - receipt SHA-256:
    `94b40454abc12397b6a05dbff7602b3ceffc90a683a1c75331ca6aba9dde62de`
  - file SHA-256:
    `6d6df67245d1353b03a3fe7690e8e0eb60582251a57e5de197f7801b75276863`

## Explicitly not requested

This request does not authorize an F2 root, Stage 0 rerun, Stage 1, formal 360,
training, H-reveal, compression, pi0.5, or any F3/F4 action.
