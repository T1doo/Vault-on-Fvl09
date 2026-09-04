# F2 controlled-insertion route Gate post-run auditor V1

## Purpose

This directory contains a read-only, pure-CPU auditor for the already sealed
F2 11-query planner-only Gate. It does not modify the approved manifest,
Guard, runner, run output, cache, lease, or any GPU state. Its JSON audit
receipt is written only to stdout.

The separate auditor is necessary because the sealed F2 runner intentionally
writes `job_terminal.json` and exits zero even when a planner chain fails.
Therefore `child_exit_code=0` and Guard `status=completed` are transport
evidence, not the scientific success decision.

## Pass conjunction

The auditor returns exit code 0 only if all of the following are independently
consistent:

- exact sealed manifest file/self-hash, run/job identity, Runtime hashes and
  zero physical/formal authorization;
- `job_terminal.json` self-hash, `error=null`, and `pass=true`;
- `result.both_chains_pass=true`;
- independently published inside and beside receipts are byte-semantically
  identical to their embedded planner rows and have valid self-hashes;
- inside is the exact ordered 5/5 successful unexecuted segment chain;
- beside is the exact ordered 6/6 successful unexecuted segment chain;
- every segment has a matching successful planner-query receipt and continuous
  qpos-hash lineage;
- aggregate planner queries are exactly 11, with exactly two unique fresh
  scene IDs and clean per-scene cleanup receipts;
- physical, branch, raw, video, accepted-root and formal counts are all zero;
- output has no raw/video/root/branch/formal artifacts or symlinks;
- Guard start and terminal self-hashes bind the same run/job/manifest,
  physical index, UUID, lease and pre-snapshot;
- selected GPU is independently recomputed as idle at Guard pre/launch and as
  returned to the permitted relative baseline at the final post snapshot;
- Guard cleanup errors are empty, cache removal and lease release are true,
  task-owned cleanup passes, Guard logs exist, and the per-job cache is absent.

Any missing, malformed, inconsistent, or tampered evidence yields a self-hashed
`REJECTED_F2_POSTRUN_EVIDENCE` receipt and nonzero exit. No rejection authorizes
a retry, target change, physical execution, root execution, Stage 1, or formal
data generation.

## Invocation after the sealed job terminates

From this directory:

```sh
env PYTHONDONTWRITEBYTECODE=1 \
  /nfs_share/lijunhui/Robotwin2/env/bin/python auditor.py
```

Capture stdout into a new, separately published Vault receipt using the
project's normal immutable publication procedure. The auditor itself never
creates that receipt. The GPU iron rule still requires the operator's fresh
outer post-run live snapshot; this auditor verifies and recomputes the Guard's
persisted final baseline evidence but deliberately does not call `nvidia-smi`.

## Pure-CPU tests

```sh
env PYTHONDONTWRITEBYTECODE=1 \
  /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest -v test_auditor.py
```

The suite is in-memory apart from reading the immutable approved manifest. It
does not create the F2 output path or initialize CUDA.

## Implementation freeze at initial review

- `auditor.py` SHA-256:
  `a76aee0674ff641da41f5951d221d28547dc92db87e7a5c0f41558ced047251d`
- `test_auditor.py` SHA-256:
  `a0cb73a8c37d3ebb8d80609a766164c180020d2419ec6e5a3fe5b9d9918fc2c6`

