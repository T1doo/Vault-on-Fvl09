# Stage 0 readiness

## `BLOCKED_WITH_REASONS`

静态审计、registry、cleanup/trace、atomic GPU guard、Stage-0-shaped pipeline、20/20 CPU tests、synthetic integration、scene inspection 和多轮有限 repair probes 已完成，但仍不满足 `READY_FOR_USER_REVIEW_BEFORE_STAGE_0`。

已通过：F2 同一 `071_can/base1`/同一左臂的 inside/on；F3 V/H/V→H realized motion 与完整 contact continuity；F4 yellow-X visible scene 和单 A neutral block。

新增代码已通过 synthetic 的 candidate/current/anchor/prefix/raw/receipt/verifier/finalizer 控制流，并验证 26-D/250 Hz/N+1 contract；这不是实际 SAPIEN fresh-scene 证据。

核心 blockers：F1 两个 bounded variants 均未同时满足 inside/non-target predicates；F2 stand 两 sector 和 pot_left 全部 place planner fail；F3 pad_center planner fail、bottle_fp 最终位置/姿态/rest 不等价；F4 common-X→tray 在第一 Gate place planner fail，后续程序按规则未运行；真实 SAPIEN pipeline integration 未运行；budget 仍只是 proposal。

当前没有 Stage 0 授权。所有已批准 bounded repair/fallback 均已到 terminal status；停止 GPU probing。必须先做 family-level impact review 并批准新的 implementation version，不能原地重试或换 asset/arm/threshold 掩盖失败。
