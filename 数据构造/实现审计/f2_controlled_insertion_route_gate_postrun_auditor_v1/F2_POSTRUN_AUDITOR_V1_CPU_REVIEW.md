# F2 Post-run Auditor V1 CPU Review — 2026-09-04

## Scope and preservation

- Implemented only under the new versioned directory
  `f2_controlled_insertion_route_gate_postrun_auditor_v1/`.
- Existing F2 approved manifest, Guard, runner, hashes and paths were not
  modified.
- No GPU query, CUDA context, simulator scene, physical action, original F2
  output, cache, lease, raw trajectory, video, root, or formal artifact was
  created by this implementation or its tests.
- The auditor is read-only at runtime and emits its result to stdout.

## Verified behavior

AST parsing passed for both Python files. The pure-CPU synthetic test suite
passed 16/16 cases in 0.054 seconds. Coverage includes:

1. exact valid 5/5 + 6/6 + 11-query + two-fresh-scene conjunction;
2. `child_exit_code=0` and Guard `completed` with `job_terminal.pass=false`;
3. invalid job-terminal self-hash;
4. `both_chains_pass=false`;
5. incomplete inside chain;
6. a failed segment inside an otherwise claimed successful row;
7. aggregate planner-count mismatch;
8. fresh-scene-count mismatch;
9. duplicate scene identity;
10. every prohibited nonzero result count: physical, branch, raw, video,
    accepted root, and formal;
11. mismatch between a published relation receipt and its embedded row;
12. Guard `completed` without full cleanup;
13. independently detected non-baseline post-GPU state;
14. nonzero child exit;
15. uncleared per-job cache;
16. forbidden raw/video disk artifacts.

The real CLI was also invoked before the F2 run existed. It correctly returned
exit 1 with failure code `job_start_missing`; it did not create the missing
output. This proves the operational entry point fails closed at the current
pre-run boundary.

## Source identities

- `auditor.py`:
  `a76aee0674ff641da41f5951d221d28547dc92db87e7a5c0f41558ced047251d`
- `test_auditor.py`:
  `a0cb73a8c37d3ebb8d80609a766164c180020d2419ec6e5a3fe5b9d9918fc2c6`

## Remaining operational boundary

The auditor can verify the persisted Guard cleanup and independently recompute
the selected GPU's baseline from the Guard snapshots. An unkeyed receipt
self-hash detects accidental or unresealed modification but is not a digital
signature. Git/Vault publication and the mandatory fresh outer post-run GPU
snapshot remain part of the complete operational audit. A passing auditor
receipt does not authorize automatic F2 root execution or any later stage.

