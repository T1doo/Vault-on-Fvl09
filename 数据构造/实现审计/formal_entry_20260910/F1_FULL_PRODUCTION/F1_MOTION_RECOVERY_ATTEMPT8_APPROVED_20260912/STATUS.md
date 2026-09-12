# F1_000013 attempt8：已收尾，prefix current 合同阻断

最终manifest合同：`c367702b0f02a08acd1c14392a040ec3da994ec0f4785454d17279297a9b7775`。

用户已明确批准预算扩展及两条motion。timeout5200、cleanup100、overhead100，合计5400≤5501。最终授权版本的真实validate_manifest及完整恢复preflight均通过，正式CLI也再次通过前置。

实际恢复读取器确认只复用F1-red，待采集队列只有F1-green、F1-blue；logical attempt=8。六条旧数据、red原raw/失败receipt、prefix/baseline未更改。正式入口随后取得GPU0 lease并启动child。

首次正式CLI到达实时Guard时，固定GPU0被外部compute作业占用，未获得lease；等待后重启同一批准入口，GPU0空闲并通过Guard。attempt8随后实际创建5个fresh场景、1个action场景并耗用518秒GPU lease。三项任务物理可行性均通过，随后在 canonical prefix reference 阶段停止；没有任何正式 branch、green/blue motion 或新 raw。

终端错误为 `SameCurrentMismatch.__init__() missing 1 required positional argument: 'receipt'`。该构造器错误已在 CPU 源码中修正，并新增回归测试。修正后的审计还明确记录了真实 prefix 复用 current 不一致：封存 prefix 的 reconstruction source 为 `574a205b...`，新鲜场景为 `c8dcac07...`，anchor 也出现 physics_config 差异；因此旧 prefix 不能在当前源码/场景配置下直接复用。

attempt8 的 `physical_started=false` 指的是正式 motion branch 未开始；场景已创建且 GPU child 已运行，不能把这次当作零成本或未执行 attempt。旧 raw、失败 receipt 和 recovery_6 root receipt 均保留原样，账本已结算。

累计cap：fresh/action/collection/solver/GPU=28/15/3/64/7200。
累计消耗：23/10/1/0/2217；预留为零。
本次最大预留：10/6/2/64/5501；未执行任何attempt9。

数据状态：原六条保留，red真实执行并通过只读复核，green/blue未执行，root仍INCOMPLETE；尚无新9/9或完整副本交付。剩余预算约为fresh5/action5/collection2/solver64/GPU4983秒，但当前批准不允许在未解决prefix current合同前重试。

运行状态目录：`/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911_attempt8_approved/recovery_state`。
恢复仍使用本目录manifest及该状态目录recovery_request.json，经first_wave_launcher正常入口，固定UUID实时Guard。一次只运行本root，发生物理/共享实现失败后停止，不自动重试。下一步仅限CPU影响审查：决定是否冻结匹配旧prefix的源码/配置，或批准一次新的prefix/root采集合同；不能用现有剩余额度假设可直接补 green/blue。

2026-09-13 CPU审查新增一个候选方案：`f1_prefix_source_alias_v1`。它只把已经审查过的实现来源差异转换为 prefix 复用的比较视图，原始 RGB、state、anchor 文件和 live source 都保持不变。实际 sealed/fresh current/anchor 对账显示底层字段一致，相关 CPU 套件已 54/54 通过；该 alias 仍是候选，未写入本批准 manifest/authorization/STATE，也不授权任何新的物理 attempt。
