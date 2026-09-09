# P4 F2/F3 当前状态（2026-09-09）

## 结论

本轮 P4 已完成 F2-A、F2-B 两个六格 root，并通过独立 root finalizer；F3-A、F3-B 六格证据也已分别通过或完成兼容性保留审计。当前资格索引包含 **24 个 scoped pilot 输入**。这表示本轮 24 格输入矩阵齐备，不等同于 formal Stage1 科学结论；formal360、训练、H-reveal、压缩和 π0.5 均未启动。

F2 的关键修复已经得到真实证据：旧高位 `side_at_target` 从 S0/S1 都是底层 `IK_FAIL`，碰撞 mesh 推导的真实罐底支撑目标从 S1 可达；v6 采用“side_at_current → geometry target”，F2-A/B 均完成了真实旁放、inside、on、path/motion 变体和独立验收。

## 账本与资源

P4 累计实际消耗：fresh=24、action=21、collection=21、solver=182、GPU lease=9600 秒；当前 reservation 全为 0。相对合同上限 fresh=32、action=28、collection=24、solver=480、GPU=14400，剩余 fresh=8、action=7、collection=3、solver=298、GPU=4800 秒。

旧的 5000 秒保守核销记录保持原样，并在账本中标记为非实测；后续作业已按真实 end evidence 和实际 lease 结算。

## 当前资格

- F2-A-v2：v5 布局、direct geometry route，6/6 accepted。
- F2-B-v2：v5 布局、0.12 m lift recovery、direct geometry route，6/6 accepted。
- F3-A-v2：既有 6/6 root finalizer 通过；兼容性审计确认当前差异仅为碰撞边界 metadata 增补，保留为 scoped pilot。
- F3-B-v2：time-scaled 6/6 root finalizer 通过。
- 全部旧 raw、旧 Goal、旧接受回执和失败历史保持不变；F2 v4/v5 失败轨迹继续作为失败/诊断证据。

## 验证

当前 active source 的 py_compile 和真实 CLI 参数链测试通过，`test_redesign_f2_f3_v2.py` 为 **28/28**。CLI 测试实际经过参数解析、`run_root`、seed root 读取和 `_f2_cell` 参数绑定，在场景边界停止；没有把主函数或 root 结果替换成固定成功。

## 主要证据

- P4 合同与账本：`p4_execution/P4_EXECUTION_CONTRACT.json`、`p4_execution/execution_ledger.jsonl`
- 当前状态与摘要：`p4_execution/P4_STATE.json`、`p4_execution/P4_PROGRESS_SUMMARY.json`
- 当前资格索引：`P4_CURRENT_RESEARCH_ELIGIBILITY.json`
- 四族 24 格聚合对账：`P4_SCOPED_24_FINAL_RECONCILIATION.json`
- F2-A root 对账：`P4_F2A_ROOT_FINALIZER_RECONCILIATION.json`
- F2-B root 对账：`P4_F2B_ROOT_FINALIZER_RECONCILIATION.json`
- F3-A 保留兼容性审计：`P4_F3A_PRESERVED_COMPATIBILITY_AUDIT.json`
- F2 S0/S1 诊断：`P4_F2_POST_WAYPOINT_DIAGNOSTIC_ANALYSIS.json`
- F2 v6 资格对账：`P4_F2_V6_QUALIFICATION_RECONCILIATION.json`
- 运行源快照：`runtime_source_snapshot_v43/SNAPSHOT_MANIFEST.json`

F2-B root 的 cell 回执逐格记录了 0.12 m lift；root-level lift 字段修复在其运行后完成，因此以 `P4_F2B_ROOT_FINALIZER_RECONCILIATION.json` 作为该事实的对账入口。
