# F2 admission reissue Run2 CPU review — 2026-09-04

## Outcome

The first and only path-only/manual admission successor is implemented and
CPU-valid. It retains scientific attempt ordinal 1 and uses dispatch ordinal
2. No GPU, simulator scene, planner query, physical action, output, cache-job,
root, trajectory, or formal data was created.

The recovery receipt self-hash is
`5c44f850e6e2957db932d151e52bc2977b33da9e6503a395a9f54cd3ae16e41a`
(file SHA
`0e4baca15482429c285de9edaf34402967b8f876943a20d86faa6020c1858229`).
The successor manifest self-hash is
`42d4d48a41ab8fcab1515679450f20c2852dfc94a531022009a5b7fce56ff396`
(file SHA
`210dd17071c1f5b89aee6fb8f7451cb14949a2948c663cbc2e86c2824725ccd0`).

After removing the exact additive lineage fields and normalizing only the four
declared scheduling paths, the successor is structurally equal to the parent
manifest. The new Guard directory, cache-job path, and output namespace were
all absent after validation.

## Existing-loader validation

The first CPU preflight invocation omitted the project `PYTHONPATH`. The
successor manifest loader completed, then sealed-contract import failed with
`ModuleNotFoundError: controlled_multi_future`. It created no path, scene, GPU
context, output, or authorization consumption.

The corrected invocation added only the required exact project `PYTHONPATH`.
The unchanged Guard/runner preflight returned exit 0 and `pass=true`, with
inside target count 5, beside target count 6, aggregate cap 11, and
scene/GPU/output all false. Thus the existing loader accepts the successor;
no Guard or runner modification was needed.

## Auditor validation

- AST: 2/2 pass.
- Tests: 20/20 pass in 0.099 seconds.
- The 16 frozen V1 positive/negative cases all pass unchanged.
- Four added tests cover exact on-disk lineage, lineage tampering, V1 source
  identity, and the read-only pre-run boundary.
- The real V1.1 CLI before execution correctly returns exit 1 with
  `job_start_missing`; its self-hashed rejection receipt is
  `c09b2cea6683b8533b1e341e3867bbb6fc19e1f74550b8bb319196cd48b1c4c4`.

Source hashes:

- auditor:
  `4ae74fa01fb60a181a3dc2ef1d329e09452e77156a1f58b68c16a14598589a7c`;
- tests:
  `b566197952c78632de692fccb5d704ce460e71bfe81dbf2b1522b25aa1a202a3`.

## Immutable boundary

The old manifest, Guard, runner, Guard terminal, and V1 auditor remain
unchanged. The successor must be published before execution. It still requires
a fresh full GPU0–7 outer snapshot and its own atomic Guard recheck. A second
atomic admission rejection terminates this recovery path; it must not cause a
third dispatch identity. Passing this planner-only Gate does not authorize an
F2 root or Stage 1.

