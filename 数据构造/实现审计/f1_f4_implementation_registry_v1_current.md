# F1–F4 current implementation registry v1

本文件只更新“当前状态”，不覆盖 `f1_f4_implementation_registry.{md,json}` 的历史证据。当前唯一设计仍为 `controlled_multi_future_f1_f4_v1_2`，正式数据与 Stage 0 数据均为 0。

## 当前 runtime 范围

- host：fvl05；用户最新允许物理 GPU0–7 中任意一张 independently fresh-idle 卡，无固定优先或排除编号；每个 child 启动前独立检查并绑定 UUID。
- 监控结果不能替代 child 启动前的即时复核。首轮 environment、joint-scene 和 action probes 已运行，不能再写 `pending_gpu0` 或 `runtime probe not run`。
- F4 white common-X 失败证据保留；当前 scene 使用不改变科学语义的 yellow common-X v2。

## 当前状态

| Family | 已通过 | 当前 blocker | versioned next probe |
|---|---|---|---|
| F1 | fp1 planner 完成且非目标稳定；interior OBB inside=true | fp1 不 inside；interior 移动 green/blue 5.63/1.97 cm；两方案已用尽 | stop / unresolved |
| F2 | 同一 `071_can/base1`/left arm 的 inside/on；pot CPU audit | stand sector1/2 与 pot_left 均 place planner fail | stop / unresolved |
| F3 | realized V/H；bottle_fp 完成 planning/release | pad_center planner fail；bottle_fp position/orientation/rest errors 过大 | stop / unresolved |
| F4 | yellow-X 可见；历史 single A neutral block | common-X→tray place planner fail；顺序 Gate 停止后续 | stop at F4-01 |

## 当前代码

active source 已实现并通过 20/20 CPU tests：cleanup `finally`、dense trace v2、candidate freezer、current hash、anchor equivalence、26-D/250 Hz/N+1 raw writer、attempt state machine、receipt/finalizer、semantic probe Gate、atomic GPU guard 和 F2 pot fallback。全部获准 bounded repairs 已执行到 terminal status；没有进一步 GPU retry 权限。CPU synthetic integration 仍不能替代真实 SAPIEN fresh-scene integration。

机器可读完整字段见同名 JSON。
