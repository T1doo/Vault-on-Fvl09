# GPT review request: F4 infrastructure-corrected root V1

日期：2026-09-04

性质：`EXTERNAL_REVIEW_REQUEST_NOT_AUTHORIZATION`

请审阅 F4 CPU-only Infrastructure Recovery V2 是否足以 supersede 旧
`CLOSED_NO_REOPEN_REQUESTED`，并决定是否允许恰好一个 infrastructure-corrected
development `r_pc` root。

## 当前证据

- F4 scientific status=`PHYSICALLY_QUALIFIED`：Run2 isolation 5/5；Run9
  ABC/ACB/BAC real physical 3/3；same-current/anchor/final-state equivalence通过。
- Run10–Run14均在branch前由task-feasibility/accounting/NameError/manifest schema/
  Guard-runner lifecycle基础设施问题终止，没有新的真实branch动作失败。
- 新Runtime V2不修改candidate、program、layout、arm schedule、threshold、verifier或
  source planner terminals。

## CPU 修复证据

- execution plan SHA=`f219a4e57f617b322a9526f939bf9498716f4e428ba220bbd80e64e21e7cfe12`
- Runtime source freeze HEAD=`9b4efa5691a746688c2516abb3d99b5659d66eb8`
- contract=`64484a94d436e5c521975b8906c427965235865c278f16e7a935a63376f58bb9`
- Guard=`884ccd6c946991b95f8a92e2c7740bc83eb6e6a4d4ae09d0a047cd1f4f7d7702`
- runner=`e9217b437e360e0fdd2540420ff86b094c5ec4f8e59c1aebd37458aa1e89e175`
- lifecycle source=`cc3c1db3b12a8e735d4c24e3afd7e3b195257a14bcad5430a9d4c7a9781c5c36`
- proposal manifest SHA=`8afaf49a83aaaedc9473cd20866ad06e2b18e1f8adfcd1e6747baa401ce0a4f5`
- final lifecycle receipt=`3df1f4c21fec4c1b7f304c8a0f08351179f0eaf1dad2039e699be02547d3a3ba`

生命周期测试覆盖真实 Guard→runner path transition、13个负例、Run10–Run14具名
回归、proposal真实Guard fail-closed、strict root finalizer及NumPy serialization。
测试全程scene/GPU/output/authorization consumption均0。

## 若批准，精确 root scope

```yaml
decision: APPROVE_ONE_F4_INFRASTRUCTURE_CORRECTED_ROOT_V1
candidate: f4-slot-corridor-hv2-r01
programs: [F4-ABC, F4-ACB, F4-BAC]
fixed_arm_schedule:
  canonical_prefix: right
  program_suffix: left

maximum_root_invocations: 1
maximum_canonical_prefix_generations: 1
maximum_suffix_prefix_replays: 3
maximum_branch_prefix_replays: 3
maximum_total_prefix_replays: 6
maximum_suffix_preflights: 3
maximum_branch_executions: 3
maximum_planner_queries: 136
maximum_fresh_scenes: 11
maximum_robot_action_scenes: 7
maximum_raw_trajectories: 3
maximum_debug_videos: 3
maximum_accepted_development_roots: 1
maximum_accepted_development_trajectories: 3
maximum_formal_trajectories: 0

fallback_allowed: false
candidate_search_allowed: false
seed_retry_allowed: false
second_root_allowed: false
automatic_retry: false

stage0_rerun: false
stage1: false
formal360: false
training: false
h_reveal: false
compression: false
pi05: false
```

批准时请要求发布一个新的、hash-bound、`approved=true` manifest；不要修改或覆盖
当前 `approved=false` proposal。该 F4 root 仍须服从 F2 first、clean postcheck、F3 V2
之后的串行调度，并在启动时重新做两轮稳定 driver/GPU fresh-idle Gate。

## 请返回

```yaml
f4:
  decision: KEEP_CLOSED | APPROVE_ONE_F4_INFRASTRUCTURE_CORRECTED_ROOT_V1 | REVISE
  exact_scope_if_revised: null

stage0_rerun: false
stage1: false
formal360: false
training: false
h_reveal: false
compression: false
pi05: false
```
