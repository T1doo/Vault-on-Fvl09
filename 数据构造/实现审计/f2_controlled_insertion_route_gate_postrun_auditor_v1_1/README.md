# F2 path-only admission reissue post-run auditor V1.1

This directory is the exact-binding, read-only auditor for
`F2_CONTROLLED_INSERTION_ROUTE_GATE_ADMISSION_REISSUE_RUN2_MANIFEST_V1.json`.
It does not modify the original F2 manifest, Guard, runner, terminal, or V1
auditor.

V1.1 hash-loads the frozen V1 auditor and retains all of its scientific and
Guard checks. It adds fail-closed validation that:

- the predecessor Guard failure was prelaunch and consumed no scientific
  attempt;
- the predecessor manifest and Guard terminal retain exact file/self-hashes;
- dispatch ordinal is 2 while scientific-attempt ordinal remains 1;
- the successor differs from its parent only in `run_id`, `guard_directory`,
  `cache_directory`, and `jobs[0].output_namespace`, plus the exact additive
  lineage fields;
- original review binding, source, assets, sealed evidence, job ID, 5+6=11
  planner budget, and every zero cap are unchanged;
- a second atomic admission rejection must stop rather than create another
  successor automatically.

After the successor job terminates, invoke from this directory:

```sh
env PYTHONDONTWRITEBYTECODE=1 \
  /nfs_share/lijunhui/Robotwin2/env/bin/python auditor_v1_1.py
```

It prints one self-hashed JSON receipt to stdout and returns zero only for the
complete 5/5 + 6/6 + 11-query + clean-Guard/GPU-baseline conjunction. It never
calls `nvidia-smi`; the mandatory outer fresh post-run GPU check remains
separate.

Pure-CPU tests:

```sh
env PYTHONDONTWRITEBYTECODE=1 \
  /nfs_share/lijunhui/Robotwin2/env/bin/python -m unittest -v \
  test_auditor_v1_1.py
```

Initial source hashes:

- `auditor_v1_1.py`:
  `4ae74fa01fb60a181a3dc2ef1d329e09452e77156a1f58b68c16a14598589a7c`
- `test_auditor_v1_1.py`:
  `b566197952c78632de692fccb5d704ce460e71bfe81dbf2b1522b25aa1a202a3`

