# 统一 Stage 1 readiness — 2026-09-05

结论：仍为 NOT_READY，但 F4 的三条真实执行已经跑通。阻碍整组最终入账的是一处收据同步错误，不是物理失败。严格 accepted development 仍为 5 roots / 15 trajectories（全部 F1）；F4 新增 3 raw + 3 MP4 单列为“物理和原始数据通过、外层封存待修复”，不提前计入 accepted。

| 家族 | 已完成 | 当前下一步 |
| --- | --- | --- |
| F1 | 5 development r_pc roots / 15 trajectories；invariance CPU 设计 | 单独冻结并批准真实 r_inv_path/r_inv_motion |
| F2 | Run3 inside planner 5/5；目标语义修复 9/9 CPU tests | 澄清 collision inventory 与 live metadata 的中心数值差异，再完成 beside-only 6-query 专属执行入口 |
| F3 | 4 exact recipes；新 pre-close executor/Guard/runner；23 runtime + 8 window tests，CPU preflight 通过 | 窄复审后才可运行最多 52 queries / 12 scenes / 4 micro attempts；尚无新 physical 正证据 |
| F4 | ABC/ACB/BAC 均通过物理和分支检查，3 raw/MP4、inner root accepted、GPU 已释放 | CPU-only hash-bound append-only receipt resolution 复审；不重跑机器人 |

F4 使用 GPU4，136 planner queries / 11 fresh scenes / 7 action scenes / 3 branches，耗时约 36.7 分钟。外层唯一失败是三份 branch receipt 的 `first_post_prefix_divergence_step` 在磁盘为 2851、root 为 2926。三 raw 重算确认 2926；canonical P 保持 2851。单字段派生视图的只读 finalizer 验证全部通过，原文件未改；原 job terminal 仍 pass=false，修复尚未被采纳为新 acceptance。

Stage 0 不重开。Stage 1 authorized accepted=0/48，formal accepted=0/40 roots、0/360 trajectories；训练、H-reveal、compression、π0.5 未授权。不能将 F4 物理通过或 F3 CPU 通过说成后续科学 Gate 通过。

机器依据：`STAGE1_READINESS_AFTER_F4_ROOT1_RECEIPT_SYNC_20260905.json`，receipt=`13d6ee408d72227f3f522729b2b113d31930c95d620a325b80c50ea79a9dac35`。本次总交接入口：`GPT_HANDOFF_F4_ROOT1_RECEIPT_RECOVERY_F2_F3_20260905.md`。
