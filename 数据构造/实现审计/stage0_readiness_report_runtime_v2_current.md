# Stage 0 readiness — runtime v2 current

## BLOCKED_WITH_REASONS

`controlled_multi_future_runtime_v2` 的四条 bounded probes 已执行完毕；active 与 byte-equal Vault snapshot 均为 32/32 tests passed。实际 family 结果为 F1 红分支 PASS，F2/F3/F4 terminal FAIL；cpu2 synthetic pipeline 仍仅是软件证据。

| Family | CPU/static 修复 | runtime-v2 probe | 是否完整跑通 |
| --- | --- | --- | --- |
| F1 | true cavity、support、rest、non-target | 红分支全部通过；绿/蓝未运行 | 否 |
| F2 | actor→EEF + real planner preflight | 三个姿态 planner 全 Fail | 否 |
| F3 | realized EEF+bottle V/H + return | V/H PASS；final pose FAIL | 否 |
| F4 | common-X mapping | safe-horizontal planner FAIL；后续未运行 | 否 |

公共 trace/raw 问题已在代码层修复：effective/requested/planner target 分开，完整双臂 realized state，quaternion angular velocity，逐字段来源，明确 26-D 顺序，N/N+1 adapter，强制 N+1 object/contact audit 与 250 Hz cadence。GPU guard v2 对 child receipt、pre/post snapshot 和显存/利用率/进程回 baseline 都 fail closed。

仍然缺少两类决定性证据：

1. 四个 runtime-v2 family probes 的真实 SAPIEN 结果；
2. 一个真实 SAPIEN fresh-scene current/anchor/raw/verifier integration。

Stage 0 的 `pilot_attempt_budget_v0` 继续保持未批准；仅 runtime-v2 nonformal probe addendum 已获批准并冻结。当前只允许 physical GPU0。

四条授权 probes 已结束，不能在当前版本内继续重试。下一步需要新的 impact review 和 implementation version；该轮从未授权 Stage 0、Stage 1、360 条正式数据或任何训练。
