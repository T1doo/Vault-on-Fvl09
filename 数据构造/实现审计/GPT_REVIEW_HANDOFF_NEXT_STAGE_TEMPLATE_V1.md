# GPT review handoff — next-stage template result V1

```yaml
source: 9873bbe87ed44f7d54003e831ddf9015159036da8078e5cab29ccdc9fcd9fc72
stage0: STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE
stage0_reopened: false

F1:
  status: PASS
  roots: 5/5
  trajectories: 15/15 development r_pc
  raw: 15
  mp4: 15
  planner_queries: 230
  executions: 15
  recovery: 0
  reserve_activations: 0
  formal_increment: 0

F2:
  status: FAILED_INFRASTRUCTURE
  error: numpy.bool_ is not JSON serializable
  development_execution_count: 0
  physical_conclusion: null

F3:
  status: FAILED_PHYSICAL
  planner_queries: 7
  prefix_executions: 1
  failure: unstable grasp/contact and bottle still on pad/table

F4:
  status: FAILED_PLANNER_NO_FALLBACK
  prefix_executions: 1
  planner_queries: 11
  first_failed_segment: A_pregrasp
  motiongen_status: IK_FAIL
  rendered_visibility_pass: false

stage1_ready_families: [F1]
canonical_stage1_authorized: false
formal_data_authorized: false
training_authorized: false
h_reveal_authorized: false
compression_authorized: false
pi05_authorized: false
```

Interpretation: F1 has passed the requested scale-pilot test, but these 15 trajectories remain development data. F2 has no new physics result because it failed while serializing its first dynamic audit receipt. F3 now has genuine evidence that the current V2_1 grasp template is physically unstable. F4 c01 is rejected without fallback because the first A pregrasp endpoint is IK-infeasible and the visibility aggregate also fails. Full Stage 1 remains blocked by F2/F3/F4.

Machine report: `NEXT_STAGE_TEMPLATE_DEVELOPMENT_RESULT_V1.json` (`ee374c140c44d4537f95901fcb6a13c0ade018689f939528b1f98bff1af559cf`).
