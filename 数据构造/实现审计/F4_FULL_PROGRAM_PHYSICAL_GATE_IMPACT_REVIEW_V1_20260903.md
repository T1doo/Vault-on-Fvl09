# F4 full-program physical Gate impact review V1

日期：2026-09-03  
范围：post-Stage-0、nonformal、development qualification only

## 1. 触发证据

Run 2 的 r01 F4 候选已经取得以下真实物理证据：

- `F4-ABC/F4-ACB/F4-BAC` 三个 source planner terminal 均为 42-query pass；
- `A_ONLY/B_ONLY/C_ONLY/AB_NONINTERFERENCE/AC_NONINTERFERENCE` 五个物理隔离 Gate 全部通过；
- 五个 fresh scene 的 current aggregate SHA 均为 `d5b115e413423884648a22dc3d6f8760ec4c92e483e0880ba2f76ccdb7107f8d`；
- 五个 pre-prefix physical anchor SHA 均为 `e68389999f99405bb6624b4f701161b314baca0b516d4e3c8cd74cb8839c9815`；
- authoritative prerequisite receipt 为 `RUN2_MICRO_GATE_TERMINAL_V1.json` payload `ad8f34ca9d8c1780329d95a767a90205856604aa899a2c224edc8d988cefec40`。

因此，执行计划中“隔离门全部通过后才允许同一 r01 的 ABC/ACB/BAC”条件已满足。该证据只解锁三条完整程序各一次，不授权新的 layout/candidate 搜索、F4 isolation 重跑、第二个 development root 或 Stage 1。

## 2. 实现变化

新增 `controlled_multi_future/f4_full_program_physical_v1.py`，它只组合现有且已真实验证的组件：

- 沿用 r01 source grasp candidate、r01 slot corridor candidate、program/object-slot mapping；
- 沿用 Run 2 三个精确 planner terminal；
- 沿用 common-X prefix、每个 role 的 10-segment target、gripper close/open、75-step settle；
- 沿用现有 slot footprint、稳定性、table support、common-X preservation、gripper-open 和 neutral-pose verifier；
- 沿用 frozen final-state equivalence tolerance：position 0.03 m、orientation 0.20 rad；
- 新增的只是完整 role sequence `ABC/ACB/BAC` 的显式串联、最终 A/B/C/common-X/EEF payload 记录，以及三分支 same-current、same-anchor、final-state-equivalence 聚合。

未修改现有 F4 isolation module、候选、目标姿态、动作顺序、阈值、正式 denominator、split 或科学 claim。

## 3. 精确运行预算与停止规则

- 固定顺序：`F4-ABC → F4-ACB → F4-BAC`；
- 每条程序最多 1 个 fresh physical scene、1 次物理执行、1 条 debug trace、1 个 MP4；
- 每条 full program planner query limit=42，总上限=126 queries/3 scenes/3 physical/3 MP4；
- 任一程序失败立即停止，不执行后续程序；不自动 retry，不换 seed/candidate/layout；
- F2、F3、F4 isolation 均禁止重跑；
- accepted/formal/training trajectory count 固定为 0。

## 4. 资格边界

只有同时满足以下条件，才能记录 `F4 full-program template qualification pass`：

1. 三条程序均真实执行且各自完整 verifier pass；
2. 三条分支 current aggregate SHA byte-identical；
3. 三条分支 pre-prefix physical anchor SHA byte-identical；
4. 三条最终状态按冻结 comparator 等价；
5. 每次 scene cleanup、Guard cleanup、GPU post-release 均通过。

即使全部通过，本 Gate 仍不是 accepted development root：current 尚未按 root-once/reference-only 规范封装，缺少正式 root finalizer、failure/orphan/balance/leakage receipts，且没有 `r_inv_path/r_inv_motion`。通过后只允许进入“最多一个 F4 development r_pc root”的下一独立 Gate。

## 5. CPU/静态校验结果

- active source 与 Vault review snapshot byte-equal；
- 新 module 与更新后的 run-layer runner 均 AST pass；
- 使用 Run 2 三个 immutable planner terminal 构建并重新验证三份 full-program spec，program order 分别为 `ABC/ACB/BAC`，query limit 均为 42；
- 三份 spec SHA 分别为 `9a3800dd25119ca0d4a4354010c3bbb3a83556456465d762535526fe54bf2cfe`、`cb732b45e192318335b80691de07d54776448ed2529b3c1f88113e717af36e45`、`9c9ffa307487b162d75132dcac6e8e50ec4a84ec58ddc3dc99c210c1769bdc71`；
- 未运行新 fake-heavy CPU suite，未初始化 GPU。

当前 controlled source SHA：`24a3a3bf1b367761e65f296f8251395292680643e54e16682a96c5c303fb73db`。

