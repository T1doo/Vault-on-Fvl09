# F1 three-object reachability impact review v1

状态：`cpu_comparison_complete_joint_margin_pending_planner_only_gate`。

## v3_2 证据比较

| Role | 12 cm chain | Failure | Grasp workspace margin | 6 cm midpoint margin | 12 cm lift margin |
|---|---|---|---:|---:|---:|
| red | passed | — | 0.1020 m | 0.0780 m | 0.0180 m |
| green | passed | — | 0.1020 m | 0.0780 m | 0.0180 m |
| blue | failed | second 6 cm `target_lift` | 0.1014 m | 0.0786 m | 0.0186 m |

三色的几何 workspace margin 几乎一致；blue 不是因为 CPU bounding box 明显更差。v3.2 receipt 只保存 terminal qpos hash，没有保存真实 terminal qpos 数值，因此 joint-limit margin 不做猜测，必须由新的固定 GPU0 planner-only Gate 补齐。

## 公平修复

```yaml
rule: all red/green/blue use two 4cm world-z lift segments
total_lift: 8cm
layout_changed: false
grasp_orientation_changed: false
role_specific_parameter: false
planner_only_gate_required: true
```

该规则不移动 blue、不改变身份/位置关系，也不给任何颜色特殊路径。只有三色 3/3 planner-only 通过后，才允许运行完整 F1 root。

完整 poses、segment hashes、pairwise clearance 与 pending 字段见同名 JSON。
