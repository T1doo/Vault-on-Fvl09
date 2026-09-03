# F2/F3 approved execution bridge V1

日期：2026-09-03  
状态：`IMPLEMENTED_CPU_STATIC_VALIDATED_GPU_NOT_YET_RUN`

本桥接层不改 `controlled_multi_future/` 已审阅源树，其 SHA-256 仍为 `cb4cb3b1058f8296febddae5eeb261fa2b9c413187d50cbf45d7de6538af8a43`。运行层文件为 `/nfs_share/lijunhui/Robotwin2/post_recovery_gate_v1/job_runner.py`，SHA-256=`2d6dd7fc8e50539eb10163888cacadd6fab95664417a07839be15fcece2b5af6`，并绑定封存base runner SHA-256=`376ddfbe07b1c9ae3e6e3b2d1975344a8605c6e81e49f27e92241c88a851a1d4`。

## F2

- 按四个已审阅strata顺序运行，每stratum只对official top contacts 8–15各发一次10-rotation batch query。
- 在全部8个batch回执中选取字典序最小的planner-success `(contact_id, rotation_index)`，然后绑定该official pose发出精确3-query `pregrasp→grasp→25mm lift` chain；每stratum恰为8+3=11，四个上限44。
- Physical micro Gate在独立fresh scene中复用刚才已资格验证的3段control，不再新增planner query；只检验接触前tracking、close、接触identity/continuity、25mm lift与post-lift transform/off-table。在这些Gate通过前不进入insertion/release。
- `pregrasp` 或 `grasp` 追踪误差超过5 mm/0.05 rad时，硬拦截`close_gripper`。选中姿态physical失败无fallback；两次连续同类失败立即停止。

## F3

- 直接从full recipe universe精确解析已审阅的四个rotation1 recipe SHA，每个均唯一命中；不使用旧rotation0/5 panel。
- Stage A每candidate 3 queries；Stage B每candidate 7 queries，其首个target与Stage-A lift pose bitwise一致，V/H距离仍为55/50 mm。只有至少两个A+B survivor才进入physical。
- Physical shared-V micro Gate在fresh scene里复用planner已通过的Stage-A 3段和Stage-B前4段control，不新增planner query，以保持全Gate上限40。
- 至少两个physical success时只记录conditional no-suffix trigger与首个成功candidate；三场fresh-scene diagnostic需用该实际终端另行签发一次性派生manifest，不在主Gate中未知candidate就预编译。

## CPU/static validation

- runner AST/import pass；
- F2 full universe构建成功，recipe count=5760；
- F3四个精确recipe SHA均在full universe中唯一命中；
- lift-center 7 targets audit pass，首target精确等于lift pose；
- 未初始化GPU，未创建scene，未发planner query或机器人动作。

本文件只说明执行接线已实现并静态验证，不说明F2/F3已generated、verified或scientifically supported。
