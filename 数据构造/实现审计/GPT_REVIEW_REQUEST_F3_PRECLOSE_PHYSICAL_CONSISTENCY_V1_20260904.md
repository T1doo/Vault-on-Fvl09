# GPT review request: F3 pre-close physical-consistency Gate V1

Please review the new CPU-only F3 Gate and choose one precise next decision.
This request does not authorize GPU execution.

## Evidence

F3 V2.1 completed with replacement Stage A/B 3/3, planner accounting 58/58,
scenes 10/10, and physical shared-V 0/4. All four selected-gripper contact
fractions after lift were zero. No-suffix, root, raw and formal counts were
zero.

Terminal publication receipt:
070e1bec9e46e2b5aa42c8e489fd168d073be78b77cd2d14f61a8fbc74016210.

The traces establish a collision-model mismatch. CuRobo reported tiny
terminal errors, while SAPIEN execution showed arm self collisions and
table/pad collisions. r0005/r1505 never reached the bottle; r2180/r3677
displaced it before close. Action routing and gripper drive were correct.

## Implemented CPU Gate

Files and SHA-256:

- gate.py: ca33ced9e4da99d9c3fcc21f4e7133a99bacd6cdfecd74183fe79012de9274e1
- replay.py: e3fc6fcfec6353a04dede6704cbf4e1f8be479a4d0042d9926f99e9ee397d656
- proposal.py: 0060cedbd95cadac31ed4caeb5672fcf2993cd6b1e207e827b36e274ace83f92
- test_gate.py: 69c0c6d1bfb7e44f42a2d4bb58c27e7713bf82b6af96438c946d681260acc58e

Replay receipt:

- receipt: d2a42d743ca126aab42f54009d2153b97c346efbe31ce82dccf2c3ed5607a24a
- file: bd1414caa51b423ea64f8f6d27a79d256e119680aeb180b7058b3bfa549504db
- 20/20 CPU tests pass;
- 4/4 sealed traces are rejected before close;
- no GPU, scene, planner, action, or artifact mutation.

The Gate checks actual selected-arm qpos and EEF tracking, V8-classified
self/support/bottle contact, and bottle displacement at pregrasp/grasp.
Failure stops before gripper close.

## Proposal boundary

PROPOSED_F3_PRECLOSE_PHYSICAL_CONSISTENCY_MICRO_GATE_V1.json:

- manifest SHA: 1ef3f9b543b4f93cdbccf5948d3022c1116456d04a8dd0d5bf12cdf1c6115b1e
- file SHA: 6d54c7156661090cd75953985dd85f38ddaf84eaeff72ea8ef5da6ab7a6e52dd
- approved=false and every execution authority is false;
- four candidate slots remain deliberately pending;
- future ceiling is 52 planner queries / 12 scenes / 4 physical attempts;
- physical scope ends at conditional 25 mm micro-lift;
- shared-V, suffix, root, raw, and formal remain zero.

Older-protocol 001_bottle/base13 + left-arm evidence had contact fraction 1.0.
It is only an audit lead and must not be silently promoted.

## Requested decision

Because exact candidates are not yet frozen, do not approve a GPU run from
this proposal. Return one of:

1. APPROVE_F3_PRECLOSE_GATE_DESIGN_CPU_CANDIDATE_FREEZE_ONLY_V1, together
   with an exact deterministic candidate-freeze rule and whether a second
   review of the frozen four candidates is required before GPU;
2. REVISE_F3_PRECLOSE_GATE_V1, naming exact code/field/test deficiencies;
3. REJECT_F3_PRECLOSE_GATE_V1, with the conflicting protocol requirement.

Do not authorize retry of r0005/r1505/r2180/r3677, full shared-V, no-suffix,
root generation, Stage 1, formal 360, training, H-reveal, compression or pi0.5.
