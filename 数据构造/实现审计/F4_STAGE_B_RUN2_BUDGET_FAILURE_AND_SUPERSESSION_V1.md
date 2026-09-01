# F4 Stage-B Run2 Budget Failure and Supersession

Status: `RUN2_BUDGET_UNDERSPECIFIED_ALL_SCOPES_SUPERSEDED_DO_NOT_RUN`

Run2 corrected the first budget estimate from 32 to 33, but that estimate still treated each role's planner-assisted grasp construction as one query. The already sealed Stage-A r01 receipt proves the exact accounting for this selected source:

- A grasp-target construction: 4 batch queries.
- B grasp-target construction: 4 batch queries.
- C grasp-target construction: 4 batch queries.
- Stage-B neutral-to-neutral chain: 30 segment queries.
- Deterministic total: `4 + 4 + 4 + 30 = 42`.

Run2 r01 stopped at `33/33`, with zero physical execution and complete Guard cleanup. Run2 r02 was blocked before consumption because the atomic GPU3 admission snapshot observed a transient 21 MiB/P0 state; it created no child or output. Run2 r03–r08 remained untouched and unconsumed. All eight run2 scopes are superseded and must not be run or reused.

Machine report SHA-256: `7791702763ccf8d87127d75f4c5651c03917a845b1a113a9cf40f1bb147af9a6`.

The next correction must use the evidence-derived 42-query budget, a new source/publication version, a fresh CPU/source freeze, and new authorizations. Candidates, rank, target chain, physical execution count, Gates, thresholds, and selection rule remain unchanged.
