# P4 F2/F3 当前状态（2026-09-09）

## 结论

本轮 P4 已停止物理采集。F3-B 的独立 root finalizer 对 6 个 cell 返回通过，F3-A 的 6/6 证据保留；F2 的唯一有界 v5 候选资格验证仍在 `beside_side_at_target` planner 控制处失败，与 v4 为同一失败阶段。因此不能把 F2/F3 合并报告成完整 24 格，更不能启动 formal360、训练、H-reveal 或压缩。

F2 v5 真实作业保存了完整 t0 RGB/state/anchor 和失败 trace。失败是动作可达性问题，不是通过修改关系谓词或阈值制造的成功。按 P4 有界规则，F2 物理资格在此关闭，不再盲试第三个布局。

## 账本与资源

P4 账本累计实际消耗为：fresh=10、action=8、collection=8、solver=117、GPU lease=1910 秒；当前 reservation 全为 0。F2 child 的 owned cleanup 通过；结束后宿主快照确认选中 GPU 回到 14 MiB、0% 利用率、P8、无 compute process。

## 可保留的研究范围

- F3-B-v2：独立 root finalizer 通过的 6 个 scoped pilot cell，可进入当前 P4 eligibility index。
- F3-A：保留为既有 scoped evidence；本报告不把它自动升级为新 24 格完整资格。
- F2-A/B：当前不具备研究资格；F2-A 的 v4/v5 beside 失败 trace 作为开发和失败诊断证据保留。
- 全部旧 raw、旧 Goal、旧接受回执和失败历史保持不变。

## 主要证据

- P4 合同与账本：`p4_execution/P4_EXECUTION_CONTRACT.json`、`p4_execution/execution_ledger.jsonl`
- 当前状态：`p4_execution/P4_STATE.json`、`p4_execution/P4_PROGRESS_SUMMARY.json`
- F2 v5 CPU 候选：`P4_CPU_F2_V5_CANDIDATE.json`
- F2 v5 失败分析：`P4_F2_V5_FAILURE_ANALYSIS.json`
- F2 v5 作业回执：`p4_execution/p4-f2-a-beside-qualification-v5.json`
- F3-B finalizer 对账：`P4_F3B_ROOT_FINALIZER_RECONCILIATION.json`
- 当前资格索引：`P4_CURRENT_RESEARCH_ELIGIBILITY.json`
- 运行源快照：`runtime_source_snapshot_v32/SNAPSHOT_MANIFEST.json`

F3-B runner 的 `root_receipt.json` 保持原样；它早于独立 root finalizer 的最后一次 CPU 对账，仍显示历史 runner 状态。当前结论以独立 finalizer 和 reconciliation receipt 为准，未改写 raw 或旧回执。
