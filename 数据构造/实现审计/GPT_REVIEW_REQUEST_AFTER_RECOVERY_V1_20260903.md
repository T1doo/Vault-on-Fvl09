# 可直接转发给GPT的审阅请求

请以以下文件为唯一current evidence，不要建议重跑Stage0，也不要恢复旧152/1696-query路线：

1. `POST_RECOVERY_NEXT_GATE_REVIEW_PACKET_V1_20260903.md`
2. `PROPOSED_NEXT_GATE_MANIFEST_V1.json`
3. `LINK_EXECUTION_COMPLETION_AUDIT_V1.md/json`
4. `STAGE1_READINESS_AFTER_F2_F3_CPU_REDESIGN_V1.md/json`
5. `production_micro_gate_v1/RUN12_DEVELOPMENT_ROOT_TERMINAL_V1.json`

当前事实：

- F2旧physical是接触前arm tracking failure，不是盒子太小；新proposal仅用官方top contacts 8–15，planner cap 44、physical cap 4。
- F3旧四tuple为rotation0；新proposal固定四个rotation1 recipe，并使用lift-anchored Stage B，planner cap 40、physical cap 4。
- F4 isolation 5/5、full-program 3/3真实通过；development root最终在branch前失败。明显NameError已静态修复，但Run12规定后续不得replacement。
- formal accepted仍0/0；Stage1、formal360、训练、H-reveal、compression、π0.5未授权。
- proposal manifest当前`approved=false`且被validator证明不可执行。

请返回一个明确、可机械转录的决定，格式如下：

```yaml
F2:
  decision: APPROVE_AS_PROPOSED | REVISE | DENY
  exact_changes: []
  planner_query_cap: 44
  physical_candidate_cap: 4

F3:
  decision: APPROVE_AS_PROPOSED | REVISE | DENY
  exact_changes: []
  planner_query_cap: 40
  physical_candidate_cap: 4
  conditional_no_suffix_scene_cap: 3

F4:
  decision: KEEP_CLOSED | REOPEN_EXACTLY_ONCE
  exact_changes: []
  if_reopened_planner_query_cap: 136
  if_reopened_branch_cap: 3

global:
  allowed_physical_gpu_indices: [0,1,2,3,4,5,6,7]
  Stage0_rerun: false
  Stage1_authorized: false
  formal360_authorized: false
  training_authorized: false
  H_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false
```

若选择REVISE，请必须给出具体candidate tuple、query/scene/physical cap和停止条件，不能只说“再多试几个”。
