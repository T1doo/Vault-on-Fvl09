# F4 Stage-B Run3 Numeric Audit Failure

Status: `R01_R02_COMPLETE_PLANNER_EVIDENCE_NUMERIC_AUDIT_BUG_R03_R08_STOPPED`

Run3 r01/r02 each completed the evidence-derived 42-query budget and all thirty planner segments. Rendered visibility and nominal swept-block noninterference passed. The only failed Gate was `prior_slot_preservation`.

The failure is a pure audit implementation defect: the nominal audit normalizes quaternions, while the added prior-slot check compared normalized and unnormalized quaternion components with raw `np.allclose(..., atol=1e-12)`. The maximum raw component difference was about `5.73e-11`, even though every compared position error and quaternion angular error was exactly zero under the existing `1e-9 m / 1e-7 rad` target tolerances.

- r01/r02 contain complete immutable planner evidence and do not require GPU re-execution for this correction.
- A correction must be reconstructible, hash-bound to the original receipts, and use the existing pose tolerances.
- r03–r08 remained untouched and unconsumed; their run3 scopes are stopped pending a new source version.
- Physical execution and new trajectory counts remain zero.

Machine report SHA-256: `7270af4d8635a6c3f44fec1b1ef93304d9b2eb3ec4267ea39e9d133d4909ff80`.
