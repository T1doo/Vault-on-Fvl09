# F1_000013 attempt8：批准版已就绪，等待固定GPU空闲

最终manifest合同：`c367702b0f02a08acd1c14392a040ec3da994ec0f4785454d17279297a9b7775`。

用户已明确批准预算扩展及两条motion。timeout5200、cleanup100、overhead100，合计5400≤5501。最终授权版本的真实validate_manifest及完整恢复preflight均通过，正式CLI也再次通过前置。

实际恢复读取器确认只复用F1-red，待采集队列只有F1-green、F1-blue；logical attempt=8。六条旧数据、red原raw/失败receipt、prefix/baseline未更改。

首次正式CLI到达实时Guard时，固定GPU0被外部compute作业占用，未获得lease、未启动child、未生成attempt_8目录，无新增消耗。顶层历史FAILED不代表此次物理失败；有效状态是WAITING_FIXED_GPU_IDLE。其他GPU空闲不授权本root跨卡。

累计cap：fresh/action/collection/solver/GPU=28/15/3/64/7200。
累计消耗：18/9/1/0/1699；预留为零。
本次最大预留：10/6/2/64/5501；未执行任何attempt9。

数据状态：原六条保留，red真实执行并通过只读复核，green/blue未执行，root仍INCOMPLETE；尚无新9/9或完整副本交付。

运行状态目录：`/nfs_share/lijunhui/Robotwin2/datasets/f1_motion_recovery_20260911_attempt8_approved/recovery_state`。
恢复仍使用本目录manifest及该状态目录recovery_request.json，经first_wave_launcher正常入口，固定UUID实时Guard。一次只运行本root，发生物理/共享实现失败后停止，不自动重试。
