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
  blocker: sole post-Stage-0 no-suffix diagnostic failed physical pre-V Gate; second diagnostic forbidden

F4:
  stage0_status: FAILED_PLANNER_WITH_EVIDENCE
  development_template_ready: false
  blocker: new-layout CPU geometry passed, but sole planner-only run failed derivation infrastructure before endpoint IK and cannot be retried

canonical_stage1_authorized: false
```

Post-Stage-0 review已完成：F3唯一diagnostic物理失败；F4 CPU geometry通过但唯一planner-only run在IK query前发生interface infrastructure failure，且两者均不得在当前single-use合同下重跑。F2 inside仍为release-safety blocker。统一结论保持`canonical_stage1_authorized=false`；需要新的影响审阅与用户批准才能定义后续repair scopes。
