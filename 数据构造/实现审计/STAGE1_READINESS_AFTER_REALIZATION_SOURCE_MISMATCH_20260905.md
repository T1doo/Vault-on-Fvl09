# 统一 Stage1 readiness（2026-09-05）

状态：`NOT_READY_REALIZATION_RECOVERY_PENDING_F2_F3_MODEL_GATES_PENDING`。

已验收开发数据仍为 F1 5 roots/15 trajectories、F4 1 root/3 trajectories，共6/18。F2/F3没有完整验收 root；不把局部成功或失败诊断加入这个分母。

新9条变体批次实际启动后首F1入口因旧/新源码指纹冲突停止：1scene/0planner/0physical rollout/0raw，8格未尝试，GPU2已释放。不是9条都执行失败，也不是GPU驱动失败。

CPU恢复版已采用隔离旧F1源码命名空间，active/F4源码不变，15项测试通过；这不等于真实same-current/anchor验收通过。旧V1许可不能直接复用。首格replacement和剩余8格恢复尚未授权；若重新执行9场景，累计场景应记10（包含旧失败1），不能抹掉旧尝试。

Stage1 0/48、formal 0/360；9个既有potential-reuse格不自动promotion。F2 endpoint和F3 world/gripper后续CPU工作可继续，GPU队列受本轮global-stop约束。Stage0封存与旧F4采纳不变；训练/H-reveal/compression/π0.5继续禁止。

完整机器证据见同名JSON；交接入口：`GPT_HANDOFF_REALIZATION_SOURCE_COMPATIBILITY_20260905.md`。
