# Stage 1 readiness after F2/F3 CPU redesign V1

日期：2026-09-03

状态：`NOT_READY_CPU_REDESIGN_READY_FOR_EXTERNAL_REVIEW_GPU_NOT_AUTHORIZED`。

新的 CPU redesign 已把 F2/F3 的下一步从泛化的“再修抓取/规划”收敛为两个明确合同：

- F2：历史失败重分类为接触前 arm tracking failure；新执行入口必须在 close 前通过5 mm/0.05 rad tracking Gate，并通过 planner-assisted official grasp candidate → exact pose freeze 生成新候选。
- F3：Stage B central改为精确 Stage-A lift pose，消除旧137.3 mm全局中心跳转，同时保持table-frame V/H幅度、方向、顺序和等端点。

这两项均已实现为独立版本化模块、用历史证据重放并通过311-file AST；但 exact F2 pose freeze 与新 F3 candidate universe 尚未冻结，也没有新的 GPU 授权，所以不能称 planner/physical ready。

F4仍为 isolation 5/5、full-program template 3/3，但 development root最终失败且禁止替代；终止后的代码修复仍是 `implemented_unvalidated`。F1已有5 roots/15 r_pc，但缺 real r_inv_path/r_inv_motion。

formal accepted仍为0/0；Stage0封存不变，Stage1/formal360/training/H-reveal/compression/π0.5均未授权。新审阅需明确：

1. F2 exact pose-freeze procedure 与新的 bounded physical budget；
2. F3 new candidate universe 与 lift-anchored Stage-B planner/physical budget；
3. 是否允许重新打开一次 F4 final root replacement。

Machine artifact：`STAGE1_READINESS_AFTER_F2_F3_CPU_REDESIGN_V1.json`，payload `36ed92e736fbb3d2e1d35e1c0b6561c49daff481178c8db689084fa9486aff56`。
