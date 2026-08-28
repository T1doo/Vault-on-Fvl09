# pilot_attempt_budget_v0 — runtime-v2 addendum

状态为 `executed_and_exhausted`。F1/F2/F3/F4 各 1 次 execution 已使用，planner 分别为 9/12、7/12、14/18、6/12；剩余 planner headroom 不是 retry 授权。Stage 0/Stage 1 base budget 仍未批准。

本 addendum 只约束 Stage 0 之前的 runtime-v2 nonformal probes，不修改原 Stage 0/Stage 1 root budget：

| Family | Variant | execution | planner queries | timeout |
| --- | --- | ---: | ---: | ---: |
| F1 | `transport_true_inside` | 1 | 12 | 1200 s |
| F2 | `actor_to_eef_stand` | 1 | 12 | 1200 s |
| F3 | `return_equivalence` | 1 | 18 | 1800 s |
| F4 | `common_prefix_mapping` | 1 | 12 | 1800 s |

可从 physical GPU0–7 中选择任一 independently fresh-idle 卡，但全局仍顺序执行、一卡一 job。没有自动 retry 或 recovery；planner limit 用尽即 `aborted_with_reason`。child receipt 缺失、pre/post snapshot 失败、显存/利用率/进程未回 baseline、cleanup 不确定或 task-owned orphan 都必须 fail closed；ownership 不确定的进程不得被杀。F4 common-X 失败时不运行后续 blocks。

Wall-time 和 GPU-hour 仍标记为 `unresolved`，要等这些 probes 有真实结果后再评估。不能通过增加 retry 绕过当前 blocker。
