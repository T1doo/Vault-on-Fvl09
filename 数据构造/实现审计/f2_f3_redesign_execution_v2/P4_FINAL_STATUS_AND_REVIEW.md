# P4 F2/F3 当前状态（2026-09-09）

## 结论

本轮 P4 已停止物理采集。F3-B 的独立 root finalizer 对 6 个 cell 返回通过，F3-A 的 6/6 证据保留；F2 v4/v5 的高位路线在 `beside_side_at_target` 失败；随后按链接要求修复了底层失败传播、S0/S1 状态恢复和碰撞支撑几何。基于对照，v6 直接几何路线的 `beside:r_pc` 已真实通过，但 F2-A 剩余五格因 P4 GPU 余额只剩 48 秒而未采集。因此不能把 F2/F3 合并报告成完整 24 格，更不能启动 formal360、训练、H-reveal 或压缩。

F2 v5 真实作业保存了完整 t0 RGB/state/anchor 和失败 trace；S0/S1 诊断取得了真实底层 IK_FAIL，并证明正确碰撞底部目标可达。v6 资格样本保存了完整 t0/prefix/trace 并由独立 finalizer 通过。由于两次入口接线失败按保守上限核销了 GPU，当前 P4 只能暂停剩余物理采集，不能把单个 v6 cell升级成完整 F2 root。

## 账本与资源

P4 账本累计实际消耗为：fresh=12、action=9、collection=9、solver=130、GPU lease=7152 秒；当前 reservation 全为 0，剩余 GPU 48 秒。F2 child 的 owned cleanup 通过；结束后宿主快照确认选中 GPU 回到 14 MiB、0% 利用率、P8、无 compute process。

## 可保留的研究范围

- F3-B-v2：独立 root finalizer 通过的 6 个 scoped pilot cell，可进入当前 P4 eligibility index。
- F3-A：保留为既有 scoped evidence；本报告不把它自动升级为新 24 格完整资格。
- F2-A/B：完整 root 当前不具备研究资格；F2-A 的 v4/v5 失败 trace 与 v6 单格正证据均保留，v6 单格只作为开发/审计/positive control。
- 全部旧 raw、旧 Goal、旧接受回执和失败历史保持不变。

## 主要证据

- P4 合同与账本：`p4_execution/P4_EXECUTION_CONTRACT.json`、`p4_execution/execution_ledger.jsonl`
- 当前状态：`p4_execution/P4_STATE.json`、`p4_execution/P4_PROGRESS_SUMMARY.json`
- F2 v5 CPU 候选：`P4_CPU_F2_V5_CANDIDATE.json`
- F2 v5 失败分析：`P4_F2_V5_FAILURE_ANALYSIS.json`
- F2 v5 作业回执：`p4_execution/p4-f2-a-beside-qualification-v5.json`
- F2 v5 路径诊断：`P4_F2_V5_PATH_DIAGNOSTIC.json`（query 8 到达 side_at_current，随后 0.1414 m 横向转移在 planner 前失败）
- F2 S0/S1 底层诊断：`P4_F2_POST_WAYPOINT_DIAGNOSTIC_ANALYSIS.json`
- F2 v6 资格对账：`P4_F2_V6_QUALIFICATION_RECONCILIATION.json`
- F2 v6 GPU 收尾：`P4_F2_V6_POST_COMPLETION_IDLE_CHECK.json`
- F3-B finalizer 对账：`P4_F3B_ROOT_FINALIZER_RECONCILIATION.json`
- 当前资格索引：`P4_CURRENT_RESEARCH_ELIGIBILITY.json`
- 运行源快照：`runtime_source_snapshot_v39/SNAPSHOT_MANIFEST.json`

F3-B runner 的 `root_receipt.json` 保持原样；它早于独立 root finalizer 的最后一次 CPU 对账，仍显示历史 runner 状态。当前结论以独立 finalizer 和 reconciliation receipt 为准，未改写 raw 或旧回执。
