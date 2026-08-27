# F1–F4 bounded repair execution report

## 结论

`BLOCKED_WITH_REASONS`

所有已批准的有限 repair/fallback 都已运行到 terminal status。没有 Stage 0 数据；不得继续原地重试。

| Family | 最终结果 | Terminal blocker |
|---|---|---|
| F1 | fp1：非目标稳定但 block 不 inside；interior：inside=true，但 green/blue 位移 5.63/1.97 cm | 两个 bounded targets 均未通过完整 strict verifier |
| F2 | 同一 `071_can/base1 + left arm` 的 inside/on 保留通过；stand sector1/2 与 pot_left 都 place planner fail | stand/pot authorized references 全部用尽 |
| F3 | V/H realized core 仍成立；pad_center return pre-place planner fail；bottle_fp planner 完成但 final errors 很大 | 两个 return variants 均失败 |
| F4 | F4-01 common-X→tray place planner fail | ordered Gate 停止 B/C、AB、ABC/ACB/BAC 与 strict reorder |

F3 bottle_fp 的 V/H 事件 selected-gripper contact fraction 均为 1.0、break=0，但最终 bottle position/orientation/rest errors 分别约 `0.2515 m / 0.9969 / 0.3862 m`，不能因 motion core 成功而升级为完整 F3 成功。

## GPU 安全闭包

- 当前规则：GPU0–7 任意编号，只用即时 independently fresh-idle 卡。
- 本阶段 task-owned GPU children=12；timeouts=0；scene cleanup failures=0；orphans=0。
- 最后一个 F2 pot_left job 结束后，GPU5=`14 MiB / 0% / no compute process`。
- 曾有四次 guard precheck 发现其他用户已占用而 exit 42；没有 child。

## 下一步

停止 GPU probing。需要对 F1 non-target interference、F2 joint-scene reachability、F3 release/final-state reconstruction、F4 common-X tray mapping 做 impact review，并批准新的 implementation version，才能再运行任何 probe。Stage 0 仍未授权。
