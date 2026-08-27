# Stage 0 readiness

## `BLOCKED_WITH_REASONS`

静态审计、registry、additive skeleton、7/7 CPU tests、GPU4–7 environment certification、F1–F4 scene inspection 和首轮有限 action probes 已完成，但还不满足 `READY_FOR_USER_REVIEW_BEFORE_STAGE_0`。

已通过：F2 同一 `071_can/base1`/同一左臂的 inside/on；F3 V/H/V→H realized motion 与完整 contact continuity；F4 yellow-X visible scene 和单 A neutral block。

核心 blockers：F1 block→box place planning 失败；F2 beside place planning 失败；F3 return-to-original-pad place planning 失败；F4 full common-X + ABC/ACB/BAC/noninterference/reorder 未测试；budget 仍只是 proposal。

当前没有 Stage 0 授权。下一安全动作是先做 CPU-only versioned repair design；首轮具名失败 probes 不原地重试、不换 asset/arm/threshold 掩盖失败。任何新 targeted probe 都必须使用新 namespace 和 GPU4–7 fresh idle Gate。
