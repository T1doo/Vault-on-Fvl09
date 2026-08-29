# F4 arm / asset / layout impact review v6

状态：`cpu_geometry_and_common_route_pass_neutral_orientation_repair_pending`

本修订不改变 F4 的科学设计、common-X、`ABC / ACB / BAC`、对象—槽位映射、托盘位置或执行臂。它只修复 v3_2 run2 暴露的 right-arm branch-neutral 姿态问题。

## 已有真实证据

- planned right-arm layout 已在真实 SAPIEN scene 中生效；common-X 初始位置为约 `(0.28, 0.10)`。
- Route 1 的 9/9 chained planner segments 全部成功并真实执行。
- common-X 放入 official `008_tray/base0` 后，tray footprint、连续支撑、稳定窗口、夹爪打开和 A/B/C 非目标稳定均通过。
- 旧 neutral pose 的位置为 `(0.15, -0.02, 0.95)`，但其四元数未经右臂真实验证；planner 返回 Success 后，实际终态仍有约 `0.1567 m` 位置误差与 `0.0809 rad` 姿态误差。

## v6 冻结修复

保持 neutral 位置不变，将 orientation 冻结为同一 run 中已被 right arm 在 common-grasp 与 transport 段真实跟踪的姿态：

```yaml
layout_version: f4_right_arm_mirror_base0_v2_grasp_neutral
arm: right
branch_neutral_pose:
  - 0.15
  - -0.02
  - 0.95
  - 0.5243570072481656
  - -0.47439082845243685
  - 0.4743935067167858
  - 0.5243604405510669
branch_neutral_orientation_policy: fixed_same_as_realized_right_arm_common_grasp_orientation
```

该四元数通过单位长度检查。机器可读完整布局、资产 hash、CPU geometry checks 与证据引用见同名 JSON。

## 边界

- `formal_data=false`
- `stage0_data=false`
- `stage0_authorized=false`
- common route 已有真实 planner/rollout 证据；新的 neutral orientation 与完整三程序仍待最后一次有限 GPU 验证。
- 本修订不批准 strict block reorder，也不批准 Stage 0。
