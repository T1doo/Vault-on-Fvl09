# F3 replacement reissue Runtime V2.1

Status: `IMPLEMENTED_CPU_VALIDATED_NOT_YET_MANIFESTED`

This is the exact fail-closed hotfix authorized by
`EXTERNAL_REVIEW_DECISION_F2_F3_F4_RUNTIME_V2_1_20260904.md`. It supersedes
the unconsumed V2 while retaining reissue ordinal 1. It does not alter the
approved overlay, retained r0005 evidence, r1505/r2180/r3677 order, physical
Gate, candidate semantics, or the `30 + 4*7 = 58` budget.

## Files and SHA-256

- `job_runner.py`: `1078938b6e5314836e4b1fa79862b254a80f00442f4d28631d3f7829ffbaa61d`
- `guarded_launcher.py`: `405067d3c7d2734040a03961ae8dff3658a86811dec427e0bb6efba58151110f`
- `test_job_runner.py`: `30e1af550e08d79e6ce3da72d5a65c90e88d06a0e5b0c5de8f1c953c6dc81b87`

The immutable V2 inputs were rechecked after implementation:

- V2 runner: `d95d1c71fb3ebdf93d8d4918dad8b5cc2acfc395906be2421952d1aea826136c`
- V2 Guard: `57e31200d585120363628fef35401f3f0fc50f6c4ef47bf13d30c8f2b721398d`
- V2 manifest file: `e0d85ab17ee19ef04f298fbef4cf9c2a5ca0d06af99b5ecca0295b15c38de0fa`

## Exact changes

1. `main()` returns zero if and only if `job_terminal.pass` is true.
2. Each physical scene writes `planner_query_count_before`,
   `planner_query_count_after`, and `planner_query_delta` from a `finally`
   block. The receipt is written even when the physical executor raises.
3. Runtime accounting reopens and self-hash-validates every physical-scene
   receipt; it never treats the returned physical terminal as the authority
   for physical planner count.
4. Accounting requires exactly three qualification rows in the frozen
   r1505/r2180/r3677 order, a nonnegative qualification total equal to the
   Stage-A plus Stage-B row sums, one complete receipt per physical attempt,
   `len(physical_rows) == physical_execution_count <= 4`, internally
   consistent planner/physical/aggregate scene counts, and no-suffix count 0.
5. Any missing, negative, inconsistent, over-cap, or incorrectly ordered
   accounting evidence fails closed.
6. The wrapper never overwrites the execution body's
   `conditional_no_suffix_executed` truth. A missing or non-`False` value
   fails closed. The hash-bound legacy V1 body explicitly reports `False`
   but omits its scene count, so only that exact case derives count zero and
   records provenance; any explicit count must be an exact integer zero.

## CPU-only verification

Command:

```text
env -u LD_LIBRARY_PATH PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/nfs_share/lijunhui/Robotwin2/project/RoboTwin \
  /nfs_share/lijunhui/Robotwin2/env/bin/python \
  数据构造/实现审计/f3_replacement_reissue_run1_runtime_v2_1/test_job_runner.py
```

Result: `7 tests / 7 PASS`, process exit 0.

The tests cover:

- actual runner-main success exit 0;
- scientific failure without exception exit 1;
- executor exception after three queries persists delta 3 and exits 1;
- exact aggregate 58 passes and aggregate 59 fails;
- exact three-row order, qualification identity, physical attempt/receipt
  cardinality, negative receipt count, and no-suffix fail-closed checks;
- preservation of a reported no-suffix execution value, rejection of true or
  missing execution evidence and explicit nonzero/bool counts, and the sole
  legacy `False` plus missing-count derivation;
- preflight declares zero scene/GPU/output and creates no output.

All three Python files parse/import on CPU. Guard `--help` exits 0. Test
temporary directories were removed. No simulator scene, CUDA context, GPU
process, real output namespace, Guard invocation, lease, or authorization
consumption occurred.

## Publication boundary

This directory deliberately contains no final V2.1 manifest. The next step is
to commit this source freeze, then create a separate V2-unconsumed
supersession receipt and a V2.1 manifest bound to that new Vault HEAD and these
runtime hashes. A real CPU Guard preflight must pass before any execution.
