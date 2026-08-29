# F1 uniform carry-hub revision-2 impact review v1

状态：`CPU_IMPLEMENTED_GPU_NOT_YET_AUTHORIZED`。

## 唯一物理修复

保持revision-1已通过的同一官方planner-assisted top-down grasp、4 cm+4 cm lift和1.02 m安全高度；删除每个role原地升至1.02 m的`safe_vertical`，改为先在8 cm lift高度移动至冻结canonical cluster-neutral的共同xy，再在共同xy升高：

```text
target_pregrasp
target_grasp
target_lift_mid
target_lift
carry_hub_low   = [-0.11, 0.02, role lift_z, same grasp q]
carry_hub_high  = [-0.11, 0.02, 1.02, same grasp q]
safe_horizontal
preplace
release
retreat
rest
```

三色使用完全相同的target-construction函数；没有`if blue`。不改变slot、seed、scene layout、left arm、RGB roles、plasticbox/base3、candidate universe、canonical prefix、release target或verifier。

Revision-1实际`T_eef_actor`的posthoc swept-AABB复核得到非目标最小间隔：red≈0.0360 m、green≈0.05841 m、blue≈0.0360 m；共同hub对box outer AABB保守间隔均大于0.062 m。新纯CPU nominal check三色最小vertical surface clearance为0.036 m。几何只排除明显hard blocker，真实机器人路径仍必须由官方CuRobo逐段通过。

## Planner审计修复

Additive wrapper现在逐次记录官方`left/right_plan_multi_path` grasp-target selection：contact point、batch size=10、ordered goal hash、每个candidate status、selected index、start-qpos hash、planner reset及wrapper restoration。计数单位是一次官方batch API call，内部10个candidate另行记录。

F1 revision-2 source-bound上限：

```text
canonical prefix explicit planner       1
4 grasp-selection batch calls × 3      12
11 frozen suffix segments × 3          33
total                                  46 < 64
```

同一修复也覆盖F2/F3 canonical grasp chooser与F4 common-X chooser；新的static planner envelopes分别为F2=35、F3=55、F4=125，均低于既有scope budgets。Root orchestrator额外要求runtime planner API delta与receipt count完全相等。

## GPU与停止线

Revision-2只能运行一次、同一root identity；3/3 suffix planners全部通过前execution=0。任一planner或semantic branch失败即F1 terminal incomplete，不允许revision-3、改seed/arm/layout、降低高度或放宽verifier。

当前active与byte-equal snapshot source SHA-256：`40e2ef209ba407e44cdf952637d4725b57daa8194f9cde0cd7ab6d6b2cfaf037`；revision-1 source为`fd26a46f…`，已满足source-distinct条件。Active/snapshot各256/256 CPU tests通过。GPU授权仍必须等本baseline发布和新source-lock完成后另行签发。
