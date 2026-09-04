# F3 pre-close physical-consistency Gate V1

Status: CPU_IMPLEMENTED_AND_REPLAY_VALIDATED_PROPOSAL_ONLY

## Outcome

The F3 V2.1 planner repair worked: r1505, r2180 and r3677 all passed Stage A
and Stage B. The physical Gate nevertheless failed 0/4. The four sealed
traces show that the failure is not a gripper-command, 26-D action-layout, or
verifier defect. CuRobo accepted trajectories whose approximate collision
model did not exclude collisions visible in SAPIEN mesh/contact physics.

The new proposal-only Gate stops a candidate before close when the realized
pregrasp or grasp boundary shows wrong arm routing, incomplete contact
evidence, executing-arm self/support collision, premature bottle contact,
more than 10 mm bottle displacement, selected-arm qpos error above 0.10 rad,
or EEF error above 30 mm / 20 mrad.

It reuses the existing V8 physical-contact classifier; pair presence alone is
not treated as collision. It cannot initialize CUDA, create a scene, call a
planner, close a gripper, execute shared-V, create raw data, or authorize a
root.

## Sealed-trace replay

All four V2.1 physical traces are rejected at the pregrasp boundary:

| candidate | first failure | collision | qpos error | EEF error |
|---|---|---|---:|---:|
| r0005 | self collision | fl_link6 ↔ fl_link4, impulse 76.59 | 0.568 rad | 75.0 mm / 639 mrad |
| r1505 | self collision | fr_link6 ↔ fr_link4, impulse 63.43 | 0.807 rad | 87.0 mm / 632 mrad |
| r2180 | self collision | fl_link6 ↔ fl_link4, impulse 10.68 | 0.339 rad | 119.9 mm / 89.9 mrad |
| r3677 | self collision | fr_link6 ↔ fr_link4, impulse 35.76 | 0.628 rad | 103.4 mm / 464 mrad |

r2180 and r3677 also displaced the bottle before close. The later 0/4
selected-gripper-contact result was a correct consequence.

Replay receipt:
f3_preclose_physical_consistency_gate_v1/F3_PRECLOSE_PHYSICAL_CONSISTENCY_CPU_REPLAY_RECEIPT_V1.json

- receipt SHA: d2a42d743ca126aab42f54009d2153b97c346efbe31ce82dccf2c3ed5607a24a
- file SHA: bd1414caa51b423ea64f8f6d27a79d256e119680aeb180b7058b3bfa549504db

## CPU verification

Main-agent rerun: 20/20 unittest cases passed in 3.851 seconds; 4/4 Python
files passed AST parsing. Tests cover the four sealed traces, a good synthetic
sequence, wrong-arm routing, positive-separation nonphysical pair presence,
missing signals, collision categories, premature bottle displacement,
inclusive tracking boundaries, exact 52-query budget, execution rejection,
and zero file-I/O behavior.

Two read-only proposal-publication commands failed before producing output:
one used an invalid compound def after a semicolon and raised SyntaxError;
the next requested a nonexistent decision_receipt_sha256 key and raised
KeyError. The corrected read-only command succeeded. None wrote a file,
initialized a GPU, or changed an authorization.

## Next bounded proposal

PROPOSED_F3_PRECLOSE_PHYSICAL_CONSISTENCY_MICRO_GATE_V1.json is unapproved
and has four intentionally pending candidate slots. A future candidate-frozen
job is capped at 4 candidates, 52 planner queries, 12 scenes, and 4 physical
attempts. Physical scope ends at a conditional 25 mm micro-lift. Shared-V,
suffix, root, raw, and formal counts remain zero.

The consumed r0005/r1505/r2180/r3677 candidates are not retried. Candidate
selection must be deterministic and frozen before GPU.

Older-protocol evidence for 001_bottle/base13 + left arm had contact fraction
1.0 and zero breaks. It is an audit lead only, not a current candidate or
current-protocol pass. External review should decide whether and how that lead
may constrain the candidate-freeze rule.

No F3 execution is authorized by these files.
