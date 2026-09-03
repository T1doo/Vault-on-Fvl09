# F4 development-root Runtime V2 implementation review

日期：2026-09-04

状态：`CPU_IMPLEMENTED_SOURCE_TESTED_PROPOSAL_NOT_YET_ISSUED`

## Corrected status

F4 is `PHYSICALLY_QUALIFIED` from immutable isolation 5/5 and real
ABC/ACB/BAC 3/3 evidence. Its root remains
`INFRASTRUCTURE_BLOCKED_BEFORE_BRANCH`. This CPU repair does not authorize a
third candidate search, GPU execution, planner execution, physical execution,
or a root.

Run10--Run14 are bound as separate historical failures:

- Run10: obsolete 0.10 m slot-center check;
- Run11: 12 target-construction plus 30 chain accounting collapsed to 30;
- Run12: `total_before` NameError;
- Run13: missing `asset_hashes_by_family`;
- Run14: Guard-created paths rejected again by the runner.

## New Runtime V2

Directory: `f4_development_root_runtime_v2/`

- `manifest_contract.py` SHA-256: `753dec90df49984fc974066af2b9c5b6dcb8f0e6bede55cdc7800893d3953a0c`
- `guarded_launcher.py` SHA-256: `884ccd6c946991b95f8a92e2c7740bc83eb6e6a4d4ae09d0a047cd1f4f7d7702`
- `job_runner.py` SHA-256: `e9217b437e360e0fdd2540420ff86b094c5ec4f8e59c1aebd37458aa1e89e175`
- `lifecycle_preflight.py` SHA-256: `cc3c1db3b12a8e735d4c24e3afd7e3b195257a14bcad5430a9d4c7a9781c5c36`

The contract splits `PREPUBLICATION`, `GUARD_ENTRY`, `RUNNER_ENTRY`, and
`POST_CHILD`. `RUNNER_ENTRY` requires the Guard-created start receipt,
stdout/stderr files, cache job and all nine cache subdirectories, plus the
UUID/index/lease/start-receipt environment. It no longer applies the
Guard-entry “all absent” rule to a child.

The Guard imports only the existing audited snapshot/idle/cache primitives;
it does not call or monkey-patch the old Guard `main`. The runner imports only
the hash-bound `run_f4_development_r_pc_root` function; it does not call or
monkey-patch the old runner `main`.

## Strict root finalizer

The V2 finalizer requires all of the following before exit 0:

- task feasibility 3/3, one candidate freeze and one prefix;
- suffix/branch prefix replays 3+3=6;
- three accepted branches in ABC/ACB/BAC order;
- raw integrity fields, MP4 integrity and family verifiers 3/3;
- selected-contact identity/continuity, prior-slot preservation and untouched
  role preservation for all nine role operations;
- all final slots, common-X, gripper-open and arm-neutral checks;
- frozen branch planner delta 0 and final-state equivalence;
- exact planner counts 10 + 126 = 136;
- 11 fresh scenes, 7 robot-action scenes and cleanup/orphan pass.

All terminal data is passed through `canonical_jsonable` before hashing and
writing. A CPU regression with a nested NumPy `bool_` passes; the same
synthetic root with `status=failed_verifier` is rejected even when no exception
was raised.

## Source-level CPU checks completed

- Four files parse/import.
- The exact Run2 planner terminals rebuild the same candidate/program specs.
- Each terminal reports 12 target-construction queries + 30 chain queries =
  42; aggregate suffix planning is 126.
- Synthetic successful finalizer counts 11 scenes and 7 action scenes.
- No scene, GPU context, output or authorization has been created.

The next step is to commit/push this source freeze, generate an
`approved=false` proposal manifest bound to these hashes, and run the complete
Guard-to-runner lifecycle test with all negative cases. F4 must remain CPU-only
until a new external review explicitly authorizes one root.
