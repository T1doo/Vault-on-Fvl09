# Stage 0 v1.2 seal 与 Stage 1 readiness

## STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE

Stage 0已正式封存：12个active slots均有可信terminal evidence，无active infrastructure/schema/current/cleanup/source blocker。历史F2 v1.1 infrastructure attempts保留但由三个v1.2 replacement active receipts替代。

```yaml
F1:
  stage0_status: PASS
  stage1_candidate_ready: true

F2:
  stage0_replacement_result:
    inside: FAILED_EXECUTION_WITH_EVIDENCE
    on: PASSED
    beside: PASSED
  development_template_ready: false
  blocker: inside release-safety

F3:
  stage0_status: FAILED_EXECUTION_WITH_EVIDENCE
  development_template_ready: false
  blocker: shared pre-V grasp/stationarity/support boundary

F4:
  stage0_status: FAILED_PLANNER_WITH_EVIDENCE
  development_template_ready: false
  blocker: old layout has no planner-solvable complete corridor

canonical_stage1_authorized: false
```

下一阶段不是直接运行48条Stage 1，而是：F3共享前缀impact review与最多一次3-fresh无suffix diagnostic；F4 versioned layout impact review、CPU geometry/IK/planner-only审计与最多一个development root；同时F2 inside需在Stage 1前作为family implementation问题处理。未经用户新批准，不运行Stage 1。
