# `pilot_attempt_budget_v0` 建议

```text
status = proposed_for_user_review
approved = false
frozen = false
```

该建议用于阻止无限 planner 重试，不是 Stage 0 授权。GPU4–7 首轮 runtime probes 已执行；scene inspection 约 44.6–47.6 秒/family，F1/F3/F4 action probes 约 32.5/39.7/34.2 秒，F2 三关系约 88.9 秒。由于三项 planner failures 尚未修复，Stage 0/1 cost 仍是低置信范围。

## 建议上限

| 项目 | F1 | F2 | F3 | F4 |
|---|---:|---:|---:|---:|
| feasibility queries / candidate | 2 | 2 | 2 | 2 |
| planning attempts / trajectory | 2 | 2 | 2 | 2 |
| execution attempts / trajectory | 1 | 1 | 1 | 1 |
| recovery attempts / trajectory | 1 | 1 | 1 | 1 |
| max trajectory wall time | 30 min | 40 min | 30 min | 60 min |
| max pilot-root wall time | 2 h | 2.5 h | 2 h | 4 h |

所有 family：scene build 每 slot 最多 1 次；pilot root 总 attempt 最多 12。planner 尚未执行前的 `no_path` 可在冻结预算内重试；错误 asset/candidate、anchor mismatch、verifier signal 缺失、F3 丢抓、F4 slot 不可见、GPU ownership/cleanup 不确定和预算耗尽均为 non-retryable terminal failure。

## Probe 预算

- 每个具名 probe 只运行 1 次；每 candidate 最多 2 次 planner query。
- timeout：F1 15 min；F2 每 relation 15 min；F3 单 V/H 10 min、V→H 15 min；F4 单 neutral block 20 min。
- probe 失败后保留输出并停止，不现场换 asset/arm/threshold。

## 暂估成本

- Stage 0：12 条，约 4–10 GPU-hours，低置信；
- Stage 1：累计 48 条，约 18–45 GPU-hours，低置信。

这些范围只用于用户评审和排期，不能写入 frozen budget。版本化 repair probes 和 Stage 0 实测必须继续校准后，才能讨论正式 `formal_attempt_budget_v1`。
