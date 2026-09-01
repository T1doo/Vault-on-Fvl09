# F4 Stage-B Run1 Budget Failure and Supersession

Status: `RUN1_BUDGET_UNDERSPECIFIED_ALL_SCOPES_SUPERSEDED_DO_NOT_RUN`

The selected F4 Stage-A source uses the left-arm planner-assisted grasp constructor. Each Stage-B candidate therefore has a deterministic minimum of 33 planner queries: three official grasp-target batch queries plus thirty neutral-to-neutral chain segments. Run1 incorrectly froze a limit of 32.

- r01 and r02 both stopped at `32/32` with `PlannerQueryLimitExceeded` before producing candidate evidence.
- Physical/release execution count remained zero.
- Both Guards completed ownership-scoped cleanup and returned GPU0/GPU3 to baseline.
- r03–r08 remained unconsumed with no Guard or output.
- All eight run1 scopes are superseded and must not be run or reused.

Machine report SHA-256: `acfb7018e2960de8f756b25e79bdbce64e1368d4f350c59a19dda0ee9dda29bb`.

A replacement requires a new source version, a corrected query budget derived from the 33-query lower bound, a fresh CPU/source freeze, and new single-use authorizations. The candidate set, ranking, physical semantics, and scientific Gates remain unchanged.
