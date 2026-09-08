# F2 beside 首格有界失败报告

日期：2026-09-09  
任务：`f2_f3_observation_contract_repair_20260909_p3`  
范围：仅记录 F2-A-v2 `beside:r_pc` 的真实尝试，不改变旧 raw、旧 Goal 或研究验收定义。

## 结论

四次真实执行都在抓持和高位搬运完成后，第一次前往 beside 目标的 planner query 失败。失败发生在支撑、释放、稳定和独立关系验收之前，因此不能把它归因于 `beside` verifier，也不能把失败轨迹改标签为成功。

目前最强的共同证据是：抓持后的 EEF 姿态和目标物体姿态保持稳定，前七次 planner query 成功；第八次 query 在以下目标族中均返回 `None`/`Failed`：

| attempt | v2 版本 | 第八次目标 EEF 的位置 | 失败标签 |
|---|---|---|---|
| 1 | 原目标，stand 中心 +120 mm | x≈0.200, y≈−0.187, z≈1.094 | `v2_beside_lateral` |
| 2 | 目标改为 +160 mm | x≈0.240, y≈−0.187, z≈1.094 | `v2_beside_lateral` |
| 3 | 高位负 y 绕行 | x≈0.240, y≈−0.300, z≈1.094 | `v2_beside_beside_far_y` |
| 4 | 高位正 y 绕行 | x≈0.240, y≈−0.061, z≈1.094 | `v2_beside_beside_far_y` |

四次都记录了动作前四相机 RGB、76-D state、完整 anchor、trace row0 和实际 planner query；没有一条进入真实 table 支撑窗口。原始 job receipt 与 trace 路径见：

```text
/nfs_share/lijunhui/Robotwin2/datasets/f2_f3_observation_contract_repair_p3/
  p3-f2-a-beside-rpc.retry1/beside_r_pc/
  p3-f2-a-beside-rpc.retry2/beside_r_pc/
  p3-f2-a-beside-rpc.retry3/beside_r_pc/
  p3-f2-a-beside-rpc.retry4/beside_r_pc/
```

## 已排除的解释

* `beside` 目标并非落在 stand 顶面：CPU 几何合同使用 stand 作为参照、table 作为承重面，目标位于合法 annulus；stand-top 负例仍被拒绝。
* 目标不是单纯因为 x=0.20 太近：+0.16 m 目标和两个相反 y 高位路线都在同一 planner 阶段失败。
* 不是 RGB、state 或 anchor 缺失：四次真实 t0 bundle 都读回通过；失败发生在 query 8。
* 不是终态 verifier 误判：没有进入 support/release/terminal 阶段，独立 finalizer 对这些 partial cell 不会给 accepted。

## 当前可支持的工程判断

在当前抓持姿态下，`left_move_to_pose` 对从 carry 到 x≈0.20–0.24 的目标（以及两个 y 变体）没有返回成功路径。现有证据不足以把原因进一步归结为某个单独的关节极限、碰撞体或姿态奇异性；需要一次新的、预注册的 CPU/物理可达性检查来区分：

1. 保持物体与关系合同，重新设计 stand/桌面布局，使合法 annulus 落在当前抓持姿态可达区域；或
2. 保持布局，预先定义另一种可验证的抓持姿态/目标变换，再重新检查完整开爪、退出和支撑包络。

这两种方案都会产生新的 scene/spec/current/anchor lineage，不能用改 seed、改标签或只修改 receipt 解决。由于本轮 F2 beside 已达到四次有界恢复停止条件，报告不自动启动第五次物理尝试。

## 资源事实

F2-A beside 四次真实尝试结算为 `fresh=4`、`action=4`、`collection=4`、`solver=32`、`GPU lease=505 s`；另有一次最初调度器目录接线失败，`collection=1`、`GPU lease=1 s`，无物理 scene。该失败事实保留在 P3 ledger 的事件链中。F3-A `VHVH:r_pc` 已独立通过一条；F3-A 剩余五格的 reservation 因调度器崩溃后的 lease 未知而暂时保留，未继续派发。

本报告是失败影响和下一设计边界，不是 F2 科研资格通过声明，也不改变用户已批准的总 cap 或 F3 已有正结果。
