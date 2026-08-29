# F2 official asset compatibility matrix v2

## Frozen CPU audit order

1. 全部`071_can` IDs与当前`062_plasticbox/base3`；
2. 当前`071_can/base1`与全部`062_plasticbox` IDs；
3. 只有前两项无解时才审计其他较小官方物体。

所有组合先要求官方model-data/visual/collision provenance完整，再要求从官方collision convex pieces导出的strict cavity具有5 mm/side安全margin。通过Gate后的tie按固定ascending model ID，不运行多个GPU组合再择优。

## Result

```yaml
stage1_can_ids_with_box3_solution: none
selection_stage: box_id_with_current_can
selected_main_object: 071_can/base1
selected_plasticbox: 062_plasticbox/base2
selected_arm: left
selected_axis_permutation: [1, 0, 2]
strict_cavity_dimensions_m: [0.156, 0.083, 0.156]
oriented_can_dimensions_m: [0.09657, 0.06508, 0.06528]
minimum_total_clearance_m: 0.017916
safety_margin_per_side_already_removed_m: 0.005
```

Base2 cavity由15个官方convex collision pieces、1 mm line-grid提取，raw cavity约`[0.166,0.093,0.166] m`；strict cavity在每侧再收缩5 mm。Can的长轴通过box-local z旋转映射到cavity x轴。

该更新保留同一个`071_can/base1`、inside/on/beside和left arm，只更新官方plasticbox model ID与scene layout version；不放宽full-OBB predicate，也不改成basket。
