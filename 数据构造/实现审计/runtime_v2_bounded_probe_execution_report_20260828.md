# runtime-v2 bounded probe execution report

## BLOCKED_WITH_REASONS

四条已批准 nonformal probes 已全部到达终态，均在 physical GPU1 上顺序运行。结果是 1 pass / 3 terminal failures：

| Family | 结果 | 关键结论 |
| --- | --- | --- |
| F1 | PASS | 红方块 true-inside、连续 box support、绿/蓝全阶段稳定、rest/stationarity 全通过；但只证明红分支 |
| F2 | FAIL | 同一 `071_can/base1 + left arm + stand` 的三个预注册 yaw 均通过几何检查，但真实 planner preflight 全部失败 |
| F3 | FAIL | V/H realized motion 与抓取连续性全部通过；最终瓶子位置误差 4.10 cm、姿态误差 0.156，return-equivalence 失败 |
| F4 | FAIL | swept geometry 通过，但 safe-horizontal waypoint planner 失败；按 ordered Gate 未运行任何后续 block/program |

首次 F1 child 曾因调用者继承 host CUDA 12.2 而在 scene 前 import 失败，execution/planner=0。Guard 随后内建 workspace activation contract，固定 CUDA 12.1；环境修复后的 F1 才是唯一真实 F1 attempt。

所有实际 family runs 均 cleanup 成功、orphan=0、timeout=0，GPU1 每次 postcheck 都回到 14 MiB、0%、无 compute process。没有自动 retry，也没有 Stage 0、正式数据或训练。

当前不能继续原地调参。F2/F3/F4 的下一版，以及 F1 绿/蓝分支扩展，都需要新的 impact review 和 implementation version。真实 SAPIEN fresh-scene pipeline integration 仍未完成。
