# F2 physical compatibility impact review

## 结论

```text
F2 status: terminal_failed_task_physical_feasibility
repair execution: not justified
Stage 0 eligible: false
```

固定对象与设施：

```yaml
main_object: 071_can/base1
arm: left
inside_target: 062_plasticbox/base3
on_target: 072_electronicscale/base0
beside_target: 074_displaystand/base3
```

真实task/physical receipt中，roles、same object、left arm、relations、scale functional point、六个beside候选的桌面范围与box/scale clearance均通过。唯一失败是`can_fits_box_cavity=false`。

资产几何：

```yaml
can_outer_half_extents_m:
  - 0.0325419861
  - 0.0482850832
  - 0.0326393597
can_minimum_full_dimension_m: 0.0650839722
box_strict_cavity_dimensions_m:
  - 0.100
  - 0.052
  - 0.080
box_minimum_cavity_dimension_m: 0.052
```

因此，can最小完整直径仍大于box严格内部短轴约13.1 mm；无姿态能使完整OBB进入该cavity。历史center/loose inside成功不能替代当前要求的full-OBB inside。

当前授权禁止更换main can；共享任务只允许在BESIDE stand失败后做stand或pot impact revision，不能用更换box或放宽inside verifier修复本问题。因此没有执行伪repair或planner重试。
