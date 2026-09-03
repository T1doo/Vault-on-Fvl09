# GPT review request after F2/F3/F4 recovery Gates V2

请审阅以下终端与提案：

1. `POST_RECOVERY_F2_F3_GATE_TERMINAL_V1.json`
2. `STAGE1_READINESS_AFTER_EXTERNAL_REVIEW_GATES_V1.md/json`
3. `production_micro_gate_v1/RUN13_DEVELOPMENT_ROOT_TERMINAL_V1.json`
4. `POST_GATE_CPU_ROOT_CAUSE_AND_NEXT_PROPOSALS_V1_20260903.md`
5. `PROPOSED_NEXT_RECOVERY_REVIEW_PACKET_V2.json`
6. `PROPOSED_F4_GUARD_COMPLETE_REOPEN2_MANIFEST_V1.json`

关键新证据：F2 top-contact grasp/lift 2/2通过；F3仅1个rotation1 planner survivor，lift-centered Stage B已通过而其余失败在pregrasp；F4 Run13在child/GPU/scene前因manifest缺asset map终止，新CPU static preflight已精确复现并对含完整asset map的新提案全14项pass。

请按以下YAML返回明确决定；`REVISE` 必须写出exact tuple/budget/stop condition：

```yaml
F2:
  decision: APPROVE_AS_PROPOSED | REVISE | DENY
  exact_changes: []
  root_invocation_cap: 1
  planner_query_cap: 75
  fresh_scene_cap: 8
  robot_action_scene_cap: 4
  branch_cap: 3
  development_root_cap: 1
  formal_trajectory_cap: 0

F3:
  decision: APPROVE_AS_PROPOSED | REVISE | DENY
  exact_changes: []
  retained_survivor_rerun: false
  replacement_tuples:
    - [bottle5, right, lower_body, contact2, rotation1, r1505]
    - [bottle4, left, upper_body, contact0, rotation6, r2180]
    - [bottle13, right, upper_body, contact2, rotation5, r3677]
  planner_query_cap: 30
  planner_scene_cap: 6
  physical_candidate_cap: 4
  conditional_no_suffix_scene_cap: 3

F4:
  decision: KEEP_CLOSED | REOPEN_EXACTLY_ONCE_AGAIN
  exact_changes: []
  if_reopened_planner_query_cap: 136
  if_reopened_fresh_scene_cap: 8
  if_reopened_robot_action_scene_cap: 4
  if_reopened_branch_cap: 3
  if_reopened_development_root_cap: 1
  formal_trajectory_cap: 0

global:
  allowed_physical_gpu_indices: [0, 1, 2, 3, 4, 5, 6, 7]
  Stage0_rerun: false
  Stage1_authorized: false
  formal360_authorized: false
  training_authorized: false
  H_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false
```

F4若再次开放，必须说明这是Run13零child/零GPU/零scene的Guard-schema修复例外，并明确禁止后续再开。当前两个proposal manifest均`approved=false/executable=false`，本请求本身不是GPU或Stage1授权。
