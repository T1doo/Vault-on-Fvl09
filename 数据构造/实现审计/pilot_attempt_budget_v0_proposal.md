# `pilot_attempt_budget_v0` 建议

```text
status = proposed_for_user_review
approved = false
frozen = false
```

该建议用于阻止无限 planner 重试，不是 Stage 0 授权。所有已批准 bounded repairs/fallbacks 已执行并保留 terminal failures；F4 在 common-X 第一 Gate 停止，因此仍不能批准 Stage 0/1 wall-time 或 GPU-hour 数值。

## 计数语义

- `feasibility_query_count`：对一个冻结 candidate 做一次 task/physical feasibility 审计；成功失败都计数。
- `planner_query_count`：一次真实 motion-planner segment call；内部每段分别计数。
- `execution_attempt_count`：所需计划形成后，开始应用 realized control 的一次 rollout。
- `recovery_attempt_count`：失败后显式允许的一次恢复动作；成功 rollout 内的正常撤离不算 recovery。
- `max_total_attempts_per_root` 只等于该 root 的 execution + recovery；feasibility 与 planner query 使用独立上限，不混入该总数。

## 建议上限

| 项目 | F1 | F2 | F3 | F4 |
|---|---:|---:|---:|---:|
| feasibility queries / candidate | 2 | 2 | 2 | 2 |
| planning attempts / trajectory | 2 | 2 | 2 | 2 |
| execution attempts / trajectory | 1 | 1 | 1 | 1 |
| recovery attempts / trajectory | 1 | 1 | 1 | 1 |
| max trajectory wall time | 待 repair/F4 完整测量 | 待测量 | 待测量 | 待完整程序测量 |
| max pilot-root wall time | 待测量 | 待测量 | 待测量 | 待测量 |

所有 family：`max_slot_spec_generation_attempts=1`；每次 attempt 必须 fresh-scene reconstruction。Stage 0 每 root 是 3 条 `r_pc`，execution≤3、recovery≤3、total≤6；Stage 1 完成后的单 root 是 6 条 rollout，execution≤6、recovery≤6、total≤12。planner 尚未执行前的 `no_path` 只能在冻结 planning-site retry budget 内重试；错误 asset/candidate、anchor mismatch、verifier signal 缺失、F3 丢抓、F4 slot 不可见、GPU ownership/cleanup 不确定和预算耗尽均为 non-retryable terminal failure。

## Probe 预算

- 每个具名 repair variant 只运行 1 次；F1/F2 place 段与 F3 return 段最多 2 次 planner segment calls。
- timeout：F1/F2 每 variant 15 min；F3 每 return variant 30 min；F4 每个自然程序 45 min。
- probe 失败后保留输出并停止，不现场换 asset/arm/threshold。

## 成本状态

Stage 0 的 12 条与 Stage 1 累计 48 条设计规模不变，但 GPU-hour 范围不批准。当前 family blockers 必须先经过 impact review 和新 implementation version 批准；不得通过提高 retry budget 绕过失败。当前仍只能写 `proposed_for_user_review / approved=false / frozen=false`。
