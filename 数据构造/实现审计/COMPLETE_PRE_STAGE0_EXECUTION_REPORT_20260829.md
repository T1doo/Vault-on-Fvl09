# Complete Pre-Stage-0 Execution Report — 2026-08-29

## 通俗总结

## **BLOCKED_WITH_REASONS**

这轮把“开工前的安全系统和完整程序代码”继续补强，并真实启动了两次A0。但A0的有限预算在到达四场景same-current检查前耗尽：第一次卡在SAPIEN接口差异，修复后第二次已能保存真实current/anchor，却被过严的浮点比较和未初始化的native planner ledger挡住。

好消息是两次都安全退出：没有planner/action/physics越界，没有timeout，没有cleanup失败，没有残留进程，GPU0均恢复空闲。坏消息是A0没有pass，所以按预注册Gate，F1–F4一个都不能继续跑，Stage 0更不能批准。

Postmortem CPU代码已经把第二次失败的两个问题修好并通过158/158 tests，但授权只允许“A0初始一次 + versioned repair一次”；两次都已消费，不能悄悄跑第三次。

## 1. A0

| Run | 做到哪里 | 失败原因 | Cleanup/orphan/GPU release |
|---|---|---|---|
| run1 | 创建pristine scene，开始capture current | `is_sleeping`在fvl05为bool property，旧代码当method调用 | pass / 0 / pass |
| run2 | pristine current与anchor均保存 | `0.004000000189989805`被exact-float Gate拒绝；native planner ledger为null | pass / 0 / pass |

Run2真实hash：

```text
current = 0b3160326b189aa4d5592e31ea6c32925ddae0d5b7dec9911348a89c65d95836
anchor  = 27daa3e63ba5040580a6edb7725f28ab7de23490ec754d126ea167310cdb5d76
```

两次post-setup activity均为：

```text
planner = 0
controlled action = 0
physics step = 0
```

但fresh1/2/3没有运行，因此same-current与anchor四场景Gate未完成。

## 2. F1–F4

| Family | 最终代码版本 | 三分支/三程序 | 当前blocker |
|---|---|---|---|
| F1 | `f1_three_branch_coverage_v3_1` | 未运行 | A0前置失败 |
| F2 | `f2_workspace_and_three_branch_v4_1` | 未运行 | A0前置失败 |
| F3 | `f3_release_and_full_program_v3_2` | 未运行 | A0前置失败；historical return仍失败 |
| F4 | `f4_common_carry_and_full_program_v3_2` | 未运行 | A0前置失败；historical common-X仍失败 |

代码层面已经补齐F3 `diagnosis → conditional repair → VVHH/VHVH/VHHV`和F4 `common route → ABC/ACB/BAC`，并让F3/F4终态payload进入root finalizer；这些只是CPU/code readiness，不是物理成功证据。

## 3. 数据管线

| 项目 | 当前状态 |
|---|---|
| real current hash | pristine单场捕获成功；四场等价未验证 |
| real physical anchor | pristine单场捕获成功；四场等价未验证 |
| candidate freeze / task tree / prefix | synthetic通过，real未运行 |
| task/physical vs planner分账 | 代码与测试通过，real未运行 |
| fresh-scene root | 代码与测试通过，real未运行 |
| 26-D / 250 Hz / N+1 | schema/synthetic通过，real family raw未生成 |
| receipt | A0两次真实receipt完整 |
| verifier/finalizer | CPU/synthetic通过，real family未运行 |
| cleanup/orphan | A0两次真实通过 |

## 4. Stage 0 包

没有生成`STAGE0_EXECUTION_MANIFEST_V1`、`STAGE0_ATTEMPT_BUDGET_V1`或`STAGE0_USER_APPROVAL_REQUEST_V1`，因为这些文件要求A0和F1–F4完整成功证据。当前：

```yaml
stage0_root_slots_frozen: 0
stage0_manifest_trajectories: 0
stage0_attempt_budget_frozen: false
stage0_authorized: false
```

## 5. 实际运行统计

```text
GPU runs: 2
physical GPU: 0
planner queries: 0
controlled action executions: 0
timeouts: 0
cleanup failures: 0
orphan count: 0
total guard elapsed: 108.38 s
```

## 6. 关键证据

```text
run1:
probe_outputs/nonformal_A0_F1_seed20260829_run1/
probe_outputs/nonformal_A0_F1_seed20260829_run1.guard.json

run2:
probe_outputs/nonformal_A0_F1_seed20260829_run2/
probe_outputs/nonformal_A0_F1_seed20260829_run2.guard.json

current registry:
f1_f4_implementation_registry_v3_1_v5_1_current.md/json

current readiness:
stage0_readiness_report_runtime_v3_1_current.md/json
```

## 7. 明确没有执行

- 没有正式Stage 0轨迹；
- 没有Stage 1；
- 没有360条正式数据；
- 没有模型训练；
- 没有`H_reveal`裁决；
- 没有compression；
- 没有π0.5。

下一安全动作：审阅两次A0 evidence与postmortem CPU修复。如果用户决定继续，应建立新implementation/request namespace并单独批准新增A0预算；不得复用已消费authorization，也不得跳过A0直接跑family scopes。
