# Post-Stage-0 Closure V1 — F4 result

状态：`ENTERED_ENDPOINT_IK_NO_COMPLETE_ROUTE`。

V2 derivation interface通过并真正进入endpoint planner。新layout的F4-ABC中，A_pregrasp、A_grasp、A_lift和A_carry_mid均规划成功；第5个A_preplace返回`MotionGenStatus.IK_FAIL`。总计10个canonical-prefix queries + 5个suffix queries，qpos chain与joint-limit evidence完整；suffix execution/release均为0。

因此F4不是接口失败，而是新layout下没有得到完整可解route。按Closure V1停止线，不运行ACB/BAC、不添加临时waypoint、不开放A-only development，进入新的layout impact review。

GPU2 task-owned cleanup通过且返回原idle baseline：14 MiB/0%/P8、orphan=0、无后到外部进程；source-lock、cache和lease均通过。
