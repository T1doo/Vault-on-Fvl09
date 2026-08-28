# F1–F4 runtime-v3 CPU current registry

`controlled_multi_future_runtime_v3` 仅完成 CPU/static contracts；没有 GPU 授权，也没有 Stage 0 授权。

| Family | CPU/static current | Runtime |
| --- | --- | --- |
| F1 | red/green/blue 参数化、固定顺序、target-neutral prefix、fresh-scene 与 3/3 Gate | not run |
| F2 | 固定 6 candidates、同 seed/start state、preplace+release planner、禁止 fallback | not run |
| F3 | release 前后多时间点诊断、pad footprint/contact、actual gripper qpos、条件式 correction | not run |
| F4 | obstacle-derived safe height、两条固定 segmented routes、endpoint preflight、tray immutable | not run |

Raw current 是 `controller_effective_setpoint_v1_layout_v2_1`：N+1 state timestamps、N action interval start/end、`planner_goal_eef_pose`、drive-target readback 与真实左右 gripper qpos。

Root orchestrator CPU skeleton 已做到 pristine capture before feasibility、三个 disposable feasibility scenes、freeze once、三个 fresh rollouts 和 3/3 finalizer。cpu5 raw 与 root-cpu2 synthetic evidence 均通过，但 real SAPIEN adapter 尚未实现。

最终仍为 `BLOCKED_WITH_REASONS`。
