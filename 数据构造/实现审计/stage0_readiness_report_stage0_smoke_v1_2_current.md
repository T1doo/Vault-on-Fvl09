# Stage 0 v1.2 seal 与 Stage 1 readiness

## STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE

Stage 0已正式封存：12个active slots均有可信terminal evidence，无active infrastructure/schema/current/cleanup/source blocker。历史F2 v1.1 infrastructure attempts保留但由三个v1.2 replacement active receipts替代。

下一阶段当前CPU freeze为`V1.3`：source=`9873bbe8…fc72`。V1.2的F1 run3、F2 run1、F3 run3、F4 run3因全卡外部繁忙而过期且从未消费；新identity为F1/F3/F4 run4、F2 run2。

V1.3 development wave已终端：F1通过5/5 roots与15/15 development trajectories；F2为首个dynamic receipt的NumPy bool JSON基础设施失败、没有新物理结论；F3为真实prefix物理失败；F4 c01在A_pregrasp IK失败且无fallback。当前仅F1具备Stage 1 candidate readiness，canonical Stage 1仍未授权。

```yaml
F1:
  stage0_status: PASS
  stage1_candidate_ready: true
  batch_pilot_cpu_implemented: true
  batch_pilot_gpu_status: PASS
  accepted: 5/5 roots, 15/15 trajectories
  reserves: 0
  target: 5 development roots / 15 r_pc trajectories

F2:
  stage0_replacement_result:
    inside: FAILED_EXECUTION_WITH_EVIDENCE
    on: PASSED
    beside: PASSED
  development_template_ready: false
  cpu_asset_matrix: 1650 rows / 860 static-admissible
  bounded_dynamic_ranks: 50-61
  selected_binding: null
  status: FAILED_INFRASTRUCTURE
  blocker: NumPy bool JSON serialization before development execution

F3:
  stage0_status: FAILED_EXECUTION_WITH_EVIDENCE
  development_template_ready: false
  closure_v1_status: FAILED_INFRASTRUCTURE_BEFORE_PHYSICAL_DIAGNOSTIC
  physical_prefix_attempts: 0
  v2_1_interface_cpu_status: PASS
  v2_1_real_physical_attempts: 1
  old_closure_retry: forbidden
  status: FAILED_PHYSICAL
  blocker: unstable grasp/contact; bottle remained on pad/table

F4:
  stage0_status: FAILED_PLANNER_WITH_EVIDENCE
  development_template_ready: false
  closure_v1_status: ENTERED_ENDPOINT_IK_NO_COMPLETE_ROUTE
  entered_endpoint_ik: true
  complete_route_solved: false
  finite_layout_search_cpu_status: PASS
  cpu_selected_layout: f4-layout-v2-c01
  cpu_selection_is_ik_evidence: false
  selected_layout_gpu_status: FAILED_A_PREGRASP_IK
  rendered_visibility_pass: false
  blocker: c01 rejected; fallback/temporary waypoint forbidden

canonical_stage1_authorized: false
```

Post-Stage-0 Closure V1旧namespace保持终端且不得重跑。新工作包已完成四family CPU实现与source freeze，但尚未运行GPU：F1 batch、F2 bounded dynamic asset audit、F3 V2_1新namespace、F4 c01 selected-layout planner-only均为pending。CPU结果不能替代物理/IK证据，统一结论保持`canonical_stage1_authorized=false`。
