# GPT Review Handoff — Complete Pre-Stage-0 Attempt 2026-08-29

## 审阅入口

Repository：`https://github.com/T1doo/Vault-on-Fvl09`

Branch：`main`

Current decision：`BLOCKED_WITH_REASONS`

Postmortem code/evidence content commit：`28cfb46cf14be9c5850efd1af00489acc5e8b8ee`

最终docs/publication commit与remote HEAD将在本文件发布后回填。

## 建议阅读顺序

1. `Idea/项目核心Idea.md`
2. `数据构造/数据构造方案.md`，特别是D-A.6
3. `数据构造/实现审计/COMPLETE_PRE_STAGE0_EXECUTION_REPORT_20260829.md/json`
4. `数据构造/实现审计/stage0_readiness_report_runtime_v3_1_current.md/json`
5. `数据构造/实现审计/f1_f4_implementation_registry_v3_1_v5_1_current.md/json`
6. `数据构造/实现审计/PRE_STAGE0_GPU_SCOPE_BUDGET_V1.md/json`
7. `数据构造/实现审计/PRE_STAGE0_GPU_SCOPE_REQUESTS_V1.md/json`（historical run1 bundle）
8. `数据构造/实现审计/PRE_STAGE0_GPU_SCOPE_REQUESTS_V1_1.md/json`（run2后terminal）
9. `数据构造/实现审计/probe_outputs/nonformal_A0_F1_seed20260829_run1*`
10. `数据构造/实现审计/probe_outputs/nonformal_A0_F1_seed20260829_run2*`
11. `数据构造/实现审计/代码审阅快照/`
12. `数据构造/正式数据构造日志.md`第77–79节

## 这轮实际完成

- 保存用户完整pre-Stage-0总授权；
- A0 native planner/physics hard Gate、request-bound auth v1.2、source lock v1、guard v2.2；
- F3/F4完整三程序runner、F4 block/noninterference、F3/F4 root final-state equivalence；
- active/snapshot 158/158 CPU tests；
- 真实A0两次，均由独立request/source-lock/one-shot auth/guard启动；
- 两次cleanup/orphan/GPU release全部安全；
- 保留所有失败、consumption、partial current/anchor和日志。

## A0裁决

Run1：`is_sleeping` bool-property兼容失败。修复后run2成功保存pristine current/anchor，但旧validator拒绝SAPIEN的`0.004000000189989805` 4ms表示，同时native planner ledger未初始化。

Run2仍记录：planner=0、controlled action=0、physics=0。它不是same-current/anchor mismatch；但fresh1/2/3未运行，所以A0没有pass。

授权只允许`1 initial + 1 versioned repair`，现已耗尽。没有运行F1–F4或real root。

## Postmortem code

已加入：

```text
4 ms representation tolerance = 1e-9 s
monitor前初始化空RuntimeTraceMixin planner ledger
ledger非零/非空继续fail closed
```

该修复只通过CPU测试，没有真实GPU evidence。

## 请GPT重点裁决

1. 是否同意当前`BLOCKED_WITH_REASONS`与禁止Stage 0？
2. `1e-9 s`是否是对SAPIEN float32 timestep的合理表示容差，而非放宽250Hz合同？
3. 在A0不初始化dense trace的前提下，显式初始化RuntimeTraceMixin-compatible `planner_query_count=0 / planner_queries=[]`，再与独立wrapper双重检查，是否满足native counter hard Gate？
4. 是否建议用户批准一个全新namespace下的额外单次A0，还是应先补其他CPU审计？
5. 在A0未pass前，应继续禁止F1–F4 family scopes和Stage 0。

## Claim boundary

没有Stage 0/1/formal数据，没有训练、`H_reveal`、compression或π0.5。F3/F4 full runner存在不等于物理程序已经跑通。
